"""Swiss Parliament tools from the zbern.ch MCP server, served beside our own tools (ADR 0018).

The zbern server is a separate MCP server with its own data (Federal Parliament: members, business items,
debates, roll-call votes; federal popular votes). This module connects to it as an MCP client and re-exports
its tools under a prefix (`zbern_` by default), so a client sees one server. Nothing about the zbern tools is
hard-coded here: names, descriptions, input schemas and the server's instructions are discovered from the
remote server and refreshed periodically, so the zbern side can add, change or remove tools without a change
in this repository. Calls are passed through unchanged and the remote result is returned verbatim.

The hosted zbern server needs a bearer token, so the tools are served once ZBERN_MCP_TOKEN is present (`setup`
installs it) and ZBERN_MCP_URL is not empty. When the zbern server is unreachable our own tools keep working: its tools
are listed from the last successful discovery (none if there never was one) and a call answers
`source_unavailable`.
"""
import json
import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta
from time import monotonic, perf_counter
from typing import Any

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations

from swiss_grounding.config import Settings
from swiss_grounding.serving.call_log import CallRecord, record_call

log = logging.getLogger(__name__)

# Yields the (read, write) streams of one MCP client connection.
Transport = Callable[[], AbstractAsyncContextManager[tuple[Any, Any]]]

DESCRIPTION_TAG = "[Swiss Parliament, via zbern.ch] "
# The zbern server declares no annotations. Its tools only read (a read-only DuckDB plus BFS fetches), and
# clients such as Claude Code ask the user before calling a tool without readOnlyHint.
FORWARDED = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
UNAVAILABLE = ("The Swiss Parliament source (zbern.ch) cannot be reached right now. Tell the user this part "
               "cannot be answered at the moment; do not answer it from memory.")


def instructions_section(prefix: str, remote: str | None) -> str:
    """Routing hint plus the zbern server's own instructions, appended to ours."""
    head = (
        f"Swiss federal Parliament and federal popular votes are answered by the `{prefix}*` tools (served by "
        f"zbern.ch): members of parliament, business items (motions, postulates, interpellations, bills), debate "
        f"transcripts, roll-call votes, popular vote results and upcoming votes. Use them for those questions even "
        f"where `swiss_scope` does not list them; use the `swiss_*` tools for law, public services and lookups."
    )
    return f"{head}\n\n{remote.strip()}" if remote and remote.strip() else head


def http_transport(url: str, token: str | None, timeout_seconds: float) -> Transport:
    @asynccontextmanager
    async def open_() -> AsyncIterator[tuple[Any, Any]]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 10.0))
        async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client, \
                streamable_http_client(url, http_client=client) as (read, write, _):
            yield read, write
    return open_


