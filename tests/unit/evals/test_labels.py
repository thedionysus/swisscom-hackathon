from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.evals.labels import (
    LABEL_KIND,
    agreement,
    judge_pairs,
    label_task,
    sample_for_review,
)

PAIR = {"probe_id": "g1", "key": "https://x#a", "question": "Kündigungsfrist?", "passage": "drei Monate"}


def test_task_asks_for_a_json_verdict_with_minimal_tokens():
    task = label_task(PAIR, model="gpt-5-mini")
    assert task.custom_id == "g1|https://x#a" and "relevant" in task.system and task.max_output_tokens <= 200


def test_judge_pairs_records_verdicts_and_spend():
    spent = []
    llm = FakeLLM(lambda t: {"relevant": True, "reason": "states the period"})
    rows = judge_pairs([PAIR], llm, model="gpt-5-mini", on_usage=lambda usd: spent.append(usd))
    assert rows == [{**PAIR, "relevant": True, "reason": "states the period", "judge": "gpt-5-mini"}]
    assert spent and spent[0] > 0 and LABEL_KIND == "eval_label"


def test_an_unparseable_reply_is_skipped_but_its_spend_is_reported():
    from swiss_grounding.corpus.providers import ReplyError, Usage

    class Broken:
        def complete(self, task):
            raise ReplyError("bad", Usage(100, 10))
    spent = []
    assert judge_pairs([PAIR], Broken(), model="gpt-5-mini", on_usage=spent.append) == []
    assert spent and spent[0] > 0


def test_sample_is_deterministic():
    rows = [{**PAIR, "key": str(i), "relevant": True} for i in range(300)]
    assert sample_for_review(rows, 100, seed=7) == sample_for_review(rows, 100, seed=7)
    assert len(sample_for_review(rows, 100, seed=7)) == 100


def test_agreement():
    judged = [{"probe_id": "a", "key": "1", "relevant": True}, {"probe_id": "a", "key": "2", "relevant": False}]
    human = {("a", "1"): True, ("a", "2"): True}
    assert agreement(judged, human) == 0.5
