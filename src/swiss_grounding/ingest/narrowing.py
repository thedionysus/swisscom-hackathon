"""Extent narrowing under ADR 0002: only a level marker, a postal code, or a bare name in the
title or a heading may narrow; a name shared with an ancestor of the default extent never
narrows on its own; common-word Quartier names always need a marker."""
import re
from collections.abc import Sequence

from swiss_grounding.locations.models import LEVEL_DEPTH, Level
from swiss_grounding.locations.tree import LocationTree, normalize

SOURCE_DEFAULT = "source_default"
COMMON_WORD_NEIGHBORHOODS = frozenset({"city", "hard", "werd", "enge"})
COMMON_WORD_COMMUNES = frozenset({
    "egg", "horn", "port", "rain", "stein", "wald", "lens", "buch", "berg",
    "arch", "cham", "birr", "nods", "vex", "oberdorf",
})
PLZ = re.compile(r"(?<!\d)(\d{4})(?!\d)")
WORD = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]*"
MARKER_WORDS = {
    "kanton": Level.CANTON,
    "canton": Level.CANTON,
    "canton of": Level.CANTON,
    "stadt": Level.MUNICIPALITY,
    "gemeinde": Level.MUNICIPALITY,
    "city of": Level.MUNICIPALITY,
    "quartier": Level.NEIGHBORHOOD,
}
MARKED = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in MARKER_WORDS) + r")\s+(" + WORD + r"(?:\s+" + WORD + r"){0,2})",
    re.IGNORECASE,
)
KREIS = re.compile(r"\bKreis\s+(\d{1,2})\b", re.IGNORECASE)
MAX_NGRAM = 3


def _names(tree: LocationTree) -> dict[str, str]:
    """normalized name -> location id; deeper nodes win duplicate names (city over canton)."""
    names: dict[str, str] = {}
    for loc in sorted(tree.all(), key=lambda l: LEVEL_DEPTH[l.level]):
        for name in loc.all_names():
            names[normalize(name)] = loc.id
    return names


def _ngrams(text: str) -> list[str]:
    words = re.findall(WORD, text)
    return [" ".join(words[i:i + n]) for n in range(MAX_NGRAM, 0, -1) for i in range(len(words) - n + 1)]


def _marker_mentions(tree: LocationTree, names: dict[str, str], text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in MARKED.finditer(text):
        level = MARKER_WORDS[m.group(1).lower()]
        for gram in _ngrams(m.group(2)):
            node_id = names.get(normalize(gram))
            if node_id and tree.get(node_id).level is level:
                found.append((node_id, f"marker:{m.group(1)} {gram}"))
                break
    for m in KREIS.finditer(text):
        node_id = names.get(normalize(f"Kreis {m.group(1)}"))
        if node_id:
            found.append((node_id, f"marker:Kreis {m.group(1)}"))
    for m in PLZ.finditer(text):
        node_id = names.get(m.group(1))
        if node_id:
            found.append((node_id, f"plz:{m.group(1)}"))
    return found


def _bare_mentions(tree: LocationTree, names: dict[str, str], text: str, where: str,
                    ancestors: set[str]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for gram in _ngrams(text):
        key = normalize(gram)
        node_id = names.get(key)
        if not node_id or node_id in ancestors:
            continue
        node = tree.get(node_id)
        if node.level is Level.NEIGHBORHOOD and key in COMMON_WORD_NEIGHBORHOODS:
            continue
        if node.level is Level.MUNICIPALITY and key in COMMON_WORD_COMMUNES:
            continue
        if any(normalize(n) == key for a in ancestors for n in tree.get(a).all_names()):
            continue
        found.append((node_id, f"{where}:{gram}"))
    return found


def _deepest_common_ancestor(tree: LocationTree, ids: tuple[str, ...]) -> str:
    paths = [tree.path(i) for i in ids]
    common = paths[0]
    for p in paths[1:]:
        common = tuple(a for a, b in zip(common, p) if a == b)
    return common[-1]


def narrow_extent(tree: LocationTree, default_extent_id: str, title: str, headings: Sequence[str],
                  text: str) -> tuple[str, str]:
    """Narrow to a descendant of the default extent; never widen, never move sideways."""
    names = _names(tree)
    ancestors = set(tree.path(default_extent_id))
    mentions = _marker_mentions(tree, names, " ".join((title, *headings, text)))
    mentions += _bare_mentions(tree, names, title, "title", ancestors)
    for h in headings:
        mentions += _bare_mentions(tree, names, h, "heading", ancestors)
    below = [(n, why) for n, why in mentions if default_extent_id in tree.path(n) and n != default_extent_id]
    if not below:
        return default_extent_id, SOURCE_DEFAULT
    target = _deepest_common_ancestor(tree, tuple(dict.fromkeys(n for n, _ in below)))
    if target == default_extent_id:
        return default_extent_id, SOURCE_DEFAULT
    return target, "narrowed:" + ",".join(dict.fromkeys(why for _, why in below))
