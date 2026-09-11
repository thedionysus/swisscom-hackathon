import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from swiss_grounding.cli.main import app

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
runner = CliRunner()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    assert os.environ.get("DATABASE_URL")


def test_full_cli_flow():
    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    r = runner.invoke(app, ["load-fixture", str(FIXTURE)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["query", "Can my dog run off leash?", "--location", "Wiedikon", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["status"] == "results"
    r = runner.invoke(app, ["query", "Can my dog run off leash?"])
    assert r.exit_code == 2
    assert "needs_location" in r.output


def test_invalid_request_exits_with_code_one():
    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    r = runner.invoke(app, ["query", "dog rules", "--location", "Wiedikon", "--categories", "nope"])
    assert r.exit_code == 1, r.output
    assert "invalid_request" in r.output


def test_needs_location_exits_with_code_two():
    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    r = runner.invoke(app, ["query", "Can my dog run off leash?"])
    assert r.exit_code == 2
    assert "needs_location" in r.output


def _reset_documents():
    from swiss_grounding.config import load_settings
    from swiss_grounding.db.connection import connect

    with connect(load_settings().database_url) as conn:
        conn.execute("truncate chunk, document_change, document, fetch_state restart identity cascade")


def test_ingest_with_stub_fetcher_and_sources_commands(monkeypatch):
    from swiss_grounding.cli import main as cli
    from swiss_grounding.ingest.models import FetchedDocument, FetchResult, Section

    class Stub:
        def fetch(self, source, known):
            return FetchResult(documents=(FetchedDocument(
                source_id=source.id, url=f"{source.base_url}/cli-test", title="T", language="en",
                sections=(Section("T", None, "Dogs in Zurich must be leashed."),)),))

    monkeypatch.setattr(cli, "build_fetcher", lambda strategy, settings: Stub())
    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    _reset_documents()
    r = runner.invoke(app, ["ingest", "--source", "zh_ch"])
    assert r.exit_code == 0, r.output
    assert "added=1" in r.output
    r = runner.invoke(app, ["ingest", "--source", "zh_ch"])
    assert "unchanged=1" in r.output
    r = runner.invoke(app, ["sources", "list"])
    assert r.exit_code == 0 and "zh_ch" in r.output
    r = runner.invoke(app, ["ingest", "--source", "does_not_exist"])
    assert r.exit_code == 1


def test_sources_review_approve_reject(monkeypatch):
    import httpx

    from swiss_grounding.config import load_settings
    from swiss_grounding.db.connection import connect
    from swiss_grounding.registry.suggestions import submit_suggestion

    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    with connect(load_settings().database_url) as conn:
        conn.execute("truncate source_suggestion restart identity")
        conn.execute("delete from source where origin <> 'seed'")
        ok = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
        a = submit_suggestion(conn, ok, url="https://www.sac-cas.ch/de/huetten", reason="huts", suggested_by="t")
        b = submit_suggestion(conn, ok, url="https://www.example.com/x", reason="x", suggested_by="t")
    r = runner.invoke(app, ["sources", "review"])
    assert "sac-cas" in r.output and "example.com" in r.output
    r = runner.invoke(app, ["sources", "approve", str(a.id), "--extent", "CH", "--authority", "institutional", "--categories", "hiking", "--note", "ok"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["sources", "reject", str(b.id), "--note", "not swiss"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["sources", "review"])
    assert "sac-cas" not in r.output and "example.com" not in r.output
