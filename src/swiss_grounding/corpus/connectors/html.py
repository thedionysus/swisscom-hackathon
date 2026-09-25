import logging
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urldefrag, urlparse

import httpx
from protego import Protego

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.connectors.crawl_queue import CrawlQueue
from swiss_grounding.corpus.connectors.html_meta import work_key
from swiss_grounding.corpus.connectors.html_page import CrawledPage, parse_crawled_page
from swiss_grounding.corpus.connectors.politeness import (
    SHARED_THROTTLE,
    HostThrottle,
    request_with_backoff,
)
from swiss_grounding.corpus.connectors.sitemap import collect_sitemap_urls
from swiss_grounding.corpus.models import (
    ConnectorResult,
    DiscoveredPdf,
    KnownState,
    ParsedDocument,
    SourceSpec,
    content_hash,
)

logger = logging.getLogger(__name__)

SKIP_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv",
                 ".docx", ".doc", ".xlsx", ".xls", ".mp4", ".mp3")
# The skipped files that could hold content (#11): an in-scope link to one is reported as skipped, so a
# source whose rules sit in a .docx does not look fully covered. Images and media are never counted.
ATTACHMENT_SUFFIXES = (".zip", ".xml", ".json", ".ics", ".csv", ".docx", ".doc", ".xlsx", ".xls")
DEFAULT_MAX_PAGES = 300
DEFAULT_MAX_PDFS = 50
_DENY_ALL_ROBOTS = "User-agent: *\nDisallow: /\n"
# RFC 9309 leaves an unbounded Crawl-delay unpoliced; we cap it so one host cannot stall a whole
# run. A host that genuinely needs longer belongs on a lower max_pages/schedule, not a longer wait.
MAX_CRAWL_DELAY_SECONDS = 30.0
# The product token of `corpus_user_agent` (config.py). RFC 9309: a crawler obeys the group naming it
# and falls back to `*` only when no group does. The full browser-style UA string would also match a
# `User-agent: Mozilla` group, so the token is passed, not the header value.
ROBOTS_USER_AGENT = "swiss-grounding"


