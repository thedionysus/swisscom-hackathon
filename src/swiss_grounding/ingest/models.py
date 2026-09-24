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
    event_date: date | None = None      # when the described event happens (calendar-style records)
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
class ChunkContext:
    """One model call's answer about one chunk.

    `context_en` is a short description of what the document is about and what this chunk covers.
    It is indexed with the text and never cited. `boilerplate` is the model's verdict that the
    chunk is page furniture rather than evidence, and the chunk is then dropped rather than stored.
    """
    context_en: str
    topics: tuple[CategoryTag, ...]
    boilerplate: bool


@dataclass(frozen=True)
class EnrichedDocument:
    """A fetched document translated to English and placed at an extent.

    It carries no categories: a document's topics are the roll-up of its chunks' own topics,
    which are decided after chunking, so `persist` derives them from the chunks it
    is writing rather than from a field that could disagree with them.
    """
    fetched: FetchedDocument
    title_en: str
    sections_en: tuple[Section, ...]
    extent_id: str
    extent_reason: str


@dataclass(frozen=True)
class ChunkDraft:
    """One chunk on its way to the index.

    `chunk_sections` produces it without `context_en` or `topics`; `context.describe_chunks`
    returns a copy carrying both. The defaults are what the two steps' split costs: they mirror
    `chunk.context_en`'s own `not null default ''`, so an undescribed draft persists as a chunk
    indexed on its text alone -- the behaviour before chunks had a context, never a crash or a null.
    """
    ordinal: int
    heading_path: str
    anchor: str | None
    text_original: str
    text_en: str
    # False when `text_original` is the whole section's and `text_en` only a slice of it, which
    # `chunking.chunk_sections` does deliberately so a citation can quote the original article.
    # A reader of the two as a *pair* -- the description call, which lifts untranslatable terms
    # out of the original -- must not be handed a text that does not correspond to this chunk.
    original_is_parallel: bool = True
    context_en: str = ""
    topics: tuple[CategoryTag, ...] = ()


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    WITHDRAWN = "withdrawn"
