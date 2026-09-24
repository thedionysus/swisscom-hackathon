from datetime import UTC, datetime

import pytest
from PIL import Image

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.ocr import OCR_PROMPT, build_ocr_tasks, estimate_ocr, run_ocr
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import LlmOutcome, SyncRunner
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
SPEC = SourceSpec(id="ahv", name="AHV", publisher="AHV/IV Informationsstelle", authority="official_info",
                  level="federal", extent_id="CH", connector="html", tier=1, languages=("de",), config={})


def _seed(conn, tmp_path):
    image = tmp_path / "p1.png"
    Image.new("RGB", (10, 10), "white").save(image)
    doc = ParsedDocument(source_id="ahv", url="https://ahv/m.pdf", language="de", work_key="pdf:https://ahv/m.pdf",
                         title="Merkblatt", extraction="pdf_text",
                         sections=(ParsedSection("de:p1", ("Merkblatt", "p. 1"), "page=1", "", needs_ocr=True,
                                                 ocr_image=str(image), ocr_digest="d1"),))
    upsert_source(conn, SPEC)
    persist_document(conn, doc, SPEC, datetime(2026, 9, 24, tzinfo=UTC))


class _ScriptedRunner:
    """Yields fixed outcomes and remembers what `run` was called with."""

    def __init__(self, outcomes):
        self._outcomes = outcomes
        self.calls = []

    def run(self, tasks, kind, estimated_usd=0.0):
        self.calls.append((len(tasks), kind, estimated_usd))
        yield from self._outcomes


