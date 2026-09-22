"""Backfilling stored chunks with generated context and per-chunk topics (ADR 0005, ADR 0003).

The backfill spends real money on the live index -- one description call per chunk -- so these
tests are as much about what is *not* called and what survives a failure as about the text
written. `FakeLLM` stands in for the model; `ForbiddenLLM` stands in for "this must cost
nothing".
"""

import json
import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.context import indexed_text
from swiss_grounding.ingest.errors import EnrichmentError
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.models import CategoryTag, ChunkContext
from swiss_grounding.ingest.recontext import (
    RECOVERED_CONFIDENCE,
    EmptiedDocument,
    SourceRecontext,
    recontext_all,
)
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
DIM = 8
# What Fedlex's five declared categories wrote onto all 563 of its chunks: the defect of ADR 0003.
STALE_TOPICS = ["hiking", "waste", "dogs", "safety", "transport"]


def _embedder() -> FakeEmbedder:
    return FakeEmbedder(dim=DIM)


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=DIM)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, _embedder())
        # The stored corpus as the backfill finds it: every chunk carrying its source's declared
        # categories and no generated context at all, and every document carrying the same union
        # in the shape `persist` writes it.
        conn.execute("update chunk set categories = %s, context_en = ''", (STALE_TOPICS,))
        conn.execute("update document set categories = %s::jsonb", (json.dumps(
            [{"id": topic, "confidence": 0.9} for topic in STALE_TOPICS]),))
    return u


class RecordingLLM(FakeLLM):
    """Describes everything, and remembers what it was asked, so a test can count the bill."""

    def __init__(self, furniture: tuple[str, ...] = (), breaks_on: str | None = None,
                 topic: str = "dogs", breaks_always: bool = False):
        self.summarised: list[str] = []
        self.described: list[dict] = []
        self._furniture = furniture
        self._breaks_on = breaks_on
        self._topic = topic
        self._breaks_always = breaks_always

    def summarise(self, title_en, text_en):
        self.summarised.append(title_en)
        return f"a summary of {title_en}"

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        if self._breaks_always or heading_path == self._breaks_on:
            raise EnrichmentError(f"unusable reply for {heading_path!r}")
        self.described.append({"heading": heading_path, "text_original": text_original})
        return ChunkContext(context_en=f"From {summary_en}. Covers {heading_path}.",
                            topics=(CategoryTag(self._topic, 0.8),),
                            boilerplate=heading_path in self._furniture)


class ResamplingLLM(RecordingLLM):
    """A model whose first reply about one chunk is unusable, so the client sends twice.

    `messages_sent` is what `AnthropicLLM` keeps: every message actually put on the wire,
    resamples included. One description of one chunk can cost two of them.
    """

    def __init__(self, resamples_on: str):
        super().__init__()
        self.messages_sent = 0
        self._resamples_on = resamples_on

    def summarise(self, title_en, text_en):
        self.messages_sent += 1
        return super().summarise(title_en, text_en)

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        self.messages_sent += 2 if heading_path == self._resamples_on else 1
        return super().describe(summary_en, heading_path, text_en, text_original, categories)


class ForbiddenLLM(FakeLLM):
    """Any call at all is the failure under test."""

    def summarise(self, title_en, text_en):
        raise AssertionError(f"summarise was called for {title_en!r}")

    def describe(self, summary_en, heading_path, text_en, text_original, categories):
        raise AssertionError(f"describe was called for {heading_path!r}")


def _add_chunk(conn, document_id: int, ordinal: int, heading: str, text_en: str,
               text_original: str | None = None) -> None:
    """Add one more chunk to a stored document, as a multi-article act has."""
    conn.execute(
        """
        insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor,
                           embedding, chunk_hash, extent_id, authority, categories)
        select %s, %s, %s, %s, %s, null, embedding, %s, extent_id, authority, %s
        from chunk where document_id = %s limit 1
        """,
        (document_id, ordinal, text_original or text_en, text_en, heading,
         f"hash-{document_id}-{ordinal}", STALE_TOPICS, document_id),
    )


