# Swiss Grounding MCP

Jurisdiction-aware retrieval over Swiss public sources, exposed as an MCP server and a CLI.

Ask a chat assistant "When is cardboard collected in 8003?" or "Can my dog run off leash in
Kanton Zürich?" and it answers from federal law, cantonal and municipal pages, and the Zurich
waste calendar, with citations, instead of guessing. Every answer says which jurisdiction it
applies to and admits when a place is not covered.

## How it works

1. **Ingest.** Fetchers pull pages from registered sources (Fedlex SPARQL, HTML crawls of
   ch.ch, zh.ch, stadt-zuerich.ch and schweizer-wanderwege.ch, the Open ERZ waste API).
   Each document is translated to English, tagged with topic categories, narrowed to the
   jurisdiction it applies to, chunked, embedded, and stored in Postgres with pgvector.
2. **Retrieve.** A hybrid search (vector plus full text) ranks chunks, filtered by location
   and category, with a penalty for calendar events that have already passed.
3. **Serve.** An MCP server exposes search, coverage, and document tools that a chat client
   such as Claude Code or Claude Desktop calls on the user's behalf.

## Quick start (fake translation and embeddings)

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

## Real backends

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

## Which steps need an API key

The declared-scope corpus (`swiss-grounding corpus …`, steps in `docs/ENCODING-RUNBOOK.md`)
is built in stages. Only some of them call a paid API.

On a database that has never held the corpus (and was not restored from a dump, such as
the one `swiss-grounding setup` restores), the corpus schema has to exist first. As of
2026-09-24 `swiss-grounding corpus init` creates it, and re-running it is harmless.
Without it, `corpus status` fails with `relation "corpus.document" does not exist`. The
runbook §1 has the details; if the commands change, check `swiss-grounding corpus --help`.

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

## Connect a chat client

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

## Tools

| Tool | Purpose |
|---|---|
| `swiss_resolve_location(query)` | Resolve a place name, canton, district, or postal code to a jurisdiction node. |
| `swiss_search(question, location, categories, as_of, limit, response_format)` | Hybrid search with jurisdiction filtering. Returns citations with `url`, `snippet_en`, `extent_id`, `authority`, `valid_from`, `event_date`, and a `notice` explaining what was retrieved. `response_format="detailed"` adds original-language snippets and `retrieved_at`. |
| `swiss_get_document(document_id, chunk_id)` | Full document or one chunk from a previous result. |
| `swiss_list_categories()` | Topic categories that `swiss_search` filters on. Passing them excludes evidence carrying none of them, rather than reranking it; a question whose subject nothing on the jurisdiction path covers returns `no_evidence`. |
| `swiss_coverage(location)` | Per source and jurisdiction: document count, last retrieval, and fetch health. `health` is `ok`, `degraded`, `failing`, or `unknown`; `fixture_only` marks rows that come only from demo data. A failing or fixture-only row is not live coverage even if `documents` is non-zero. |
| `swiss_suggest_source(url, reason, ...)` | Propose a new source. Official government domains are approved automatically as `official_info`; other domains wait for human review. |

Chunks are retrieved on their English translation; the original German, French, or Italian
text is stored and returned in `detailed` citations.

## Operating the ingest

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

## Offline demo

Loads a small fixture of Zurich hiking and dog pages so the tools return something without
any network access. Fixture documents are flagged `fixture_only` in `swiss_coverage`.

    uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json

## Sources

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

## Tests

    uv run pytest tests/unit
    DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration

The integration suite creates a throwaway `swiss_grounding_test_*` database on that server
and drops it afterwards, so it is safe to point at the quick-start database. Run it
serially (no `pytest -n`).

## Further reading

Design: `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`
Plans: `docs/superpowers/plans/`
Research: `research/README.md`

## Evals

Probes are hand-written adversarial questions under `evals/probes/`, one YAML file per location tier (city, communes, lookalikes). Each probe states the expected tool response and, once recorded, the observed one. `status: red` marks a probe the server fails today. See `CONTEXT.md` for the failure classes and `docs/adr/` for the decisions behind the expectations.

    uv run pytest tests/integration/test_probes_structural.py   # structural probes on fixtures, frozen clock
    uv run swiss-grounding eval probes --record                  # all probes on the live database, writes observed blocks
    uv run swiss-grounding eval judge                            # judge cases across models, needs the claude CLI
    uv run swiss-grounding locations fetch-register              # regenerate the committed commune register snapshot
    uv run swiss-grounding renarrow                              # re-file stored documents under the narrowing rule (no API calls)

The probes command exits 3 when a probe's red or green status disagrees with the live result.

The judge is always Fable 5.1, which is also one of the four answering models, so that row of the judge table is self-graded.

Red probes run as strict expected failures. When a fix makes one pass, pytest reports it and the probe's `status` must be flipped to green in its YAML file.
