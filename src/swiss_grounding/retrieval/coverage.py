"""Document counts per extent on a path. Shared by swiss_search and swiss_coverage."""
from collections.abc import Sequence

import psycopg

from swiss_grounding.locations.models import Location
from swiss_grounding.locations.resolver import canton_label
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


def _describe(tree: LocationTree, location: Location) -> str:
    """"Label (level, Canton)" for a location, used to name alternatives and the chosen reading."""
    return f"{location.label('en')} ({location.level.value}, {canton_label(tree, location)})"


def _empty_labels(tree: LocationTree, rows: Sequence[CoverageRow]) -> list[str]:
    """Labels of empty extents; a label that repeats is qualified with its level to disambiguate."""
    empty = [r for r in rows if r.documents == 0]
    counts = {r.label: 0 for r in empty}
    for r in empty:
        counts[r.label] += 1
    return [
        f"{r.label} ({tree.get(r.extent_id).level.value})" if counts[r.label] > 1 else r.label
        for r in empty
    ]


def resolution_note(
    rows: Sequence[CoverageRow], tree: LocationTree, input_text: str, resolved: Location,
    method: str, alternatives: Sequence[Location],
) -> str:
    """Human-readable sentence(s) explaining coverage gaps and resolution caveats. Names the raw
    input whenever the resolver had to fall back or pick among candidates, so the caller can tell
    which reading was used."""
    empty_labels = _empty_labels(tree, rows)
    parts = []
    if empty_labels:
        parts.append(
            "No documents indexed for " + ", ".join(empty_labels) + "; evidence comes from parent jurisdictions."
        )
    if method == "geoadmin_approximate":
        parts.append(
            f"'{input_text}' was not recognised below canton level; answered at {resolved.label('en')} (canton)."
        )
    if alternatives:
        alts = ", ".join(_describe(tree, a) for a in alternatives)
        parts.append(f"'{input_text}' could also mean {alts}; this answer used {_describe(tree, resolved)}.")
    return " ".join(parts)
