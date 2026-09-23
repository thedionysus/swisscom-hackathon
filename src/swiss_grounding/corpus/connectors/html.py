import logging
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from urllib import robotparser
from urllib.parse import urldefrag, urlparse

import httpx

from swiss_grounding.corpus.connectors.crawl_queue import CrawlQueue
from swiss_grounding.corpus.connectors.html_meta import work_key
from swiss_grounding.corpus.connectors.html_page import CrawledPage, parse_crawled_page
from swiss_grounding.corpus.connectors.politeness import SHARED_THROTTLE, HostThrottle
from swiss_grounding.corpus.connectors.sitemap import collect_sitemap_urls
from swiss_grounding.corpus.models import (
    ConnectorResult,
    DiscoveredPdf,
    KnownState,
    ParsedDocument,
    SourceSpec,
)

logger = logging.getLogger(__name__)

SKIP_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv",
                 ".docx", ".doc", ".xlsx", ".xls", ".mp4", ".mp3")
DEFAULT_MAX_PAGES = 300
DEFAULT_MAX_PDFS = 50
_DENY_ALL_ROBOTS = ("User-agent: *", "Disallow: /")


def _robots_root(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def load_robots(http: httpx.Client, root: str) -> tuple[robotparser.RobotFileParser, str | None]:
    """The parsed robots.txt of a host, and why the whole host is disallowed when it could not be read.

    A fetch failure, 401/403 or 5xx disallows the host; any other non-200 (e.g. 404) allows everything.
    """
    parser = robotparser.RobotFileParser()
    try:
        response = http.get(root + "/robots.txt", timeout=20, follow_redirects=True)
    except httpx.HTTPError as exc:
        parser.parse(_DENY_ALL_ROBOTS)
        return parser, f"fetch failed: {exc}"
    if response.status_code == 200:
        parser.parse(response.text.splitlines())
        return parser, None
    if response.status_code in (401, 403) or response.status_code >= 500:
        parser.parse(_DENY_ALL_ROBOTS)
        return parser, f"HTTP {response.status_code}"
    parser.parse([])
    return parser, None


def robots_verdict(http: httpx.Client, url: str, respect: bool) -> str:
    """'allowed', 'disallowed', or 'disallowed-ignored' (disallowed, but RESPECT_ROBOTS is off),
    with the crawler's own rules."""
    parser, _problem = load_robots(http, _robots_root(url))
    if parser.can_fetch("*", url):
        return "allowed"
    return "disallowed" if respect else "disallowed-ignored"


@dataclass(frozen=True)
class CrawlPolicy:
    respect_robots: bool
    delay_seconds: float


def _language_groups(alternates_by_url: Mapping[str, Mapping[str, str]],
                     languages: Mapping[str, str]) -> dict[str, str]:
    """Final work_key per crawled URL, grouping only pages that list each other symmetrically.

    Two crawled pages P and Q are joined when P's alternates contain Q and Q's alternates contain
    P (both hreflang-defragged). Groups are the connected components of that symmetric relation.
    A component holding two pages of the same language falls back to a per-page key for every
    page in it -- it is not a real translation group, just a shared "no translation" pointer
    (e.g. every untranslated German page listing the same French homepage as its `fr` alternate).
    A page whose alternates were not crawled in this run (no symmetric partner found) also keeps
    its own key.
    """
    parent: dict[str, str] = {url: url for url in alternates_by_url}

    def find(u: str) -> str:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for url, alts in alternates_by_url.items():
        for target in alts.values():
            target = urldefrag(target)[0]
            back = alternates_by_url.get(target)
            if back is not None and urldefrag(url)[0] in {urldefrag(v)[0] for v in back.values()}:
                union(url, target)

    members_by_root: dict[str, list[str]] = {}
    for url in alternates_by_url:
        members_by_root.setdefault(find(url), []).append(url)

    result: dict[str, str] = {}
    for members in members_by_root.values():
        member_languages = [languages.get(u) for u in members]
        if len(members) < 2 or len(set(member_languages)) != len(member_languages):
            for u in members:
                result[u] = "html:" + urldefrag(u)[0]
        else:
            key = "html:" + min(urldefrag(u)[0] for u in members)
            for u in members:
                result[u] = key
    return result


def _matches(url: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """True when `url` is one of config.pdf_link_patterns: a PDF to hand over, never a page to crawl."""
    return any(p.search(url) for p in patterns)


class HtmlConnector:
    def __init__(self, http: httpx.Client, policy: CrawlPolicy, sleep: Callable[[float], None] = time.sleep,
                 throttle: HostThrottle | None = None):
        self._http = http
        self._policy = policy
        self._sleep = sleep
        self._throttle = throttle or SHARED_THROTTLE
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._warned_hosts: set[str] = set()

    def _warn_once(self, root: str, message: str) -> None:
        if root not in self._warned_hosts:
            self._warned_hosts.add(root)
            logger.warning("robots.txt for %s: %s -- disallowing the whole host", root, message)

    def _before(self, url: str) -> None:
        """Per-host politeness, shared with every other connector and thread (see politeness)."""
        self._throttle.wait(url, self._policy.delay_seconds, self._sleep)

    def _robots_allow(self, url: str) -> bool:
        if not self._policy.respect_robots:
            return True
        root = _robots_root(url)
        if root not in self._robots:
            self._before(root + "/robots.txt")
            parser, problem = load_robots(self._http, root)
            if problem:
                self._warn_once(root, problem)
            self._robots[root] = parser
        return self._robots[root].can_fetch("*", url)

    @staticmethod
    def _in_prefixes(url: str, prefixes: tuple[str, ...]) -> bool:
        return any(url.startswith(p) for p in prefixes)

    def _crawlable(self, url: str, prefixes: tuple[str, ...], pdf_patterns: tuple[re.Pattern[str], ...]) -> bool:
        """In scope as a page (robots aside): inside the prefixes, not a file, not a PDF pattern."""
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not path.endswith(SKIP_SUFFIXES)
                and not _matches(url, pdf_patterns))

    def _allowed(self, url: str, prefixes: tuple[str, ...]) -> bool:
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not path.endswith(SKIP_SUFFIXES)
                and self._robots_allow(url))

    def _seed_from_sitemaps(self, cfg: Mapping, queue: CrawlQueue, limit: int, prefixes: tuple[str, ...],
                            pdf_patterns: tuple[re.Pattern[str], ...]) -> list[tuple[str, str]]:
        """Queue URLs from config.sitemap_urls matching config.sitemap_include (A11), at most
        `limit`. Known or already-queued URLs do not use up the budget: it is for new pages."""
        if not cfg.get("sitemap_urls"):
            return []

        def accept(url: str) -> bool:
            return not queue.is_known_or_queued(url) and self._crawlable(url, prefixes, pdf_patterns)

        seeds = collect_sitemap_urls(self._http, tuple(cfg["sitemap_urls"]), tuple(cfg.get("sitemap_include", ())),
                                     limit, accept=accept, fetchable=self._robots_allow, before=self._before)
        for url in seeds.urls:
            queue.add(url)
        return list(seeds.errors)

    def _get(self, url: str, conditional: bool, known: Mapping[str, KnownState]) -> httpx.Response:
        headers = {}
        # Only revisit-queue pages (known, and linked from nowhere reachable this run) are sent
        # conditionally: a 304 on any other page would hide the links it carries.
        prior = known.get(url) if conditional else None
        if prior and prior.etag:
            headers["if-none-match"] = prior.etag
        if prior and prior.last_modified:
            headers["if-modified-since"] = prior.last_modified
        self._before(url)
        return self._http.get(url, headers=headers, follow_redirects=True, timeout=30)

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        cfg = spec.config
        prefixes = tuple(cfg["allow_prefixes"])
        max_pages = int(cfg.get("max_pages", DEFAULT_MAX_PAGES))
        pdf_patterns = tuple(re.compile(p) for p in cfg.get("pdf_link_patterns", ()))
        queue = CrawlQueue(cfg["start_urls"], known)
        errors = self._seed_from_sitemaps(cfg, queue, max_pages, prefixes, pdf_patterns)
        crawl = _CrawlResults(spec, int(cfg.get("max_pdfs", DEFAULT_MAX_PDFS)),
                              tuple(cfg.get("pdf_allow_prefixes", prefixes)))
        crawl.errors.extend(errors)
        pages = 0
        while pages < max_pages and (item := queue.pop()) is not None:
            url, conditional = item
            if url in queue.seen or not self._allowed(url, prefixes):
                continue
            queue.seen.add(url)
            pages += 1
            try:
                response = self._get(url, conditional, known)
            except httpx.HTTPError as exc:
                crawl.errors.append((url, f"fetch failed: {exc}"))
                continue
            final = self._settle(url, str(response.url), response.status_code, queue, known, prefixes, crawl)
            if final is None or "html" not in response.headers.get("content-type", "text/html").lower():
                continue
            try:
                page = parse_crawled_page(response.text, final, spec, pdf_patterns)
            except Exception as exc:  # noqa: BLE001 - one malformed page fails that URL, never the source
                logger.warning("parse failed for %s: %r", final, exc)
                crawl.errors.append((final, f"parse failed: {exc!r}"))
                continue
            for alt_lang, href in page.alternates.items():
                # Language versions jump the queue, ahead of the page's own links (which often
                # include the language switcher): A1 groups only pages crawled in the same run.
                if alt_lang in spec.languages and self._crawlable(href, prefixes, pdf_patterns):
                    queue.add(href, front=True)
            for link in page.links:
                if self._crawlable(link, prefixes, pdf_patterns):
                    queue.add(link)
            crawl.record(final, page, response)
        return crawl.result()

    def _settle(self, url: str, final: str, status: int, queue: CrawlQueue, known: Mapping[str, KnownState],
                prefixes: tuple[str, ...], crawl: "_CrawlResults") -> str | None:
        """The URL to parse the response as, or None after recording why it is not parsed."""
        if final != url:
            if url in known:
                crawl.gone[url] = None  # a known URL that now redirects is retired either way
            # A redirect's destination scope matters more than whatever status it ends on.
            if not self._allowed(final, prefixes):
                crawl.errors.append((final, "redirected outside scope"))
                return None
            if final in queue.seen:
                return None
            queue.seen.add(final)
        if status == 304:
            crawl.unchanged.append(url)
            return None
        if status in (404, 410) and url in known:
            crawl.gone[url] = None
            return None
        if status >= 400:
            if url not in crawl.gone:
                crawl.errors.append((url, f"HTTP {status}"))
            return None
        return final


