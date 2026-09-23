from datetime import UTC, datetime

import pytest

from swiss_grounding.corpus.describe import (
    build_chunk_tasks,
    build_doc_tasks,
    estimate_describe,
    mark_repeated_furniture,
    run_chunk_descriptions,
    run_doc_descriptions,
)
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import LlmOutcome, SyncRunner
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, tzinfo=UTC)
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "fr"),
                  config={"sr_numbers": ["220"]})
CITY = SourceSpec(id="city", name="City", publisher="Stadtverwaltung", authority="official_info",
                  level="municipal", extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})
TEXT = {"de": "1 Nach Ablauf der Probezeit darf der Arbeitgeber nicht kündigen.",
        "fr": "1 Après le temps d'essai, l'employeur ne peut pas résilier le contrat."}
FOOTER = ParsedSection("de:9", ("Seite",), None, "Kontakt: Stadtverwaltung, Bundesgasse 1, 3011 Bern")


def _seed(conn):
    upsert_source(conn, SPEC)
    for lang in ("de", "fr"):
        persist_document(conn, ParsedDocument(
            source_id="fedlex", url=f"https://f/{lang}", language=lang, work_key="eli/220", title=f"OR {lang}",
            identifier="SR 220", sections=(ParsedSection("art_336_c", (f"SR 220 OR {lang}", "Art. 336c"), "art_336_c",
                                                         TEXT[lang]),)), SPEC, NOW)


def _seed_city_pages(conn, pages: int):
    upsert_source(conn, CITY)
    for i in range(pages):
        persist_document(conn, ParsedDocument(
            source_id="city", url=f"https://city/{i}", language="de", work_key=f"html:{i}", title=f"Seite {i}",
            sections=(ParsedSection("de:0", ("Seite",), None, f"Eigener Inhalt {i}."), FOOTER)), CITY, NOW)


def _responder(task):
    langs = ("de", "fr")
    if task.custom_id.startswith("doc|"):
        return {"descriptions": {lang: f"Obligationenrecht [{lang}]" for lang in langs},
                "topics": ["work", "business"]}
    return {"descriptions": {"de": "Kündigungsschutz bei Krankheit", "fr": "Protection contre le licenciement"},
            "topics": ["work"], "boilerplate": False}


class _ScriptedRunner:
    def __init__(self, outcomes):
        self._outcomes = outcomes
        self.calls = []

    def run(self, tasks, kind, estimated_usd=0.0):
        self.calls.append((len(tasks), kind, estimated_usd))
        yield from self._outcomes


