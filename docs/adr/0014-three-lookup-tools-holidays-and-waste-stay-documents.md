---
status: accepted
date: 2026-09-23
amends: 0009-declared-scope
---

# Three lookup tools; school holidays and waste collection stay indexed documents

ADR 0009 declared live lookups for premiums, connections, the reference interest rate, school holidays and waste collection. Only three of these have one official source that covers the whole declared scope:

- **`swiss_premium`**: the BAG premium table (yearly CSV/XLSX on opendata.swiss) and its premium regions, shipped in the database dump. Input: municipality, age, deductible, insurance model and accident cover. Output: the cheapest premiums with premium region, year and source URL.
- **`swiss_connections`**: live call to transport.opendata.ch `/v1/connections`, keyless. A timeout or error returns `source_unavailable`.
- **`swiss_reference_rate`**: fetches the BWO reference-rate page live and returns the rate with its effective date. When BWO is unreachable it returns the stored value, that value's date and `source_unavailable` (ADR 0013, step 4).

School holidays and waste collection have no common official feed: each canton or city publishes its own page, PDF or dataset. They are answered by retrieval over those indexed documents, each carrying its reference date. The existing Zürich OpenERZ calendar stays as calendar evidence.

## Considered Options

- A dedicated tool per city for holidays and waste: six or seven separate integrations for two days of hackathon work, with little gain over retrieval.
- Community or commercial holiday APIs (feiertagskalender.ch, OpenHolidays): one integration, but not official sources, which the challenge requires.
- opentransportdata.swiss instead of transport.opendata.ch: more official, but it needs a registration key, which works against keyless serving (ADR 0006).

## Consequences

- The encoding manifest must include the official holiday and waste pages of every declared canton and city, including Scuol's school calendar and ge.ch's school holidays. This is checked against the encoded corpus.
- The premium table is loaded by `setup` along with the rest of the dump and reloaded once a year.
