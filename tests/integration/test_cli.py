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
