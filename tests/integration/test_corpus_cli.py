import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from PIL import Image
from typer.testing import CliRunner

from swiss_grounding.cli import corpus_commands
from swiss_grounding.cli.main import app
from swiss_grounding.corpus.budget import spent
from swiss_grounding.corpus.describe import build_doc_tasks
from swiss_grounding.corpus.embed import pending_for_index
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import INDEXES
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, tzinfo=UTC)
MANIFEST = """
version: 1
sources:
  - id: tiny
    name: Tiny
    publisher: Tiny
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 1
    languages: [de]
    config: {start_urls: ["http://127.0.0.1:9/"], allow_prefixes: ["http://127.0.0.1:9/"]}
"""
FEDLEX = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                    level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "fr"),
                    config={"sr_numbers": ["220"]})
AHV = SourceSpec(id="ahv", name="AHV", publisher="AHV/IV", authority="official_info", level="federal",
                 extent_id="CH", connector="html", tier=1, languages=("de",), config={})
TEXT = {"de": "1 Nach Ablauf der Probezeit darf der Arbeitgeber nicht kündigen.",
        "fr": "1 Après le temps d'essai, l'employeur ne peut pas résilier le contrat."}


def _seed_law(url):
    with connect(url) as conn:
        upsert_source(conn, FEDLEX)
        for lang in ("de", "fr"):
            persist_document(conn, ParsedDocument(
                source_id="fedlex", url=f"https://f/{lang}", language=lang, work_key="eli/220", title=f"OR {lang}",
                identifier="SR 220", sections=(ParsedSection("art_336_c", (f"SR 220 OR {lang}", "Art. 336c"),
                                                             "art_336_c", TEXT[lang]),)), FEDLEX, NOW)


def _seed_scan(url, tmp_path, pages=1):
    sections = []
    for n in range(1, pages + 1):
        image = tmp_path / f"p{n}.png"
        Image.new("RGB", (10, 10), "white").save(image)
        sections.append(ParsedSection(f"de:p{n}", ("Merkblatt", f"p. {n}"), f"page={n}", "", needs_ocr=True,
                                      ocr_image=str(image), ocr_digest=f"d{n}"))
    with connect(url) as conn:
        upsert_source(conn, AHV)
        persist_document(conn, ParsedDocument(
            source_id="ahv", url="https://ahv/m.pdf", language="de", work_key="pdf:https://ahv/m.pdf",
            title="Merkblatt", extraction="pdf_text", sections=tuple(sections)), AHV, NOW)


def _insert_batch(url, batch_id, kind, estimated=0.5):
    with connect(url) as conn:
        conn.execute("insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, "
                     "estimated_usd) values (%s, %s, '/v1/x', 'submitted', 1, 'in.jsonl', %s)",
                     (batch_id, kind, estimated))


def _no_openai(monkeypatch):
    def refuse(settings):
        raise AssertionError("an OpenAI client must not be built when CORPUS_LLM_PROVIDER=fake")
    monkeypatch.setattr(corpus_commands, "_openai_client", refuse)


class _FinishedBatches:
    """An OpenAI client whose batches already finished: `outputs` maps a batch id to its result lines."""

    def __init__(self, outputs: dict[str, list[dict]]):
        self.created: list = []
        outer = self

        class Batches:
            def retrieve(self, batch_id):
                return SimpleNamespace(status="completed", output_file_id=f"out-{batch_id}", error_file_id=None,
                                       errors=None)

            def create(self, **kwargs):
                outer.created.append(kwargs)
                raise AssertionError("no new batch expected")

        class Files:
            def content(self, file_id):
                lines = outputs[file_id.removeprefix("out-")]
                return SimpleNamespace(text="\n".join(json.dumps(line) for line in lines))

            def create(self, file, purpose):
                raise AssertionError("no upload expected")

        self.batches = Batches()
        self.files = Files()


