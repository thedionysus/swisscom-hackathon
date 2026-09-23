"""`serving`, `lookups`, `dump` and `setup` commands."""
import json as _json_module
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
import typer

from swiss_grounding.app import build_search_service
from swiss_grounding.config import load_settings
from swiss_grounding.corpus.calendar import (
    OPENERZ_SOURCE,
    ZURICH_ZIPS,
    calendar_document,
    fetch_events,
    now,
    swiss_today,
)
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium_data import load_premiums
from swiss_grounding.serving.call_log import latency_summary
from swiss_grounding.serving.models import SearchRequest

serving_app = typer.Typer(help="Serving: schema, calendars, latency stats.")


@serving_app.command("calendar")
def calendar_cmd() -> None:
    """Import the Zürich waste calendar (OpenERZ) as corpus documents. Run `corpus embed` afterwards."""
    settings = load_settings()
    today = swiss_today()
    with httpx.Client(timeout=settings.fetch_timeout_seconds,
                       headers={"user-agent": settings.corpus_user_agent}) as client, \
            connect(settings.database_url) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        for zip_code in ZURICH_ZIPS:
            doc = calendar_document(zip_code, fetch_events(client, zip_code, today), today)
            if doc is not None:
                typer.echo(f"{zip_code}: {persist_document(conn, doc, OPENERZ_SOURCE, now())}")


lookups_app = typer.Typer(help="Lookup data: premiums.")
INSURERS_OPTION = typer.Option(None, help="CSV 'id;name' of insurers")


@lookups_app.command("load-premiums")
def load_premiums_cmd(premiums: Path, regions: Path, year: int,
                      insurers: Path | None = INSURERS_OPTION) -> None:
    """Load the BAG premium table and premium-region list for one business year."""
    names = {}
    if insurers:
        names = dict(line.strip().split(";", 1) for line in insurers.read_text(encoding="utf-8-sig").splitlines()
                     if ";" in line)
    with connect(load_settings().database_url) as conn:
        n_prem, n_reg = load_premiums(conn, premiums, regions, year, names)
    typer.echo(f"loaded {n_prem} premiums and {n_reg} municipalities for {year}")


@serving_app.command("ask")
def ask_cmd(question: str,
            location: Annotated[list[str] | None, typer.Option("--location", "-l")] = None,
            as_of: str | None = typer.Option(None, "--as-of")) -> None:
    """Run swiss_search from the command line and print the JSON response."""
    service = build_search_service(load_settings())
    request = SearchRequest(question, tuple(location or ()), {}, date.fromisoformat(as_of) if as_of else None)
    typer.echo(_json_module.dumps(asdict(service.search(request)), default=str, ensure_ascii=False, indent=2))


@serving_app.command("stats")
def stats_cmd() -> None:
    """p50/p95 latency, abstention and empty-result rate per tool."""
    with connect(load_settings().database_url) as conn:
        for row in latency_summary(conn):
            typer.echo(f"{row['tool']:<22} calls={row['calls']:<5} p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
                       f"abstain={row['abstain_rate']:.0%} empty={row['empty_rate']:.0%}")
