import json
from typing import Iterable

import psycopg

from swiss_grounding.registry.models import Source

UPSERT = """
insert into source (id, name, base_url, default_extent_id, authority, categories,
                    fetch_strategy, fetch_config, allow_narrowing, license, origin)
values (%(id)s, %(name)s, %(base_url)s, %(default_extent_id)s, %(authority)s, %(categories)s,
        %(fetch_strategy)s, %(fetch_config)s::jsonb, %(allow_narrowing)s, %(license)s, %(origin)s)
on conflict (id) do update set
    name = excluded.name, base_url = excluded.base_url,
    default_extent_id = excluded.default_extent_id, authority = excluded.authority,
    categories = excluded.categories, fetch_strategy = excluded.fetch_strategy,
    fetch_config = excluded.fetch_config, allow_narrowing = excluded.allow_narrowing,
    license = excluded.license, origin = excluded.origin
"""


def upsert_sources(conn: psycopg.Connection, sources: Iterable[Source]) -> None:
    """Insert or update source registry rows."""
    for s in sources:
        conn.execute(UPSERT, {
            "id": s.id, "name": s.name, "base_url": s.base_url,
            "default_extent_id": s.default_extent_id, "authority": s.authority.value,
            "categories": list(s.categories), "fetch_strategy": s.fetch_strategy.value,
            "fetch_config": json.dumps(s.fetch_config), "allow_narrowing": s.allow_narrowing,
            "license": s.license, "origin": s.origin,
        })


def load_sources(conn: psycopg.Connection) -> tuple[Source, ...]:
    rows = conn.execute("select * from source order by id").fetchall()
    return tuple(
        Source(
            id=r["id"], name=r["name"], base_url=r["base_url"],
            default_extent_id=r["default_extent_id"], authority=r["authority"],
            categories=tuple(r["categories"]), fetch_strategy=r["fetch_strategy"],
            fetch_config=r["fetch_config"], allow_narrowing=r["allow_narrowing"],
            license=r["license"], origin=r["origin"],
        )
        for r in rows
    )
