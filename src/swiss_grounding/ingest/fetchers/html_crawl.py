import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx

from swiss_grounding.ingest.html_sections import extract_links, html_to_page
from swiss_grounding.ingest.models import FetchedDocument, FetchError, FetchResult, KnownUrl
from swiss_grounding.registry.models import Source

SKIP_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv")
NON_HTML_TYPES = ("application/pdf", "application/json", "application/octet-stream", "application/zip",
                   "image/", "audio/", "video/")


@dataclass(frozen=True)
class CrawlLimits:
    max_pages: int = 200
    delay_seconds: float = 0.5


@dataclass(frozen=True)
class _Fetched:
    doc: FetchedDocument | None
    links: tuple[str, ...]
    status: int


class HtmlCrawlFetcher:
    """Bounded same-domain crawl with path allowlist, robots.txt, and conditional requests."""

    def __init__(self, http: httpx.Client, limits: CrawlLimits):
        self._http = http
        self._limits = limits

    def fetch(self, source: Source, known: Mapping[str, KnownUrl]) -> FetchResult:
        base = urlparse(source.base_url)
        allow = tuple(source.fetch_config.get("path_allowlist", ["/"]))
        starts = tuple(source.fetch_config.get("start_paths", allow))
        robots = self._robots(source.base_url)
        queue = deque(urljoin(source.base_url, p) for p in starts)
        queue.extend(u for u in known if u not in queue)
        seen: set[str] = set()
        documents: list[FetchedDocument] = []
        unchanged: list[str] = []
        gone: list[str] = []
        errors: list[FetchError] = []
        pages = 0
        while queue and pages < self._limits.max_pages:
            url = queue.popleft()
            if url in seen or not self._allowed(url, base, allow, robots):
                continue
            seen.add(url)
            pages += 1
            try:
                fetched = self._get(url, source, known.get(url))
            except httpx.HTTPError as exc:
                errors.append(FetchError(url=url, reason=str(exc)))
                continue
            if fetched.status == 304:
                unchanged.append(url)
            elif fetched.status in (404, 410):
                if url in known:
                    gone.append(url)
            elif fetched.doc is not None:
                documents.append(fetched.doc)
            queue.extend(link for link in fetched.links if link not in seen)
            if self._limits.delay_seconds:
                time.sleep(self._limits.delay_seconds)
        return FetchResult(documents=tuple(documents), unchanged_urls=tuple(unchanged),
                            gone_urls=tuple(gone), errors=tuple(errors))

    def _robots(self, base_url: str) -> robotparser.RobotFileParser:
        parser = robotparser.RobotFileParser()
        try:
            response = self._http.get(urljoin(base_url, "/robots.txt"))
            parser.parse(response.text.splitlines() if response.status_code == 200 else [])
        except httpx.HTTPError:
            parser.parse([])
        return parser

    def _allowed(self, url: str, base, allow: tuple[str, ...], robots) -> bool:
        parsed = urlparse(url)
        if parsed.netloc != base.netloc or parsed.scheme not in ("http", "https"):
            return False
        if parsed.path.lower().endswith(SKIP_SUFFIXES):
            return False
        if not any(parsed.path.startswith(prefix) for prefix in allow):
            return False
        return robots.can_fetch("*", url)

    def _get(self, url: str, source: Source, prior: KnownUrl | None) -> _Fetched:
        headers = {}
        if prior and prior.etag:
            headers["if-none-match"] = prior.etag
        if prior and prior.last_modified:
            headers["if-modified-since"] = prior.last_modified
        response = self._http.get(url, headers=headers, follow_redirects=True)
        if response.status_code == 304:
            return _Fetched(doc=None, links=(), status=304)
        if response.status_code >= 400:
            return _Fetched(doc=None, links=(), status=response.status_code)
        content_type = response.headers.get("content-type", "").lower()
        if content_type.startswith(NON_HTML_TYPES):
            return _Fetched(doc=None, links=(), status=response.status_code)
        page = html_to_page(response.text, url=url, default_language=source.fetch_config.get("language", "de"))
        links = extract_links(response.text, base_url=url)
        if not page.sections:
            return _Fetched(doc=None, links=links, status=response.status_code)
        doc = FetchedDocument(
            source_id=source.id, url=url, title=page.title or url, language=page.language,
            sections=page.sections, etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
        return _Fetched(doc=doc, links=links, status=response.status_code)
