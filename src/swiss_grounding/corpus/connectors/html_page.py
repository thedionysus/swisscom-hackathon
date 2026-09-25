"""One fetched HTML page turned into a document draft, its language, alternates and links."""
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from urllib.parse import urldefrag

from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.models import LANGUAGES, ParsedSection, SourceSpec
from swiss_grounding.ingest.html_sections import extract_links, html_to_page

# CMS include-markers seen leaking into live page text: TYPO3's TYPO3SEARCH_begin/end (normally
# an HTML comment, but see html_sections._is_hidden/Comment handling -- some templates emit it as
# plain text), generic Start_Module/End_Module block markers, and bare bracket runs ("[[[", "]]]")
# left over from a template's own delimiters. A line consisting of nothing else is dropped.
_MARKER_LINE = re.compile(
    r"^\s*(?:\\?\[+|\\?\]+|TYPO3SEARCH\\?_(?:begin|end)|(?:Start|End)\\?_Module\w*)\s*$"
)


_BLANK_RUN = re.compile(r"\n{3,}")
# An error page served with 200 (a "soft 404", #20), recognised by its <title> or its h1 only: body text
# can discuss a missing page. "404" alone is not enough ("Art. 404 OR"); it must stand alone or next to
# an error word.
_SOFT_404 = re.compile(
    r"not found|seite (?:wurde )?nicht gefunden|page (?:introuvable|non trouvée)|pagina non trovata"
    r"|^\W*404\W*$|\b(?:error|fehler|erreur|errore)\W+(?:page\W+)?\(?404\b|\b404\W+(?:error|fehler|erreur|errore)\b",
    re.IGNORECASE)


def _strip_cms_markers(text: str) -> str:
    """Drop lines that are only a known CMS include-marker or a bare run of brackets."""
    lines = [line for line in text.split("\n") if not _MARKER_LINE.match(line)]
    return _BLANK_RUN.sub("\n\n", "\n".join(lines)).strip()


@dataclass(frozen=True)
class CrawledPage:
    language: str
    emit: bool  # in one of the source's languages (or undeclared, taking the source default)
    title: str  # the page title, else its URL
    title_hint: str  # the page title alone, "" when it has none
    sections: tuple[ParsedSection, ...]
    alternates: Mapping[str, str]
    links: tuple[str, ...]
    pdf_links: tuple[tuple[str, str], ...]
    published: date | None
    modified: date | None
    soft_404: str | None = None  # the <title> or h1 that marks an error page served with 200
    canonical: str | None = None  # <link rel="canonical">, absolute, without its fragment


def _soft_404(*titles: str) -> str | None:
    return next((t for t in titles if t and _SOFT_404.search(t)), None)


def parse_crawled_page(html: str, final: str, spec: SourceSpec,
                       pdf_patterns: tuple[re.Pattern[str], ...]) -> CrawledPage:
    cfg = spec.config
    # Sentinel default so "no <html lang>" is told apart from "declared as the source's default
    # language" -- both would otherwise read as the default.
    page = html_to_page(html, url=final, default_language="", content_selector=cfg.get("content_selector"))
    meta = page_meta(html, final, language_links_selector=cfg.get("language_links_selector"),
                     pdf_link_patterns=pdf_patterns)
    self_lang = next((lang for lang, href in meta.alternates.items()
                      if urldefrag(href)[0] == urldefrag(final)[0]), None)
    declared = self_lang or (page.language or None)
    if declared is None:
        lang, emit = spec.languages[0], True
    else:
        lang, emit = declared, declared in LANGUAGES and declared in spec.languages
    title = page.title or final
    sections = []
    for i, s in enumerate(page.sections):
        parts = [p for p in s.heading_path.split(" > ") if p]
        crumbs = tuple(parts) if parts and parts[0] == title else (title, *parts)
        sections.append(ParsedSection(align_key=f"{lang}:{i}", breadcrumb=crumbs, anchor=s.anchor,
                                      text=_strip_cms_markers(s.text)))
    return CrawledPage(language=lang, emit=emit, title=title, title_hint=page.title, sections=tuple(sections),
                       alternates=dict(meta.alternates), links=extract_links(html, base_url=final),
                       pdf_links=meta.pdf_links, published=meta.published, modified=meta.modified,
                       soft_404=_soft_404(meta.title, page.title), canonical=meta.canonical)
