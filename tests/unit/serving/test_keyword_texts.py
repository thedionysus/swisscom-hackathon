import numpy as np

from swiss_grounding.serving.candidates import ArmQuery, keyword_texts
from swiss_grounding.serving.models import LANGS


def _q(question, lang, translations=None):
    return ArmQuery(question=question, question_lang=lang, question_vec=np.zeros(4), question_sparse=None,
                    translations=translations or {}, translation_vecs={}, extent_path=("CH",), local_extents=(),
                    as_of=None, per_arm=10, top_n=30, local_quota=10)


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
