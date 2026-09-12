# Swiss Grounding MCP

Jurisdiction-aware retrieval over Swiss public sources, exposed as an MCP server and a CLI.

## Quick start (real sources, fake translation and embeddings)

    cp .env.example .env
    docker compose up -d db
    uv sync
    uv run swiss-grounding db init
    uv run swiss-grounding db seed
    CRAWL_MAX_PAGES=15 uv run swiss-grounding ingest --source fedlex
    CRAWL_MAX_PAGES=15 uv run swiss-grounding ingest --source ch_ch
    uv run swiss-grounding ingest --source open_erz
    uv run swiss-grounding query "What does the Animal Welfare Act require of dog owners?" --location Switzerland
    uv run swiss-grounding query "When is cardboard collected in 8003?" --location 8003 --categories waste
    uv run swiss-grounding serve --transport stdio

Set `LLM_BACKEND=anthropic` and `ANTHROPIC_API_KEY` for real translation and tagging, and
`EMBEDDING_BACKEND=sentence_transformers` with `EMBEDDING_DIM=1024` for real embeddings.
The embedding dimension is fixed when the schema is created; recreate the database to change it
(`docker compose down -v`).

Re-running `ingest` is incremental: unchanged pages are skipped via ETag/Last-Modified and
content hashes, changed pages get a new version (the old one is kept as `superseded`), and
pages that disappeared are marked `withdrawn`.

## Offline demo

    uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json

## Sources

    uv run swiss-grounding sources list
    uv run swiss-grounding sources review          # pending suggestions from MCP clients
    uv run swiss-grounding sources approve <id> --extent CH --authority institutional --categories hiking
    uv run swiss-grounding sources reject <id> --note "not a public source"

MCP clients can propose sources with the `swiss_suggest_source` tool. Official government
domains are approved automatically as `official_info`; everything else waits for review.

## Tests

    uv run pytest tests/unit
    DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration
    # the suite creates a throwaway swiss_grounding_test_* database on that server and drops it
    # afterwards, so it is safe to point at the quick-start database; run serially (no pytest -n)

Design: `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`
Plans: `docs/superpowers/plans/`
Research: `research/README.md`