class _CrawlResults:
    """What one run collects: emitted documents, their alternates for A1 grouping, PDFs, errors."""

    def __init__(self, spec: SourceSpec, max_pdfs: int, pdf_prefixes: tuple[str, ...]):
        self._spec = spec
        self._max_pdfs = max_pdfs
        self._pdf_prefixes = pdf_prefixes
        self.pending: list[ParsedDocument] = []
        self.alternates_by_url: dict[str, dict[str, str]] = {}
        self.page_languages: dict[str, str] = {}
        self.pdfs: dict[str, DiscoveredPdf] = {}
        self.unchanged: list[str] = []
        self.gone: dict[str, None] = {}
        self.errors: list[tuple[str, str]] = []

    def record(self, final: str, page: CrawledPage, response: httpx.Response) -> None:
        if not page.emit:
            return
        self.alternates_by_url[final] = dict(page.alternates)
        self.page_languages[final] = page.language
        for pdf_url, text in page.pdf_links:
            if (len(self.pdfs) < self._max_pdfs and pdf_url not in self.pdfs
                    and any(pdf_url.startswith(p) for p in self._pdf_prefixes)):
                self.pdfs[pdf_url] = DiscoveredPdf(url=pdf_url, language=page.language,
                                                   title_hint=text or page.title_hint, source_id=self._spec.id)
        if page.sections:
            self.pending.append(ParsedDocument(
                source_id=self._spec.id, url=final, language=page.language, work_key="", title=page.title,
                sections=page.sections, published_at=page.published, modified_at=page.modified,
                retrieved_via=self._spec.retrieved_via, etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified")))

    def result(self) -> ConnectorResult:
        keys = _language_groups(self.alternates_by_url, self.page_languages)
        documents = tuple(replace(doc, work_key=keys.get(doc.url, work_key(doc.url, {}))) for doc in self.pending)
        return ConnectorResult(documents=documents, unchanged_urls=tuple(self.unchanged),
                               gone_urls=tuple(self.gone), errors=tuple(self.errors), pdfs=tuple(self.pdfs.values()))
