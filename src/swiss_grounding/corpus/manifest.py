import re
import string
from pathlib import Path
from typing import Any, Literal

import soupsieve
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from swiss_grounding.corpus.models import SourceSpec

# Every config key a connector reads (connectors/html.py and html_page.py, json_api.py, fedlex.py), plus
# `ca_bundle`, read when the HTTP client is built. Any other key is a typo the connector would ignore.
_COMMON_KEYS = frozenset({"delay_seconds", "ca_bundle"})
CONFIG_KEYS = {
    "fedlex": frozenset({"sr_numbers"}),
    "html": _COMMON_KEYS | {
        "start_urls", "allow_prefixes", "max_pages", "sitemap_urls", "sitemap_include", "sitemap_rewrite",
        "language_links_selector", "content_selector", "deny_patterns", "pdf_allow_prefixes", "pdf_link_patterns",
        "max_pdfs", "max_pdf_bytes", "pdf_urls", "json_link_attributes", "keep_html"},
    "json": _COMMON_KEYS | {
        "url", "paging", "records_path", "id_template", "title_template", "text_template", "html_path",
        "url_template", "url_replace", "cite_url", "published_path", "modified_path", "breadcrumbs", "max_records",
        "robots_exception_reason"},
}


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
        unknown = sorted(set(self.config) - CONFIG_KEYS[self.connector])
        if unknown:
            raise ValueError(f"source {self.id}: unknown config key(s) for the {self.connector} connector: {unknown}")
        _check_fetch_keys(self.id, self.config)
        if self.connector == "html":
            if not self.config.get("allow_prefixes"):
                raise ValueError(f"source {self.id}: html connector needs config.allow_prefixes")
            if not self.config.get("start_urls") and not self.config.get("pdf_urls"):
                raise ValueError(f"source {self.id}: html connector needs config.start_urls (or config.pdf_urls)")
            _check_site_adaptations(self.id, self.config)
            prefixes = tuple(_string_list(self.id, self.config, "allow_prefixes"))
            outside = [u for u in _string_list(self.id, self.config, "start_urls") if not u.startswith(prefixes)]
            if outside:  # the crawl would skip them without a word
                raise ValueError(f"source {self.id}: config.start_urls {outside} are outside config.allow_prefixes")
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


def _check_fetch_keys(source_id: str, config: dict[str, Any]) -> None:
    """Per-source fetch settings (#57, #12): a CA bundle for a host with an incomplete certificate chain,
    a larger PDF size limit, raw HTML kept, and a sitemap index that names an internal host."""
    bundle = config.get("ca_bundle")
    if bundle is not None and (not isinstance(bundle, str) or not bundle.strip()):
        raise ValueError(f"source {source_id}: config.ca_bundle must be the path of a PEM file")
    size = config.get("max_pdf_bytes")
    if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size < 1):
        raise ValueError(f"source {source_id}: config.max_pdf_bytes must be an integer >= 1")
    if not isinstance(config.get("keep_html", False), bool):
        raise ValueError(  # noqa: TRY004 - pydantic turns only ValueError into a validation error
            f"source {source_id}: config.keep_html must be true or false")
    rewrite = config.get("sitemap_rewrite")
    if rewrite is not None and (not isinstance(rewrite, dict) or set(rewrite) != {"from", "to"} or not all(
            isinstance(v, str) and v.startswith(("http://", "https://")) for v in rewrite.values())):
        raise ValueError(f"source {source_id}: config.sitemap_rewrite must be {{from, to}}, two absolute URL prefixes")


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
        _check_selector(source_id, key, selector)
    _check_pdf_urls(source_id, config.get("pdf_urls", []))
    _check_json_link_attributes(source_id, config.get("json_link_attributes", []))


def _check_selector(source_id: str, key: str, selector: str) -> None:
    try:
        soupsieve.compile(selector)
    except soupsieve.SelectorSyntaxError as exc:
        raise ValueError(f"source {source_id}: config.{key} is not a valid CSS selector: {selector!r}") from exc


def _check_pdf_urls(source_id: str, entries: Any) -> None:
    """`pdf_urls: [{url, title_hint?}]`: PDFs handed to the PDF connector without a linking page (#56)."""
    problem = f"source {source_id}: config.pdf_urls must be a list of {{url, title_hint?}} with an absolute url"
    if not isinstance(entries, list):
        raise ValueError(problem)  # noqa: TRY004 - pydantic turns only ValueError into a validation error
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) - {"url", "title_hint"}
                or not isinstance(entry.get("url"), str) or not entry["url"].startswith(("http://", "https://"))
                or not isinstance(entry.get("title_hint", ""), str)):
            raise ValueError(problem)


def _check_json_link_attributes(source_id: str, entries: Any) -> None:
    """`json_link_attributes: [{selector, attribute}]`: elements whose attribute holds JSON with links (#56)."""
    problem = f"source {source_id}: config.json_link_attributes must be a list of {{selector, attribute}}"
    if not isinstance(entries, list):
        raise ValueError(problem)  # noqa: TRY004 - pydantic turns only ValueError into a validation error
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {"selector", "attribute"}
                or not all(isinstance(v, str) and v.strip() for v in entry.values())):
            raise ValueError(problem)
        _check_selector(source_id, "json_link_attributes", entry["selector"])


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
    """Parse and validate a manifest. A relative `config.ca_bundle` is taken from the manifest's own
    directory, so it names the same file from any working directory."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for source in (data.get("sources") or []) if isinstance(data, dict) else []:
        config = source.get("config") if isinstance(source, dict) else None
        bundle = config.get("ca_bundle") if isinstance(config, dict) else None
        if isinstance(bundle, str) and bundle.strip() and not Path(bundle).is_absolute():
            config["ca_bundle"] = str(path.parent / bundle)
    return Manifest.model_validate(data)


def select_sources(manifest: Manifest, tier: int, source_ids: tuple[str, ...] = ()) -> tuple[SourceSpec, ...]:
    """Sources at or below `tier`, in manifest order; `source_ids` narrows further when given."""
    if source_ids:
        known = {s.id for s in manifest.sources}
        unknown = sorted(set(source_ids) - known)
        if unknown:
            raise ValueError(f"unknown source ids: {unknown}")
    chosen = [s for s in manifest.sources if s.tier <= tier and (not source_ids or s.id in source_ids)]
    return tuple(s.to_spec() for s in chosen)
