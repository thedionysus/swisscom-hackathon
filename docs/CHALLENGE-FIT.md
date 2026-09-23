# Challenge fit: our plan against the published challenge requirements

Checked 2026-09-23 against `Swiss-ai-Weeks/swisscom-2026/swiss-grounding-mcp/README.md` (Q&A answers of 2026-09-21, 16 topic areas, 5 sample questions) and the eight practice cases and review checklist in the submission self-check pack (commit `0fc28ee`). The plan it is compared with is grill #1 so far: ADRs 0006–0008 and the decisions recorded in `CONTEXT.md` on the same date.

## What the evaluators actually do

- **Hackathon dates: 24 and 25 September 2026.** "Tomorrow's encoding run" is day 1; the demo is day 2.
- **Declared scope decides what is graded.** We state topics and geography; answer quality is judged inside that declaration, breadth separately. "A high quality solution with narrow coverage is preferred over a broad solution with low quality."
- **Order of importance:** correct and honest answers → breadth → agent efficiency, operability, MCP contract quality (tie breakers).
- **Questions in German, French, Italian and Romansh.**
- **Two unknown MCP clients × two unknown LLMs.** Nothing can depend on one client following our tool description well.
- **Asking back is correct only when the missing fact changes the answer.** Asking for context that isn't needed counts as wrong.
- **Outside-scope questions must get a clear "not covered", never a guess.**
- **Operability:** a server that runs with no external keys is rated better; a prebuilt index is allowed if setup downloads it with no manual step and the build script is in the repo; robots.txt / terms-of-use compliance must be a documented configuration switch, on by default.

## The five sample questions against our plan

| # | Question | What a correct answer needs | Our plan today |
|---|---|---|---|
| 1 | *Wann wird bei uns das nächste Mal Karton abgeholt?* | Ask for the municipality (and street/zone only if the calendar needs it), then the next date from that municipality's calendar | Asking back works (`needs_location`). After that, only Zurich Kreis 3 has a calendar; every other municipality: nothing. |
| 2 | *Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?* | Vaud road traffic office page (procedure) + the 12-month deadline (federal ordinance VZV, cantonal page) | Federal law yes (if VZV SR 741.51 is in the Fedlex list); **no cantonal administration pages** (vd.ch is not in the plan; only cantonal *law*). |
| 3 | *Premio mensile più basso, adulto 30 anni, Lugano, franchigia 2500?* | A lookup over the BAG premium dataset (priminfo) for premium region, age band, franchise, then the minimum | **Impossible.** It is a computation over a table, not text retrieval. CSV/XLSX is deferred; no structured tool exists. |
| 4 | *Cura èn las vacanzas d'atun 2026 per la scola da Scuol?* (Romansh) | Understand Romansh, resolve Scuol (GR), find the 2026 school calendar of Scuol's school | **Impossible.** Romansh is not searched; no school-holiday data. |
| 5 | *Rundfunkbeitrag nach meinem Umzug nach Konstanz?* | Recognise Konstanz is in Germany; say it is outside coverage; do not give the Swiss Serafe fee | **Wrong behaviour.** The resolver returns "no Swiss location matched" → `needs_location` → the client asks the user for a place, which counts as wrong. |

## The eight practice cases

| Case | Pass needs | Our plan |
|---|---|---|
| missing_location (Karton) | ask municipality, no invented date | ✓ asks; ✗ no calendars beyond Kreis 3 |
| enough_context (Geneva school holidays 2026) | don't ask; cite ge.ch 2026 calendar | ✗ no ge.ch education content; question-scan may resolve "ville de Genève" oddly (audit §3.3) |
| cross_border (Konstanz) | say Germany, out of scope | ✗ asks back (above) |
| romansh_locality (Scuol) | identify Scuol, 2026, local calendar | ✗ no Romansh, no school calendars |
| rate_freshness (reference interest rate) | current BWO publication + effective date | ✗ bwo.admin.ch not in plan; no effective-date field for pages |
| paired_jurisdiction (Lausanne and Bern registration) | two independent municipal answers | ✗ no lausanne.ch / bern.ch residents'-office pages in the priority tier; `swiss_search` takes one location and a two-place question resolves to nothing |
| citation_support ("which source proves that deadline?") | return the exact supporting passage | ~ we return a 600-char snippet from the *start* of the chunk, not the passage that supports the claim |
| source_failure | distinguish "source down" from "fact absent", disclose cached date | ✗ `retrieved_at` means "last seen"; no live-source failure status |

Review checklist items we do not meet yet: responsible-publisher check beyond domain, reference year / effective date on non-law sources, "outside scope vs insufficient context vs source unavailable vs no match" as four distinct statuses, reproducible setup with downloadable prebuilt index, configurable robots/ToS switch.

## Verdict

The plan's **foundation is right**: jurisdiction as a hard filter, multilingual stores without document translation, cited passages, honest coverage signals, and a cost-capped encoding pipeline. Its **content focus is wrong for this evaluation**. It is built around *legal texts* (all of Fedlex, 26 cantons' law), which serves one of the sixteen topic areas ("law and regulations"). The evaluators' questions are mostly practical administrative questions answered by federal-office, cantonal-administration and municipal-service pages, plus a set that only structured or live data can answer (premiums, next train, company register, reference rate, holidays, waste dates, population).

## 1. Missing data resources

