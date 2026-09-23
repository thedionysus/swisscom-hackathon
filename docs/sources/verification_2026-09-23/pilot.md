# Pilot report: U12, C1, U8, D8 (Sonnet 5 agent, 2026-09-23)

Run: 58 tool calls, ~129k tokens, ~27 minutes. Scratch evidence: /tmp/sg-verify-pilot/.

**Spot-checked by the main session (live curl, 2026-09-23). All four checks matched the agent's claims:**
- U12 PDF: `200 application/pdf 121636B`
- ville-fribourg.ch/reglements-tarifs/410-2: `200`, contains "impôt sur les chiens est fixé à 120 francs par an et par animal"
- zstb-172-1.html: `200 text/html 122694B`
- daten.sg.ch ZAB dataset: `nhits 1116`. Fields: standort_typ, status, standort_code, ort_code, kanton,
  rubriken_abfallcode, ort_name, standort_name, ort, plz, x/y_koordinate, standort[lat,lon]
Not re-checked: C1 fr.ch guidance page, the ZAB PDFs and member counts, the zh.ch sitemap contents, the Bern /fr/ sibling.

## Summary
| id | can we get it | format | strategy / new fetcher | value |
|---|---|---|---|---|
| U12 BE school holidays | Yes today | PDF text (2 pages) | pdf, fixed URL (+ French sibling for Jura bernois) | high |
| C1 FR commune bylaws | Partly: per commune, no cantonal index | server HTML | html_crawl per commune + new "commune-site enumerator" | high |
| U8 ZH Steuerbuch | Partly: content yes, discovery no | server HTML per entry (`zstb-<nr>.html`) | new: search- or probe-seeded crawler | medium |
| D8 ZAB waste association | Yes today | PDF text (35 per-commune agendas) + JSON (ODS) | pdf fixed list + api. Paginated JSON needed for all 1116 records | high |

## Key findings
- **U12:** a 6-year Ferienordnung (2026/27–2031/32) for the **German-speaking part of BE only**. Jura bernois has
  its own French calendar. Sample: "Sommerferien Sa, 04.07.2026 - So, 09.08.2026". No Bern open-data dataset
  found on opendata.swiss. **BS and BL publish Schulferien as open data** (BL covers 2026/27–2031/32).
- **C1: the AI's claim was wrong.** The fr.ch page is guidance (Info'GemA 23/2021) on how communes number their
  bylaws, not an index. But Art. 42b ARGG **requires FR communes to publish their bylaws online**, and the
  numbering scheme is in live use: ville-fribourg.ch/reglements-tarifs/<code> (e.g. 410-2 dog tax, 120 CHF/year).
  cressier.ch and saint-martin-fr.ch appear to use the same pattern (WebSearch only, not curl-verified).
  bdlf.fr.ch (FR cantonal law) is a LexWork JS shell. Its API was not probed (handoff lead 1).
- **U8:** the landing page is thin. Entries are at `.../steuerbuch/steuerbuch-definition/zstb-<nr>.html`
  (≥16 found via WebSearch). The zh.ch sitemap (`/bin/zhweb/publish/sitemap.xml`) contains **no** zstb URLs.
  Weisungen/Merkblätter → official_info, taxes.
- **D8:** 33 communes (self-stated) or 35 (PDF list) across **SG + TG**. Per-commune "Abfall-Agenda 2026" PDFs
  with text layers. The Organisationsreglement is in the SG Gesetzessammlung (publikationen.sg.ch/…/258), in force since 2000.
  **No fee schedule found.** Collection points are on daten.sg.ch (ODS API, 1116 records).
  Authority edge case: an SG-published statute that also binds TG communes.

## New fetcher classes the pilot points to
1. **Commune-site enumerator.** Walks `docs/sources/commune_sites.csv` (2,110 rows: extent_id, bfs, canton,
   website) and applies a per-commune html_crawl path (e.g. `/reglements-tarifs`, `/reglements-communaux`).
2. **PDF index discoverer.** Reads an index page (zab.ch/sammelstellen/) and collects the yearly PDF links.
3. **Paginated JSON.** Opendatasoft `rows`/`start` or `offset` (issue #38).
4. **Seeded crawler.** Seeds from search results or numeric probing when there is no index or sitemap (ZH Steuerbuch).

## Agent's feedback on the brief (condensed)
- The ladder worked: 3 of 4 leads only became useful at step 3 (WebSearch) or step 6 (one hop).
- Unclear how many hops are allowed. It went 2 hops on D8, and that paid off.
- WebFetch undercounted lists. Never report a count from WebFetch alone.
- 8 minutes per lead is unrealistic for high-value multi-hop leads. It wants a concrete ceiling (~20 min).
- Unclear whether "Partly" leads need a ladder log.
- Add portal-API probing as a named step: Opendatasoft and CKAN `package_search` worked generically.
