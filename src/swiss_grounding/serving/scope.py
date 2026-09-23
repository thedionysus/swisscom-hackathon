"""The declared scope (ADR 0009, amended by ADR 0014 and ADR 0015), quotable by the server."""
from collections.abc import Sequence

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


def covered_levels(path: Sequence[str]) -> tuple[str, ...]:
    """Which levels of a resolved path the declared scope covers. Federal is always covered."""
    levels = ["federal"]
    if len(path) > 1 and path[1] in SCOPE_CANTONS:
        levels.append("cantonal")
        if len(path) > 2 and path[2] in SCOPE_MUNICIPALITIES:
            levels.append("municipal")
    return tuple(levels)


def scope_statement() -> str:
    return (
        "Covered: federal information for all of Switzerland; cantonal information for "
        f"{CANTON_NAMES}; municipal services for {MUNICIPALITY_NAMES}; lookups for "
        f"{', '.join(LOOKUPS)}. Not covered: {'; '.join(NOT_COVERED)}."
    )
