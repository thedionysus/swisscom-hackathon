"""Which status a place gets, in a fixed order."""
from collections.abc import Sequence

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import PlaceResult, ScoredGroup
from swiss_grounding.serving.place_dependent import answer_depends_on_place
from swiss_grounding.serving.places import PlaceOutcome

FOREIGN = ("{place!r} is outside Switzerland. This server covers Swiss public sources only; "
           "look for the answer in other sources for that country.")
UNRESOLVED = ("{place!r} is not a Swiss municipality this server recognises, so it is treated as outside "
              "Switzerland: look for the answer in other sources. If it is a Swiss place, check the spelling "
              "or give the postal code and search again.")
AMBIGUOUS = "{place!r} matches several Swiss places ({options}). Ask the user which one they mean."
NEEDS_PLACE = ("The answer depends on the place: {reason}. "
               "Ask the user for their municipality, then search again.")
NO_EVIDENCE = "No passage in the indexed sources answers this question{where}."
OUT_OF_SCOPE_PLACE = ("{place!r} is in Switzerland, but its {levels} rules are outside this server's declared "
                      "scope, and no covered passage answers the question.")
UNCOVERED_NOTE = "The {levels} rules of {place!r} are not covered by this server; only the evidence below applies."


def describe_place(loc: Location) -> str:
    """A German label a user understands, never an internal id: "Zürich (Kanton)",
    "Zürich (Gemeinde, ZH)", "Kreis 3 (Quartier, ZH)". The canton code is the id's second segment."""
    label = loc.label("de")
    if loc.level == Level.COUNTRY:
        return label
    if loc.level == Level.CANTON:
        return f"{label} (Kanton)"
    canton_code = loc.id.split("-")[1]
    kind = "Gemeinde" if loc.level == Level.MUNICIPALITY else "Quartier"
    return f"{label} ({kind}, {canton_code})"


def uncovered_levels(outcome: PlaceOutcome) -> tuple[str, ...]:
    """Levels the place has (canton: cantonal; municipality or below: cantonal and municipal) that the
    declared scope does not cover. A canton or Switzerland itself has no municipal level to miss."""
    if outcome.kind != "resolved" or outcome.resolved is None:
        return ()
    depth = len(outcome.resolved.path)
    present = ("cantonal",) if depth == 2 else ("cantonal", "municipal") if depth > 2 else ()
    return tuple(level for level in present if level not in outcome.covered)


def pre_search(outcome: PlaceOutcome) -> PlaceResult | None:
    """Statuses decided before any search: a foreign, unresolved or ambiguous place."""
    if outcome.kind == "foreign":
        return PlaceResult(outcome.text, "outside_scope", message=FOREIGN.format(place=outcome.text))
    if outcome.kind == "unresolved":
        return PlaceResult(outcome.text, "outside_scope", message=UNRESOLVED.format(place=outcome.text))
    if outcome.kind == "ambiguous":
        options = ", ".join(describe_place(c) for c in outcome.candidates)
        return PlaceResult(outcome.text, "needs_location",
                           message=AMBIGUOUS.format(place=outcome.text, options=options))
    return None


def decide(outcome: PlaceOutcome, scored: Sequence[ScoredGroup], *, threshold: float,
           tree: LocationTree, question: str = "") -> tuple[str, str]:
    """Statuses decided after the search: uncovered levels, no evidence, a place still needed."""
    relevant = [s for s in scored if s.relevance >= threshold]
    uncovered = " and ".join(uncovered_levels(outcome))
    if not relevant:
        if uncovered:
            return "outside_scope", OUT_OF_SCOPE_PLACE.format(place=outcome.text, levels=uncovered)
        where = f" for {outcome.text}" if outcome.text else ""
        return "no_evidence", NO_EVIDENCE.format(where=where)
    # No place given: the evidence says whether the answer depends on the place:
    # several places hold their own page and no federal passage answers by itself.
    if outcome.kind == "none":
        reason = answer_depends_on_place(question, relevant, tree)
        if reason is not None:
            return "needs_location", NEEDS_PLACE.format(reason=reason)
    if uncovered:
        return "results", UNCOVERED_NOTE.format(levels=uncovered, place=outcome.text)
    return "results", ""