def _chunks(conn, source_id: str | None = None) -> list[dict]:
    sql = ("select c.id, c.document_id, c.ordinal, c.heading_path, c.context_en, c.categories, "
           "c.text_en, c.embedding from chunk c join document d on d.id = c.document_id")
    if source_id:
        return conn.execute(f"{sql} where d.source_id = %s order by c.id", (source_id,)).fetchall()
    return conn.execute(f"{sql} order by c.id").fetchall()


def test_recontext_writes_context_and_replaces_the_stale_topics(url):
    with connect(url) as conn:
        report = recontext_all(conn, FakeLLM(), _embedder())
        rows = _chunks(conn)

    assert rows, "the fixture must leave chunks to describe"
    assert all(row["context_en"] for row in rows)
    assert all(sorted(row["categories"]) != sorted(STALE_TOPICS) for row in rows)
    assert report.examined == len(rows)
    assert report.updated == len(rows)
    assert (report.skipped, report.failed, report.deleted_chunks) == (0, 0, 0)


def test_recontext_reembeds_every_chunk_over_its_context_and_its_text(url):
    embedder = _embedder()
    with connect(url) as conn:
        before = {row["id"]: row["embedding"].to_list() for row in _chunks(conn)}
        recontext_all(conn, FakeLLM(), embedder)
        rows = _chunks(conn)

    for row in rows:
        expected = embedder.embed([indexed_text(row["context_en"], row["text_en"])])[0]
        assert row["embedding"].to_list() == pytest.approx(expected)
        assert row["embedding"].to_list() != pytest.approx(before[row["id"]])


def test_recontext_reports_per_source_and_counts_its_model_calls(url):
    with connect(url) as conn:
        report = recontext_all(conn, FakeLLM(), _embedder())

    fedlex = next(s for s in report.by_source if s.source_id == "fedlex")
    assert fedlex == SourceRecontext(
        source_id="fedlex", examined=2, updated=2, skipped=0, deleted_chunks=0,
        deleted_documents=0, failed=0, describe_calls=2, summary_calls=2,
    )
    assert [s.source_id for s in report.by_source] == sorted(s.source_id for s in report.by_source)
    assert report.describe_calls == report.examined


def test_recontext_counts_account_for_every_chunk_examined(url):
    with connect(url) as conn:
        report = recontext_all(conn, FakeLLM(), _embedder())

    for source in report.by_source:
        assert source.examined == (
            source.updated + source.skipped + source.deleted_chunks + source.failed
        )
    assert report.examined == report.updated + report.skipped + report.deleted_chunks + report.failed


def test_recontext_refreshes_the_documents_topic_roll_up(url):
    with connect(url) as conn:
        recontext_all(conn, FakeLLM(), _embedder())
        documents = conn.execute("select id, categories from document").fetchall()
        chunks = conn.execute("select document_id, categories from chunk").fetchall()

    on_chunks: dict[int, set[str]] = {}
    for chunk in chunks:
        on_chunks.setdefault(chunk["document_id"], set()).update(chunk["categories"])
    for document in documents:
        assert {t["id"] for t in document["categories"]} == on_chunks[document["id"]]


def test_a_chunk_that_already_has_a_context_is_not_described_again(url):
    with connect(url) as conn:
        recontext_all(conn, RecordingLLM(), _embedder())
        before = {row["id"]: row["context_en"] for row in _chunks(conn)}

    resumed = RecordingLLM()
    with connect(url) as conn:
        report = recontext_all(conn, resumed, _embedder())
        after = {row["id"]: row["context_en"] for row in _chunks(conn)}

    assert after == before
    assert resumed.described == []
    assert resumed.summarised == []
    assert report.skipped == report.examined
    assert (report.updated, report.describe_calls, report.summary_calls) == (0, 0, 0)