def _openai_mode(monkeypatch, client, tmp_path):
    monkeypatch.setenv("CORPUS_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(corpus_commands, "_openai_client", lambda settings: client)


def _invoke(*args):
    return CliRunner().invoke(app, ["corpus", *args])


def test_init_status_and_estimate_run(corpus_db):
    assert _invoke("init").exit_code == 0
    status = _invoke("status")
    assert status.exit_code == 0 and "spend" in status.output.lower()
    assert _invoke("estimate").exit_code == 0


def test_check_manifest_reports_an_unreachable_start_url(corpus_db, tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    result = _invoke("check-manifest", str(path))
    assert result.exit_code == 1 and "tiny" in result.output


def test_describe_dry_run_spends_nothing(corpus_db):
    result = _invoke("describe", "--what", "chunks", "--dry-run")
    assert result.exit_code == 0 and "estimate" in result.output.lower()


def test_fake_describe_all_sync_describes_everything_and_spends_nothing(corpus_db, monkeypatch):
    _no_openai(monkeypatch)
    _seed_law(corpus_db)
    result = _invoke("describe", "--what", "all", "--sync")
    assert result.exit_code == 0, result.output
    with connect(corpus_db) as conn:
        assert spent(conn) == 0.0
        group = conn.execute("select description_by_lang from corpus.translation_group").fetchone()
        chunks = conn.execute("select description from corpus.chunk").fetchall()
    assert set(group["description_by_lang"]) == {"de", "fr"}
    assert chunks and all(c["description"] for c in chunks)


def test_fake_ocr_and_embed_spend_nothing(corpus_db, monkeypatch, tmp_path):
    _no_openai(monkeypatch)
    _seed_scan(corpus_db, tmp_path)
    assert _invoke("ocr", "--sync").exit_code == 0
    result = _invoke("embed", "--index", "openai-3l", "--allow-undescribed")
    assert result.exit_code == 0, result.output
    with connect(corpus_db) as conn:
        assert spent(conn) == 0.0
        assert conn.execute("select needs_ocr from corpus.chunk").fetchone()["needs_ocr"] is False
        assert conn.execute("select count(*) as n from corpus.emb_openai_3l").fetchone()["n"] == 1


def test_ocr_pilot_prints_the_projection(corpus_db, monkeypatch, tmp_path):
    _no_openai(monkeypatch)
    _seed_scan(corpus_db, tmp_path)
    result = _invoke("ocr", "--pilot", "1")
    assert result.exit_code == 0, result.output
    assert "per page" in result.output and "projection" in result.output


def test_budget_cap_blocks_a_paid_run(corpus_db, monkeypatch):
    _seed_law(corpus_db)
    monkeypatch.setenv("CORPUS_BUDGET_USD", "0")
    result = _invoke("describe", "--what", "docs", "--sync")
    assert result.exit_code == 2 and "budget" in result.output.lower()
    with connect(corpus_db) as conn:
        assert conn.execute("select description_by_lang from corpus.translation_group").fetchone()[
            "description_by_lang"] == {}


def test_batches_lists_batch_jobs(corpus_db):
    _insert_batch(corpus_db, "batch_abc", "describe-doc")
    result = _invoke("batches")
    assert result.exit_code == 0 and "batch_abc" in result.output and "describe-doc" in result.output


def test_describe_ingests_unfinished_batches_before_building_tasks(corpus_db, monkeypatch, tmp_path):
    _seed_law(corpus_db)
    with connect(corpus_db) as conn:
        [task] = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
    reply = {"descriptions": {"de": "Obligationenrecht", "fr": "Code des obligations"}, "topics": ["work"]}
    line = {"custom_id": task.custom_id, "response": {"status_code": 200, "body": {
        "choices": [{"message": {"content": json.dumps(reply)}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 100}}}}
    client = _FinishedBatches({"batch_1": [line]})
    _openai_mode(monkeypatch, client, tmp_path)
    _insert_batch(corpus_db, "batch_1", "describe-doc")
    result = _invoke("describe", "--what", "docs")
    assert result.exit_code == 0, result.output
    assert client.created == []
    with connect(corpus_db) as conn:
        job = conn.execute("select status, ingested_at from corpus.batch_job").fetchone()
        group = conn.execute("select description_by_lang from corpus.translation_group").fetchone()
        assert spent(conn, "describe") > 0
    assert job["status"] == "completed" and job["ingested_at"] is not None
    assert group["description_by_lang"]["fr"] == "Code des obligations"


def test_embed_ingests_unfinished_batches_before_building_new_ones(corpus_db, monkeypatch, tmp_path):
    _seed_law(corpus_db)
    with connect(corpus_db) as conn:
        conn.execute("update corpus.chunk set description = 'Kündigungsschutz'")
        conn.commit()
        pending = pending_for_index(conn, INDEXES["openai-3l"], require_description=True, limit=None)
    lines = [{"custom_id": f"{p['language']}|{p['id']}|{p['hash']}", "response": {"status_code": 200, "body": {
        "data": [{"embedding": [0.01] * 3072}], "usage": {"prompt_tokens": 20}}}} for p in pending]
    client = _FinishedBatches({"batch_e": lines})
    _openai_mode(monkeypatch, client, tmp_path)
    _insert_batch(corpus_db, "batch_e", "embed")
    result = _invoke("embed", "--index", "openai-3l")
    assert result.exit_code == 0, result.output
    assert client.created == []
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.emb_openai_3l").fetchone()["n"] == len(pending) == 2
        assert conn.execute("select ingested_at from corpus.batch_job").fetchone()["ingested_at"] is not None


def test_fetch_prints_a_tally_per_source_and_the_promotion_line(corpus_db, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRAWL_DELAY_SECONDS", "0")
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    result = _invoke("fetch", "--manifest", str(path), "--source", "tiny")
    assert result.exit_code == 0, result.output
    assert "tiny:" in result.output and "promote: promoted=0" in result.output
    assert _invoke("fetch", "--manifest", str(path), "--source", "nope").exit_code != 0


def test_fake_providers_refuse_to_write_into_a_real_database(corpus_db, monkeypatch):
    _no_openai(monkeypatch)
    monkeypatch.setattr(corpus_commands, "TEST_DB_PREFIX", "not_this_database_")
    _seed_law(corpus_db)
    for args in (("describe", "--what", "docs", "--sync"), ("ocr",), ("embed", "--index", "bge-m3"),
                 ("embed", "--index", "openai-3l", "--allow-undescribed")):
        refused = _invoke(*args)
        assert refused.exit_code == 2 and "--allow-fake" in refused.output, args
    assert _invoke("describe", "--what", "docs", "--dry-run").exit_code == 0
    assert _invoke("estimate").exit_code == 0
    with connect(corpus_db) as conn:
        assert conn.execute("select description_by_lang from corpus.translation_group").fetchone()[
            "description_by_lang"] == {}
    allowed = _invoke("describe", "--what", "docs", "--sync", "--allow-fake")
    assert allowed.exit_code == 0, allowed.output


def test_estimate_projects_chunk_descriptions_before_documents_are_described(corpus_db):
    _seed_law(corpus_db)
    result = _invoke("estimate")
    assert result.exit_code == 0, result.output
    assert "describe chunks projected: 1 tasks" in result.output
    assert "embed openai-3l before descriptions: 2 chunks" in result.output
    assert "embed openai-3l projected with descriptions: 2 chunks" in result.output


def test_anthropic_fallback_is_estimated_at_its_own_price(corpus_db, monkeypatch):
    _seed_law(corpus_db)
    monkeypatch.setenv("CORPUS_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    result = _invoke("describe", "--what", "docs", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "claude-haiku-4-5-20251001" in result.output


def test_ocr_without_a_limit_runs_in_slices_until_nothing_is_pending(corpus_db, monkeypatch, tmp_path):
    _no_openai(monkeypatch)
    monkeypatch.setattr(corpus_commands, "OCR_SLICE", 1)
    _seed_scan(corpus_db, tmp_path, pages=2)
    result = _invoke("ocr")
    assert result.exit_code == 0, result.output
    assert result.output.count("ocr: {'done': 1") == 2
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.chunk where needs_ocr").fetchone()["n"] == 0


def test_an_unreachable_database_is_one_friendly_line(corpus_db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:9/nothing")
    result = _invoke("describe", "--what", "docs", "--dry-run")
    assert result.exit_code == 1
    assert "database" in result.output.lower() and "Traceback" not in result.output
