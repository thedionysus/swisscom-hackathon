"""`serving`, `lookups`, `dump` and `setup` commands."""
from pathlib import Path

import httpx
import typer

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
