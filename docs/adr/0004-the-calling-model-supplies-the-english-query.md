---
status: accepted
date: 2026-09-21
---

# The calling model supplies the English query and the topic

Everything is indexed in English, and questions arrive in German, French and Italian. The server cannot translate at query time: the design forbids a model call while answering, and the README promises search keeps working on an empty credit balance. Matching a German question against English category descriptions works, but unevenly — ordinary German costs little, while Swiss compound nouns with no English cognate cost a lot. `Leinenpflicht` was classified as hiking rather than dogs on a margin of 0.008, and `Grüngutabfuhr` scraped in on 0.032.

The caller is already a language model, already reads the user's question, and is already paying for its own tokens. So `swiss_search` asks it for the work: the question as the user wrote it, the same question in English, and a short English description of what the topic is about. The server stays deterministic and offline, and the quality of query understanding rises with the calling model instead of being fixed by whatever the server could do without one.

We rejected translating the category descriptions into German, French and Italian, because measurement put the benefit at one question in eight and it bought confidence rather than correctness, at the price of thirty strings to maintain. We rejected a model call inside the server, because it breaks the offline guarantee that lets chat keep working when credits run out.

## Consequences

- The tool contract changes, so registered clients must be updated. This is the expensive half of the decision.
- Retrieval quality now depends on how well the caller follows the tool description. A weak client gets worse answers than a strong one, and nothing in the response reveals which happened.
- The verbatim question is kept alongside the English one so that original-language terms still have something to match against in the keyword index.
- Probes stay deterministic, because a probe author writes the English fields by hand rather than having a model produce them. All existing probe files gain those fields.
- The local topic classifier remains, as the fallback for a caller that supplies no topic.
