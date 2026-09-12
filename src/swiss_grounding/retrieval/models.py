from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from swiss_grounding.registry.models import Authority


@dataclass(frozen=True)
class ChunkRecord:
    """A chunk as loaded from the database, with the document fields needed for citation."""
    chunk_id: int
    document_id: int
    ordinal: int
    text_original: str
    text_en: str
    heading_path: str
    anchor: str | None
    extent_id: str
    authority: Authority
    categories: tuple[str, ...]
    url: str
    identifier: str | None
    title_original: str
    title_en: str
    language: str
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    source_id: str
    event_date: date | None = None


@dataclass(frozen=True)
class Hit:
    chunk: ChunkRecord
    rrf_score: float
    dense_rank: int | None
    lexical_rank: int | None


@dataclass(frozen=True)
class ScoredHit:
    hit: Hit
    score: float
    specificity: float
    category_overlap: float
    authority_score: float


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    source_id: str
    title_en: str
    title_original: str
    url: str
    anchor: str | None
    identifier: str | None
    snippet_en: str
    snippet_original: str
    language: str
    heading_path: str
    extent_id: str
    extent_label: str
    authority: str
    categories: tuple[str, ...]
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    score: float
    event_date: date | None = None      # calendar-style records: the date the event happens


@dataclass(frozen=True)
class QueryRequest:
    question: str
    location: str | None = None
    categories: tuple[str, ...] = ()
    as_of: date | None = None
    limit: int = 8


NOTICE = "Retrieved public information from Swiss sources. Not legal advice."


@dataclass(frozen=True)
class QueryResponse:
    status: Literal["results", "needs_location", "no_evidence", "invalid_request"]
    citations: tuple[Citation, ...] = ()
    resolved_location_id: str | None = None
    resolved_location_label: str | None = None
    resolution_method: str | None = None
    alternatives: tuple[str, ...] = ()
    message: str = ""
    field: str | None = None      # the offending request field when status is invalid_request
    notice: str = NOTICE
    categories_used: tuple[str, ...] = ()
