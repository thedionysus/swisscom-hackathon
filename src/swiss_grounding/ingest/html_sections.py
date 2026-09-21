from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from swiss_grounding.ingest.models import Section

DROP_TAGS = ("nav", "footer", "header", "script", "style", "noscript", "aside", "form")
HEADING_TAGS = ("h1", "h2", "h3", "h4")
MAIN_CANDIDATES = ("main", "article", "[role=main]", "body")


@dataclass(frozen=True)
class Page:
    title: str
    language: str
    sections: tuple[Section, ...]


def _content_root(soup: BeautifulSoup) -> Tag | None:
    for selector in MAIN_CANDIDATES:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return None


def _clean(root: Tag) -> Tag:
    for tag in root.find_all(DROP_TAGS):
        tag.decompose()
    return root


def _title(soup: BeautifulSoup, root: Tag | None) -> str:
    """The page's title: the first h1 inside the (cleaned) content root, falling back to <title>.

    Pages commonly carry a visually-hidden ``<h1>Navigation</h1>`` inside their nav and another
    hidden h1 inside their footer; neither lives in the content root, so this never sees them.
    """
    if root is not None:
        h1 = root.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(" ", strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.split("|")[0].strip()
    return ""


def _language(soup: BeautifulSoup, default: str) -> str:
    html = soup.find("html")
    lang = html.get("lang") if html else None
    return lang.split("-")[0].lower() if lang else default


def _to_text(nodes: list[Tag]) -> str:
    html = "".join(str(n) for n in nodes)
    return markdownify(html, heading_style="ATX", strip=["a", "img"]).strip()


def _holds_heading(node: Tag) -> bool:
    return node.find(HEADING_TAGS) is not None


def _split_by_headings(root: Tag, title: str) -> tuple[Section, ...]:
    """Split root into sections keyed by heading, walking the DOM recursively.

    Real pages nest their content several levels below the content root (wrapping
    ``<div>``s, ``<details>``, breadcrumb containers, ...), so headings are not necessarily
    direct children of root. Any child that itself contains a heading is descended into;
    everything else is buffered as-is and converted to markdown in one piece, so list/table
    structure inside it is preserved exactly as before.
    """
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    anchor: str | None = None
    buffer: list[Tag] = []

    def flush() -> None:
        text = _to_text(buffer)
        if text:
            path = " > ".join(name for _, name in stack) or title
            sections.append(Section(heading_path=path, anchor=anchor, text=text))
        buffer.clear()

    def walk(node: Tag) -> None:
        nonlocal anchor
        for child in node.find_all(recursive=False):
            if child.name in HEADING_TAGS:
                flush()
                level = int(child.name[1])
                name = child.get_text(" ", strip=True)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, name))
                anchor = child.get("id")
            elif _holds_heading(child):
                walk(child)
            else:
                buffer.append(child)

    walk(root)
    flush()
    return tuple(sections)


def html_to_page(html: str, url: str, default_language: str) -> Page:
    """Parse an HTML page into a title, a language, and heading-delimited sections."""
    soup = BeautifulSoup(html, "lxml")
    language = _language(soup, default_language)
    root = _content_root(soup)
    if root is None:
        return Page(title=_title(soup, None), language=language, sections=())
    cleaned = _clean(root)
    title = _title(soup, cleaned)
    sections = _split_by_headings(cleaned, title)
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
