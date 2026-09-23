import re
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from bs4.element import PageElement
from markdownify import markdownify

from swiss_grounding.ingest.models import Section

DROP_TAGS = ("nav", "footer", "header", "script", "style", "noscript", "aside", "form")
# Class tokens CMSes use to visually hide a heading from sighted users while keeping it in the
# DOM for screen readers (chur.ch's "Inhalt", others' "Navigation"/"Kopfzeile"). Such a heading
# is never the page title and never a real section break -- its text is dropped entirely.
# The bare `hidden` token is deliberately absent: utility CSS pairs it with a breakpoint
# (`hidden md:block`), so a heading carrying it is usually a real, responsive heading.
_HIDDEN_CLASSES = frozenset({
    "sr-only", "visually-hidden", "visuallyhidden", "invisible", "screen-reader-text",
    "element-invisible", "u-visually-hidden", "show-for-sr", "access", "offscreen",
})
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)
# _clean runs in two stages (see html_to_page): everything except <header> first, then
# <header> on its own, with the title looked up in between. That way an h1 wrapped in a
# <header> inside the content root (a page-header block inside <main>) still counts as the
# content title, while a <nav>'s or <body>'s own hidden "Navigation" h1 -- gone in stage one
# regardless of which selector supplied the content root -- never can.
_NON_HEADER_DROP_TAGS = tuple(tag for tag in DROP_TAGS if tag != "header")
_HEADER_DROP_TAGS = ("header",)
HEADING_TAGS = ("h1", "h2", "h3", "h4")
MAIN_CANDIDATES = ("main", "article", "[role=main]", "body")
# Never split a table/list on a heading nested inside it: markdownify needs the whole
# element in one piece, or its structure (rows, item nesting) comes out destructured.
NO_DESCEND_TAGS = frozenset({"table", "ul", "ol", "dl"})


@dataclass(frozen=True)
class Page:
    title: str
    language: str
    sections: tuple[Section, ...]


def _content_root(soup: BeautifulSoup, content_selector: str | None = None) -> Tag | None:
    """The element holding the page content: `content_selector` when given and matching, else the
    first of <main>, <article>, [role=main], <body>."""
    candidates = (content_selector, *MAIN_CANDIDATES) if content_selector else MAIN_CANDIDATES
    for selector in candidates:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return None


def _clean(root: Tag, tags: tuple[str, ...] = DROP_TAGS) -> Tag:
    for tag in root.find_all(tags):
        tag.decompose()
    return root


def _is_hidden(tag: Tag) -> bool:
    """True for a heading that is in the DOM but never shown to a sighted visitor: a `hidden`
    attribute, `aria-hidden="true"`, an inline `display:none`/`visibility:hidden` style, or a
    class token from a known screen-reader-only convention (sr-only, visually-hidden, ...)."""
    if tag.has_attr("hidden"):
        return True
    if (tag.get("aria-hidden") or "").strip().lower() == "true":
        return True
    if _HIDDEN_STYLE.search(tag.get("style") or ""):
        return True
    classes = tag.get("class") or []
    return any(c in _HIDDEN_CLASSES for c in classes)


def _visible_heading(node: Tag) -> Tag | None:
    """The first heading inside `node` that is not visually hidden, else None."""
    for heading in node.find_all(HEADING_TAGS):
        if not _is_hidden(heading):
            return heading
    return None


