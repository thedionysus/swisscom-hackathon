import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import typer

from swiss_grounding.app import build_query_core
from swiss_grounding.config import load_settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.models import QueryRequest


def _link(url: str, anchor: str | None) -> str:
    """Append the anchor unless the URL already carries a fragment."""
    if not anchor or "#" in url:
        return url
    return f"{url}#{anchor}"


app = typer.Typer(help="Swiss Grounding MCP command line.", no_args_is_help=True)
db_app = typer.Typer(help="Database commands.")
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init() -> None:
    """Create tables and the pgvector extension."""
    settings = load_settings()
    apply_schema(settings.database_url, settings.embedding_dim)
    typer.echo("schema applied")


@db_app.command("seed")
def db_seed() -> None:
    """Insert the location tree and seed source definitions."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    typer.echo("locations and sources seeded")


@app.command("load-fixture")
def load_fixture_cmd(path: Path) -> None:
    """Load a JSON fixture of documents and chunks (development and demo only)."""
    settings = load_settings()
    if not path.exists():
        typer.echo(f"fixture not found: {path}", err=True)
        raise typer.Exit(code=1)
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    with connect(settings.database_url) as conn:
        report = load_fixture(conn, path, embedder)
    typer.echo(f"loaded {report.documents} documents, {report.chunks} chunks")


@app.command("query")
def query_cmd(
    question: str,
    location: str | None = typer.Option(None, "--location", "-l"),
    categories: str | None = typer.Option(None, "--categories", "-c", help="comma-separated"),
    as_of: str | None = typer.Option(None, "--as-of", help="ISO date"),
    limit: int = typer.Option(8, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run the query core and print evidence. Exit code 2 when a location is needed."""
    core = build_query_core(load_settings())
    request = QueryRequest(
        question=question, location=location,
        categories=tuple(c.strip() for c in categories.split(",")) if categories else (),
        as_of=date.fromisoformat(as_of) if as_of else None, limit=limit,
    )
    resp = core.query(request)
    if as_json:
        typer.echo(json.dumps(asdict(resp), default=str, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"status: {resp.status}")
        if resp.resolved_location_id:
            typer.echo(f"location: {resp.resolved_location_label} ({resp.resolved_location_id}, {resp.resolution_method})")
        if resp.message:
            typer.echo(resp.message)
        for i, c in enumerate(resp.citations, 1):
            typer.echo(f"\n[{i}] {c.title_en} — {c.extent_label} / {c.authority} (score {c.score})")
            typer.echo(f"    {_link(c.url, c.anchor)}")
            typer.echo(f"    {c.snippet_en}")
        typer.echo(f"\n{resp.notice}")
    if resp.status == "needs_location":
        raise typer.Exit(code=2)


@app.command("serve")
def serve_cmd(transport: str = typer.Option("stdio", "--transport", help="stdio or http")) -> None:
    """Start the MCP server."""
    from swiss_grounding.mcp_server.server import build_server

    server = build_server(load_settings())
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "http":
        server.run(transport="streamable-http")
    else:
        typer.echo("transport must be stdio or http", err=True)
        raise typer.Exit(code=1)
