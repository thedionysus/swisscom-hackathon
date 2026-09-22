import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.pipeline import IngestReport
from swiss_grounding.ingest.run_log import record_run
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.mcp_server.server import build_server
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
# Every swiss_search call that expects citations states its `categories`. Topic is a hard
# filter now (ADR 0003) and a request stating none falls through to the local classifier,
# whose thresholds are calibrated against bge-m3 (`retrieval/topics.py`) and decide
# nothing meaningful under the 8-dimension FakeEmbedder this suite runs on. Before they
# were pinned, four of these failed and one passed on a hash collision; none of them is
# about topics, so none of them should depend on that.
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
T1 = datetime(2026, 9, 10, 1, tzinfo=UTC)
T2 = datetime(2026, 9, 11, 1, tzinfo=UTC)


@pytest.fixture
def server():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        conn.execute("truncate source_suggestion restart identity")
        conn.execute("delete from source where origin <> 'seed'")
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
                     "swiss_list_categories", "swiss_coverage", "swiss_suggest_source"}
    # The count as well as the names: a set comparison says nothing about a tool
    # registered twice, and Task 10's plan asks for the six registrations to be pinned
    # rather than checked by hand in an MCP client.
    assert len(tools.tools) == 6


async def test_search_returns_results_with_notice(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?", "location": "Wiedikon",
                       "categories": ["dogs"]})
    assert data["status"] == "results"
    assert data["notice"].startswith("Retrieved public information")
    assert data["citations"][0]["url"].startswith("https://")
    assert "snippet_original" not in data["citations"][0]      # concise by default


async def test_search_detailed_includes_original_snippet(server):
    data = await call(server, "swiss_search", {"question": "leash", "location": "Wiedikon", "categories": ["dogs"],
                       "response_format": "detailed"})
    assert "snippet_original" in data["citations"][0]