def test_documents_then_chunks_are_described_in_each_language(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        doc_tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
        assert len(doc_tasks) == 1 and '"de"' in doc_tasks[0].user and '"fr"' in doc_tasks[0].user
        assert estimate_describe(doc_tasks, model="gpt-5-mini", languages_per_task=2) > 0
    runner = SyncRunner(FakeLLM(_responder), workers=1)
    assert run_doc_descriptions(corpus_db, runner, doc_tasks, model="gpt-5-mini", batch=False) == {"done": 1, "failed": 0}
    with connect(corpus_db) as conn:
        chunk_tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
        assert len(chunk_tasks) == 1                       # one task for the aligned DE+FR pair
        assert "Obligationenrecht [de]" in chunk_tasks[0].user
        assert 'starting guess is ["' in chunk_tasks[0].user   # the SR prior reaches the prompt
    run_chunk_descriptions(corpus_db, runner, chunk_tasks, model="gpt-5-nano", batch=False)
    with connect(corpus_db) as conn:
        rows = {r["language"]: r for r in conn.execute("select language, description, topics from corpus.chunk")}
        found = conn.execute("select count(*) as n from corpus.chunk "
                             "where tsv @@ to_tsquery('sg_french', 'licenciement')").fetchone()["n"]
        kinds = {r["kind"] for r in conn.execute("select kind from corpus.llm_spend")}
        assert build_chunk_tasks(conn, model="gpt-5-nano", limit=None) == []
        assert build_doc_tasks(conn, model="gpt-5-mini", limit=None) == []
    assert rows["de"]["description"] == "Kündigungsschutz bei Krankheit"
    assert rows["fr"]["description"] == "Protection contre le licenciement"
    assert rows["de"]["topics"] == ["work"]
    assert found == 1 and kinds == {"describe"}


def test_html_chunks_with_empty_topics_build_tasks(corpus_db):
    """A2: array_agg over empty text[] must not fail."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 1)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    assert len(tasks) == 2 and all("starting guess is []" in t.user for t in tasks)


def test_document_prompt_names_the_municipality(corpus_db):
    """A6: the jurisdiction comes from public.location.names labels (communes carry only 'de')."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 1)
        [task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    assert "applies to (Bern)" in task.user


def test_repeated_site_furniture_is_marked_before_describing(corpus_db):
    """RAG review E2: the same chunk on three pages of one site is furniture, found without a model call."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 3)
        assert mark_repeated_furniture(conn, min_documents=3) == 3
        statuses = {r["text"][:7]: r["status"] for r in conn.execute("select text, status from corpus.chunk")}
        assert len(build_chunk_tasks(conn, model="gpt-5-nano", limit=None)) == 3   # only the own-content chunks
    assert statuses["Kontakt"] == "boilerplate" and statuses["Eigener"] == "current"


def test_law_is_exempt_from_furniture_marking(corpus_db):
    law = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                     level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de",), config={})
    with connect(corpus_db) as conn:
        upsert_source(conn, law)
        for i in range(3):
            persist_document(conn, ParsedDocument(
                source_id="fedlex", url=f"https://f/{i}", language="de", work_key=f"eli/{i}", title=f"Act {i}",
                sections=(ParsedSection("art_1", ("Act", "Art. 1"), "art_1", "Aufgehoben"),)), law, NOW)
        assert mark_repeated_furniture(conn, min_documents=3) == 0


def test_furniture_marked_after_build_is_not_overwritten(corpus_db):
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 3)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
        mark_repeated_furniture(conn, min_documents=3)
        conn.commit()
    runner = SyncRunner(FakeLLM(lambda t: {"descriptions": {"de": "Beschreibung"}, "topics": [],
                                           "boilerplate": False}), workers=1)
    run_chunk_descriptions(corpus_db, runner, tasks, model="gpt-5-nano", batch=False)
    with connect(corpus_db) as conn:
        footer = conn.execute("select status, description from corpus.chunk where text like 'Kontakt%'").fetchall()
        own = conn.execute("select description from corpus.chunk where text like 'Eigener%'").fetchall()
    assert {(r["status"], r["description"]) for r in footer} == {("boilerplate", "")}
    assert {r["description"] for r in own} == {"Beschreibung"}


def test_boilerplate_chunks_leave_the_live_set(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    runner = SyncRunner(FakeLLM(lambda t: {"descriptions": {"de": "Menü", "fr": "Menu"}, "topics": [],
                                           "boilerplate": True}), workers=1)
    run_chunk_descriptions(corpus_db, runner, tasks, model="gpt-5-nano", batch=False)
    with connect(corpus_db) as conn:
        assert {r["status"] for r in conn.execute("select status from corpus.chunk")} == {"boilerplate"}


def test_failed_outcomes_record_spend_quarantine_and_stay_pending(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        [doc_task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
        [chunk_task] = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    doc_runner = _ScriptedRunner([LlmOutcome(doc_task.custom_id, None, 900, 100, error="unparseable reply")])
    chunk_runner = _ScriptedRunner([
        LlmOutcome(chunk_task.custom_id, {"descriptions": {"de": "nur deutsch"}, "topics": []}, 500, 60)])
    assert run_doc_descriptions(corpus_db, doc_runner, [doc_task], model="gpt-5-mini", batch=True,
                                estimated_usd=0.2) == {"done": 0, "failed": 1}
    assert run_chunk_descriptions(corpus_db, chunk_runner, [chunk_task], model="gpt-5-nano", batch=True,
                                  estimated_usd=0.1) == {"done": 0, "failed": 1}
    with connect(corpus_db) as conn:
        spend = conn.execute("select kind, input_tokens from corpus.llm_spend order by id").fetchall()
        stages = {r["stage"] for r in conn.execute("select stage from corpus.quarantine")}
        assert len(build_doc_tasks(conn, model="gpt-5-mini", limit=None)) == 1
        assert len(build_chunk_tasks(conn, model="gpt-5-nano", limit=None)) == 1
    assert doc_runner.calls == [(1, "describe-doc", 0.2)] and chunk_runner.calls == [(1, "describe-chunk", 0.1)]
    assert [(r["kind"], r["input_tokens"]) for r in spend] == [("describe", 900), ("describe", 500)]
    assert stages == {"describe-doc", "describe-chunk"}


def test_estimate_uses_batch_price_by_default(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    assert estimate_describe(tasks, model="gpt-5-mini", batch=False) == pytest.approx(
        2 * estimate_describe(tasks, model="gpt-5-mini"))