class ZbernTools:
    """Discovers the zbern tools, lists them under a prefix and passes calls through."""

    def __init__(self, transport: Transport, *, prefix: str = "zbern_", exclude: tuple[str, ...] = (),
                 refresh_seconds: float = 300.0, timeout_seconds: float = 60.0,
                 discovery_timeout_seconds: float = 10.0, clock: Callable[[], float] = monotonic,
                 on_call: Callable[[CallRecord], None] | None = None):
        self._transport = transport
        self.prefix = prefix
        self._exclude = frozenset(exclude)
        self._refresh_seconds = refresh_seconds
        self._timeout = timeout_seconds
        self._discovery_timeout = discovery_timeout_seconds
        self._clock = clock
        self._on_call = on_call
        self._tools: dict[str, Tool] = {}      # prefixed name -> tool as listed to our clients
        self.remote_instructions: str | None = None
        self._refreshed_at: float | None = None

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        async with self._transport() as (read, write), \
                ClientSession(read, write, read_timeout_seconds=timedelta(seconds=self._timeout)) as session:
            init = await session.initialize()
            self.remote_instructions = init.instructions
            yield session

    async def refresh(self) -> bool:
        """Re-reads the remote tool list. On failure keeps the last known tools. True on success.

        Two concurrent refreshes are harmless (both write the same list), so there is no lock: an anyio lock
        would be bound to the event loop of `prime`."""
        # A failed discovery counts as a refresh too, so an unreachable server is retried once per period
        # instead of on every tools/list.
        self._refreshed_at = self._clock()
        try:
            with anyio.fail_after(self._discovery_timeout):
                async with self._session() as session:
                    remote = await _list_all_tools(session)
        except Exception as exc:  # noqa: BLE001 - any transport, protocol or timeout error keeps the old list
            log.warning("zbern discovery failed, keeping %d known tools: %r", len(self._tools), exc)
            return False
        self._tools = {self.prefix + t.name: self._relabel(t) for t in remote if t.name not in self._exclude}
        return True

    def prime(self) -> None:
        """Blocking first discovery, so the tools and instructions exist before the first client connects.

        Runs in its own thread and event loop: callers may already be inside one."""
        thread = threading.Thread(target=anyio.run, args=(self.refresh,), daemon=True)
        thread.start()
        thread.join(self._discovery_timeout + 5)

    def _relabel(self, tool: Tool) -> Tool:
        # outputSchema is dropped: our own `source_unavailable` answer could not satisfy an arbitrary remote
        # schema, and clients reject a result that misses a declared schema. Remote results stay verbatim.
        return tool.model_copy(update={"name": self.prefix + tool.name, "outputSchema": None,
                                       "annotations": tool.annotations or FORWARDED,
                                       "description": DESCRIPTION_TAG + (tool.description or "")})

    def _stale(self) -> bool:
        return self._refreshed_at is None or self._clock() - self._refreshed_at >= self._refresh_seconds

    async def list_tools(self) -> list[Tool]:
        if self._stale():
            await self.refresh()
        return list(self._tools.values())

    def owns(self, name: str) -> bool:
        return name.startswith(self.prefix)

    async def call(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        if name not in self._tools and self._stale():
            await self.refresh()
        started = perf_counter()
        if name not in self._tools:
            return await self._logged(name, started, _result("invalid_request", f"Unknown tool: {name}"))
        try:
            with anyio.fail_after(self._timeout + 5):
                async with self._session() as session:
                    result = await session.call_tool(name[len(self.prefix):], arguments or {})
        except Exception as exc:  # noqa: BLE001 - a zbern outage must never break our server
            log.warning("zbern call %s failed: %r", name, exc)
            return await self._logged(name, started, _result("source_unavailable", UNAVAILABLE),
                                      error=type(exc).__name__)
        return await self._logged(name, started, result)

    async def _logged(self, name: str, started: float, result: CallToolResult,
                      error: str | None = None) -> CallToolResult:
        if self._on_call is not None:
            status = "error" if result.isError else _status(result)
            record = CallRecord(name, int((perf_counter() - started) * 1000), status, error=error)
            await anyio.to_thread.run_sync(self._on_call, record)
        return result


async def _list_all_tools(session: ClientSession) -> list[Tool]:
    tools, cursor = [], None
    while True:
        page = await session.list_tools(cursor=cursor) if cursor else await session.list_tools()
        tools.extend(page.tools)
        cursor = page.nextCursor
        if not cursor:
            return tools


def _result(status: str, message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(
        {"status": status, "message": message}, ensure_ascii=False))])


def _status(result: CallToolResult) -> str:
    """Our status vocabulary for the call log; zbern results without one count as results."""
    try:
        body = json.loads(result.content[0].text)
    except (IndexError, AttributeError, ValueError):
        return "results"
    return body.get("status", "results") if isinstance(body, dict) else "results"


def attach(mcp: FastMCP, zbern: ZbernTools, base_instructions: str | None) -> None:
    """Serves the zbern tools beside the FastMCP server's own ones and extends its instructions."""
    server = mcp._mcp_server

    def update_instructions() -> None:
        server.instructions = "\n\n".join(
            p for p in (base_instructions, instructions_section(zbern.prefix, zbern.remote_instructions)) if p)

    async def list_tools() -> list[Tool]:
        remote = await zbern.list_tools()
        update_instructions()   # read per session on HTTP, so a refresh reaches new sessions
        local = await mcp.list_tools()
        names = {t.name for t in local}
        return local + [t for t in remote if t.name not in names]

    async def call_tool(name: str, arguments: dict[str, Any]):
        if zbern.owns(name) and mcp._tool_manager.get_tool(name) is None:
            return await zbern.call(name, arguments)
        return await mcp.call_tool(name, arguments)

    # Replaces the handlers FastMCP registered; input validation stays off, as FastMCP has it, and the zbern
    # server validates its own arguments.
    server.list_tools()(list_tools)
    server.call_tool(validate_input=False)(call_tool)
    update_instructions()


def from_settings(settings: Settings) -> ZbernTools | None:
    """The zbern tools for these settings, or None when they stay off (no URL, or no token for the server)."""
    if not settings.zbern_mcp_url:
        return None
    if settings.zbern_mcp_token is None:
        log.info("zbern tools stay off: ZBERN_MCP_TOKEN is not set (run `swiss-grounding setup` to install it)")
        return None
    token = settings.zbern_mcp_token.get_secret_value()
    return ZbernTools(
        http_transport(settings.zbern_mcp_url, token, settings.zbern_mcp_timeout_seconds),
        prefix=settings.zbern_mcp_prefix, exclude=settings.zbern_mcp_exclude,
        refresh_seconds=settings.zbern_mcp_refresh_seconds, timeout_seconds=settings.zbern_mcp_timeout_seconds,
        on_call=lambda record: record_call(settings.database_url, record))
