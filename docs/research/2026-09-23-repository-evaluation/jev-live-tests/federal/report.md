# Jev live test on our own text, 2026-09-23

**Setup.** `typesafe-ai/jev` through Vercel AI Gateway's TypeSafe-compatible endpoint
(`POST https://ai-gateway.vercel.sh/typesafe/v1/systemone`, contract from Vercel's docs fetched this
session). Test data is real Fedlex acts in German and in their official English editions, parsed with
**our own** `parse_akoma_ntoso` (`src/swiss_grounding/ingest/fetchers/fedlex.py:66-78` at `9c8fd14`), so
the chunks are what our pipeline stores.

Labels were written by the orchestrator (Claude) **before any Jev call** (`jev-test/data/labels.json`).
They are not a human gold standard. Question wording for T2 and T3 is copied from jev-mcp
(`src/index.ts:170-177`, `1030-1036`).

Raw responses: `jev-test/results/raw_t*.jsonl`. Scores: `jev-test/results/summary.md`.
Scripts: `jev-test/run_tests.py` and `score.py`.

## Results

| Test | What | Result |
|---|---|---|
| **T1** topics, multi-label: one yes/no per category (10 per request), English text, 40 articles from 9 acts | Would Jev tag chunks for ADR 0003's hard topic filter? | **Ranking is excellent; the probabilities run low.** The top category was a correct label in **26/26** labelled chunks, with a ranking AUC of 0.998 (correct vs wrong labels). Only 4 of 357 wrong-category probabilities exceed 0.10 (max 0.24). At a fixed 0.5 threshold, recall is only 0.27 (precision 1.00); at 0.3, recall is 0.62 (precision 1.00). The rule "top category if ≥ 0.10" gives **precision 0.96 and recall 0.96**, and keeps 3 of 4 no-topic articles empty. |
| **T2** claim check of written chunk contexts (jev-mcp's verify wording), 10 contexts, 24 claims | Would it catch a wrong generated `context_en` (ADR 0005's accepted risk)? | **23/24** claims as expected. All 8 correct contexts passed at probability 1.0, so there were **no false alarms**. **Both wrong contexts were caught:** "can never be interrupted" came back contradicts 1.0, and an invented cost-recovery claim came back says_nothing 0.8. **Missed:** "ten years" against the text's "five years" came back *supports* 0.68. |
| **T3** entry-into-force date, a pick among regex candidates (jev-mcp's extract wording), German text, 15 acts, gold = Fedlex `jolux:dateEntryInForce` | Can it fill `valid_from`-style dates verbatim? | **14/15** exact, despite 2 to 15 distractor dates per act (adoption, Federal Council decision and amendment dates). Confidence was ≥ 0.97 on all 14. The 15th, SR 741.01, entered into force in stages: Jev chose the date on which "all remaining provisions" took effect (1 Jan 1963), while Fedlex records the first partial date (1 Oct 1959). My question ("as a whole first entered into force") was ambiguous there, and Jev's **confidence dropped to 0.63**. |
| **T4** the T1 questions on the German originals of 10 chunks | Does it read German as well as the English translation? | **Mean difference EN vs DE 0.009, maximum 0.15** over 100 category pairs; the same topic set at 0.5 in 10/10. |

**Operations.**
- **Latency:** median 389 ms, maximum 1.6 s per request (10 questions).
- **Reliability:** after about 30 back-to-back calls, **46 of 123 HTTP attempts returned 429** "upstream provider is currently experiencing high demand", plus 2 × 503. With 1 s pacing and the server's `retry-after` (18 to 32 s), all 75 items completed.
- **Cost:** Vercel reported **cost "0"** on all 75 successful calls; why is not known. At the listed $0.042 per million input tokens, the 82,719 input tokens would be about $0.0035.
- **Choice answers:** these return `choice`, `confidence` and full `probabilities` through Vercel, which settles the open question in the jev-mcp report.

## What it means for integration (updates the addendum)

1. **Per-chunk topics at ingest: viable.** Use it as a cheap second opinion next to `describe`, or to tag
   chunks without Anthropic credits. Generating `context_en` still needs a generative model. Use a
   top-1 or relative rule, **not** a fixed 0.5 threshold; the low absolute probabilities are consistent
   with #29 (confidence semantics). Calibrate on a larger labelled set before it becomes a hard
   filter.
2. **Date extraction: viable.** German works, and low confidence flags ambiguous staged commencements
   for review. The real gap is **pages without metadata** (municipal and cantonal); this test used
   Fedlex because it has ground truth.
3. **Guard on generated context: good at invented claims, weak on numbers.** Pair it with a
   deterministic check that every number in a claim appears in the source text. Numbers (fees,
   deadlines, fines) are what matter most in our domain.
4. **Screening before translation is feasible** given T4. Topic or substance checks on German text
   could run before paying for translation. Not tested here.
5. **Main risk is operational:** capacity 429s at a modest rate. Ingest would need queueing and backoff,
   and must not make a crawl depend on Jev being available.

## Not tested

- Relevance labelling for evals
- Injection screening
- Substance and boilerplate screening
- Chunks with genuinely several topics (most of these chunks have one)
- Municipal and cantonal web pages
- French and Italian
- Transport and parking topics (no English federal act in the sample)
- Behaviour at ingest scale (thousands of chunks)

## Caveats

- 40 chunks, federal law only.
- Labels by the orchestrator, not a person.
- One question wording per test; wording can move Jev's probabilities.
- The key used is the user's test key, capped at $2.
