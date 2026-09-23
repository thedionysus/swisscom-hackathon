# RAG architecture review against the `rag-architect` skill

Reviewed 2026-09-23. Subject: the encoding-track plan (`docs/superpowers/plans/2026-09-23-encoding-track.md`), ADRs 0006–0011, and the serving-track decisions so far. Yardstick: the skill's MUST / MUST NOT lists, its chunking, embedding, retrieval and evaluation references (`~/.claude/skills/rag-architect/`). Each finding says whether it changes what gets encoded tomorrow (and so must be fixed in the plan before approval) or only the serving track (can wait).

## Scorecard

| Skill rule | Our plan | Verdict |
|---|---|---|
| Hybrid search (vector + keyword) | Dense per language partition + per-language weighted `tsv` with accent folding | ✓ (serving must use it) |
| Metadata filters | Jurisdiction path, status, validity, language, topic | ✓ — stronger than the skill's tenant filter |
| Metadata enrichment (source, timestamp, section) | Publisher, authority, extent, breadcrumb, anchor, `fetched_at`, `modified_at`, validity, extraction method | ✓ |
| Idempotent ingestion with deterministic IDs | URL + content-hash identity; deterministic `translation_group_id` | ~ — chunk ids are serial, so a changed document re-pays descriptions and embeddings for unchanged chunks (**finding E3**) |
| Clean before storing | nav/footer stripping + model boilerplate verdict | ~ — the verdict is paid for *after* describing; repeated site furniture is described once per page (**E2**) |
| Don't use chunk sizes without evaluation | 1,800 chars (≈450–600 tokens) by article/paragraph; skill's legal range is 600–800 tokens | ~ — defensible, unmeasured; raw artifacts make re-chunking free of re-crawl |
| Evaluate multiple embedding models on domain data | Two indexes encoded (OpenAI 3-large, bge-m3) | ✓ — better than the skill asks, since the comparison runs on our own questions |
| Version embeddings, plan migration | `corpus.embedding_index`, one table per model, `text_hash` re-embed | ✓ |
| Don't couple the model to application code | `EmbeddingProvider` / `LLMProvider` | ✓ |
| Test at production-like volume | Free full fetch in Task 21 gives real counts; HNSW build time and Docker memory never measured | ~ (**E5**) |
| Reranking before the LLM | Not in any plan | ✗ serving (**S1**) |
| Measure precision@k, recall@k, MRR, NDCG | Not built yet | ✗ serving (**S5**) |
| Monitor latency and quality | Not planned | ✗ serving (**S6**) |
| Handle empty results, malformed docs | Quarantine at ingestion; outside-scope / source-unavailable statuses planned | ✓ / serving |

## Findings that change tomorrow's encoding (fix before approving the plan)

**E1. Use bge-m3's sparse output as a multilingual keyword index — free, same pass.** bge-m3 returns dense *and* learned sparse (lexical-weight) vectors in one forward pass (skill, embedding-models §BGE-M3). Our keyword arm is Postgres `tsv`, which only matches in the question's own language (ADR 0011 accepts this). The sparse vectors are in bge-m3's shared multilingual vocabulary, weight exact tokens such as `336c`, `SR`, `Hundegesetz`, and cost nothing extra to produce since we already run bge-m3. pgvector 0.8.6 stores them as `sparsevec` with an HNSW index (≤ 1,000 non-zero entries per vector; a 500-token chunk has a few hundred). Change: add a `sparse sparsevec(250002)` column to `corpus.emb_bge_m3`, embed with `FlagEmbedding.BGEM3FlagModel(return_dense=True, return_sparse=True)`. Risk: FlagEmbedding on Apple MPS is unverified — a 15-minute spike decides; fallback is today's dense-only path.

**E2. Mark repeated site furniture as boilerplate before paying to describe it.** A cookie banner, contact block or footer that survives HTML cleaning appears as the identical chunk on hundreds of pages of one site; today each copy is described (and only then flagged). Change: before the chunk-description stage, set `status = 'boilerplate'` on every chunk whose `chunk_hash` occurs in ≥ 3 distinct documents of the same source. Free, deterministic, and it shrinks the paid chunk count.

