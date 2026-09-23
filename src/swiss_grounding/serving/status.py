"""Which status a place gets, in the fixed order of ADR 0013."""
from collections.abc import Sequence

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import PlaceResult, ScoredGroup
from swiss_grounding.serving.places import PlaceOutcome

FOREIGN = ("{place!r} is outside Switzerland. This server covers Swiss public sources only; "
           "look for the answer in other sources for that country.")
UNRESOLVED = ("{place!r} is not a Swiss municipality this server recognises, so it is treated as outside "
              "Switzerland: look for the answer in other sources. If it is a Swiss place, check the spelling "
              "or give the postal code and search again.")
AMBIGUOUS = "{place!r} matches several Swiss places ({options}). Ask the user which one they mean."
NEEDS_PLACE = ("The answer depends on the place (matching local rules found for: {options}). "
               "Ask the user for their municipality, then search again.")
NO_EVIDENCE = "No passage in the indexed sources answers this question{where}."
OUT_OF_SCOPE_PLACE = ("{place!r} is in Switzerland, but its {levels} rules are outside this server's declared "
                      "scope, and no covered passage answers the question.")
UNCOVERED_NOTE = "The {levels} rules of {place!r} are not covered by this server; only the evidence below applies."


def uncovered_levels(outcome: PlaceOutcome) -> tuple[str, ...]:
    """Levels the place has (canton: cantonal; municipality or below: cantonal and municipal) that the
    declared scope does not cover. A canton or Switzerland itself has no municipal level to miss."""
    if outcome.kind != "resolved" or outcome.resolved is None:
        return ()
    depth = len(outcome.resolved.path)
    present = ("cantonal",) if depth == 2 else ("cantonal", "municipal") if depth > 2 else ()
    return tuple(level for level in present if level not in outcome.covered)


def pre_search(outcome: PlaceOutcome) -> PlaceResult | None:
    """Steps 1 of ADR 0013 and the ambiguity rule: statuses decided before any search."""
    if outcome.kind == "foreign":
        return PlaceResult(outcome.text, "outside_scope", message=FOREIGN.format(place=outcome.text))
    if outcome.kind == "unresolved":
        return PlaceResult(outcome.text, "outside_scope", message=UNRESOLVED.format(place=outcome.text))
    if outcome.kind == "ambiguous":
        options = ", ".join(f"{c.label('de')} ({c.id})" for c in outcome.candidates)
        return PlaceResult(outcome.text, "needs_location",
                           message=AMBIGUOUS.format(place=outcome.text, options=options))
    return None


def decide(outcome: PlaceOutcome, scored: Sequence[ScoredGroup], *, threshold: float,
           tree: LocationTree) -> tuple[str, str]:
    """Steps 2, 3 and 5 of ADR 0013, after the search."""
    relevant = [s for s in scored if s.relevance >= threshold]
    uncovered = " and ".join(uncovered_levels(outcome))
    if not relevant:
        if uncovered:
            return "outside_scope", OUT_OF_SCOPE_PLACE.format(place=outcome.text, levels=uncovered)
        where = f" for {outcome.text}" if outcome.text else ""
        return "no_evidence", NO_EVIDENCE.format(where=where)
    extents = [s.group.representative.extent_id for s in relevant]
    # No place given and nothing federal answers: the answer depends on the place, even when only one
    # place's documents matched (answering from Zürich's calendar to a placeless question is a guess).
    if outcome.kind == "none" and "CH" not in extents:
        options = ", ".join(sorted({tree.get(e).label("de") for e in extents}))
        return "needs_location", NEEDS_PLACE.format(options=options)
    if uncovered:
        return "results", UNCOVERED_NOTE.format(levels=uncovered, place=outcome.text)
    return "results", ""
