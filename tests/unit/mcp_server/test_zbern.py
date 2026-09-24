"""The zbern.ch parliament tools served beside our own (ADR 0018), against in-memory fake servers."""
import json
from contextlib import asynccontextmanager
from functools import partial

import anyio
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import (
    create_client_server_memory_streams,
    create_connected_server_and_client_session,
)

from swiss_grounding.config import Settings
from swiss_grounding.mcp_server import zbern

REMOTE_INSTRUCTIONS = "Swiss federal politics from official sources, compiled and maintained by zbern.ch."


def fake_zbern() -> FastMCP:
    remote = FastMCP("zbern", instructions=REMOTE_INSTRUCTIONS)

    @remote.tool()
    def search_person(name: str, language: str = "de") -> str:
        """Find members of parliament by name."""
        return json.dumps({"status": "results", "name": name, "language": language})

    @remote.tool()
    def query(sql: str) -> str:
        """Run read-only SQL."""
        return json.dumps({"rows": []})

    return remote


def local_server() -> FastMCP:
    local = FastMCP("swiss-grounding", instructions="LOCAL INSTRUCTIONS")

    @local.tool()
    def swiss_scope() -> str:
        """What this server covers."""
        return json.dumps({"status": "results", "scope": "Covered: ..."})

    return local


def memory_transport(remote: FastMCP) -> zbern.Transport:
    @asynccontextmanager
    async def open_():
        async with create_client_server_memory_streams() as (client, server), anyio.create_task_group() as tg:
            low = remote._mcp_server
            tg.start_soon(partial(low.run, server[0], server[1], low.create_initialization_options(),
                                  raise_exceptions=True))
            yield client
            tg.cancel_scope.cancel()
    return open_


def down_transport() -> zbern.Transport:
    @asynccontextmanager
    async def open_():
        raise ConnectionError("zbern is down")
        yield  # pragma: no cover
    return open_


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def served(local: FastMCP, tools: zbern.ZbernTools):
    zbern.attach(local, tools, "LOCAL INSTRUCTIONS")
    return local


async def list_names(local: FastMCP) -> list[str]:
    async with create_connected_server_and_client_session(local._mcp_server) as client:
        return [t.name for t in (await client.list_tools()).tools]


async def call(local: FastMCP, name: str, args: dict):
    async with create_connected_server_and_client_session(local._mcp_server) as client:
        result = await client.call_tool(name, args)
        return result, json.loads(result.content[0].text)


async def test_remote_tools_are_served_with_a_prefix_beside_ours():
    local = await served(local_server(), zbern.ZbernTools(memory_transport(fake_zbern())))
    async with create_connected_server_and_client_session(local._mcp_server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"swiss_scope", "parl_search_person", "parl_query"}
    person = tools["parl_search_person"]
    assert person.description.startswith(zbern.DESCRIPTION_TAG)
    assert "Find members of parliament" in person.description
    assert set(person.inputSchema["properties"]) == {"name", "language"}


async def test_a_call_reaches_the_remote_tool_with_its_own_name_and_arguments():
    local = await served(local_server(), zbern.ZbernTools(memory_transport(fake_zbern())))
    await list_names(local)
    result, body = await call(local, "parl_search_person", {"name": "Jositsch", "language": "fr"})
    assert not result.isError
    assert body == {"status": "results", "name": "Jositsch", "language": "fr"}


async def test_our_own_tools_still_answer():
    local = await served(local_server(), zbern.ZbernTools(memory_transport(fake_zbern())))
    _, body = await call(local, "swiss_scope", {})
    assert body["scope"] == "Covered: ..."


async def test_excluded_tools_are_not_served():
    tools = zbern.ZbernTools(memory_transport(fake_zbern()), exclude=("query",))
    local = await served(local_server(), tools)
    assert set(await list_names(local)) == {"swiss_scope", "parl_search_person"}
    _, body = await call(local, "parl_query", {"sql": "select 1"})
    assert body["status"] == "invalid_request"


async def test_a_custom_prefix_is_used():
    local = await served(local_server(), zbern.ZbernTools(memory_transport(fake_zbern()), prefix="zbern_"))
    assert "zbern_search_person" in await list_names(local)


async def test_instructions_carry_the_routing_hint_and_the_remote_instructions():
    tools = zbern.ZbernTools(memory_transport(fake_zbern()))
    await tools.refresh()
    local = await served(local_server(), tools)
    text = local._mcp_server.instructions
    assert text.startswith("LOCAL INSTRUCTIONS")
    assert "`parl_*` tools" in text and REMOTE_INSTRUCTIONS in text


async def test_an_unreachable_server_leaves_our_tools_working():
    local = await served(local_server(), zbern.ZbernTools(down_transport()))
    assert await list_names(local) == ["swiss_scope"]
    assert "`parl_*` tools" in local._mcp_server.instructions   # the routing hint, without remote text
    _, body = await call(local, "swiss_scope", {})
    assert body["status"] == "results"


