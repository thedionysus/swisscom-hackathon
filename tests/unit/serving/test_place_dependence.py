"""The evidence-based rule: a placeless question is asked back when several places hold their own
page on the subject and no federal passage answers by itself."""
from dataclasses import replace

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.models import ScoredGroup
from swiss_grounding.serving.place_dependent import (
    answer_depends_on_place,
    distinct_places,
    federal_defers,
)
from tests.unit.serving.test_groups import cand

TREE = LocationTree.from_locations([
    Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"}),
    Location("CH-ZH", "CH", Level.CANTON, 1, None, {"de": "Zürich"}),
    Location("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, 261, None, {"de": "Zürich"}),
    Location("CH-BE", "CH", Level.CANTON, 2, None, {"de": "Bern"}),
    Location("CH-BE-351", "CH-BE", Level.MUNICIPALITY, 351, None, {"de": "Bern"}),
])


def scored(extent, text, group, relevance=0.9):
    [g] = collapse([replace(cand("de", group=group), extent_id=extent, text=text)], {}, "de")
    return ScoredGroup(g, relevance, relevance, 0)


def test_distinct_places_collapses_a_canton_and_its_own_commune_into_one_place():
    assert distinct_places(("CH-ZH", "CH-ZH-261", "CH"), TREE) == ("CH-ZH-261",)
    assert distinct_places(("CH-ZH-261", "CH-BE-351"), TREE) == ("CH-BE-351", "CH-ZH-261")
    assert distinct_places(("CH",), TREE) == ()


def test_federal_defers_recognises_pointers_to_the_commune_or_canton_in_every_language():
    assert federal_defers("Haben Sie neu einen Hund? Dann müssen Sie ihn bei der Wohngemeinde anmelden.")
    assert federal_defers("Die Höhe der Steuer legt jede Gemeinde selbst fest.")
    assert federal_defers("Le montant est fixé par la commune ; renseignez-vous auprès de votre commune.")
    assert federal_defers("Le date variano a seconda del Cantone.")
    assert federal_defers("The amount depends on your commune.")
    assert not federal_defers("Ab 1. Januar 2024 gilt für Frauen und Männer Referenzalter 65.")
    assert not federal_defers("Die Kündigungsfrist beträgt drei Monate.")


def test_no_federal_passage_and_local_pages_asks_even_from_one_place():
    reason = answer_depends_on_place("Wann ist die Kartonabfuhr?", [scored("CH-ZH-261", "Karton Abfuhr", "a")], TREE)
    assert reason is not None and "Zürich" in reason


def test_several_places_with_a_federal_page_that_defers_asks():
    groups = [scored("CH", "Die Hundesteuer legt jede Gemeinde fest.", "ch"),
              scored("CH-ZH-261", "Hundesteuer Zürich 180 Franken", "zh"),
              scored("CH-BE-351", "Hundesteuer Bern 150 Franken", "be")]
    assert answer_depends_on_place("Was kostet ein Hund im Jahr?", groups, TREE) is not None


def test_several_places_with_a_federal_page_that_answers_by_itself_does_not_ask():
    """The AHV case: branch offices in two cities have pages, but the federal page states the age."""
    groups = [scored("CH", "Referenzalter 65 für Frauen und Männer.", "ch"),
              scored("CH-ZH", "AHV-Zweigstelle Zürich Öffnungszeiten", "zh"),
              scored("CH-BE-351", "AHV-Zweigstelle Bern Öffnungszeiten", "be")]
    assert answer_depends_on_place("Ab welchem Alter erhalte ich eine AHV-Altersrente?", groups, TREE) is None


def test_a_known_local_subject_stands_in_for_the_missing_deferral_flag():
    """Until chunks carry an 'answers or defers' flag, a subject from the written list counts as
    deferring, but only when the corpus shows several places holding their own page on it."""
    groups = [scored("CH", "Il calendario delle vacanze scolastiche di tutti i Cantoni.", "ch"),
              scored("CH-ZH", "Schulferien Kanton Zürich 2026", "zh"),
              scored("CH-BE-351", "Schulferien Bern 2026", "be")]
    assert answer_depends_on_place("Quando iniziano le vacanze scolastiche?", groups, TREE) is not None


def test_a_known_local_subject_with_only_one_place_in_the_corpus_does_not_ask_on_its_own():
    groups = [scored("CH", "Referenzalter 65.", "ch"), scored("CH-ZH-261", "Hundesteuer Zürich", "zh")]
    assert answer_depends_on_place("Wie hoch ist die Hundesteuer?", groups, TREE) is None


def test_federal_only_evidence_never_asks():
    groups = [scored("CH", "Die Kündigungsfrist beträgt drei Monate.", "ch")]
    assert answer_depends_on_place("Wie lange ist die Kündigungsfrist?", groups, TREE) is None
