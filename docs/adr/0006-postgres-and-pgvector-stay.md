---
status: accepted
date: 2026-09-22
---

# Postgres with pgvector stays; SurrealDB was evaluated and not adopted

SurrealDB (github.com/surrealdb/surrealdb, 3.2.4 stable, 3.3 in beta, Business Source License 1.1 until 2030) was evaluated on 2026-09-22 as a replacement for Postgres + pgvector, on the hypothesis that a multi-model engine with graph relations and in-database hybrid search would improve retrieval. It would not. Retrieval quality in this system is decided in application code, not by the engine: the jurisdiction hierarchy is a materialised `location.path` array filtered with one equality check, so nothing is traversed at query time; reciprocal rank fusion, the specificity, authority and recency scoring, and the diversity caps all run in Python after the database returns candidates; the known quality gaps (#32 lexical query ANDs the place name, #33 latent HNSW recall cap, #34 single candidate pool, #24 unindexed heading paths, #10 English-only indexing) live in those layers. The production dense query ran in 11.6 ms and the lexical one in 0.4 ms on 5,195 chunks; Postgres ships German, French and Italian full-text configurations and pgvector 0.8.1 has iterative scans for filtered HNSW, both unused today. SurrealDB's open issues sit exactly on the path this project would use: #7423 (filtered HNSW KNN silently drops results after delete/overwrite churn, which every re-ingest performs), #7424 (RocksDB resident memory grows to nine times the dataset with ~12k HNSW vectors, OOM-killed), #7430 (surrealkv OOM regression), #7337 (DiskANN without a memory cap), #6819 (HNSW read lock starves other queries), #7383 (OOM under full-text load); filtered vector search was being reworked in the 3.3 betas. Switching would rewrite 13 modules, 51 SQL call sites and 22 integration test files two days before the deadline. We rejected the switch and recorded the levers that do move retrieval quality as issues #32–#36.

## Consequences

- Retrieval work targets the application layer: query formation, candidate pooling, index configuration, reranking.
- If a norm-hierarchy or citation graph is added later (#47), it is an edge table with a recursive CTE in Postgres, not a reason to change engines.
- Re-evaluate only if a workload needs graph traversal at query time or live query subscriptions, which this system does not.
