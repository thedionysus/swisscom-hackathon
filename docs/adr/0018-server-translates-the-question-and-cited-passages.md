---
status: accepted
date: 2026-09-24
amends: 0011-every-store-searched-with-the-question-as-asked
---

# The server translates the question into every language store, and cited passages back, through Supertext

ADR 0011 searched every language store with the question as asked and left translation to the client, because a server-side model call needs a key for every question. Measured on the encoded corpus, that is not enough: the multilingual embedding finds pages published in another language less often than expected, and the cross-encoder scores the right passage in another language as if it were irrelevant (docs/RESEARCH.md H1: the French version of the article that answers a German question scores 0.02). A French speaker asking about Zürich gets German pages, if any, in German.

So the server now translates. Before the search, the question is translated into each other language store (German, French, Italian, Romansh, English) and each store gets its own vector and keyword query; the reranker reads every candidate with the question in the candidate's own language. After the search, passages published in a language other than the question's are translated into the question's language and published on the citation as `translated_passage`. The published `passage` is kept verbatim: a citation must stay checkable against its source, and the translation is what the calling model answers from, never what it quotes.

The provider is Supertext (Swiss-hosted, speaks Swiss German, French and Italian variants and Romansh), configured with one key, `SUPERTEXT_API_KEY`. Client-sent translations still win over the server's own. Without the key nothing is translated and the server behaves exactly as under ADR 0011, so the keyless path of ADR 0006 survives as the degraded mode rather than the promised one. Every translation failure is logged and the search goes on untranslated; a translation problem never turns into an error status.

## Considered Options

- Keep ADR 0011 and rely on the multilingual embedding: cheapest, but the reranker's cross-language bias means cross-lingual hits are found and then discarded at the threshold.
- Rerank with the smaller cross-encoder that scores cross-lingual pairs well: fixes ranking only; the citation would still be in the wrong language for the user.
- Translate with the corpus LLM provider (OpenAI or Anthropic): one key fewer, but a chat model is slower and dearer per character than a translation service, and the hackathon supplies a Supertext key.

## Consequences

- Each `swiss_search` costs up to four translation requests before the search (one per other language, run in parallel) and one per source language of the cited passages after it. Golden-set runs spend Supertext credit; set `TRANSLATE_CITATIONS=false` or leave the key unset to run them for free.
- When the question's language is not recognised from its function words, the first translation request is made alone and the language Supertext detected is taken from its reply; one request may then have been into the question's own language and is dropped.
- The `translations` argument of `swiss_search` is now an override, not a boost: the tool description says so.
- The reranker cache is keyed per chunk and language as before; within one request the query text per language is fixed, so the cache stays valid.
- The key is shared the way the corpus dump is (ADR 0017): as an asset of the private release, uploaded with `dump publish-key` and written into `.env` by `setup`. It is never committed. Every collaborator can read it, which is the price of one shared key; a dedicated key that is rotated after the evaluation limits the damage of a leak. A relay that keeps the key server-side would need only `SUPERTEXT_BASE_URL` to change.
- Measured with the key on 2026-09-24: translation works for de, fr, it and rm (English must be requested as `en-GB`; bare `en` is refused). Romansh is not a default target: the reranker scored weak Romansh passages 0.95 against the Romansh query and 0.00 against the German question, displacing the right German page. On the golden set, which asks every question in its source's language and so cannot show the cross-language benefit, translation costs two status points: a marginal Italian climate page clears the placeholder threshold for a weather question, and four cantons' licence pages are now found for a placeless deadline question, so the evidence rule asks back. Both are the unfitted abstention threshold, not translation defects; the fitted relevance model (ADR 0012) is the fix.
