# Research: query-time decisions

Research for the serving track, written one section at a time just before the matching grill question is decided. Workstream letters follow the production-readiness brief (H = retrieval and scoring). Measurements were taken on the development machine (Apple M1 Pro, 16 GB, torch 2.14 with MPS, sentence-transformers 6.0.1) on 2026-09-23. The scripts live in the session scratchpad, not in the repo; the numbers are reproducible with `sentence_transformers.CrossEncoder`.

## H1. What one number decides ranking, confidence and abstention (grill question S2)

### Rank fusion cannot abstain

Reciprocal rank fusion (RRF) scores a chunk only by its rank in each list: `Σ 1/(k + rank)`. The top chunk of every query gets roughly the same score whether or not it is relevant, so no RRF threshold separates "found it" from "found nothing" ([analysis](https://dev.to/ji_ai/reciprocal-rank-fusion-why-k60-buries-your-best-hit-525c); [when to skip RRF](https://dev.to/aws-builders/reciprocal-rank-fusion-rrf-how-it-works-and-when-to-skip-it-4obi)). RRF works well for merging candidate lists. It cannot be the confidence number.

### A cross-encoder score can abstain, but it is biased across languages

We scored hand-written probe passages with `BAAI/bge-reranker-v2-m3` (sigmoid output):

| Question | Passage | Score |
|---|---|---|
| DE "Kündigungsfrist Mietwohnung" | Art. 266c OR, **German** | 0.978 |
| same | Art. 266c CO, **French** (same article) | **0.020** |
| same | Art. 266c CO, **Italian** (same article) | 0.117 |
| same | Art. 335c OR, employment notice (wrong topic) | 0.013 |
| IT "termine di disdetta appartamento" | Italian / German / French 266c | 0.821 / 0.139 / 0.012 |
| RM "vacanzas d'atun Scuol" | Romansh Scuol calendar / German Scuol calendar | 0.998 / 0.997 |
| same | German **Zürich** calendar | 0.436 |
| FR "permis de conduire Vaud" | French Vaud page | 0.997 |
| DE "Rundfunkbeitrag Konstanz" | five unrelated Swiss passages | all 0.000 |

Findings:
1. **Same-language scores separate relevant from irrelevant sharply**, and a question with no relevant passage (Konstanz) scores near zero everywhere. So the score is a usable basis for abstention.
2. **The same article in another language scores as if it were irrelevant** (0.02 for the French version of the answer to a German question). The score cannot be compared across languages as it is. This matters for ADR 0011, where every language store is searched: a single threshold would discard every cross-lingual hit.
3. **Place is not a reranker job.** The Zürich calendar scored 0.44 for a Scuol question. Jurisdiction stays a hard filter applied before scoring.

A smaller multilingual cross-encoder, `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (118M parameters, against 568M), scored the cross-lingual pairs close to the same-language ones (DE question → French 266c 0.98, Italian 0.83) and kept the rest of the pattern (Konstanz all ≤ 0.00, Zürich calendar 0.21). Five questions are a probe, not an evaluation. Which reranker to use is decided on the golden set.

### Speed (30 query–chunk pairs; median chunk + question length 407 tokens, max 499)

| Model | Device | max tokens | 30 pairs |
|---|---|---|---|
| bge-reranker-v2-m3 fp32 | MPS | 512 | 2.7 s |
| bge-reranker-v2-m3 fp16 | MPS | 512 | 2.4 s |
| bge-reranker-v2-m3 | MPS | 256 | 1.5 s |
| bge-reranker-v2-m3 | CPU | 512 | 12.3 s |
| bge-reranker-v2-m3 | CPU | 256 | 4.5 s |
| mmarco-mMiniLMv2-L12 | CPU | 512 | 1.2 s |

The evaluators' machine is unknown and may have no GPU. Reranking 30 candidates with bge-reranker-v2-m3 on CPU takes 12 s per tool call, which is too slow when a client makes several calls per question. Options: rerank fewer candidates, cut passages to 256 tokens, or default to the small model on CPU.

### How many labels a learned score needs

- Logistic regression's own outputs are well calibrated, and sigmoid (Platt) calibration is the right choice for small samples. Isotonic calibration overfits below about 1,000 samples ([scikit-learn calibration guide](https://scikit-learn.org/stable/modules/calibration.html)).
- A common rule of thumb is 10–20 examples of the rarer outcome per feature ([CASRAI on events per variable](https://casrai.org/guides/events-per-variable-and-the-minimum-sample-size-for-regression)). The rule is known to be rough ([van Smeden et al. 2019](https://journals.sagepub.com/doi/10.1177/0962280218784726); [Riley et al.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5045274/)). With about 8 features we need roughly 80–160 relevant and as many irrelevant judged pairs. A golden set of 150 questions with the top 10 candidates judged per question gives about 1,500 pairs, which is enough, with a held-out split for choosing the threshold.

### Consequence for S2

- RRF merges the candidate lists.
- A cross-encoder score is the base for confidence and abstention.
- Language needs handling explicitly: score a translation group by its best language version (the aligned chunk in the question's language, where one exists), and give the learned model a same-language feature.
- A logistic model over the reranker score and the other signals, fitted on the golden set, replaces hand-set thresholds once labels exist.

## H2. pgvector recall settings (RAG review S2)

From the [pgvector README](https://github.com/pgvector/pgvector/blob/master/README.md): `hnsw.ef_search` is the size of the candidate list during search, 40 by default. Iterative scans (`hnsw.iterative_scan = strict_order | relaxed_order`) keep scanning when filters remove results, up to `hnsw.max_scan_tuples` (20,000 by default). `relaxed_order` gives better recall at the cost of slightly out-of-order distances. That doesn't matter here, since the reranker re-orders the candidates anyway. The README recommends list partitioning when filtering by many values, which matches ADR 0010. HNSW on `sparsevec` accepts at most 1,000 non-zero elements.

Decided for serving:
- `SET LOCAL hnsw.ef_search = 100` per search transaction (at least the per-arm candidate count of 30 with room to spare).
- `SET LOCAL hnsw.iterative_scan = relaxed_order`.
- The language filter prunes partitions.
- When a place is resolved, candidates are drawn per jurisdiction level: at least 10 of the top 30 come from the resolved canton or municipality, so federal law cannot crowd out local pages (audit weakness "shared 50-candidate pool").
