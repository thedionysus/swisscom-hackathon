"""The MCP contract: every tool is described, bad input is answered with a status, citations exist."""
import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.mcp_server.server import build_server
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


@pytest.fixture
def server(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c")
    return build_server(Settings(database_url=serving_db, query_embedder="fake", reranker_model="overlap",
                                 zbern_mcp_url="", _env_file=None))


async def call(server, name, args):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args)
        return json.loads(result.content[0].text)


async def test_every_tool_has_a_description_and_an_input_schema(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = (await client.list_tools()).tools
    assert tools
    for t in tools:
        assert t.description and t.description.strip(), t.name
        assert t.inputSchema.get("type") == "object", t.name


@pytest.mark.parametrize("args", [
    {"question": "Kündigungsfrist?", "as_of": "gestern"},
    {"question": ""},
    {"question": "   "},
])
async def test_bad_search_input_is_invalid_request(server, args):
    out = await call(server, "swiss_search", args)
    assert out["status"] == "invalid_request"


async def test_four_locations_are_answered_not_raised(server):
    out = await call(server, "swiss_search", {"question": "Kündigungsfrist Wohnung?",
                                              "locations": ["Zürich", "Bern", "Chur", "Lugano"]})
    assert out["status"] in {"invalid_request", "results", "no_evidence"}
    assert out["status"] == "invalid_request" or len(out["places"]) <= 3


async def test_bad_document_reference_is_invalid_request(server):
    assert (await call(server, "swiss_get_document", {"reference": "no such thing"}))["status"] == "invalid_request"


async def test_every_cited_url_exists_in_the_corpus(server, serving_db):
    out = await call(server, "swiss_search", {"question": "Kündigungsfrist Wohnung?"})
    urls = {c["url"] for p in out["places"] for c in p["citations"]}
    assert urls
    with connect(serving_db) as conn:
        known = {r["url"] for r in conn.execute("select url from corpus.document where url = any(%s)",
                                                (list(urls),)).fetchall()}
    assert urls <= known
