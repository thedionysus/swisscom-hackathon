---
status: accepted
date: 2026-09-23
---

# A cross-encoder score, later a fitted relevance probability, decides ranking and abstention; each translation group is scored by its best language version

The current ranking orders by specificity tier and then cosine distance, with an uncalibrated relevance floor that can never produce `no_evidence` (audit §4). The challenge grades a clear "not covered" as correct and a guess as wrong, so the server needs one number that can say "nothing relevant was found". Rank fusion cannot supply it, because the top RRF score is nearly the same for every query (`docs/RESEARCH.md` §H1). A cross-encoder can: on the probes, same-language relevant passages score about 0.98 and a question with nothing relevant (Konstanz) scores 0.00 everywhere.

The pipeline is:
1. Hard filters: jurisdiction chain, validity, status.
2. Candidates: dense, sparse and keyword search per language store, merged with RRF into the top 30.
3. Collapse candidates into translation groups. The reranker scores the group's version in the question's language when one exists, otherwise its best-scoring version. The other versions become corroboration.
4. Order by reranker score. Abstain (`no_evidence`) when the top score is below a provisional threshold set on the probes.
5. Once the golden set is labelled, a logistic model gives a relevance probability from these features: reranker score, same-language flag, RRF rank, corroboration count and basis, specificity tier, authority and age. The abstention threshold is then chosen for a target precision on a held-out split.

The reranker model is a configuration value chosen by hardware: `BAAI/bge-reranker-v2-m3` when a GPU or MPS is present, `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` on CPU. The golden-set evaluation decides the defaults.

## Considered Options

- RRF alone: good fusion, but it cannot express "nothing found".
- A hand-weighted sum of tier, cosine distance and corroboration: no calibration, and no principled threshold.
- Scoring every language version on its own: bge-reranker-v2-m3 gives the French text of the right article 0.02 for a German question, so correct cross-language hits would be discarded.

## Consequences

- The relevance floor and the tier-first ordering are retired. The specificity tier stays on every citation and becomes a feature.
- Reranking 30 pairs costs 2.4 s on MPS and 12 s on CPU with bge-reranker-v2-m3, or 1.2 s on CPU with the small model. Latency is logged per call (RAG review S6).
- The golden set must be labelled at pair level (question, chunk, relevant yes/no), about 1,500 judged pairs, before the fitted probability replaces the provisional threshold.
