---
status: accepted
date: 2026-09-23
---

# A hand-written golden set with fixed pass thresholds gates every release; generated questions only measure recall

The 47 existing probes are Zürich-only and were written for English-only indexing, so they cannot set the abstention threshold, fit the relevance probability (ADR 0012), or choose the reranker.

- **Golden set:** about 150 probes written by hand from the challenge's samples and practice cases, stratified by the 16 topic areas, DE/FR/IT/RM, and federal, cantonal and municipal level. It includes about 20 outside-scope, 15 ask-back, 10 multi-place and 5 source-failure probes. Each names its expected status, source and key fact. It is version-controlled, with a held-out split.
- **Generated questions:** about 500, written by gpt-5-mini from known answer chunks. Recall only.
- **Relevance labels:** the top 10 per golden probe are judged by gpt-5-mini (about 1,500 pairs). A human checks 100 of them; at least 85% agreement is required before the labels are used.
- **Pass thresholds:** status accuracy ≥ 0.9; recall@5 ≥ 0.8; precision@5 ≥ 0.7; nDCG@5 ≥ 0.7; faithfulness ≥ 0.9, measured end to end through the MCP with a judge checking each claim against its cited passage.
- **Every run records its configuration and the dataset version.** Evals write to the database only with `--record`.

## Considered Options

- Generated questions only: cheap and large, but a model writing questions from known chunks produces questions that are easy for retrieval, and it never produces outside-scope or ask-back cases.
- Human labels for every pair: the most reliable, but about 1,500 judgements do not fit into the hackathon.

## Consequences

- Status accuracy is the first gate, because it measures what the rubric grades most heavily.
- The existing probes stay as regression tests.
