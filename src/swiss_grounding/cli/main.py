import json
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import typer

from swiss_grounding.app import build_query_core
from swiss_grounding.cli.eval_commands import eval_app
from swiss_grounding.config import load_settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fetchers import build_fetcher
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.llm import build_llm
from swiss_grounding.ingest.pipeline import run_ingest
from swiss_grounding.ingest.reclean import reclean_all
from swiss_grounding.ingest.recontext import recontext_all
from swiss_grounding.ingest.renarrow import renarrow_all
from swiss_grounding.ingest.retitle import retitle_all
from swiss_grounding.ingest.run_log import record_run
from swiss_grounding.locations.repository import load_tree, prune_locations, upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.models import FetchStrategy
from swiss_grounding.registry.repository import load_sources, upsert_sources
from swiss_grounding.registry.suggestions import list_suggestions, review_suggestion
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.models import QueryRequest


def _link(url: str, anchor: str | None) -> str:
    """Append the anchor unless the URL already carries a fragment."""
    if not anchor or "#" in url:
        return url
    return f"{url}#{anchor}"


EXIT_CODES = {"invalid_request": 1, "needs_location": 2}
SWISS_TZ = ZoneInfo("Europe/Zurich")

app = typer.Typer(help="Swiss Grounding MCP command line.", no_args_is_help=True)
db_app = typer.Typer(help="Database commands.")
app.add_typer(db_app, name="db")
sources_app = typer.Typer(help="Source registry and suggestions.")
app.add_typer(sources_app, name="sources")
app.add_typer(eval_app, name="eval")
locations_app = typer.Typer(help="Location tree data.")
app.add_typer(locations_app, name="locations")


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
    locations = seed_locations()
    with connect(settings.database_url) as conn:
        upsert_locations(conn, locations)
        upsert_sources(conn, load_seed_sources())
        report = prune_locations(conn, [loc.id for loc in locations])
    typer.echo("locations and sources seeded")
    typer.echo(f"pruned {len(report.deleted)} stale communes")
    if report.kept_referenced:
        typer.echo(f"kept {len(report.kept_referenced)} referenced stale communes: {', '.join(report.kept_referenced)}")


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
    """Run the query core and print evidence.

    Exit code 1 when the request is invalid, 2 when a location is needed.
    """
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
            when = f" — event on {c.event_date.isoformat()}" if c.event_date else ""
            typer.echo(f"\n[{i}] {c.title_en} — {c.extent_label} / {c.authority} (score {c.score}){when}")
            typer.echo(f"    {_link(c.url, c.anchor)}")
            typer.echo(f"    {c.snippet_en}")
        typer.echo(f"\n{resp.notice}")
    raise typer.Exit(code=EXIT_CODES.get(resp.status, 0))


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

@app.command("ingest")
def ingest_cmd(
    source_id: str | None = typer.Option(None, "--source", help="source id; omit with --all"),
    all_sources: bool = typer.Option(False, "--all"),
) -> None:
    """Fetch, enrich, chunk, embed and persist one source or all sources. Exit 1 if a source is unknown."""
    if not source_id and not all_sources:
        typer.echo("pass --source <id> or --all", err=True)
        raise typer.Exit(code=1)
    settings = load_settings()
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    llm = build_llm(settings.llm_backend, settings.llm_model, settings.anthropic_api_key)
    run_id = uuid.uuid4().hex[:12]
    with connect(settings.database_url) as conn:
        tree = load_tree(conn)
        sources = load_sources(conn)
        selected = sources if all_sources else tuple(s for s in sources if s.id == source_id)
        if not selected:
            typer.echo(f"unknown source: {source_id}", err=True)
            raise typer.Exit(code=1)
        for source in selected:
            fetcher = build_fetcher(source.fetch_strategy, settings)
            started_at = datetime.now(UTC)
            report = run_ingest(conn, source, fetcher, llm, embedder, tree, run_id=run_id)
            record_run(conn, report, started_at=started_at, finished_at=datetime.now(UTC))
            typer.echo(
                f"{source.id}: added={report.added} modified={report.modified} unchanged={report.unchanged} "
                f"withdrawn={report.withdrawn} skipped={report.skipped} failed={report.failed} run={run_id}"
            )
            for error in report.errors:
                typer.echo(f"  ! {error.url}: {error.reason}", err=True)


@app.command("renarrow")
def renarrow_cmd() -> None:
    """Re-run extent narrowing over every stored document using its stored English text."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        tree = load_tree(conn)
        report = renarrow_all(conn, tree)
    typer.echo(f"examined {report.examined}, moved {report.moved}, relabelled {report.relabelled}, skipped {report.skipped}")


@app.command("reclean")
def reclean_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="report what would be dropped, without deleting"),
) -> None:
    """Delete boilerplate chunks and any document left with none. No network, no model calls."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        report = reclean_all(conn, dry_run=dry_run)
    for source in report.by_source:
        typer.echo(f"{source.source_id}: dropped_chunks={source.dropped_chunks} dropped_documents={source.dropped_documents}")
    prefix = "dry run: " if dry_run else ""
    typer.echo(f"{prefix}examined={report.examined} dropped_chunks={report.dropped_chunks} dropped_documents={report.dropped_documents}")


