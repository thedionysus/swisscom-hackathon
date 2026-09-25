"""Calls the MCP server's tools in-process, through the same handlers a client reaches."""
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import anyio
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings

Call = tuple[str, Mapping[str, Any]]


def parse_result(result) -> dict:
    """The first text content as JSON; non-JSON text is wrapped so it can still be searched."""
    text = result.content[0].text if result.content else ""
    try:
        body = json.loads(text)
    except ValueError:
        body = {"text": text}
    body = body if isinstance(body, dict) else {"items": body}
    return {"status": "error", **body} if result.isError and "status" not in body else body


def call_all(settings: Settings, calls: Sequence[Call]) -> tuple[frozenset[str], tuple[dict | None, ...]]:
    """Listed tool names and one parsed output per call; None for a tool the server does not list."""
    from swiss_grounding.mcp_server.server import build_server
    server = build_server(settings)

    async def run() -> tuple[frozenset[str], tuple[dict | None, ...]]:
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            names = frozenset(t.name for t in (await client.list_tools()).tools)
            outs = []
            for name, args in calls:
                outs.append(parse_result(await client.call_tool(name, dict(args))) if name in names else None)
            return names, tuple(outs)
    return anyio.run(run)


def list_tools(settings: Settings) -> list:
    from swiss_grounding.mcp_server.server import build_server
    server = build_server(settings)

    async def run() -> list:
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            return (await client.list_tools()).tools
    return anyio.run(run)


Caller = Callable[[Sequence[Call]], tuple[frozenset[str], tuple[dict | None, ...]]]
