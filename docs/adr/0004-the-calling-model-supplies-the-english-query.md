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
- The verbatim question is kept alongside the English one and is what the keyword arm is searched for. This was justified at the time by original-language matching; see the measurement below, which shows the keyword index cannot do that.
- Probes stay deterministic, because a probe author writes the English fields by hand rather than having a model produce them. All existing probe files gain those fields.
- The local topic classifier remains, as the fallback for a caller that supplies no topic.

## Measured, 2026-09-23: the keyword index is English-only

Recorded here because it is a fact about the index rather than about this decision, and because it is expensive to re-derive. Whatever replaces the language handling will need it.

This ADR asserted that the verbatim question is kept "so that original-language terms still have something to match against in the keyword index". Nobody had measured that, and it is false.

`db/schema.sql` builds `tsv` from `context_en || ' ' || text_en`. `text_original`, `title_original` and `identifier` are all absent from it, so the keyword index holds translated English text and nothing else, and `websearch_to_tsquery('english', ...)` applies English stemming and stopwords to whatever it is handed. Measured against the live index — 719 chunks over 108 documents, 89 of which come from sources that already publish in English:

| query | chunks | English equivalent |
|---|---|---|
| `Leinenpflicht` | 0 | `leash` → 4 |
| `Hund` / `Hunde` | 0 / 0 | `dog` → 7 |
| `Abfall` | 0 | `waste` → 65 |
| `Grüngutabfuhr` | 0 | — |
| `Gemeinde` | 0 | `commune` → 5 |
| `Kreis` | 0 | — |
| `SR 455` | 0 | `455` → 0 |
| `Zürich` | 2 | `Zurich` → 89 |
| `Graubünden` | 6 | `Graubunden` → 0 |

Three findings:

1. **German vocabulary contributes nothing.** The one apparent counter-example, `Wanderwege` at 6 chunks, is an untranslated proper noun sitting inside English text ("Registration: Wanderwege Graubünden"). It confirms the rule rather than breaking it: names survive translation, words do not. Legal identifiers do not survive either, since `identifier` never reaches `tsv`.
2. **There is no `unaccent`, and it cuts both ways.** An accented form and its plain form are different lexemes. `Zürich` reaches 2 chunks where `Zurich` reaches 89; `Graubunden` reaches 0 where `Graubünden` reaches 6. Which spelling wins depends on which one the English text happens to use, so neither is safe to rely on — this is a defect in the index, not in any particular query.
3. **Whole sentences rarely match in any language.** `websearch_to_tsquery` requires every term. `Darf mein Hund im Wald frei laufen?` returns 0 chunks, and so does `May my dog run off leash in the forest?`. The lexical arm is driven by distinctive terms, not by sentences.

Sending the verbatim question to the lexical arm costs nothing and place and organisation names do reach it, so it stays. But it is not buying original-language matching, and the `swiss_search` description no longer implies it is. Any future design that expects the keyword arm to serve non-English input has to change `tsv` first — adding `text_original`, an `unaccent` dictionary, or per-language configurations — and none of that is done today.
