import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx
import psycopg

from swiss_grounding.registry.models import LAW_AUTHORITIES, Authority, FetchStrategy, Source
from swiss_grounding.registry.official_domains import classify_domain, extent_for_domain
from swiss_grounding.registry.repository import upsert_sources

SOURCE_ID_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Suggestion:
    id: int
    url: str
    reason: str
    domain_class: str
    status: str
    proposed_extent_id: str | None
    proposed_authority: str | None
    proposed_categories: tuple[str, ...]
    suggested_by: str | None
    suggested_at: datetime
    review_note: str | None
    source_id: str | None


def _row_to_suggestion(r: dict) -> Suggestion:
    return Suggestion(
        id=r["id"], url=r["url"], reason=r["reason"], domain_class=r["domain_class"], status=r["status"],
        proposed_extent_id=r["proposed_extent_id"], proposed_authority=r["proposed_authority"],
        proposed_categories=tuple(r["proposed_categories"]), suggested_by=r["suggested_by"],
        suggested_at=r["suggested_at"], review_note=r["review_note"], source_id=r["source_id"],
    )


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"URL is not a valid http(s) URL: {url!r}")


def _check_reachable(http: httpx.Client, url: str) -> None:
    try:
        response = http.head(url, follow_redirects=True)
        if response.status_code >= 400:
            response = http.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise ValueError(f"URL is not reachable: {exc}") from exc
    if response.status_code >= 400:
        raise ValueError(f"URL is not reachable (HTTP {response.status_code})")


def _host_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _check_not_known(conn: psycopg.Connection, url: str) -> None:
    host = _host_of(url)
    for row in conn.execute("select id, base_url from source").fetchall():
        if _host_of(row["base_url"]) == host:
            raise ValueError(f"domain already covered by source {row['id']!r}")
    if conn.execute("select 1 from source_suggestion where url = %s", (url,)).fetchone():
        raise ValueError("URL already suggested")


def _source_id_for(url: str) -> str:
    return SOURCE_ID_RE.sub("_", _host_of(url)).strip("_")


def _to_source(url: str, extent_id: str, authority: Authority, categories: tuple[str, ...], origin: str) -> Source:
    parsed = urlparse(url)
    return Source(
        id=_source_id_for(url), name=parsed.netloc, base_url=f"{parsed.scheme}://{parsed.netloc}",
        default_extent_id=extent_id, authority=authority, categories=categories,
        fetch_strategy=FetchStrategy.HTML_CRAWL,
        fetch_config={"path_allowlist": [parsed.path or "/"], "start_paths": [parsed.path or "/"]},
        allow_narrowing=authority not in LAW_AUTHORITIES, origin=origin,
    )


def submit_suggestion(conn: psycopg.Connection, http: httpx.Client, url: str, reason: str, suggested_by: str | None,
                      proposed_extent_id: str | None = None, proposed_authority: str | None = None,
                      proposed_categories: tuple[str, ...] = ()) -> Suggestion:
    """Validate and record a suggestion; official domains are approved immediately as official_info."""
    _validate_url(url)
    if proposed_authority and Authority(proposed_authority) in LAW_AUTHORITIES:
        raise ValueError("law authority levels can only be assigned by a human reviewer")
    _check_not_known(conn, url)
    _check_reachable(http, url)
    domain_class = classify_domain(url)
    row = conn.execute(
        """
        insert into source_suggestion (url, reason, proposed_extent_id, proposed_authority, proposed_categories,
                                       domain_class, suggested_by)
        values (%s, %s, %s, %s, %s, %s, %s) returning *
        """,
        (url, reason, proposed_extent_id, proposed_authority, list(proposed_categories), domain_class, suggested_by),
    ).fetchone()
    if domain_class != "official":
        return _row_to_suggestion(row)
    source = _to_source(url, extent_for_domain(url), Authority.OFFICIAL_INFO, proposed_categories, "auto_approved")
    upsert_sources(conn, (source,))
    row = conn.execute(
        "update source_suggestion set status = 'approved', reviewed_by = 'auto', reviewed_at = now(), "
        "review_note = 'official domain', source_id = %s where id = %s returning *",
        (source.id, row["id"]),
    ).fetchone()
    return _row_to_suggestion(row)


def review_suggestion(conn: psycopg.Connection, suggestion_id: int, approve: bool, reviewer: str, note: str,
                      extent_id: str | None = None, authority: str | None = None,
                      categories: tuple[str, ...] = ()) -> Suggestion:
    row = conn.execute("select * from source_suggestion where id = %s", (suggestion_id,)).fetchone()
    if row is None:
        raise ValueError(f"suggestion {suggestion_id} not found")
    if row["status"] != "pending":
        raise ValueError(f"suggestion {suggestion_id} is already {row['status']}")
    source_id = None
    if approve:
        chosen_extent = extent_id or row["proposed_extent_id"] or extent_for_domain(row["url"])
        if not chosen_extent:
            raise ValueError("an extent_id is required to approve a non-official source")
        chosen_authority = Authority(authority or row["proposed_authority"] or Authority.INSTITUTIONAL)
        source = _to_source(row["url"], chosen_extent, chosen_authority,
                            categories or tuple(row["proposed_categories"]), "reviewed")
        upsert_sources(conn, (source,))
        source_id = source.id
    updated = conn.execute(
        "update source_suggestion set status = %s, reviewed_by = %s, reviewed_at = now(), review_note = %s, "
        "source_id = %s where id = %s returning *",
        ("approved" if approve else "rejected", reviewer, note, source_id, suggestion_id),
    ).fetchone()
    return _row_to_suggestion(updated)


def list_suggestions(conn: psycopg.Connection, status: str | None = None) -> tuple[Suggestion, ...]:
    if status:
        rows = conn.execute("select * from source_suggestion where status = %s order by id", (status,)).fetchall()
    else:
        rows = conn.execute("select * from source_suggestion order by id").fetchall()
    return tuple(_row_to_suggestion(r) for r in rows)
