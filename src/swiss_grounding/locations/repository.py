import json
from collections.abc import Iterable

import psycopg

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree

UPSERT = """
insert into location (id, parent_id, level, bfs_id, lindas_uri, names, path)
values (%(id)s, %(parent_id)s, %(level)s, %(bfs_id)s, %(lindas_uri)s, %(names)s::jsonb, %(path)s)
on conflict (id) do update set
    parent_id = excluded.parent_id, level = excluded.level, bfs_id = excluded.bfs_id,
    lindas_uri = excluded.lindas_uri, names = excluded.names, path = excluded.path
"""


def upsert_locations(conn: psycopg.Connection, locations: Iterable[Location]) -> None:
    """Insert or update locations. Parents are written before children."""
    tree = LocationTree.from_locations(locations)
    ordered = sorted(tree.all(), key=lambda loc: len(tree.path(loc.id)))
    for loc in ordered:
        conn.execute(UPSERT, {
            "id": loc.id,
            "parent_id": loc.parent_id,
            "level": loc.level.value,
            "bfs_id": loc.bfs_id,
            "lindas_uri": loc.lindas_uri,
            "names": json.dumps({"labels": dict(loc.names), "aliases": list(loc.aliases)}),
            "path": list(tree.path(loc.id)),
        })


def load_tree(conn: psycopg.Connection) -> LocationTree:
    rows = conn.execute(
        "select id, parent_id, level, bfs_id, lindas_uri, names from location"
    ).fetchall()
    locations = tuple(
        Location(
            id=r["id"], parent_id=r["parent_id"], level=Level(r["level"]), bfs_id=r["bfs_id"],
            lindas_uri=r["lindas_uri"], names=r["names"]["labels"],
            aliases=tuple(r["names"]["aliases"]),
        )
        for r in rows
    )
    return LocationTree.from_locations(locations)
