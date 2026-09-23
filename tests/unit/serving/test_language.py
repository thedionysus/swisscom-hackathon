import pytest

from swiss_grounding.serving.language import FUNCTION_WORDS, ROMANSH_MARKERS, detect_language


@pytest.mark.parametrize(("text", "lang"), [
    ("Wann wird bei uns das nächste Mal Karton abgeholt?", "de"),
    ("Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?", "fr"),
    ("Premio mensile più basso per un adulto di 30 anni a Lugano con franchigia 2500?", "it"),
    ("Cura èn las vacanzas d'atun 2026 per la scola da Scuol?", "rm"),
    ("What is the notice period for a rented flat?", "en"),
    ("Quelle est la date de la collecte?", "fr"),
    ("Quando è la raccolta della carta a Lugano?", "it"),
    ("Co è la gara da Trun?", "rm"),
    ("Nus vulain ir a Scuol", "rm"),
    ("Dov'è la stazione?", "it"),
    ("Quando parte il treno da Lugano?", "it"),
    ("Où sont-ils inscrits à Genève?", "fr"),
])
def test_detects_the_four_national_languages_and_english(text, lang):
    assert detect_language(text) == lang


def test_returns_none_when_no_function_word_matches():
    assert detect_language("SR 220 Art. 266c") is None


def test_romansh_markers_are_a_subset_of_the_romansh_function_words():
    assert ROMANSH_MARKERS <= FUNCTION_WORDS["rm"]
