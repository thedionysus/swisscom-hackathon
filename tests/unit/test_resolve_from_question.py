import pytest

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.query_core import resolve_from_question


@pytest.fixture(scope="module")
def tree():
    return LocationTree.from_locations(seed_locations())


def resolved_id(tree, question):
    resolved = resolve_from_question(tree, question)
    return None if resolved is None else resolved.location.id


@pytest.mark.parametrize("question", [
    "So what are the dog rules?",
    "City recycling rules?",
    "Hard hats required on trails?",
    "Enge spaces in apartments?",
    "What is the SG standard?",
    "Is it Basel or Zurich that has the stricter rule?",
    "Do I need to leash my dog in the forest?",
])
def test_ordinary_english_words_do_not_resolve(tree, question):
    assert resolve_from_question(tree, question) is None


@pytest.mark.parametrize("question", [
    "Be careful with dogs in Switzerland",
    "What are AI regulations in Switzerland?",
])
def test_country_wins_over_ambiguous_abbreviation(tree, question):
    assert resolved_id(tree, question) == "CH"


def test_canton_alias_resolves(tree):
    assert resolved_id(tree, "What are the dog rules in Basel?") == "CH-BS"


def test_neighborhood_resolves_when_an_ancestor_is_also_mentioned(tree):
    assert resolved_id(tree, "Where can my dog run in Wiedikon, Zurich?") == "CH-ZH-261-K3-ALT-WIEDIKON"


def test_multi_word_kreis_resolves(tree):
    assert resolved_id(tree, "Waste rules in Kreis 3?") == "CH-ZH-261-K3"


def test_postal_code_resolves(tree):
    assert resolved_id(tree, "Parking in 8003?") == "CH-ZH-261-K3"


def test_method_is_alias_in_question(tree):
    resolved = resolve_from_question(tree, "What are the dog rules in Basel?")
    assert resolved.method == "alias_in_question"
    assert resolved.path[0] == "CH"


def test_longer_ngram_wins_over_contained_unigram(tree):
    assert resolved_id(tree, "Rules for the Kanton Zürich?") == "CH-ZH"
