# Worth borrowing later (from the Jev tests, 2026-09-23/24)

These are not part of the topic check. Each needs its own test on our data before anyone builds it.

## 1. A claim-by-claim faithfulness check for our judge (from jkudish/jev-mcp, MIT)

- **The design:**
  - Split an answer into atomic factual claims.
  - For each claim, give one verdict: *supports*, *contradicts* or *says_nothing*. Also name the evidence
    item the claim rests on, or none.
  - A missing or malformed verdict is recorded as invalid, never as "unsupported"
    (jev-mcp `src/index.ts:217` at `7162ac4`).
- **The verdict wording** (`src/index.ts:173-175`):
  - supports: "The evidence states the claim or directly implies that it is true"
  - contradicts: "The evidence states the opposite of the claim or implies that it is false"
  - says_nothing: "The evidence does not address what the claim asserts, either way"
- **Where it fits.** ADR 0016 sets a faithfulness gate of at least 0.9, "measured end to end through the MCP
  with a judge checking each claim against its cited passage". This is a ready template for that judge.
  Run it on our own judge model, because splitting an answer into claims needs a generative model.
- **Evidence** (federal test T2, with Jev as the judge; `jev-live-tests/federal/results/score_output_as_printed.md`):
  - 23 of 24 claims were judged as expected.
  - Both deliberately wrong descriptions were caught, with no false alarm on the 8 correct ones.
  - It **missed** "ten years" where the text said five. Pair it with a plain check that every number in a
    claim appears in the cited passage.
  - Whether our own judge does as well is untested (*inferred* transfer).

## 2. In-force dates by picking among candidates (from jkudish/jev-mcp)

- **The design:**
  1. A regex proposes the date strings found in the text.
  2. The model picks one of them, or `none_of_them`.
  3. The value is copied verbatim from the chosen candidate and never generated (`src/index.ts:1098`).
  - Working Python for this: `jev-live-tests/municipal/run_muni.py` (`DATE_RE`, `iso()`, the date question).
- **Evidence:**
  - 14 of 15 Fedlex acts, German text, gold `jolux:dateEntryInForce` (`federal/results/*_as_printed.*`).
  - 12 of 12 Basel-Stadt laws, gold the portal's `enactment` field (`municipal/results/summary.md`). Two
    naive regex rules got 3 of 12 there (a check run in the session, not saved as a file).
- **Limits:**
  - Both sources already carry the date as metadata. The real target, documents without
    `corpus.document.valid_from`, is untested.
  - Confidence cannot decide what gets reviewed: correct Basel answers ranged from 0.38 to 0.99.

## 3. Operational lessons for any Jev call

- **Send one request at a time, about 1 s apart, and honour `retry-after`** on 429 and 5xx (Vercel asked
  for up to 60 s). Eight parallel requests with a fixed 1-2-4 s backoff lost 39 of 75 items
  (`jev-live-tests/typesafe-mcp/results/summary.md`).
- **Report AUC next to precision and recall.** Every topic design ranked almost perfectly (AUC ≥ 0.986);
  what differed was the cut between "a topic" and "none".
- **Store the model id and the time with every result.** Vercel lists a single, unpinned `typesafe-ai/jev`.
- **Endpoint:** `POST https://ai-gateway.vercel.sh/typesafe/v1/systemone` with a Vercel AI Gateway key.
- **Cost:** about $0.03–0.05 per 1,000 chunks at list price. Vercel reported $0 on every call.
