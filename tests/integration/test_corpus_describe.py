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
DONE_1 = {"done": 1, "failed": 0, "skipped": 0}
FAILED_1 = {"done": 0, "failed": 1, "skipped": 0}
SKIPPED_1 = {"done": 0, "failed": 0, "skipped": 1}


def _seed(conn):
    upsert_source(conn, SPEC)
    for lang in ("de", "fr"):
        persist_document(conn, ParsedDocument(
            source_id="fedlex", url=f"https://f/{lang}", language=lang, work_key="eli/220", title=f"OR {lang}",
            identifier="SR 220", sections=(ParsedSection("art_336_c", (f"SR 220 OR {lang}", "Art. 336c"), "art_336_c",
                                                         TEXT[lang]),)), SPEC, NOW)


def _seed_city_pages(conn, pages: int, work_key=lambda i: f"html:{i}"):
    upsert_source(conn, CITY)
    for i in range(pages):
        persist_document(conn, ParsedDocument(
            source_id="city", url=f"https://city/{i}", language="de", work_key=work_key(i), title=f"Seite {i}",
            sections=(ParsedSection("de:0", ("Seite",), None, f"Eigener Inhalt {i}."), FOOTER)), CITY, NOW)


def _describe_groups(conn):
    """Stand-in for the document pass: chunks wait for their group's description."""
    conn.execute("""update corpus.translation_group set description_by_lang = '{"de": "Seite"}'""")


def _responder(task):
    langs = ("de", "fr")
    if task.custom_id.startswith("doc|"):
        return {"descriptions": {lang: f"Obligationenrecht [{lang}]" for lang in langs},
                "topics": ["work", "business"]}
    return {"descriptions": {"de": "Kündigungsschutz bei Krankheit", "fr": "Protection contre le licenciement"},
            "topics": ["work"], "boilerplate": False}


def _describe_documents(corpus_db):
    with connect(corpus_db) as conn:
        doc_tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    run_doc_descriptions(corpus_db, SyncRunner(FakeLLM(_responder), workers=1), doc_tasks, model="gpt-5-mini",
                         batch=False)


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
        assert build_chunk_tasks(conn, model="gpt-5-nano", limit=None) == []   # waits for the document pass
        assert len(doc_tasks) == 1 and '"de"' in doc_tasks[0].user and '"fr"' in doc_tasks[0].user
        assert estimate_describe(doc_tasks, model="gpt-5-mini") > 0
    runner = SyncRunner(FakeLLM(_responder), workers=1)
    assert run_doc_descriptions(corpus_db, runner, doc_tasks, model="gpt-5-mini", batch=False) == DONE_1
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


