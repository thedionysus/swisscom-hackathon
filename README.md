# Swiss Grounding MCP

Jurisdiction-aware retrieval over Swiss public sources, exposed as an MCP server and a CLI.

**This repository and its prebuilt database are private.** If you are an evaluator, you should
already have been added as a collaborator (repository Settings -> Collaborators); if not, ask for
access before starting. Setup below downloads the prebuilt database from a release of this
repository with `gh`, using your own GitHub login, so `gh auth login` with that account is a
prerequisite, not optional.

## What it answers

The server's own `swiss_scope` tool states this; the text below is its exact output, and is what
the server tells a client that asks about something outside it:

> Covered: federal information for all of Switzerland; cantonal information for Zurich, Bern,
> Vaud, Geneva, Ticino and Graubünden; municipal services for Zürich, Bern, Lausanne, Genève,
> Lugano, Chur and Scuol; lookups for health insurance premiums, public transport connections, the
> reference interest rate. Not covered: places outside Switzerland; computed amounts such as tax
> bills or pensions (the official rules and calculators are cited instead); looking up a specific
> company in the commercial register (how the register works is covered); live weather forecasts,
> statistics and geodata (MeteoSwiss hazard guidance is covered); cantonal and municipal rules
> outside the named cantons and municipalities.

The challenge's five sample questions, and what the server does for each:

| # | Question | What the server does |
|---|---|---|
| 1 | *Wann wird bei uns das nächste Mal Karton abgeholt?* (no place given) | `swiss_search` returns `needs_location`: it asks for the municipality before answering, because no federal passage covers a waste-collection date. |
| 2 | *Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?* | `swiss_search` with `locations=["Vaud"]` returns the federal 12-month rule (VZV/OAC, SR 741.51) and the Vaud cantonal procedure page, both in French. |
| 3 | *Premio mensile più basso, adulto 30 anni, Lugano, franchigia 2500?* | `swiss_premium(municipality="Lugano", age=30, deductible=2500)`: a lookup over the loaded BAG premium table, not a text search. |
| 4 | *Cura èn las vacanzas d'atun 2026 per la scola da Scuol?* (Romansh) | `swiss_search` resolves Scuol (GR) and returns the school's 2026 autumn-holiday dates from the Scuol source. |
| 5 | *Rundfunkbeitrag nach meinem Umzug nach Konstanz?* | With `locations=["Konstanz"]` (or "Konstanz, Deutschland") the resolver cannot place it in Switzerland, so `swiss_search` returns `outside_scope` and tells the client to look elsewhere; it does not guess a Swiss fee. Without a location argument, "Konstanz" is not recognised as foreign (ADR 0013) and the server asks back instead — a known, accepted gap, see `docs/CHALLENGE-FIT.md`. |

## Setup (no API key)

Requirements:

- **Docker**, with at least 6 GB of memory allocated to it, and about 15 GB of free disk (the
  prebuilt database dump plus its restored size).
- **`uv`** (Python package/venv manager).
- **`torch` and the local models** (`bge-m3` and a cross-encoder reranker, a few GB total): pulled
  in by `uv sync --extra embed` and downloaded once by `setup` below.
- **The GitHub CLI, `gh`**, logged in as an account with access to this private repository:
  `gh auth login`. `setup` uses it to download the prebuilt database from a release asset; without
  access, the download is refused with an actionable message.

Steps, in order:

```bash
cp .env.example .env                    # already points at the compose database; leave QUERY_EMBEDDER unset
docker compose up -d db
uv sync --extra embed
uv run swiss-grounding setup             # downloads, verifies and restores the dump; pre-downloads the models
uv run swiss-grounding serve             # starts the MCP server over stdio
```

`setup` needs no API key: the prebuilt database already carries the bge-m3 index and the
descriptions it depends on (ADR 0017). It prints how long the restore and index rebuild took.
It also installs the team's shared translation key into `.env` when one is published on the
release (see "Translation at question time"); without one, translation simply stays off.

