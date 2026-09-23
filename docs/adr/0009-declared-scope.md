---
status: accepted
date: 2026-09-23
---

# We declare a scope: federal information for all of Switzerland, six cantons, seven municipalities, and live lookups

The evaluators grade answer quality inside the scope each team declares and weigh breadth separately, and they prefer a narrow, high-quality server to a broad, weak one; questions arrive in German, French, Italian and Romansh, and questions outside the declaration must be answered with a clear "not covered". Our earlier plan encoded legal text broadly (all of Fedlex, twenty-six cantons' law), which serves one of the sixteen topic areas the evaluators draw from. We declared instead: **federal** information for all of Switzerland (core Fedlex acts in DE/FR/IT/EN, the federal offices behind health insurance, law, permits, pensions, unemployment, housing, voting and customs, and ch.ch); **cantonal** administration for Zurich, Bern, Vaud, Geneva, Ticino and Graubünden, which between them cover all four national languages; **municipal** services for Zürich, Bern, Lausanne, Genève, Lugano, Chur and Scuol; and **live lookups** for health insurance premiums, public transport connections, the reference interest rate, school holidays and waste collection in those municipalities. Everything else receives an explicit outside-scope answer.

## Considered Options

- Broad legal corpus (all Fedlex, 26 cantons' law): answers one topic area in sixteen, and the practical questions not at all.
- One canton only: highest quality, but no French, Italian or Romansh municipal content, which the sample questions require.

## Consequences

- The scope is published in the README and quoted by the server itself, so an outside-scope answer can say exactly what is covered.
- Cantonal law for the other twenty cantons (ADR 0008) moves to a lower priority tier; it widens breadth once the declared scope is answered well.
- Questions that are tables or live data (premiums, connections, rates, holiday and collection dates) are answered by lookup tools, not by retrieval over embedded text.