async def test_search_without_location_asks(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?"})
    assert data["status"] == "needs_location"


async def test_resolve_location(server):
    data = await call(server, "swiss_resolve_location", {"query": "8003"})
    assert data["location_id"] == "CH-ZH-261-K3"
    assert data["path"][0] == "CH"


async def test_get_document(server):
    search = await call(server, "swiss_search", {"question": "leash", "location": "Zurich", "categories": ["dogs"]})
    doc_id = search["citations"][0]["document_id"]
    data = await call(server, "swiss_get_document", {"document_id": doc_id})
    assert data["document"]["id"] == doc_id
    assert "event_date" in data["document"]
    assert len(data["chunks"]) >= 1


async def test_list_categories(server):
    data = await call(server, "swiss_list_categories", {})
    assert any(c["id"] == "hiking" for c in data["categories"])


async def test_coverage(server):
    data = await call(server, "swiss_coverage", {"location": "Zurich"})
    extents = {row["extent_id"] for row in data["coverage"]}
    assert "CH-ZH-261" in extents and "CH-BS" not in extents


async def test_coverage_reports_fetch_health_and_fixture_origin(server):
    with connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("truncate ingest_run")
        record_run(conn, IngestReport(source_id="zh_ch", run_id="r1", added=2), started_at=T1, finished_at=T1)
        record_run(conn, IngestReport(source_id="zh_ch", run_id="r2", failed=3), started_at=T2, finished_at=T2)
    data = await call(server, "swiss_coverage", {"location": "Zurich"})
    zh = next(row for row in data["coverage"] if row["source_id"] == "zh_ch")
    assert zh["health"] == "failing" and zh["last_run_failed"] == 3
    assert zh["last_run_at"].startswith("2026-09-11") and zh["last_successful_run_at"].startswith("2026-09-10")
    assert zh["fixture_only"] is True
    other = next(row for row in data["coverage"] if row["source_id"] != "zh_ch")
    assert other["health"] == "unknown" and other["last_run_at"] is None


async def test_resolve_location_not_found_carries_notice(server):
    data = await call(server, "swiss_resolve_location", {"query": "Atlantis"})
    assert data["found"] is False
    assert data["notice"].startswith("Retrieved public information")


async def test_resolve_location_found_carries_notice(server):
    data = await call(server, "swiss_resolve_location", {"query": "8003"})
    assert data["notice"].startswith("Retrieved public information")


async def test_list_categories_carries_notice(server):
    data = await call(server, "swiss_list_categories", {})
    assert data["notice"].startswith("Retrieved public information")


async def test_get_document_not_found_carries_notice(server):
    data = await call(server, "swiss_get_document", {"document_id": 999999})
    assert data["error"] == "document 999999 not found"
    assert data["notice"].startswith("Retrieved public information")


EVENTS = Path(__file__).parent.parent / "fixtures" / "waste_events.json"


async def test_event_citations_carry_event_date_and_rank_upcoming_first(server):
    with connect(os.environ["DATABASE_URL"]) as conn:
        load_fixture(conn, EVENTS, FakeEmbedder(dim=8))
    query = {"question": "When is cardboard collected?", "location": "8003", "categories": ["waste"]}
    concise = await call(server, "swiss_search", query)
    events = [c for c in concise["citations"] if c["source_id"] == "open_erz"]
    assert [c["event_date"] for c in events] == ["2099-12-30", "2020-01-22"]
    detailed = await call(server, "swiss_search", {**query, "response_format": "detailed"})
    assert detailed["citations"][0]["event_date"] == "2099-12-30"
    assert detailed["citations"][0]["event_date"] and "retrieved_at" in detailed["citations"][0]


async def test_coverage_unresolvable_location_carries_notice(server):
    data = await call(server, "swiss_coverage", {"location": "Atlantis"})
    assert data["coverage"] == []
    assert data["notice"].startswith("Retrieved public information")


async def test_invalid_as_of_returns_structured_error(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(
            "swiss_search", {"question": "leash", "location": "Zurich", "as_of": "not-a-date"},
        )
    assert result.isError is False
    data = json.loads(result.content[0].text)
    assert data["status"] == "invalid_request"
    assert data["field"] == "as_of"
    assert "YYYY-MM-DD" in data["message"]
    assert data["notice"].startswith("Retrieved public information")


async def test_get_document_rejects_chunk_from_another_document(server):
    search = await call(server, "swiss_search", {"question": "leash", "location": "Zurich", "categories": ["dogs"], "limit": 8})
    doc_id = search["citations"][0]["document_id"]
    other = next(c for c in search["citations"] if c["document_id"] != doc_id)
    data = await call(server, "swiss_get_document",
                      {"document_id": doc_id, "chunk_id": other["chunk_id"]})
    assert data["error"] == f"chunk {other['chunk_id']} is not part of document {doc_id}"
    assert data["notice"].startswith("Retrieved public information")


async def test_search_limit_is_constrained_by_schema(server):
    schema = None
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    for tool in tools.tools:
        if tool.name == "swiss_search":
            schema = tool.inputSchema["properties"]["limit"]
    assert schema["minimum"] == 1
    assert schema["maximum"] == 25


async def test_dates_are_serialized_as_iso(server):
    data = await call(server, "swiss_search",
                      {"question": "leash", "location": "Wiedikon", "categories": ["dogs"],
                       "response_format": "detailed"})
    retrieved = data["citations"][0]["retrieved_at"]
    assert "T" in retrieved


def _ok_http():
    import httpx

    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))


