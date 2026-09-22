# What the two rnckp lists give Swiss Grounding

Assessed 2026-09-22 against the pipeline at `ec2d7ed` (fetch strategies: `fedlex_sparql`,
`html_crawl`, `api`, `pdf`; categories: hiking, waste, dogs, taxes, housing, transport, parking,
schools, health, safety). Every claim below was checked with a live request on that date unless
marked *inferred* or *unverified*. Commands are in the appendix so anyone can re-run them.

Repository facts (GitHub API, 2026-09-22): 177 stars, 18 forks, created 2022-11-13, last push
2026-09-16, no open issues; maintained by one person (rnckp / Patrick Arnecke, 190 of ~205 commits)
with a handful of contributors. The maintainer also publishes `opencaselaw-client` (MIT, a Python
client for the opencaselaw REST API), `entscheidsuche-client`, `onlinekommentar-client` and
starter-code generators for opendata.swiss CSVs.

Lists:
- `rnckp/awesome-ogd-switzerland` (CC0, 320 links, last commit 2026-09-16) — open government
  *data*: statistics, geodata, APIs, linked data.
- `rnckp/awesome-open-legal-switzerland` (same author, 114 links, last commit 2026-08-17) — open
  *legal* data: legislation, courts, soft law, MCP servers. **This is the list that maps onto the
  project; the OGD list pointed to it.**

## 1. Verdict

About ninety percent of the OGD list is statistical tables and geodata the pipeline cannot ingest
and a citizen question cannot cite. The remaining ten percent contains the cheapest coverage wins
left before the deadline (calendar feeds, YAML only, no LLM cost) and the only practical route to
cantonal law (an API, because the cantonal law portals are JavaScript apps the crawler cannot read).

## 2. Ingestible now, YAML only, through the `api` strategy

Constraints of the strategy (`ingest/fetchers/api.py`): one request per source, no pagination, so
at most 100 records per YAML; `{start}` and `{today}` placeholders in the URL; `records_path`,
`id_template`, `title_template`, `text_template`, `event_date_field`; `llm_tagging: false` with
English templates means zero translation cost. Use a date filter in the URL to stay under 100.

### 2.1 OpenERZ waste calendars — `https://openerz.metaodi.ch/api/calendar`

Already used for Zurich 8003 (`registry/sources/open_erz.yaml`). The same feed serves 23 more
regions. Upcoming rows from 2026-09-22 (`?region=<r>&start=2026-09-22`):

| region | upcoming | filter key | note |
|---|---|---|---|
| zurich | 1407 | zip | in use for 8003 |
| winterthur | 521 | zip 8400 works (521) | area 1..n |
| basel | 470 | **area a–h, guf**; zip empty | data is data.bs.ch dataset 100096 (see 2.2) |
| duebendorf | 213 | zip 8600 | area 1 |
| uster | 161 | zip 8610 works (161) | |
| horgen | 158 | zip 8810 works (158) | area b |
| wetzikon | 151 | zip 8620 | area 1 |
| waedenswil | 138 | zip 8820 | area b |
| thalwil | 110 | zip 8800 works (110) | area b |
| embrach | 102 | zip 8424 | area ost |
| rueschlikon | 79 | zip 8803 | area a |
| richterswil | 75 | zip 8805 | area a |
| gossau-zh | 71 | zip 8625 | area aussenwachten |
| kilchberg | 69 | zip 8802 | |
| adliswil | 60 | zip 8134 works (60) | |
| bassersdorf | 60 | zip 8303 | |
| wiesendangen | 57 | zip 8542 | |
| wangen-bruttisellen | 50 | zip 8306 | |
| hombrechtikon | 44 | zip 8634 | |
| oberrieden | 43 | zip 8942 | |
| langnau | 41 | zip 8135 | |
| seon | 32 | no zip | canton AG |
| stgallen | **0** | — | stale; use the city's own dataset (2.2) |
| zimmerberg | error | — | |

Waste types seen: waste, organic, paper, cardboard, metal, bulky_goods, incombustibles,
chipping_service. Extent: the commune node (`CH-<canton>-<BFS>`); only Zurich has neighbourhood
nodes. For area-based regions put the area letter in the text template; a user cannot be resolved
to an area, so the answer will list the area's dates.

Provenance per region (`csv/README.md` and the loaders in the OpenERZ repo, read 2026-09-22):

| regions | how OpenERZ gets the data | licence to record |
|---|---|---|
| zurich, basel, stgallen | the city's open-data portal (data.stadt-zuerich.ch, data.bs.ch 100096, daten.stadt.sg.ch) | CC0 (Zurich), CC BY 4.0 (Basel), CC BY (St. Gallen) |
| adliswil, horgen, kilchberg, langnau, oberrieden, richterswil, rueschlikon, thalwil, waedenswil | one shared municipal web application for the district of Horgen (`zimmerberg.py`) | none stated; municipal website |
| winterthur, wetzikon | municipal ICS calendars (Antrahzit) | none stated |
| duebendorf, uster | municipal ICS files; Uster partly hand-checked for holidays | none stated |
| bassersdorf, embrach, hombrechtikon, wangen-bruttisellen, wiesendangen | **hand-transcribed** from the municipal website into a config file (weekly rules plus exceptions) | none stated; secondary source |
| seon, gossau-zh | municipal website | none stated |

OpenERZ itself publishes no data licence (no LICENSE file on `main`). For the three portal-backed
cities the licence is the portal's. For the rest, cite the municipal page named in the README as the
source and mark the OpenERZ row `institutional`, not `official_info`, since the dates were typed in
by a volunteer. The hand-transcribed regions are the ones most likely to drift.

### 2.2 Opendatasoft portals (cantons and cities)

These portals expose every dataset as JSON at
`https://<host>/api/explore/v2.1/catalog/datasets/<id>/records?where=<field>>=date'{start}'&order_by=<field>&limit=100`
with `records_path: results`. Verified datasets that fit a category:

