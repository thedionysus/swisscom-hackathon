import re

from swiss_grounding.locations.models import LEVEL_DEPTH
from swiss_grounding.locations.tree import LocationTree, normalize

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]*")
MIN_NAME_LEN = 3
MAX_NGRAM = 3
SOURCE_DEFAULT = "source_default"


def _candidate_names(tree: LocationTree) -> dict[str, str]:
    """normalized name -> location id; deeper nodes win duplicate names (city over canton)."""
    names: dict[str, str] = {}
    for loc in sorted(tree.all(), key=lambda l: LEVEL_DEPTH[l.level]):
        for name in loc.all_names():
            if len(name) < MIN_NAME_LEN or not name[:1].isupper():
                continue
            names[normalize(name)] = loc.id
    return names


def _mentions(tree: LocationTree, text: str) -> tuple[str, ...]:
    names = _candidate_names(tree)
    words = WORD_RE.findall(text)
    found: list[str] = []
    for size in range(MAX_NGRAM, 0, -1):
        for start in range(len(words) - size + 1):
            span = words[start:start + size]
            if not span[0][:1].isupper():
                continue
            key = normalize(" ".join(span))
            if key in names:
                found.append(names[key])
    return tuple(dict.fromkeys(found))


def _deepest_common_ancestor(tree: LocationTree, ids: tuple[str, ...]) -> str:
    paths = [tree.path(i) for i in ids]
    common = paths[0]
    for p in paths[1:]:
        common = tuple(a for a, b in zip(common, p) if a == b)
    return common[-1]


def narrow_extent(tree: LocationTree, default_extent_id: str, text: str) -> tuple[str, str]:
    """Narrow to a descendant of the default extent when every mention lies under one; never widen."""
    mentions = tuple(
        m for m in _mentions(tree, text)
        if default_extent_id in tree.path(m) and m != default_extent_id
    )
    if not mentions:
        return default_extent_id, SOURCE_DEFAULT
    target = _deepest_common_ancestor(tree, mentions)
    if target == default_extent_id:
        return default_extent_id, SOURCE_DEFAULT
    labels = ",".join(tree.get(m).label("en") for m in mentions)
    return target, f"narrowed:{labels}"
