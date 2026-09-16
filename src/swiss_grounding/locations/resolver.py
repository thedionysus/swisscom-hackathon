import re
from dataclasses import replace
from typing import Protocol

from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.tree import LocationTree, normalize

SCAN_METHOD = "alias_scan"
CANTON_IN_LABEL = re.compile(r"\(([A-Z]{2})\)\s*$")
LABEL_PUNCTUATION = "()[],.-"
MIN_OVERLAP_TOKEN_LENGTH = 3


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(t for t in (w.strip(LABEL_PUNCTUATION) for w in normalize(text).split()) if t)


def overlaps(text: str, label: str) -> bool:
    """True when some input token of length >= 3 prefixes a token of the GeoAdmin label.

    GeoAdmin is a fuzzy search: it answers "nowhere" with "Nidwalden". Requiring
    a shared token stem keeps genuine hits ("uster" -> "Uster (ZH)") and drops
    hallucinated ones.
    """
    label_tokens = _tokens(label)
    return any(
        len(token) >= MIN_OVERLAP_TOKEN_LENGTH
        and any(candidate.startswith(token) for candidate in label_tokens)
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

    def resolve(self, text: str) -> ResolvedLocation | None:
        cleaned = text.strip()
        if not cleaned:
            return None
        matches = self._tree.find(cleaned)
        if matches:
            best = matches[0]
            return ResolvedLocation(
                location=best, path=self._tree.path(best.id), method="alias",
                input_text=cleaned, alternatives=tuple(matches[1:]),
            )
        scanned = resolve_from_question(self._tree, cleaned)
        if scanned is not None:
            return replace(scanned, method=SCAN_METHOD, input_text=cleaned)
        return self._resolve_via_geoadmin(cleaned)

    def _resolve_via_geoadmin(self, text: str) -> ResolvedLocation | None:
        try:
            hits = self._geo.search_communes(text)
        except RuntimeError:
            return None
        if not hits:
            return None
        hit = hits[0]
        if not overlaps(text, hit.label):
            return None
        exact = self._tree.by_bfs_id(hit.bfs_id)
        if exact is not None:
            return ResolvedLocation(
                location=exact, path=self._tree.path(exact.id), method="geoadmin", input_text=text,
            )
        canton_match = CANTON_IN_LABEL.search(hit.label)
        if canton_match:
            canton = self._tree.find(canton_match.group(1))
            if canton:
                return ResolvedLocation(
                    location=canton[0], path=self._tree.path(canton[0].id),
                    method="geoadmin_approximate", input_text=text,
                )
        return None
