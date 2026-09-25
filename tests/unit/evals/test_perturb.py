from swiss_grounding.evals.perturb import (add_filler, drop_question_mark, lowercase, perturbations,
                                           strip_diacritics, strip_filler, typo)


def test_simple_perturbations():
    assert lowercase("Wie hoch?") == "wie hoch?"
    assert strip_diacritics("Führerausweis für Genève") == "Fuhrerausweis fur Geneve"
    assert drop_question_mark("Wie hoch ist sie?") == "Wie hoch ist sie"


def test_typo_swaps_two_adjacent_letters_and_is_seeded():
    q = "Kündigungsfrist Mietwohnung"
    once = typo(q, seed=7)
    assert once == typo(q, seed=7) and once != q
    assert sorted(once) == sorted(q) and len(once) == len(q)
    assert sum(a != b for a, b in zip(once, q)) == 2


def test_filler_is_added_per_language_and_stripped():
    assert add_filler("Wie hoch ist sie?", "de") == "Wie hoch ist sie bitte?"
    assert add_filler("Quand?", "fr") == "Quand s'il vous plaît?"
    assert strip_filler("Wie hoch ist sie bitte?", "de") == "Wie hoch ist sie?"
    assert strip_filler("Wie hoch?", "de") == "Wie hoch?"


def test_perturbations_drop_variants_equal_to_the_original():
    variants = perturbations("wie hoch", "de", seed=1)
    assert "lowercase" not in variants and "no_question_mark" not in variants
    assert set(variants) >= {"typo", "add_filler"}