| Topic area (their #) | Authoritative source | Kind | In plan? |
|---|---|---|---|
| Health insurance premiums (1) | BAG premium dataset (priminfo; yearly CSV/XLSX on opendata.swiss) | structured table | no |
| Taxes (2) | cantonal tax administrations (ti.ch, …), ESTV | pages + tax tables / calculators | no |
| Law (3) | Fedlex | XML | yes |
| Waste (4) | municipal calendars (Lausanne, Bern, Basel open data, OpenERZ 22 regions) | live API / ICS / tables | Kreis 3 only |
| Moving / registration (5) | municipal residents' offices (bern.ch, lausanne.ch, …), ch.ch | pages | ch.ch only |
| Permits / migration (6) | sem.admin.ch, cantonal migration offices | pages | no |
| AHV / pensions (7) | ahv-iv.ch (leaflets, often PDF) | pages + PDF | no |
| Work / unemployment (8) | arbeit.swiss (SECO) | pages | no |
| School holidays (9) | cantonal education departments, municipal schools (ge.ch, Scuol, Bern) | pages, PDF, tables | no |
| Public transport (10) | opentransportdata.swiss / transport.opendata.ch | live API | no |
| Driving licences (11) | cantonal road traffic offices (gr.ch, vd.ch, …) | pages | no |
| Housing / reference rate (12) | bwo.admin.ch | page, changes quarterly | no |
| Voting (13) | bk.admin.ch (votes calendar) | pages / open data | no |
| Companies (14) | zefix.ch (REST), ESTV UID register | live API | no |
| Customs (15) | bazg.admin.ch | pages | no |
| Statistics / geo / weather (16) | BFS, opendata.swiss, geo.admin.ch, MeteoSwiss | live API / datasets | GeoAdmin for location only |

## 2. Where the pipeline cannot handle the questions

1. **No structured or live answers.** Premiums, next connection, company lookup, current reference rate, holiday dates and waste dates are rows in a table or an API response, not paragraphs. Embedding them as text is either impossible (premium table: millions of rows) or immediately stale.
2. **Out-of-Switzerland is treated as "ask for a location".** Wrong under the rubric. Foreign places that share a name with a Swiss commune (Lindau, Rheinfelden, Freiburg) are silently answered as Swiss.
3. **Location is required for every question,** including purely federal ones ("what does the law say about notice periods?"). Asking back there counts as wrong.
4. **Romansh is not searchable,** and the query protocol relies on the client translating into English — two unknown clients and models will not do that reliably.
5. **Query-time dependency on an OpenAI key** (ADR 0006: the primary index needs OpenAI to embed each question). Legal but hurts operability, and Swisscom must be given a working key.
6. **One location per search;** two-place questions resolve to nothing.
7. **Citations quote the chunk start,** not the supporting passage; no effective date on non-law pages; `retrieved_at` is "last seen".
8. **Four failure states collapse into two** (`needs_location`, `no_evidence`); the rubric wants outside-scope, missing-context, source-unavailable and no-match told apart.
9. **robots.txt compliance is hard-coded** in the crawler and ignored in the API fetcher; the rubric wants a documented switch.
10. **Setup is not reproducible from the repo alone:** the database is local Docker with no downloadable prebuilt dump.

## 3. What to change

**A. Declare a scope that we can answer with high quality,** shaped by their sixteen areas, not by what is easiest to crawl. Proposal: *federal information for all of Switzerland* (Fedlex core acts; the federal offices behind areas 1, 3, 6, 7, 8, 12, 13, 15; ch.ch) + *cantonal administration for a named set of cantons* + *municipal services for a named set of cities* + *live data tools* for premiums, transport, reference rate, school holidays and waste where an official feed exists.

**B. Rebalance the corpus.** Keep Fedlex, but limited to the most-asked acts in DE/FR/IT/EN (OR, ZGB, SVG/VZV, AIG, AHVG, KVG, AVIG, MWSTG, …) rather than every act; defer the 26-canton law corpus (ADR 0008 stays valid but drops a tier). Add the federal-office sites, the named cantons' administration sites and the named cities' service pages, in every language they publish. PDF + OCR stays (AHV leaflets, school calendars).

**C. Add structured and live tools next to `swiss_search`,** each returning the record, its official source URL and its reference date: premium lookup (BAG dataset, shipped as a table), public transport connections, company register, current reference rate, school holidays and waste collection (per covered municipality). These answer by lookup, not by retrieval.

**D. Fix the honesty contract:** an explicit `outside_scope` status (outside Switzerland, or outside declared topics/geography) distinct from `needs_location`, `source_unavailable` and `no_evidence`; foreign-place detection before Swiss resolution; location optional when the question is national; a declared-scope document that the server itself can quote.

**E. Make it run without keys and install itself:** serve queries on the local bge-m3 index by default (OpenAI index used only when a key is configured), accept questions in any of the four languages and search all language stores directly with the multilingual model — client-supplied translations become an optional boost, not a requirement; ship a prebuilt database dump that `setup` downloads automatically; robots/ToS as a configuration switch, on by default.

**F. Citations the reviewers can check:** return the passage that supports the claim, the responsible publisher, the jurisdiction, and the effective or reference date; `retrieved_at` means when the text was fetched.

## Decisions to revisit

- **ADR 0006** (OpenAI `halfvec(3072)` as primary): encoding stays as decided, but *serving* should default to bge-m3 so the server runs without keys; OpenAI becomes the optional higher-quality path.
- **ADR 0007** (twenty topics): covers fifteen of their sixteen areas; statistics, geodata and weather have no topic.
- **ADR 0008** (cantonal law for 26 cantons): valid, but moves down a priority tier.
- **Source scope and priority tiers** from grill #1: replaced by the scope declaration in A.
