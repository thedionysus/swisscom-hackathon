"""JSON / REST records connector (`connector: json`, #55): one document per record of a JSON API.

A source names an endpoint, how to page through it, where the records sit in each response, and
templates that turn a record into a document. Its manifest `config` keys:

- `url` (required): the endpoint. It may hold `{offset}`, `{size}` or `{page}` for paging; any other
  literal brace must be doubled.
- `paging`: `{style, size, first_page, next_path}`. `style` is `none` (one request, the default),
  `offset` or `page` (stop at an empty or short page), or `next` (follow the URL at `next_path`, default
  `batching.next`, until it is missing). `size` defaults to 100, `first_page` to 1.
- `records_path` (required): dotted path to the list of records in a response; `""` when the response
  itself is the one record.
- `id_template`, `title_template` (required): `str.format_map` templates over a record, so nested fields
  work (`{parent[title]}`, `{@id}`). A missing field or a `None` value makes that record a per-record
  error; the run goes on with the other records.
- `text_template` and/or `html_path` (at least one): the body. `text_template` renders one plain-text
  section; `html_path` (dotted) points at an HTML field that is split into sections at its headings,
  like a crawled page. A record with an empty body is not a document; under `breadcrumbs` it can still
  name a level of the tree.
- `url_template`: the public page to cite for each record, optionally rewritten by `url_replace`
  (`[from_prefix, to_prefix]`). Without it: `cite_url` (else the endpoint without its query) + `#<id>`.
- `published_path`, `modified_path`: dotted paths to dates (ISO date or datetime, or dd.mm.yyyy).
- `breadcrumbs`: `{id_path, title_path}` for records that form a tree by URL path (Plone). A document's
  breadcrumb is the titles of the records whose `id_path` URL is a path prefix of its own, and the
  templates can use `{_parent}`: the nearest of those titles that differs from the record's own.
- `max_records` (default 5000) and `delay_seconds` (as for html sources).
- `robots_exception_reason`: why this documented API may be fetched although robots.txt disallows it.
  It takes effect only when the operator sets `ROBOTS_API_EXCEPTIONS=true` (default false).

robots.txt is honoured exactly as in the html connector (`RESPECT_ROBOTS`, `load_robots`), apart from the
opt-in exception above, which is logged for every request it lets through. A record
that disappears is never reported as gone: an API page can shift, and a record that leaves a date window
is not withdrawn. This connector hands over no PDFs.
"""
import logging
import re
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import date, datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from protego import Protego

from swiss_grounding.corpus.connectors.html import (
    ROBOTS_USER_AGENT,
    CrawlPolicy,
    host_delay,
    load_robots,
)
from swiss_grounding.corpus.connectors.politeness import (
    SHARED_THROTTLE,
    HostThrottle,
    request_with_backoff,
)
from swiss_grounding.corpus.models import (
    ConnectorResult,
    KnownState,
    ParsedDocument,
    ParsedSection,
    SourceSpec,
)
from swiss_grounding.ingest.html_sections import html_to_page

logger = logging.getLogger(__name__)

DEFAULT_MAX_RECORDS = 5000
DEFAULT_PAGE_SIZE = 100
_DMY = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


class RecordError(ValueError):
    """A record that cannot become a document: a field is missing or None, or a template fails."""


class _Strict(Mapping):
    """A record as `str.format_map` sees it: a missing key or a None value raises instead of
    rendering as the text "None". Nested mappings are wrapped too, so `{parent[title]}` is checked."""

    def __init__(self, data: Mapping):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        if key not in self._data:
            raise RecordError(f"missing field {key!r}")
        value = self._data[key]
        if value is None:
            raise RecordError(f"field {key!r} is empty")
        return _Strict(value) if isinstance(value, Mapping) else value

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def render(template: str, record: Mapping) -> str:
    try:
        return template.format_map(_Strict(record)).strip()
    except RecordError:
        raise
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise RecordError(f"template {template!r} failed: {exc!r}") from exc


def dig(obj: Any, path: str) -> Any:
    """The value at a dotted path (`text.data`, `items.0`), or None when any step is missing."""
    if not path:
        return obj
    for part in path.split("."):
        if isinstance(obj, Mapping) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