@app.command("retitle")
def retitle_cmd(
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="report the titles that would change, without writing"),
) -> None:
    """Repair stored Fedlex titles from the SPARQL endpoint. Run this before `recontext`.

    The query is free; each title that actually changes costs one translation call.
    """
    settings = load_settings()
    llm = build_llm(settings.llm_backend, settings.llm_model, settings.anthropic_api_key)
    fetcher = build_fetcher(FetchStrategy.FEDLEX_SPARQL, settings)
    with connect(settings.database_url) as conn:
        report = retitle_all(conn, fetcher, llm, dry_run=dry_run)
    for change in report.changes:
        typer.echo(f"{change.identifier}: {change.before!r} -> {change.after!r}")
    for error in report.errors:
        typer.echo(f"  ! {error.url}: {error.reason}", err=True)
    prefix = "dry run: " if dry_run else ""
    typer.echo(f"{prefix}examined={report.examined} updated={report.updated} "
               f"skipped={report.skipped} failed={report.failed}")


@app.command("recontext")
def recontext_cmd(
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="report the scope and the bill, without calling or writing"),
    force: bool = typer.Option(False, "--force",
                               help="describe chunks that already carry a context"),
) -> None:
    """Re-enrich every stored chunk from text already in the database. No fetch, no translation.

    One description call per chunk and one summary call per document, committed as they are paid
    for, so an interrupted run is resumable. Run `retitle` first: a document titled by its SR
    number is refused, not described.
    """
    settings = load_settings()
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model,
                              settings.embedding_dim)
    llm = build_llm(settings.llm_backend, settings.llm_model, settings.anthropic_api_key)
    with connect(settings.database_url) as conn:
        report = recontext_all(conn, llm, embedder, dry_run=dry_run, force=force)
    for source in report.by_source:
        typer.echo(
            f"{source.source_id}: examined={source.examined} updated={source.updated} "
            f"skipped={source.skipped} deleted={source.deleted_chunks} failed={source.failed} "
            f"calls={source.describe_calls + source.summary_calls}"
        )
    for error in report.errors:
        typer.echo(f"  ! {error.url}: {error.reason}", err=True)
    prefix = "dry run: " if dry_run else ""
    typer.echo(
        f"{prefix}examined={report.examined} updated={report.updated} skipped={report.skipped} "
        f"deleted={report.deleted_chunks} failed={report.failed} "
        f"deleted_documents={report.deleted_documents} "
        f"calls={report.describe_calls + report.summary_calls} "
        f"(describe={report.describe_calls} summary={report.summary_calls})"
    )


@sources_app.command("list")
def sources_list() -> None:
    """List registered sources."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        for s in load_sources(conn):
            typer.echo(f"{s.id:24} {s.authority.value:14} {s.default_extent_id:14} {s.origin:13} {s.base_url}")


@sources_app.command("review")
def sources_review() -> None:
    """List pending source suggestions."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        pending = list_suggestions(conn, status="pending")
    if not pending:
        typer.echo("no pending suggestions")
    for s in pending:
        typer.echo(f"[{s.id}] {s.url}  ({s.domain_class})  reason: {s.reason}")


@sources_app.command("approve")
def sources_approve(
    suggestion_id: int,
    extent: str | None = typer.Option(None, "--extent"),
    authority: str | None = typer.Option(None, "--authority"),
    categories: str | None = typer.Option(None, "--categories", help="comma-separated"),
    note: str = typer.Option("", "--note"),
    reviewer: str = typer.Option("cli", "--reviewer"),
) -> None:
    """Approve a pending suggestion and register it as a source."""
    settings = load_settings()
    cats = tuple(c.strip() for c in categories.split(",")) if categories else ()
    try:
        with connect(settings.database_url) as conn:
            s = review_suggestion(conn, suggestion_id, approve=True, reviewer=reviewer, note=note,
                                  extent_id=extent, authority=authority, categories=cats)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(f"approved {s.url} as source {s.source_id}")


DEFAULT_OUT_OPTION = typer.Option(None, "--out")


@locations_app.command("fetch-register")
def fetch_register_cmd(
    snapshot_date: str = typer.Option(None, "--date", help="ISO date, default today"),
    out: Path | None = DEFAULT_OUT_OPTION,
) -> None:
    """Regenerate the committed commune register snapshot from BFS and LINDAS."""
    from swiss_grounding.locations.register import SNAPSHOT, write_register_csv
    from swiss_grounding.locations.register_fetch import fetch_register

    when = date.fromisoformat(snapshot_date) if snapshot_date else datetime.now(SWISS_TZ).date()
    communes = fetch_register(when)
    destination = out or SNAPSHOT
    write_register_csv(destination, communes)
    typer.echo(f"wrote {len(communes)} communes to {destination}")


@sources_app.command("reject")
def sources_reject(suggestion_id: int, note: str = typer.Option("", "--note"),
                   reviewer: str = typer.Option("cli", "--reviewer")) -> None:
    """Reject a pending suggestion."""
    settings = load_settings()
    try:
        with connect(settings.database_url) as conn:
            s = review_suggestion(conn, suggestion_id, approve=False, reviewer=reviewer, note=note)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(f"rejected {s.url}")