def test_force_describes_a_chunk_that_already_has_a_context(url):
    with connect(url) as conn:
        recontext_all(conn, RecordingLLM(), _embedder())

    redone = RecordingLLM()
    with connect(url) as conn:
        report = recontext_all(conn, redone, _embedder(), force=True)

    assert len(redone.described) == report.examined
    assert report.updated == report.examined
    assert report.skipped == 0


def test_a_dry_run_reports_the_bill_without_calling_the_model_or_writing_anything(url):
    with connect(url) as conn:
        before = [(row["id"], row["context_en"], row["categories"]) for row in _chunks(conn)]
        documents_before = conn.execute("select id, categories from document").fetchall()

    with connect(url) as conn:
        report = recontext_all(conn, ForbiddenLLM(), _embedder(), dry_run=True)

    with connect(url) as conn:
        after = [(row["id"], row["context_en"], row["categories"]) for row in _chunks(conn)]
        documents_after = conn.execute("select id, categories from document").fetchall()

    assert after == before
    assert documents_after == documents_before
    assert report.updated == report.examined
    assert report.describe_calls == report.examined
    assert report.summary_calls == len(documents_before)
    assert (report.failed, report.deleted_chunks, report.errors) == (0, 0, ())


def test_a_chunk_the_model_calls_furniture_is_deleted_rather_than_described(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Navigation panel",
                   text_en="Environment  Energy  Contact")

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(furniture=("Navigation panel",)), _embedder())
        headings = [row["heading_path"] for row in _chunks(conn, "zh_ch")]

    assert headings == ["Leinenpflicht"]
    zh = next(s for s in report.by_source if s.source_id == "zh_ch")
    assert (zh.examined, zh.updated, zh.deleted_chunks, zh.deleted_documents) == (2, 1, 1, 0)


def test_a_document_whose_every_chunk_was_furniture_is_deleted_when_deletion_is_asked_for(url):
    with connect(url) as conn:
        document = conn.execute(
            "select id, url from document where source_id = 'schweizer_wanderwege'").fetchone()
        heading = conn.execute(
            "select heading_path from chunk where document_id = %s", (document["id"],)).fetchone()
        conn.execute(
            "insert into document_change (run_id, document_id, change_type) values (%s, %s, %s)",
            ("test-run", document["id"], "added"),
        )

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(furniture=(heading["heading_path"],)),
                               _embedder(), delete_emptied=True)
        gone = conn.execute("select id from document where id = %s", (document["id"],)).fetchone()
        history = conn.execute(
            "select id from document_change where document_id = %s", (document["id"],)).fetchall()

    assert gone is None
    assert history == []
    wanderwege = next(s for s in report.by_source if s.source_id == "schweizer_wanderwege")
    assert (wanderwege.deleted_chunks, wanderwege.deleted_documents) == (1, 1)


def test_the_chunks_paid_for_before_a_failure_are_kept(url):
    with connect(url) as conn:
        document = conn.execute(
            "select id, url from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")
        _add_chunk(conn, document["id"], ordinal=2, heading="Third", text_en="Third article.")

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(breaks_on="Second"), _embedder())
        # Discard anything the backfill did not commit itself: what survives is what a run
        # killed at that moment would leave behind.
        conn.rollback()

    with connect(url) as conn:
        contexts = {row["heading_path"]: row["context_en"] for row in _chunks(conn, "zh_ch")}

    assert contexts["Leinenpflicht"] != ""
    assert contexts["Second"] == ""
    assert contexts["Third"] == ""
    zh = next(s for s in report.by_source if s.source_id == "zh_ch")
    assert (zh.examined, zh.updated, zh.failed) == (3, 1, 2)
    assert [e.url for e in report.errors] == [document["url"]]
    assert "Second" in report.errors[0].reason


def test_a_failed_document_keeps_its_previous_topics_and_the_run_goes_on(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(breaks_on="Second"), _embedder())
        topics = conn.execute(
            "select categories from document where id = %s", (document["id"],)).fetchone()

    assert sorted(t["id"] for t in topics["categories"]) == sorted(STALE_TOPICS)
    assert report.updated == report.examined - report.failed
    assert next(s for s in report.by_source if s.source_id == "fedlex").updated == 2