async def test_known_tools_survive_an_outage_and_calls_say_the_source_is_unavailable():
    remote = memory_transport(fake_zbern())
    current = {"transport": remote}
    tools = zbern.ZbernTools(lambda: current["transport"](), refresh_seconds=0)
    local = await served(local_server(), tools)
    assert "parl_search_person" in await list_names(local)
    current["transport"] = down_transport()
    assert "parl_search_person" in await list_names(local)
    result, body = await call(local, "parl_search_person", {"name": "x"})
    assert not result.isError
    assert body == {"status": "source_unavailable", "message": zbern.UNAVAILABLE}


async def test_changes_on_the_zbern_side_show_up_after_the_refresh_period():
    remote, clock = fake_zbern(), Clock()
    tools = zbern.ZbernTools(memory_transport(remote), refresh_seconds=300, clock=clock)
    local = await served(local_server(), tools)
    assert "parl_get_upcoming_votes" not in await list_names(local)

    @remote.tool()
    def get_upcoming_votes() -> str:
        """Upcoming federal votes."""
        return json.dumps({"status": "results", "votes": []})

    clock.now = 299
    assert "parl_get_upcoming_votes" not in await list_names(local)
    clock.now = 300
    assert "parl_get_upcoming_votes" in await list_names(local)
    _, body = await call(local, "parl_get_upcoming_votes", {})
    assert body == {"status": "results", "votes": []}


async def test_a_new_tool_is_found_on_first_call_even_before_the_period_ends():
    remote, clock = fake_zbern(), Clock()
    tools = zbern.ZbernTools(memory_transport(remote), refresh_seconds=300, clock=clock)
    local = await served(local_server(), tools)
    await list_names(local)

    @remote.tool()
    def get_coverage() -> str:
        """What zbern covers."""
        return json.dumps({"status": "results"})

    clock.now = 400   # a client that cached an old list calls the new tool after the period
    _, body = await call(local, "parl_get_coverage", {})
    assert body == {"status": "results"}


async def test_calls_are_logged_with_their_status():
    records = []
    tools = zbern.ZbernTools(memory_transport(fake_zbern()), on_call=records.append)
    local = await served(local_server(), tools)
    await list_names(local)
    await call(local, "parl_search_person", {"name": "x"})
    tools._transport = down_transport()
    await call(local, "parl_search_person", {"name": "x"})
    assert [(r.tool, r.status, r.error) for r in records] == [
        ("parl_search_person", "results", None),
        ("parl_search_person", "source_unavailable", "ConnectionError"),
    ]


async def test_prime_works_from_inside_a_running_event_loop():
    tools = zbern.ZbernTools(memory_transport(fake_zbern()))
    tools.prime()
    assert tools.remote_instructions == REMOTE_INSTRUCTIONS
    assert "parl_search_person" in {t.name for t in await tools.list_tools()}


def test_off_without_a_url():
    assert zbern.from_settings(Settings(database_url="postgresql://u:p@h:1/db", _env_file=None)) is None


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("ZBERN_MCP_URL", "https://mcp.zbern.ch/mcp")
    monkeypatch.setenv("ZBERN_MCP_TOKEN", "secret-token")
    monkeypatch.setenv("ZBERN_MCP_EXCLUDE", "query, list_tables,,query")
    s = Settings(_env_file=None)
    assert s.zbern_mcp_exclude == ("query", "list_tables")
    assert "secret-token" not in repr(s)
    tools = zbern.from_settings(s)
    assert tools is not None and tools.prefix == "parl_"


@pytest.mark.parametrize("token, expected", [("t0k3n", "Bearer t0k3n"), (None, None)])
async def test_http_transport_sends_the_bearer_token(token, expected):
    import socket

    import uvicorn

    remote = FastMCP("zbern", instructions=REMOTE_INSTRUCTIONS, stateless_http=True, json_response=True)

    @remote.tool()
    def ping() -> str:
        return "pong"

    seen = []
    app = remote.streamable_http_app()

    async def recording(scope, receive, send):
        if scope["type"] == "http":
            seen.append(dict(scope["headers"]).get(b"authorization", b"").decode() or None)
        await app(scope, receive, send)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(recording, host="127.0.0.1", port=port, log_level="error",
                                           lifespan="on"))
    async with anyio.create_task_group() as tg:
        tg.start_soon(server.serve)
        while not server.started:
            await anyio.sleep(0.01)
        tools = zbern.ZbernTools(zbern.http_transport(f"http://127.0.0.1:{port}/mcp", token, 10))
        assert await tools.refresh()
        assert [t.name for t in await tools.list_tools()] == ["parl_ping"]
        server.should_exit = True
    assert seen and all(h == expected for h in seen)
