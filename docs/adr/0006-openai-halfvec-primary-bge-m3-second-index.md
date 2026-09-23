---
status: accepted
date: 2026-09-23
---

# OpenAI text-embedding-3-large stored at full width as halfvec is the primary index; bge-m3 is a second, local index

The corpus is encoded once with real keys (OpenAI and Anthropic; no Voyage key), and every vector belongs to the model that made it, so the model choice is the most expensive decision to reverse. We store OpenAI `text-embedding-3-large` at its full 3,072 dimensions as pgvector `halfvec`, because the HNSW index accepts at most 2,000 dimensions for 32-bit `vector` but 4,000 for 16-bit `halfvec`, so no dimension is thrown away and the storage equals a 1,536-dimension 32-bit vector. A shorter index can later be built from the stored vectors without calling OpenAI again, because the model is trained so that its leading dimensions form a usable embedding on their own. We also encode every chunk with local `BAAI/bge-m3` (1,024 dimensions) into a separate index, because it costs nothing, keeps a sovereign path that needs no foreign API, and turns the embedding comparison the evals require into a measurement on our own questions rather than a benchmark citation. Measured on the project laptop (M1 Pro, 16 GB, 2026-09-23): 12.4 chunks/s on the GPU, about 11 hours per 500k chunks before descriptions are added.

## Considered Options

- Request 1,536 dimensions from the API: same storage, but discards detail we cannot recover without re-encoding.
- Store 3,072 at 32-bit and index a 1,536 slice: lossless, but twice the storage and a two-step search for a gain smaller than the halfvec rounding.
- Voyage: no key available.

## Consequences

- Every index records its model name, version and dimension; vectors from two indexes are never compared, and switching the primary model means re-encoding into a new index, not overwriting.
- bge-m3 encoding runs in the background and resumes where it stopped; the OpenAI index never waits for it.
- Amended 2026-09-23: a question can only be compared with vectors made by the same model, so serving from the OpenAI index needs an OpenAI key for every question. The server therefore answers from the bge-m3 index by default and needs no key at query time; the OpenAI index is used only when a key is configured. Keys are needed for ingestion only.
- Clarified 2026-09-23: "ingestion" includes building the bge-m3 index. The model runs locally, but it embeds each chunk's generated description (ADR 0005), and writing descriptions needs a key. A keyless build (`corpus embed --index bge-m3 --allow-undescribed`) embeds breadcrumb and text only, and is re-embedded once descriptions exist. Evaluators use the prebuilt dump and need no key.
- Flagged 2026-09-24 (open decision, #52): the code default is now bge-m3 only and the OpenAI index is opt-in (`CORPUS_INDEXES`, see AGENTS.md), so "primary" in the title no longer describes the default. AGENTS.md also says not to pass `--index` by hand, while the clarification above names `corpus embed --index bge-m3 --allow-undescribed`. Amend this ADR or supersede it (next free number: 0019; PR #49 gives 0018 to the Postgres ADR).
