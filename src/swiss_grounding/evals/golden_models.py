"""The golden set: hand-written probes with expected status, source and key fact."""
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The sixteen topic areas of the challenge README, plus none for outside-scope probes.
Area = Literal["health_insurance", "taxes", "law", "waste", "moving", "permits", "pensions", "work",
               "school_holidays", "transport", "driving", "housing", "voting", "companies", "customs",
               "statistics", "none"]
GOLDEN_DIR = Path("evals/golden")
SEARCH_TOOL = "swiss_search"
LOCAL_TOOLS = (SEARCH_TOOL, "swiss_get_document", "swiss_scope", "swiss_premium", "swiss_connections",
               "swiss_reference_rate")
REMOTE_PREFIX = "zbern_"   # tools proxied from zbern.ch, discovered at run time


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenExpect(_Strict):
    status: Literal["results", "needs_location", "outside_scope", "source_unavailable", "no_evidence",
                    "invalid_request"]
    place_statuses: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    key_fact: str | None = None
    # Exact checks for the non-search tools, on the tool's JSON output.
    contains: tuple[str, ...] = ()          # substrings of the JSON text
    nonempty: tuple[str, ...] = ()          # dotted paths that must hold a non-empty value
    value_path: str | None = None           # dotted path to a number, e.g. premiums.0.premium_chf
    value: float | None = None
    tolerance: float = 0.0

    @model_validator(mode="after")
    def _value_has_a_path(self) -> "GoldenExpect":
        if (self.value is None) != (self.value_path is None):
            raise ValueError("value and value_path go together")
        return self

    @property
    def has_tool_check(self) -> bool:
        return bool(self.contains or self.nonempty or self.value_path)


class GoldenProbe(_Strict):
    id: str = Field(min_length=2)
    question: str = Field(min_length=3)
    locations: tuple[str, ...] = ()
    language: Literal["de", "fr", "it", "rm", "en"]
    area: Area
    level: Literal["federal", "cantonal", "municipal", "none"]
    split: Literal["dev", "holdout"]
    tool: str = SEARCH_TOOL
    args: dict[str, Any] = Field(default_factory=dict)
    group: str | None = None                # probes asking the same thing in several languages
    as_of: str | None = None
    note: str = ""
    expect: GoldenExpect

    @field_validator("tool")
    @classmethod
    def _known_tool(cls, tool: str) -> str:
        if tool not in LOCAL_TOOLS and not (tool.startswith(REMOTE_PREFIX) and len(tool) > len(REMOTE_PREFIX)):
            raise ValueError(f"unknown tool {tool!r}")
        return tool

    @model_validator(mode="after")
    def _results_need_evidence(self) -> "GoldenProbe":
        if self.expect.status != "results":
            return self
        if self.tool == SEARCH_TOOL and (not self.expect.sources or not self.expect.key_fact):
            raise ValueError("a results probe needs sources and a key_fact")
        if self.tool != SEARCH_TOOL and not (self.expect.has_tool_check or self.expect.key_fact):
            raise ValueError("a tool results probe needs a check (contains, nonempty, value) or a key_fact")
        return self


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
