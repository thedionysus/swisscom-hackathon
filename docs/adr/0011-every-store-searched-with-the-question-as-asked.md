---
status: accepted
date: 2026-09-23
supersedes: 0004-the-calling-model-supplies-the-english-query
---

# Every language store is searched with the question as asked; client translations are an optional boost

The server answers without any API key (ADR 0006), is tested through two unknown MCP clients with two unknown models, and receives questions in German, French, Italian and Romansh. We search every language store with the user's question exactly as written, relying on the multilingual embedding model to match across languages, so a client that sends nothing extra still gets full recall. When a client also supplies the question in other languages, each store is additionally queried in its own language, for both vector and keyword search. Corroboration records its basis: `independent` when separate per-language queries found the aligned chunks, `cross_lingual` when one vector found them; the weight given to each basis is fitted on the evals, not assumed.

## Considered Options

- Require the client to translate (the ADR 0004 contract): real independence, but weak clients skip or garble it, and nothing in the response can repair that.
- Translate on the server: real independence, but needs a key for every question, the operability cost ADR 0006 avoided.

## Consequences

- ADR 0004's `question_en`/`topic_en` contract is retired; the tool accepts optional per-language queries instead.
- Keyword search only helps in the question's own language unless translations are supplied, so the lexical arm is strongest for exact references (SR numbers, article numbers, names) that are language-independent.
- Corroboration from a single cross-lingual vector partly measures the model's own alignment, which is why its basis is published and weighted separately.
