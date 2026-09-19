import json
from collections.abc import Collection, Iterable
from dataclasses import dataclass

import psycopg

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree

PRUNE_UNREFERENCED = """
delete from location
where level = 'municipality' and bfs_id is not null and id <> all(%(keep)s)
    and not exists (select 1 from document where document.extent_id = location.id)
    and not exists (select 1 from chunk where chunk.extent_id = location.id)
    and not exists (select 1 from source where source.default_extent_id = location.id)
returning id
"""

PRUNE_REFERENCED = """
select id from location
where level = 'municipality' and bfs_id is not null and id <> all(%(keep)s)
    and (
        exists (select 1 from document where document.extent_id = location.id)
        or exists (select 1 from chunk where chunk.extent_id = location.id)
        or exists (select 1 from source where source.default_extent_id = location.id)
    )
"""

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


@dataclass(frozen=True)
class PruneReport:
    deleted: tuple[str, ...]
    kept_referenced: tuple[str, ...]


def prune_locations(conn: psycopg.Connection, keep_ids: Collection[str]) -> PruneReport:
    """Delete register-derived municipality rows no longer in the seed set.

    A stale row still referenced by a document, chunk, or source is kept and
    reported separately rather than deleted or raised on.
    """
    keep = list(keep_ids)
    deleted_rows = conn.execute(PRUNE_UNREFERENCED, {"keep": keep}).fetchall()
    kept_rows = conn.execute(PRUNE_REFERENCED, {"keep": keep}).fetchall()
    return PruneReport(
        deleted=tuple(sorted(r["id"] for r in deleted_rows)),
        kept_referenced=tuple(sorted(r["id"] for r in kept_rows)),
    )


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
