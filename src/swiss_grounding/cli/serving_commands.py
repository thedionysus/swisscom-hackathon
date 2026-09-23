"""`serving`, `lookups`, `dump` and `setup` commands."""
import httpx
import typer

from swiss_grounding.config import load_settings
from swiss_grounding.corpus.calendar import (
    OPENERZ_SOURCE,
    ZURICH_ZIPS,
    calendar_document,
    fetch_events,
    now,
)
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect

serving_app = typer.Typer(help="Serving: schema, calendars, latency stats.")


@serving_app.command("calendar")
def calendar_cmd() -> None:
    """Import the Zürich waste calendar (OpenERZ) as corpus documents. Run `corpus embed` afterwards."""
    settings = load_settings()
    today = now().date()
    with httpx.Client(timeout=settings.fetch_timeout_seconds,
                       headers={"user-agent": settings.corpus_user_agent}) as client, \
            connect(settings.database_url) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        for zip_code in ZURICH_ZIPS:
            doc = calendar_document(zip_code, fetch_events(client, zip_code, today), today)
            if doc is not None:
                typer.echo(f"{zip_code}: {persist_document(conn, doc, OPENERZ_SOURCE, now())}")
