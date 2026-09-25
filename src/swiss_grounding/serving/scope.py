"""The declared scope, quotable by the server.

The six cantons and seven municipalities named here are the floor. `load_scope` adds every canton and
municipality holding current passages of its own in the corpus (issue #59), so a fetched source is searched
and declared without a code change, and each database declares what it holds.
"""
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import psycopg

from swiss_grounding.locations.tree import LocationTree

SCOPE_CANTONS: tuple[str, ...] = ("CH-ZH", "CH-BE", "CH-VD", "CH-GE", "CH-TI", "CH-GR")
SCOPE_MUNICIPALITIES: tuple[str, ...] = (
    "CH-ZH-261",   # Zürich
    "CH-BE-351",   # Bern
    "CH-VD-5586",  # Lausanne
    "CH-GE-6621",  # Genève
    "CH-TI-5192",  # Lugano
    "CH-GR-3901",  # Chur
    "CH-GR-3762",  # Scuol
)
MUNICIPALITY_NAMES = "Zürich, Bern, Lausanne, Genève, Lugano, Chur and Scuol"
CANTON_NAMES = "Zurich, Bern, Vaud, Geneva, Ticino and Graubünden"
LOOKUPS = ("health insurance premiums", "public transport connections", "the reference interest rate")
# Amended 2026-09-24: the manifest gained general-information sources on the commercial register
# (EHRA, KMU portal), VAT and MeteoSwiss hazards, so those topics are covered in general; only
# looking up a specific company, and live forecasts/statistics/geodata, remain not covered.
NOT_COVERED = (
    "places outside Switzerland",
    "computed amounts such as tax bills or pensions (the official rules and calculators are cited instead)",
    "looking up a specific company in the commercial register (how the register works is covered)",
    "live weather forecasts, statistics and geodata (MeteoSwiss hazard guidance is covered)",
    "cantonal and municipal rules outside the named cantons and municipalities",
)


# A canton with more added municipalities than this is counted in the statement, not named one by one.
LISTED_PER_CANTON = 10
PASSAGE_EXTENTS = ("select distinct c.extent_id from corpus.chunk c join corpus.document d on d.id = c.document_id "
                   "where c.status = 'current' and d.status = 'current' and c.text <> ''")


@dataclass(frozen=True)
class Scope:
    """The cantons and municipalities whose own rules are searched and declared, and the names quoted for them."""
    cantons: frozenset[str] = frozenset(SCOPE_CANTONS)
    municipalities: frozenset[str] = frozenset(SCOPE_MUNICIPALITIES)
    canton_names: str = CANTON_NAMES
    municipality_names: str = MUNICIPALITY_NAMES


DECLARED = Scope()


def _and(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def scope_from_extents(extents: Iterable[str], tree: LocationTree) -> Scope:
    """The floor plus every canton with a passage at canton level and every municipality with a passage at it or
    below. Extents missing from the tree are skipped: no question can resolve to them."""
    known = {e for e in extents if e in tree.by_id}
    cantons = sorted({e for e in known if e.count("-") == 1} - set(SCOPE_CANTONS))
    municipalities = sorted({"-".join(e.split("-")[:3]) for e in known if e.count("-") >= 2}
                            - set(SCOPE_MUNICIPALITIES))
    by_canton: dict[str, list[str]] = defaultdict(list)
    for m in municipalities:
        by_canton[m.rsplit("-", 1)[0]].append(m)
    named = sorted(tree.get(m).label() for ms in by_canton.values() if len(ms) <= LISTED_PER_CANTON for m in ms)
    counted = sorted(f"{len(ms)} municipalities in {tree.get(c).label()}"
                     for c, ms in by_canton.items() if len(ms) > LISTED_PER_CANTON)
    return Scope(
        cantons=frozenset((*SCOPE_CANTONS, *cantons)),
        municipalities=frozenset((*SCOPE_MUNICIPALITIES, *municipalities)),
        canton_names=_and([*CANTON_NAMES.replace(" and ", ", ").split(", "),
                           *sorted(tree.get(c).label() for c in cantons)]),
        municipality_names=_and([*MUNICIPALITY_NAMES.replace(" and ", ", ").split(", "), *named, *counted]),
    )


def load_scope(conn: psycopg.Connection, tree: LocationTree) -> Scope:
    """`scope_from_extents` over the extents of the corpus's current passages."""
    return scope_from_extents((r["extent_id"] for r in conn.execute(PASSAGE_EXTENTS)), tree)


def covered_levels(path: Sequence[str], scope: Scope = DECLARED) -> tuple[str, ...]:
    """Which levels of a resolved path the scope covers. Federal is always covered, and a municipality with
    passages of its own is covered even when its canton has none."""
    levels = ["federal"]
    if len(path) > 1 and path[1] in scope.cantons:
        levels.append("cantonal")
    if len(path) > 2 and path[2] in scope.municipalities:
        levels.append("municipal")
    return tuple(levels)


def scope_statement(scope: Scope = DECLARED) -> str:
    return (
        "Covered: federal information for all of Switzerland; cantonal information for "
        f"{scope.canton_names}; municipal services for {scope.municipality_names}; lookups for "
        f"{', '.join(LOOKUPS)}. Not covered: {'; '.join(NOT_COVERED)}."
    )