| dataset | host / id | records | fields | licence |
|---|---|---|---|---|
| Abfuhrtermine (waste, Basel-Stadt) | data.bs.ch / 100096 | 470 upcoming | termin, art, wochentag, zone (A–H, GUF) | CC BY 4.0 |
| Schulferien Kanton Basel-Stadt | data.bs.ch / 100397 | 88 | year, name, start_date, end_date | CC BY 4.0 |
| Schulferien Kanton Basel-Landschaft | data.bl.ch / 13350 | 58 (2026/27–2031/32) | schuljahr, name, startdatum, enddatum | CC BY (portal terms) |
| Abfuhrdaten Stadt St.Gallen | daten.stadt.sg.ch / abfuhrdaten-stadt-stgallen | 72,826 upcoming (per street) | gemeinde, abfuhrgebiet, datum, sammlung, zeit, strasse, titel | CC BY (portal) |
| Schulferien und Feiertage Stadt St.Gallen | daten.stadt.sg.ch / schulferien-feiertage-stadt-stgallen | 30, **stale: last row 2025-07** | betreff, beginnt_am, endet_am | CC BY |
| Ferien und schulfreie Tage, Stadt Zürich | data.stadt-zuerich.ch, CKAN datastore resource `aad477f6-…` | 296, maintained to 2030-07 | start_date, end_date, summary | CC0 |

Zurich's holidays are JSON through the CKAN datastore:
`https://data.stadt-zuerich.ch/api/3/action/datastore_search_sql?sql=SELECT * FROM "aad477f6-db39-4d1b-92d8-0885f2d363d1" WHERE start_date >= '{start}'`
with `records_path: result.records`. St. Gallen is per street: filter by `abfuhrgebiet` (e.g. `where=abfuhrgebiet='L Ost' and datum>=date'{start}'`)
or by `sammlung` to stay under 100 rows, and name the area in the template.

Not ingestible although related: Basel *Hundesignalisation* (data.bs.ch 100023; 226 dog bans, 74
leash zones, 10+6 free-run areas) has coordinates but **no place names**, so a record cannot be
cited in prose without a reverse-geocoding join. Bern *Leinenpflicht für Hunde* is WMS/WFS geodata
only. Basel *Ordnungsbussen* (100058) is 2.05 million individual fines, statistics not a tariff.

### 2.3 OpenHolidays API — `https://openholidaysapi.org/PublicHolidays?countryIsoCode=CH&subdivisionCode=CH-<canton>&validFrom={start}&validTo=...`

Public holidays per canton with `startDate`/`endDate`/`name`; returned two for canton Zurich for
the rest of 2026. Category `schools` (holidays) or a calendar note. Extent: the canton node.

### 2.4 Geodata that carries rule text — GeoJSON through WFS or ArcGIS REST

I first dismissed all geodata. Wrong: several city layers carry a place name, the rule and the
legal basis as attributes, and every WFS / ArcGIS feature service returns GeoJSON, which is JSON.
`records_path: features` and templates such as `{properties[zonenname]}` work today —
`_render` uses `str.format_map`, and nested indexing was tested against the real function.

| layer | endpoint | features | text fields | licence |
|---|---|---|---|---|
| Zurich **Hundezonen** | `https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Hundezonen?service=WFS&version=1.1.0&request=GetFeature&typename=hundezone&outputFormat=GeoJSON&FILTER=<ogc filter>` | 69 leash zones, 7 free-run zones, 652 dog bans | zonenname, einschraenkungen, gesetzgebung (HuG / STRB 1184/2021 / § 205 PBG), zusatzbedingung (hours, season) | CC0 |
| Zurich parking tariff zones | WFS `Gebietseinteilung_Parkierungsgebuehren`, typename `tarifzonen` | 2 | zone_bezeichnung, tarifzone, bedienungszeiten | CC0 |
| Zurich street parking | WFS typename `view_pp_ogd` | 300+ | art, gebuehrenpflichtig, parkdauer — **no street name**, not citable | CC0 |
| Bern **Leinenpflicht** | `https://map.bern.ch/arcgis/rest/services/Geoportal/Hundeverordnung_Leinenpflicht/MapServer/0/query?where=1=1&outFields=*&f=geojson` | 37 | Flaechename, Beschrieb ("Gemäss Hundeverordnung vom 24. November 2010"), rubrik_desc | not stated on opendata.swiss |
| Geneva **Espaces interdits aux chiens** | `https://vector.sitg.ge.ch/arcgis/rest/services/FFP_CHIENS_INTERDITS/FeatureServer/0/query?where=1=1&outFields=*&f=geojson` | >2 (paged) | NOM (e.g. Parc Louis Cottier), LOCALISATION | SITG conditions, *unverified* |
| Geneva Espaces pour chiens en liberté | `…/FFP_CHIENS/FeatureServer` | paged | GESTION only, **no names** | |
| Geneva Points de collecte des déchets | `…/GOL_DECHETTERIE/FeatureServer` | paged | COMMUNE, ADRESSE, TYPE_CENTRE, BENNE, HORAIRES (a URL) | |
| Geneva Stationnement sur la voie publique | `…/OTC_STATIONNEMENT_V_PUBLIQUE/FeatureServer` | paged | NOM_RUES, TYPE_STATIONNEMENT ("Gratuit 60 min"), NOMBRE_PLACES | |
| Basel Hundesignalisation | data.bs.ch 100023 | 316 | coordinates only, no names | CC BY 4.0 |

The Zurich leash layer answers the README's own demo question ("Can my dog run off leash in Zurich
parks?") place by place, with the ordinance cited in the record. The OGC `FILTER` parameter
selects one restriction type (69 rows, under the cap); `CQL_FILTER` is ignored by that server;
WFS 2.0 paging returned 500. Extent for all of these is the city node; Kreis-level placement would
need geocoding. Ban layers with hundreds of rows need the pagination gap below closed.

**Pagination gap in the `api` strategy.** One request, no `offset`/`page` placeholder, so every
source is capped at 100 records: 652 Zurich dog bans, 7,817 Basel parking rows and 72,826 St.
Gallen collection rows are out of reach except by hand-splitting with filters. ArcGIS services
support `resultOffset`/`resultRecordCount` (offset *not tested*), Opendatasoft `offset`, WFS 1.1.0
`maxFeatures` only. A `{offset}` placeholder plus a `page_size`/`max_pages` config would unlock all
of them. Worth an enhancement issue.

