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

For the Wikipedia "Law of Switzerland" reference list, verified entry by entry, see Appendix C.

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

## Appendix C — The Wikipedia "Law of Switzerland" reference list, verified entry by entry

Source: https://en.wikipedia.org/wiki/Law_of_Switzerland, sections "References" and "External
links"; the URLs were extracted from the page DOM on 2026-09-22 (twelve entries). Each entry was
checked by a separate Sonnet 5 agent with a clean context and one shared brief (goal: resolve the
link, find machine-readable law data behind it, dig one hop, report evidence, verify nothing by
assumption). The verdict line of each row is the agent's own; notes marked "editor" are mine.
Recurring fact: `www.admin.ch` returns HTTP 403 (Akamai) to plain HTTP clients, so the five
2016-era admin.ch links were resolved through a browser-like fetch; `fedlex.admin.ch` and
`fedlex.data.admin.ch` are not blocked.

### C.0 Summary table

| # | Entry | Resolves to | Verdict | Feedback in one line |
|---|---|---|---|---|
| R1 | "Bundesrecht", admin.ch | 404 (page retired); modern equivalent Fedlex | Already covered by Fedlex | Same SPARQL endpoint holds unused surface: EN/RM editions, HTML/PDF/DOCX formats, historical consolidations back to 1875, treaties, consultations |
| R2 | "Internationales Recht", admin.ch | fedlex.admin.ch/de/cc/international-law | Usable with a new fetcher | Treaties are absent from our ConsolidationAbstract/XML path; PDF-only via the `oc` family; low value for our categories |
| R3 | "Landesrecht", admin.ch | fedlex.admin.ch/de/cc/internal-law | Usable with a new fetcher | Sitemap enumeration (acts, treaties, gazette, OC), an undocumented live Elasticsearch proxy with the legal-subject taxonomy, stable per-act PDF URLs |
| R4 | SR 101 constitution, admin.ch | fedlex.admin.ch/eli/cc/1999/404/de | Already covered by Fedlex | Four formats per act, full amendment-date history we discard, EN non-binding notice is plain text only |
| R5 | "Systematische Sammlung (SR)", admin.ch | fedlex.admin.ch/de/cc | Usable with a new fetcher / core covered | SKOS legal taxonomy with SR-number notations is SPARQL-queryable and could drive category→SR mapping; bulk OC PDF bundles per year |
| R6 | Tages-Anzeiger, 2006 | dead host; Wayback copy readable | Not a law-data source | Paywalled commercial opinion interview, no legal text, no official links, AI crawling disallowed |
| R7 | 20 Minuten, 2010 | live, redirected | Not a law-data source | Media commentary, no official links, explicit anti-data-mining notice |
| R8 | UniDistance, 2021 | live | Not a law-data source | Institutional commentary; one hop out: the official military-court decision PDF archive (HTML + PDF, no API), outside our categories |
| R9 | Federal Assembly committee report, 2005 | live PDF | Usable with a new fetcher | The parliament OData API and OpenParlData are keyless high-volume JSON sources of preparatory material (`official_info`) |
| E1 | Classified Compilation (English), admin.ch | 403/404; equivalent fedlex.admin.ch/en/cc | Usable with a new fetcher (small extension of FedlexFetcher) | 292 SR acts have official English Akoma Ntoso XML that our parser already handles; add `en` to the language map plus per-act availability handling |
| E2 | OpenCaseLaw | live API | Usable with a new fetcher | Decision, citation-graph, scholarship and commentary APIs plus a CC0 bulk parquet; authority for court rulings from an aggregator to decide |
| E3 | Thommen, Introduction to Swiss Law, 2018 | live PDF, 10 MB | Usable now (PDF, institutional) | CC-BY-4.0 English textbook, text-extractable, chapter on tax law and a passage on cantonal competences incl. waste management |