def test_a_document_titled_by_its_own_identifier_is_refused_before_any_call(url):
    with connect(url) as conn:
        conn.execute("update document set title_en = identifier where identifier is not null")
        conn.execute("update document set title_en = '' where source_id = 'ch_ch'")

    llm = RecordingLLM()
    with connect(url) as conn:
        report = recontext_all(conn, llm, _embedder())

    fedlex = next(s for s in report.by_source if s.source_id == "fedlex")
    ch_ch = next(s for s in report.by_source if s.source_id == "ch_ch")
    assert (fedlex.failed, fedlex.describe_calls, fedlex.summary_calls) == (2, 0, 0)
    assert (ch_ch.failed, ch_ch.describe_calls) == (2, 0)
    assert all("title" in e.reason for e in report.errors)
    assert next(s for s in report.by_source if s.source_id == "zh_ch").updated == 1


def test_a_templated_source_is_backfilled_without_one_model_call(url):
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        document = conn.execute(
            """
            insert into document (source_id, url, identifier, title_original, title_en, language,
                                  extent_id, authority, content_hash)
            values ('open_erz', 'https://openerz.metaodi.ch/api/calendar#cardboard-2026-09-25',
                    'cardboard-2026-09-25', 'Waste collection cardboard in 8003 on 2026-09-25',
                    'Waste collection cardboard in 8003 on 2026-09-25', 'en', 'CH-ZH-261-K3',
                    'official_info', 'test-open-erz-hash')
            returning id
            """
        ).fetchone()
        conn.execute(
            """
            insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor,
                               embedding, chunk_hash, extent_id, authority, categories)
            values (%s, 0, %s, %s, %s, null, %s, 'open-erz-chunk', 'CH-ZH-261-K3', 'official_info', %s)
            """,
            (document["id"], "Collection of cardboard on 2026-09-25.",
             "Collection of cardboard on 2026-09-25.", "Waste collection cardboard",
             _embedder().embed(["Collection of cardboard on 2026-09-25."])[0], STALE_TOPICS),
        )

    with connect(url) as conn:
        report = recontext_all(conn, ForbiddenLLM(), _embedder())
        chunk = _chunks(conn, "open_erz")[0]

    assert report.by_source == (
        SourceRecontext(source_id="open_erz", examined=1, updated=1, skipped=0, deleted_chunks=0,
                        deleted_documents=0, failed=0, describe_calls=0, summary_calls=0),
    )
    assert chunk["context_en"].startswith("From Open ERZ waste calendar")
    assert chunk["categories"] == ["waste"]


def test_a_split_section_is_described_from_its_english_alone(url):
    shared_original = "Wer ein Tier hält, muss es angemessen nähren."
    with connect(url) as conn:
        document = conn.execute(
            "select id from document where source_id = 'stadt_zuerich' "
            "order by id limit 1").fetchone()
        conn.execute("update chunk set text_original = %s where document_id = %s",
                     (shared_original, document["id"]))
        _add_chunk(conn, document["id"], ordinal=1, heading="Hunde in Parks",
                   text_en="The second half of the same section.", text_original=shared_original)

    llm = RecordingLLM()
    with connect(url) as conn:
        recontext_all(conn, llm, _embedder())

    described = {call["heading"]: call["text_original"] for call in llm.described}
    assert described["Hunde in Parks"] is None
    assert all(call["text_original"] is not None
               for call in llm.described if call["heading"] == "Leinenpflicht")


