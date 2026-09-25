import re
import string
from pathlib import Path
from typing import Any, Literal

import soupsieve
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from swiss_grounding.corpus.models import SourceSpec


class SourceEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    publisher: str
    authority: Literal["federal_law", "cantonal_law", "municipal_law", "official_info", "institutional"]
    level: Literal["federal", "cantonal", "municipal"]
    extent_id: str
    connector: Literal["fedlex", "html", "json"]
    tier: int = Field(ge=1, le=3)
    languages: tuple[Literal["de", "fr", "it", "en", "rm"], ...] = Field(min_length=1)
    config: dict[str, Any] = {}
    retrieved_via: str | None = None

    @model_validator(mode="after")
    def _connector_config(self) -> "SourceEntry":
        if self.connector == "html":
            for key in ("start_urls", "allow_prefixes"):
                if not self.config.get(key):
                    raise ValueError(f"source {self.id}: html connector needs config.{key}")
            _check_site_adaptations(self.id, self.config)
        if self.connector == "fedlex" and not self.config.get("sr_numbers"):
            raise ValueError(f"source {self.id}: fedlex connector needs config.sr_numbers")
        if self.connector == "json":
            _check_json_config(self.id, self.config)
        dupes = sorted({lang for lang in self.languages if self.languages.count(lang) > 1})
        if dupes:
            raise ValueError(f"source {self.id}: duplicate languages: {dupes}")
        return self

    def to_spec(self) -> SourceSpec:
        return SourceSpec(id=self.id, name=self.name, publisher=self.publisher, authority=self.authority,
                          level=self.level, extent_id=self.extent_id, connector=self.connector, tier=self.tier,
                          languages=tuple(self.languages), config=dict(self.config),
                          retrieved_via=self.retrieved_via)


def _string_list(source_id: str, config: dict[str, Any], key: str) -> list[str]:
    value = config.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise ValueError(f"source {source_id}: config.{key} must be a list of non-empty strings")
    return value


def _check_delay_seconds(source_id: str, config: dict[str, Any]) -> None:
    if "delay_seconds" not in config:
        return
    value = config["delay_seconds"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"source {source_id}: config.delay_seconds must be a number >= 0")


def _check_site_adaptations(source_id: str, config: dict[str, Any]) -> None:
    """Optional per-site keys of the html connector: fail at load time, not mid-crawl."""
    _check_delay_seconds(source_id, config)
    for key in ("pdf_link_patterns", "sitemap_include", "deny_patterns"):
        for pattern in _string_list(source_id, config, key):
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"source {source_id}: config.{key} has an invalid regex {pattern!r}: {exc}") from exc
    for url in _string_list(source_id, config, "sitemap_urls"):
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"source {source_id}: config.sitemap_urls must be absolute URLs, got {url!r}")
    for key in ("language_links_selector", "content_selector"):
        if key not in config:
            continue
        selector = config[key]
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError(f"source {source_id}: config.{key} must be a non-empty CSS selector")
        try:
            soupsieve.compile(selector)
        except soupsieve.SelectorSyntaxError as exc:
            raise ValueError(f"source {source_id}: config.{key} is not a valid CSS selector: {selector!r}") from exc


JSON_PAGING_STYLES = ("none", "offset", "page", "next")
JSON_URL_FIELDS = frozenset({"offset", "size", "page"})


def _template_fields(source_id: str, key: str, template: Any) -> set[str]:
    """The top-level field names a `str.format_map` template uses; a syntax error fails at load time."""
    if not isinstance(template, str) or not template.strip():
        raise ValueError(f"source {source_id}: config.{key} must be a non-empty template")
    try:
        names = [name for _, name, _, _ in string.Formatter().parse(template) if name is not None]
    except ValueError as exc:
        raise ValueError(f"source {source_id}: config.{key} is not a valid template: {exc}") from exc
    return {re.split(r"[.\[]", name, maxsplit=1)[0] for name in names}


