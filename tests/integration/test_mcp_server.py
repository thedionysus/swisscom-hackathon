import json
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium_data import load_premiums
from swiss_grounding.mcp_server.server import build_server
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration
TOOLS = {"swiss_search", "swiss_get_document", "swiss_scope", "swiss_premium", "swiss_connections",
         "swiss_reference_rate"}


@pytest.fixture
def server(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c")
        load_premiums(conn, Path("tests/fixtures/premium/premiums_sample.csv"),
                      Path("tests/fixtures/premium/regions_sample.csv"), 2026, {})
    return build_server(Settings(database_url=serving_db, query_embedder="fake", reranker_model="overlap",
                                 _env_file=None))


async def call(server, name, args):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args)
        return json.loads(result.content[0].text)


async def test_exactly_six_read_only_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS and len(tools) == 6
    assert all(t.annotations.readOnlyHint for t in tools)


async def test_search_returns_places_and_is_logged(server, serving_db):
    out = await call(server, "swiss_search", {"question": "Kündigungsfrist Wohnung?"})
    assert out["status"] == "results" and out["places"][0]["citations"]
    assert "notice" in out
    with connect(serving_db) as conn:
        assert conn.execute("select count(*) as n from serving.call_log where tool = 'swiss_search'"
                            ).fetchone()["n"] == 1


async def test_search_with_a_foreign_place(server):
    out = await call(server, "swiss_search", {"question": "Rundfunkbeitrag?", "locations": ["Konstanz, Deutschland"]})
    assert out["status"] == "outside_scope" and "Covered:" in out["scope"]


async def test_scope_tool(server):
    out = await call(server, "swiss_scope", {})
    assert "Scuol" in out["scope"] and "commercial register" in out["scope"]


async def test_premium_tool_resolves_the_municipality(server):
    out = await call(server, "swiss_premium", {"municipality": "Lugano", "age": 30, "deductible": 2500,
                                               "year": 2026})
    assert out["status"] == "results" and out["premiums"][0]["premium_chf"] == 330.55


async def test_more_than_three_places_are_trimmed_not_rejected(server):
    out = await call(server, "swiss_search", {"question": "Anmeldung?",
                                              "locations": ["Zürich", "Bern", "Chur", "Scuol"]})
    assert len(out["places"]) == 3 and "first three" in out["message"]


async def test_internal_errors_do_not_leak(server, monkeypatch):
    from swiss_grounding.serving import search_service
    def boom(*a, **k):
        raise RuntimeError("password=secret host=db")
    monkeypatch.setattr(search_service.SearchService, "search", boom)
    out = await call(server, "swiss_search", {"question": "x"})
    assert out["status"] == "error" and "secret" not in json.dumps(out)


async def test_premium_tool_outside_switzerland(server):
    out = await call(server, "swiss_premium", {"municipality": "Konstanz, Deutschland", "age": 30,
                                               "deductible": 2500})
    assert out["status"] == "outside_scope"
