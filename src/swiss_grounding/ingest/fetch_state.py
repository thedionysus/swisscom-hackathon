import psycopg

from swiss_grounding.ingest.models import KnownUrl

UPSERT = """
insert into fetch_state (url, source_id, etag, last_modified, content_hash, last_seen_at)
values (%(url)s, %(source_id)s, %(etag)s, %(last_modified)s, %(content_hash)s, now())
on conflict (url) do update set source_id = excluded.source_id, etag = excluded.etag,
    last_modified = excluded.last_modified, content_hash = excluded.content_hash, last_seen_at = now()
"""


def load_known(conn: psycopg.Connection, source_id: str) -> dict[str, KnownUrl]:
    rows = conn.execute(
        "select url, etag, last_modified, content_hash from fetch_state where source_id = %s", (source_id,)
    ).fetchall()
    return {r["url"]: KnownUrl(etag=r["etag"], last_modified=r["last_modified"], content_hash=r["content_hash"])
            for r in rows}


def save_known(conn: psycopg.Connection, source_id: str, url: str, known: KnownUrl) -> None:
    conn.execute(UPSERT, {"url": url, "source_id": source_id, "etag": known.etag,
                          "last_modified": known.last_modified, "content_hash": known.content_hash})


def touch_known(conn: psycopg.Connection, url: str) -> None:
    conn.execute("update fetch_state set last_seen_at = now() where url = %s", (url,))


def forget_known(conn: psycopg.Connection, url: str) -> None:
    conn.execute("delete from fetch_state where url = %s", (url,))
