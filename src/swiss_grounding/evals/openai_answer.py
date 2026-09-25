"""Answer a question with an OpenAI-compatible model (Apertus) using the MCP server's tools.

`claude -p` cannot drive a non-Claude model, so this runs the tool loop itself: it connects to the
running server over HTTP (`swiss-grounding serve --transport http`), offers its tools as function
tools, runs every call the model makes, and returns the tool results (evidence) and the final answer.
"""
import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

SERVER_NAME = "swiss-grounding"
MAX_TURNS = 8
ANSWER_TEMPERATURE = 0.2
# Apertus answers from memory unless made to search; Claude calls the tools on its own. The first turn
# therefore requires a tool call, later turns leave the choice to the model.
FIRST_TURN_TOOL_CHOICE = "required"


def mcp_http_url(config: Path) -> str:
    server = json.loads(config.read_text(encoding="utf-8"))["mcpServers"][SERVER_NAME]
    if server.get("type") != "http" or not server.get("url"):
        raise ValueError(f"{config} is not an HTTP config; start `swiss-grounding serve --transport http` "
                         "and use evals/judge/mcp-http.json")
    return server["url"]


def openai_tools(tools: Sequence) -> list[dict]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": t.inputSchema}} for t in tools]


def _arguments(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _complete(client, model: str, messages: list[dict], tools: list[dict], tool_choice: str):
    """One chat turn. A server that rejects the forced tool call ("Invalid tool call", seen on the
    Swisscom endpoint) gets the same turn once more with the choice left to the model. Any other
    BadRequestError (e.g. context length exceeded) is not this failure mode and is re-raised."""
    from openai import BadRequestError

    def create(choice: str):
        return client.chat.completions.create(model=model, messages=messages, tools=tools, tool_choice=choice,
                                              temperature=ANSWER_TEMPERATURE)
    try:
        return create(tool_choice)
    except BadRequestError as exc:
        if tool_choice == "auto" or "tool call" not in str(exc).lower():
            raise
        return create("auto")


async def tool_loop(question: str, *, client, model: str, tools: list[dict],
                    call_tool: Callable[[str, dict], Awaitable[str]], system: str,
                    max_turns: int = MAX_TURNS) -> tuple[list[str], str]:
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    evidence: list[str] = []
    for turn in range(max_turns):
        response = _complete(client, model, messages, tools, FIRST_TURN_TOOL_CHOICE if turn == 0 else "auto")
        message = response.choices[0].message
        if not message.tool_calls:
            return evidence, message.content or ""
        assistant_message = {"role": "assistant", "content": message.content or "", "tool_calls": [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in message.tool_calls]}
        messages = [*messages, assistant_message]
        for call in message.tool_calls:
            text = await call_tool(call.function.name, _arguments(call.function.arguments))
            evidence = [*evidence, text]
            messages = [*messages, {"role": "tool", "tool_call_id": call.id, "content": text}]
    raise RuntimeError(f"no final answer after {max_turns} turns")


def _innermost(error: BaseException) -> BaseException:
    """The first leaf of a (possibly nested) exception group."""
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    return error


async def _answer(question: str, *, client, model: str, mcp_url: str, system: str) -> tuple[list[str], str]:
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    # The MCP HTTP transport keeps its connection alive in a background task, so any exception raised
    # in this `async with` body - including a plain RuntimeError from `tool_loop` (e.g. "no final
    # answer") - can reach here wrapped in an anyio BaseExceptionGroup rather than on its own. The
    # unwrap branch below re-raises a non-connection error as itself, group or not.
    try:
        async with streamablehttp_client(mcp_url) as (read, write, _), ClientSession(read, write) as session:
            await session.initialize()
            tools = openai_tools((await session.list_tools()).tools)

            async def call_tool(name: str, args: dict) -> str:
                result = await session.call_tool(name, args)
                text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")
                text = text or "(no text result)"
                return f"tool error: {text}" if result.isError else text

            return await tool_loop(question, client=client, model=model, tools=tools, call_tool=call_tool,
                                   system=system)
    except BaseExceptionGroup as group:
        first = _innermost(group)
        if isinstance(first, (OSError, httpx.TransportError)):
            message = f"MCP server at {mcp_url} unreachable: {first!r}; start `swiss-grounding serve --transport http`"
            raise RuntimeError(message) from None  # noqa: TRY004 - not a type check: a failed connection
        raise first from None  # e.g. tool_loop's RuntimeError or an API error, unwrapped from the transport's group


def answer_with_tools(question: str, *, client, model: str, mcp_url: str, system: str) -> tuple[list[str], str]:
    return asyncio.run(_answer(question, client=client, model=model, mcp_url=mcp_url, system=system))