After `setup` has run once, set `HF_HUB_OFFLINE=1` in `.env` to stop the model libraries from
checking the Hugging Face Hub for updates at every start.

Connect an MCP client with the config in `evals/judge/mcp.json`:

```json
{
  "mcpServers": {
    "swiss-grounding": {
      "command": "uv",
      "args": ["run", "swiss-grounding", "serve"]
    }
  }
}
```

For Claude Code: `claude mcp add swiss-grounding --scope user -- uv --directory "$(pwd)" run swiss-grounding serve`,
then open a new session and run `/mcp` to confirm the six tools are listed.

## Tools

| Tool | Purpose |
|---|---|
| `swiss_search(question, locations, translations, as_of, limit)` | Find passages in official Swiss sources that answer a question, for up to three places. Returns citations with `passage`, `url`, `publisher`, `extent_label`, `tier`, `relevance`, and dates; abstains with `no_evidence` when nothing relevant was found. |
| `swiss_get_document(document_id, chunk_id, reference, language)` | Read the whole article or section around a search hit, or look one up by official reference (e.g. "Art. 336c OR") or URL. |
| `swiss_scope()` | What this server covers and what it does not — quote it verbatim when telling a user a question is not covered. |
| `swiss_premium(municipality, age, deductible, accident, model, year, limit)` | Cheapest monthly basic health-insurance premiums (BAG data) for a Swiss municipality, age and deductible. |
| `swiss_connections(origin, destination, date, time, limit)` | Next public transport connections between two Swiss stops (live timetable). |
| `swiss_reference_rate()` | The current Swiss mortgage reference interest rate for rents (BWO), with its effective date. |

Chunks are retrieved on their English translation; the original German, French, Italian or Romansh
text is stored and can be requested through `swiss_get_document`.

### Swiss Parliament tools (optional, from zbern.ch)

Questions about the Federal Parliament and federal popular votes (members, business items, debates,
roll-call votes, vote results down to municipality, upcoming votes) are answered by the zbern.ch MCP
server, a separate server with its own database. Set `ZBERN_MCP_URL` and our server lists its tools
beside the six above, prefixed `zbern_`, and forwards calls to it (ADR 0018):

```bash
ZBERN_MCP_URL=https://mcp.zbern.ch/mcp      # or a local run of the zbern-mcp repository
ZBERN_MCP_TOKEN=...                         # bearer token for the hosted endpoint; never commit it
ZBERN_MCP_EXCLUDE=                          # optional, zbern tool names not to serve, comma-separated
```

The zbern tools, their descriptions and the zbern instructions are discovered from that server and
re-read every five minutes, so they follow its changes without a change here. If it cannot be reached,
our own tools keep working and a `zbern_*` call answers `source_unavailable`.

## How it ranks and when it abstains

