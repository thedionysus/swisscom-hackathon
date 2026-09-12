import json
from dataclasses import asdict
from datetime import date, datetime
from typing import Annotated, Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from swiss_grounding.app import build_query_core
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.suggestions import list_suggestions, submit_suggestion
from swiss_grounding.retrieval.models import NOTICE, QueryRequest, QueryResponse
from swiss_grounding.retrieval.query_core import QueryCore

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=True)
SUGGESTION_TIMEOUT = 10.0
SUGGESTION_USER_AGENT = "swiss-grounding-suggest/0.1"


def _suggestion_http() -> httpx.Client:
    """HTTP client used to check that a suggested URL is reachable (monkeypatched in tests)."""
    return httpx.Client(timeout=SUGGESTION_TIMEOUT, headers={"user-agent": SUGGESTION_USER_AGENT})
CONCISE_DROP = {"snippet_original", "title_original", "heading_path", "license", "retrieved_at"}
MIN_LIMIT = 1
MAX_LIMIT = 25
AS_OF_ERROR = "Could not parse as_of {value!r}; expected ISO date YYYY-MM-DD."


def _encode(value: Any) -> str:
    """JSON fallback encoder: ISO 8601 for dates and datetimes, str for the rest."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _json(obj: Any) -> str:
    """Serialize a tool response, ensuring every dict payload carries the notice."""
    payload = {**obj, "notice": NOTICE} if isinstance(obj, dict) and "notice" not in obj else obj
    return json.dumps(payload, default=_encode, ensure_ascii=False)


def _response_to_dict(resp: QueryResponse, response_format: str) -> dict:
    data = asdict(resp)
    if response_format == "concise":
        data["citations"] = [
            {k: v for k, v in c.items() if k not in CONCISE_DROP} for c in data["citations"]
        ]
    return data


def build_server(settings: Settings) -> FastMCP:
    core: QueryCore = build_query_core(settings)
    mcp = FastMCP("swiss-grounding")

    @mcp.tool(annotations=READ_ONLY)
    def swiss_resolve_location(query: str) -> str:
        """Resolve a Swiss place name, canton, city district, or postal code to a jurisdiction node.
        Use this to confirm the location with the user before calling swiss_search when the
        user's wording is ambiguous."""
        resolved = core.resolver.resolve(query)
        if resolved is None:
            return _json({"found": False, "query": query,
                          "message": "No Swiss location matched. Ask for a city, canton, or postal code."})
        return _json({
            "found": True, "location_id": resolved.location.id,
            "label": resolved.location.label("en"), "level": resolved.location.level.value,
            "path": list(resolved.path), "method": resolved.method,
            "alternatives": [a.id for a in resolved.alternatives],
        })

    @mcp.tool(annotations=READ_ONLY)
    def swiss_search(
        question: str,
        location: str | None = None,
        categories: list[str] | None = None,
        as_of: str | None = None,
        limit: Annotated[int, Field(ge=MIN_LIMIT, le=MAX_LIMIT)] = 8,
        response_format: Literal["concise", "detailed"] = "concise",
    ) -> str:
        """Search Swiss public sources (federal law, cantonal and municipal information,
        institutional guidance) for evidence answering a question, restricted to the
        jurisdictions that apply to a location.

        The location is a hard filter: only documents scoped to the location or one of its
        parent jurisdictions (city, canton, Switzerland) are returned, most specific first.
        If the question concerns a specific place and no location is given, the response
        status is 'needs_location': ask the user for a city, canton, or postal code, then
        call again. Do not guess a location.

        categories: optional hints from swiss_list_categories; they rerank, never exclude.
        as_of: ISO date to retrieve law as it stood on that date.
        Results are evidence with citations; write the answer from them and cite the URLs.
        Calendar-style citations (e.g. waste collections) carry event_date: the day the event
        happens. Treat an event_date before today as already passed; do not present it as the
        next occurrence. Never invent URLs."""
        try:
            parsed_as_of = date.fromisoformat(as_of) if as_of else None
        except ValueError:
            return _json({"status": "invalid_request", "field": "as_of",
                          "message": AS_OF_ERROR.format(value=as_of)})
        resp = core.query(QueryRequest(
            question=question, location=location, categories=tuple(categories or ()),
            as_of=parsed_as_of, limit=limit,
        ))
        return _json(_response_to_dict(resp, response_format))

    @mcp.tool(annotations=READ_ONLY)
    def swiss_get_document(document_id: int, chunk_id: int | None = None) -> str:
        """Fetch a full document, or one chunk of it, by id from a previous swiss_search result."""
        with connect(settings.database_url) as conn:
            doc = conn.execute(
                "select id, source_id, url, identifier, title_original, title_en, language, "
                "extent_id, authority, categories, valid_from, valid_to, event_date, retrieved_at, status "
                "from document where id = %s", (document_id,),
            ).fetchone()
            if doc is None:
                return _json({"error": f"document {document_id} not found"})
            if chunk_id is None:
                chunks = conn.execute(
                    "select id, ordinal, heading_path, anchor, text_en, text_original "
                    "from chunk where document_id = %s order by ordinal", (document_id,),
                ).fetchall()
            else:
                chunks = conn.execute(
                    "select id, ordinal, heading_path, anchor, text_en, text_original "
                    "from chunk where document_id = %s and id = %s", (document_id, chunk_id),
                ).fetchall()
                if not chunks:
                    return _json({
                        "error": f"chunk {chunk_id} is not part of document {document_id}",
                        "document_id": document_id, "chunk_id": chunk_id,
                    })
        return _json({"document": doc, "chunks": chunks})

    @mcp.tool(annotations=READ_ONLY)
    def swiss_list_categories() -> str:
        """List the topic categories that swiss_search accepts as hints."""
        return _json({"categories": [asdict(c) for c in CATEGORIES]})

    @mcp.tool(annotations=READ_ONLY)
    def swiss_coverage(location: str | None = None) -> str:
        """Report which sources and jurisdictions are indexed, with document counts and the
        latest retrieval date. Use it to tell the user when a place has no coverage instead
        of guessing."""
        path: list[str] | None = None
        resolved_id = None
        if location:
            resolved = core.resolver.resolve(location)
            if resolved is None:
                return _json({"coverage": [], "message": f"Could not resolve {location!r}"})
            path = list(resolved.path)
            resolved_id = resolved.location.id
        with connect(settings.database_url) as conn:
            if path is None:
                rows = conn.execute(
                    "select d.extent_id, d.source_id, count(*) as documents, "
                    "max(d.retrieved_at) as last_retrieved "
                    "from document d where d.status = 'current' "
                    "group by d.extent_id, d.source_id order by d.extent_id, d.source_id",
                ).fetchall()
            else:
                rows = conn.execute(
                    "select d.extent_id, d.source_id, count(*) as documents, "
                    "max(d.retrieved_at) as last_retrieved "
                    "from document d where d.status = 'current' and d.extent_id = any(%(path)s) "
                    "group by d.extent_id, d.source_id order by d.extent_id, d.source_id",
                    {"path": path},
                ).fetchall()
            pending = [asdict(s) for s in list_suggestions(conn, status="pending")]
        return _json({"resolved_location_id": resolved_id, "coverage": rows, "pending_suggestions": pending})

    @mcp.tool(annotations=WRITE)
    def swiss_suggest_source(
        url: str,
        reason: str,
        proposed_extent: str | None = None,
        proposed_authority: str | None = None,
        proposed_categories: list[str] | None = None,
    ) -> str:
        """Propose a Swiss public source for ingestion. Official government domains (admin.ch,
        cantonal and city sites, ch.ch) are approved immediately as official information; every
        other domain is queued for human review. Law authority levels are never assigned here.
        Use when a question could not be answered and you know the authoritative site."""
        try:
            with connect(settings.database_url) as conn:
                suggestion = submit_suggestion(
                    conn, _suggestion_http(), url=url, reason=reason, suggested_by="mcp",
                    proposed_extent_id=proposed_extent, proposed_authority=proposed_authority,
                    proposed_categories=tuple(proposed_categories or ()),
                )
        except ValueError as exc:
            field = "proposed_authority" if "law" in str(exc) else "url"
            return _json({"status": "invalid_request", "field": field, "message": str(exc)})
        approved = suggestion.status == "approved"
        return _json({
            "status": suggestion.status, "suggestion_id": suggestion.id, "url": suggestion.url,
            "domain_class": suggestion.domain_class, "source_id": suggestion.source_id,
            "message": ("Source approved and queued for the next ingestion run." if approved
                        else "Suggestion recorded; awaiting human review."),
        })

    return mcp
