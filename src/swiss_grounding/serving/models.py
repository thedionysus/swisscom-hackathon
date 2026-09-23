"""Value types of the serving track. Everything here is immutable."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

Lang = Literal["de", "fr", "it", "en", "rm"]
LANGS: tuple[str, ...] = ("de", "fr", "it", "en", "rm")
MAX_LOCATIONS = 3
DEFAULT_LIMIT = 8
MAX_LIMIT = 20

Status = Literal["results", "needs_location", "outside_scope", "source_unavailable",
                 "no_evidence", "invalid_request"]
# When several places disagree, the response's top-level status is the most informative one.
STATUS_PRIORITY: tuple[str, ...] = ("results", "outside_scope", "needs_location",
                                    "source_unavailable", "no_evidence", "invalid_request")
NOTICE = "Retrieved public information from Swiss sources. Not legal advice."


def overall_status(statuses: Sequence[str]) -> str:
    return min(statuses, key=STATUS_PRIORITY.index) if statuses else "no_evidence"


@dataclass(frozen=True)
class SearchRequest:
    question: str
    locations: tuple[str, ...] = ()
    translations: Mapping[str, str] = field(default_factory=dict)
    as_of: date | None = None
    limit: int = DEFAULT_LIMIT

    def __post_init__(self) -> None:
        if len(self.locations) > MAX_LOCATIONS:
            raise ValueError(f"at most {MAX_LOCATIONS} locations per search")
        clean = {k: v.strip() for k, v in self.translations.items() if k in LANGS and v and v.strip()}
        object.__setattr__(self, "translations", clean)
        object.__setattr__(self, "limit", max(1, min(self.limit, MAX_LIMIT)))


@dataclass(frozen=True)
class Candidate:
    """One chunk found by at least one arm, with what citing it needs."""
    chunk_id: int
    language: str
    document_id: int
    translation_group_id: str
    align_key: str
    extent_id: str
    authority: str
    url: str
    anchor: str | None
    title: str
    publisher: str
    breadcrumb: tuple[str, ...]
    text: str
    is_authentic: bool
    valid_from: date | None
    valid_to: date | None
    modified_at: date | None
    fetched_at: datetime
    extraction: str
    rrf: float = 0.0
    rrf_rank: int = 0
    arms: frozenset[str] = frozenset()
    query_langs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GroupHit:
    """A translation group's candidates at one align key, scored through one representative."""
    representative: Candidate
    others: tuple[Candidate, ...]
    corroboration: float | None
    corroboration_basis: str | None
    versions_diverge: bool


@dataclass(frozen=True)
class ScoredGroup:
    group: GroupHit
    rerank_score: float
    relevance: float
    tier: int | None


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    title: str
    url: str
    anchor: str | None
    breadcrumb: tuple[str, ...]
    passage: str
    language: str
    other_languages: tuple[str, ...]
    publisher: str
    authority: str
    extent_id: str
    extent_label: str
    tier: int | None
    relevance: float
    corroboration: float | None
    corroboration_basis: str | None
    versions_diverge: bool
    valid_from: date | None
    modified_at: date | None
    fetched_at: datetime
    extraction: str


@dataclass(frozen=True)
class CoverageRow:
    extent_id: str
    label: str
    documents: int


@dataclass(frozen=True)
class PlaceResult:
    place: str | None
    status: Status
    location_id: str | None = None
    location_label: str | None = None
    message: str = ""
    citations: tuple[Citation, ...] = ()
    coverage: tuple[CoverageRow, ...] = ()
    uncovered_levels: tuple[str, ...] = ()
    """Levels of the place outside the declared scope ("cantonal", "municipal"); ADR 0013 step 3."""


@dataclass(frozen=True)
class SearchResponse:
    status: str
    places: tuple[PlaceResult, ...]
    message: str = ""
    scope: str = ""
    notice: str = NOTICE
    field: str | None = None
