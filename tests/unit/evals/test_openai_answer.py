import asyncio
import json
from types import SimpleNamespace

import pytest

from swiss_grounding.evals.openai_answer import mcp_http_url, openai_tools, tool_loop


def _msg(content=None, calls=()):
    tool_calls = [SimpleNamespace(id=f"t{i}", type="function",
                                  function=SimpleNamespace(name=n, arguments=json.dumps(a)))
                  for i, (n, a) in enumerate(calls)] or None
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    message.model_dump = lambda exclude_none=True: {
        "role": "assistant", "content": content,
        **({"tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in tool_calls]} if tool_calls else {})}
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _Client:
    def __init__(self, replies):
        self.bodies = []
        self._replies = iter(replies)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **body):
        self.bodies.append(body)
        return next(self._replies)


def test_tool_calls_are_run_and_their_results_become_evidence():
    client = _Client([_msg(calls=[("swiss_search", {"question": "Hund anmelden", "locations": ["Bern"]})]),
                      _msg(content="Anmelden bei ... https://x")])
    ran = []

    async def call_tool(name, args):
        ran.append((name, args))
        return "result text https://x"
    evidence, answer = asyncio.run(tool_loop("Hund anmelden?", client=client, model="m", tools=[],
                                             call_tool=call_tool, system="sys"))
    assert ran == [("swiss_search", {"question": "Hund anmelden", "locations": ["Bern"]})]
    assert evidence == ["result text https://x"] and answer == "Anmelden bei ... https://x"
    assert client.bodies[1]["messages"][-1] == {"role": "tool", "tool_call_id": "t0",
                                                "content": "result text https://x"}


def test_the_loop_gives_up_after_max_turns():
    client = _Client([_msg(calls=[("swiss_search", {})])] * 3)

    async def call_tool(name, args):
        return "r"
    with pytest.raises(RuntimeError, match="3 turns"):
        asyncio.run(tool_loop("q", client=client, model="m", tools=[], call_tool=call_tool, system="s",
                              max_turns=3))


def test_mcp_tools_become_openai_function_tools():
    tool = SimpleNamespace(name="swiss_search", description="Search", inputSchema={"type": "object"})
    assert openai_tools([tool]) == [{"type": "function", "function": {
        "name": "swiss_search", "description": "Search", "parameters": {"type": "object"}}}]


def test_mcp_http_url_needs_an_http_config(tmp_path):
    http = tmp_path / "http.json"
    http.write_text(json.dumps({"mcpServers": {"swiss-grounding": {"type": "http", "url": "http://h/mcp"}}}))
    assert mcp_http_url(http) == "http://h/mcp"
    stdio = tmp_path / "stdio.json"
    stdio.write_text(json.dumps({"mcpServers": {"swiss-grounding": {"command": "uv"}}}))
    with pytest.raises(ValueError, match="serve --transport http"):
        mcp_http_url(stdio)
