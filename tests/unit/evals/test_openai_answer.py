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
    sent = client.bodies[1]["messages"]
    assert sent[-2] == {"role": "assistant", "content": "", "tool_calls": [
        {"id": "t0", "type": "function",
         "function": {"name": "swiss_search",
                      "arguments": json.dumps({"question": "Hund anmelden", "locations": ["Bern"]})}}]}
    assert sent[-1] == {"role": "tool", "tool_call_id": "t0", "content": "result text https://x"}


def test_two_tool_calls_in_one_turn_are_both_run_in_order():
    client = _Client([_msg(calls=[("swiss_search", {"q": 1}), ("swiss_search", {"q": 2})]),
                      _msg(content="done")])
    ran = []

    async def call_tool(name, args):
        ran.append((name, args))
        return f"result for {args['q']}"
    evidence, answer = asyncio.run(tool_loop("q?", client=client, model="m", tools=[],
                                             call_tool=call_tool, system="sys"))
    assert ran == [("swiss_search", {"q": 1}), ("swiss_search", {"q": 2})]
    assert evidence == ["result for 1", "result for 2"]
    assert answer == "done"


def _msg_with_raw_arguments(raw_arguments: str):
    call = SimpleNamespace(id="t0", type="function",
                           function=SimpleNamespace(name="swiss_search", arguments=raw_arguments))
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_malformed_tool_arguments_call_the_tool_with_empty_dict():
    client = _Client([_msg_with_raw_arguments("not json"), _msg(content="ok")])
    seen = []

    async def call_tool(name, args):
        seen.append(args)
        return "r"
    asyncio.run(tool_loop("q", client=client, model="m", tools=[], call_tool=call_tool, system="s"))
    assert seen == [{}]


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


def test_answer_reports_an_unreachable_mcp_server_clearly(monkeypatch):
    from contextlib import asynccontextmanager

    from swiss_grounding.evals import openai_answer

    @asynccontextmanager
    async def broken_client(url, *args, **kwargs):
        raise ExceptionGroup("connect failed", [ConnectionRefusedError("nope")])
        yield (None, None, None)  # pragma: no cover - never reached

    monkeypatch.setattr("mcp.client.streamable_http.streamablehttp_client", broken_client)
    with pytest.raises(RuntimeError, match="MCP server at http://dead/mcp unreachable"):
        asyncio.run(openai_answer._answer("q", client=object(), model="m", mcp_url="http://dead/mcp",
                                          system="s"))


def test_a_non_connection_error_in_the_group_is_reported_as_itself(monkeypatch):
    from contextlib import asynccontextmanager

    from swiss_grounding.evals import openai_answer

    @asynccontextmanager
    async def failing_client(url, *args, **kwargs):
        raise ExceptionGroup("body failed", [LookupError("401 from the model API")])
        yield (None, None, None)  # pragma: no cover - never reached

    monkeypatch.setattr("mcp.client.streamable_http.streamablehttp_client", failing_client)
    with pytest.raises(LookupError, match="401"):
        asyncio.run(openai_answer._answer("q", client=object(), model="m", mcp_url="http://h/mcp", system="s"))


def test_the_first_turn_requires_a_tool_call_and_later_turns_do_not():
    client = _Client([_msg(calls=[("swiss_search", {})]), _msg(content="done")])

    async def call_tool(name, args):
        return "r"
    asyncio.run(tool_loop("q", client=client, model="m", tools=[], call_tool=call_tool, system="s"))
    assert [b["tool_choice"] for b in client.bodies] == ["required", "auto"]


def test_a_nested_connection_error_is_reported_as_an_unreachable_server(monkeypatch):
    from contextlib import asynccontextmanager

    from swiss_grounding.evals import openai_answer

    @asynccontextmanager
    async def nested(url, *args, **kwargs):
        raise ExceptionGroup("outer", [ExceptionGroup("inner", [ConnectionRefusedError("nope")])])
        yield (None, None, None)  # pragma: no cover - never reached

    monkeypatch.setattr("mcp.client.streamable_http.streamablehttp_client", nested)
    with pytest.raises(RuntimeError, match="unreachable: ConnectionRefusedError"):
        asyncio.run(openai_answer._answer("q", client=object(), model="m", mcp_url="http://h/mcp", system="s"))


def test_a_rejected_forced_tool_call_is_retried_with_auto():
    import httpx
    from openai import BadRequestError

    rejected = BadRequestError("Invalid tool call", response=httpx.Response(400, request=httpx.Request("POST", "http://x")),
                               body=None)
    replies = iter([rejected, _msg(content="answer without tools")])
    bodies = []

    def create(**body):
        bodies.append(body)
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    async def call_tool(name, args):
        return "r"
    _evidence, answer = asyncio.run(tool_loop("q", client=client, model="m", tools=[], call_tool=call_tool, system="s"))
    assert [b["tool_choice"] for b in bodies] == ["required", "auto"] and answer == "answer without tools"
