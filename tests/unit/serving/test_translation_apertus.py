import json

from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.serving.translation import Translation
from swiss_grounding.serving.translation_apertus import ApertusTranslator


def test_translates_in_order_and_reports_the_source_language():
    seen = []

    def reply(task):
        seen.append(task)
        return {"source_lang": "de", "translations": ["délai de congé", "loyer"]}
    out = ApertusTranslator(FakeLLM(reply)).translate(["Kündigungsfrist", "Miete"], target="fr", source=None)
    assert out == Translation(("délai de congé", "loyer"), "de")
    assert json.dumps(["Kündigungsfrist", "Miete"], ensure_ascii=False) in seen[0].user
    assert "French" in seen[0].user


def test_a_wrong_count_is_no_translation():
    llm = FakeLLM(lambda t: {"source_lang": "de", "translations": ["nur eins"]})
    assert ApertusTranslator(llm).translate(["a", "b"], target="fr", source="de") is None


def test_a_failing_call_is_no_translation_and_does_not_raise():
    class Down:
        def complete(self, task):
            raise TimeoutError("slow")
    assert ApertusTranslator(Down()).translate(["a"], target="fr", source="de") is None


def test_unknown_target_and_empty_input_are_skipped():
    llm = FakeLLM(lambda t: {"translations": []})
    t = ApertusTranslator(llm)
    assert t.translate(["a"], target="xx", source=None) is None and t.translate([], target="fr", source=None) is None


def test_repeated_texts_are_served_from_the_cache():
    calls = []
    llm = FakeLLM(lambda t: calls.append(t) or {"source_lang": "de", "translations": ["x"]})
    t = ApertusTranslator(llm)
    t.translate(["a"], target="fr", source="de")
    t.translate(["a"], target="fr", source="de")
    assert len(calls) == 1