def _title(soup: BeautifulSoup, root: Tag | None) -> str:
    """The page's title: the first VISIBLE h1 inside the content root, falling back to <title>.

    Pages commonly carry a visually-hidden ``<h1>Navigation</h1>`` inside their nav (or, when
    the content root falls back to ``<body>``, a nav that's a direct sibling of it there too)
    and another hidden h1 inside their footer; the caller has already dropped both by the time
    this runs, so neither is ever seen. A ``<header>`` wrapping the real content h1 (e.g. a
    page-header block inside ``<main>``) is still in place at this point, so that h1 is found.
    Some sites (chur.ch's #maincontent) instead open the content root itself with a hidden h1
    ("Inhalt"); that one is never dropped by ancestry, so it is skipped by `_is_hidden` here.
    """
    if root is not None:
        h1 = next((h for h in root.find_all("h1") if not _is_hidden(h) and h.get_text(strip=True)), None)
        if h1:
            return h1.get_text(" ", strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.rsplit("|", 1)[0].strip()
    return ""


def _language(soup: BeautifulSoup, default: str) -> str:
    html = soup.find("html")
    lang = html.get("lang") if html else None
    return lang.split("-")[0].lower() if lang else default


def _to_text(nodes: list[PageElement]) -> str:
    html = "".join(str(n) for n in nodes)
    return markdownify(html, heading_style="ATX", strip=["a", "img"]).strip()


def _holds_heading(node: Tag) -> bool:
    return _visible_heading(node) is not None


def _split_by_headings(root: Tag, title: str) -> tuple[Section, ...]:
    """Split root into sections keyed by heading, walking the DOM recursively.

    Real pages nest their content many levels below the content root (wrapping ``<div>``s,
    ``<header>`` blocks, ``<details>``, breadcrumb containers, ...), so headings are not
    necessarily direct children of root, or even close to it. Any child element that itself
    contains a heading is descended into, however deep; everything else -- elements and bare
    text alike -- is buffered as-is and converted to markdown in one piece, so structure
    inside it (e.g. a list) is preserved. A table/list/dl is never descended into even if a
    heading tag lives inside it, since splitting one apart destructures it.
    """
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    anchor: str | None = None
    buffer: list[PageElement] = []

    def flush() -> None:
        text = _to_text(buffer)
        if text:
            path = " > ".join(name for _, name in stack) or title
            sections.append(Section(heading_path=path, anchor=anchor, text=text))
        buffer.clear()

    def walk(node: Tag) -> None:
        nonlocal anchor
        for child in node.children:
            if isinstance(child, Comment):
                continue  # a leaked <!-- --> (e.g. TYPO3SEARCH markers) is never content
            if isinstance(child, NavigableString):
                buffer.append(child)
            elif not isinstance(child, Tag):
                continue
            elif child.name in HEADING_TAGS:
                if _is_hidden(child):
                    continue  # visually-hidden heading: not a heading, its text is dropped
                flush()
                level = int(child.name[1])
                name = child.get_text(" ", strip=True)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, name))
                anchor = child.get("id")
            elif child.name not in NO_DESCEND_TAGS and _holds_heading(child):
                walk(child)
            else:
                buffer.append(child)

    walk(root)
    flush()
    return tuple(sections)


def html_to_page(html: str, url: str, default_language: str, content_selector: str | None = None) -> Page:
    """Parse an HTML page into a title, a language, and heading-delimited sections.

    `content_selector` (CSS) picks the content root for sites without a usable <main>; when it
    matches nothing the default candidates apply.
    """
    soup = BeautifulSoup(html, "lxml")
    language = _language(soup, default_language)
    root = _content_root(soup, content_selector)
    if root is None:
        return Page(title=_title(soup, None), language=language, sections=())
    _clean(root, _NON_HEADER_DROP_TAGS)  # drop nav/footer/etc. first so their h1s can't win
    title = _title(soup, root)  # ... then look for the title, while a <header> is still there
    _clean(root, _HEADER_DROP_TAGS)  # now drop <header> too, before splitting into sections
    # A hidden heading nested inside a non-descended container (e.g. a breadcrumb nav's sr-only
    # <h2>) would otherwise still be serialised to markdown as part of that container's buffered
    # text (walk() only special-cases a heading it meets directly). Remove every hidden heading
    # outright so none of them can leak in, however deep.
    for heading in root.find_all(HEADING_TAGS):
        if _is_hidden(heading):
            heading.decompose()
    sections = _split_by_headings(root, title)
    return Page(title=title, language=language, sections=sections)


NON_NAVIGATIONAL_HREF_TAGS = frozenset({"link", "base", "script", "style"})


def extract_links(html: str, base_url: str) -> tuple[str, ...]:
    """All absolute http(s) links on the page, fragments removed, order preserved, deduplicated.

    Reads ``href`` from any element, not just ``<a>``: sites built on web components
    (e.g. stadt-zuerich.ch's ``<stzh-link>``) carry navigation on custom tags.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: dict[str, None] = {}
    for element in soup.find_all(href=True):
        if element.name in NON_NAVIGATIONAL_HREF_TAGS:
            continue
        absolute, _ = urldefrag(urljoin(base_url, element["href"]))
        if absolute.startswith(("http://", "https://")):
            seen.setdefault(absolute, None)
    return tuple(seen)