## 3. Cantonal law: needs a fetcher, and the API route is the only practical one

**The portals are JavaScript apps.** `bl.clex.ch`, `gesetzessammlung.bs.ch`, `belex.sites.be.ch`,
`srl.lu.ch`, `bgs.zg.ch` each return ~2.3 KB with zero `<a href>` and one word of text to a plain
HTTP client. `html_crawl` cannot ingest them. (`zh.ch` and `ge.ch` landing pages are real HTML, but
their inner collections were not tested.)

**The schema has a `cantonal_law` authority and no source uses it** (`grep authority: cantonal_law
registry/sources/` is empty).

### 3.1 opencaselaw.ch — keyless REST API, CC0 corpus

Base `https://mcp.opencaselaw.ch/api`, OpenAPI at `/api/openapi.json` (62 endpoints). No API key.
Relevant endpoints:

| endpoint | returns |
|---|---|
| `GET /laws/search?q=&canton=&limit=` | federated hits over federal and cantonal *articles*: level, canton, sr_number, title, article_num, heading, snippet, lexfind_id |
| `GET /laws/{canton}/{sr_number}` | act metadata + article list (num, heading) |
| `GET /legislation/{lexfind_id}` | **full article text**, `is_active`, `current_version.active_since`, `urls.<lang>.original_url` |
| `GET /legislation/search?q=&canton=&active_only=` | LexFind catalogue (33k acts) |
| `GET /legislation/changes?canton=` | change feed |
| `GET /laws/{abbreviation}?article=` | federal article text with Fedlex ELI `source_url` and `consolidation_date` |

Verified across six cantons that `original_url` points at the **official** cantonal portal:

| canton | act | articles with text | original_url host |
|---|---|---|---|
| ZH | 554.51 Hundeverordnung | 38/39 | www.zh.ch (zhlex) |
| GE | M 3 45 Loi sur les chiens | 45/45 | silgeneve.ch (Geneva legislative system; *official status inferred*) |
| BS | 365.110 Hundehalteverordnung | 67/67 | www.gesetzessammlung.bs.ch |
| BE | 916.31 Hundegesetz | 28/28 | www.belex.sites.be.ch (de + fr) |
| TI | 922.110 Regolamento caccia | 69/69 | www3.ti.ch |
| VD | 133.75 Loi police des chiens | 40/40 | prestations.vd.ch |

Provenance chain for a citation: opencaselaw → LexFind → official portal. Cite `original_url`.
Refresh (README): decisions daily at 01:00/04:00 UTC; the **cantonal legislation mirror monthly on
the 2nd of each month**, the day after acts enter into force; `legislation/changes` hits LexFind
live. Rate limits: none documented, no rate-limit headers on responses, no API key, no uptime
commitment. Licence: code MIT; dataset packaging CC0 "to the extent rights exist"; the act texts
stay official publications of the cantons. Operator Jonas Hertner; citation file in the repo. One
TI lookup by LexFind id failed ("Failed to fetch legislation from LexFind"), so a fetcher needs
retry and a failed-item report, and should run after the 2nd of the month.

Fetcher shape: like `fedlex.py` but simpler — enumerate acts per canton (`/legislation/search`,
`active_only`), fetch `/legislation/{id}`, one section per article with `heading_path = "Art. N
Heading"`, `authority: cantonal_law`, `default_extent_id: CH-<canton>`, `valid_from = active_since`,
`url = original_url`, `identifier = <canton> <systematic_number>`. Documents are DE/FR/IT and go
through translation like Fedlex.

### 3.2 LexFind itself — `https://www.lexfind.ch/api/fe/{lang}/...`

Operated for the Schweizerische Staatsschreiberkonferenz by Sitrox with ZRI (*from a web search,
secondary source*). 28 entities: CH, Intlex, all 26 cantons. `GET /api/fe/de/entities` and
`GET /api/fe/de/texts-of-law/{id}` respond (id, systematic_number, is_active, dta_urls with
original_url). `robots.txt` contains no rules. **No published terms of use found**: the impressum
is a JavaScript shell. There is no listing endpoint; opencaselaw's scraper enumerates through
full-text search sessions and sleeps between requests. Prefer opencaselaw's mirror for bulk work
and keep LexFind as the per-act fallback.

### 3.3 The 26 cantonal collection URLs

Listed in `awesome-open-legal-switzerland` § Cantonal Legislation. Nine cantons share the
`…/app/de/systematic/texts_of_law` platform (AI, AR, BL, GL, NW, OW, TG, UR; SH on clex) —
*inferred from the URL pattern*. Useful as the citation targets and for spot-checking.

### 3.4 Zurich and Geneva, tested directly

- **Zurich (zhlex):** an act page is server-rendered HTML (63 KB, 49 links) but holds only
  metadata; the text is a PDF on `notes.zh.ch`. The attachment link answers with a 156-byte
  JavaScript redirect; its target
  `https://www.notes.zh.ch/appl/zhlex_r.nsf/WebView/<docid>/$File/<file>.pdf` returns the PDF
  (180 KB for LS 554.51), so the `pdf` strategy works per act once the target URL is derived.
  Enumeration: the page's own JSON
  `…/gesetzessammlung/_jcr_content/main/lawcollectionsearch_312548694.zhweb-zhlex-ls.zhweb-cache.json?page=N`
  paginates 15 per page (link, referenceNumber, enactmentTitle, enactmentDate, withdrawalDate) but
  is **capped at 150 results** (`moreSearchResultsThanAllowed: true`) and none of the filter
  parameters tried (`query`, `q`, `searchTerm`, `text`) narrow it. Full enumeration therefore comes
  from opencaselaw/LexFind; the site JSON is only good for spot checks.
- **Geneva (rsGE):** the index `silgeneve.ch/legis/index.aspx` is an application; each act is a
  PDF (`…/legis/program/books/RSG/pdf/rsg_m3_45.pdf`, 461 KB, fetches fine). The `pdf` strategy can
  ingest acts from a URL list taken from opencaselaw/LexFind; the API route gives article text
  directly and is simpler.