def test_prompts_name_the_exact_language_keys_and_caps_leave_room(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        [doc_task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    _describe_documents(corpus_db)
    with connect(corpus_db) as conn:
        [chunk_task] = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    for task in (doc_task, chunk_task):
        assert "Use exactly these keys: de, fr." in task.user
        assert '{"descriptions": {"de": "...", "fr": "..."}' in task.user
    assert doc_task.max_output_tokens == 200 * 2 + 150
    assert chunk_task.max_output_tokens == 180 * 2 + 150


def test_html_chunks_with_empty_topics_build_tasks(corpus_db):
    """A2: array_agg over empty text[] must not fail."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 1)
        _describe_groups(conn)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    assert len(tasks) == 2 and all("starting guess is []" in t.user for t in tasks)


def test_document_prompt_names_the_municipality(corpus_db):
    """A6: the jurisdiction comes from public.location.names labels (communes carry only 'de')."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 1)
        [task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    assert "applies to (Bern)" in task.user


def test_document_excerpt_leaves_out_boilerplate(corpus_db):
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 3)
        mark_repeated_furniture(conn, min_documents=3)
        tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    assert len(tasks) == 3 and not any("Bundesgasse" in t.user for t in tasks)
    assert all("Eigener Inhalt" in t.user for t in tasks)


def test_duplicate_same_language_chunks_are_described_one_per_task(corpus_db):
    """Two current German documents in one group (undated, versioned by URL): one chunk per language per task,
    written back by id; the left-out duplicate is picked up on the next build."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 2, work_key=lambda i: "html:shared")
        _describe_groups(conn)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
        newest = conn.execute("select max(document_id) as d from corpus.chunk").fetchone()["d"]
        assert len(tasks) == 2 and all(t.user.count('"de": {') == 1 for t in tasks)
    runner = SyncRunner(FakeLLM(lambda t: {"descriptions": {"de": "Erste Runde"}, "topics": []}), workers=1)
    assert run_chunk_descriptions(corpus_db, runner, tasks, model="gpt-5-nano", batch=False)["done"] == 2
    with connect(corpus_db) as conn:
        described = {r["document_id"] for r in conn.execute(
            "select document_id from corpus.chunk where description <> ''")}
        again = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    assert described == {newest} and len(again) == 2


def test_repeated_site_furniture_is_marked_before_describing(corpus_db):
    """RAG review E2: the same chunk on three pages of one site is furniture, found without a model call."""
    with connect(corpus_db) as conn:
        _seed_city_pages(conn, 3)
        _describe_groups(conn)
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
        _describe_groups(conn)
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
    _describe_documents(corpus_db)
    with connect(corpus_db) as conn:
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
        _describe_groups(conn)
        [chunk_task] = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
        conn.execute("update corpus.translation_group set description_by_lang = '{}'::jsonb")
    doc_runner = _ScriptedRunner([LlmOutcome(doc_task.custom_id, None, 900, 100, error="unparseable reply")])
    chunk_runner = _ScriptedRunner([
        LlmOutcome(chunk_task.custom_id, {"descriptions": {"de": "nur deutsch"}, "topics": []}, 500, 60)])
    assert run_doc_descriptions(corpus_db, doc_runner, [doc_task], model="gpt-5-mini", batch=True,
                                estimated_usd=0.2) == FAILED_1
    assert run_chunk_descriptions(corpus_db, chunk_runner, [chunk_task], model="gpt-5-nano", batch=True,
                                  estimated_usd=0.1) == FAILED_1
    with connect(corpus_db) as conn:
        spend = conn.execute("select kind, input_tokens from corpus.llm_spend order by id").fetchall()
        stages = {r["stage"] for r in conn.execute("select stage from corpus.quarantine")}
        assert len(build_doc_tasks(conn, model="gpt-5-mini", limit=None)) == 1
        _describe_groups(conn)
        assert len(build_chunk_tasks(conn, model="gpt-5-nano", limit=None)) == 1
    assert doc_runner.calls == [(1, "describe-doc", 0.2)] and chunk_runner.calls == [(1, "describe-chunk", 0.1)]
    assert [(r["kind"], r["input_tokens"]) for r in spend] == [("describe", 900), ("describe", 500)]
    assert stages == {"describe-doc", "describe-chunk"}


def test_replayed_outcomes_are_skipped_without_spend(corpus_db):
    """A resumed batch can replay outcomes already ingested: no second spend row, nothing overwritten."""
    with connect(corpus_db) as conn:
        _seed(conn)
        [doc_task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    doc_outcome = LlmOutcome(doc_task.custom_id, _responder(doc_task), 900, 100)
    assert run_doc_descriptions(corpus_db, _ScriptedRunner([doc_outcome]), [doc_task], model="gpt-5-mini",
                                batch=True) == DONE_1
    assert run_doc_descriptions(corpus_db, _ScriptedRunner([doc_outcome]), [doc_task], model="gpt-5-mini",
                                batch=True) == SKIPPED_1
    with connect(corpus_db) as conn:
        [chunk_task] = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    chunk_outcome = LlmOutcome(chunk_task.custom_id, _responder(chunk_task), 500, 60)
    replay = LlmOutcome(chunk_task.custom_id, {"descriptions": {"de": "anders", "fr": "autre"}}, 500, 60)
    assert run_chunk_descriptions(corpus_db, _ScriptedRunner([chunk_outcome]), [chunk_task], model="gpt-5-nano",
                                  batch=True) == DONE_1
    assert run_chunk_descriptions(corpus_db, _ScriptedRunner([replay]), [chunk_task], model="gpt-5-nano",
                                  batch=True) == SKIPPED_1
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.llm_spend").fetchone()["n"] == 2
        descriptions = {r["description"] for r in conn.execute("select description from corpus.chunk")}
    assert descriptions == {"Kündigungsschutz bei Krankheit", "Protection contre le licenciement"}


def test_a_direct_call_outcome_is_priced_at_the_sync_rate_in_a_batch_run(corpus_db):
    """Batch and direct calls run side by side (HybridRunner); each outcome is priced by its own path."""
    from swiss_grounding.corpus.budget import cost_usd
    with connect(corpus_db) as conn:
        _seed(conn)
        [doc_task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    outcome = LlmOutcome(doc_task.custom_id, _responder(doc_task), 900, 100, sync=True)
    run_doc_descriptions(corpus_db, _ScriptedRunner([outcome]), [doc_task], model="gpt-5-mini", batch=True)
    with connect(corpus_db) as conn:
        usd = conn.execute("select usd from corpus.llm_spend").fetchone()["usd"]
    assert float(usd) == pytest.approx(cost_usd("gpt-5-mini", 900, 100, batch=False))


def test_estimate_uses_batch_price_by_default(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    assert estimate_describe(tasks, model="gpt-5-mini", batch=False) == pytest.approx(
        2 * estimate_describe(tasks, model="gpt-5-mini"))


def test_chunk_tasks_are_projected_before_documents_are_described(corpus_db):
    from swiss_grounding.corpus.describe import project_chunk_tasks
    with connect(corpus_db) as conn:
        _seed(conn)
        assert build_chunk_tasks(conn, model="gpt-5-nano", limit=None) == []
        count, usd = project_chunk_tasks(conn, model="gpt-5-nano")
    assert count == 1 and usd > 0
