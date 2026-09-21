---
status: accepted
date: 2026-09-21
---

# Topic is a constraint on retrieval, and it is decided per chunk

Categories were a soft rerank signal that never excluded anything, and a source's declared categories were written onto every document it produced at full confidence, overwriting the classifier. Fedlex declares five, so 563 of the 795 chunks in the index — 71 per cent — assert dogs, hiking, safety, transport and waste simultaneously, and an article levying a tax on solvent imports is tagged `dogs`. A hint that everything carries cannot discriminate, and measurement confirmed it: supplying `categories: ["dogs"]` moved every candidate by exactly +0.3 and changed neither the order nor the membership of the result.

A question is about a subject as much as it is about a place, and the server already treats place as a hard filter. Topic now works the same way: a chunk that does not carry the question's topic is not evidence for that question. The topic is decided per chunk, from the chunk's own text, because a hundred-article act is not about one subject and filing every article under the act's union of subjects is what produced the failure above. A source's declared categories survive only as a fallback for a chunk the classifier returns nothing for.

We rejected keeping topic as a ranking signal, because no weighting of a tag carried by 71 per cent of the corpus separates anything. We rejected classifying per document, because it is the granularity that caused the defect. We rejected dropping the fixed taxonomy in favour of a similarity threshold against free text, because a threshold on similarity is a magic number fitted to one corpus, and measurement showed the scores do not separate cleanly.

## Consequences

- Re-tagging reads text already stored, so it costs one model call per chunk and needs no re-crawl and no re-translation. This is affordable while translation credits are not available.
- `swiss_search` can now return no evidence because nothing on the extent path carries the topic. ADR 0001 governs the case where a *place* has no documents; this is the case where a *subject* has none, and the two compose.
- A wrong topic hides correct evidence rather than merely misranking it. The classifier keeps every category within a margin of the best rather than taking the single best, so a near-tie keeps both.
- `source.categories` changes meaning: it declares what a source is expected to cover, and no longer asserts what each of its documents is about.