**E3. Reuse descriptions and embeddings for unchanged chunks across versions.** When a page or act changes, `persist` inserts a new document with new chunk rows; every chunk — including the 99% whose text did not change — then has an empty description and no embedding, so the refresh re-pays both. The brief asks for incremental processing ("only re-process what changed"). Change: on insert, copy `description`/`topics` from the superseded version's chunk with the same `(translation_group_id, align_key, language, chunk_hash)`, and in the embed stage copy an existing vector whose `text_hash` matches instead of calling the model.

**E4. bge-m3 sequence length.** `LocalBgeM3` sets `max_seq_length = 1024` tokens; breadcrumb + description + a 3,000-character paragraph can exceed that in German and would be silently truncated. Change to 2,048 (bge-m3 supports 8,192; speed cost is small at our chunk sizes).

**E5. Size check before building indexes.** Expected volume for the declared scope is far below the 1M chunks estimated earlier: roughly 30k law chunks (28 acts × ~300 articles × 3.5 languages) + ~70k HTML chunks + ~5k PDF pages ≈ 100–150k. At that size `halfvec(3072)` is ~1 GB of vectors plus index — fine — but the HNSW build has not been timed and Docker Desktop's memory limit is unknown. Change: after the free fetch, `corpus status` records the real count; before `corpus index`, check `docker stats` memory headroom and set `maintenance_work_mem` to fit; time one partition's build first.

## Findings for the serving track (no re-encoding needed)

**S1. Rerank with a local multilingual cross-encoder.** The skill's largest single precision gain (+10–20% precision@k, +50–100 ms). `BAAI/bge-reranker-v2-m3` is multilingual, local and keyless, so it respects ADR 0006. Its query–passage score is also the strongest feature for the calibrated relevance model and for abstention (the open question S2 of the serving grill).

**S2. Recall safeguards the skill lists for pgvector:** set `hnsw.ef_search` ≥ candidate pool and `hnsw.iterative_scan = relaxed_order` (issue #33); per-extent candidate quotas so federal law cannot crowd out municipal chunks (issue #34).

**S3. Small-to-big.** A paragraph-level law chunk (long articles) should return its whole article to the client: fetch sibling chunks sharing the article's `align_key` prefix. Pure query-time logic.

**S4. Query decomposition without a server LLM.** The paired-jurisdiction case ("Lausanne? And Bern?") is decomposition; since the server is keyless, the tool description instructs the client to call once per place, and the server refuses to merge two places into one search.

**S5. Evaluation with thresholds.** Adopt the skill's structure: a curated golden set (50–200, stratified by topic area, language, level, and including out-of-scope and ask-back cases drawn from the challenge's samples) plus a larger generated set with a held-out split; retrieval metrics precision@5, recall@5, MRR, nDCG@5; pass thresholds precision@5 ≥ 0.7, recall@5 ≥ 0.8, nDCG@5 ≥ 0.7; LLM-judge faithfulness ≥ 0.9, checked against a human-labelled sample. Version the dataset and store the config with every run (audit §9).

**S6. Latency and quality logging** per tool call (p50/p95, empty-result rate, abstention rate), cheap and useful for the operability criterion.

**S7. Measure what the descriptions buy.** Embedding a text-only variant into a scratch bge-m3 table (free, local) gives the ablation "with vs without chunk descriptions" on the golden set.

## Skill advice deliberately not adopted

- **BGE query instruction prefix** ("Represent this sentence…"): applies to bge-large-en, not bge-m3, which is trained without instructions.
- **HyDE, LLM query expansion and rewriting at query time:** each needs a model call per question and breaks keyless serving (ADR 0006); the calling client may do them itself.
- **Late chunking:** needs token-level access to a long-context model; not possible with the OpenAI API and marginal for article-sized legal chunks.
- **Semantic / proposition chunking:** our sources have explicit structure (articles, headings), which beats similarity-based boundaries and keeps language versions aligned.
- **Cohere rerank / Pinecone / Qdrant:** external services or a database change; ADR 0018 stands.
