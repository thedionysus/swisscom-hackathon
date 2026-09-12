import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import psycopg
from pydantic import BaseModel, ConfigDict

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.embedder import Embedder


class FixtureChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading_path: str = ""
    anchor: str | None = None
    text_original: str
    text_en: str


class FixtureDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    url: str
    identifier: str | None = None
    title_original: str
    title_en: str
    language: str
    extent_id: str
    authority: Authority
    categories: list[str] = []
    valid_from: date | None = None
    event_date: date | None = None
    chunks: list[FixtureChunk] = []


class Fixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[FixtureDocument]


@dataclass(frozen=True)
class LoadReport:
    documents: int
    chunks: int


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_fixture(conn: psycopg.Connection, path: Path, embedder: Embedder) -> LoadReport:
    """Insert fixture documents and chunks. Re-running with the same URL and content is a no-op."""
    fixture = Fixture.model_validate(json.loads(path.read_text()))
    known_sources = {r["id"] for r in conn.execute("select id from source").fetchall()}
    known_locations = {r["id"] for r in conn.execute("select id from location").fetchall()}
    docs_written = 0
    chunks_written = 0
    for doc in fixture.documents:
        if doc.source_id not in known_sources:
            raise ValueError(f"unknown source id {doc.source_id!r} in fixture {path}")
        if doc.extent_id not in known_locations:
            raise ValueError(f"unknown extent id {doc.extent_id!r} in fixture {path}")
        content_hash = _hash("\n".join(c.text_en for c in doc.chunks))
        existing = conn.execute(
            "select id from document where url = %s and content_hash = %s and status = 'current'",
            (doc.url, content_hash),
        ).fetchone()
        if existing:
            continue
        row = conn.execute(
            """
            insert into document (source_id, url, identifier, title_original, title_en, language,
                                  extent_id, authority, categories, valid_from, event_date, content_hash, origin)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, 'fixture') returning id
            """,
            (doc.source_id, doc.url, doc.identifier, doc.title_original, doc.title_en,
             doc.language, doc.extent_id, doc.authority.value, json.dumps(doc.categories),
             doc.valid_from, doc.event_date, content_hash),
        ).fetchone()
        document_id = row["id"]
        docs_written += 1
        vectors = embedder.embed([c.text_en for c in doc.chunks]) if doc.chunks else []
        for ordinal, (chunk, vector) in enumerate(zip(doc.chunks, vectors)):
            conn.execute(
                """
                insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor,
                                   embedding, chunk_hash, extent_id, authority, categories)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (document_id, ordinal, chunk.text_original, chunk.text_en, chunk.heading_path,
                 chunk.anchor, vector, _hash(chunk.text_en), doc.extent_id, doc.authority.value,
                 doc.categories),
            )
            chunks_written += 1
    return LoadReport(documents=docs_written, chunks=chunks_written)
