"""The unpaid `corpus` commands: schema setup, manifest checks, fetching, and reporting.

`register(app)` adds them to the `corpus` Typer app defined in `corpus_commands`, which holds the paid
stages. The shared helpers used by both modules live here (`friendly_errors`, `usd`, `REFUSED_EXIT_CODE`).
"""
import functools
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import anthropic
import httpx
import openai
import psycopg
import typer

from swiss_grounding.config import Settings, load_settings
from swiss_grounding.corpus.budget import BudgetExceeded, spent
from swiss_grounding.corpus.connectors.fedlex import FedlexConnector
from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector, robots_verdict
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.connectors.pdf import PdfConnector
from swiss_grounding.corpus.db import apply_corpus_schema
from swiss_grounding.corpus.fetch_stage import run_fetch
from swiss_grounding.corpus.manifest import load_manifest, select_sources
from swiss_grounding.corpus.providers import INDEXES
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

REFUSED_EXIT_CODE = 2          # budget cap, fake providers on a real database, missing price
ERROR_EXIT_CODE = 1
SWISS_TZ = ZoneInfo("Europe/Zurich")


def usd(amount: float) -> str:
    """Cents matter for pilots and small runs; whole runs read better rounded."""
    return f"${amount:.2f}" if amount >= 1 else f"${amount:.4f}"


def swiss_today() -> date:
    return datetime.now(tz=SWISS_TZ).date()


def corpus_http(settings: Settings) -> httpx.Client:
    return httpx.Client(headers={"user-agent": settings.corpus_user_agent}, timeout=settings.fetch_timeout_seconds)


def _first_line(exc: Exception) -> str:
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__


def friendly_errors[**P, R](command: Callable[P, R]) -> Callable[P, R]:
    """One line instead of a traceback for the failures an operator can act on."""
    @functools.wraps(command)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return command(*args, **kwargs)
        except BudgetExceeded as exc:
            typer.echo(f"refused: {exc}")
            raise typer.Exit(REFUSED_EXIT_CODE) from exc
        except psycopg.OperationalError as exc:
            typer.echo(f"database error: {_first_line(exc)}")
            raise typer.Exit(ERROR_EXIT_CODE) from exc
        except (openai.APIError, anthropic.APIError) as exc:
            typer.echo(f"provider error ({exc.__class__.__name__}): {_first_line(exc)}")
            raise typer.Exit(ERROR_EXIT_CODE) from exc
    return wrapper


# --- init -------------------------------------------------------------------------------------------

@friendly_errors
def init_cmd() -> None:
    """Apply the public schema and the corpus schema."""
    settings = load_settings()
    apply_schema(settings.database_url, settings.embedding_dim)
    apply_corpus_schema(settings.database_url)
    typer.echo("corpus schema ready")


# --- check-manifest ---------------------------------------------------------------------------------

def _check_html(http: httpx.Client, entry, respect_robots: bool) -> int:
    problems = 0
    selector = entry.config.get("language_links_selector")
    for url in entry.config["start_urls"]:
        try:
            response = http.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            typer.echo(f"{entry.id}: FAILED {url} ({exc})")
            problems += 1
            continue
        alternates = len(page_meta(response.text, str(response.url), language_links_selector=selector).alternates)
        verdict = robots_verdict(http, url, respect=respect_robots)
        typer.echo(f"{entry.id}: {response.status_code} {url} -> {response.url} robots={verdict} "
                   f"alternates={alternates}")
        problems += int(response.status_code >= 400 or verdict == "disallowed")
    return problems


def _check_fedlex(connector: FedlexConnector, entry) -> int:
    problems = 0
    for sr in entry.config["sr_numbers"]:
        try:
            found = connector.probe(str(sr), "de")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            typer.echo(f"{entry.id}: SR {sr} FAILED ({exc!r})")
            problems += 1
            continue
        typer.echo(f"{entry.id}: SR {sr} de " + (f"{found} in-force consolidation(s)" if found else "NOT FOUND"))
        problems += int(not found)
    return problems


@friendly_errors
def check_manifest_cmd(path: Path) -> None:
    """Validate a manifest and probe every start URL and SR number. Exit 1 on any problem."""
    settings = load_settings()
    manifest = load_manifest(path)
    with connect(settings.database_url) as conn:
        extents = {r["id"] for r in conn.execute("select id from location").fetchall()}
    problems = 0
    with corpus_http(settings) as http:
        fedlex = FedlexConnector(http, swiss_today, settings.data_dir)
        for entry in manifest.sources:
            if entry.extent_id not in extents:
                typer.echo(f"{entry.id}: unknown extent {entry.extent_id}")
                problems += 1
            if entry.connector == "html":
                problems += _check_html(http, entry, settings.respect_robots)
            else:
                problems += _check_fedlex(fedlex, entry)
    typer.echo(f"{problems} problem(s)")
    raise typer.Exit(1 if problems else 0)


