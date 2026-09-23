---
status: accepted
date: 2026-09-23
---

# The four language stores are list partitions of one chunk table in a new `corpus` schema, with one embedding table per model

Every chunk is stored in the language it was published in, and a question must be searchable in one language or in all of them at once. We keep one `corpus.chunk` table partitioned by `language` (de, fr, it, en, rm) rather than four separate tables or databases: each partition gets its own vector and keyword indexes, a single-language search prunes to one partition, a cross-language lookup of aligned chunks is one indexed query over `(translation_group_id, align_key)`, and there is one schema to migrate. The keyword index uses a per-language text-search configuration with accent folding (German, French, Italian and English stemmers; Romansh without stemming), weighted breadcrumb over description over text. Vectors live outside the chunk table, one partitioned table per embedding index (`emb_openai_3l` as `halfvec(3072)`, `emb_bge_m3` as `vector(1024)`), so a model can be added, rebuilt or dropped without touching chunks, and the local index can be filled in the background while the other serves.

The new schema sits beside the existing `public.document`/`public.chunk` tables instead of replacing them, so the running server keeps working until the serving track switches to it.

## Considered Options

- Four separate tables or databases: four migrations, four sets of queries, and cross-language alignment becomes a join across tables.
- One unpartitioned table with a language column: works, but every vector search scans an index over all languages and per-language keyword configurations cannot be applied per partition.
- Vectors as columns on the chunk table: adding the second model would rewrite the whole table, and a missing vector would be a null inside the evidence row.
