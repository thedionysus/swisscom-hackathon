"""Generated questions: one per sampled chunk, answerable by that chunk. Recall only."""
from collections.abc import Callable, Mapping, Sequence

from swiss_grounding.corpus.budget import cost_usd
from swiss_grounding.corpus.providers import LLMProvider, ReplyError
from swiss_grounding.corpus.runner import LlmTask

GENERATE_KIND = "eval_generate"
SYSTEM = ("Write one question a resident of Switzerland might ask that the passage answers. Write it in the "
          "passage's language, as a person would type it, without quoting the passage or naming its article "
          "number. Answer JSON: {\"question\": \"...\"}.")
# Up to `per_stratum` random current chunks per (language, source level), skipping boilerplate and tiny chunks.
SAMPLE_SQL = """
select * from (
  select c.id as chunk_id, c.language, d.url, c.anchor, c.extent_id, c.breadcrumb, c.text,
         row_number() over (partition by c.language, s.level order by md5(c.id::text || %(seed)s)) as n
  from corpus.chunk c join corpus.document d on d.id = c.document_id join corpus.source s on s.id = d.source_id
  where c.status = 'current' and d.status = 'current' and length(c.text) > 200
) t where n <= %(per_stratum)s
"""


def generate_questions(chunks: Sequence[Mapping], llm: LLMProvider, *, model: str,
                       on_usage: Callable[[float], None]) -> list[dict]:
    """One question per chunk. A reply that fails to parse still billed tokens: report spend and skip it."""
    rows = []
    for c in chunks:
        task = LlmTask(custom_id=str(c["chunk_id"]), model=model, system=SYSTEM,
                       user=f"Passage ({c['language']}):\n{' › '.join(c['breadcrumb'])}\n{c['text'][:2000]}",
                       max_output_tokens=120)
        try:
            reply, usage = llm.complete(task)
        except ReplyError as exc:
            on_usage(cost_usd(model, exc.usage.input_tokens, exc.usage.output_tokens, batch=False))
            continue
        on_usage(cost_usd(model, usage.input_tokens, usage.output_tokens, batch=False))
        key = f"{c['url']}#{c['anchor']}" if c["anchor"] else c["url"]
        rows.append({"chunk_id": c["chunk_id"], "key": key, "language": c["language"],
                     "extent_id": c["extent_id"], "question": str(reply.get("question", "")).strip()})
    return [r for r in rows if r["question"]]