async def test_tool_list_includes_suggest_source(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    suggest = next(t for t in tools.tools if t.name == "swiss_suggest_source")
    assert suggest.annotations.readOnlyHint is False


async def test_suggest_official_source_is_auto_approved(server, monkeypatch):
    from swiss_grounding.mcp_server import server as server_module

    monkeypatch.setattr(server_module, "_suggestion_http", _ok_http)
    data = await call(server, "swiss_suggest_source", {"url": "https://www.bs.ch/hunde", "reason": "Basel dogs"})
    assert data["status"] == "approved" and data["domain_class"] == "official"
    assert data["source_id"] == "bs_ch"
    assert data["notice"]


async def test_suggest_invalid_url_is_structured_error(server):
    data = await call(server, "swiss_suggest_source", {"url": "nope", "reason": "r"})
    assert data["status"] == "invalid_request" and data["field"] == "url"


async def test_coverage_lists_pending_suggestions(server, monkeypatch):
    from swiss_grounding.mcp_server import server as server_module

    monkeypatch.setattr(server_module, "_suggestion_http", _ok_http)
    await call(server, "swiss_suggest_source", {"url": "https://www.sac-cas.ch/de/huetten", "reason": "huts"})
    data = await call(server, "swiss_coverage", {})
    assert data["pending_suggestions"][0]["url"] == "https://www.sac-cas.ch/de/huetten"


GENERATED = "Sets penalties for mistreating animals"


async def test_swiss_get_document_never_hands_back_generated_context(server):
    """The one caller path the citation guard does not cover.

    `swiss_get_document` selects an explicit column list that excludes `context_en`, which is
    correct -- but `fixture_loader` never writes a context, so every chunk the MCP suite loads
    has an empty one and adding `context_en` to that select would leak into tool output with the
    whole suite still green. This seeds a real context so the leak has something to carry.
    """
    url = os.environ["DATABASE_URL"]
    with connect(url) as conn:
        chunk = conn.execute("select id, document_id from chunk order by id limit 1").fetchone()
        conn.execute("update chunk set context_en = %s where id = %s", (GENERATED, chunk["id"]))
    data = await call(server, "swiss_get_document", {"document_id": chunk["document_id"]})
    assert data["chunks"], "nothing came back, so nothing was actually checked"
    assert GENERATED not in json.dumps(data)


# --- the swiss_search contract ADR 0004 asks for (Task 10) ------------------------------
#
# The calling model supplies the question as written, the question in English, and a short
# English description of the topic. These check the tool boundary: that the three text
# fields and `topics` are on the signature, that the response says which of them were used,
# and that a client still on the old contract degrades rather than breaks.

DE = "Wo darf mein Hund frei laufen?"
EN = "Where may my dog run off leash?"
DOG_TOPIC = "off-leash dog zones and leash rules"


async def test_search_accepts_the_english_query_fields_and_reports_them(server):
    data = await call(server, "swiss_search", {
        "question": DE, "question_en": EN, "topic_en": DOG_TOPIC,
        "location": "Wiedikon", "topics": ["dogs"],
    })
    assert data["status"] == "results"
    assert data["query_fields"] == ["question_en", "topic_en"]
    assert data["topic_decided_by"] == "topics"
    assert data["categories_used"] == ["dogs"]


async def test_search_without_question_en_reports_the_degraded_path(server):
    """An un-updated client gets an answer, and the response tells anyone reading it that
    a German question was matched against an English index."""
    data = await call(server, "swiss_search",
                      {"question": DE, "location": "Wiedikon", "topics": ["dogs"]})
    assert data["status"] == "results"
    assert data["query_fields"] == ["question"]


async def test_search_still_accepts_the_deprecated_categories_field(server):
    """ADR 0004 accepts that registered clients must be updated; it does not accept that
    an un-updated one gets a schema error instead of an answer. `categories` keeps
    filtering, under its own name in the report so the deprecation is visible."""
    data = await call(server, "swiss_search",
                      {"question": "leash", "location": "Wiedikon", "categories": ["dogs"]})
    assert data["status"] == "results"
    assert data["topic_decided_by"] == "categories"
    assert data["categories_used"] == ["dogs"]


async def test_topics_outrank_the_deprecated_categories_field(server):
    data = await call(server, "swiss_search", {
        "question": "leash", "location": "Wiedikon",
        "topics": ["dogs"], "categories": ["waste"],
    })
    assert data["categories_used"] == ["dogs"]
    assert data["topic_decided_by"] == "topics"


async def test_search_schema_advertises_the_new_contract(server):
    """What a calling model actually reads. `question` stays the only required field, so
    the three additions cannot break a client that sends nothing new."""
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    search = next(t for t in tools.tools if t.name == "swiss_search")
    assert {"question", "question_en", "topic_en", "topics"} <= set(search.inputSchema["properties"])
    assert search.inputSchema.get("required", []) == ["question"]


def _flat(description: str) -> str:
    """A tool description with its line wrapping collapsed.

    The description is a docstring, so where a sentence breaks is an accident of the
    source line width. Asserting against the raw string would make a reflow of the
    paragraph fail a test that is about what the description says.
    """
    return " ".join(description.split())


async def test_search_description_states_what_as_of_really_does(server):
    """The old description said `as_of` is an "ISO date to retrieve law as it stood on that
    date". The index holds current consolidations only and has no version history (D2), so
    that was false. The description a calling model reads must carry the correction, not
    merely drop the claim -- a model that has seen the old contract needs telling."""
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    description = _flat(next(t for t in tools.tools if t.name == "swiss_search").description)
    assert "no version history" in description
    assert "does NOT retrieve law as it stood on that date" in description


async def test_search_description_does_not_sell_distance_as_relevance(server):
    """`distance` is published for information and nothing filters on it. A calling model
    that reads it as a relevance score will drop good evidence, so the description has to
    say lower-is-better and say it is not a threshold."""
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    description = _flat(next(t for t in tools.tools if t.name == "swiss_search").description)
    assert "lower-is-better" in description
    assert "NOT a relevance threshold" in description
    assert "question_en + topic_en" in description
