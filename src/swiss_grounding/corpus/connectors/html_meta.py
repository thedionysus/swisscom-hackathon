import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

DATE_META = ("article:modified_time", "dcterms.modified", "last-modified", "dc.date.modified",
             "article:published_time", "dcterms.date", "date", "dc.date")
STAND = re.compile(r"(?:Stand|Letzte Änderung|Aktualisiert|Mise à jour|Mis à jour le|Aggiornato|"
                   r"Ultimo aggiornamento)\s*:?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.IGNORECASE)


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


def page_meta(html: str, url: str) -> PageMeta:
    soup = BeautifulSoup(html, "lxml")
    alternates: dict[str, str] = {}
    for link in soup.find_all("link", hreflang=True, href=True):
        rel = link.get("rel") or []
        lang = link["hreflang"].split("-")[0].lower()
        if "alternate" in rel and lang != "x" and len(lang) == 2:
            alternates.setdefault(lang, _absolute(url, link["href"]))
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

    pdfs: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        target = _absolute(url, a["href"])
        if target.lower().split("?")[0].endswith(".pdf"):
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
