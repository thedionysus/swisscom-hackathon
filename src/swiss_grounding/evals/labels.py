"""Relevance labels: a model judges (question, passage) pairs; a human checks a sample (ADR 0016)."""
import random
from collections.abc import Callable, Mapping, Sequence

from swiss_grounding.corpus.budget import cost_usd
from swiss_grounding.corpus.providers import LLMProvider, ReplyError
from swiss_grounding.corpus.runner import LlmTask

LABEL_KIND = "eval_label"
MIN_AGREEMENT = 0.85
SYSTEM = ("You judge search results for a Swiss public-information service. Given a user's question and one "
          "passage from an official source, decide whether the passage answers the question or states a fact "
          "needed to answer it for the place asked about. Answer JSON: {\"relevant\": true|false, "
          "\"reason\": \"<one short sentence>\"}.")


def label_task(pair: Mapping, model: str) -> LlmTask:
    return LlmTask(custom_id=f"{pair['probe_id']}|{pair['key']}", model=model, system=SYSTEM,
                   user=f"Question: {pair['question']}\n\nPassage:\n{pair['passage']}", max_output_tokens=120)


def judge_pairs(pairs: Sequence[Mapping], llm: LLMProvider, *, model: str,
                on_usage: Callable[[float], None], on_row: Callable[[dict], None] = lambda row: None) -> list[dict]:
    """Judge each pair. Spend is reported per reply (also for unparseable ones, which are skipped),
    and each row is handed to on_row as soon as it exists, so an interrupted run loses nothing."""
    rows = []
    for pair in pairs:
        try:
            reply, usage = llm.complete(label_task(pair, model))
        except ReplyError as exc:
            on_usage(cost_usd(model, exc.usage.input_tokens, exc.usage.output_tokens, batch=False))
            continue
        on_usage(cost_usd(model, usage.input_tokens, usage.output_tokens, batch=False))
        row = {**pair, "relevant": bool(reply.get("relevant")), "reason": str(reply.get("reason", "")),
               "judge": model}
        on_row(row)
        rows.append(row)
    return rows


def sample_for_review(rows: Sequence[Mapping], n: int, seed: int) -> list[Mapping]:
    return random.Random(seed).sample(list(rows), min(n, len(rows)))


def agreement(judged: Sequence[Mapping], human: Mapping[tuple[str, str], bool]) -> float:
    compared = [(r["relevant"], human[(r["probe_id"], r["key"])]) for r in judged
                if (r["probe_id"], r["key"]) in human]
    return sum(1 for a, b in compared if a == b) / len(compared) if compared else 0.0
