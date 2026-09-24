---
status: proposed
date: 2026-09-24
amends: 0015-six-tool-contract
---

# Swiss Parliament questions are answered by the zbern.ch MCP server, whose tools we serve under a `zbern_` prefix

The zbern.ch MCP server covers what our corpus does not: the Federal Parliament (members, business items, debate transcripts, roll-call votes) and federal popular votes (results down to municipality, upcoming votes). Its data comes from a separate pipeline and database (DuckDB, rebuilt nightly from the Parliament's open data), and it is developed on its own schedule. Merging the two databases is not worth it for the hackathon; clients should still see one server.

- Our server connects to the zbern server as an MCP client and lists its tools beside ours, each prefixed `zbern_` (`zbern_search_person`, `zbern_get_business`, ...). A call to a `zbern_*` tool is forwarded with its own name and arguments, and the zbern result is returned verbatim.
- Nothing about the zbern tools is copied into this repository. Names, descriptions, input schemas and the zbern server's instructions are discovered at start and re-read every `ZBERN_MCP_REFRESH_SECONDS` (default 300), so the zbern side adds, changes or removes tools without a change here. `ZBERN_MCP_EXCLUDE` hides tools we do not want to serve.
- Our instructions gain a routing paragraph (`zbern_*` for parliament and popular votes, `swiss_*` for law, services and lookups) followed by the zbern server's own instructions.
- It is off unless `ZBERN_MCP_URL` is set. The zbern server is either the hosted endpoint (`https://mcp.zbern.ch/mcp`, bearer token in `ZBERN_MCP_TOKEN`) or a local run of its own repository.
- A zbern outage never breaks our server: its tools stay listed from the last successful discovery (none if there never was one), and a call answers `source_unavailable`. Calls go into `serving.call_log` like ours.

## Considered Options

- One server over both databases: the fewest moving parts at run time, but it couples two codebases and two data pipelines that change daily during the hackathon.
- A separate gateway server in front of both: a third thing to build, host and hand to the evaluators, for the same result.
- Copying the zbern tool definitions into this repository: every change on the zbern side would need a change here.
- One `ask_parliament(question)` tool that runs its own model against the zbern server: a second model per call, slower, non-deterministic, and the zbern citations reach the client second-hand.

## Consequences

- With the integration on, the contract is our six tools plus the zbern tools; a client may see 20 tools. `ZBERN_MCP_EXCLUDE` trims it (for example the raw-SQL tools `query,list_tables,describe_table`) if the golden set shows weaker models choosing badly.
- `swiss_scope` still states only our own scope. The routing paragraph tells the client to use `zbern_*` for parliament questions regardless; folding the zbern coverage into `swiss_scope` is a follow-up.
- `outputSchema` of the zbern tools is not passed on, because a `source_unavailable` answer could not satisfy an arbitrary schema; the zbern tools return JSON text, so nothing is lost today.
- Each forwarded call opens a new connection to the zbern server (initialize, then the call). The zbern server is stateless, so this costs one extra round trip and nothing else.
