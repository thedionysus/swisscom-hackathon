import re
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol

from swiss_grounding.locations.fuzzy import MIN_FUZZY_LENGTH, token_matches, tokens_covered
from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.markers import strip_marker
from swiss_grounding.locations.models import AmbiguousLocation, Level, Location, ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.tree import LocationTree, normalize

SCAN_METHOD = "alias_scan"
FUZZY_METHOD = "alias_fuzzy"
CANTON_IN_LABEL = re.compile(r"\(([A-Z]{2})\)\s*$")
LABEL_PUNCTUATION = "()[],.-"
MIN_OVERLAP_TOKEN_LENGTH = 3
COMMON_WORD_NEIGHBORHOODS = frozenset({"city", "hard", "werd", "enge", "affoltern"})
Resolution = ResolvedLocation | AmbiguousLocation | None


def _on_one_path(tree: LocationTree, nodes: Sequence[Location]) -> bool:
    deepest = max(nodes, key=lambda n: len(tree.path(n.id)))
    path = tree.path(deepest.id)
    return all(n.id in path for n in nodes)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(t for t in (w.strip(LABEL_PUNCTUATION) for w in normalize(text).split()) if t)


def _shares_a_token(text: str, label: str) -> bool:
    """True when at least one input token of length >= 3 exactly matches a label token.

    GeoAdmin is a fuzzy search: it answers "nowhere" with "Nidwalden". Requiring
    a shared token keeps genuine hits ("Zürich Oberland" -> "Zürich (ZH)") and
    drops hallucinated ones ("nowhere" -> "Nidwalden").
    """
    label_tokens = _tokens(label)
    return any(
        len(token) >= MIN_OVERLAP_TOKEN_LENGTH and token in label_tokens
        for token in _tokens(text)
    )


class CommuneSearch(Protocol):
    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]: ...


class LocationResolver:
    """Exact alias, then aliases found inside the text (e.g. a postal code next to a city
    name), then GeoAdmin. Never guesses."""

    def __init__(self, tree: LocationTree, geo: CommuneSearch):
        self._tree = tree
        self._geo = geo

    def resolve(self, text: str) -> Resolution:
        cleaned = text.strip()
        if not cleaned:
            return None
        level, name = strip_marker(cleaned)
        matches = self._tree.find(name)
        if level is not None:
            matches = tuple(m for m in matches if m.level is level)
        if matches:
            return self._from_alias_matches(cleaned, name, level, matches)
        scanned = resolve_from_question(self._tree, cleaned, prose=False)
        if scanned is not None:
            return replace(scanned, method=SCAN_METHOD, input_text=cleaned)
        return self._resolve_via_geoadmin(cleaned)

    def _from_alias_matches(
        self, cleaned: str, name: str, level: Level | None, matches: tuple[Location, ...],
    ) -> Resolution:
        if (
            level is None
            and normalize(name) in COMMON_WORD_NEIGHBORHOODS
            and all(m.level is Level.NEIGHBORHOOD for m in matches)
        ):
            return AmbiguousLocation(cleaned, matches, "a common word; say Quartier <name> to mean the district")
        if len(matches) > 1 and not _on_one_path(self._tree, matches):
            return AmbiguousLocation(cleaned, matches, "several places share this name")
        best = matches[0]
        return ResolvedLocation(
            location=best, path=self._tree.path(best.id), method="alias",
            input_text=cleaned, alternatives=tuple(matches[1:]),
        )

    def _resolve_via_geoadmin(self, text: str) -> Resolution:
        try:
            hits = self._geo.search_communes(text)
        except RuntimeError:
            return None
        if not hits:
            return self._resolve_fuzzy_alias(text)
        hit = hits[0]
        exact = self._tree.by_bfs_id(hit.bfs_id)
        if exact is not None and tokens_covered(text, hit.label):
            return ResolvedLocation(
                location=exact, path=self._tree.path(exact.id), method="geoadmin", input_text=text,
            )
        canton_match = CANTON_IN_LABEL.search(hit.label)
        if canton_match and _shares_a_token(text, hit.label):
            bare_label = hit.label[:canton_match.start()].strip()
            if (
                exact is None
                and not hit.bfs_id
                and normalize(text) == normalize(bare_label)
            ):
                # bfs 0 is GeoAdmin's sentinel for a non-commune feature (a lake, say);
                # when the input names exactly that feature, don't paper over it with a
                # canton guess, unlike a genuinely unlisted commune (nonzero bfs).
                return None
            canton = self._tree.find(canton_match.group(1))
            if canton:
                return ResolvedLocation(
                    location=canton[0], path=self._tree.path(canton[0].id),
                    method="geoadmin_approximate", input_text=text,
                )
        return self._resolve_fuzzy_alias(text)

    def _resolve_fuzzy_alias(self, text: str) -> Resolution:
        """Single-token inputs within one edit of exactly one alias resolve to it."""
        key = normalize(text)
        if " " in key or len(key) < MIN_FUZZY_LENGTH:
            return None
        candidates = {
            node_id
            for alias, ids in self._tree.alias_index.items()
            if " " not in alias and token_matches(key, alias)
            for node_id in ids
        }
        if len(candidates) != 1:
            return None
        node = self._tree.get(candidates.pop())
        return ResolvedLocation(
            location=node, path=self._tree.path(node.id), method=FUZZY_METHOD, input_text=text,
        )