### 3.5 Amtsblattportal — the official gazettes, one REST API, jurisdiction built in

`https://amtsblattportal.ch/api/v1/` (docs at `/docs/api/`): "The API is freely accessible for
anyone to use"; no key for published data; default page 100, **maximum 2,000 per page**; no rate
limit documented; no guarantee of completeness; legally binding is only the signed PDF. Verified:

- 29 tenants: every cantonal gazette (ZH, BE, LU, …, GE, VD, TI) plus SHAB and `kabda`,
  "ePublikation für Gemeinden und Städte".
- 152 rubrics, including "Allgemeine amtliche Bekanntmachungen", "Bau, Raum, Verkehr, Umwelt und
  Energie", "Bürgerrecht, Steuer- und Zivilstandswesen", "Politische Rechte", "Kommunale
  Bauprojekte", "Beschlüsse und Erlasse".
- Filters on `GET /publications`: `tenants`, `rubrics`, `cantons`, `registrationOffice`,
  **`municipalityId` (FSO commune number, joins `location.bfs_id`)**, `publicationDate.start/.end`,
  `keyword`, `title`. Example counts: tenant ZH 2,849,769 total, 11,348 in the week to 2026-09-22;
  Stadt Bern municipal rubric 1,120.
- Each publication: JSON meta (rubric, office with `municipalityId`, cantons, publicationDate,
  expirationDate, multilingual title) and `GET /publications/{id}/xml` with a `<content>` block
  holding the notice text (e.g. the Solothurn police lifting a forest fire ban, 3 KB).

