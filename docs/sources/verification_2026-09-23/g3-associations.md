# G3 report: commune associations, gaps, city open data (Opus 5.5 agent, 2026-09-23)
Run: 138 tool calls, ~238k tokens, ~43 min. Evidence: /tmp/sg-verify-g3-associations/. The harness blocked the backup,
so this is the main session's transcription.

**Spot-checked by the main session (2026-09-23). All matched:**
- SBB `tarifverbundkarte/exports/json?select=id,name,partners,tarifverbund_urls`: a list of **2,137** rows in one GET (e.g. Mörigen → Libero)
- REAL Luzern ICS (Dietwil, gemid=4): 200 text/calendar, **120 VEVENTs**, "Kehrichtsammlung" (needs `curl -g` for the `[]` params)
- map.bern.ch Abfallsammelquartiere/0: **7 features** with Sammelgebiete_* rule text
- Lausanne WFS `ms:planville_zones_chiens`: numberOfFeatures=**225**
- Code: the `api` fetcher accepts a top-level list when `records_path` is empty (api.py:20-27), and `str.format_map`
  supports `{attributes[X]}` (tested). **So SBB and Bern waste zones work today with YAML only.**
Not re-checked: SIGE, Schöftland, Diessenhofen, SRFWL scans, entsorglos 10 hits, Biel 4,027, Zollikon/Dietikon.

## Summary
| id | can we get it | format | fetcher | value |
|---|---|---|---|---|
| **SBB Tarifverbundkarte** | **Yes today** (api, empty records_path) | ODS JSON export | api + name→BFS join | **high**: every commune → fare networks |
| **REAL Luzern** (22 communes) | New fetcher | ICS per commune + fees in HTML | ICS; fees html_crawl today | **high** |
| **Bern Abfallsammelquartiere** | **Yes today** (api) | ArcGIS JSON | api | **high** |
| Lausanne dog zones (225 + 308 forest) + parking | New fetcher | WFS **GML only** | WFS-GML | med-high |
| entsorglos.swiss (10 Zimmerberg communes) | New fetcher | ICS, no auth | ICS | med |
| D10 Schule Zollikon / D11 Schule Dietikon | Yes today (pdf) + new for lists | i-CMS `data-entities` + PDF text | i-web/i-CMS table | med. **Single-commune schools, not joint bodies** |
| D13 Feuerwehr-ZV Diessenhofen (2 communes) | Yes today (pdf) | govis HTML + PDF text | pdf / govis list | med. **No rate in it; each commune sets it** |
| D12 SRFWL Liestal (7 communes BL+SO) | Partly | WordPress; **2025 Statuten and Verordnung are scanned** | pdf + OCR | med. Liestal exemption tax: 0.4% of income, min 100, max 1000 CHF |
| Water: SIGE Vevey (8–10 communes) | Yes today (one tariff PDF mostly scanned) | PDF | pdf / OCR | med. "CHF 1.75 par m3" |
| Water: AV Schöftland (6 communes) | Yes today | PDF text | pdf | low. Only splits costs between communes |
| Preisüberwacher fee comparison | New fetcher | HTML form POST | – | low (looks outdated: cites VAT 7.6%) |
| D9 z-a-v.ch | No | – | – | low. Forum of 5 ZH incinerator operators, reports only |
| Transport fares (OJP Fare) | No | API key (401) | – | low. **No fare rules found as open data** |
| ZVV zones WFS | Yes | GeoJSON | – | low (no commune names, no prices) |
| Biel parking fields (4,027) | New fetcher | GeoJSON | – | low |
| Lugano, Winterthur | No rule data / already covered | – | – | low |
| Uster fee regulation | New fetcher | i-CMS + PDF | i-CMS | med |
| D27 amicus.ch | No (login) | – | – | low |

## Key findings
- **Fees are almost always set per commune, not by the association** (Diessenhofen fire, SRFWL fire, Schöftland water).
  SIGE and REAL are exceptions: they publish uniform tariffs for all members.
- Waste-calendar vendors: **Sammelkalender** (5 central-Swiss associations, API needs auth), **entsorglos.swiss**
  (`<slug>.entsorglos.swiss/calendar.ics`, open, 10 hits out of 2,686 slugs probed), **anthrazit** (A-Region; ICS for Winterthur/Wetzikon already known).
  There is no single dominant vendor.
- **govis/backslash CMS:** 264 commune homepages contain `public/upload/assets` (AG 69, ZH 46, TG 44…). G1 counted
  "GOViS 254", a similar but differently detected number. Not reconciled.
- **i-CMS/i-web:** G3 counts the same 496 signature as G1.

## Fetcher hints (YAML, work today)
```yaml
# SBB fare networks (needs a name→BFS join for the jurisdiction; 1,909/2,137 names match commune_sites labels exactly)
fetch_strategy: api
fetch_config:
  url: https://data.sbb.ch/api/explore/v2.1/catalog/datasets/tarifverbundkarte/exports/json?select=id,name,partners,tarifverbund_urls
  records_path: ""
  id_field: id
  title_template: "Tarifverbund in {name}"
  text_template: "{name} belongs to fare network(s) {partners}. Details: {tarifverbund_urls}"
---
# Bern waste zones (CH-BE-351)
fetch_strategy: api
fetch_config:
  url: https://map.bern.ch/arcgis/rest/services/Geoportal/Abfallsammelquartiere/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=json
  records_path: features
  id_template: "bern-abfallquartier-{attributes[Objectid]}"
  title_template: "Bern Abfallzone {attributes[Zone_hauskehricht]}"
  text_template: "Kehricht {attributes[Sammelgebiete_hauskehricht]}; Papier {attributes[Sammelgebiete_papier]}; Grüngut {attributes[Sammelgebiete_gruengut]}; {attributes[Sammelgebiete_bereitstellung]}"
```
Caveat on jurisdiction: `api.py` has no per-record extent field (grep "extent" in api.py: no hits). A document's extent is
`source.default_extent_id`, or the result of narrowing from title, headings and text (`enrich.py:42-44`). So the SBB
source would sit on CH and rely on narrowing to find the commune name in "{name}". Whether narrowing resolves all
2,137 names (e.g. "Muri (AG)") is not verified.

## New fetcher classes
1. **ICS calendar** (REAL 22, entsorglos 10, GE school holidays, anthrazit).
2. **i-CMS/i-web publication table** (same as G1 #2).
3. **govis regulation list** (264 homepages).
4. **OCR PDF** (SRFWL 2025, SIGE water tariff).
5. **WFS-GML → records** (Lausanne).
