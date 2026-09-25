import numpy as np

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.candidates import ArmQuery, keyword_texts
from swiss_grounding.serving.models import LANGS
from swiss_grounding.serving.places import place_names

TREE = LocationTree.from_locations(seed_locations())
CITY_ZH = place_names(TREE, ("CH-ZH", "CH-ZH-261"))
KREIS_3 = place_names(TREE, ("CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"))


def _q(question, lang, translations=None, places=()):
    return ArmQuery(question=question, question_lang=lang, question_vec=np.zeros(4), question_sparse=None,
                    translations=translations or {}, translation_vecs={}, extent_path=("CH",), local_extents=(),
                    as_of=None, per_arm=10, top_n=30, local_quota=10, place_names=places)


def test_translation_wins_over_identifiers():
    texts = keyword_texts(_q("Was sagt Art. 266c OR?", "de", {"fr": "Que dit l'art. 266c CO ?"}))
    assert texts["fr"] == "Que dit l'art. 266c CO ?"


def test_the_questions_own_store_gets_the_question():
    assert keyword_texts(_q("Kündigungsfrist Wohnung", "de"))["de"] == "Kündigungsfrist Wohnung"


def test_other_stores_get_identifiers_only():
    texts = keyword_texts(_q("Art. 266c OR", "de"))
    assert {lang: texts[lang] for lang in LANGS if lang != "de"} == {"fr": "266c", "it": "266c", "en": "266c",
                                                                     "rm": "266c"}


def test_a_store_is_skipped_without_identifiers():
    texts = keyword_texts(_q("Kündigungsfrist 3 Monate", "de"))
    assert set(texts) == {"de"}


def test_unknown_language_sends_the_question_to_every_store():
    texts = keyword_texts(_q("Kündigungsfrist", None))
    assert texts == {lang: "Kündigungsfrist" for lang in LANGS}


def test_the_city_the_search_is_filtered_by_is_left_out():
    texts = keyword_texts(_q("Wann ist die Kartonsammlung in Zürich?", "de", places=CITY_ZH))
    assert texts == {"de": "Wann ist die Kartonsammlung in ?"}


def test_a_canton_goes_with_its_marker():
    places = place_names(TREE, ("CH-AR",))
    texts = keyword_texts(_q("Wie hoch ist die Hundesteuer im Kanton Appenzell Ausserrhoden?", "de", places=places))
    assert texts["de"] == "Wie hoch ist die Hundesteuer im ?"


def test_the_place_is_matched_without_case_or_accents_and_as_a_whole_word():
    texts = keyword_texts(_q("Baden im Zürichsee oder in ZURICH", "de", places=CITY_ZH))
    assert texts["de"] == "Baden im Zürichsee oder in"


def test_without_a_resolved_place_the_question_is_unchanged():
    texts = keyword_texts(_q("Wann ist die Kartonsammlung in Zürich?", "de"))
    assert texts["de"] == "Wann ist die Kartonsammlung in Zürich?"


def test_translations_leave_the_place_out_too():
    texts = keyword_texts(_q("Wann ist die Kartonsammlung in Zürich?", "de", places=CITY_ZH,
                             translations={"fr": "Quand a lieu la collecte du carton à Zurich ?",
                                           "it": "Quando si raccoglie il cartone a Zurigo?"}))
    assert texts["fr"] == "Quand a lieu la collecte du carton à ?"
    assert texts["it"] == "Quando si raccoglie il cartone a ?"


def test_identifiers_are_kept_even_a_postal_code_that_names_the_place():
    texts = keyword_texts(_q("Kartonsammlung 8003 Zürich nach Art. 12", "de", places=KREIS_3))
    assert texts["de"] == "Kartonsammlung 8003 nach Art. 12"
    assert texts["fr"] == "8003 OR 12"


def test_a_number_inside_the_place_name_is_no_identifier():
    texts = keyword_texts(_q("Kartonsammlung Kreis 11", "de", places=place_names(TREE, ("CH-ZH-261-K11",))))
    assert texts == {"de": "Kartonsammlung"}


def test_a_question_that_is_only_the_place_has_no_keyword_arm():
    assert keyword_texts(_q("Zürich", "de", places=CITY_ZH)) == {}


def test_a_question_that_is_only_the_place_falls_back_to_its_identifiers():
    texts = keyword_texts(_q("Zürich 8003", "de", places=KREIS_3))
    assert texts == {lang: "8003" for lang in LANGS}