### C.1 R1 — "Bundesrecht"
https://www.admin.ch/gov/de/start/bundesrecht.html → curl 403 (Akamai, whole www.admin.ch host incl. / and robots.txt); WebFetch ×2 → 404 (page gone). Sibling …/bundesrecht/amtliche-sammlung.html → 301 → https://www.fedlex.admin.ch/de/oc; web index still titles the URL "Fedlex". Modern equivalent: Fedlex (inferred from sibling redirect + index title; original not resolvable).
What: Fedlex (www.fedlex.admin.ch + fedlex.data.admin.ch), Federal Chancellery; publishes BBl (Federal Gazette), AS (Official Compilation), SR (Classified Compilation), and is integrating the EDA treaty database; built on Legilux's "Casemates" software. DE/FR/IT/RM/EN at the data layer.
Law data: Yes — SR (ingested), AS, BBl, treaties.
Machine-readable (verified live):
- SPARQL (in use): for SR 814.01 (one of our 16 acts) manifestations PDF, DOC, DOCX, HTML, XML, PDFX exist — we fetch XML only; languages DEU, ENG, FRA, ITA, ROH exist — fedlex.py LANGUAGE_URI maps de/fr/it only, one language per source.
- Treaty classes exist (TreatyDocument, TreatySignature, TreatyRatification…); the agent's sample title query returned 0 rows — query shape not found.
- Sitemaps (sitemap-index.xml, 200): acts 27 files (10,000 URLs each; pattern eli/fga/<year>/<id>/<lang>), cc1 historical consolidations (e.g. eli/cc/1/452_414_453/de?version=18750129 — versions back to 1875; we fetch "current" only), treaties 10 files (~98,125 <loc> across 5 language editions; eli/treaty/9999/<id>/<lang>), consultations 1 file (111 URLs: draft legislation foreseen/ongoing).
- No RSS/Atom (/de/rss and /rss/oc.xml return the 77,151 B SPA shell).
Crawlability: SPA (0 content links) → html_crawl not viable; fedlex.data.admin.ch has a few static prose pages (e.g. /assets/home/en-CH/01.html, 5,484 B). robots Allow /.
Licence: static description page: "The text and the metadata are made available … in accordance with the technical and legal information for third-party users [fedlex.admin.ch/de/broadcasters], which authorises their re-use for commercial and other purposes." (matches fedlex.yaml:16); exact clause on /de/broadcasters not retrievable (JS).
Fit: SR text covered. Same-endpoint extensions: other formats (HTML/PDF/DOCX) of the same acts; EN/RM editions (official English where present); historical consolidations for "law as of date X"; treaties (needs a working query + list); AS/BBl query patterns not verified. Authority federal_law; CH.
Related: Fedlex SPARQL/LOD; Fedlex sitemaps; Legilux (upstream software, not checked).
VERDICT: Already covered by Fedlex — the platform exposes unused surface within the same SPARQL endpoint (treaties, historical versions, EN/RM editions, HTML/PDF/DOCX) worth a config/fetcher extension, not a new source.
Unknowns: literal licence clause; AS/BBl SPARQL patterns; treaty enumeration query; meaning of eli/fga; bulk RDF dump URL; whether the original page is retired or only bot-gated.

