import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from swiss_grounding.corpus.models import LANGUAGES

DATE_META = ("article:modified_time", "dcterms.modified", "last-modified", "dc.date.modified",
             "article:published_time", "dcterms.date", "date", "dc.date")
STAND = re.compile(r"(?:Stand|Letzte Änderung|Aktualisiert|Mise à jour|Mis à jour le|Aggiornato|"
                   r"Ultimo aggiornamento)\s*:?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.IGNORECASE)
# Language-switcher link texts that name a language instead of giving its code.
LANGUAGE_NAMES = {
    "deutsch": "de", "german": "de", "allemand": "de", "tedesco": "de",
    "français": "fr", "francais": "fr", "french": "fr", "französisch": "fr", "francese": "fr",
    "italiano": "it", "italian": "it", "italienisch": "it", "italien": "it",
    "english": "en", "englisch": "en", "anglais": "en", "inglese": "en",
    "rumantsch": "rm", "romansh": "rm", "rätoromanisch": "rm", "romanche": "rm", "romancio": "rm",
}
_PATH_LANGUAGE = re.compile(r"^/([a-z]{2})(?:/|$)", re.IGNORECASE)
# Nuxt's payload serialiser wraps reactive state as ["Reactive", <index>] and the like.
_NUXT_WRAPPERS = ("Reactive", "ShallowReactive", "Ref", "ShallowRef")


@dataclass(frozen=True)
class PageMeta:
    alternates: Mapping[str, str] = field(default_factory=dict)
    canonical: str | None = None
    published: date | None = None
    modified: date | None = None
    pdf_links: tuple[tuple[str, str], ...] = ()


def _absolute(base: str, href: str) -> str:
    return urldefrag(urljoin(base, href))[0]


def _iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _language_code(value: str | None) -> str | None:
    """A known corpus language from a hreflang/lang value ("fr-CH" -> "fr"), else None."""
    code = (value or "").strip().split("-")[0].split("_")[0].lower()
    return code if code in LANGUAGES else None


def _hreflang_alternates(soup: BeautifulSoup, url: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for link in soup.find_all("link", hreflang=True, href=True):
        lang = _language_code(link["hreflang"])
        if "alternate" in (link.get("rel") or []) and lang:
            found.setdefault(lang, _absolute(url, link["href"]))
    return found


def _switcher_language(link: Any, target: str) -> str | None:
    """Language of a language-switcher link: its hreflang/lang attribute, else its text (a
    two-letter code or a language name), else a leading /xx/ segment of the URL it points to."""
    for attribute in ("hreflang", "lang"):
        if link.get(attribute):
            return _language_code(link[attribute])
    text = " ".join(link.get_text(" ").split()).lower()
    for candidate in (text, *text.split()):
        if len(candidate) == 2 and candidate in LANGUAGES:
            return candidate
        if candidate in LANGUAGE_NAMES:
            return LANGUAGE_NAMES[candidate]
    match = _PATH_LANGUAGE.match(urlparse(target).path)
    return _language_code(match.group(1)) if match else None


def _switcher_alternates(soup: BeautifulSoup, url: str, selector: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for link in soup.select(selector):
        if not link.get("href"):
            continue
        target = _absolute(url, link["href"])
        if not target.startswith(("http://", "https://")):
            continue
        lang = _switcher_language(link, target)
        if lang:
            found.setdefault(lang, target)
    return found


def _nuxt_alternates(soup: BeautifulSoup, url: str) -> dict[str, str]:
    """Alternates from the federal new-CMS Nuxt payload (``<script id="__NUXT_DATA__">``).

    The payload is a flat JSON array whose containers hold integer indices into the same array.
    The page record is the dict carrying both ``groupId`` and ``translationPages``; each
    translation page is ``{lang, slug}`` and lives at ``/{lang}/{slug}`` on the same host.
    Anything malformed yields no alternates rather than an error.
    """
    script = soup.find("script", id="__NUXT_DATA__")
    if script is None or not script.string:
        return {}
    try:
        data = json.loads(script.string)
    except ValueError:
        return {}
    if not isinstance(data, list):
        return {}

    def at(index: Any) -> Any:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(data):
            return None
        value = data[index]
        if isinstance(value, list) and len(value) == 2 and value[0] in _NUXT_WRAPPERS:
            return at(value[1])
        return value

    record = next((node for node in data if isinstance(node, dict)
                   and "groupId" in node and "translationPages" in node), None)
    if record is None:
        return {}
    host = urlparse(url)
    found: dict[str, str] = {}
    own_lang = at(record.get("lang"))
    own = _language_code(own_lang) if isinstance(own_lang, str) else None
    if own:
        found[own] = urldefrag(url)[0]
    pages = at(record["translationPages"])
    for entry in pages if isinstance(pages, list) else ():
        page = at(entry)
        if not isinstance(page, dict):
            continue
        lang, slug = at(page.get("lang")), at(page.get("slug"))
        code = _language_code(lang) if isinstance(lang, str) else None
        if code and isinstance(slug, str) and slug.strip("/"):
            found.setdefault(code, f"{host.scheme}://{host.netloc}/{code}/{slug.strip('/')}")
    return found


def _is_pdf_link(target: str, patterns: Sequence[re.Pattern[str]]) -> bool:
    return target.lower().split("?")[0].endswith(".pdf") or any(p.search(target) for p in patterns)


def page_meta(html: str, url: str, language_links_selector: str | None = None,
              pdf_link_patterns: Sequence[str | re.Pattern[str]] = ()) -> PageMeta:
    """Alternates, canonical, dates and PDF links of one page.

    Alternates come from hreflang first; languages hreflang does not give are filled in from the
    links matched by `language_links_selector` (a site's language switcher), then from the
    federal new-CMS Nuxt payload. Only corpus languages (LANGUAGES) are kept.
    `pdf_link_patterns` (regexes on absolute URLs) mark links as PDFs beyond the .pdf suffix.
    """
    soup = BeautifulSoup(html, "lxml")
    alternates = _hreflang_alternates(soup, url)
    extra_sources = [_switcher_alternates(soup, url, language_links_selector)] if language_links_selector else []
    extra_sources.append(_nuxt_alternates(soup, url))
    for extra in extra_sources:
        for lang, href in extra.items():
            alternates.setdefault(lang, href)
    canonical_tag = soup.find("link", rel="canonical", href=True)
    canonical = _absolute(url, canonical_tag["href"]) if canonical_tag else None

    found: dict[str, date] = {}
    for meta in soup.find_all("meta", content=True):
        name = (meta.get("property") or meta.get("name") or "").lower()
        if name in DATE_META and (parsed := _iso_date(meta["content"])):
            found.setdefault(name, parsed)
    modified = next((found[n] for n in DATE_META[:4] if n in found), None)
    published = next((found[n] for n in DATE_META[4:] if n in found), None)
    if modified is None and (match := STAND.search(soup.get_text(" "))):
        day, month, year = (int(g) for g in match.groups())
        try:
            modified = date(year, month, day)
        except ValueError:
            modified = None

    patterns = [re.compile(p) if isinstance(p, str) else p for p in pdf_link_patterns]
    pdfs: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        target = _absolute(url, a["href"])
        if _is_pdf_link(target, patterns):
            pdfs.setdefault(target, " ".join(a.get_text(" ").split()))
    return PageMeta(alternates=alternates, canonical=canonical, published=published, modified=modified,
                    pdf_links=tuple(pdfs.items()))


def work_key(url: str, alternates: Mapping[str, str]) -> str:
    """One key for all language versions of a page: the smallest URL among the page and its alternates.

    Assumes alternates are listed symmetrically, which hreflang requires. A site that lists them
    asymmetrically yields two groups for one page; that costs corroboration, never correctness.
    """
    members = sorted({urldefrag(url)[0], *alternates.values()})
    return "html:" + members[0]