def parse_date(value: Any) -> date | None:
    """An ISO date or datetime, or a Swiss dd.mm.yyyy date; None for anything else."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if match := _DMY.match(text):
        try:
            return date(int(match[3]), int(match[2]), int(match[1]))
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _root(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def _is_path_prefix(parent: str, child: str) -> bool:
    parent = parent.rstrip("/")
    return child != parent and child.startswith(parent + "/")


def _cite_url(cfg: Mapping, record_id: str) -> str:
    base = cfg.get("cite_url") or cfg["url"].split("?", 1)[0]
    return f"{base}#{quote(record_id, safe='')}"


class JsonConnector:
    def __init__(self, http: httpx.Client, policy: CrawlPolicy, sleep: Callable[[float], None] = time.sleep,
                 throttle: HostThrottle | None = None, robots_api_exceptions: bool = False):
        self._http = http
        self._policy = policy
        self._robots_api_exceptions = robots_api_exceptions
        self._sleep = sleep
        self._throttle = throttle or SHARED_THROTTLE
        self._robots: dict[str, tuple[Protego, str | None]] = {}
        self._delays: dict[str, float] = {}

    def _before(self, url: str, min_delay: float = 0.0) -> None:
        delay = max(self._delays.get(_root(url), self._policy.delay_seconds), min_delay)
        self._throttle.wait(url, delay, self._sleep)

    def _refusal(self, url: str, min_delay: float, exception_reason: str | None = None) -> str | None:
        """Why robots.txt forbids `url`, or None when it may be fetched (including under an exception)."""
        if not self._policy.respect_robots:
            return None
        root = _root(url)
        if root not in self._robots:
            self._before(root + "/robots.txt", min_delay)
            parser, problem = load_robots(self._http, root)
            if problem:
                logger.warning("robots.txt for %s: %s -- disallowing the whole host", root, problem)
            self._robots[root] = (parser, problem)
            self._delays[root] = host_delay(max(self._policy.delay_seconds, min_delay),
                                            parser.crawl_delay(ROBOTS_USER_AGENT), root)
        parser, problem = self._robots[root]
        if parser.can_fetch(url, ROBOTS_USER_AGENT):
            return None
        refusal = f"robots.txt {problem}: host disallowed" if problem else "disallowed by robots.txt"
        if self._robots_api_exceptions and exception_reason:
            logger.warning("ROBOTS_API_EXCEPTIONS: fetching %s although %s; reason: %s", url, refusal, exception_reason)
            return None
        return refusal

    def _get_json(self, url: str, min_delay: float, exception_reason: str | None = None) -> tuple[Any, str | None]:
        refused = self._refusal(url, min_delay, exception_reason)
        if refused:
            return None, refused
        try:
            response = request_with_backoff(
                url, self._throttle, lambda u: self._before(u, min_delay),
                lambda: self._http.get(url, headers={"accept": "application/json"}, follow_redirects=True,
                                       timeout=30),
                self._sleep)
        except httpx.HTTPError as exc:
            return None, f"fetch failed: {exc}"
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        try:
            return response.json(), None
        except ValueError:
            return None, "response is not JSON"

    def _pages(self, cfg: Mapping, errors: list[tuple[str, str]],
               min_delay: float) -> Iterator[tuple[str, list[Mapping]]]:
        """(page URL, records) per page, until the paging style says stop or `max_records` is reached."""
        paging = cfg.get("paging") or {}
        style = paging.get("style", "none")
        size = int(paging.get("size", DEFAULT_PAGE_SIZE))
        first_page = int(paging.get("first_page", 1))
        budget = int(cfg.get("max_records", DEFAULT_MAX_RECORDS))
        url = cfg["url"].format(offset=0, size=size, page=first_page)
        index, requested = 0, set()
        while budget > 0 and url not in requested:
            requested.add(url)
            data, problem = self._get_json(url, min_delay, cfg.get("robots_exception_reason"))
            if problem:
                errors.append((url, problem))
                return
            records = dig(data, cfg.get("records_path", ""))
            if isinstance(records, Mapping):
                records = [records]
            if not isinstance(records, list):
                errors.append((url, f"no list of records at {cfg.get('records_path', '')!r}"))
                return
            records = [r for r in records if isinstance(r, Mapping)][:budget]
            budget -= len(records)
            yield url, records
            index += 1
            if style == "none" or not records or (style in ("offset", "page") and len(records) < size):
                return
            if style == "next":
                following = dig(data, paging.get("next_path", "batching.next"))
                if not isinstance(following, str) or not following:
                    return
                url = following
            else:
                url = cfg["url"].format(offset=index * size, size=size, page=first_page + index)

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        cfg = spec.config
        errors: list[tuple[str, str]] = []
        records = [(url, r) for url, page in self._pages(cfg, errors, float(cfg.get("delay_seconds", 0.0)))
                   for r in page]
        documents = _documents(spec, records, errors)
        logger.info("source %s: %d records, %d documents, %d errors", spec.id, len(records), len(documents),
                    len(errors))
        return ConnectorResult(documents=tuple(documents), errors=tuple(errors))


def _tree(cfg: Mapping, records: list[tuple[str, Mapping]]) -> dict[str, str]:
    """Tree URL -> breadcrumb title, for every record that has both (under `breadcrumbs`)."""
    crumbs = cfg.get("breadcrumbs")
    if not crumbs:
        return {}
    titles = {}
    for _, record in records:
        node, title = dig(record, crumbs.get("id_path", "@id")), dig(record, crumbs.get("title_path", "title"))
        if isinstance(node, str) and isinstance(title, str) and title.strip():
            titles[node.rstrip("/")] = title.strip()
    return titles


def _ancestors(node: str, tree: Mapping[str, str]) -> tuple[str, ...]:
    """The titles on the path down to `node`, shortest path first, with repeats collapsed."""
    path = sorted((url for url in tree if _is_path_prefix(url, node)), key=len)
    titles: list[str] = []
    for url in path:
        if not titles or titles[-1] != tree[url]:
            titles.append(tree[url])
    return tuple(titles)


def _documents(spec: SourceSpec, records: list[tuple[str, Mapping]],
               errors: list[tuple[str, str]]) -> list[ParsedDocument]:
    cfg = spec.config
    language = spec.languages[0]
    tree = _tree(cfg, records)
    crumbs_cfg = cfg.get("breadcrumbs") or {}
    documents: list[ParsedDocument] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for position, (page_url, record) in enumerate(records):
        where = f"{page_url}#record-{position}"
        try:
            own, ancestors, parent = "", (), ""
            if tree:
                node = dig(record, crumbs_cfg.get("id_path", "@id"))
                own = tree.get(node.rstrip("/"), "") if isinstance(node, str) else ""
                ancestors = _ancestors(node, tree) if isinstance(node, str) else ()
                parent = next((t for t in reversed(ancestors) if t != own), "")
            fields = {**record, "_parent": parent}
            record_id = render(cfg["id_template"], fields)
            title = render(cfg["title_template"], fields)
            url = render(cfg["url_template"], fields) if cfg.get("url_template") else _cite_url(cfg, record_id)
            replace = cfg.get("url_replace")
            if replace and url.startswith(replace[0]):
                url = replace[1] + url[len(replace[0]):]
            text = render(cfg["text_template"], fields) if cfg.get("text_template") else ""
        except RecordError as exc:
            errors.append((where, str(exc)))
            continue
        if not record_id:
            errors.append((where, "empty id"))
            continue
        if record_id in seen_ids or url in seen_urls:
            errors.append((url, f"duplicate record id {record_id!r} or URL"))
            continue
        crumbs = (*ancestors, own) if tree and own else (title,)
        if tree and ancestors and ancestors[-1] == own:
            crumbs = ancestors
        sections: list[ParsedSection] = []
        if text:
            sections.append(ParsedSection(align_key=f"{language}:0", breadcrumb=crumbs, anchor=None, text=text))
        html = dig(record, cfg["html_path"]) if cfg.get("html_path") else None
        if isinstance(html, str) and html.strip():
            for section in html_to_page(html, url=url, default_language=language).sections:
                if not section.text.strip():
                    continue
                parts = tuple(p for p in section.heading_path.split(" > ") if p)
                sections.append(ParsedSection(align_key=f"{language}:{len(sections)}", breadcrumb=(*crumbs, *parts),
                                              anchor=section.anchor, text=section.text))
        if not sections:
            continue  # no body: a level of the tree (a Plone chapter), not a document
        seen_ids.add(record_id)
        seen_urls.add(url)
        documents.append(ParsedDocument(
            source_id=spec.id, url=url, language=language, work_key=f"json:{spec.id}:{record_id}", title=title,
            sections=tuple(sections), identifier=record_id,
            published_at=parse_date(dig(record, cfg["published_path"])) if cfg.get("published_path") else None,
            modified_at=parse_date(dig(record, cfg["modified_path"])) if cfg.get("modified_path") else None,
            retrieved_via=spec.retrieved_via))
    return documents
