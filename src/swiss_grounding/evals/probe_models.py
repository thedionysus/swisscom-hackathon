"""Shape of a probe file. A probe states what the server should return and, once recorded,
what it returned. Evidence is named by source, URL fragment, or extent, never by database id."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

FailureClass = Literal[
    "jurisdiction_confusion",
    "authority_hierarchy",
    "temporal_misapplication",
    "entity_substitution",
    "silent_under_coverage",
    "none",
]
ProbeKind = Literal["structural", "ranking"]
ProbeStatus = Literal["red", "green"]
Tier = Literal["city", "communes", "lookalikes"]
ResponseStatus = Literal["results", "needs_location", "no_evidence", "invalid_request"]
FirstEventRule = Literal["nearest_future"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRule(_Strict):
    """Selects citations. All given selectors must match one citation for the rule to hit."""
    source: str | None = None
    url_contains: str | None = None
    extent: str | None = None          # extent id, or "off_path" for any extent off the resolved path
    authority: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "EvidenceRule":
        if not any((self.source, self.url_contains, self.extent, self.authority)):
            raise ValueError("an evidence rule needs at least one selector")
        return self


class ResolvedExpectation(_Strict):
    """Either an exact node id, or a label plus level plus parent for nodes that do not exist yet."""
    id: str | None = None
    label: str | None = None
    level: str | None = None
    parent: str | None = None

    @model_validator(mode="after")
    def _id_or_label(self) -> "ResolvedExpectation":
        if self.id is None and self.label is None:
            raise ValueError("resolved expectation needs id or label")
        return self


class Expectation(_Strict):
    status: ResponseStatus
    resolved: ResolvedExpectation | None = None
    method: str | None = None
    alternatives_include: tuple[str, ...] = ()
    must_include: tuple[EvidenceRule, ...] = ()
    must_exclude: tuple[EvidenceRule, ...] = ()
    first_extent: str | None = None
    first_authority: str | None = None
    first_url_contains: str | None = None
    first_event: FirstEventRule | None = None
    coverage_empty: tuple[str, ...] = ()
    coverage_present: tuple[str, ...] = ()
    message_contains: str | None = None


class ObservedCitation(_Strict):
    source: str
    extent: str
    url: str
    authority: str
    event_date: date | None = None


class Observed(_Strict):
    recorded_at: datetime
    git_commit: str | None = None
    status: str
    resolved_id: str | None = None
    method: str | None = None
    alternatives: tuple[str, ...] = ()
    message: str = ""
    citations: tuple[ObservedCitation, ...] = ()
    failures: tuple[str, ...] = ()


class Probe(_Strict):
    id: str
    question: str
    location: str | None = None
    categories: tuple[str, ...] = ()
    as_of: date | None = None
    limit: int = 8
    kind: ProbeKind
    failure_class: FailureClass
    status: ProbeStatus
    judge: bool = False
    note: str = ""
    expect: Expectation
    observed: Observed | None = None


class ProbeFile(_Strict):
    tier: Tier
    probes: tuple[Probe, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> "ProbeFile":
        ids = [p.id for p in self.probes]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate probe ids: {dupes}")
        return self
