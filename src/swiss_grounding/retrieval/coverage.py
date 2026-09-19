"""Document counts per extent on a path. Shared by swiss_search and swiss_coverage."""
from collections.abc import Sequence

import psycopg

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import CoverageRow

COUNTS_SQL = """
select extent_id, count(*) as documents from document
where status = 'current' and extent_id = any(%(path)s) group by extent_id
"""


def coverage_rows(conn: psycopg.Connection, tree: LocationTree, path: Sequence[str]) -> tuple[CoverageRow, ...]:
    """One row per extent on `path`, in path order, counting current documents at that extent."""
    counts = {r["extent_id"]: r["documents"] for r in conn.execute(COUNTS_SQL, {"path": list(path)}).fetchall()}
    return tuple(CoverageRow(extent_id=e, label=tree.get(e).label("en"), documents=counts.get(e, 0)) for e in path)


def resolution_note(rows: Sequence[CoverageRow], method: str, alternatives: Sequence[str]) -> str:
    """Human-readable sentence(s) explaining coverage gaps and resolution caveats."""
    empty = [r.label for r in rows if r.documents == 0]
    parts = []
    if empty:
        parts.append("No documents indexed for " + ", ".join(empty) + "; evidence comes from parent jurisdictions.")
    if method == "geoadmin_approximate":
        parts.append("The place was not recognised below canton level; answered at canton level.")
    if alternatives:
        parts.append("Alternative reading: " + ", ".join(alternatives) + ".")
    return " ".join(parts)