Most volume is commercial-register and bankruptcy notices; the value is in the general and
municipal rubrics: temporary rules, closures, changed collection days, new ordinances entering
into force. Needs an XML fetcher (new code): filter by rubric and date, map `municipalityId` →
commune node and `cantons` → canton node, `valid_from = publicationDate`, `valid_to =
expirationDate`, cite the portal URL. **Authority: `official_info` for every rubric, including
"Beschlüsse und Erlasse"** — a gazette is a publication organ, not a law collection; the law
authorities are reserved for legal text fetched from the official law platforms (Fedlex, the
cantonal collections via LexFind/opencaselaw, municipal collections), `official_info` for official
entities and the online systems they run, `institutional` for non-government publishers (decision
2026-09-22, recorded in #39). The web UI's robots.txt disallows crawling; the API is the
intended access path.

## 4. Evaluation assets

- **Swiss Legal RAG Bench** (`huggingface.co/datasets/voilaj/swiss-legal-rag-bench`, CC0,
  v0.1 2026-04-28): 30 questions in DE/FR/IT with reference answers and gold SR-article citations;
  federal law only so far. Usable as extra judge cases once the acts are ingested.
- **opencaselaw MCP** (`https://mcp.opencaselaw.ch`, 42 tools): a second grounding server to
  compare answers against in the judge harness. *Not tried.*

## 5. Location resolution assets

- Swiss official commune register (BFS) — already the basis of `locations/data/communes.csv`.
- OpenPLZ API (`openplzapi.org`) — street and postal-code directory; could resolve shared postal
  codes that the tree currently drops (`register.py` keeps a PLZ alias only when unique). *Not tried.*
- ortsnamen.ch REST API — place-name catalogue for aliases. *Not tried.*
- **TERMDAT** v2 API (`https://api.termdat.bk.admin.ch/v2`, OpenAPI at `/swagger/v2/swagger.json`,
  no key; `search?SearchTerm=&InLanguageCode=`): official DE/FR/IT/EN equivalents for
  administrative terms and authority names. Coverage is deliberately partial (the Federal
  Chancellery confirmed the API serves only the translators' subset, per the termdat-mcp project);
  "Abfuhr" returned nothing. Low value for retrieval; possible use for authority-name aliases.

## 6. Discovery instruments

- **opendata.swiss CKAN API** works: `https://ckan.opendata.swiss/api/3/action/package_search?q=`
  — but only with a browser User-Agent; the default curl agent gets 403. Counts on 2026-09-22:
  entsorgung 91, hunde 55, reglement 75, kehricht 15, parkieren 12, schulferien 5, abfuhr 3.
  Most hits are statistics or geodata; the text-shaped ones are listed in 2.2.
- **I14Y** (`api.i14y.admin.ch/api/public/v1/datasets`) answers, but no search parameter tried
  (`query`, `search`, `q`, `text`) filtered the results. Not needed while CKAN works.
- LexFind and opencaselaw `/legislation/search` for law discovery per canton and topic.
- Wikidata commune → website map (already in `docs/sources/commune_sites.csv`).
- **Geneva SITG**: the catalogue is a JavaScript app with no search API found; use the national
  catalogue instead — organisation `canton-geneve` lists 65 waste, 6 dog, 32 noise and 36 parking
  datasets, most with an ArcGIS `FeatureServer` resource (see 2.4).

## 7. Not useful for this project

Statistics portals (BFS, cantonal and city statistics offices), geodata and geoportals, ÖREB
cadastre (parcel level), financial, health, energy, transport, research, cultural-heritage and
international entries, tools, organisations, newsletters, podcasts, media. Reason: numbers or
geometry, not rules; no fetch strategy for CSV or geodata; not citable as evidence for a question.
Federal tax guidance (`estv.admin.ch`, taxes category): the publication pages return 324 KB with
28 links and 325 words to a plain client, i.e. JavaScript-rendered; not crawlable as-is. The social
insurance directives portal `sozialversicherungen.admin.ch` is server-rendered (442 links, 1,174
words) and crawlable with `html_crawl` at extent `CH`, authority `official_info`. Both come from the
legal list's soft-law section.
Basel *Kantonsblatt* (data.bs.ch 100352; 90,871 records) is a gazette **index**: rubric, dates,
registration office and `url_pdf`/`url_xml`, no announcement text inline; the sample rows are
commercial-register entries. Amtsblattportal itself *not checked*.

## 8. Still unverified

- OpenERZ: `zimmerberg` region errors; the hand-transcribed regions' accuracy (no machine source).
- Zurich: a filter parameter for the zhlex listing JSON, if one exists. St. Gallen holidays
  dataset last updated 2025-09.
- opencaselaw refresh is documented, not observed; the failed TI lookup is unexplained.
- Licences of the Bern and Geneva geodata layers (not stated on opendata.swiss); ArcGIS
  `resultOffset` paging; Amtsblattportal terms for automated commercial reuse (not addressed).

## 9. Suggested sequence

1. OpenERZ YAMLs for Winterthur, Uster, Horgen, Thalwil, Adliswil, Dübendorf, Wetzikon, Wädenswil
   (zip-filtered), Basel (per area). Validate each with the fake-backend loop and `audit_ingest.sql`.
2. Basel Abfuhrtermine and the school-holiday datasets; OpenHolidays per canton.
3. Geodata YAMLs: Zurich leash and free-run zones (WFS with FILTER), Bern leash areas (ArcGIS
   REST), Geneva dog-ban spaces and street parking — all under the 100-row cap or filterable.
4. Hand the colleague three enhancement issues with the evidence here: an `opencaselaw` fetcher
   for cantonal law (§3.1), pagination in the `api` strategy (§2.4), and an Amtsblattportal XML
   fetcher (§3.5).
5. Add the RAG Bench questions to the judge cases after the Fedlex expansion lands.

## Appendix: verify commands

```bash
# OpenERZ upcoming rows per region
curl -s "https://openerz.metaodi.ch/api/calendar?region=winterthur&zip=8400&start=2026-09-22&limit=1"
# Basel waste calendar with a date filter (the URL shape a YAML would use)
curl -s "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100096/records?where=termin%3E%3Ddate%272026-09-22%27&order_by=termin&limit=100"
# St. Gallen waste, one area
curl -s "https://daten.stadt.sg.ch/api/explore/v2.1/catalog/datasets/abfuhrdaten-stadt-stgallen/records?where=abfuhrgebiet%3D%27L%20Ost%27%20and%20datum%3E%3Ddate%272026-09-22%27&limit=100"
# opencaselaw: search cantonal articles, then full text
curl -s "https://mcp.opencaselaw.ch/api/laws/search?q=Hund%20Leine&canton=ZH&limit=5"
curl -s "https://mcp.opencaselaw.ch/api/legislation/22888"
# LexFind record with official original_url
curl -s "https://www.lexfind.ch/api/fe/de/texts-of-law/22888"
# cantonal portal is a JS shell (2 KB, no links)
curl -sL "https://www.gesetzessammlung.bs.ch/" | wc -c
# opendata.swiss needs a browser User-Agent
curl -s -A "Mozilla/5.0" "https://ckan.opendata.swiss/api/3/action/package_search?q=schulferien&rows=5"
```

## Appendix B — Source specifications for re-engineering the ingestion

Everything below was observed with live requests on 2026-09-22. Types are as they appear in the
JSON (`string`, `int`, `float`, `bool`, `null`); dates are ISO `YYYY-MM-DD` unless stated. Where a
field was seen but its type not checked, it says so. Keep this with the fetcher work: the current
`api` strategy (`ingest/fetchers/api.py`) reads exactly these keys — `url` (with `{start}` and
`{today}` placeholders; the identity URL is the same URL with placeholder parameters removed, see
#18), `start_offset_days`, `records_path` (dotted path to a list), `id_field` or `id_template`,
`event_date_field`, `title_template`, `text_template`, `language` — makes **one request**, and
renders templates with `str.format_map`, so `{properties[name]}` reaches nested fields.

### B.1 OpenERZ waste calendars — JSON over HTTPS

- Endpoint: `GET https://openerz.metaodi.ch/api/calendar` (also `calendar.json`, `calendar.ics`).
- Parameters: `region` (one of 24 codes below), `zip`, `area`, `types` (repeatable), `start`,
  `end` (`YYYY-MM-DD`), `sort` (`date` | `date:desc`), `offset`, `limit`, `lang`.
- Response: `{"_metadata": {"total_count": int, "row_count": int}, "result": [record…]}`.
- Record: `date` string `YYYY-MM-DD`; `waste_type` string enum (`waste`, `organic`, `paper`,
  `cardboard`, `metal`, `bulky_goods`, `incombustibles`, `chipping_service`, `special`, `textile`,
  `cargotram`, `etram`); `zip` **int** (8400) or **empty string** (Basel) — type is inconsistent
  across regions; `area` string (`""`, `a`–`h`, `guf`, `1`, `ost`, `aussenwachten`); `station`
  string; `region` string; `description` string.
- Regions and upcoming rows on 2026-09-22: zurich 1407, winterthur 521, basel 470, duebendorf 213,
  uster 161, horgen 158, wetzikon 151, waedenswil 138, thalwil 110, embrach 102, rueschlikon 79,
  richterswil 75, gossau-zh 71, kilchberg 69, adliswil 60, bassersdorf 60, wiesendangen 57,
  wangen-bruttisellen 50, hombrechtikon 44, oberrieden 43, langnau 41, seon 32, stgallen 0,
  zimmerberg error.
- Identity: `{waste_type}-{date}` plus zip or area. Cadence: per-region config with
  `start_date`/`end_date` for the calendar year, loaded by GitHub Actions. Licence: none published;
  provenance per region in §2.1. Existing YAML: `registry/sources/open_erz.yaml`.

### B.2 Opendatasoft Explore API v2.1 — JSON (data.bs.ch, data.bl.ch, daten.stadt.sg.ch, data.tg.ch, daten.sg.ch, data.sz.ch, opendata.fr.ch)

- Catalogue search: `GET https://<host>/api/explore/v2.1/catalog/datasets?where="<term>"&limit=N`
  → `{total_count, results: [{dataset_id, metas: {default: {title, license, modified, publisher,
  …}, dcat: {…}}}]}`. A bare `search=` parameter does **not** filter.
- Records: `GET …/catalog/datasets/{id}/records?where=<ODSQL>&order_by=<field>&limit=<≤100>
  &offset=<n>&select=<expr>&group_by=<fields>` → `{total_count: int, results: [{field: value…}]}`.
  ODSQL date filter: `field>=date'YYYY-MM-DD'`; strings in single quotes; errors are HTTP 400 with
  `{error_code, message}`.
- Whole-dataset exports (listed on opendata.swiss, not fetched):
  `…/api/v2/catalog/datasets/{id}/exports/{csv|json|jsonl|parquet|rdfxml}`.
- Datasets:

| host / id | rows | fields (type) | licence |
|---|---|---|---|
| data.bs.ch / 100096 Abfuhrtermine | 15,925; 470 upcoming | `termin` date, `art` string (Grünabfuhr, Kehrichtabfuhr, Papierabfuhr, Metallabfuhr, Grobsperrgut, Unbrennbares), `wochentag` string, `dayofweek` int, `zone` string (A–H, GUF), `geo_shape` GeoJSON Feature (Polygon), `geo_point_2d` {lon, lat} | CC BY 4.0 |
| data.bs.ch / 100397 Schulferien BS | 88 | `year`, `name`, `start_date`, `end_date`, `name_short` (year printed as `"2025"`, type not checked) | CC BY 4.0 |
| data.bs.ch / 100023 Hundesignalisation | 316 | `hs_id`, `hs_beschreibung` (Hundeverbot 226, Leinenpflicht 74, eingezäuntes Freilauf-Hundeareal 10, nicht eingezäuntes 6), `hs_beschraenkung` (e.g. ganzjährig), `hs_bemerkung`, `geo_point_2d`, `geo_shape`; **no place name** | CC BY 4.0 + OSM |
| data.bs.ch / 100329 Parkflächen | 7,817 | `id`, `strasse`, `anzahl_parkfelder` int, `id_typ`, `typ` (Blaue Zone 4,405; Parkplätze gebührenpflichtig 587; Velos…), `tarif_gebiet`, `sopfg_geb`, `tarif_id`, `tarif_code`, `gebpflicht` string ("MO-SA: 08:00-19:00"), `maxparkz` int minutes, `keinl`, `plz` string, `wov_id` | CC BY 4.0 (portal default; not read on the dataset) |
| data.bs.ch / 100352 Kantonsblatt | 90,871 | index only: `rubric_de`, `rubric`, `subrubric_de`, `subrubric`, `publicationdate`, `expirationdate`, `language`, `registrationoffice*`, `id`, `publicationnumber`, `publicationstate`, `primarytenantcode`, `primarytenantname`, `onbehalfof`, `legalremedy`, `cantons`, `url_kantonsblatt`, `url_pdf`, `url_xml` | |
| data.bs.ch / 100058 Ordnungsbussen | 2,051,246 | individual fines (`buzi`, `buzi_text`, `bussen_betrag`, `u_ort_plz`…) — statistics, not a tariff | |
| data.bl.ch / 13350 Schulferien BL | 58 | `schuljahr` string, `name`, `startdatum` date, `enddatum` date | CC BY (portal terms) |
| daten.stadt.sg.ch / abfuhrdaten-stadt-stgallen | 641,215; 72,826 upcoming | `gemeinde`, `abfuhrgebiet` ("L Ost"), `datum` date, `sammlung` (Kehricht…), `zeit` ISO datetime with offset, `strasse`, `pdf` URL string, `periode` ("2024 - 2025"), `titel` | CC BY |
| daten.stadt.sg.ch / schulferien-feiertage-stadt-stgallen | 30, last row 2025-07 | `betreff`, `beginnt_am` date, `endet_am` date | CC BY |

### B.3 CKAN — JSON (ckan.opendata.swiss, data.stadt-zuerich.ch)

- National catalogue: `GET https://ckan.opendata.swiss/api/3/action/package_search?q=<term>
  &fq=organization:<slug>&rows=N` → `{success, result: {count, results: [{name, title: {de, fr,
  it, en}, organization: {name, title: {…}}, license_id, resources: [{format, url,
  download_url}]}]}}`. **Requires a browser User-Agent**; the default curl agent gets 403.
  `organization_list?all_fields=true` lists publishers (`canton-geneve`, `kanton-basel-stadt`,
  `stadt-zurich`, `stadt-st-gallen`, …). Title-exact search: `q=title:"…"`.
- Zurich city: same action API plus the datastore: `GET https://data.stadt-zuerich.ch/api/3/action/
  datastore_search?resource_id=<id>&limit=N&offset=M` and `datastore_search_sql?sql=<SQL>` →
  `{result: {total, records: [{_id, …}]}}`. `ssd_schulferien` resource
  `aad477f6-db39-4d1b-92d8-0885f2d363d1`: `start_date`, `end_date` ISO datetime `Z`, `summary`,
  `created_date`; 296 rows to 2030-07; CC0; also plain CSV at
  `https://data.stadt-zuerich.ch/dataset/ssd_schulferien/download/schulferien.csv`.

### B.4 WFS — GeoJSON (Zurich city geoportal)

- Base `https://www.ogd.stadt-zuerich.ch/wfs/geoportal/<Layer>` (the CKAN package's WFS resource
  gives the exact URL). `?service=WFS&version=1.1.0&request=GetCapabilities` → XML; typename is
  the `<Name>` element. `…&request=GetFeature&typename=<t>&outputFormat=GeoJSON` → content type
  `application/vnd.geo+json`, a FeatureCollection `{features: [{type, properties: {…}, geometry}]}`.
- Works: `maxFeatures=N`; `FILTER=<url-encoded OGC Filter XML>` e.g.
  `<Filter><PropertyIsEqualTo><PropertyName>einschraenkungen</PropertyName><Literal>Leinenpflicht</Literal></PropertyIsEqualTo></Filter>`.
  Ignored: `CQL_FILTER`. Fails (HTTP 500): WFS 2.0.0 `count`/`startIndex`.
- `Hundezonen`, typename `hundezone`, 728 features, 1.76 MB, CC0: `bemerkungen` string|null,
  `einschraenkungen` string (Hundeverbot 652, Leinenpflicht 69, Hundefreilaufzone 7),
  `geometrie_gdo` null, `gesetzgebung` string (HuG 592, STRB 1184/2021 77, § 205 PBG 57,
  Verfügung SID … 2), `gueltig_ab` null (all), `guetlig_bis` (sic) null, `objectid` int, `objekt`
  int, `zone` int, `zonenname` string, `zusatzbedingung` string|null ("10 bis 22 Uhr", "1. April
  bis 30. September 10-22 Uhr").
- `Gebietseinteilung Parkierungsgebühren`, typename `tarifzonen`, 2 features, CC0:
  `bedienungszeiten` string, `tarifzone` string, `zone_bezeichnung` string, `objectid` int.
- `Öffentlich zugängliche Strassenparkplätze OGD`, typename `view_pp_ogd`, >300, CC0: `art`,
  `gebuehrenpflichtig`, `parkdauer` string minutes, `id1` float, `objectid` — no street name.
- `POI öffentliche Spielplätze`, typename `poi_spielplatz_att`, 188, CC0: descriptive fields
  (`besonderes`, `eignung`, `elemente`, `geraete`, `nummer`, `gsz_id`), not rules.

### B.5 ArcGIS REST — GeoJSON (Bern MapServer, Geneva SITG FeatureServer)

- Query: `GET <service>/<layer>/query?where=1%3D1&outFields=*&f=geojson&resultRecordCount=N
  [&resultOffset=M]` → `application/geo+json` FeatureCollection; when truncated the collection
  carries `properties.exceededTransferLimit: true`. `resultOffset` not tested.
- Bern `https://map.bern.ch/arcgis/rest/services/Geoportal/Hundeverordnung_Leinenpflicht/MapServer/0`:
  37 features; `Objectid` int, `Flaechename` string, `Beschrieb` string ("Gemäss Hundeverordnung
  vom 24. November 2010 (Stand 01.04.2017)"), `Url`, `Email`, `Telefon`, `Rubrik` int,
  `Rubrik_desc`, `Letzte_Aenderung` int epoch ms. The same layer over WFS 2.0
  (`…/MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature&typeNames=Geoportal_Hundeverordnung_Leinenpflicht_1:Hundeverordnung_Leinenpflicht&outputFormat=GEOJSON&count=N`)
  returns upper-case field names (`FLAECHENAME`, `BESCHRIEB`, …) and `GmlID`. Licence not stated.
- Geneva `https://vector.sitg.ge.ch/arcgis/rest/services/<SERVICE>/FeatureServer/0`:
  `FFP_CHIENS_INTERDITS` — `OBJECTID` int, `NOM` string, `LOCALISATION` string, `Shape__Area`,
  `Shape__Length` float; `FFP_CHIENS` — `GESTION` string only; `GOL_DECHETTERIE` — `NO_SITE`,
  `NO_VGE` int, `BENNE`, `MODELE_BENNE`, `PROFONDEUR` float, `COMMUNE`, `ADRESSE`, `HORAIRES` URL
  string, `TYPE_CENTRE`, `PHOTO`; `OTC_STATIONNEMENT_V_PUBLIQUE` — `NOM_RUES`,
  `TYPE_STATIONNEMENT` ("Gratuit 60 min"), `NOMBRE_PLACES` int, `TYPE_SUPPORT`, `NOMBRE_ARCEAUX`.
  Licence: SITG conditions page (not read); `license_id` empty on opendata.swiss.

### B.6 OpenHolidays API — JSON

- `GET https://openholidaysapi.org/PublicHolidays?countryIsoCode=CH&languageIsoCode=DE
  &validFrom=YYYY-MM-DD&validTo=YYYY-MM-DD&subdivisionCode=CH-<canton>` → JSON **array** (no
  wrapper; `records_path` must be empty) of `{id uuid, startDate, endDate date, type
  ("Public"), name: [{language, text}], regionalScope, temporalScope ("FullDay"), nationwide bool}`.
  A `SchoolHolidays` endpoint is advertised, not tested.

### B.7 opencaselaw REST — JSON (cantonal and federal legislation)

- Base `https://mcp.opencaselaw.ch/api`; OpenAPI 3.0.3 at `/api/openapi.json` (62 paths); no key;
  no rate-limit headers; cantonal mirror refreshed monthly on the 2nd; corpus CC0, code MIT.
- `GET /laws/search?q=&canton=&sr_number=&jurisdiction=&language=&limit=` →
  `{query, count, results: [{level "federal"|"cantonal", canton, sr_number, abbreviation, title,
  article_num, heading, snippet (matches wrapped in >>> <<<), lexfind_id (cantonal)}],
  federal_hits, cantonal_hits}`.
- `GET /laws/{abbreviation}?article=&language=&canton=&as_of=&format=` (federal) →
  `{sr_number, title, abbreviation, consolidation_date date, canton "CH", level "federal",
  language, source_url (Fedlex ELI with `#art_N`), source_label "Fedlex", articles: [{article_num,
  heading, …}]}` (article text presence not checked on this endpoint).
- `GET /laws/{canton}/{sr_number}` → `{sr_number, title, abbreviation, canton, level "cantonal",
  language, category, lexfind_id, version_active_since, source, articles: [{article_num,
  heading}]}` — headings only.
- `GET /legislation/{lexfind_id}?systematic_number=&canton=&language=&include_versions=` →
  `{lexfind_id, systematic_number, is_active bool, entity (canton code), entity_name, title,
  current_version: {version_id int, title, keywords, status "current", active_since string
  **DD.MM.YYYY**, inactive_since null, is_active bool, category ("Gesetz"|"Verordnung"|"Reglement")},
  urls: {<lang>: {original_url, lexfind_pdf}}, language, source "lexfind", articles: [{article_num
  string, heading string, text string}]}` — full text; 52 KB for 39 articles.
- `GET /legislation/search?q=&canton=&language=&limit=&active_only=&search_in_content=
  &fetch_top_n_texts=` → `{query, canton, language, total, laws: […], merged_from_per_lang_total}`;
  `GET /legislation/changes?canton=&language=` (live LexFind).
- Error shape: unknown abbreviation returns **HTTP 200** with `{error, note}`; validation errors
  are 422 `{detail: [...]}`; a failed LexFind fetch is 200 `{error: "Failed to fetch legislation …"}`.
  A fetcher must check for an `error` key, not only the status code.
- `original_url` hosts seen: www.zh.ch (zhlex act page), silgeneve.ch (PDF), gesetzessammlung.bs.ch,
  belex.sites.be.ch (de and fr), www3.ti.ch, prestations.vd.ch.

### B.8 LexFind API — JSON and PDF

- `GET https://www.lexfind.ch/api/fe/{de|fr|it}/entities` → `[{id int, abbreviation, name,
  icon_endpoint, image_endpoint}]` (28: CH, Intlex, 26 cantons).
- `GET https://www.lexfind.ch/api/fe/{lang}/texts-of-law/{id}` → `{id int, systematic_number,
  is_active bool, dta_urls: [{language, url "/tol/{id}/{lang}", file_size int bytes,
  original_url}], entity: {id, abbreviation, name, …}}`.
- `GET https://www.lexfind.ch/tol/{id}/{lang}` → the act document (the ZH file size 180,129 bytes
  equals the official PDF). No listing endpoint; enumeration only through full-text search
  sessions (`POST /api/fe/{lang}/fulltext-search`, then `GET …/fulltext-search/{sid}?session_id=
  &page_no=&results_per_page=60`, as opencaselaw's scraper does, with a sleep between calls).
  `robots.txt` has no rules; no terms page (the site is a JavaScript shell).

### B.9 Amtsblattportal REST — JSON index, XML body

- Base `https://amtsblattportal.ch/api/v1/`; docs `/docs/api/`; no key for published data;
  page size default 100, **max 2,000**; no rate limit documented; "freely accessible for anyone to
  use"; no completeness guarantee; legally binding only the signed PDF.
- `GET /publications?publicationStates=PUBLISHED[&tenants=&rubrics=&subRubrics=&cantons=
  &registrationOffice=<text>&registrationOfficeIds=&municipalityId=<BFS>&publicationDate.start=
  &publicationDate.end=&keyword=&title=&pageRequest.page=&pageRequest.size=]` →
  `{content: [{meta: {…}, content: null}], total int, …}`.
- `meta`: `id` uuid, `creationDate`, `updateDate` ISO datetime `Z`, `rubric`, `subRubric`
  (e.g. `AM-DA` / `AM-DA50`), `language`, `registrationOffice: {id, displayName, street,
  streetNumber, swissZipCode, town, containsPostOfficeBox, postOfficeBox, municipalityId string
  BFS (e.g. "351"), uid}`, `publicationOriginator`, `publicationNumber`, `publicationState`,
  `publicationDate` ISO datetime, `expirationDate`, `primaryTenantCode`, `onBehalfOf`,
  `invoiceAddressId`, `legalRemedy`, `cantons: [codes]`, `secondaryTenants`,
  `repeatedPublications`, `customsStampImages`, `title: {de, fr, it, en}`, `dossierReference`,
  `copyDeadline`.
- `GET /publications/{id}` → same JSON; `GET /publications/{id}/xml` → `<{SUBRUBRIC}:publication
  xmlns:…>` with `<meta>` and `<content>` (elements such as `announcementTitle`, `text`, HTML
  paragraphs escaped inside). Schemas: `/api/v1/schemas/{tenant}/{version}/{SHORT-CODE}-export.xsd`,
  bulk `/api/v1/schemas/bulk-export.xsd`.
- `GET /rubrics` → 152 `{code, id, name: {de, fr, it, en}, active, tenantId, allowSecondary…}`;
  `GET /tenants` → 29 `{id, code, title: {…}}` (all cantonal gazettes, `shab`, `kabda` municipal).
- Counts on 2026-09-22: tenant `kabzh` 2,849,769 total, 11,348 in the week to 2026-09-22;
  `cantons=ZH` 524,415; Stadt Bern municipal rubric 1,120.

### B.10 Cantonal law portals — HTML, PDF, JavaScript

- JavaScript shells (≈2.3 KB, zero links): `bl.clex.ch`, `gesetzessammlung.bs.ch`,
  `belex.sites.be.ch`, `srl.lu.ch`, `bgs.zg.ch` (landing URLs; the `…/data/<nr>/de` act URLs
  that LexFind returns for BS and BE were not fetched).
- Zurich: act landing page HTML with metadata only; PDF at
  `https://www.notes.zh.ch/appl/zhlex_r.nsf/OpenAttachment?Open&docid=<docid>&file=<file>.pdf`,
  which answers with a 156-byte HTML JavaScript redirect to
  `/appl/zhlex_r.nsf/WebView/<docid>/$File/<file>.pdf` (application/pdf). Listing JSON
  `…/gesetzessammlung/_jcr_content/main/lawcollectionsearch_312548694.zhweb-zhlex-ls.zhweb-cache.json?page=N`
  → `{data: [{link, referenceNumber, enactmentTitle, enactmentDate DD.MM.YYYY, withdrawalDate}],
  numberOfResults (capped 150), numberOfResultPages, moreSearchResultsThanAllowed bool}`.
- Geneva: `https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_<code>.pdf` (application/pdf,
  461 KB for M 3 45); index `silgeneve.ch/legis/index.aspx` is an application.

### B.11 Federal guidance portals — HTML

- `sozialversicherungen.admin.ch` (directives): server-rendered, 442 links, 1,174 words on a
  sample page → `html_crawl`, extent `CH`, `official_info`.
- `estv.admin.ch` publications: 324 KB, 28 links, 325 words → JavaScript-rendered, not crawlable.

### B.12 TERMDAT v2 — JSON

- `GET https://api.termdat.bk.admin.ch/v2/search?SearchTerm=<t>&InLanguageCode=<de|fr|it|en>`
  (both required); OpenAPI at `/swagger/v2/swagger.json` with paths `classification`,
  `collection`, `entry`, `search`; no key. Coverage is a deliberate subset; "Abfuhr" → `[]`.
