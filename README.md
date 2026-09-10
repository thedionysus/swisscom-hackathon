# Swiss Grounding MCP

Jurisdiction-aware retrieval over Swiss public sources, exposed as an MCP server and a CLI.

## Quick start

    cp .env.example .env
    docker compose up -d db
    uv sync
    uv run swiss-grounding db init
    uv run swiss-grounding db seed
    uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json
    uv run swiss-grounding query "Do I need to leash my dog on hiking trails?" --location "Wiedikon"
    uv run swiss-grounding serve --transport stdio

## Tests

    uv run pytest tests/unit
    DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration

Design: `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`
Research: `research/README.md`
