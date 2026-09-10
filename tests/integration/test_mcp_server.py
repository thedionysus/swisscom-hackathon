import json
import os
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.mcp_server.server import build_server
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def server():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return build_server(Settings(database_url=url, embedding_backend="fake", embedding_dim=8))


async def call(server, name, args):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args)
        return json.loads(result.content[0].text)


async def test_lists_expected_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert names == {"swiss_resolve_location", "swiss_search", "swiss_get_document",
                     "swiss_list_categories", "swiss_coverage"}


async def test_search_returns_results_with_notice(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?", "location": "Wiedikon"})
    assert data["status"] == "results"
    assert data["notice"].startswith("Retrieved public information")
    assert data["citations"][0]["url"].startswith("https://")
    assert "snippet_original" not in data["citations"][0]      # concise by default


async def test_search_detailed_includes_original_snippet(server):
    data = await call(server, "swiss_search", {"question": "leash", "location": "Wiedikon", "response_format": "detailed"})
    assert "snippet_original" in data["citations"][0]


async def test_search_without_location_asks(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?"})
    assert data["status"] == "needs_location"


async def test_resolve_location(server):
    data = await call(server, "swiss_resolve_location", {"query": "8003"})
    assert data["location_id"] == "CH-ZH-261-K3"
    assert data["path"][0] == "CH"


async def test_get_document(server):
    search = await call(server, "swiss_search", {"question": "leash", "location": "Zurich"})
    doc_id = search["citations"][0]["document_id"]
    data = await call(server, "swiss_get_document", {"document_id": doc_id})
    assert data["document"]["id"] == doc_id
    assert len(data["chunks"]) >= 1


async def test_list_categories(server):
    data = await call(server, "swiss_list_categories", {})
    assert any(c["id"] == "hiking" for c in data["categories"])


async def test_coverage(server):
    data = await call(server, "swiss_coverage", {"location": "Zurich"})
    extents = {row["extent_id"] for row in data["coverage"]}
    assert "CH-ZH-261" in extents and "CH-BS" not in extents