def test_an_emptied_document_is_left_standing_and_named_unless_deletion_is_asked_for(url):
    # Which chunks the model calls furniture is exactly what the dry run cannot preview, and
    # three live documents hold one chunk each. One verdict must not irreversibly erase a
    # document and its history without a preview, so deletion is opt-in and the rest is reported.
    with connect(url) as conn:
        document = conn.execute(
            "select id, url from document where source_id = 'schweizer_wanderwege'").fetchone()
        heading = conn.execute(
            "select heading_path from chunk where document_id = %s", (document["id"],)).fetchone()
        conn.execute(
            "insert into document_change (run_id, document_id, change_type) values (%s, %s, %s)",
            ("test-run", document["id"], "added"),
        )

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(furniture=(heading["heading_path"],)), _embedder())
        standing = conn.execute(
            "select id from document where id = %s", (document["id"],)).fetchone()
        chunks_left = _chunks(conn, "schweizer_wanderwege")
        history = conn.execute(
            "select id from document_change where document_id = %s", (document["id"],)).fetchall()

    assert standing is not None
    assert chunks_left == []
    assert history != []
    assert report.emptied == (EmptiedDocument(document_id=document["id"],
                                              source_id="schweizer_wanderwege",
                                              url=document["url"]),)
    wanderwege = next(s for s in report.by_source if s.source_id == "schweizer_wanderwege")
    assert (wanderwege.deleted_chunks, wanderwege.emptied_documents,
            wanderwege.deleted_documents) == (1, 1, 0)


def test_a_document_finished_by_a_later_run_gets_its_topic_roll_up(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")
        _add_chunk(conn, document["id"], ordinal=2, heading="Third", text_en="Third article.")

    with connect(url) as conn:
        recontext_all(conn, RecordingLLM(breaks_on="Second"), _embedder())
        stale = conn.execute(
            "select categories from document where id = %s", (document["id"],)).fetchone()

    with connect(url) as conn:
        resumed = recontext_all(conn, RecordingLLM(), _embedder())
        topics = conn.execute(
            "select categories from document where id = %s", (document["id"],)).fetchone()
        on_chunks = conn.execute(
            "select distinct unnest(categories) as topic from chunk where document_id = %s",
            (document["id"],)).fetchall()

    assert sorted(t["id"] for t in stale["categories"]) == sorted(STALE_TOPICS)
    assert resumed.failed == 0
    assert {t["id"] for t in topics["categories"]} == {row["topic"] for row in on_chunks}


def test_the_report_bills_a_description_the_client_had_to_resample_twice(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")

    with connect(url) as conn:
        report = recontext_all(conn, ResamplingLLM(resamples_on="Second"), _embedder())

    zh = next(s for s in report.by_source if s.source_id == "zh_ch")
    assert zh.examined == 2
    assert zh.updated == 2
    assert zh.describe_calls == 3      # two chunks, one of them sampled twice


def test_the_run_stops_once_three_documents_in_a_row_have_failed(url):
    # A dead API key answers 401 to every call. Without a breaker the run pays a summary and a
    # description for each of the remaining documents to be told the same thing every time.
    llm = RecordingLLM(breaks_always=True)
    with connect(url) as conn:
        documents = conn.execute("select count(*) as n from document").fetchone()["n"]
        report = recontext_all(conn, llm, _embedder())

    assert report.stopped_early is True
    assert len(llm.summarised) == 3
    assert report.not_attempted == documents - 3
    assert len(report.errors) == 3


def test_refusals_that_cost_nothing_never_stop_the_run(url):
    # The untitled guard refuses before any call, so a corpus of them is a data condition to be
    # listed in full, not a systemic failure to abort on.
    with connect(url) as conn:
        conn.execute("update document set title_en = ''")

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(), _embedder())

    assert report.stopped_early is False
    assert report.not_attempted == 0
    assert report.failed == report.examined
    assert len(report.errors) == 8


def test_a_document_that_fails_while_being_finished_is_reported_not_raised(url, monkeypatch):
    from swiss_grounding.ingest import recontext as module

    real = module._roll_up
    seen: list[int] = []

    def flaky(conn, document, kept):
        seen.append(document.id)
        if len(seen) == 1:
            raise RuntimeError("roll-up exploded")
        return real(conn, document, kept)

    monkeypatch.setattr(module, "_roll_up", flaky)
    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(), _embedder())
        contexts = [row["context_en"] for row in _chunks(conn)]

    assert all(contexts)                       # every chunk was described and committed anyway
    assert [e.reason for e in report.errors if "roll-up exploded" in e.reason]
    assert report.updated == report.examined
    assert report.stopped_early is False


