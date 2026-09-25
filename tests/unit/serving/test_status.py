from dataclasses import replace

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.models import ScoredGroup
from swiss_grounding.serving.places import PlaceOutcome
from swiss_grounding.serving.status import decide, pre_search
from tests.unit.serving.test_groups import cand

TREE = LocationTree.from_locations([
    Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"}),
    Location("CH-ZH", "CH", Level.CANTON, 1, None, {"de": "Zürich"}),
    Location("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, 261, None, {"de": "Zürich"}),
    Location("CH-BE", "CH", Level.CANTON, 2, None, {"de": "Bern"}),
    Location("CH-BE-351", "CH-BE", Level.MUNICIPALITY, 351, None, {"de": "Bern"}),
])


def scored(extent="CH", relevance=0.9, group="g", text="text de"):
    [g] = collapse([replace(cand("de", group=group), extent_id=extent, text=text)], {}, "de")
    return ScoredGroup(g, relevance, relevance, 0)


def test_foreign_place_is_outside_scope_and_sends_the_client_elsewhere():
    r = pre_search(PlaceOutcome("foreign", "Konstanz, Deutschland"))
    assert r.status == "outside_scope" and "outside Switzerland" in r.message
    assert "other sources" in r.message


def test_unresolved_place_is_outside_scope_with_a_spelling_hint():
    r = pre_search(PlaceOutcome("unresolved", "Konstanz"))
    assert r.status == "outside_scope" and "spelling" in r.message


def test_ambiguous_place_asks_which_one():
    loc = TREE.get("CH-ZH-261")
    r = pre_search(PlaceOutcome("ambiguous", "Zürich", candidates=(loc, TREE.get("CH-ZH"))))
    assert r.status == "needs_location"


def test_ambiguous_place_message_names_level_and_canton_not_ids():
    loc = TREE.get("CH-ZH-261")
    r = pre_search(PlaceOutcome("ambiguous", "Zürich", candidates=(TREE.get("CH-ZH"), loc)))
    assert "Zürich (Kanton)" in r.message
    assert "Zürich (Gemeinde, ZH)" in r.message
    assert "CH-" not in r.message


def test_resolved_place_goes_on_to_search():
    assert pre_search(PlaceOutcome("resolved", "Bern")) is None


def test_nothing_above_threshold_is_no_evidence():
    status, _ = decide(PlaceOutcome("none"), [scored(relevance=0.05)], threshold=0.1, tree=TREE)
    assert status == "no_evidence"


def test_no_place_and_answers_from_two_cities_asks_for_the_place():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-BE-351", group="b")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "needs_location"


def test_no_place_but_a_federal_answer_answers():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-BE-351", group="b"), scored("CH", group="c")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "results"


def test_no_place_and_only_one_city_answers_still_asks():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-ZH", group="b")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "needs_location"


def test_canton_in_scope_has_nothing_uncovered():
    from swiss_grounding.locations.models import ResolvedLocation
    vd = ResolvedLocation(TREE.get("CH-ZH"), ("CH", "CH-ZH"), "alias", "Zürich")
    outcome = PlaceOutcome("resolved", "Kanton Zürich", resolved=vd, covered=("federal", "cantonal"))
    status, message = decide(outcome, [scored("CH-ZH")], threshold=0.1, tree=TREE)
    assert (status, message) == ("results", "")


def test_swiss_place_outside_scope_with_nothing_relevant_is_outside_scope():
    from swiss_grounding.locations.models import ResolvedLocation
    basel = ResolvedLocation(TREE.get("CH-BE-351"), ("CH", "CH-BS", "CH-BS-2701"), "alias", "Basel")
    outcome = PlaceOutcome("resolved", "Basel", resolved=basel, covered=("federal",))
    status, message = decide(outcome, [scored(relevance=0.01)], threshold=0.1, tree=TREE)
    assert status == "outside_scope" and "Basel" in message


def test_placeless_question_with_pages_from_two_places_and_a_deferring_federal_page_asks():
    groups = [scored("CH", group="ch", text="Die Hundesteuer legt jede Gemeinde fest."),
              scored("CH-ZH-261", group="zh"), scored("CH-BE-351", group="be")]
    status, message = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE,
                             question="Wie hoch ist die Hundesteuer?")
    assert status == "needs_location" and "municipality" in message


def test_placeless_question_answered_by_a_federal_page_is_not_asked_back():
    groups = [scored("CH", group="ch", text="Referenzalter 65."), scored("CH-ZH", group="zh"),
              scored("CH-BE-351", group="be")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE,
                       question="Ab welchem Alter erhalte ich eine AHV-Altersrente?")
    assert status == "results"


def test_pre_search_never_gates_on_the_question():
    assert pre_search(PlaceOutcome("none")) is None


def test_street_without_a_place_asks_for_the_municipality_even_without_evidence():
    status, message = decide(PlaceOutcome("none"), [], threshold=0.1, tree=TREE,
                             question="When is the next cardboard collection at Bahnhofstrasse?")
    assert status == "needs_location" and "'Bahnhofstrasse'" in message
