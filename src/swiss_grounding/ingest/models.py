from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


@dataclass(frozen=True)
class Section:
    heading_path: str
    anchor: str | None
    text: str


@dataclass(frozen=True)
class FetchedDocument:
    """One fetched unit in its original language. Never touches the database."""
    source_id: str
    url: str
    title: str
    language: str
    sections: tuple[Section, ...]
    identifier: str | None = None
    published_at: datetime | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    in_force: bool | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class KnownUrl:
    """What we already know about a URL from a previous run, for conditional requests."""
    etag: str | None
    last_modified: str | None
    content_hash: str


@dataclass(frozen=True)
class FetchError:
    url: str
    reason: str


@dataclass(frozen=True)
class FetchResult:
    documents: tuple[FetchedDocument, ...]
    unchanged_urls: tuple[str, ...] = ()
    gone_urls: tuple[str, ...] = ()
    errors: tuple[FetchError, ...] = ()


@dataclass(frozen=True)
class CategoryTag:
    id: str
    confidence: float


@dataclass(frozen=True)
class EnrichedDocument:
    fetched: FetchedDocument
    title_en: str
    sections_en: tuple[Section, ...]
    extent_id: str
    extent_reason: str
    categories: tuple[CategoryTag, ...]


@dataclass(frozen=True)
class ChunkDraft:
    ordinal: int
    heading_path: str
    anchor: str | None
    text_original: str
    text_en: str


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    WITHDRAWN = "withdrawn"