# --- fetch ------------------------------------------------------------------------------------------

def _tally(counts) -> str:
    return " ".join(f"{k}={v}" for k, v in sorted(counts.items()))


@friendly_errors
def fetch_cmd(manifest: Annotated[Path, typer.Option("--manifest")],
              tier: Annotated[int, typer.Option("--tier")] = 1,
              source: Annotated[list[str] | None, typer.Option("--source", help="Repeatable; narrows the tier.")] = None,
              workers: Annotated[int, typer.Option("--workers")] = 4) -> None:
    """Fetch the manifest's sources, persist documents and chunks, promote scheduled versions that are due."""
    settings = load_settings()
    try:
        specs = select_sources(load_manifest(manifest), tier=tier, source_ids=tuple(source or ()))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    with corpus_http(settings) as http:
        policy = CrawlPolicy(respect_robots=settings.respect_robots, delay_seconds=settings.crawl_delay_seconds)
        connectors = {"fedlex": FedlexConnector(http, swiss_today, settings.data_dir),
                      "html": HtmlConnector(http, policy)}
        pdf = PdfConnector(http, settings.data_dir, delay_seconds=settings.crawl_delay_seconds)
        report = run_fetch(settings.database_url, specs, connectors, pdf, now=lambda: datetime.now(tz=UTC),
                           workers=workers)
    promote = report.get("_promote", {})
    for sid, tally in report.items():
        if sid != "_promote":
            typer.echo(f"{sid}: {_tally(tally)}")
    typer.echo(f"promote: {_tally(promote) or 'nothing due'}")


# --- reporting --------------------------------------------------------------------------------------

@friendly_errors
def status_cmd() -> None:
    """Documents, chunks, embeddings, spend and quarantine at a glance."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        for r in conn.execute("select source_id, language, status, count(*) as n from corpus.document "
                              "group by 1,2,3 order by 1,2,3").fetchall():
            typer.echo(f"documents {r['source_id']:<28} {r['language']} {r['status']:<11} {r['n']}")
        c = conn.execute("select count(*) filter (where status in ('current','scheduled')) as live, "
                         "count(*) filter (where status in ('current','scheduled') and description <> '') "
                         "as described, count(*) filter (where needs_ocr) as ocr from corpus.chunk").fetchone()
        typer.echo(f"chunks live={c['live']} described={c['described']} awaiting_ocr={c['ocr']}")
        for name, spec in INDEXES.items():
            n = conn.execute(f"select count(*) as n from {spec.table}").fetchone()["n"]
            typer.echo(f"embeddings {name}: {n}")
        for r in conn.execute("select kind, sum(usd) as usd from corpus.llm_spend group by kind order by kind"):
            typer.echo(f"spend {r['kind']}: {usd(float(r['usd']))}")
        typer.echo(f"spend total: {usd(spent(conn))} of {usd(settings.corpus_budget_usd)}")
        pending = conn.execute("select count(*) as n from corpus.batch_job where ingested_at is null").fetchone()
        typer.echo(f"batches not ingested: {pending['n']}")
        q = conn.execute("select count(*) as n from corpus.quarantine").fetchone()["n"]
        typer.echo(f"quarantine: {q}")


@friendly_errors
def batches_cmd() -> None:
    """List Batch API jobs: id, kind, status, requests, estimate, submitted and ingested times."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        rows = conn.execute("select id, kind, status, request_count, estimated_usd, created_at, ingested_at "
                            "from corpus.batch_job order by created_at, id").fetchall()
    if not rows:
        typer.echo("no batch jobs")
        return
    for r in rows:
        ingested = r["ingested_at"].isoformat(timespec="seconds") if r["ingested_at"] else "not ingested"
        typer.echo(f"{r['id']}  {r['kind']:<14} {r['status']:<11} {r['request_count']:>6} requests  "
                   f"{usd(float(r['estimated_usd']))}  submitted {r['created_at'].isoformat(timespec='seconds')}  "
                   f"{ingested}")


def register(app: typer.Typer) -> None:
    for name, command in (("init", init_cmd), ("check-manifest", check_manifest_cmd), ("fetch", fetch_cmd),
                          ("status", status_cmd), ("batches", batches_cmd)):
        app.command(name)(command)
