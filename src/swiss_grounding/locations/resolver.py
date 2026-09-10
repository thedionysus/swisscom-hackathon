import re
from typing import Protocol

from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.locations.tree import LocationTree

CANTON_IN_LABEL = re.compile(r"\(([A-Z]{2})\)\s*$")


class CommuneSearch(Protocol):
    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]: ...


class LocationResolver:
    """Alias match against the tree first; GeoAdmin as fallback. Never guesses."""

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
        return self._resolve_via_geoadmin(cleaned)

    def _resolve_via_geoadmin(self, text: str) -> ResolvedLocation | None:
        try:
            hits = self._geo.search_communes(text)
        except RuntimeError:
            return None
        if not hits:
            return None
        hit = hits[0]
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
