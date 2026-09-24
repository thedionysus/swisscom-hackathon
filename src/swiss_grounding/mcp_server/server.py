# src/swiss_grounding/mcp_server/server.py
"""The MCP server: six read-only tools (ADR 0015).

Tools are async and run their blocking work (SQL, torch) in a worker thread, so the event loop keeps
answering pings and cancellations. One limiter serialises the torch models. The search service loads its
models in a background thread started with the server, so `initialize` is answered at once.
"""
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Annotated, Any, Literal

import anyio
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from swiss_grounding.app import build_search_service
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.connections import find_connections
from swiss_grounding.lookups.premium import cheapest_premiums
from swiss_grounding.lookups.reference_rate import reference_rate
from swiss_grounding.serving.call_log import CallRecord, record_call
from swiss_grounding.serving.documents import get_document
from swiss_grounding.serving.models import LANGS, MAX_LIMIT, MAX_LOCATIONS, NOTICE, SearchRequest
from swiss_grounding.serving.places import place_outcomes
from swiss_grounding.serving.scope import scope_statement
from swiss_grounding.serving.search_service import SearchService
from swiss_grounding.serving.status import pre_search

log = logging.getLogger(__name__)
READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
LIVE = ToolAnnotations(readOnlyHint=True, idempotentHint=False, openWorldHint=True)
MAX_QUESTION_CHARS = 2000
MODEL_LOAD_TIMEOUT_SECONDS = 600
INTERNAL_ERROR = "The server hit an internal error answering this call. Try again; if it persists, say so."
INSTRUCTIONS = (
    "Swiss public information: federal law and federal offices, six cantons, seven cities, and three lookups. "
    "Search in the user's own language; pass every place the user names in `locations`. Cite the URLs you are "
    "given and never invent one. When a tool says a question is outside scope, tell the user it is not covered. "
    + scope_statement()
)


