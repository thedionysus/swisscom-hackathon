"""Value types that flow from connectors to persistence. None of them touches the database."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

Language = Literal["de", "fr", "it", "en", "rm"]
LANGUAGES: tuple[str, ...] = ("de", "fr", "it", "en", "rm")
DocStatus = Literal["current", "scheduled"]


@dataclass(frozen=True)
class SourceSpec:
    id: str
    name: str
    publisher: str
    authority: str
    level: str
    extent_id: str
    connector: str
    tier: int
    languages: tuple[str, ...]
    config: dict[str, Any] = field(default_factory=dict)
    retrieved_via: str | None = None


@dataclass(frozen=True)
class ParsedSection:
    """One structural unit: a law article, an HTML section, a PDF page.

    `align_key` is the position this section holds in its document's structure; for law it is
    the article's eId, which is the same in every language version, so aligned chunks share it.
    `paragraphs` holds (align_key, text) per paragraph for law articles, used to split long ones.
    """
    align_key: str
    breadcrumb: tuple[str, ...]
    anchor: str | None
    text: str
    paragraphs: tuple[tuple[str, str], ...] = ()
    needs_ocr: bool = False
    ocr_image: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    source_id: str
    url: str
    language: str
    work_key: str
    title: str
    sections: tuple[ParsedSection, ...]
    identifier: str | None = None
    is_authentic: bool = True
    valid_from: date | None = None
    valid_to: date | None = None
    status: DocStatus = "current"
    published_at: date | None = None
    modified_at: date | None = None
    extraction: str = "native"
    retrieved_via: str | None = None
    artifact_path: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class DiscoveredPdf:
    url: str
    language: str
    title_hint: str
    source_id: str


@dataclass(frozen=True)
class ConnectorResult:
    documents: tuple[ParsedDocument, ...] = ()
    unchanged_urls: tuple[str, ...] = ()
    gone_urls: tuple[str, ...] = ()
    errors: tuple[tuple[str, str], ...] = ()      # (url, reason)
    pdfs: tuple[DiscoveredPdf, ...] = ()


@dataclass(frozen=True)
class KnownState:
    etag: str | None
    last_modified: str | None
    content_hash: str


@dataclass(frozen=True)
class ChunkDraft:
    align_key: str
    ordinal: int
    breadcrumb: tuple[str, ...]
    anchor: str | None
    text: str
    needs_ocr: bool = False
    ocr_image: str | None = None


def content_hash(doc: ParsedDocument) -> str:
    """Hash of everything a reader sees: title, validity and every section.

    Status is excluded on purpose: a scheduled consolidation that comes into force changes status,
    not content, and persistence handles that as a status change rather than a new version.
    """
    payload = [doc.title, doc.valid_from.isoformat() if doc.valid_from else None,
               [[s.align_key, list(s.breadcrumb), s.text, s.ocr_image is not None] for s in doc.sections]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
