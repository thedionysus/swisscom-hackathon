<!-- DRAFT, not filed. Labels: enhancement, area:ingest. File only after the fresh-sample re-test (Gate below) and with the owner's approval. -->

# Ingest: a cheap Jev second opinion on chunk topics (one choice with a no-match option)

## Why

- **A wrong topic hides correct evidence.** Topic is a hard filter on retrieval (ADR 0003; today
  `retrieval/search.py:52`), so a wrong or missing topic hides correct evidence rather than merely
  misranking it (ADR 0003:18). ADR 0007:41 leaves open whether it stays a filter on the corpus serving path.
- **Topics come from one paid call per chunk.** A chunk's topics are chosen in the paid describe call
  (`corpus/describe.py:54-66`); until it is described, it carries only the prior. It picks up to three topics and falls back to the prior when it picks none
  (`:84-87`). The prior is empty except for Fedlex, where it is the SR-number topic
  (`corpus/persist.py:84-88`).
- **Nothing checks those topics independently, and re-tagging is expensive.** Changing them after the
  encoding run "costs a second paid pass" (ADR 0007:8).

TypeSafe's Jev model returns typed judgments with probabilities, reached through Vercel AI Gateway. It costs
about $0.03–0.05 per 1,000 chunks at list price. We tested it on our own text three times (evidence below).
Asked the right way, it looks good enough to act as a cheap independent check on production topics. That
is not yet confirmed.

## Evidence so far

From `docs/research/2026-09-23-repository-evaluation/findings/2026-09-24-jev-topic-question-design.md`.
It covers 75 crawled municipal chunks (Stadt Zürich, Ville de Genève, Kanton Zürich) and uses the old ten
categories. Labels came from two blind labellers and were sealed before any call.

| Jev question design | Precision | Recall | German pages (P / R) | False topics on junk |
|---|---|---|---|---|
| Ten independent yes/no questions, "top if ≥ 0.10" | 0.29 | 0.64 | 0.07 / 0.20 | 10 |
| One `choice` over the topics plus `none_of_these`, plain one-line criteria | 0.77 | 0.91 | 0.57 / 0.80 | 3 |
| **The same choice, Winnow-style structured criteria (`what` / `examples` / `not_for`)** | **0.91** | **0.91** | 0.80 / 0.80 | 1 |

- Per chunk, the choice design made fewer errors on 16 chunks and more on 1 (sign test p = 0.0003).
- **The result is in-sample.** The design was fixed after the first design's errors had been seen.
- **Not yet measured:**
  - the twenty topics of ADR 0007;
  - chunks with several topics;
  - how production's own topics score on the same labels.

## Gate: confirm before building

Run `docs/research/2026-09-23-repository-evaluation/jev-live-tests/retest-kit/` on a fresh sample labelled
on the twenty topics:
1. Freeze `prereg_retest.json` and record its hash.
2. Export chunks together with their production topics.
3. Have two blind labellers label them.
4. Ask Jev, then score.

Build only if it **replicates**: precision ≥ 0.70, recall ≥ 0.70, and the precision interval's lower bound
≥ 0.50. It must also be **useful next to production**: where Jev and production disagree and gold decides,
gold sides with Jev at least one third of the time.

## Proposal (after the gate)

1. **`src/swiss_grounding/corpus/jev.py`**: a small synchronous httpx client.
   - Endpoint `POST https://ai-gateway.vercel.sh/typesafe/v1/systemone`, model `typesafe-ai/jev`, key from
     the environment.
   - Send **one request at a time, about 1 s apart, and honour `retry-after`** on 429 and 5xx. Eight
     parallel requests with a fixed 1-2-4 s backoff lost 39 of 75 items to 429s in our test, and Vercel
     asked for waits of up to 60 s.
2. **The question**, built from `corpus.topics.TOPICS`:
   ```json
   {"topic": {"type": "choice",
     "instructions": "Which of the listed topics does the passage's own content in `passage` concern? Pick the single best match.",
     "criteria": {"<id>": {"what": "<label>", "examples": ["<covers, split at commas>"], "not_for": "<shared not_for>"},
                  "none_of_these": {"what": "The passage's own content concerns none of these topics", "examples": ["…"]}}}}
   ```
   - Use the design the re-test confirms: structured criteria (primary in `prereg_retest.json`; texts in
     `retest-kit/criteria_structured.json`), or plain one-line criteria if only those replicate.
   - State: `{"passage": {"page_title": <document title>, "heading": <breadcrumb joined with " > ">, "text": <text[:2500]>}}`.
   - Decision: the chosen topic, unless it is `none_of_these`. Keep the full probabilities.
3. **`swiss-grounding corpus jev-topics [--limit N] [--dry-run]`** (wired in `cli/corpus_commands.py`):
   - Runs on described chunks that are not boilerplate.
   - Writes to a new side table, for example
     `corpus.chunk_topic_check(chunk_id, language, choice, confidence, probabilities jsonb, model, checked_at)`.
   - Prints how often Jev's choice is missing from `chunk.topics`, and lists those chunks.
   - **Changes neither `chunk.topics` nor the query path.**
4. **Spend** goes into the existing ledger under its own kind (`record_spend(kind="jev-topics", …)`,
   `corpus/budget.py:36`), checked against the cap like other paid stages. Vercel reports $0, so record
   the list-price estimate with `estimated=True`.
5. **Later, as a separate decision:** use the disagreements, for example to route chunks for review or
   re-describe, or to fill topics where describe returned none and the prior was used.

## Acceptance

- [ ] The re-test summary, with the hash of `prereg_retest.json` recorded before labelling, shows both gate
      conditions met, and is linked here.
- [ ] `corpus jev-topics --limit 20 --dry-run` prints the requests and makes no call.
- [ ] A live `--limit 200` run finishes with no lost chunks at the default pacing, and reports its spend
      under `jev-topics`.
- [ ] Unit tests cover these, with a fake transport and no network:
  - the question builder: 21 options, none present, text equal to `TOPICS`;
  - the reply parser: none means no topic; a malformed reply is quarantined, not stored;
  - the backoff: honours `retry-after`, retries 429 and 503.

## Not in scope

- **Replacing describe's topics.** A single choice is effectively single-label: keeping near-ties added no
  second topic in our test. Production allows up to three, and ADR 0003 keeps near-ties.
- **Any model call on the query path.** The server answers with no key (AGENTS.md:9-10).
- **The `evaluate` MCP binary (itsmostafa/typesafe-mcp) and its `items` batching.** It was evaluated and
  rejected as a component.
- **In-force dates.** This is a follow-up issue. Picking the date among regex candidates scored 14 of 15 on
  Fedlex and 12 of 12 on Basel-Stadt, but both sources already carry the date as metadata, and confidence
  did not separate right answers from wrong ones on Basel (correct answers ranged 0.38–0.99). It needs its
  own test on documents without `valid_from` before any work.

## Risks

- **The model id is unpinned** on Vercel; answers could change without notice. Store `model` and
  `checked_at` with every result.
- **Gateway capacity:** 429 "high demand" comes quickly without pacing. A crawl or describe run must never
  depend on this step.
- **Text leaves for Vercel and TypeSafe.** Vercel's model list shows zero data retention and no training;
  their terms were not read.

**Suggested PR:**
- New: `src/swiss_grounding/corpus/jev.py`, the side table in `corpus/schema.sql`, and unit tests.
- One command in `cli/corpus_commands.py`.
- No change to `describe.py`, `chunk.topics` or retrieval.