Candidates come from dense, sparse and keyword search per language store, merged with RRF into the
top 30, then collapsed into translation groups and scored by a cross-encoder reranker (the group's
version in the question's language when one exists, otherwise its best-scoring version). The
server orders results by that reranker score and abstains with `no_evidence` when the top score is
below a fitted threshold; once the golden set is labelled, the threshold comes from a logistic
relevance model fit on reranker score, same-language flag, RRF rank, corroboration and other
features, chosen for a target precision on a held-out split (ADR 0012).

`swiss_search` decides its response status in a fixed order: a place outside Switzerland gets
`outside_scope` (never a guess); a local question with no place given gets `needs_location` unless
a federal passage already answers it; a Swiss place outside the declared cantons/municipalities
gets federal evidence plus `outside_scope` for the rest; a failed live lookup gets
`source_unavailable`; and a top relevance score below the abstention threshold gets `no_evidence`
(ADR 0013).

## Rebuilding the index

The declared-scope corpus is built by the encoding pipeline described end to end in
`docs/ENCODING-RUNBOOK.md` (fetch, OCR, describe, embed, index). `RESPECT_ROBOTS=true` is the
documented default switch for robots.txt / terms-of-use compliance during crawling
(`.env.example`); it is on by default and must stay on unless a source's own terms are checked
individually. After encoding finishes, `docs/SERVING-RUNBOOK.md` covers the remaining steps:
serving schema, calendars, lookup data, evaluation gates, and publishing the prebuilt dump.

## Evaluation

The numbers below come from running these commands, in this order, against the encoded corpus, and
pasting their output verbatim (do not round up numbers or omit failing rows):

```bash
uv run swiss-grounding eval golden --split holdout --record
uv run swiss-grounding eval recall
uv run swiss-grounding eval faithfulness
uv run swiss-grounding serving stats
```

Record the date and `git rev-parse HEAD` of the run alongside the output.

**Results: pending the first run on the encoded corpus (see `docs/SERVING-RUNBOOK.md`).**

## Legacy pipeline

The sections below describe the original ingest pipeline (source registry, fake-backend quick
start, offline demo). It predates the declared-scope corpus and the serving track above; it still
works, but evaluators should use "Setup (no API key)" instead.

### Quick start (fake translation and embeddings)

This path needs no API key or model download and runs in a couple of minutes. Search
quality is meaningless with fake embeddings; it is for checking that the plumbing works.

    cp .env.example .env
    docker compose up -d db
    uv sync
    uv run swiss-grounding db init          # tables and pgvector extension
    uv run swiss-grounding db seed          # location tree and source registry
    CRAWL_MAX_PAGES=15 uv run swiss-grounding ingest --source fedlex
    CRAWL_MAX_PAGES=15 uv run swiss-grounding ingest --source ch_ch
    uv run swiss-grounding ingest --source open_erz
    uv run swiss-grounding query "What does the Animal Welfare Act require of dog owners?" --location Switzerland
    uv run swiss-grounding query "When is cardboard collected in 8003?" --location 8003 --categories waste

### Real backends

For real answers, switch embeddings to bge-m3 and translation to Claude before ingesting.

    uv sync --extra embed                    # sentence-transformers and torch

Edit `.env`:

    EMBEDDING_BACKEND=sentence_transformers
    EMBEDDING_MODEL=BAAI/bge-m3
    EMBEDDING_DIM=1024
    LLM_BACKEND=anthropic
    LLM_MODEL=claude-sonnet-5
    ANTHROPIC_API_KEY=sk-ant-...

Then start from an empty database and ingest everything:

    docker compose down -v && docker compose up -d db
    uv run swiss-grounding db init
    uv run swiss-grounding db seed
    CRAWL_MAX_PAGES=15 uv run swiss-grounding ingest --all

What to expect:

- The first run downloads the bge-m3 model, about 2 GB, into `~/.cache/huggingface`.
- Translation makes one Claude call per section plus one per document, sequentially. A
  federal law takes ten minutes or more; a 15-page crawl a few minutes; a 200-page crawl
  hours. A crawled page now yields a section per heading rather than one section for the
  whole page, so a content-heavy page costs tens of calls; budget accordingly. Start with `CRAWL_MAX_PAGES=15`, then re-run with a larger budget later; unchanged
  pages are skipped.
- Only ingest uses the Anthropic API. Search and the MCP server run entirely locally, so
  an empty credit balance does not stop chat from working.
- The embedding dimension is fixed when the schema is created. Changing it means
  `docker compose down -v` and starting over.

### Translation at question time (optional key)

The server can translate the question into every other language store before searching and the
cited passages back into the question's language afterwards (ADR 0018). It uses Supertext. Put
the key in `.env`:

    SUPERTEXT_API_KEY=...

The key is shared through the private release, never through git: a team member with the key in
their own `.env` runs `uv run swiss-grounding dump publish-key`, which uploads it as the asset
`supertext.env` next to the corpus dump. Everyone else receives it on their next
`uv run swiss-grounding setup`, which writes it into their `.env`. Anyone with access to the
repository can read it, so keep a dedicated key for this project and rotate it from the Supertext
cockpit when the evaluation is over.

Nothing else changes: without the key the server searches every store with the question as asked,
as before. `TRANSLATE_QUERY_LANGUAGES` (default `de,fr,it,en`; Romansh is off because the reranker
over-scores Romansh pages against a Romansh query) limits the stores translated into; `TRANSLATE_CITATIONS=false` keeps the query translation but stops translating passages.
Every `swiss_search` then costs up to four Supertext requests before the search plus one per
source language of the cited passages for each place, so a golden-set run spends credit.

### Which steps need an API key

The declared-scope corpus (`swiss-grounding corpus …`, steps in `docs/ENCODING-RUNBOOK.md`)
is built in stages. Only some of them call a paid API:

| Stage | Needs a key? |
|---|---|
| `corpus fetch` (crawl Fedlex and the official sites) | No |
| `corpus ocr` (transcribe scanned PDF pages) | Yes: OpenAI (or Anthropic) |
| `corpus describe` (a short description of every document and chunk) | Yes: OpenAI (or Anthropic) |
| `corpus embed` for `openai-3l` (only when it is in `CORPUS_INDEXES`) | Yes: OpenAI |
| `corpus embed` for `bge-m3` (local model, the `CORPUS_INDEXES` default) | No, but it embeds the descriptions |
| Search and the MCP server | No: questions are embedded locally with bge-m3 |

**Even the local bge-m3 index needs the API, indirectly.** Every chunk is embedded as
breadcrumb + description + text (ADR 0005). The description is what places a bare
article under its subject and adds the words a resident would use, and it is written by
a language model. So a full-quality local index can only be built after `corpus describe`
has run with a key. At the current corpus size (about 130k chunks) the whole paid part
costs roughly $14 at batch prices, well under the $100 cap.

`CORPUS_INDEXES` decides which embedding indexes are built, and so whether the key also
pays for embeddings: the default `bge-m3` is local; add `openai-3l` to also build the
OpenAI index. `corpus run` does every stage after `corpus fetch` in order, within the budget.

Two ways around it:

- **Use the prebuilt database dump** (published after the encoding run). It contains the
  descriptions and both indexes, so evaluators need no key at all. A key is only needed
  to rebuild the corpus.
- **Build without descriptions:** `corpus embed --index bge-m3 --allow-undescribed`
  embeds breadcrumb + text only. It runs fully offline and gives a working index, at lower
  retrieval quality. Once descriptions exist, the changed text is detected and those
  chunks are embedded again.

### Connect a chat client (legacy)

The server speaks MCP over stdio. Register it once and the client starts it on demand.
The Docker database must be running whenever you chat.

**Claude Code**

    claude mcp add swiss-grounding --scope user -- \
      uv --directory "/absolute/path/to/swisscom-hackathon" run swiss-grounding serve --transport stdio

Open a new session, run `/mcp` to confirm six tools are listed, and ask a question.

**Claude Desktop**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` and restart:

    {
      "mcpServers": {
        "swiss-grounding": {
          "command": "uv",
          "args": ["--directory", "/absolute/path/to/swisscom-hackathon",
                   "run", "swiss-grounding", "serve", "--transport", "stdio"]
        }
      }
    }

**Other clients** can use `--transport http` for a streamable HTTP endpoint.

Good first questions:

- "When is cardboard collected in 8003?" shows the structured `event_date` and the
  past-event penalty.
- "What are the leash rules for dogs in Kanton Zürich?" combines federal law with cantonal
  and municipal pages.
- "What are the noise rules in Geneva?" shows the coverage tool reporting no live data
  instead of the assistant guessing.

### Operating the ingest

    uv run swiss-grounding ingest --source <id>      # one source
    uv run swiss-grounding ingest --all              # every registered source

Each run prints one line per source, `added=N modified=N unchanged=N withdrawn=N failed=N`,
followed by one line per failure with the URL and reason. Runs are incremental: unchanged
pages are skipped via ETag, Last-Modified and content hashes; changed pages get a new
version and the old one is kept as `superseded`; pages that disappeared are marked
`withdrawn`. Every run is recorded per source in `ingest_run`, which is what feeds the
`health` fields in `swiss_coverage`.

Things that trip people up:

- **Source configuration lives in the database.** `ingest` reads the `source` table, not the
  YAML files under `src/swiss_grounding/registry/sources/`. After editing a YAML, run
  `uv run swiss-grounding db seed` again.
- **Schema changes are idempotent.** After pulling, run `db init` again; it adds new columns
  and tables without touching data.
- **A run commits only when it exits** (see issue #13). Do not kill a long run part way
  through unless you are prepared to lose the sources it has processed.
- **Settings** all come from `.env` or the environment: `CRAWL_MAX_PAGES` (default 200),
  `CRAWL_DELAY_SECONDS`, `FETCH_TIMEOUT_SECONDS`, `FETCH_RETRY_ATTEMPTS`,
  `FETCH_RETRY_BACKOFF_SECONDS`.

### Offline demo

Loads a small fixture of Zurich hiking and dog pages so the tools return something without
any network access. Fixture documents are flagged `fixture_only` in `swiss_coverage`.

    uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json

### Sources

    uv run swiss-grounding sources list
    uv run swiss-grounding sources review          # pending suggestions from MCP clients
    uv run swiss-grounding sources approve <id> --extent CH --authority institutional --categories hiking
    uv run swiss-grounding sources reject <id> --note "not a public source"

To add a source by hand, drop a YAML file in `src/swiss_grounding/registry/sources/`
following an existing one (`fetch_strategy` is `html_crawl`, `api`, `fedlex_sparql`, or `pdf`),
then run `db seed`.

Set `llm_tagging: false` for a source whose records describe themselves. Ingestion then makes
no model call for it at all: each chunk's context comes from the record template the source
already renders, and its topics from the source's own `categories`. This only suits a
single-category feed such as a waste calendar -- a source spanning several categories would
silently keep every chunk tagged with just its declared defaults.

Every other source costs one model call per document for a shared summary, plus one per chunk
for that chunk's context, topics and page-furniture verdict (ADR 0005). Chunks whose heading is
known page furniture are dropped before any call is made.

For those sources, `categories` stands in for a chunk the model tagged with nothing only when
exactly one category is declared. A source declaring several says what it *covers*, which is no
statement about an individual chunk: writing all five of `fedlex`'s onto one article would be
the very defect ADR 0003 removes. Such a chunk is stored with no topics at all.

### Tests

    uv run pytest tests/unit
    DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration

The integration suite creates a throwaway `swiss_grounding_test_*` database on that server
and drops it afterwards, so it is safe to point at the quick-start database. Run it
serially (no `pytest -n`).

### Further reading

Design: `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`
Plans: `docs/superpowers/plans/`
Research: `research/README.md`

### Evals (legacy probes)

Probes are hand-written adversarial questions under `evals/probes/`, one YAML file per location tier (city, communes, lookalikes). Each probe states the expected tool response and, once recorded, the observed one. `status: red` marks a probe the server fails today. See `CONTEXT.md` for the failure classes and `docs/adr/` for the decisions behind the expectations.

    uv run pytest tests/integration/test_probes_structural.py   # structural probes on fixtures, frozen clock
    uv run swiss-grounding eval probes --record                  # all probes on the live database, writes observed blocks
    uv run swiss-grounding eval judge                            # judge cases across models, needs the claude CLI
    uv run swiss-grounding locations fetch-register              # regenerate the committed commune register snapshot
    uv run swiss-grounding renarrow                              # re-file stored documents under the narrowing rule (no API calls)

The probes command exits 3 when a probe's red or green status disagrees with the live result.

The judge is always Fable 5.1, which is also one of the four answering models, so that row of the judge table is self-graded.

Red probes run as strict expected failures. When a fix makes one pass, pytest reports it and the probe's `status` must be flipped to green in its YAML file.
