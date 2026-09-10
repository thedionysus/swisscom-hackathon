import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from swiss_grounding.locations.models import LEVEL_DEPTH, Location


def normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace. Used for alias matching."""
    stripped = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in stripped if not unicodedata.combining(c))
    return " ".join(ascii_only.lower().split())


@dataclass(frozen=True)
class LocationTree:
    by_id: Mapping[str, Location]
    alias_index: Mapping[str, tuple[str, ...]]
    bfs_index: Mapping[int, str]

    @classmethod
    def from_locations(cls, locations: Iterable[Location]) -> "LocationTree":
        by_id = {loc.id: loc for loc in locations}
        alias_acc: dict[str, list[str]] = {}
        for loc in by_id.values():
            for name in loc.all_names():
                key = normalize(name)
                ids = alias_acc.setdefault(key, [])
                if loc.id not in ids:
                    ids.append(loc.id)
        alias_index = {k: tuple(v) for k, v in alias_acc.items()}
        bfs_index = {loc.bfs_id: loc.id for loc in by_id.values() if loc.bfs_id is not None}
        return cls(by_id=by_id, alias_index=alias_index, bfs_index=bfs_index)

    def get(self, location_id: str) -> Location:
        return self.by_id[location_id]

    def path(self, location_id: str) -> tuple[str, ...]:
        """Ancestor ids from root to the node, inclusive."""
        chain: list[str] = []
        current: str | None = location_id
        while current is not None:
            loc = self.by_id[current]
            chain.append(loc.id)
            current = loc.parent_id
        return tuple(reversed(chain))

    def distance(self, node_id: str, ancestor_id: str) -> int | None:
        """Number of steps from node up to ancestor; None if ancestor is not on the path."""
        p = self.path(node_id)
        if ancestor_id not in p:
            return None
        return len(p) - 1 - p.index(ancestor_id)

    def find(self, text: str) -> tuple[Location, ...]:
        """Exact alias match, most specific level first."""
        ids = self.alias_index.get(normalize(text), ())
        found = [self.by_id[i] for i in ids]
        found.sort(key=lambda loc: -LEVEL_DEPTH[loc.level])
        return tuple(found)

    def by_bfs_id(self, bfs_id: int) -> Location | None:
        location_id = self.bfs_index.get(bfs_id)
        return self.by_id[location_id] if location_id else None

    def all(self) -> tuple[Location, ...]:
        return tuple(self.by_id.values())
