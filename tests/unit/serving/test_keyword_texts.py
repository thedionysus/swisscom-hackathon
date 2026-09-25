import numpy as np

from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.candidates import ArmQuery, keyword_texts
from swiss_grounding.serving.models import LANGS
from swiss_grounding.serving.places import PlaceText, place_outcomes, place_text

TREE = LocationTree.from_locations(seed_locations())


class NoGeoAdmin:
    def search_communes(self, text):
        return ()


def _places(question, locations=()):
    """The PlaceText serving builds, as if every level of the resolved path were covered."""
    [o] = place_outcomes(question, locations, LocationResolver(TREE, NoGeoAdmin()), TREE)
    return place_text(TREE, o, o.resolved.path[1:] if o.resolved else ())


def _q(question, lang, translations=None, places=None):
    return ArmQuery(question=question, question_lang=lang, question_vec=np.zeros(4), question_sparse=None,
                    translations=translations or {}, translation_vecs={}, extent_path=("CH",), local_extents=(),
                    as_of=None, per_arm=10, top_n=30, local_quota=10, places=places or PlaceText())


def _texts(question, lang="de", locations=(), translations=None):
    return keyword_texts(_q(question, lang, translations, _places(question, locations)))


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


def test_the_city_the_question_named_is_left_out():
    assert _texts("Wann ist die Kartonsammlung in Zürich?") == {"de": "Wann ist die Kartonsammlung in ?"}


def test_a_canton_goes_with_its_marker():
    assert _texts("Leinenpflicht im Kanton Zürich")["de"] == "Leinenpflicht im"


def test_a_marker_before_the_matched_name_goes_too():
    texts = _texts("Wie hoch ist die Hundesteuer im Kanton Appenzell Ausserrhoden?")
    assert texts["de"] == "Wie hoch ist die Hundesteuer im ?"


def test_only_the_text_that_named_the_place_goes_not_the_same_word_elsewhere():
    assert _texts("Hunde im Wald in Wald ZH")["de"] == "Hunde im Wald in"


def test_a_place_argument_leaves_the_same_word_as_a_noun_in_the_question():
    texts = _texts("Darf mein Hund im Wald frei laufen?", locations=("Wald ZH",))
    assert texts["de"] == "Darf mein Hund im Wald frei laufen?"


def test_a_place_argument_is_left_out_where_the_question_repeats_it():
    assert _texts("Wann ist die Kartonsammlung in Zürich?", locations=("Zürich",))["de"] == (
        "Wann ist die Kartonsammlung in ?")


def test_the_place_is_matched_without_case_or_accents_and_as_a_whole_word():
    assert _texts("Baden im Zürichsee oder in ZURICH")["de"] == "Baden im Zürichsee oder in"


def test_without_a_resolved_place_the_question_is_unchanged():
    texts = _texts("Wann ist die Kartonsammlung?")
    assert texts["de"] == "Wann ist die Kartonsammlung?"
    assert keyword_texts(_q("Kartonsammlung in Zürich", "de"))["de"] == "Kartonsammlung in Zürich"


def test_translations_lose_the_mention_and_marked_names_but_keep_a_bare_name():
    texts = _texts("Leinenpflicht im Kanton Waadt?", translations={
        "fr": "Laisse obligatoire dans le canton de Vaud ?",
        "it": "Obbligo del guinzaglio per i cani di Vaud?"})
    assert texts["fr"] == "Laisse obligatoire dans le ?"
    assert texts["it"] == "Obbligo del guinzaglio per i cani di Vaud?"


def test_a_translation_loses_the_mention_but_not_another_languages_name():
    """The mention "Zürich" is matched without accents, so the French "Zurich" goes; the Italian
    "Zurigo" is a bare name that did not name the place, so it stays."""
    texts = _texts("Wann ist die Kartonsammlung in Zürich?", translations={
        "fr": "Quand a lieu la collecte du carton à Zurich ?",
        "it": "Quando si raccoglie il cartone a Zurigo?"})
    assert texts["fr"] == "Quand a lieu la collecte du carton à ?"
    assert texts["it"] == "Quando si raccoglie il cartone a Zurigo?"


def test_identifiers_are_kept_even_a_postal_code_that_names_the_place():
    texts = _texts("Kartonsammlung 8003 im Kanton Zürich nach Art. 12")
    assert texts["de"] == "Kartonsammlung 8003 im nach Art. 12"
    assert texts["fr"] == "8003 OR 12"


def test_a_number_inside_the_place_name_is_no_identifier():
    assert _texts("Kartonsammlung Kreis 11") == {"de": "Kartonsammlung"}


def test_a_question_that_is_only_the_place_has_no_keyword_arm():
    assert _texts("Kanton Zürich") == {}


def test_a_question_that_is_only_the_place_falls_back_to_its_identifiers():
    assert _texts("Kanton Zürich 8003") == {lang: "8003" for lang in LANGS}