### C.2 R2 — "Internationales Recht" (treaties)
https://www.admin.ch/opc/de/classified-compilation/international.html → curl 403 (Akamai bot block on www.admin.ch); via WebFetch 301 → fedlex.admin.ch/redirect?url=… → https://www.fedlex.admin.ch/de/cc/international-law (200, 77,151 B SPA shell, 0 links).
What: Fedlex international-law branch of the Classified Compilation (treaties Switzerland is party to), Federal Chancellery; de/fr/it/rm/en.
Law data: Yes — treaties (SR 0.xxx), federal law, jurisdiction CH.
Machine-readable:
- Same SPARQL endpoint, with a treaty ontology extension not used by our fetcher: jolux:TreatyDocument 43,403; TaskForTreaty 227,330; PartyConditionToTreaty 72,697; TreatyRatification 3,058; TreatySignature 18,664; TreatyType/Process/Status; TreatySubjectTheme 19,305.
- CRITICAL: our fedlex.py query (ConsolidationAbstract → XML manifestation) returns ZERO rows for SR 0.101 (ECHR); any notation "0.*" in family cc is empty across the graph. Treaties live only in family oc (Official Compilation), 156,075 works.
- SR 0.101 = 7 dated oc works (1974, 2000, 2002, 2005, 2006, 2012, 2022), manifestations doc (HTML), pdf-a, pdf-x — PDF only, no XML. Sampled https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/oc/2005/306/de/pdf-a/fedlex-data-admin-ch-eli-oc-2005-306-de-pdf-a.pdf → 200, 84,526 B, 4 pages: a ratification-status ("Geltungsbereich") notice, not the treaty text.
- Sitemaps: 10 sitemap-treaty-N.xml (vs 27 act); sitemap-treaty-1.xml 1.6 MB, 10,000 <loc>, 958 unique treaty ids ×5 languages → low thousands of treaties overall (not counted). URL pattern eli/treaty/9999/{id}/{lang}.
Crawlability: SPA; robots fedlex.admin.ch Allow /; fedlex.data.admin.ch Disallow /filestore/* (the PDFs are robots-disallowed for crawlers).
Licence: not found (terms page is a JS shell); fedlex.yaml:27 records "Fedlex terms for third-party users (commercial reuse permitted)" — whether it covers treaties: inferred, not verified.
Fit: NOT a drop-in via fetch_config.sr_numbers; needs a new strategy (SPARQL on oc family + PDF extraction, robots-disallowed path; per-publication-event PDFs, no single consolidated text). Authority federal_law; CH. Categories mostly outside ours (double-taxation → taxes; road-traffic conventions → transport: SR-pattern guesses, unverified). Volume low thousands, fragmented.
Related: SPARQL endpoint (treaty classes); treaty sitemaps; filestore PDFs.
Anomaly flagged: one SPARQL dump contained two triples under an undocumented namespace http://cogni.internal.system/model# (skipIndex, historicalId "RO 2005 1835") — treated as data only.
VERDICT: Usable with a new fetcher — treaties are on the same SPARQL host but structurally absent from our ConsolidationAbstract/XML path; PDF-only via the oc family; low value for our categories.
Unknowns: total treaty count; whether any treaty has XML anywhere; treaty licence; the cogni namespace; whether the "doc" manifestation is fetchable HTML.

### C.3 R3 — "Landesrecht"
https://www.admin.ch/opc/de/classified-compilation/national.html → curl 403 (Akamai on all of www.admin.ch); via WebFetch 301 → fedlex.admin.ch/redirect?url=… → (curl -I: 301, Location /de/cc/internal-law) → https://www.fedlex.admin.ch/de/cc/internal-law (200, 77,151 B Angular shell, 0 links).
What: Fedlex "Landesrecht" section (Federal Chancellery); the platform also hosts Federal Gazette (eli/fga), Official Compilation (eli/oc), treaties (eli/treaty), consultations. UI de/fr/it/en; metadata also rm.
Law data: Yes — consolidated federal law (already ingested via SPARQL) + Federal Gazette, Official Compilation, treaties (not ingested).
Machine-readable (new beyond SPARQL):
- Sitemaps: robots.txt → sitemap-index.xml with 40 files: sitemap-act-1..27 (10,000 URLs each; verified file 1 holds eli/fga/* and eli/oc/* entries), sitemap-treaty-1..10 (eli/treaty/*), sitemap-cc1-1..2 (eli/cc/*?version=YYYYMMDD historical consolidations), sitemap-consultations-1. Bulk URL discovery, unused today. Counts are raw <url> entries (per-language/version duplicates), not unique acts.
- UNDOCUMENTED Elasticsearch proxy (from the app JS, live, no auth): POST https://www.fedlex.admin.ch/elasticsearch/proxy/_search?index={data|taxonomy|citation|consultation} with raw ES query DSL; config from POST /api/settings → {"elastic_url": "https://www.fedlex.admin.ch/elasticsearch/proxy", …}.
  - index=taxonomy: SKOS-like legal-subject tree (prefLabel, broaderTransitive), ≥10,000 concepts; query "Tierschutz" → 9 hits (e.g. "Tierschutz bei der Jagd/Fischerei/beim Schlachten").
  - index=data: full JOLux records; sampled SR 455 (Animal Protection Act) 2008 consolidation: dateApplicability 2008-09-01, dateEndApplicability 2010-12-31, 5 language expressions (de/fr/it/en/rm; PDFs only de/fr/it), stable manifestation URLs; also a Federal Gazette entry eli/fga/2011/772 with doc/pdf-a/pdf-x.
  - index=citation, index=consultation: constants in code only, NOT queried.
  - Fragile: not a published contract; could change or be blocked.
- api/assets/app-config.json (200): manifestationTypes pdf-a, pdf-a-an, rdf, xml, html, docx, doc-an, docx-an; availableLanguages en/fr/de/it-CH. Only pdf-a and xml verified this session.
- Verified PDF download: https://fedlex.data.admin.ch/filestore/…/eli/cc/2008/414/20080901/de/pdf-a/fedlex-data-admin-ch-eli-cc-2008-414-20080901-de-pdf-a.pdf → 200, application/pdf, 513,162 B, 10 pages.
- RSS: /rss.xml and /de/rss return the SPA shell → no feed.
- One hop: opendata.swiss CKAN q=fedlex → 155 results incl. "Amtliche Sammlung des Bundesrechts (BS/AS) 1948–2018" (Swiss Federal Archives, ZIP; landing page amtsdruckschriften.bar.admin.ch timed out).
Crawlability: SPA (0 links on every content URL); robots Allow / (print params disallowed).
Licence: not found (terms page JS-only; vocabulary/license URI → 415 on ld+json; opendata.swiss license_id null).
Fit: SPARQL coverage unchanged; ES taxonomy index could drive category→SR enumeration (fragile); sitemap-treaty for treaty enumeration (text still via SPARQL/ES); Federal Gazette / Official Compilation as official_info (consistent with the gazette rule); pdf-a URLs as stable fallback format.
VERDICT: Usable with a new fetcher — three unused verified channels (sitemap enumeration incl. treaties/gazette/OC, an undocumented live Elasticsearch proxy with the legal-subject taxonomy, stable per-act PDF URLs) beyond the SPARQL fetcher.
Unknowns: html/rdf/docx manifestation URLs; citation/consultation indexes; licence text; the BAR bulk ZIP; ES proxy terms/rate limits; unique act counts behind sitemap totals.

### C.4 R4 — SR 101 Bundesverfassung
https://www.admin.ch/opc/de/classified-compilation/19995395/index.html → 301 (seen via WebFetch; curl gets 403 Akamai on www.admin.ch) → https://www.fedlex.admin.ch/redirect?url=… → https://www.fedlex.admin.ch/eli/cc/1999/404/de (200, 77,151 B Angular SPA shell).
What: Fedlex (Federal Chancellery, FRBRauthor ch.bk). SR 101 has 5 jolux:Expressions (DE/FR/IT/RM/EN).
Law data: Yes (federal law text) — ALREADY COVERED by our fedlex_sparql fetcher (re-ran its exact query: dateApplicability 2024-03-03, dateEndApplicability 2028-12-31, XML fileUrl).
Machine-readable, beyond what we use:
- ELI content negotiation on fedlex.data.admin.ch/eli/cc/1999/404 with Accept text/turtle or application/rdf+xml → 200 (CONSTRUCT over the act's named graph): metadata only (titles ×5, jolux:dateEntryInForce 2000-01-01, inForceStatus SKOS concept .../vocabulary/enforcement-status/0 "In force"), partial article stubs (9 of ~197). application/ld+json → 415.
- Per-consolidation manifest via jolux:isEmbodiedBy / jolux:format: FOUR formats per act/lang/date — HTML, PDF (pdf-a), XML (Akoma Ntoso, what we use), DOCX — at https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/{y}/{n}/{YYYYMMDD}/{lang}/{fmt}/{slug}-{n}.{ext}. Static HTML (DE) 527 KB, 1,680 links, 30,104 words, per-article anchors id="art_1"…"art_197" (letter articles "art_10_a" in HTML vs "art_10a" in RDF).
- As-of-date page URLs work: https://www.fedlex.admin.ch/eli/cc/1999/404/20240303/de → 200 (our _page_url pattern).
- EN edition: disclaimer only as plain text in <preface><p> ("English is not an official language … no legal force"); FRBRauthoritative="true" appears once at FRBRWork level, not per expression → non-binding status is string-match only.
- Amendment history queryable: 5 prior consolidation dates for SR 101 (2024-03-03, 2024-01-01, 2022-02-13, 2021-11-28, 2021-03-07); our fetcher keeps only the current one.
- Sitemaps: sitemap-index.xml → 27 act + 10 treaty + cc1 + consultations sitemaps; sampled sitemap-act-1.xml and sitemap-treaty-1.xml: 10,000 <loc> each. Treaty URIs eli/treaty/{year}/{num}/{lang} (e.g. eli/treaty/1852/0001/de) — not ingested today.
Crawlability: www.fedlex.admin.ch SPA (0 links, 375 words) → not html_crawl-able; filestore HTML is crawlable in isolation but reachable only via SPARQL discovery. robots: fedlex.admin.ch Allow / (print params disallowed); fedlex.data.admin.ch Disallow /filestore/* for all UAs (SPARQL paths not disallowed) — compliance question for our direct filestore GETs.
Licence: not found (terms pages are JS shells).
Fit: already covered; same-strategy extensions: treaties (federal_law, CH), full dateApplicability history for valid_from/valid_to.
Related: SPARQL endpoint; treaty sitemaps (~100k treaty-lang URLs); filestore manifests (4 formats); enforcement-status vocabulary.
VERDICT: Already covered by Fedlex — the hop out surfaces treaties, four formats per act, and a full amendment-date history we currently discard.
Unknowns: licence text; meaning of eli/fga/... URLs in sitemap-act-1.xml; exact act/treaty counts (2 of 37 sitemaps sampled); robots Disallow /filestore/* vs our direct GETs.

### C.5 R5 — "Systematische Sammlung des Bundesrechts (SR)"
https://www.admin.ch/gov/de/start/bundesrecht/systematische-sammlung.html → 301 → https://www.fedlex.admin.ch/de/cc (via WebFetch; www.admin.ch returns 403 Akamai to curl regardless of UA). fedlex.admin.ch/de/cc: 200, 77,151 B SPA shell (same size for every route).
What: Federal Chancellery; Fedlex runs on the "Casemates" software (title tag on fedlex.data.admin.ch); DE/FR/IT/RM/EN; hosts BBl (Federal Gazette), AS/OC (Official Compilation), SR/CC, treaties, drafts.
Law data: Yes — federal law (covered) + treaties, Official Compilation deltas, Federal Gazette (not used).
Machine-readable:
- SPARQL https://fedlex.data.admin.ch/sparqlendpoint (Virtuoso), 4 live queries, application/sparql-results+json.
- ELI content negotiation → 303 to a CONSTRUCT query per resource graph.
- NEW: legal taxonomy is a SKOS ConceptScheme at https://fedlex.data.admin.ch/vocabulary/legal-taxonomy ("Sachregister"); top concepts = the 9 SR books (e.g. /2697 "Öffentliche Werke - Energie - Verkehr"); children carry skos:notation = SR prefix (e.g. /2801 "Verkehr" → "0.74"; /2703 "Öffentliche Werke" → "0.72"; "Umweltschutz" at 814.x, where waste lives). jolux:classifiedByTaxonomyEntry links acts to entries → can drive category→SR-range mapping instead of a hand table.
- jolux:language / jolux:format select e.g. the English PDF of an act.
- Bulk Official Compilation PDFs per year/lang: https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/collection/oc/{year}/{lang}/pdf-a/…pdf — verified 2003/de → 200, application/pdf, 2,014,673 B.
- Volume: COUNT(DISTINCT ?act) WHERE {?act a jolux:Act} → 212,002 (includes historical versions and treaties; not disambiguated).
- JOLux docs https://swiss.github.io/fedlex-jolux/ (server-rendered, 22–35 KB pages: intro, Federal Gazette, OC, CC, treaties, vocabularies).
Crawlability: SPA (18 links, all asset chunks) → not crawlable; robots.txt Allow /, ~40 sitemaps (act 1–27, treaty 1–10, cc1-*, consultations-1). www.admin.ch blocks curl entirely (403), including its robots.txt.
Licence: not found on Fedlex (JS shells). Swiss Copyright Act Art. 5 excludes laws/ordinances/treaties/official decrees from copyright — from a third-party site, unconfirmed on an official page.
Fit: covered for SR act XML; same-strategy extensions: taxonomy vocabulary query, treaties, Federal Gazette; new pdf-fetcher opportunity for OC year bundles. Authority federal_law; CH.
Related: JOLux docs (Chancellery-authored, GitHub-hosted); LINDAS https://lindas.admin.ch/ (200, not deep-checked); SPARQL GUI https://fedlex.data.admin.ch/sparql.
VERDICT: Usable with a new fetcher (taxonomy query for category mapping; optional OC PDF bundles); SR act text itself Already covered by Fedlex.
Unknowns: whether our pipeline already uses classifiedByTaxonomyEntry (agent did not read our source); full notation ranges of the 9 books (2 sampled); Fedlex terms page; SPARQL rate limits; opendata.swiss listing for Fedlex; LINDAS depth.

### C.6 R6 — Tages-Anzeiger article
Original http://sc.tagesanzeiger.ch/dyn/news/schweiz/702540.html — DNS failure (host gone).
Wayback https://web.archive.org/web/20110120150718/http://sc.tagesanzeiger.ch/dyn/news/schweiz/702540.html — 200, 85 KB, static HTML, 162 links, ~2,377 words.
What: German interview with Zurich chief prosecutor Andreas Brunner on the 2007 StGB sanctions reform (day-fines). Publisher Tamedia (commercial media). Opinion journalism.
Law data: No. No statute text, no SR/AS numbers, no links to any official domain (grep for admin.ch/fedlex/bger/parlament/bj.admin/ejpd: zero matches).
Machine-readable: none (a story RSS link only).
Crawlability of live host: paywall (302 + premium entitlement cookie); robots.txt allows * but `Claude-Web: Disallow: /`, Google-Extended disallowed.
Licence: not checked.
Fit: none; would be `institutional` at best; 1 document; not worth ingesting.
Related sources: none found.
VERDICT: Not a law-data source — paywalled commercial opinion interview, dead original link, no legal text, no links to official platforms.
Unknowns: other Wayback captures; tagesanzeiger.ch terms; later articles with Fedlex links.

### C.7 R7 — 20 Minuten article
Original http://www.20min.ch/news/schweiz/story/11448235 → 301 → 308 → https://www.20min.ch/story/bedingte-geldstrafe-bald-abgeschafft-348694939046 (200, 271 KB, server-rendered; article body in inline __NEXT_DATA__ JSON).
What: sda wire copy on a 2010 Federal Council consultation draft to toughen the Criminal Code (abolish conditional day-fines, reintroduce short prison terms, electronic monitoring) with party reactions. Publisher 20 Minuten (Tamedia), commercial media.
Law data: No. No statute citations, no outbound links to admin.ch/parlament/fedlex/bger (24 links, all nav).
Machine-readable: none public; /*.json disallowed in robots.txt.
Crawlability: server-rendered; robots.txt allows generic agents but disallows /*story* for named AI bots (GPTBot, CCBot, Amazonbot, …) and carries an explicit notice: automated access, collection or mining without express permission is prohibited; licensing via verlag@20minuten.ch.
Licence: restricted (above).
Fit: none; institutional at best; licensing forbids automated use.
Related (one hop, platform-level only): Fedlex consultation procedures https://www.fedlex.admin.ch/de/consultation-procedures — official, but an Angular SPA (0 links in raw HTML); backend API not checked; the specific 2010 procedure not located.
VERDICT: Not a law-data source — media commentary with no legal text, no official links, and an explicit anti-data-mining notice.
Unknowns: Fedlex consultation-procedures backend API; the specific 2010 record; 20min terms page.

### C.8 R8 — UniDistance article
URL https://unidistance.ch/droit/article/la-justice-militaire-sous-la-loupe — 200, 119 KB, server-rendered TYPO3 (1,574 words, 120 links), sitemap.xml valid; /droit/article/feed.rss → 500.
What: French blog post by Prof. Thierry Godel announcing an academic commentary project on military criminal procedure; summarises Swiss military justice; links to a Weblaw journal article (zstrr.recht.ch, not checked).
Law data: No on the page (institutional commentary). Names Fedlex acts CPM SR 321.0 and PPM SR 322.1 (already covered by our Fedlex ingestion).
Machine-readable: none.
Licence: "Tous droits réservés. Aucun texte de ce site ne peut être reproduit sans l'autorisation d'UniDistance Suisse."
Fit: none (1 page; institutional; military law outside our categories).
Related (one hop):
- Office de l'auditeur en chef https://www.oa.admin.ch/fr — official; HTML.
- ATMC decisions https://www.oa.admin.ch/fr/jugements-tribunal-militaire-de-cassation — 76 per-decision PDFs (vol. 13–16, 2006–2026) with stable URLs `/dam/fr/sd-web/<hash>/<name>.pdf`; sampled `MKGE 16 Nr. 1.pdf` 166 KB, 6 pages, DE/FR/IT/RM headnotes citing articles; enumerable from one server-rendered page; no API/bulk. Official. Licence not confirmed (admin.ch terms page 403).
- Alexandria catalogue (full archive) — JS-only, not crawlable.
- zstrr.recht.ch article — access model unknown.
VERDICT: Not a law-data source — institutional commentary; the one-hop find is the official military-court decision PDF archive (crawlable HTML + PDF, no API), outside our categories.
Unknowns: Alexandria/Primo API; ATMC volumes before 13; oa.admin.ch licence.

### C.9 R9 — Federal Assembly committee report
https://www.parlament.ch/centers/kb/Documents/2004/Rapport_de_la_commission_CAJ-N_04.465_2005-05-26.pdf — 200, application/pdf, 108,222 B, 3 pages, no redirect. Committee report (14–8 against abolishing military justice), Parlamentsdienste; French edition.
Law data: Partial — preparatory material tied to a Business record, not codified law.
Machine-readable (one hop):
- Swiss Parliament OData v1 API https://ws.parlament.ch/odata.svc/ (no key; $format=json): 50 collections (Business, Bill, BillLink, Publication, Committee, Session, Vote, Transcript, Person…). Counts: Business 339,265; Bill 372,275; BillLink 11,467; Publication 71,189. Business?$filter=BusinessShortNumber eq '04.465' → ID 20040465 with SubmittedText/ReasonText HTML inline. Publication (Bundesblatt metadata: Title, Page, Volume, Year, BusinessNumber) has NO URL field. BillLink has LinkUrl (LinkType "Kommissionsunterlagen", parlament.ch/.../DocIdRedir.aspx?ID=…) but populated mainly for recent business (2023+); empty for 04.465. $top/$skip paging exist.
  Licence (Open Data page, DE): data may be used only with source attribution "Parlamentsdienste der Bundesversammlung, Bern", content must not be altered, no rights transferred.
- OpenParlData https://api.openparldata.ch (OpenAPI 3.0 at /openapi.json, 759 KB; REST/JSON): /v1/bodies/?indexed=true → 97 parliaments incl. federal "Schweiz" id 42, all 26 cantons, many municipalities; /v1/bodies/42/docs → 52,365 federal docs (Feuille fédérale items with PDF URLs admin.ch/opc/{lang}/federal-gazette/{year}/{page}.pdf, affair_id, dates to 2026-09-02); /v1/docs/ total 905,261 with offset/limit paging (next_page, total_pages) and a pre-extracted `text` field on many records (sampled a VS cantonal doc with full body). robots.txt disallows /v1/ crawling (API use unaffected). Licence not found on fetched pages (opendata.ch project; "open" per web search, unverified).
- CAVEAT: the admin.ch federal-gazette PDF URLs → curl 403 (Akamai); browser-like fetch → 301 to fedlex.admin.ch/redirect (JS shell) → not fetchable by a plain client today.
Crawlability: parlament.ch server-rendered (SharePoint; 116 KB, 48 links, 1,438 words); robots disallows /_layouts/, /_vti_bin/, /_catalogs/, /publish/; sitemap.xml exists.
Fit: `api` fetcher on ws.parlament.ch (records_path d.results, fields BusinessShortNumber, Title, SubmittedText, ReasonText, BusinessStatusText) and on api.openparldata.ch (docs with text) → official_info, CH; categories only when a business concerns our topics. The PDF itself is a one-off.
VERDICT: Usable with a new fetcher — the parliament OData API and OpenParlData are live, keyless, high-volume JSON sources of preparatory material (the "why" behind a law); official_info, distinct from Fedlex law text.
Unknowns: BillLink coverage before ~2023; OpenParlData licence; whether federal-gazette PDFs are reachable via the Fedlex ELI path; update cadence of both APIs.

### C.10 E1 — Classified Compilation of Federal Legislation (English)
http://www.admin.ch/ch/e/rs/rs.html → 403 (Akamai, whole www.admin.ch host, any UA). Wayback CDX: 200 until ~2015, then 302 → admin.ch/bundesrecht/00566/index.html?lang=en, itself now 403/404. Today's equivalent by topic: https://www.fedlex.admin.ch/en/cc (200, 77,151 B SPA shell) — reached by inference, the redirect chain is dead.
What: Fedlex (Federal Chancellery); English editions exist for a minority of acts and are always marked non-authoritative.
Law data: Yes.
Machine-readable (verified live on the SPARQL endpoint we use):
- With jolux:language <…/language/ENG>: **292 distinct SR acts have an English Akoma Ntoso XML manifestation; 310 have any real English file** (XML/PDF/DOC/DOCX/HTML), out of 13,378 SR-classified entries (not date-filtered).
- Sample: SR 101, consolidation 2024-03-03, EN XML at …/eli/cc/1999/404/20240303/en/xml/…xml — 231 <article eId="art_N"> elements; parsed cleanly by our parse_akoma_ntoso (fedlex.py). Older SR 101 consolidations (2014–2020) exist only as PDF; EN XML from 2021 onward for that act.
- Sitemaps sitemap-cc1-1.xml + sitemap-cc1-2.xml list 263 distinct /en act pages (versioned URLs), cross-validating the count independently.
- ELI content negotiation (303 to metadata view or CONSTRUCT) confirmed.
- Non-binding marker only in the document text: "English is not an official language of the Swiss Confederation. This translation is provided for information purposes only and has no legal force." (SR 101 EN XML <preface>).
- URL pattern per act: https://www.fedlex.admin.ch/eli/cc/{year}/{num}/{date}/en; per article eId="art_N" in XML (fragment on the SPA page untested).
Crawlability: SPA (0 links); www.admin.ch blocked; robots Allow /.
Licence: no licence text found by crawl (JS shells); only the in-document disclaimer.
Fit: extend the existing FedlexFetcher, not a new strategy: LANGUAGE_URI (fedlex.py:20-24) has de/fr/it only — add "en": …/language/ENG; the same QUERY and parser work unchanged (verified). Needs per-act availability handling: only ~2.2% of SR entries have EN XML, and the current code assumes the configured language exists for every act in a source. English does not always track the current consolidation date (false for one older generation, true for SR 101 current). Authority federal_law; CH; volume ~290–310 acts.
VERDICT: Usable with a new fetcher (a small extension of the existing FedlexFetcher) — official EN Akoma Ntoso XML exists and parses with our code for ~292 acts, ~2% of the corpus, requiring per-act availability handling.
Unknowns: in-force filtering of the 292/310; the 263-vs-292 sitemap/SPARQL gap; per-article fragments on the live page; licence page; which of our categories the EN acts cover (not checked).

### C.11 E2 — OpenCaseLaw (decisions, citation graph, scholarship, bulk dataset, MCP)
API https://mcp.opencaselaw.ch/api (200 JSON, no auth), OpenAPI /api/openapi.json (62 paths). MCP SSE at /sse live; POST /api/tool/{name} calls any of 42 tools over HTTP.
What: third-party aggregator (Jonas Hertner), rebuilt daily; 1,081,345 decisions (live /api/statistics) from federal + cantonal courts + ECtHR; 44,434 scholarship records; OnlineKommentar commentaries; legislation (verified separately). DE/FR/IT.
Law data: Yes — court decisions with full text + structure, citation graph (9.65M edges), scholarship, commentaries.
Machine-readable (new beyond legislation):
- GET /api/decisions?query=&court=&canton=&language=&date_from=&date_to=&limit=&offset=&sort= → {total, total_is_lower_bound, results[]}; record: decision_id, court, court_name, court_level, canton, chamber, docket_number, decision_date, language, regeste, snippet, source_url, pdf_url, statutes[] ("Art. 253a Abs. 1 OR"), legal_area, citation_count, is_leading_case, citation_string_{de,fr,it}, canonical_url, rule_statement, pinpoint{e_number, matched_sentence}. No structured statute filter (text query only).
- GET /api/citations/{decision_id}?direction=&min_confidence=&limit=&offset= → edges with confidence_score, source/target ids, docket, court, date (sample bge_BGE_125_III_231: 36 out / 3,121 in).
- GET /api/courts → 66 courts with decision_count, earliest, latest, languages (bger 193,393 1986–2026; ge_gerichte 170,523; bvger 109,009; bge 50,502).
- GET /api/scholarship/cited-by-statute?sr_number=&article= (structured; scholarship only). GET /api/scholarship/sources (10+ university repos; licence per record).
- GET /api/commentaries/search, /api/commentaries/{abbr}?article= → OnlineKommentar text (CC-BY-4.0); when none, a server-synthesised "doctrine_timeline" from BGE holdings (not primary text — flag).
- Atom: /api/atom/{court}.xml (50 newest per court). PDF export: /api/decisions/{id}/export.pdf.
- Bulk: HuggingFace voilaj/swiss-caselaw — cc0-1.0, parquet, 1M–10M rows, one parquet per court (data/bger.parquet …) + daily deltas; 36 fields (decision_id, court, canton, chamber, docket_number, decision_date, language, regeste, abstract_{de,fr,it}, full_text, outcome, judges, source_url, pdf_url, bge_reference, cited_decisions, source); graph/ holds 9.65M citation edges and 12.4M statute→decision links (structured, only in bulk). Legislation NOT in the parquet.
Crawlability: server-rendered + JSON API; robots.txt Allow / for all bots; mcp host disallows /api/decisions/, /metrics, /dev for bots; sitemaps.
Licence: code MIT; dataset packaging + metadata CC0-1.0; decision texts remain official court publications; commentaries CC-BY-4.0; scholarship per record.
Fit: `api` for decisions/citations/scholarship/commentaries, `pdf` for exports; the one-request rule makes full-corpus pulls impossible (total 1M+, lower bound) — bulk parquet is the route for volume. AUTHORITY UNRESOLVED: non-government aggregator republishing official court text; under the rule it is not a law platform and not an official entity → institutional unless fetched from the official court portals (surfaced via /api/courts).
Related: HF dataset (community, CC0); OnlineKommentar.ch; entscheidsuche.ch (upstream scraper for some cantons, inferred from code path); official court portals per canton (ge_gerichte, vd_findinfo… not checked); ZORA/BORIS/UNIGE/e-periodica.
Evidence: openapi 62 paths; /api/courts 18,526 B; /api/statistics total 1,081,345; sampled decisions/citations/scholarship/commentaries; 8 rapid requests all 200, no rate-limit headers; SSE handshake ok; HF API + datasets-server first-rows (36 fields); README licence section; quality.json 66 checks, 57 passed, 0 critical, publish_safe true (2026-09-22T15:14Z).
VERDICT: Usable with a new fetcher — real, sampled decision/citation/scholarship APIs and a CC0 bulk parquet; needs an owner decision on authority for court rulings from an aggregator.
Unknowns: rate limits (none published; no 429 in 8 rapid calls); SLA; whether cantonal court portals expose APIs; cited arXiv paper not read; live data-quality warnings (221,138 http:// URLs, 63,811 ids with whitespace, 40,089 publication_date < decision_date).

### C.12 E3 — Thommen, Introduction to Swiss Law
Resolved: 200, application/pdf, 10,468,933 B, no redirect; byte-identical copy at https://suigeneris-verlag.ch/img/uploads/pdf/oa_pdf-002-1605631970.pdf (same MD5).
What: 452-page open-access English textbook, ed. Marc Thommen (UZH), 13 UZH authors; sui generis book series vol. 2, Carl Grossmann Publishers 2018; DOI 10.24921/2018.94115924; ISBN 978-3-941159-24-2 (OA).
Law data: Partial — scholarship/guidance, not primary legal text; chapters on constitutional law, tax law, civil/criminal/administrative law with landmark-case boxes.
Machine-readable: the PDF (pypdf extracts 452 pages; XMP dc:description "Open Access CC BY 4.0"). One hop: sui-generis.ch/oai (OAI-PMH 2.0, OJS 3.4; ListRecords oai_dc → 89 records/page + resumptionToken; DC fields incl. dc:rights per article) and RSS/Atom feeds; suigeneris-verlag.ch/buecher/ = one server-rendered page listing all 77 OA volumes with DOI, category, type and OA-PDF link (673 KB, 516 links); suigeneris-verlag.ch/wp-json → 401.
Crawlability: open-ius.ch static HTML (no robots.txt, no sitemap, last-modified 2019); sui-generis.ch crawlable except /cache, /search; suigeneris-verlag.ch WordPress sitemap lists no product pages.
Licence: "Creative Commons … CC-BY 4.0" on the copyright page (p. 4) and in XMP; journal articles per-article CC (sampled CC BY-SA 4.0).
Fit: `pdf` strategy, one stable URL → 13–16 chapter sections via the TOC; authority institutional; CH; categories: taxes (Tax Law chapter p. 245), and a passage naming waste management among cross-border cantonal treaty topics (p. 175 book pagination). Caveat: an embedded font subset garbles some pages (Preface, Facts and Figures) → per-chapter extraction check needed.
Related: sui-generis.ch journal (OAI-PMH, DOAJ-indexed); suigeneris-verlag.ch catalogue (77 OA books); open-ius.ch/gesetzgebung (link directory to all 26 cantonal collections + Bundesrecht + LexFind); open-ius.ch/rechtsprechung; open-ius.ch/literatur (8 other OA journals).
VERDICT: Usable now (PDF, institutional background evidence) — CC-BY-4.0 English textbook, text-extractable, supplements law sources rather than replacing them.
Unknowns: "dogs" passage not found in ~15 sampled pages; extent of font corruption; WP REST access; the 8 other journals.

### C.13 What this adds to the plan (editor)

**Same strategy, new configuration — Fedlex (`fedlex_sparql`).** All verified on the endpoint we
already use: (1) **official English editions** exist for 292 acts as XML (310 with any file; SR 814.01 has DEU,
ENG, FRA, ITA, ROH); an official translation is better evidence than our LLM translation and can
replace it where present, with the non-binding notice carried as metadata (it is plain text in
the preface, not a flag); (2) six manifestation formats per act (XML in use; HTML with per-article
anchors, PDF, DOCX); (3) the **full amendment-date history** per act, which `valid_from`/`valid_to`
currently discard; (4) the **SKOS legal taxonomy** (`fedlex.data.admin.ch/vocabulary/legal-taxonomy`,
notations = SR prefixes, acts linked via `jolux:classifiedByTaxonomyEntry`) to enumerate acts per
category instead of a hand-written SR list; (5) sitemaps for bulk URL discovery. Treaties are
PDF-only in the `oc` family and outside our categories: defer.

**New sources.** Parliament OData (`ws.parlament.ch/odata.svc`, 339,265 businesses with submitted
and reason texts inline; attribution licence) and OpenParlData (905,261 documents, pre-extracted
text, offset paging) as `official_info` preparatory material; OpenCaseLaw's decision and
citation-graph APIs and CC0 bulk parquet for "how courts applied this article"; the Thommen
textbook as `institutional` background via `pdf`.

**Authority for court decisions (editor's reading of the 2026-09-22 rule, to confirm).** A court
is an official entity and its decision database is a system it runs, so decisions fetched from an
official court portal are `official_info`; the same text fetched from the OpenCaseLaw aggregator
is `institutional`, and the citation should point at the court's own URL (`source_url` in the API).
Decisions are never a law authority.

**Not sources.** R6, R7 (commercial media; R7 forbids automated use), R8's page itself.

**Fragile or blocked.** The Fedlex Elasticsearch proxy is undocumented and may change or be shut
without notice: use it for discovery experiments only, never as the production fetch path.
`www.admin.ch` blocks plain clients (403); old admin.ch federal-gazette PDF links redirect into the
Fedlex JavaScript shell and are not fetchable by a plain client. `fedlex.data.admin.ch/robots.txt`
disallows `/filestore/*` for crawlers while our fetcher GETs manifestation files there directly —
a compliance judgement to record, not a technical blocker.

### C.14 Unknowns left by the agents (aggregated)

Fedlex licence clause text (JS-only page; the description page says re-use for commercial and
other purposes is authorised); AS/BBl SPARQL query patterns; a working treaty enumeration query;
meaning of `eli/fga` URLs; a bulk RDF dump; the ES `citation`/`consultation` indexes; OpenParlData's
licence; BillLink coverage before 2023; OpenCaseLaw rate limits and the cantonal court portals'
own APIs; the extent of font corruption in the Thommen PDF; Alexandria's API for the military
court archive.
