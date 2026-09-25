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


async def tool_loop(question: str, *, client, model: str, tools: list[dict],
                    call_tool: Callable[[str, dict], Awaitable[str]], system: str,
                    max_turns: int = MAX_TURNS) -> tuple[list[str], str]:
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    evidence: list[str] = []
    for _ in range(max_turns):
        response = client.chat.completions.create(model=model, messages=messages, tools=tools,
                                                  temperature=ANSWER_TEMPERATURE)
        message = response.choices[0].message
        if not message.tool_calls:
            return evidence, message.content or ""
        messages = [*messages, message.model_dump(exclude_none=True)]
        for call in message.tool_calls:
            text = await call_tool(call.function.name, _arguments(call.function.arguments))
            evidence = [*evidence, text]
            messages = [*messages, {"role": "tool", "tool_call_id": call.id, "content": text}]
    raise RuntimeError(f"no final answer after {max_turns} turns")


async def _answer(question: str, *, client, model: str, mcp_url: str, system: str) -> tuple[list[str], str]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(mcp_url) as (read, write, _), ClientSession(read, write) as session:
        await session.initialize()
        tools = openai_tools((await session.list_tools()).tools)

        async def call_tool(name: str, args: dict) -> str:
            result = await session.call_tool(name, args)
            return "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")

        return await tool_loop(question, client=client, model=model, tools=tools, call_tool=call_tool,
                               system=system)


def answer_with_tools(question: str, *, client, model: str, mcp_url: str, system: str) -> tuple[list[str], str]:
    return asyncio.run(_answer(question, client=client, model=model, mcp_url=mcp_url, system=system))
