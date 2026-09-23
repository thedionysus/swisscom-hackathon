# G2 report: districts, courts, regional planning, geodata (Opus 5.5 agent, 2026-09-23)
Run: 116 tool calls, ~202k tokens, ~34 min. Evidence: /tmp/sg-verify-g2-districts/. The harness blocked the
agent's own backup file, so this is the main session's transcription of its hand-back.

**Spot-checked by the main session (live curl, 2026-09-23). All matched:**
- einsiedeln.ch/verwaltung/rechtssammlung: 200, 156 KB, **215 unique sre_*.pdf**
- kuessnacht.ch/politik/rechtssammlung.html/436: 200, 76 KB, **72 unique /public/upload/assets/*.pdf**
- api.geobasisdaten.ch/api/v1/corp/: **79 corps** (first = Bund)
- agvchapp.bfs.admin.ch/api/communes/snapshot?date=01-01-2026: CSV header HistoricalCode,BfsCode,…,Level,Parent,Name
- repo src/swiss_grounding/locations/data/communes.csv header: `bfs_id,name,canton,district,postal_codes`
Not re-checked: ÖREB extracts, geodienste OGC features and `dokument` links, gerichte-zh sitemap counts, RSTA sitemap, WP media APIs, Gersau.

## Summary
| id | can we get it | format | strategy / new fetcher | value |
|---|---|---|---|---|
| D4 Bezirk Küssnacht (CH-SZ-1331) | Yes | HTML index + 72 PDFs (text) | pdf / PDF index discoverer | high |
| D4b Einsiedeln (CH-SZ-1301) | Yes | HTML + 215 PDFs (text) | PDF index discoverer | high |
| D4b Gersau (CH-SZ-1311) | Yes | OneGov HTML + 22 PDFs | pdf / PDF index discoverer | med |
| D5 Bezirk Höfe (3 communes) | Yes (new) | WordPress media JSON + PDF | WP media API | low |
| D4b Bezirk Schwyz (15 communes) | Yes (new) | WordPress media JSON | WP media API | low |
| D4b March | Partly | JS (i-web CMS) | unresolved | low |
| D6 BE Regierungsstatthalterämter | Yes | server HTML (AEM), 66 sitemap URLs | html_crawl (Crawl-delay 10) | med |
| D7 gerichte-zh.ch | Yes | server HTML (Drupal), 249 /de/themen/ pages | html_crawl | med-high |
| R1 Planungsgruppe Pfannenstil (zpp.ch) + all 11 ZH regional Richtpläne | Yes | PDF text | pdf | low |
| R2 Region Oberaargau (oberaargau.ch) | Yes | Wix + PDF | pdf | low |
| geobasisdaten.ch | Yes (new) | JSON API + XLSX | list+detail fetcher | med |
| geodienste.ch | Yes (new) | OGC API Features JSON | legal-document harvester | **high** |
| ÖREB-Kataster | Yes (new) | JSON/XML extract | legal-provision harvester | **high** |
| C6/C7 resolvers | Yes | CSV | resolver data | med |

## Key findings
- **Schwyz districts are autonomous** (GOG SZ §1 Abs. 2 applies the commune rules to districts). District law is **not** in the
  cantonal SRSZ. Küssnacht, Einsiedeln and Gersau are single-commune districts, so their law is effectively commune law
  (municipal_law, one node). Küssnacht covers waste + fees, parking, building, cemetery, wastewater. Einsiedeln covers a Gebührenordnung,
  an Abfallreglement and parking. Gersau's Hundesteuer: "für einen anderen Hund Fr. 100.00".
- **BE RSTA:** guidance only (appeals against communal decisions, hospitality, inheritance). No published decisions.
- **gerichte-zh.ch:** resident guidance on court costs, family, employment and debt enforcement. The District Court GO is a PDF. The fee ordinance is not hosted there.
- **The AI got both regional-planning domains wrong** (zpp.ch, oberaargau.ch). Regional plans are low value for resident questions.
- **ÖREB (best find):** every canton runs the standard ÖREB web service (`getegrid/json?EN=x,y` → `extract/json?EGRID=`).
  Each extract lists **LegalProvisions with links to the commune's binding Baureglement PDF and the responsible office**.
  SZ sample: Küssnacht Baureglement at oereblex.sz.ch/api/attachments/1800 (53 pages, OCR-quality text). ZH: oerebdocs.zh.ch/getDoc?docid=N.
  The JSON shape differs per implementation. ogd_lists_assessment §7 dismissed ÖREB as parcel-level: right for geometry, wrong for these document links.
- **geodienste.ch:** 42 topics. The Nutzungsplanung OGC API (`/db/<topic_version>/deu/ogcapi/collections/<coll>/items?f=json&crs=…2056`,
  which returns 403 without `crs`) has a `dokument` field with **Rechtsvorschrift links to communal building regulations** (BE sample: Stadt Bern,
  Ostermundigen, Meikirch). Free in about 20 cantons. **ZH, TI and GL are not ready; NW, OW and VD need approval.** No dog zones.
- **geobasisdaten.ch:** API `api.geobasisdaten.ch/api/v1` (corp/, legislative-entry/?legislative_corp=, detail, export-xlsx).
  Maps topic → legal basis (law code + URL) → responsible authority for 25 cantons (**SZ missing**).
- **Resolvers:** the BFS snapshot API gives commune→district (144 districts). The swisstopo PLZ CSV has no district.
  **The repo's communes.csv already has a district column.**

## New fetcher classes
1. **PDF index discoverer** (Küssnacht, Einsiedeln, Gersau, regional plans). Also requested by the pilot and G5.
2. **WordPress media API** (`wp-json/wp/v2/media?mime_type=application/pdf&search=…&per_page=100`, paginated). Covers any WP commune.
3. **ÖREB legal-provision harvester** (one sample point per commune → extract → distinct LegalProvisions → PDFs). Covers communal building rules nationwide.
4. **OGC API Features legal-document harvester** (geodienste; overlaps #3).
5. **geobasisdaten list+detail JSON / XLSX reader.**
