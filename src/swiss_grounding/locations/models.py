from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Level(StrEnum):
    COUNTRY = "country"
    CANTON = "canton"
    MUNICIPALITY = "municipality"
    NEIGHBORHOOD = "neighborhood"


LEVEL_DEPTH: Mapping[Level, int] = {
    Level.COUNTRY: 0,
    Level.CANTON: 1,
    Level.MUNICIPALITY: 2,
    Level.NEIGHBORHOOD: 3,
}


@dataclass(frozen=True)
class Location:
    id: str
    parent_id: str | None
    level: Level
    bfs_id: int | None
    lindas_uri: str | None
    names: Mapping[str, str]
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def label(self, lang: str = "en") -> str:
        return self.names.get(lang) or self.names.get("de") or next(iter(self.names.values()))

    def all_names(self) -> tuple[str, ...]:
        return tuple(self.names.values()) + self.aliases


@dataclass(frozen=True)
class ResolvedLocation:
    location: Location
    path: tuple[str, ...]
    method: str            # "alias" | "geoadmin" | "geoadmin_approximate"
    input_text: str
    alternatives: tuple[Location, ...] = field(default_factory=tuple)
