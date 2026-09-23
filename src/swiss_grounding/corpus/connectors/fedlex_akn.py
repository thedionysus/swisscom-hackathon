"""Akoma Ntoso (Fedlex) → one ParsedSection per article, with breadcrumb and paragraph/letter labels."""
from bs4 import BeautifulSoup, NavigableString, Tag

from swiss_grounding.corpus.models import ParsedSection

CONTAINERS = ("book", "part", "title", "chapter", "section", "subsection", "division")
LIST_ITEMS = ("item", "point")
# Marker inserted before each list item so `_render` can split list items onto their own line
# without relying on literal "\n" characters, which pretty-printed XML also puts between a
# <num> and its <content> as pure indentation whitespace (amendment A10).
_ITEM_MARKER = "\x00"


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


def _render(block: Tag) -> str:
    """Text of a paragraph (or article body) keeping its number and one line per list item.

    Whitespace inside every text node is collapsed first (so pretty-printed indentation between,
    say, `<num>1</num>` and `<content>` never introduces a spurious line break), then an explicit
    marker is inserted before each list item and the joined text is split on that marker only.
    """
    for node in list(block.find_all(string=True)):
        node.replace_with(" ".join(node.split()))
    for item in block.find_all(LIST_ITEMS):
        item.insert_before(NavigableString(_ITEM_MARKER))
    raw = block.get_text(" ", strip=False)
    lines = [" ".join(line.split()) for line in raw.split(_ITEM_MARKER)]
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
            body = "\n".join(t for t in (_render(c) for c in article.find_all("content")) if t)
        if body:
            sections.append(ParsedSection(align_key=key, breadcrumb=tuple(c for c in crumbs if c), anchor=key,
                                          text=body, paragraphs=tuple(paragraphs)))
    return tuple(sections)
