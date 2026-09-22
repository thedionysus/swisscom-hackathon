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
from swiss_grounding.ingest.run_log import SourceHealth, load_source_health
from swiss_grounding.locations.models import AmbiguousLocation
from swiss_grounding.locations.resolver import canton_label
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.registry.suggestions import list_suggestions, submit_suggestion
from swiss_grounding.retrieval.coverage import coverage_rows
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
COVERAGE_SQL = (
    "select d.extent_id, d.source_id, count(*) as documents, max(d.retrieved_at) as last_retrieved, "
    "bool_and(d.origin = 'fixture') as fixture_only "
    "from document d where d.status = 'current' {extent_filter} "
    "group by d.extent_id, d.source_id order by d.extent_id, d.source_id"
)
UNKNOWN_HEALTH = SourceHealth(source_id="", last_run_at=None, last_successful_run_at=None,
                              last_run_failed=0, health="unknown")


def _with_health(row: dict[str, Any], health: SourceHealth) -> dict[str, Any]:
    """Coverage row plus the fetch-health fields of its source. Returns a new dict."""
    return {**row, "last_run_at": health.last_run_at, "last_successful_run_at": health.last_successful_run_at,
            "last_run_failed": health.last_run_failed, "health": health.health}


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
        if isinstance(resolved, AmbiguousLocation):
            return _json({
                "found": False, "ambiguous": True, "query": query,
                "candidates": [
                    {"location_id": c.id, "label": c.label("en"), "level": c.level.value,
                     "canton": canton_label(core.tree, c), "path": list(core.tree.path(c.id))}
                    for c in resolved.candidates
                ],
                "message": f"{resolved.input_text!r} is ambiguous ({resolved.reason}). Ask the user which one they mean.",
            })
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
        question_en: str | None = None,
        topic_en: str | None = None,
        location: str | None = None,
        topics: list[str] | None = None,
        categories: list[str] | None = None,
        as_of: str | None = None,
        limit: Annotated[int, Field(ge=MIN_LIMIT, le=MAX_LIMIT)] = 8,
        response_format: Literal["concise", "detailed"] = "concise",
    ) -> str:
        """Search Swiss public sources (federal law, cantonal and municipal information,
        institutional guidance) for evidence answering a question, restricted to the
        jurisdictions that apply to a location.

        Everything in the index is English, and this server never calls a model while
        answering, so it cannot translate for you. You already read the user's question, so
        you do the translating: send the question as written AND in English, plus a short
        English description of the subject. Answer quality depends on it.

        question: the user's question exactly as they wrote it, in their language. This is
        what the keyword index is searched for. That index is built from the English text,
        so only what survives translation matches: place and organisation names do, ordinary
        German, French and Italian words do not ("Leinenpflicht", "Abfall" and "Gemeinde"
        each match nothing). Accents are not folded either, so the spelling has to be the
        one the English text uses. Send this field anyway -- it costs nothing and names do
        reach it -- but question_en is what actually carries the search.
        question_en: the same question in English. This, joined to topic_en by a space, is
        what gets embedded and compared against the index. Omit it and the server embeds the
        verbatim question against an English index instead -- that still works and still
        returns evidence, but it matches worse. query_fields in the response lists which of
        these fields were used, so you can see whether an answer came from the good path
        ["question_en","topic_en"] or the degraded one ["question"].
        topic_en: a short English description of what the question is about, e.g. "leash
        rules for dogs in forests" or "household waste collection days". Free text, not an
        id. It sharpens the embedded query, and when you supply no topics it is also what
        the server's own topic classifier reads.

        topics: the topic ids the question is about, from swiss_list_categories. A hard
        filter, not a hint: evidence carrying none of them is not returned, and the status is
        'no_evidence' when nothing on the path carries one. Supply none and the server
        estimates them itself. categories_used says what was filtered on and is empty when no
        topic constraint was applied; topic_decided_by says who chose it -- "topics" (you),
        "categories" (you, on the deprecated field) or "classifier" (the server guessed).
        categories: DEPRECATED alias for topics, kept only so clients registered before this
        contract keep working. Same meaning, same hard filter, read only when topics is
        empty. Send topics.

        location: a hard filter, and in practice required on every call. Only documents
        scoped to the location or one of its parent jurisdictions (city, canton,
        Switzerland) are returned. Leave it out and the server looks for a place name in
        the question; find nothing and the status is 'needs_location' whatever the subject
        was -- a purely federal question is refused exactly like a local one, so do not
        assume national topics can skip it. Ask the user for a city, canton, or postal code,
        then call again. Do not guess a location.

        as_of: optional ISO date. The index holds current consolidations only and has no
        version history, so as_of can only exclude, never reach back -- it does NOT retrieve
        law as it stood on that date. A document is returned only if it records a valid_from
        on or before the date (and no valid_to at or before it). Most indexed documents --
        calendar records and municipal pages among them -- record no validity date at all and
        are therefore excluded entirely by any as_of. A date earlier than the oldest indexed
        version is refused with 'invalid_request' and field "as_of", naming the earliest date
        the index can answer for. Omit as_of for what is in force now; that is the normal case.

        Results are evidence with citations; write the answer from them and cite the URLs.
        Never invent URLs. Citations are ordered by tier, most specific first, with one
        exception: to guarantee the most specific jurisdiction is represented at all, one
        citation may be moved out of tier order, so read each citation's tier rather than
        inferring it from position. Both numbers on a citation are lower-is-better and
        neither is a relevance score:
        - tier: hops from the asked jurisdiction up to the one the evidence applies to. 0 is
          the asked jurisdiction itself, 1 its parent, rising to the federal root. null means
          the chunk claimed no tier, which usually means its distance was beyond the cutoff
          the server requires before a chunk may claim to be the *local* answer; it can also
          mean the distance was never measured. Those citations come last, barring that one
          exception, and are still evidence.
        - distance: cosine distance from the chunk to the embedded query, i.e. to
          question_en + topic_en. It moves when you reword the topic and stays put when you
          only change the location. That tier cutoff is the only thing distance decides, and
          it only demotes: nothing is ever dropped for its distance, and distance is NOT a
          relevance threshold you should apply yourself. On this corpus it does not separate
          relevant from irrelevant, so do not drop a citation for having a high one. null
          means it was never measured.

        Calendar-style citations (e.g. waste collections) carry event_date: the day the event
        happens. Treat an event_date before today as already passed; do not present it as the
        next occurrence.

        coverage lists, per jurisdiction on the path, how many documents are indexed; when the
        asked place has 0, say so in the answer, and repeat resolution_note when present."""
        try:
            parsed_as_of = date.fromisoformat(as_of) if as_of else None
        except ValueError:
            return _json({"status": "invalid_request", "field": "as_of",
                          "message": AS_OF_ERROR.format(value=as_of)})
        resp = core.query(QueryRequest(
            question=question, question_en=question_en, topic_en=topic_en, location=location,
            topics=tuple(topics or ()), categories=tuple(categories or ()),
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
        """List the topic categories swiss_search filters on. Pass the ids a question is about
        as its `topics`; evidence carrying none of them is not returned. (`categories` is the
        deprecated spelling of the same parameter.)"""
        return _json({"categories": [asdict(c) for c in CATEGORIES]})

    @mcp.tool(annotations=READ_ONLY)
    def swiss_coverage(location: str | None = None) -> str:
        """Report which sources and jurisdictions are indexed, with document counts, the latest
        retrieval date, and the fetch health of each source. Use it to tell the user when a place
        has no coverage instead of guessing. Per row: `health` is ok, degraded (last ingest run had
        some failures), failing (last run fetched nothing), or unknown (never run); `last_run_at`,
        `last_successful_run_at` and `last_run_failed` back it up. `fixture_only` is true when every
        document in the row is offline demo data rather than fetched from the source. Treat a row
        that is failing or fixture_only as NOT covered by live data, even if documents is non-zero.
        `by_extent` gives, per jurisdiction on the resolved path, the document count independent of
        source; empty only when no location was given."""
        path: list[str] | None = None
        resolved_id = None
        if location:
            resolved = core.resolver.resolve(location)
            if resolved is None or isinstance(resolved, AmbiguousLocation):
                return _json({"coverage": [], "message": f"Could not resolve {location!r}"})
            path = list(resolved.path)
            resolved_id = resolved.location.id
        extent_filter = "" if path is None else "and d.extent_id = any(%(path)s)"
        with connect(settings.database_url) as conn:
            rows = conn.execute(COVERAGE_SQL.format(extent_filter=extent_filter), {"path": path}).fetchall()
            health = load_source_health(conn)
            pending = [asdict(s) for s in list_suggestions(conn, status="pending")]
            by_extent = [asdict(r) for r in coverage_rows(conn, core.tree, path)] if path is not None else []
        coverage = [_with_health(dict(row), health.get(row["source_id"], UNKNOWN_HEALTH)) for row in rows]
        return _json({
            "resolved_location_id": resolved_id, "coverage": coverage, "by_extent": by_extent,
            "pending_suggestions": pending,
        })

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
