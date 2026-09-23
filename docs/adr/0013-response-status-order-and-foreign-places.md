---
status: accepted
date: 2026-09-23
---

# Response statuses are decided in a fixed order; a place that is not Swiss sends the client elsewhere; asking back depends on the results

The challenge grades four failure answers differently: not covered, missing context, source unavailable, and no match. It counts asking back as wrong when the missing fact would not change the answer. `swiss_search` decides in this order:

1. **The place is not in Switzerland** → `outside_scope`. The response says the location is not in Switzerland and tells the calling model to look for the answer outside this server. We keep no list of foreign places. Detection uses only what we have: a country other than Switzerland named in the question or the location argument, or a named place that the Swiss commune register cannot resolve. In the second case the message also says that a misspelled Swiss place should be retried. If a name resolves to a Swiss commune that shares its name with a foreign town (Lindau ZH, Rheinfelden AG), the answer stays Swiss and names the Swiss commune it used, so the calling model can correct the user.
2. **No place given** → search first. Return `needs_location` when no federal passage answers the question, so the relevant evidence is cantonal or municipal. This applies even when only one place's documents matched (amended 2026-09-23 after plan review: otherwise a placeless "Karton" question would be answered from the only city with a calendar). A national question is answered without asking.
3. **A Swiss place outside the declared scope** → return the federal evidence with the coverage signal (ADR 0001), plus `outside_scope` for the cantonal and municipal part. Never answer from another place's rules.
4. **A live lookup fails** → `source_unavailable`, with the date of the last good value when one is stored.
5. **The top relevance score is below the abstention threshold** (ADR 0012) → `no_evidence`.

## Considered Options

- A curated list of places in neighbouring countries: catches Konstanz and Lindau (DE) before the Swiss resolver. Rejected because the list can never be complete, and the calling model is better placed to judge where the user is.
- Deciding up front whether a question is local, by topic: brittle. Letting the candidates decide asks back only when the place changes the answer.

## Consequences

- The Swiss resolver must report "unresolved place" separately from "no place given". Today both collapse into `needs_location`.
- The tool description tells clients to pass the country when the user names one ("Konstanz, Deutschland").
- In a question with no place argument, a country name counts only as the place of the question ("in Deutschland", "en France"). "Permis étranger" or "Umzug ins Ausland" are Swiss federal topics, not foreign places.
- A foreign town that shares its name with a Swiss commune and appears with no country is answered as Swiss. The response names the commune so the calling model can correct it.
