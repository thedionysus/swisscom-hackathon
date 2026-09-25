import json

import httpx

from swiss_grounding.serving.translation import (
    MAX_CHARS_PER_REQUEST,
    NoTranslator,
    SupertextTranslator,
    Translation,
    batches,
    fill_translations,
    our_code,
)

KEY = "test-key"


def _client(handler, calls: list):
    def record(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)
    return SupertextTranslator(KEY, base_url="https://api.test/v1", timeout_seconds=1.0,
                               transport=httpx.MockTransport(record), retry_backoff_seconds=0.0)


def _ok(translated, detected="de-CH"):
    return lambda request: httpx.Response(200, json={"request_id": "r", "detected_source_lang": detected,
                                                    "translated_text": list(translated)})


def test_request_matches_the_supertext_contract():
    calls: list[httpx.Request] = []
    t = _client(_ok(["Délai de congé"]), calls)
    out = t.translate(["Kündigungsfrist"], target="fr", source="de")
    [req] = calls
    assert req.method == "POST" and req.url.path == "/v1/translate/ai/text"
    assert req.headers["authorization"] == f"Supertext-Auth-Key {KEY}"
    assert json.loads(req.content) == {"text": ["Kündigungsfrist"], "target_lang": "fr-CH", "source_lang": "de"}
    assert out == Translation(("Délai de congé",), "de")


def test_english_is_requested_as_a_regional_variant():
    calls: list[httpx.Request] = []
    _client(_ok(["x"]), calls).translate(["y"], target="en", source="de")
    assert json.loads(calls[0].content)["target_lang"] == "en-GB"


def test_source_is_omitted_when_unknown_and_the_detected_language_comes_back():
    calls: list[httpx.Request] = []
    t = _client(_ok(["x"], detected="it-CH"), calls)
    out = t.translate(["y"], target="rm", source=None)
    assert "source_lang" not in json.loads(calls[0].content)
    assert json.loads(calls[0].content)["target_lang"] == "rm"
    assert out.source_lang == "it"


def test_api_errors_never_raise_and_yield_none():
    calls: list[httpx.Request] = []
    t = _client(lambda r: httpx.Response(401, json={"error_code": "API_KEY_INVALID", "message": "bad"}), calls)
    assert t.translate(["x"], target="fr", source="de") is None


def test_transport_errors_never_raise_and_yield_none():
    def boom(request):
        raise httpx.ConnectError("down")
    assert _client(boom, []).translate(["x"], target="fr", source="de") is None


def test_rate_limit_is_retried_once():
    calls: list[httpx.Request] = []
    answers = iter([httpx.Response(429, json={"message": "slow down"}), _ok(["ok"])(None)])
    t = _client(lambda r: next(answers), calls)
    assert t.translate(["x"], target="fr", source="de") == Translation(("ok",), "de")
    assert len(calls) == 2


def test_identical_requests_are_served_from_the_cache():
    calls: list[httpx.Request] = []
    t = _client(_ok(["a"]), calls)
    t.translate(["x"], target="fr", source="de")
    t.translate(["x"], target="fr", source="de")
    assert len(calls) == 1


def test_a_reply_with_the_wrong_shape_yields_none():
    t = _client(lambda r: httpx.Response(200, json={"translated_text": "not a list"}), [])
    assert t.translate(["x"], target="fr", source="de") is None


def test_batches_respect_the_character_limit_and_keep_order():
    texts = ["a" * 6000, "b" * 6000, "c" * 100]
    assert batches(texts, MAX_CHARS_PER_REQUEST) == [["a" * 6000], ["b" * 6000, "c" * 100]]
    assert batches([], MAX_CHARS_PER_REQUEST) == []


def test_our_code_maps_bcp47_variants_back():
    assert our_code("de-CH") == "de" and our_code("rm") == "rm" and our_code("EN") == "en"
    assert our_code("es") is None and our_code(None) is None


class FakeTranslator:
    name = "fake"

    def __init__(self, table: dict[tuple[str, str], str], detected: str | None = "de"):
        self.table = table
        self.detected = detected
        self.calls: list[tuple[tuple[str, ...], str, str | None]] = []

    def translate(self, texts, *, target, source):
        self.calls.append((tuple(texts), target, source))
        return Translation(tuple(self.table.get((t, target), f"{t} [{target}]") for t in texts), self.detected)


def test_fill_translations_skips_the_question_language_and_keeps_client_translations():
    fake = FakeTranslator({("Hundesteuer?", "fr"): "Taxe sur les chiens ?"})
    filled, detected = fill_translations(fake, "Hundesteuer?", "de", ("de", "fr", "it"),
                                         have={"it": "Tassa sui cani?"})
    assert filled == {"fr": "Taxe sur les chiens ?", "it": "Tassa sui cani?"}
    assert detected == "de"
    assert [c[1] for c in fake.calls] == ["fr"]


def test_fill_translations_with_an_unknown_language_detects_it_from_the_first_reply_and_skips_that_store():
    fake = FakeTranslator({}, detected="it")
    filled, detected = fill_translations(fake, "Tassa cani?", None, ("de", "fr", "it"), have={})
    assert set(filled) == {"de", "fr"} and detected == "it"
    assert [c[1] for c in fake.calls] == ["de", "fr"]           # "it" never requested
    assert fake.calls[0][2] is None and fake.calls[1][2] == "it"  # later requests carry the detected source


def test_fill_translations_drops_the_first_translation_when_it_was_into_the_detected_language():
    fake = FakeTranslator({}, detected="de")
    filled, detected = fill_translations(fake, "Kündigungsfrist?", None, ("de", "fr"), have={})
    assert set(filled) == {"fr"} and detected == "de"


def test_fill_translations_without_a_translator_changes_nothing():
    filled, detected = fill_translations(NoTranslator(), "Hundesteuer?", "de", ("de", "fr"), have={"fr": "x"})
    assert filled == {"fr": "x"} and detected is None


def test_fill_translations_drops_a_language_the_service_could_not_translate():
    class Flaky:
        name = "flaky"

        def translate(self, texts, *, target, source):
            return None if target == "fr" else Translation(("ok",), "de")
    filled, _ = fill_translations(Flaky(), "q", "de", ("fr", "it"), have={})
    assert filled == {"it": "ok"}
