# Jev integration: tested, not yet integrated

Jev is TypeSafe's model for typed judgments: it answers yes/no or pick-one questions about a passage with a
probability, and writes no text. It was called through Vercel's AI Gateway (`typesafe-ai/jev`). Every use
tested here runs offline, over the corpus or over eval results, so the search path stays keyless. It was
explored on 2026-09-25 and is not part of the code: integrating it is future work, left out for lack of time.
The goal is answer quality. Diagrams: [architecture](diagrams/32-jev-architecture.html), [deployment](diagrams/33-jev-deployment.html) and [one batch end to end](diagrams/34-jev-sequence.html).

## Where we tested Jev

| Where | Question Jev answered | Test | Result | Next step |
|---|---|---|---|---|
| Chunk cleaning | Is this chunk real content or page furniture? | 75 hand-labelled municipal chunks; 9,990 random live chunks | Separates junk from content with AUC 0.98. At a cut-off of 0.8: 26 of 35 junk chunks caught, 0 of 40 content chunks lost. In the corpus, 13 of 15 flagged chunks read were junk | Fix the cut-off on a fresh labelled sample, then mark flagged chunks `boilerplate` |
| Data cleaning (dates) | Which date is the page's "as of" date, and which its "valid from"? | 30-document pilot, two labellers | "As of": 13 of 14 picks right, 13 of 15 found. "Valid from": 4 of 8 right | Run the prepared 150-document test; show the date on citations, not as a filter |
| Categorization (topics) | Which of the 20 topics is the chunk about? | 30-chunk pilot; 75 municipal chunks | 0.88 precision on content chunks; 0.91/0.91 on municipal chunks (in-sample). Junk chunks get topics too | Only once search reads topics; today it does not (`README.md:280`) |
| Place logic | Does this federal passage leave the answer to the canton or commune? | 150 labelled federal passages; 7,410 random live federal chunks | F1 0.88, against 0.17 for the current regex. In the corpus, 14 of 15 regex-only flags read were wrong; 11 of 14 Jev-only flags were right | Fix the regex (below), then store a Jev flag per federal chunk and read it instead |
| Answer checking | Does the evidence support each claim of an answer? | 41 claims from the stored faithfulness answers, plus 19 planted wrong claims | 59 of 60 as labelled; 19 of 19 planted claims caught; no false alarm on the 39 supported claims | Keep the judge's claim list, then add Jev as a second verdict per claim |

Not tested yet: relevance labels for `eval label` ("does this passage answer the question?").

## Throughput and cost

One hour on the whole corpus (2026-09-25, 07:32–08:33 UTC), chunks in random order, 30 passages per request,
two requests in flight per question:

| Measure | Value |
|---|---|
| Passages judged | 17,400, in 580 requests |
| Rate | about 17,000 passages per hour |
| Retries | 340 of the 580 requests needed one; 692 × 503 and 93 × 429 over the hour |
| Answer time | 0.3–0.6 s median per request |
| Cost | $0.0186 per 1,000 passages at list price; $0 billed |
| Whole corpus (305,352 passages) | about 18 hours at this rate |

- 30 passages per request gave the same verdicts as one per request on the labelled set: 146 of 150 alike,
  AUC 0.992 against 0.991.
- More requests in flight did not help: 8 and 16 gave 2.6–2.8 passages per second, 4 gave 4.9.
- The limit is TypeSafe's capacity behind the gateway (503, and 429 "providers … at capacity"), not Jev and not
  a Vercel rate limit: the gateway sends no rate-limit headers. The `digitalocean` route failed on every
  attempt seen; `providerOptions.gateway.order: ["typesafe-ai"]` tries TypeSafe first. Regular runs over the
  whole corpus need dedicated capacity.

## Found on the way

- `serving/place_dependent.py:134`: the third branch of `DEFER` ends in `{LEVELS}?`, so the canton/commune
  word is optional and "je nach", "selon le" or Italian "da … a …" match on their own. It fires on 5,219 of
  68,013 live federal chunks; 44 of 48 false hits in the sample matched without any level word. A hit turns
  an answer into `needs_location` (`serving/status.py:73-75`).
- `evals/judge_harness.py:20` keeps only `faithful` and `cited_urls_in_evidence`, so the judge's
  `unsupported_claims` are dropped.
- 11 of the 12 answers in `evals/judge/faithfulness-*.jsonl` are identical in all three runs; only
  `g-fed-vote-booklets-rm` differs.
- 137 live chunks hold letter-spaced PDF text ("d e g l i a l l i e v i"), most from `gibloux_commune` (41)
  and `echarlens_commune` (40).

## How it was measured

- One labeller (Claude) for every label, hashed before the first Jev call; the corpus spot-checks were read by
  the same person. A second labeller should confirm the results before anything is built.
- The 0.8 junk cut-off was chosen after seeing the scores.
- The hour's chunks were drawn in a fixed random order, so they are a random sample of the corpus.
- The test kits, labels and raw answers are not part of this change.

## Next steps

1. Fix the regex, and store a Jev "defers" flag for federal chunks.
2. Keep the judge's claim list, and add Jev as a second verdict per claim.
3. Settle the junk cut-off and the date question on fresh samples with a second labeller.
4. Test Jev relevance labels against `eval label`.
5. Get dedicated TypeSafe capacity before running over the whole corpus regularly.
