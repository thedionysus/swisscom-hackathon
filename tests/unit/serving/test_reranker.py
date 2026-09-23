import os

import pytest

from swiss_grounding.serving.reranker import OverlapReranker, choose_model, passage_text

GPU, CPU = "BAAI/bge-reranker-v2-m3", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


@pytest.mark.parametrize(("setting", "device", "expected"), [
    ("auto", "mps", GPU), ("auto", "cuda", GPU), ("auto", "cpu", CPU), ("my/model", "cpu", "my/model"),
])
def test_choose_model(setting, device, expected):
    assert choose_model(setting, gpu_model=GPU, cpu_model=CPU, device=device) == expected


def test_overlap_reranker_prefers_shared_words_and_stays_in_zero_one():
    r = OverlapReranker()
    scores = r.score("Kündigungsfrist Wohnung", ["Die Kündigungsfrist für eine Wohnung", "Hundesteuer"])
    assert scores[0] > scores[1] and all(0.0 <= s <= 1.0 for s in scores)


def test_passage_text_puts_the_breadcrumb_first():
    assert passage_text(("SR 220 OR", "Art. 266c"), "Text") == "SR 220 OR › Art. 266c\nText"


@pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="downloads a reranker model")
def test_cross_encoder_separates_relevant_from_irrelevant():
    from swiss_grounding.serving.reranker import CrossEncoderReranker
    r = CrossEncoderReranker(CPU, device="cpu", max_tokens=512)
    good, bad = r.score("Kündigungsfrist Mietwohnung", [
        "Bei der Miete von Wohnungen können die Parteien mit einer Frist von drei Monaten kündigen.",
        "Hundehaltende müssen ihren Hund innert zehn Tagen anmelden."])
    assert good > 0.5 > bad