def _encode(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if hasattr(value, "item"):          # numpy scalars
        return value.item()
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _json(obj: dict) -> str:
    return json.dumps({**obj, "notice": NOTICE}, default=_encode, ensure_ascii=False)


class LazyService:
    """Builds the search service (loads bge-m3 and the reranker) in a background thread."""

    def __init__(self, build: Callable[[], SearchService]):
        self._ready = threading.Event()
        self._service: SearchService | None = None
        self._error: BaseException | None = None
        threading.Thread(target=self._load, args=(build,), daemon=True).start()

    def _load(self, build: Callable[[], SearchService]) -> None:
        try:
            self._service = build()
        except BaseException as exc:
            log.exception("search service failed to load")
            self._error = exc
        finally:
            self._ready.set()

    def get(self) -> SearchService:
        if not self._ready.wait(MODEL_LOAD_TIMEOUT_SECONDS) or self._service is None:
            raise RuntimeError("search service unavailable") from self._error
        return self._service


def build_server(settings: Settings) -> FastMCP:
    lazy = LazyService(lambda: build_search_service(settings))
    models = anyio.CapacityLimiter(1)
    mcp = FastMCP("swiss-grounding", instructions=INSTRUCTIONS)

    async def timed(tool: str, fn: Callable[[], dict], *, uses_models: bool = False) -> str:
        started = perf_counter()
        try:
            out = await anyio.to_thread.run_sync(fn, limiter=models if uses_models else None)
        except Exception as exc:
            log.exception("tool %s failed", tool)
            await anyio.to_thread.run_sync(
                record_call, settings.database_url,
                CallRecord(tool, int((perf_counter() - started) * 1000), "error", error=type(exc).__name__))
            return _json({"status": "error", "message": INTERNAL_ERROR})
        places = out.get("places", [])
        await anyio.to_thread.run_sync(record_call, settings.database_url, CallRecord(
            tool, int((perf_counter() - started) * 1000), out.get("status", "results"), places=len(places),
            citations=sum(len(p.get("citations", [])) for p in places)))
        return _json(out)

    @mcp.tool(annotations=READ_ONLY)
    async def swiss_search(
        question: Annotated[str, Field(max_length=MAX_QUESTION_CHARS)],
        locations: list[str] | None = None,
        translations: dict[str, str] | None = None,
        as_of: str | None = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = 8,
    ) -> str:
        """Find passages in official Swiss sources that answer a question, for up to three places.

        question: the user's question exactly as they wrote it, in any language (German, French,
        Italian, Romansh, English). Every language store is searched with it, and the server may
        translate it into the other languages itself; do not translate the question.
        locations: every place the user names, one entry each (max 3), e.g. ["Lausanne", "Bern"].
        Add the country when the user names one ("Konstanz, Deutschland"). Leave empty when the user
        names no place: national questions are answered without one, and the server asks for a place
        only when the answer depends on it. Results come back grouped per place, never merged.
        translations: optional, the same question in other languages, keyed de/fr/it/en/rm
        ({"fr": "...", "it": "..."}); still useful, and a language you send always wins over the
        server's own translation. Never required.
        as_of: optional ISO date (YYYY-MM-DD) for the rules in force on that day (default: today).

        status per place and overall: results (cite the passages), needs_location (ask the user for
        their municipality), outside_scope (say it is not covered; for a place outside Switzerland,
        suggest other sources), no_evidence (say the indexed sources hold no answer; `scope` says what
        is covered), error (retry once). Each citation has a supporting `passage`, its `url`,
        `publisher`, `extent_label`, `tier` (0 = the asked place, rising toward federal), `relevance`
        (0-1), and dates (`valid_from`, `modified_at`, `fetched_at`). A passage published in another
        language than the question may carry `translated_passage` (in `translation_language`, the
        question's language): answer from it, but cite `url` and quote `passage`. `uncovered_levels` lists cantonal or
        municipal rules of a place that this server does not cover: say so. Not covered at all: computed
        amounts (tax bills, pensions), the commercial register, statistics, geodata, weather."""
        notes = []
        places = [p for p in (locations or []) if p and p.strip()]
        if len(places) > MAX_LOCATIONS:
            notes.append(f"Only the first three places were searched: {', '.join(places[:MAX_LOCATIONS])}.")
            places = places[:MAX_LOCATIONS]
        unknown = sorted(k for k in (translations or {}) if k not in LANGS)
        if unknown:
            notes.append(f"Ignored translations in unsupported languages: {unknown}.")
        try:
            parsed = date.fromisoformat(as_of) if as_of else None
        except ValueError:
            return _json({"status": "invalid_request", "field": "as_of",
                          "message": f"as_of must be YYYY-MM-DD, got {as_of!r}"})
        request = SearchRequest(question, tuple(places), dict(translations or {}), parsed, limit)

        def run() -> dict:
            out = asdict(lazy.get().search(request))
            return {**out, "message": " ".join([*notes, out["message"]]).strip()}
        return await timed("swiss_search", run, uses_models=True)

    @mcp.tool(annotations=READ_ONLY)
    async def swiss_get_document(document_id: int | None = None, chunk_id: int | None = None,
                                 reference: str | None = None,
                                 language: Literal["de", "fr", "it", "en", "rm"] | None = None) -> str:
        """Read the whole article or section around a search hit, or look one up by official reference.

        Give document_id (and chunk_id) from a swiss_search citation, or a reference such as
        "Art. 336c OR", "SR 741.51 Art. 44" or an official URL. language switches to another language
        version of the same text (available_languages lists them). Federal law is authentic in de, fr, it;
        en is for information only."""
        def run() -> dict:
            with connect(settings.database_url) as conn:
                out = get_document(conn, document_id=document_id, chunk_id=chunk_id, reference=reference,
                                   language=language)
            return {"status": "invalid_request" if "error" in out else "results", **out}
        return await timed("swiss_get_document", run)

    @mcp.tool(annotations=READ_ONLY)
    async def swiss_scope() -> str:
        """What this server covers and what it does not. Quote it when telling a user a question is not covered."""
        return await timed("swiss_scope", lambda: {"status": "results", "scope": scope_statement()})

    def _municipality(service: SearchService, text: str) -> tuple[str | None, dict | None]:
        [outcome] = place_outcomes("", (text,), service.resolver, service.tree)
        refused = pre_search(outcome)
        if refused is not None:
            return None, {"status": refused.status, "message": refused.message}
        return outcome.resolved.location.id, None

    @mcp.tool(annotations=READ_ONLY)
    async def swiss_premium(municipality: str, age: Annotated[int, Field(ge=0, le=120)], deductible: int,
                            accident: bool = False,
                            model: Literal["any", "standard", "family_doctor", "hmo", "telmed"] = "any",
                            year: int | None = None, limit: Annotated[int, Field(ge=1, le=20)] = 5) -> str:
        """Cheapest monthly basic health-insurance premiums (BAG data) for a Swiss municipality, age and deductible.

        accident: include accident cover (false for employees covered at work). model: insurance model.
        year: premium year (default: the latest loaded). Returns insurer, model, CHF per month, premium region."""
        def run() -> dict:
            service = lazy.get()
            location_id, refused = _municipality(service, municipality)
            if refused:
                return refused
            with connect(settings.database_url) as conn:
                latest = year or conn.execute("select max(year) as y from serving.premium").fetchone()["y"]
                if latest is None:
                    return {"status": "source_unavailable", "message": "No premium data is loaded."}
                return cheapest_premiums(conn, service.tree, location_id=location_id, age=age,
                                         deductible=deductible, accident=accident, model=model, year=latest,
                                         limit=limit)
        return await timed("swiss_premium", run)

    @mcp.tool(annotations=LIVE)
    async def swiss_connections(origin: str, destination: str, date: str | None = None, time: str | None = None,
                                limit: Annotated[int, Field(ge=1, le=6)] = 4) -> str:
        """Next public transport connections between two Swiss stops (live timetable).

        origin/destination: station or address names. date: YYYY-MM-DD, time: HH:MM (default: now).
        status source_unavailable means the timetable service is down: say so, do not guess times."""
        def run() -> dict:
            with httpx.Client(base_url=settings.transport_base_url, timeout=settings.lookup_timeout_seconds,
                              headers={"user-agent": settings.corpus_user_agent}) as client:
                return find_connections(client, origin=origin, destination=destination, date=date, time=time,
                                        limit=limit)
        return await timed("swiss_connections", run)

    @mcp.tool(annotations=LIVE)
    async def swiss_reference_rate() -> str:
        """The current Swiss mortgage reference interest rate for rents (BWO), with its effective date.

        If BWO cannot be reached, status is source_unavailable and the last stored value is returned with
        the date it was retrieved: tell the user it may be out of date."""
        def run() -> dict:
            with httpx.Client(timeout=settings.lookup_timeout_seconds, follow_redirects=True,
                              headers={"user-agent": settings.corpus_user_agent}) as client, \
                    connect(settings.database_url) as conn:
                return reference_rate(conn, client, settings.reference_rate_url)
        return await timed("swiss_reference_rate", run)

    return mcp
