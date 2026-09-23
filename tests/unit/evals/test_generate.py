from swiss_grounding.corpus.providers import FakeLLM, ReplyError, Usage
from swiss_grounding.evals.generate import SAMPLE_SQL, generate_questions

CHUNK = {"chunk_id": 1, "language": "fr", "url": "https://x", "anchor": "a", "extent_id": "CH-VD",
         "breadcrumb": ["Permis"], "text": "Le permis étranger doit être échangé dans les 12 mois."}


def test_generates_a_question_in_the_chunk_language_with_its_key():
    llm = FakeLLM(lambda t: {"question": "Dans quel délai dois-je échanger mon permis?"})
    [row] = generate_questions([CHUNK], llm, model="gpt-5-mini", on_usage=lambda usd: None)
    assert row["key"] == "https://x#a" and row["language"] == "fr" and row["question"].endswith("?")


def test_sample_sql_is_stratified_by_language_and_level():
    assert "partition by c.language" in SAMPLE_SQL and "tablesample" not in SAMPLE_SQL


def test_reply_error_reports_spend_and_skips_the_chunk():
    calls = []

    class FailingLLM:
        def complete(self, task):
            raise ReplyError("unparseable reply", Usage(input_tokens=10, output_tokens=5))

    rows = generate_questions([CHUNK], FailingLLM(), model="gpt-5-mini", on_usage=calls.append)
    assert rows == []
    assert calls and calls[0] > 0