def _robots_root(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def load_robots(http: httpx.Client, root: str) -> tuple[Protego, str | None]:
    """The parsed robots.txt of a host, and why the whole host is disallowed when it could not be read.

    RFC 9309 section 2.3.1: any 4xx -- 401 and 403 included -- means robots.txt is unavailable, and
    everything is allowed (2.3.1.3); a fetch failure or a 5xx means it is unreachable, and the whole
    host is disallowed (2.3.1.4). bl-api.webcloud7.ch answers its robots.txt with a login redirect
    that ends in 403, so under the RFC it may be crawled (#57).

    Parsed with protego (RFC 9309: longest matching rule wins, not the first one --
    urllib.robotparser gets this wrong, which wrongly refused be.ch's own PDFs under a narrower
    Allow nested inside a broader Disallow).
    """
    try:
        response = http.get(root + "/robots.txt", timeout=20, follow_redirects=True)
    except httpx.HTTPError as exc:
        return Protego.parse(_DENY_ALL_ROBOTS), f"fetch failed: {exc}"
    if response.status_code == 200:
        return Protego.parse(response.text), None
    if response.status_code >= 500:
        return Protego.parse(_DENY_ALL_ROBOTS), f"HTTP {response.status_code}"
    return Protego.parse(""), None


def robots_verdict(http: httpx.Client, url: str, respect: bool) -> str:
    """'allowed', 'disallowed', or 'disallowed-ignored' (disallowed, but RESPECT_ROBOTS is off),
    with the crawler's own rules."""
    parser, _problem = load_robots(http, _robots_root(url))
    if parser.can_fetch(url, ROBOTS_USER_AGENT):
        return "allowed"
    return "disallowed" if respect else "disallowed-ignored"


def host_delay(base_delay: float, crawl_delay: float | None, root: str = "") -> float:
    """The per-host delay HostThrottle should enforce: at least the robots.txt Crawl-delay (for
    our user agent, falling back to `*`), never less than the policy's own base delay, capped at
    MAX_CRAWL_DELAY_SECONDS (logged when the cap bites)."""
    if crawl_delay is None:
        return base_delay
    wanted = max(base_delay, crawl_delay)
    if wanted > MAX_CRAWL_DELAY_SECONDS:
        logger.warning("robots.txt for %s asks for a %.1fs crawl-delay; capping at %.1fs",
                       root or "host", wanted, MAX_CRAWL_DELAY_SECONDS)
        return MAX_CRAWL_DELAY_SECONDS
    return wanted


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


def _attachment_suffix(url: str) -> str | None:
    path = urlparse(url).path.lower()
    return next((s for s in ATTACHMENT_SUFFIXES if path.endswith(s)), None)


class HtmlConnector:
    """`data_dir` is where a source with `config.keep_html` keeps each page's raw HTML (#12); without
    it, no page is kept."""

    def __init__(self, http: httpx.Client, policy: CrawlPolicy, sleep: Callable[[float], None] = time.sleep,
                 throttle: HostThrottle | None = None, data_dir: Path | str | None = None):
        self._http = http
        self._policy = policy
        self._sleep = sleep
        self._throttle = throttle or SHARED_THROTTLE
        self._data_dir = data_dir
        self._robots: dict[str, Protego] = {}
        self._delays: dict[str, float] = {}
        self._warned_hosts: set[str] = set()

    def _warn_once(self, root: str, message: str) -> None:
        if root not in self._warned_hosts:
            self._warned_hosts.add(root)
            logger.warning("robots.txt for %s: %s -- disallowing the whole host", root, message)

    def _before(self, url: str, min_delay: float = 0.0) -> None:
        """Per-host politeness, shared with every other connector and thread (see politeness).

        `min_delay` is the source's own `config.delay_seconds`, if any.
        """
        delay = max(self._delays.get(_robots_root(url), self._policy.delay_seconds), min_delay)
        self._throttle.wait(url, delay, self._sleep)

    def _robots_allow(self, url: str, min_delay: float = 0.0) -> bool:
        if not self._policy.respect_robots:
            return True
        root = _robots_root(url)
        if root not in self._robots:
            self._before(root + "/robots.txt", min_delay)
            parser, problem = load_robots(self._http, root)
            if problem:
                self._warn_once(root, problem)
            self._robots[root] = parser
            self._delays[root] = host_delay(max(self._policy.delay_seconds, min_delay),
                                            parser.crawl_delay(ROBOTS_USER_AGENT), root)
            if parser.crawl_delay(ROBOTS_USER_AGENT) is not None:
                # The PDF connector shares the throttle but not this cache: pass the promise on.
                self._throttle.require(root, self._delays[root])
        return self._robots[root].can_fetch(url, ROBOTS_USER_AGENT)

    @staticmethod
    def _in_prefixes(url: str, prefixes: tuple[str, ...]) -> bool:
        return any(url.startswith(p) for p in prefixes)

    def _crawlable(self, url: str, prefixes: tuple[str, ...], pdf_patterns: tuple[re.Pattern[str], ...],
                   deny: tuple[re.Pattern[str], ...] = ()) -> bool:
        """In scope as a page (robots aside): inside the prefixes, not denied, not a file, not a PDF pattern."""
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not _matches(url, deny) and not path.endswith(SKIP_SUFFIXES)
                and not _matches(url, pdf_patterns))

    def _allowed(self, url: str, prefixes: tuple[str, ...], min_delay: float = 0.0,
                 deny: tuple[re.Pattern[str], ...] = ()) -> bool:
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not _matches(url, deny) and not path.endswith(SKIP_SUFFIXES)
                and self._robots_allow(url, min_delay))

    def _seed_from_sitemaps(self, cfg: Mapping, queue: CrawlQueue, limit: int, prefixes: tuple[str, ...],
                            pdf_patterns: tuple[re.Pattern[str], ...], min_delay: float = 0.0,
                            deny: tuple[re.Pattern[str], ...] = ()) -> list[tuple[str, str]]:
        """Queue URLs from config.sitemap_urls matching config.sitemap_include, at most
        `limit`. Known or already-queued URLs do not use up the budget: it is for new pages."""
        if not cfg.get("sitemap_urls"):
            return []

        def accept(url: str) -> bool:
            return not queue.is_known_or_queued(url) and self._crawlable(url, prefixes, pdf_patterns, deny)

        rewrite = cfg.get("sitemap_rewrite")
        seeds = collect_sitemap_urls(self._http, tuple(cfg["sitemap_urls"]), tuple(cfg.get("sitemap_include", ())),
                                     limit, accept=accept, fetchable=lambda u: self._robots_allow(u, min_delay),
                                     before=lambda u: self._before(u, min_delay), throttle=self._throttle,
                                     sleep=self._sleep, rewrite=(rewrite["from"], rewrite["to"]) if rewrite else None)
        for url in seeds.urls:
            queue.add(url)
        return list(seeds.errors)

    def _get(self, url: str, conditional: bool, known: Mapping[str, KnownState],
             min_delay: float = 0.0) -> httpx.Response:
        headers = {}
        # Only revisit-queue pages (known, and linked from nowhere reachable this run) are sent
        # conditionally: a 304 on any other page would hide the links it carries.
        prior = known.get(url) if conditional else None
        if prior and prior.etag:
            headers["if-none-match"] = prior.etag
        if prior and prior.last_modified:
            headers["if-modified-since"] = prior.last_modified
        return request_with_backoff(
            url, self._throttle, lambda u: self._before(u, min_delay),
            lambda: self._http.get(url, headers=headers, follow_redirects=True, timeout=30), self._sleep)

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        cfg = spec.config
        prefixes = tuple(cfg["allow_prefixes"])
        max_pages = int(cfg.get("max_pages", DEFAULT_MAX_PAGES))
        pdf_patterns = tuple(re.compile(p) for p in cfg.get("pdf_link_patterns", ()))
        # Pages inside the prefixes that must never be fetched, e.g. a gazette's personal-data rubrics.
        deny = tuple(re.compile(p) for p in cfg.get("deny_patterns", ()))
        min_delay = float(cfg.get("delay_seconds", 0.0))
        queue = CrawlQueue(cfg.get("start_urls", ()), known)
        errors = self._seed_from_sitemaps(cfg, queue, max_pages, prefixes, pdf_patterns, min_delay, deny)
        pdf_prefixes = tuple(cfg.get("pdf_allow_prefixes", prefixes))
        crawl = _CrawlResults(spec, int(cfg.get("max_pdfs", DEFAULT_MAX_PDFS)), pdf_prefixes,
                              pdf_allowed=lambda u: self._robots_allow(u, min_delay),
                              html_dir=self._data_dir if cfg.get("keep_html") else None)
        crawl.errors.extend(errors)
        for entry in cfg.get("pdf_urls", ()):
            # PDFs no crawlable page links to (#56). Listed first, so they are the last to lose out to max_pdfs.
            crawl.add_pdf(entry["url"], entry.get("title_hint", ""), spec.languages[0], listed=True)
        pages = 0
        while pages < max_pages and (item := queue.pop()) is not None:
            url, conditional = item
            # A known PDF sits in the revisit queue too; one matched by pdf_link_patterns has no .pdf
            # suffix to stop it, and it is the PDF connector's to re-check, not a page.
            if url in queue.seen or _matches(url, pdf_patterns) or not self._allowed(url, prefixes, min_delay, deny):
                continue
            queue.seen.add(url)
            pages += 1
            try:
                response = self._get(url, conditional, known, min_delay)
            except httpx.HTTPError as exc:
                crawl.errors.append((url, f"fetch failed: {exc}"))
                continue
            final = self._settle(url, str(response.url), response.status_code, queue, known, prefixes, crawl, deny)
            if final is None:
                continue
            media_type = response.headers.get("content-type", "text/html").split(";")[0].strip().lower()
            if "html" not in media_type:
                crawl.skip(final, f"type {media_type or 'missing'}")  # a link whose suffix did not say so
                continue
            try:
                page = parse_crawled_page(response.text, final, spec, pdf_patterns)
            except Exception as exc:  # noqa: BLE001 - one malformed page fails that URL, never the source
                logger.warning("parse failed for %s: %r", final, exc)
                crawl.errors.append((final, f"parse failed: {exc!r}"))
                continue
            if page.soft_404:
                # Handled like an HTTP error: reported, not stored, its links not followed. A known page
                # is not withdrawn on the strength of a title match; it stays until a real 404/410.
                crawl.errors.append((final, f"soft 404: title {page.soft_404!r}"))
                continue
            for alt_lang, href in page.alternates.items():
                # Language versions jump the queue, ahead of the page's own links (which often
                # include the language switcher): only pages crawled in the same run are grouped.
                if alt_lang in spec.languages and self._crawlable(href, prefixes, pdf_patterns, deny):
                    queue.add(href, front=True)
            if page.canonical and page.canonical != final and self._crawlable(page.canonical, prefixes,
                                                                              pdf_patterns, deny):
                queue.add(page.canonical, front=True)  # so an alias can be told apart from its canonical
            for link in page.links:
                if self._crawlable(link, prefixes, pdf_patterns, deny):
                    queue.add(link)
                elif ((suffix := _attachment_suffix(link)) and self._in_prefixes(link, prefixes + pdf_prefixes)
                      and not _matches(link, deny)):
                    crawl.skip(link, suffix)
            crawl.record(final, page, response)
        return crawl.result()

    def _settle(self, url: str, final: str, status: int, queue: CrawlQueue, known: Mapping[str, KnownState],
                prefixes: tuple[str, ...], crawl: "_CrawlResults",
                deny: tuple[re.Pattern[str], ...] = ()) -> str | None:
        """The URL to parse the response as, or None after recording why it is not parsed."""
        if final != url:
            if url in known:
                crawl.gone[url] = None  # a known URL that now redirects is retired either way
            # A redirect's destination scope matters more than whatever status it ends on.
            if not self._allowed(final, prefixes, deny=deny):
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
    """What one run collects: emitted documents, their alternates for grouping, PDFs, errors, and
    what was found but deliberately not fetched (skipped)."""

    def __init__(self, spec: SourceSpec, max_pdfs: int, pdf_prefixes: tuple[str, ...],
                 pdf_allowed: Callable[[str], bool] = lambda url: True, html_dir: Path | str | None = None):
        self._spec = spec
        self._max_pdfs = max_pdfs
        self._pdf_prefixes = pdf_prefixes
        self._pdf_allowed = pdf_allowed
        self._html_dir = html_dir
        self._pdfs_refused: set[str] = set()
        self.pending: list[ParsedDocument] = []
        self.alternates_by_url: dict[str, dict[str, str]] = {}
        self.page_languages: dict[str, str] = {}
        self.pdfs: dict[str, DiscoveredPdf] = {}
        self.unchanged: list[str] = []
        self.gone: dict[str, None] = {}
        self.errors: list[tuple[str, str]] = []
        self.skipped: dict[str, str] = {}
        self.canonicals: dict[str, str | None] = {}

    def skip(self, url: str, reason: str) -> None:
        self.skipped.setdefault(url, reason)

    def add_pdf(self, pdf_url: str, title_hint: str, language: str, listed: bool = False) -> None:
        """Hand a PDF to the PDF connector once: inside pdf_allow_prefixes, allowed by robots.txt, and
        within max_pdfs. One outside the prefixes is reported only when the manifest listed it
        (config.pdf_urls); a link found on a page is simply out of scope."""
        if pdf_url in self.pdfs or pdf_url in self._pdfs_refused:
            return
        if not any(pdf_url.startswith(p) for p in self._pdf_prefixes):
            if listed:
                self._pdfs_refused.add(pdf_url)
                self.errors.append((pdf_url, "PDF outside pdf_allow_prefixes"))
            return
        if len(self.pdfs) >= self._max_pdfs:
            self.skip(pdf_url, "max_pdfs")
            return
        # Refused before it is counted, so a PDF we may not fetch never takes the place of one we may.
        if not self._pdf_allowed(pdf_url):
            self._pdfs_refused.add(pdf_url)
            self.errors.append((pdf_url, "PDF disallowed by robots.txt"))
            return
        self.pdfs[pdf_url] = DiscoveredPdf(url=pdf_url, language=language, title_hint=title_hint,
                                           source_id=self._spec.id)

    def record(self, final: str, page: CrawledPage, response: httpx.Response) -> None:
        if not page.emit:
            return
        self.alternates_by_url[final] = dict(page.alternates)
        self.page_languages[final] = page.language
        self.canonicals[final] = page.canonical
        for pdf_url, text in page.pdf_links:
            self.add_pdf(pdf_url, text or page.title_hint, page.language)
        if page.sections:
            doc = ParsedDocument(
                source_id=self._spec.id, url=final, language=page.language, work_key="", title=page.title,
                sections=page.sections, published_at=page.published, modified_at=page.modified,
                retrieved_via=self._spec.retrieved_via, etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"))
            if self._html_dir is not None:
                # Named by the text's hash, not the markup's: a page whose markup changes on every fetch
                # (a token, a timestamp) keeps one file per version of its text.
                doc = replace(doc, artifact_path=save_artifact(self._html_dir, self._spec.id, final,
                                                               response.content, ".html", version=content_hash(doc)))
            self.pending.append(doc)

    def _drop_canonical_aliases(self) -> None:
        """Drop a page that names another page as canonical when that page was stored in this run
        with the same text, and names itself (or nothing) as canonical (#27). The canonical link
        alone is not enough: sites point language versions, or page 2 of a list, at one canonical
        URL, and those hold other text. Both stay documents then, as before."""
        by_url = {doc.url: doc for doc in self.pending}
        aliases = set()
        for doc in self.pending:
            canonical = self.canonicals.get(doc.url)
            target = by_url.get(canonical) if canonical and canonical != doc.url else None
            if (target is not None and self.canonicals.get(target.url) in (None, target.url)
                    and target.language == doc.language and content_hash(target) == content_hash(doc)):
                aliases.add(doc.url)
                self.skip(doc.url, "duplicate of canonical")
        self.pending = [doc for doc in self.pending if doc.url not in aliases]
        for url in aliases:  # an alias left in would join its canonical's translation group as a
            self.alternates_by_url.pop(url, None)  # second page of the same language, and break it
            self.page_languages.pop(url, None)

    def result(self) -> ConnectorResult:
        self._drop_canonical_aliases()
        keys = _language_groups(self.alternates_by_url, self.page_languages)
        documents = tuple(replace(doc, work_key=keys.get(doc.url, work_key(doc.url, {}))) for doc in self.pending)
        return ConnectorResult(documents=documents, unchanged_urls=tuple(self.unchanged),
                               gone_urls=tuple(self.gone), errors=tuple(self.errors), pdfs=tuple(self.pdfs.values()),
                               skipped=tuple(self.skipped.items()))
