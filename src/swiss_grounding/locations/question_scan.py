"""Alias-only scan of free-text questions for a Swiss jurisdiction.

Pure functions over a :class:`LocationTree`. Never calls GeoAdmin. The scan is
deliberately conservative: ordinary English words ("So", "Be", "AI", "City",
"Hard", "Enge", "SG") collide with canton abbreviations and Zurich Quartier
names, so single-word candidates must clear several guards before they count.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from swiss_grounding.locations.models import Level, Location, ResolvedLocation
from swiss_grounding.locations.tree import LocationTree

MAX_NGRAM = 3
PLZ_LENGTH = 4
AMBIGUOUS_ABBREVIATION_LENGTH = 2
PUNCTUATION = ".,;:!?()[]{}\"'«»„“”‚‘’"
SENTENCE_ENDERS = (".", "?", "!")
METHOD = "alias_in_question"


@dataclass(frozen=True)
class _AliasMatch:
    """One alias hit: the token span it covers and the nodes it matched."""
    start: int
    end: int
    text: str
    nodes: tuple[Location, ...]

    @property
    def size(self) -> int:
        return self.end - self.start


def _tokenize(question: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (raw tokens as written, tokens stripped of surrounding punctuation)."""
    raw = tuple(question.split())
    return raw, tuple(token.strip(PUNCTUATION) for token in raw)


def _alias_matches(tree: LocationTree, words: Sequence[str]) -> tuple[_AliasMatch, ...]:
    """Every alias hit for every 3-, 2- and 1-word window, longest first."""
    found: list[_AliasMatch] = []
    for size in range(MAX_NGRAM, 0, -1):
        for start in range(len(words) - size + 1):
            span = words[start:start + size]
            if not all(span):
                continue
            nodes = tree.find(" ".join(span))
            if nodes:
                found.append(_AliasMatch(start, start + size, " ".join(span), nodes))
    return tuple(found)


def _drop_contained(matches: Sequence[_AliasMatch]) -> tuple[_AliasMatch, ...]:
    """Drop a match whose token span sits inside a longer match ("Zürich" in "Kanton Zürich")."""
    return tuple(
        m for m in matches
        if not any(o.start <= m.start and m.end <= o.end and o.size > m.size for o in matches)
    )


def _is_sentence_initial(raw: Sequence[str], index: int) -> bool:
    return index == 0 or raw[index - 1].endswith(SENTENCE_ENDERS)


def _ancestor_ids(tree: LocationTree, node: Location) -> frozenset[str]:
    return frozenset(tree.path(node.id)[:-1])


def _has_ancestor_match(
    tree: LocationTree, node: Location, others: Sequence[_AliasMatch],
) -> bool:
    ancestors = _ancestor_ids(tree, node)
    return any(any(n.id in ancestors for n in o.nodes) for o in others)


def _accept_unigram(
    tree: LocationTree, match: _AliasMatch, raw: Sequence[str], others: Sequence[_AliasMatch],
    prose: bool,
) -> bool:
    """Guards against ordinary prose words that happen to be aliases."""
    word = match.text
    if word.isdigit():
        return len(word) == PLZ_LENGTH
    if len(word) == AMBIGUOUS_ABBREVIATION_LENGTH:
        return False
    if not word[:1].isupper():
        return False
    if prose and _is_sentence_initial(raw, match.start):
        return False
    if match.nodes[0].level is Level.NEIGHBORHOOD:
        return _has_ancestor_match(tree, match.nodes[0], others)
    return True


def _keep(
    tree: LocationTree, matches: Sequence[_AliasMatch], raw: Sequence[str], prose: bool,
) -> tuple[_AliasMatch, ...]:
    return tuple(
        m for m in matches
        if m.size > 1
        or _accept_unigram(tree, m, raw, [o for o in matches if o is not m], prose)
    )


def _most_specific(tree: LocationTree, matches: Sequence[_AliasMatch]) -> _AliasMatch:
    return max(matches, key=lambda m: len(tree.path(m.nodes[0].id)))


def _is_candidate_word(word: str) -> bool:
    """A word that looks like it could name a place: a postal code or a capitalised word.

    Mirrors the entry checks of :func:`_accept_unigram` (minus the guards that need
    context) so filler words ("postal", "code", "or") never have to be matched for
    the input to count as fully covered.
    """
    if not word:
        return False
    if word.isdigit():
        return len(word) == PLZ_LENGTH
    if len(word) == AMBIGUOUS_ABBREVIATION_LENGTH:
        return False
    return word[:1].isupper()


def _fully_covered(words: Sequence[str], matches: Sequence[_AliasMatch]) -> bool:
    """True when every place-name-shaped word is inside some match's span.

    Ordinary filler words ("postal", "code") never need to match; a leftover
    capitalised or postal-code-shaped word ("Oberland", "Airport") does.
    """
    expected = {i for i, w in enumerate(words) if _is_candidate_word(w)}
    covered = {i for m in matches for i in range(m.start, m.end)}
    return expected <= covered


def resolve_from_question(
    tree: LocationTree, question: str, prose: bool = True,
) -> ResolvedLocation | None:
    """Resolve a jurisdiction mentioned in ``question``, or None when unclear.

    Returns None when nothing survives the guards, or when two surviving matches
    are not on a single root-to-node path (e.g. "Basel or Zurich"), so the caller
    can ask the user instead of guessing. ``prose`` gates the sentence-initial
    capitalisation guard, which only makes sense for free-flowing text; a bare
    place name like "Zürich, Switzerland" is not prose and should not be
    rejected for starting the string. When ``prose`` is False the whole input
    is expected to name one place, so a leftover unmatched word ("Oberland" in
    "Zürich Oberland") means the scan should back off and let the caller (the
    resolver's GeoAdmin fallback) decide, rather than silently keeping just
    the part it recognised.
    """
    raw, words = _tokenize(question)
    kept = _keep(tree, _drop_contained(_alias_matches(tree, words)), raw, prose)
    if not kept:
        return None
    if not prose and not _fully_covered(words, kept):
        return None
    best = _most_specific(tree, kept)
    path = tree.path(best.nodes[0].id)
    if any(all(n.id not in path for n in m.nodes) for m in kept):
        return None
    return ResolvedLocation(
        location=best.nodes[0], path=path, method=METHOD,
        input_text=best.text, alternatives=tuple(best.nodes[1:]),
    )