def _check_json_config(source_id: str, config: dict[str, Any]) -> None:
    """The json connector's keys (connectors/json_api.py): fail at load time, not mid-fetch."""
    _check_delay_seconds(source_id, config)
    url = config.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError(f"source {source_id}: json connector needs config.url, an absolute URL")
    unknown = _template_fields(source_id, "url", url) - JSON_URL_FIELDS
    if unknown:
        raise ValueError(f"source {source_id}: config.url may only use {{offset}}, {{size}} and {{page}}, "
                         f"got {sorted(unknown)} (double a literal brace)")
    if not isinstance(config.get("records_path"), str):
        raise ValueError(  # noqa: TRY004 - pydantic turns only ValueError into a validation error
            f"source {source_id}: json connector needs config.records_path (\"\" for one record)")
    for key in ("id_template", "title_template"):
        _template_fields(source_id, key, config.get(key))
    if not config.get("text_template") and not config.get("html_path"):
        raise ValueError(f"source {source_id}: json connector needs config.text_template or config.html_path")
    for key in ("text_template", "url_template"):
        if key in config:
            _template_fields(source_id, key, config[key])
    paging = config.get("paging") or {}
    if not isinstance(paging, dict) or paging.get("style", "none") not in JSON_PAGING_STYLES:
        raise ValueError(f"source {source_id}: config.paging.style must be one of {JSON_PAGING_STYLES}")
    style = paging.get("style", "none")
    if style in ("offset", "page") and "{" + style + "}" not in url:
        raise ValueError(f"source {source_id}: paging style {style!r} needs {{{style}}} in config.url")
    for where, key, low in ((paging, "size", 1), (paging, "first_page", 0), (config, "max_records", 1)):
        value = where.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < low):
            raise ValueError(f"source {source_id}: {key} must be an integer >= {low}")
    replace = config.get("url_replace")
    if replace is not None and (not isinstance(replace, list) or len(replace) != 2
                                or not all(isinstance(x, str) and x for x in replace)):
        raise ValueError(f"source {source_id}: config.url_replace must be [from_prefix, to_prefix]")
    crumbs = config.get("breadcrumbs")
    if crumbs is not None and (not isinstance(crumbs, dict) or set(crumbs) - {"id_path", "title_path"}):
        raise ValueError(f"source {source_id}: config.breadcrumbs takes only id_path and title_path")
    reason = config.get("robots_exception_reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError(f"source {source_id}: config.robots_exception_reason must be a non-empty explanation")


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    sources: tuple[SourceEntry, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> "Manifest":
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source ids: {dupes}")
        return self

    @model_validator(mode="after")
    def _disjoint_prefixes(self) -> "Manifest":
        """Two sources crawling overlapping URL spaces would fight over who owns each document."""
        owned = [(s.id, _url_prefixes(s)) for s in self.sources]
        for i, (first_id, first) in enumerate(owned):
            for second_id, second in owned[i + 1:]:
                clash = next(((a, b) for a in first for b in second if a.startswith(b) or b.startswith(a)), None)
                if clash:
                    raise ValueError(f"sources {first_id} and {second_id} have overlapping URL prefixes: "
                                     f"{clash[0]!r} and {clash[1]!r}")
        return self


def _url_prefixes(source: SourceEntry) -> tuple[str, ...]:
    config = source.config
    return tuple(config.get("allow_prefixes") or ()) + tuple(config.get("pdf_allow_prefixes") or ())


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def select_sources(manifest: Manifest, tier: int, source_ids: tuple[str, ...] = ()) -> tuple[SourceSpec, ...]:
    """Sources at or below `tier`, in manifest order; `source_ids` narrows further when given."""
    if source_ids:
        known = {s.id for s in manifest.sources}
        unknown = sorted(set(source_ids) - known)
        if unknown:
            raise ValueError(f"unknown source ids: {unknown}")
    chosen = [s for s in manifest.sources if s.tier <= tier and (not source_ids or s.id in source_ids)]
    return tuple(s.to_spec() for s in chosen)
