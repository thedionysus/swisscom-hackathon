"""One fetched HTML page turned into a document draft, its language, alternates and links."""
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from urllib.parse import urldefrag

from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.models import LANGUAGES, ParsedSection, SourceSpec
from swiss_grounding.ingest.html_sections import extract_links, html_to_page


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
        sections.append(ParsedSection(align_key=f"{lang}:{i}", breadcrumb=crumbs, anchor=s.anchor, text=s.text))
    return CrawledPage(language=lang, emit=emit, title=title, title_hint=page.title, sections=tuple(sections),
                       alternates=dict(meta.alternates), links=extract_links(html, base_url=final),
                       pdf_links=meta.pdf_links, published=meta.published, modified=meta.modified)
