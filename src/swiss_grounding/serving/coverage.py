"""Documents per extent on a resolved path, from the corpus schema (the coverage signal)."""
from collections.abc import Sequence

import psycopg

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import CoverageRow

SQL = ("select extent_id, count(*) as n from corpus.document where status = 'current' "
       "and extent_id = any(%s) group by extent_id")


def coverage_rows(conn: psycopg.Connection, tree: LocationTree, path: Sequence[str]) -> tuple[CoverageRow, ...]:
    counts = {r["extent_id"]: r["n"] for r in conn.execute(SQL, (list(path),)).fetchall()}
    return tuple(CoverageRow(e, tree.get(e).label("de"), counts.get(e, 0)) for e in path)
