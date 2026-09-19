"""Extent narrowing under ADR 0002: only a level marker, a postal code, or a bare name in the
title or a heading may narrow; a name shared with an ancestor of the default extent never
narrows on its own; common-word Quartier and commune names always need a marker."""
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
PLZ_CONTEXT = re.compile(r"(?:PLZ|Postleitzahl|postal code|CH-)\s*(\d{4})(?!\d)", re.IGNORECASE)
WORD = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]*"
MARKER_WORDS = {
    "kanton": Level.CANTON,
    "canton": Level.CANTON,
    "canton of": Level.CANTON,
    "stadt": Level.MUNICIPALITY,
    "gemeinde": Level.MUNICIPALITY,
    "city of": Level.MUNICIPALITY,
    "quartier": Level.NEIGHBORHOOD,
    "municipality": Level.MUNICIPALITY,
    "municipality of": Level.MUNICIPALITY,
    "town of": Level.MUNICIPALITY,
    "commune": Level.MUNICIPALITY,
    "commune de": Level.MUNICIPALITY,
    "ville de": Level.MUNICIPALITY,
    "comune di": Level.MUNICIPALITY,
    "city": Level.MUNICIPALITY,
    "district of": Level.NEIGHBORHOOD,
}
# longest phrase first, so "canton of" is tried before "canton" and "city of" before "city"
_MARKER_ALTERNATION = sorted(MARKER_WORDS, key=lambda w: (-len(w.split()), -len(w)))
MARKED = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _MARKER_ALTERNATION) + r")\s+(" + WORD + r"(?:\s+" + WORD + r"){0,2})",
    re.IGNORECASE,
)
KREIS = re.compile(r"\b(Kreis|District)\s+(\d{1,2})\b", re.IGNORECASE)
MAX_NGRAM = 3


def _build_indexes(tree: LocationTree) -> tuple[dict[str, str], dict[Level, dict[str, tuple[str, ...]]]]:
    """One pass over the tree building both name indexes:

    - a global normalized-name -> id map where deeper nodes win duplicate names (city over canton),
      used for bare mentions;
    - a per-level normalized-name -> ids map (a name may be shared by several nodes at the same
      level, e.g. several communes called "Wald"), used for markers, which are disambiguated
      against the default extent's path.
    """
    names: dict[str, str] = {}
    by_level: dict[Level, dict[str, list[str]]] = {}
    for loc in sorted(tree.all(), key=lambda l: LEVEL_DEPTH[l.level]):
        for name in loc.all_names():
            key = normalize(name)
            names[key] = loc.id
            ids = by_level.setdefault(loc.level, {}).setdefault(key, [])
            if loc.id not in ids:
                ids.append(loc.id)
    by_level_tuples = {level: {k: tuple(v) for k, v in level_names.items()} for level, level_names in by_level.items()}
    return names, by_level_tuples


def _resolve_within(tree: LocationTree, default_extent_id: str, candidates: tuple[str, ...] | None) -> str | None:
    """Keep only candidates on the default extent's path; use one when exactly one remains."""
    if not candidates:
        return None
    matching = tuple(c for c in candidates if default_extent_id in tree.path(c))
    return matching[0] if len(matching) == 1 else None


def _ngrams(text: str) -> list[str]:
    words = re.findall(WORD, text)
    return [" ".join(words[i:i + n]) for n in range(MAX_NGRAM, 0, -1) for i in range(len(words) - n + 1)]


def _ngram_spans(text: str) -> list[tuple[str, int, int]]:
    words = list(re.finditer(WORD, text))
    return [
        (" ".join(w.group() for w in words[i:i + n]), words[i].start(), words[i + n - 1].end())
        for n in range(MAX_NGRAM, 0, -1) for i in range(len(words) - n + 1)
    ]


def _marker_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges already claimed by a level marker or a Kreis/District mention."""
    return [m.span() for m in MARKED.finditer(text)] + [m.span() for m in KREIS.finditer(text)]


def _overlaps(start: int, end: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(start < s_end and s_start < end for s_start, s_end in spans)


def _marker_mentions(tree: LocationTree, names_by_level: dict[Level, dict[str, tuple[str, ...]]], text: str,
                     default_extent_id: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in MARKED.finditer(text):
        level = MARKER_WORDS[m.group(1).lower()]
        level_names = names_by_level.get(level, {})
        for gram in _ngrams(m.group(2)):
            candidates = level_names.get(normalize(gram))
            if not candidates:
                continue
            node_id = _resolve_within(tree, default_extent_id, candidates)
            if node_id:
                found.append((node_id, f"marker:{m.group(1)} {gram}"))
            break
    for m in KREIS.finditer(text):
        candidates = names_by_level.get(Level.NEIGHBORHOOD, {}).get(normalize(f"Kreis {m.group(2)}"))
        node_id = _resolve_within(tree, default_extent_id, candidates)
        if node_id:
            found.append((node_id, f"marker:{m.group(1)} {m.group(2)}"))
    return found


def _plz_context_mentions(names: dict[str, str], text: str) -> list[tuple[str, str]]:
    """A postal code in body text counts only when preceded by an explicit postal-code cue."""
    found: list[tuple[str, str]] = []
    for m in PLZ_CONTEXT.finditer(text):
        node_id = names.get(m.group(1))
        if node_id:
            found.append((node_id, f"plz:{m.group(1)}"))
    return found


def _plz_bare_mentions(names: dict[str, str], text: str, where: str) -> list[tuple[str, str]]:
    """A postal code in the title or a heading counts without any further context."""
    found: list[tuple[str, str]] = []
    for m in PLZ.finditer(text):
        node_id = names.get(m.group(1))
        if node_id:
            found.append((node_id, f"{where}:plz:{m.group(1)}"))
    return found


def _bare_mentions(tree: LocationTree, names: dict[str, str], text: str, where: str,
                    ancestors: set[str], exclude_spans: Sequence[tuple[int, int]] = ()) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    accepted_spans: list[tuple[int, int]] = []
    for gram, start, end in _ngram_spans(text):
        if _overlaps(start, end, exclude_spans) or _overlaps(start, end, accepted_spans):
            continue
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
        accepted_spans.append((start, end))
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
    names, names_by_level = _build_indexes(tree)
    ancestors = set(tree.path(default_extent_id))

    mentions: list[tuple[str, str]] = []
    mentions += _marker_mentions(tree, names_by_level, title, default_extent_id)
    mentions += _bare_mentions(tree, names, title, "title", ancestors, _marker_spans(title))
    mentions += _plz_bare_mentions(names, title, "title")
    for h in headings:
        mentions += _marker_mentions(tree, names_by_level, h, default_extent_id)
        mentions += _bare_mentions(tree, names, h, "heading", ancestors, _marker_spans(h))
        mentions += _plz_bare_mentions(names, h, "heading")
    mentions += _marker_mentions(tree, names_by_level, text, default_extent_id)
    mentions += _plz_context_mentions(names, text)
    below = [(n, why) for n, why in mentions if default_extent_id in tree.path(n) and n != default_extent_id]
    if not below:
        return default_extent_id, SOURCE_DEFAULT
    target = _deepest_common_ancestor(tree, tuple(dict.fromkeys(n for n, _ in below)))
    if target == default_extent_id:
        return default_extent_id, SOURCE_DEFAULT
    return target, "narrowed:" + ",".join(dict.fromkeys(why for _, why in below))
