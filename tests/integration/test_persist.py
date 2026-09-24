import os
from dataclasses import replace
from datetime import date

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.chunking import ChunkLimits, chunk_sections
from swiss_grounding.ingest.context import describe_chunks
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.models import CategoryTag, EnrichedDocument, FetchedDocument, Section
from swiss_grounding.ingest.persist import mark_withdrawn, persist_document, touch_unchanged
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
EMB = FakeEmbedder(dim=8)
DOGS = (CategoryTag("dogs", 1.0),)
URL = "https://www.fedlex.admin.ch/eli/cc/2008/414/20220101/de"


def enriched(texts, valid_from=date(2022, 1, 1), url=URL, title="Tierschutzgesetz"):
    sections = tuple(Section(f"Art. {i}", f"art_{i}", t) for i, t in enumerate(texts, 1))
    fetched = FetchedDocument(source_id="fedlex", url=url, title=title, language="de", sections=sections,
                              identifier="SR 455", valid_from=valid_from, in_force=True)
    return EnrichedDocument(fetched=fetched, title_en=title + " (EN)", sections_en=sections,
                            extent_id="CH", extent_reason="source_default")


def chunks_for(doc, topics=DOGS):
    """Chunk the document and hand every chunk the same topics, as `describe_chunks` would."""
    drafts = chunk_sections(doc.fetched.sections, doc.sections_en, ChunkLimits())
    return tuple(replace(c, context_en=f"From {doc.title_en}.", topics=topics) for c in drafts)


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document, fetch_state restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def test_first_persist_is_added(url):
    doc = enriched(["Zweck.", "Wer ein Tier hält."])
    with connect(url) as conn:
        outcome = persist_document(conn, doc, chunks_for(doc), EMB, run_id="r1")
        row = conn.execute("select status, version, valid_from, categories from document").fetchone()
        n_chunks = conn.execute("select count(*) as n from chunk").fetchone()["n"]
        change = conn.execute("select change_type, chunks_added from document_change").fetchone()
        state = conn.execute("select content_hash from fetch_state where url = %s", (URL,)).fetchone()
    assert outcome.change_type == "added" and outcome.document_id is not None
    assert row["status"] == "current" and row["version"] == 1 and row["valid_from"] == date(2022, 1, 1)
    # rolled up from the chunks, not asserted separately of the document
    assert row["categories"] == [{"id": "dogs", "confidence": 1.0}]
    assert n_chunks == 2 and change["change_type"] == "added" and len(change["chunks_added"]) == 2
    assert state is not None


def test_same_content_is_unchanged(url):
    doc = enriched(["Zweck.", "Wer ein Tier hält."])
    with connect(url) as conn:
        persist_document(conn, doc, chunks_for(doc), EMB, run_id="r1")
        outcome = persist_document(conn, enriched(["Zweck.", "Wer ein Tier hält."], title="New title"), chunks_for(doc), EMB, run_id="r2")
        docs = conn.execute("select count(*) as n from document").fetchone()["n"]
    assert outcome.change_type is None and docs == 1


def test_changed_content_creates_new_version_and_supersedes_old(url):
    v1 = enriched(["Zweck.", "Wer ein Tier hält."])
    v2 = enriched(["Zweck.", "Wer ein Tier hält, muss es pflegen.", "Neu: Art. 3."], valid_from=date(2024, 1, 1))
    with connect(url) as conn:
        first = persist_document(conn, v1, chunks_for(v1), EMB, run_id="r1")
        second = persist_document(conn, v2, chunks_for(v2), EMB, run_id="r2")
        old = conn.execute("select status, superseded_by, valid_to from document where id = %s", (first.document_id,)).fetchone()
        new = conn.execute("select status, version from document where id = %s", (second.document_id,)).fetchone()
        old_chunk_status = conn.execute("select distinct document_status from chunk where document_id = %s", (first.document_id,)).fetchall()
        change = conn.execute("select * from document_change where run_id = 'r2'").fetchone()
        current = conn.execute("select count(*) as n from document where url = %s and status = 'current'", (URL,)).fetchone()["n"]
    assert second.change_type == "modified"
    assert old["status"] == "superseded" and old["superseded_by"] == second.document_id
    assert old["valid_to"] == date(2024, 1, 1)
    assert new["status"] == "current" and new["version"] == 2
    assert old_chunk_status == [{"document_status": "superseded"}]
    assert change["previous_document_id"] == first.document_id
    assert len(change["chunks_added"]) == 1 and len(change["chunks_modified"]) == 1 and change["chunks_removed"] == []
    assert current == 1


