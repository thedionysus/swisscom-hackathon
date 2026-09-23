from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from swiss_grounding.corpus.models import SourceSpec


class SourceEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    publisher: str
    authority: Literal["federal_law", "cantonal_law", "municipal_law", "official_info", "institutional"]
    level: Literal["federal", "cantonal", "municipal"]
    extent_id: str
    connector: Literal["fedlex", "html"]
    tier: int = Field(ge=1, le=3)
    languages: tuple[Literal["de", "fr", "it", "en", "rm"], ...] = Field(min_length=1)
    config: dict[str, Any] = {}
    retrieved_via: str | None = None

    @model_validator(mode="after")
    def _connector_config(self) -> "SourceEntry":
        if self.connector == "html":
            for key in ("start_urls", "allow_prefixes"):
                if not self.config.get(key):
                    raise ValueError(f"source {self.id}: html connector needs config.{key}")
        if self.connector == "fedlex" and not self.config.get("sr_numbers"):
            raise ValueError(f"source {self.id}: fedlex connector needs config.sr_numbers")
        dupes = sorted({lang for lang in self.languages if self.languages.count(lang) > 1})
        if dupes:
            raise ValueError(f"source {self.id}: duplicate languages: {dupes}")
        return self

    def to_spec(self) -> SourceSpec:
        return SourceSpec(id=self.id, name=self.name, publisher=self.publisher, authority=self.authority,
                          level=self.level, extent_id=self.extent_id, connector=self.connector, tier=self.tier,
                          languages=tuple(self.languages), config=dict(self.config),
                          retrieved_via=self.retrieved_via)


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    sources: tuple[SourceEntry, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> "Manifest":
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source ids: {dupes}")
        return self

    @model_validator(mode="after")
    def _disjoint_prefixes(self) -> "Manifest":
        """Two sources crawling overlapping URL spaces would fight over who owns each document."""
        owned = [(s.id, _url_prefixes(s)) for s in self.sources]
        for i, (first_id, first) in enumerate(owned):
            for second_id, second in owned[i + 1:]:
                clash = next(((a, b) for a in first for b in second if a.startswith(b) or b.startswith(a)), None)
                if clash:
                    raise ValueError(f"sources {first_id} and {second_id} have overlapping URL prefixes: "
                                     f"{clash[0]!r} and {clash[1]!r}")
        return self


def _url_prefixes(source: SourceEntry) -> tuple[str, ...]:
    config = source.config
    return tuple(config.get("allow_prefixes") or ()) + tuple(config.get("pdf_allow_prefixes") or ())


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def select_sources(manifest: Manifest, tier: int, source_ids: tuple[str, ...] = ()) -> tuple[SourceSpec, ...]:
    """Sources at or below `tier`, in manifest order; `source_ids` narrows further when given."""
    if source_ids:
        known = {s.id for s in manifest.sources}
        unknown = sorted(set(source_ids) - known)
        if unknown:
            raise ValueError(f"unknown source ids: {unknown}")
    chosen = [s for s in manifest.sources if s.tier <= tier and (not source_ids or s.id in source_ids)]
    return tuple(s.to_spec() for s in chosen)
