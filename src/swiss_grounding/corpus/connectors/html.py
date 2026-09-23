import logging
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from urllib import robotparser
from urllib.parse import urldefrag, urlparse

import httpx

from swiss_grounding.corpus.connectors.html_meta import page_meta, work_key
from swiss_grounding.corpus.models import (
    LANGUAGES,
    ConnectorResult,
    DiscoveredPdf,
    KnownState,
    ParsedDocument,
    ParsedSection,
    SourceSpec,
)
from swiss_grounding.ingest.html_sections import extract_links, html_to_page

logger = logging.getLogger(__name__)

SKIP_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv",
                 ".docx", ".doc", ".xlsx", ".xls", ".mp4", ".mp3")
DEFAULT_MAX_PAGES = 300
DEFAULT_MAX_PDFS = 50
_DENY_ALL_ROBOTS = ("User-agent: *", "Disallow: /")


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


class HtmlConnector:
    def __init__(self, http: httpx.Client, policy: CrawlPolicy, sleep: Callable[[float], None] = time.sleep):
        self._http = http
        self._policy = policy
        self._sleep = sleep
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._warned_hosts: set[str] = set()

    def _warn_once(self, root: str, message: str) -> None:
        if root not in self._warned_hosts:
            self._warned_hosts.add(root)
            logger.warning("robots.txt for %s: %s -- disallowing the whole host", root, message)

    def _robots_allow(self, url: str) -> bool:
        if not self._policy.respect_robots:
            return True
        host = urlparse(url)
        root = f"{host.scheme}://{host.netloc}"
        if root not in self._robots:
            parser = robotparser.RobotFileParser()
            try:
                response = self._http.get(root + "/robots.txt", timeout=20, follow_redirects=True)
            except httpx.HTTPError as exc:
                parser.parse(_DENY_ALL_ROBOTS)
                self._warn_once(root, f"fetch failed: {exc}")
            else:
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                elif response.status_code in (401, 403) or response.status_code >= 500:
                    parser.parse(_DENY_ALL_ROBOTS)
                    self._warn_once(root, f"HTTP {response.status_code}")
                else:
                    parser.parse([])
            self._robots[root] = parser
        return self._robots[root].can_fetch("*", url)

    @staticmethod
    def _in_prefixes(url: str, prefixes: tuple[str, ...]) -> bool:
        return any(url.startswith(p) for p in prefixes)

    def _allowed(self, url: str, prefixes: tuple[str, ...]) -> bool:
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not path.endswith(SKIP_SUFFIXES)
                and self._robots_allow(url))

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        cfg = spec.config
        prefixes = tuple(cfg["allow_prefixes"])
        pdf_prefixes = tuple(cfg.get("pdf_allow_prefixes", prefixes))
        max_pages = int(cfg.get("max_pages", DEFAULT_MAX_PAGES))
        max_pdfs = int(cfg.get("max_pdfs", DEFAULT_MAX_PDFS))
        start_urls = tuple(cfg["start_urls"])
        frontier = deque(start_urls)
        revisit = deque(u for u in known if u not in start_urls)
        queued = set(frontier) | set(revisit)
        seen: set[str] = set()
        pending: list[ParsedDocument] = []
        alternates_by_url: dict[str, dict[str, str]] = {}
        page_languages: dict[str, str] = {}
        unchanged, gone, errors = [], [], []
        pdfs: dict[str, DiscoveredPdf] = {}
        pages = 0
        while (frontier or revisit) and pages < max_pages:
            from_revisit = not frontier
            url = frontier.popleft() if frontier else revisit.popleft()
            if url in seen or not self._allowed(url, prefixes):
                continue
            seen.add(url)
            pages += 1
            headers = {}
            # A page fresh from the frontier (a start URL or a link just discovered) is always
            # fetched in full: it may be new, and a 304 would silently kill discovery of whatever
            # it links to. Only URLs pulled from the revisit queue -- already-known pages being
            # re-checked, not linked from anywhere reachable this run -- get conditional headers.
            if from_revisit:
                prior = known.get(url)
                if prior and prior.etag:
                    headers["if-none-match"] = prior.etag
                if prior and prior.last_modified:
                    headers["if-modified-since"] = prior.last_modified
            try:
                response = self._http.get(url, headers=headers, follow_redirects=True, timeout=30)
            except httpx.HTTPError as exc:
                errors.append((url, f"fetch failed: {exc}"))
                continue
            finally:
                if self._policy.delay_seconds:
                    self._sleep(self._policy.delay_seconds)
            final = str(response.url)
            if final != url:
                # A redirect's own destination scope matters more than whatever status it ends
                # on: report it as out-of-scope rather than as e.g. a 404 at the target.
                if not self._allowed(final, prefixes):
                    errors.append((final, "redirected outside scope"))
                    continue
                if final in seen:
                    continue
                seen.add(final)

            if response.status_code == 304:
                unchanged.append(url)
                continue
            if response.status_code in (404, 410):
                if url in known:
                    gone.append(url)
                else:
                    errors.append((url, f"HTTP {response.status_code}"))
                continue
            if response.status_code >= 400:
                errors.append((url, f"HTTP {response.status_code}"))
                continue

            if "html" not in response.headers.get("content-type", "text/html").lower():
                continue
            html = response.text
            default_lang = spec.languages[0]
            # Sentinel default so we can tell "no <html lang>" apart from "declared as the
            # source's default language" -- both would otherwise read as default_lang.
            page = html_to_page(html, url=final, default_language="")
            meta = page_meta(html, final)
            self_lang = next((lang for lang, href in meta.alternates.items()
                              if urldefrag(href)[0] == urldefrag(final)[0]), None)
            declared_lang = self_lang or (page.language or None)
            if declared_lang is None:
                lang = default_lang
                emit = True
            else:
                lang = declared_lang
                emit = lang in LANGUAGES and lang in spec.languages

            for link in extract_links(html, base_url=final):
                if link not in seen and link not in queued and self._in_prefixes(link, prefixes):
                    frontier.append(link)
                    queued.add(link)
            for alt_lang, href in meta.alternates.items():
                if (alt_lang in spec.languages and href not in seen and href not in queued
                        and self._in_prefixes(href, prefixes)):
                    frontier.append(href)
                    queued.add(href)

            if not emit:
                continue

            alternates_by_url[final] = dict(meta.alternates)
            page_languages[final] = lang
            for pdf_url, text in meta.pdf_links:
                if len(pdfs) < max_pdfs and pdf_url not in pdfs and self._in_prefixes(pdf_url, pdf_prefixes):
                    pdfs[pdf_url] = DiscoveredPdf(url=pdf_url, language=lang, title_hint=text or page.title,
                                                  source_id=spec.id)
            if not page.sections:
                continue
            title = page.title or final
            sections = []
            for i, s in enumerate(page.sections):
                parts = [p for p in s.heading_path.split(" > ") if p]
                crumbs = tuple(parts) if parts and parts[0] == title else (title, *parts)
                sections.append(ParsedSection(align_key=f"{lang}:{i}", breadcrumb=crumbs, anchor=s.anchor, text=s.text))
            pending.append(ParsedDocument(
                source_id=spec.id, url=final, language=lang, work_key="", title=title,
                sections=tuple(sections), published_at=meta.published, modified_at=meta.modified,
                retrieved_via=spec.retrieved_via, etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified")))
        keys = _language_groups(alternates_by_url, page_languages)
        documents = tuple(
            replace(doc, work_key=keys.get(doc.url, work_key(doc.url, {})))
            for doc in pending
        )
        return ConnectorResult(documents=documents, unchanged_urls=tuple(unchanged), gone_urls=tuple(gone),
                               errors=tuple(errors), pdfs=tuple(pdfs.values()))