def test_a_rollback_that_itself_fails_does_not_end_the_run(url):
    class BrittleConnection:
        """A connection that cannot even roll back, as a dead one cannot."""

        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def rollback(self):
            raise RuntimeError("the connection is gone")

    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")

    with connect(url) as conn:
        report = recontext_all(BrittleConnection(conn), RecordingLLM(breaks_on="Second"),
                               _embedder())

    assert report.failed == 1
    assert next(s for s in report.by_source if s.source_id == "fedlex").updated == 2


def test_every_document_reports_its_progress_as_the_run_goes(url):
    seen = []
    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(), _embedder(), on_document=seen.append)

    assert len(seen) == 8
    assert (seen[0].index, seen[0].total) == (1, 8)
    assert all(p.source_id and p.url for p in seen)
    assert [p.calls_so_far for p in seen] == sorted(p.calls_so_far for p in seen)
    assert seen[-1].calls_so_far == report.describe_calls + report.summary_calls


def test_a_markdown_heading_left_in_a_title_never_reaches_a_prompt(url):
    # One stored title is `# On the Road with the Kids`; the summary quotes the title and every
    # chunk repeats the summary, so the artefact would land in nine chunks' context.
    with connect(url) as conn:
        conn.execute("update document set title_en = %s where source_id = 'schweizer_wanderwege'",
                     ("# On the Road with the Kids",))

    llm = RecordingLLM()
    with connect(url) as conn:
        recontext_all(conn, llm, _embedder())
        contexts = [row["context_en"] for row in _chunks(conn, "schweizer_wanderwege")]

    assert "On the Road with the Kids" in llm.summarised
    assert not any("#" in title for title in llm.summarised)
    assert not any("#" in context for context in contexts)


def test_a_topic_described_by_an_earlier_run_is_rolled_up_below_certainty(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")
        _add_chunk(conn, document["id"], ordinal=2, heading="Third", text_en="Third article.")

    with connect(url) as conn:
        recontext_all(conn, RecontextLLM_dogs := RecordingLLM(breaks_on="Second"), _embedder())
        assert RecontextLLM_dogs.described

    with connect(url) as conn:
        recontext_all(conn, RecordingLLM(topic="hiking"), _embedder())
        topics = conn.execute(
            "select categories from document where id = %s", (document["id"],)).fetchone()

    # `dogs` comes from the chunk described by the first run: the chunk still asserts it, but the
    # confidence the model gave it was dropped when the chunk was stored.
    assert topics["categories"] == [
        {"id": "hiking", "confidence": 0.8},
        {"id": "dogs", "confidence": RECOVERED_CONFIDENCE},
    ]


def test_an_emptied_document_left_standing_asserts_no_topics(url):
    with connect(url) as conn:
        document = conn.execute(
            "select id from document where source_id = 'schweizer_wanderwege'").fetchone()
        heading = conn.execute(
            "select heading_path from chunk where document_id = %s", (document["id"],)).fetchone()

    with connect(url) as conn:
        recontext_all(conn, RecordingLLM(furniture=(heading["heading_path"],)), _embedder())
        topics = conn.execute(
            "select categories from document where id = %s", (document["id"],)).fetchone()

    assert topics["categories"] == []


def test_a_failure_names_the_chunk_it_happened_on(url):
    with connect(url) as conn:
        document = conn.execute("select id from document where source_id = 'zh_ch'").fetchone()
        _add_chunk(conn, document["id"], ordinal=1, heading="Second", text_en="Second article.")
        chunk_id = conn.execute(
            "select id from chunk where document_id = %s and heading_path = 'Second'",
            (document["id"],)).fetchone()["id"]

    with connect(url) as conn:
        report = recontext_all(conn, RecordingLLM(breaks_on="Second"), _embedder())

    assert f"chunk {chunk_id}" in report.errors[0].reason