def test_withdrawn_keeps_row_and_logs_change(url):
    doc = enriched(["Zweck."])
    with connect(url) as conn:
        first = persist_document(conn, doc, chunks_for(doc), EMB, run_id="r1")
        withdrawn = mark_withdrawn(conn, URL, run_id="r2")
        row = conn.execute("select status from document where id = %s", (first.document_id,)).fetchone()
        chunk_status = conn.execute("select distinct document_status from chunk where document_id = %s", (first.document_id,)).fetchall()
        state = conn.execute("select 1 from fetch_state where url = %s", (URL,)).fetchone()
        change = conn.execute("select change_type from document_change where run_id = 'r2'").fetchone()
    assert withdrawn is True and row["status"] == "withdrawn"
    assert chunk_status == [{"document_status": "withdrawn"}]
    assert state is None and change["change_type"] == "withdrawn"


def test_touch_unchanged_updates_retrieved_at(url):
    doc = enriched(["Zweck."])
    with connect(url) as conn:
        first = persist_document(conn, doc, chunks_for(doc), EMB, run_id="r1")
        conn.execute("update document set retrieved_at = '2000-01-01' where id = %s", (first.document_id,))
        touch_unchanged(conn, URL)
        year = conn.execute("select extract(year from retrieved_at) as y from document where id = %s", (first.document_id,)).fetchone()["y"]
    assert year > 2000


def test_withdrawn_unknown_url_is_false(url):
    with connect(url) as conn:
        assert mark_withdrawn(conn, "https://nowhere/x", run_id="r9") is False


def test_a_documents_categories_are_the_union_of_its_chunks(url):
    """Topic is decided per chunk; the document row must follow the chunks, not lead them."""
    doc = enriched(["Zweck.", "Wer ein Tier hält."])
    drafts = chunks_for(doc, topics=())
    chunks = (replace(drafts[0], topics=(CategoryTag("dogs", 0.4),)),
              replace(drafts[1], topics=(CategoryTag("dogs", 0.9), CategoryTag("waste", 0.2))))
    with connect(url) as conn:
        persist_document(conn, doc, chunks, EMB, run_id="r1")
        document = conn.execute("select categories from document").fetchone()
        stored = conn.execute("select categories from chunk order by ordinal").fetchall()
    assert document["categories"] == [{"id": "dogs", "confidence": 0.9}, {"id": "waste", "confidence": 0.2}]
    assert [c["categories"] for c in stored] == [["dogs"], ["dogs", "waste"]]


def test_each_chunk_keeps_its_own_context_and_topics(url):
    """The old defect was one tag set copied onto every chunk; this is the opposite."""
    doc = enriched(["Hunde.", "Karton."])
    drafts = chunks_for(doc, topics=())
    chunks = (replace(drafts[0], context_en="About dogs.", topics=(CategoryTag("dogs", 0.9),)),
              replace(drafts[1], context_en="About waste.", topics=(CategoryTag("waste", 0.9),)))
    with connect(url) as conn:
        persist_document(conn, doc, chunks, EMB, run_id="r1")
        rows = conn.execute("select context_en, categories from chunk order by ordinal").fetchall()
    assert [r["context_en"] for r in rows] == ["About dogs.", "About waste."]
    assert [r["categories"] for r in rows] == [["dogs"], ["waste"]]


def test_a_document_described_into_nothing_is_skipped(url):
    """Every chunk judged page furniture leaves no chunks at all: a skip, not a failure."""
    doc = enriched(["Navigation menu.", "Read page aloud."])
    sections = tuple(Section("Navigation", None, t) for t in ("Navigation menu.", "Read page aloud."))
    furniture = EnrichedDocument(fetched=replace(doc.fetched, sections=sections), title_en="Nav",
                                 sections_en=sections, extent_id="CH", extent_reason="source_default")
    described = describe_chunks(
        chunk_sections(sections, sections, ChunkLimits()),
        source=next(s for s in load_seed_sources() if s.id == "zh_ch"),
        title_en="Nav", document_text_en="Navigation menu.", llm=FakeLLM(), categories=CATEGORIES,
    )
    with connect(url) as conn:
        outcome = persist_document(conn, furniture, described.kept, EMB, run_id="r1")
        stored = conn.execute("select count(*) as n from document").fetchone()["n"]
    assert described.kept == () and len(described.dropped) == 2
    assert outcome.change_type == "skipped" and stored == 0