def test_ocr_fills_text_and_marks_document(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        hash_before = conn.execute("select chunk_hash from corpus.chunk").fetchone()["chunk_hash"]
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
        assert len(tasks) == 1 and tasks[0].image_png_b64 and tasks[0].user == OCR_PROMPT
        assert tasks[0].max_output_tokens == 4000
        assert estimate_ocr(conn, model="gpt-5-mini") > 0
    runner = SyncRunner(FakeLLM(lambda t: {"text": "1 Die AHV-Rente wird berechnet."}), workers=1)
    report = run_ocr(corpus_db, runner, tasks, model="gpt-5-mini", batch=False)
    with connect(corpus_db) as conn:
        chunk = conn.execute("select text, needs_ocr, chunk_hash from corpus.chunk").fetchone()
        doc = conn.execute("select extraction from corpus.document").fetchone()
        spend = conn.execute("select kind from corpus.llm_spend").fetchone()
        assert build_ocr_tasks(conn, model="gpt-5-mini", limit=None) == []
    assert chunk["text"].startswith("1 Die AHV-Rente") and chunk["needs_ocr"] is False
    assert chunk["chunk_hash"] == hash_before           # identity stays the image digest
    assert doc["extraction"] == "ocr" and spend["kind"] == "ocr"
    assert report == {"done": 1, "failed": 0, "skipped": 0}


def test_nul_bytes_in_transcription_are_stripped(corpus_db, tmp_path):
    """PostgreSQL rejects NUL (0x00) in text; a scanned page's transcription can carry one."""
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    report = run_ocr(corpus_db, SyncRunner(FakeLLM(lambda t: {"text": "AHV\x00-Rente"}), workers=1), tasks,
                     model="gpt-5-mini", batch=False)
    with connect(corpus_db) as conn:
        assert conn.execute("select text from corpus.chunk").fetchone()["text"] == "AHV-Rente"
    assert report == {"done": 1, "failed": 0, "skipped": 0}


def test_empty_transcription_is_quarantined(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    report = run_ocr(corpus_db, SyncRunner(FakeLLM(lambda t: {"text": ""}), workers=1), tasks,
                     model="gpt-5-mini", batch=False)
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.quarantine where stage = 'ocr'").fetchone()["n"] == 1
        assert conn.execute("select needs_ocr from corpus.chunk").fetchone()["needs_ocr"] is True
    assert report == {"done": 0, "failed": 1, "skipped": 0}


def test_error_outcome_with_tokens_records_spend_and_quarantines(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    runner = _ScriptedRunner([LlmOutcome(tasks[0].custom_id, None, 1200, 300, error="unparseable reply: x")])
    report = run_ocr(corpus_db, runner, tasks, model="gpt-5-mini", batch=True, estimated_usd=0.5)
    with connect(corpus_db) as conn:
        spend = conn.execute("select kind, input_tokens from corpus.llm_spend").fetchall()
        reason = conn.execute("select reason from corpus.quarantine where stage = 'ocr'").fetchone()["reason"]
    assert runner.calls == [(1, "ocr", 0.5)]
    assert [(r["kind"], r["input_tokens"]) for r in spend] == [("ocr", 1200)]
    assert reason == "unparseable reply: x" and report == {"done": 0, "failed": 1, "skipped": 0}


def test_missing_batch_result_is_quarantined_without_spend(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    runner = _ScriptedRunner([LlmOutcome(tasks[0].custom_id, None, 0, 0, error="no result: batch b1 expired")])
    assert run_ocr(corpus_db, runner, tasks, model="gpt-5-mini", batch=True) == {"done": 0, "failed": 1, "skipped": 0}
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.llm_spend").fetchone()["n"] == 0


def test_estimate_uses_batch_price_by_default(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        batch_price = estimate_ocr(conn, model="gpt-5-mini")
        sync_price = estimate_ocr(conn, model="gpt-5-mini", batch=False)
    assert sync_price == pytest.approx(2 * batch_price)


def test_replayed_outcome_is_skipped_without_spend_or_quarantine(corpus_db, tmp_path):
    """A resumed batch can replay an outcome already ingested."""
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    outcome = LlmOutcome(tasks[0].custom_id, {"text": "Seite eins"}, 1200, 300)
    assert run_ocr(corpus_db, _ScriptedRunner([outcome]), tasks, model="gpt-5-mini", batch=True)["done"] == 1
    replay = LlmOutcome(tasks[0].custom_id, {"text": "anders"}, 1200, 300)
    assert run_ocr(corpus_db, _ScriptedRunner([replay]), tasks, model="gpt-5-mini", batch=True) == {
        "done": 0, "failed": 0, "skipped": 1}
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.llm_spend").fetchone()["n"] == 1
        assert conn.execute("select count(*) as n from corpus.quarantine").fetchone()["n"] == 0
        assert conn.execute("select text from corpus.chunk").fetchone()["text"] == "Seite eins"


def test_missing_page_image_is_quarantined_and_does_not_use_up_the_limit(corpus_db, tmp_path):
    image = tmp_path / "p2.png"
    Image.new("RGB", (10, 10), "white").save(image)
    gone = tmp_path / "gone.png"
    doc = ParsedDocument(source_id="ahv", url="https://ahv/m.pdf", language="de", work_key="pdf:https://ahv/m.pdf",
                         title="Merkblatt", extraction="pdf_text",
                         sections=(ParsedSection("de:p1", ("Merkblatt", "p. 1"), "page=1", "", needs_ocr=True,
                                                 ocr_image=str(gone), ocr_digest="d1"),
                                   ParsedSection("de:p2", ("Merkblatt", "p. 2"), "page=2", "", needs_ocr=True,
                                                 ocr_image=str(image), ocr_digest="d2")))
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, doc, SPEC, datetime(2026, 9, 24, tzinfo=UTC))
        conn.commit()
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=1)
    assert len(tasks) == 1 and tasks[0].image_png_b64
    with connect(corpus_db) as conn:
        rows = conn.execute("select source_id, stage, reason from corpus.quarantine").fetchall()
    assert [(r["source_id"], r["stage"], r["reason"]) for r in rows] == [("ocr", "ocr", f"page image missing: {gone}")]
