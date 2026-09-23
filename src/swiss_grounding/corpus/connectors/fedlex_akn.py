"""Akoma Ntoso (Fedlex) → one ParsedSection per article, with breadcrumb and paragraph/letter labels."""
import re

from bs4 import BeautifulSoup, NavigableString, Tag

from swiss_grounding.corpus.models import ParsedSection

CONTAINERS = ("book", "part", "title", "chapter", "section", "subsection", "division")
LIST_ITEMS = ("item", "point")
# Marker inserted before each list item so `_render` can split list items onto their own line
# without relying on literal "\n" characters, which pretty-printed XML also puts between a
# <num> and its <content> as pure indentation whitespace (amendment A10).
_ITEM_MARKER = "\x00"
# Tags whose start/end is a genuine word boundary: a space is inserted around them so, e.g., a
# paragraph's <num> and <content> never fuse. Inline markup (<i>, <sup>, ...) used inside running
# text for things like "Artikel 64<i>c</i>" is deliberately NOT in this list, so it stays fused
# into "64c" instead of becoming "64 c".
_BOUNDARY_TAGS = ("num", "p", "blockList", "content")
_WHITESPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,;:)])")


def _flat(tag: Tag | None) -> str:
    return " ".join(tag.get_text("", strip=False).split()) if tag is not None else ""


def _label(element: Tag) -> str:
    num = _flat(element.find("num", recursive=False))
    heading = _flat(element.find("heading", recursive=False))
    return " ".join(part for part in (num, heading) if part)


def _containers_above(article: Tag) -> list[str]:
    labels: list[str] = []
    parent = article.parent
    while isinstance(parent, Tag):
        if parent.name in CONTAINERS:
            label = _label(parent)
            if label:
                labels.append(label)
        parent = parent.parent
    return list(reversed(labels))


def _clean_line(line: str) -> str:
    collapsed = _WHITESPACE.sub(" ", line).strip()
    # A removed <authorialNote> (footnote) can leave a stray space where it used to sit, right
    # before the punctuation that followed it, e.g. "Grenzkodex ." -> "Grenzkodex.".
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", collapsed)


def _render(block: Tag) -> str:
    """Text of a paragraph (or article body) keeping its number and one line per list item.

    Whitespace inside every text node is collapsed first, keeping edge whitespace so a real word
    boundary (e.g. pretty-printed indentation between `<num>1</num>` and `<content>`) is not lost.
    A space is then inserted only at explicit block boundaries (around `num`/`p`/`blockList`/
    `content`) rather than between every pair of text nodes, so inline markup used inside running
    text (`<i>`, `<sup>`, ...) stays fused with its neighbours instead of gaining a spurious space.
    An explicit marker is inserted before each list item so it lands on its own line.
    """
    for node in list(block.find_all(string=True)):
        node.replace_with(_WHITESPACE.sub(" ", str(node)))
    for tag in block.find_all(_BOUNDARY_TAGS):
        tag.insert_before(NavigableString(" "))
        tag.insert_after(NavigableString(" "))
    for item in block.find_all(LIST_ITEMS):
        item.insert_before(NavigableString(_ITEM_MARKER))
    raw = block.get_text("", strip=False)
    lines = [_clean_line(line) for line in raw.split(_ITEM_MARKER)]
    return "\n".join(line for line in lines if line)


def parse_akn(xml: str, act_title: str, sr: str) -> tuple[ParsedSection, ...]:
    soup = BeautifulSoup(xml, "xml")
    for note in soup.find_all("authorialNote"):
        note.decompose()
    root_crumb = f"SR {sr} {act_title}".strip()
    sections: list[ParsedSection] = []
    for article in soup.find_all("article"):
        key = article.get("eId") or f"art_{len(sections)}"
        crumbs = (root_crumb, *_containers_above(article), _label(article))
        paragraphs: list[tuple[str, str]] = []
        for index, para in enumerate(article.find_all("paragraph", recursive=False), start=1):
            text = _render(para)
            if text:
                paragraphs.append((para.get("eId") or f"{key}/para_{index}", text))
        if paragraphs:
            body = "\n".join(text for _, text in paragraphs)
        else:
            # Direct children only: `find_all` is recursive and would otherwise also pick up any
            # <content> nested inside this article's own <blockList>/<item> and render it twice.
            body = "\n".join(t for t in (_render(c) for c in article.find_all("content", recursive=False)) if t)
        if body:
            sections.append(ParsedSection(align_key=key, breadcrumb=tuple(c for c in crumbs if c), anchor=key,
                                          text=body, paragraphs=tuple(paragraphs)))
    return tuple(sections)
