"""The golden set (ADR 0016): hand-written probes with expected status, source and key fact."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# The sixteen topic areas of the challenge README, plus none for outside-scope probes.
Area = Literal["health_insurance", "taxes", "law", "waste", "moving", "permits", "pensions", "work",
               "school_holidays", "transport", "driving", "housing", "voting", "companies", "customs",
               "statistics", "none"]
GOLDEN_DIR = Path("evals/golden")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenExpect(_Strict):
    status: Literal["results", "needs_location", "outside_scope", "source_unavailable", "no_evidence"]
    place_statuses: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    key_fact: str | None = None

    @model_validator(mode="after")
    def _results_need_evidence(self) -> "GoldenExpect":
        if self.status == "results" and (not self.sources or not self.key_fact):
            raise ValueError("a results probe needs sources and a key_fact")
        return self


class GoldenProbe(_Strict):
    id: str = Field(min_length=2)
    question: str = Field(min_length=3)
    locations: tuple[str, ...] = ()
    language: Literal["de", "fr", "it", "rm", "en"]
    area: Area
    level: Literal["federal", "cantonal", "municipal", "none"]
    split: Literal["dev", "holdout"]
    tool: Literal["swiss_search", "swiss_premium", "swiss_connections", "swiss_reference_rate"] = "swiss_search"
    as_of: str | None = None
    note: str = ""
    expect: GoldenExpect


class GoldenSet(_Strict):
    version: str
    probes: tuple[GoldenProbe, ...]

    @model_validator(mode="after")
    def _unique(self) -> "GoldenSet":
        ids = [p.id for p in self.probes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate probe ids")
        return self


def load_golden(directory: Path = GOLDEN_DIR) -> GoldenSet:
    """All *.yaml files in the directory merged; they must share one version."""
    sets = [GoldenSet.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
            for p in sorted(directory.glob("*.yaml"))]
    versions = {s.version for s in sets}
    if len(versions) != 1:
        raise ValueError(f"golden files disagree on version: {sorted(versions)}")
    return GoldenSet(version=versions.pop(), probes=tuple(p for s in sets for p in s.probes))
