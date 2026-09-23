# Source catalogue — implementation brief for new ingestion sources

Status 2026-09-22. Every entry below was verified with live requests on that date; the evidence,
sampled responses and verify commands are in `docs/sources/ogd_lists_assessment.md` on PR #31
(Appendix B for wire formats, Appendix C for the Wikipedia reference list). This file is the
short version a developer needs to build the fetcher and land the data.

## The landing contract every source must meet

A fetcher implements `Fetcher.fetch(source, known) -> FetchResult` (`ingest/fetchers/base.py`) and
returns `FetchedDocument`s (`ingest/models.py`): `source_id`, `url`, `title`, `language`,
`identifier`, `published_at`, `valid_from`, `valid_to`, `in_force`, `event_date`, and a tuple of
`Section(heading_path, anchor, text)`. Enrichment adds the English title and sections, the extent
and categories; chunking makes one chunk per section, splitting only when the English exceeds the
cap. Anything that can be expressed as *text with a heading, a URL, a jurisdiction and dates* lands
in the existing `document` and `chunk` tables without schema change.

**Authority rule (decided 2026-09-22, issue #39; ADR draft on the kept branch of closed PR #42, to port in #44):** `federal_law`, `cantonal_law`, `municipal_law`
only for the legal text itself from the official law platforms; `official_info` for official
entities and the online systems they run (governments, municipalities, offices, gazettes, portals,
calendars, data services); `institutional` for non-government publishers. Court decisions from a
court's own portal are `official_info`; the same text via an aggregator is `institutional`.

**Two schema gaps** that some entries would need: a relation table (decision → article, taxonomy
tree) and a column recording whether English text is an official translation or ours.

**Template per entry:** links · wire format · sample record · fields and types · mapping to
document/section · authority · extent rule · categories · licence · cadence · paging · fetcher ·
verify · evidence.

---

## 1. Fedlex — official English editions of federal acts

- **Links:** SPARQL `https://fedlex.data.admin.ch/sparqlendpoint`; act page `https://www.fedlex.admin.ch/eli/cc/{year}/{n}/{YYYYMMDD}/en`; XML `https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/{year}/{n}/{YYYYMMDD}/en/xml/{slug}.xml`.
- **Wire format:** SPARQL results JSON → Akoma Ntoso XML per act (same as the German path).
- **Sample:** SR 101, consolidation 2024-03-03, EN XML with 231 `<article eId="art_N">`; parsed cleanly by `parse_akoma_ntoso`.
- **Volume:** 292 SR acts have an English XML manifestation, 310 any English file, of 13,378 SR-classified entries (not filtered to in force).
- **Fields:** as today (`dateApplicability`, `dateEndApplicability`, `title`, `fileUrl`, `abstract`); language URI `…/language/ENG`.
- **Mapping:** identical to the German path. Better design: fetch DE and EN per act, align by `eId`, store DE as `text_original` and the official EN as `text_en`, mark the English as official.
- **Authority:** `federal_law`. **Extent:** `CH`. **Categories:** per act.
- **Licence:** Fedlex terms for third-party users (commercial re-use authorised, per the platform's description page; clause page is JavaScript-only). The English carries a plain-text non-binding notice in the `<preface>`, not a metadata flag.
- **Cadence:** as consolidations are published; English may lag the current German consolidation (true for older SR 101 generations).
- **Paging:** n/a.
- **Fetcher:** extension of `FedlexFetcher` (`ingest/fetchers/fedlex.py`): add `en` to `LANGUAGE_URI`, choose the English edition only when it matches the newest consolidation date, fall back to the configured language otherwise. Suggested PR: see the linked issue.
- **Verify:** `curl -s -X POST https://fedlex.data.admin.ch/sparqlendpoint -H 'accept: application/sparql-results+json' --data-urlencode 'query=…'` with `jolux:language <http://publications.europa.eu/resource/authority/language/ENG>`.
- **Evidence:** assessment Appendix C.10.

## 2. Fedlex — legal taxonomy for category-driven enumeration

- **Links:** `https://fedlex.data.admin.ch/vocabulary/legal-taxonomy` (SKOS ConceptScheme), same SPARQL endpoint; JOLux docs `https://swiss.github.io/fedlex-jolux/`.
- **Wire format:** SPARQL results JSON; concepts with `skos:prefLabel`, `skos:broader`, `skos:notation` (the SR prefix, e.g. "0.74" Verkehr, "0.72" Öffentliche Werke; environmental protection at 814.x). Acts link through `jolux:classifiedByTaxonomyEntry`.
- **Mapping:** not a document. A lookup that yields SR numbers per category, replacing the hand-written `sr_numbers` list.
- **Fetcher:** a query helper inside the Fedlex fetcher or a CLI command; nothing to store.
- **Verify:** `SELECT ?c ?label ?notation WHERE { ?c skos:inScheme <…/legal-taxonomy>; skos:prefLabel ?label; skos:notation ?notation }`.
- **Evidence:** Appendix C.5 and C.3 (an undocumented Elasticsearch proxy on `www.fedlex.admin.ch/elasticsearch/proxy/_search?index=taxonomy` exposes the same tree; use only for experiments).

## 3. Fedlex — amendment history and formats (extension)

- **What:** every act has all consolidation dates (SR 101: 2024-03-03, 2024-01-01, 2022-02-13, 2021-11-28, 2021-03-07) and manifestations in HTML, PDF, XML, DOCX; `?version=YYYYMMDD` page URLs; sitemaps `sitemap-cc1-*.xml` list historical versions back to 1875.
- **Mapping:** `valid_from`/`valid_to` per consolidation; `document.version` and `superseded_by` already exist. Enables "law as of date X" (`as_of` in `swiss_search`).
- **Fetcher:** extension of the Fedlex query (drop `LIMIT 1`, keep all consolidations, persist as versions).
- **Evidence:** Appendix C.4, C.1.

## 4. Fedlex — international treaties (defer)

- **Links:** `https://www.fedlex.admin.ch/de/cc/international-law`; sitemaps `sitemap-treaty-1..10.xml` (~98,125 URLs across 5 languages); SPARQL classes `jolux:TreatyDocument` (43,403), `TreatyRatification`, `TreatySignature`.
- **Wire format:** PDF only, one per publication event in the `oc` family; the `ConsolidationAbstract`/XML query used for acts returns nothing for SR 0.x.
- **Mapping:** one document per PDF with page sections; several per treaty; sampled PDF was a ratification-status notice, not the text.
- **Authority:** `federal_law`. **Extent:** `CH`. **Categories:** mostly outside ours.
- **Fetcher:** new (SPARQL on `oc` + `pdf`); `fedlex.data.admin.ch/robots.txt` disallows `/filestore/*` for crawlers.
- **Verdict:** defer. **Evidence:** Appendix C.2.

## 5. Cantonal law — the official portals' JSON API (12 cantons verified)

- **Links:** `https://<portal>/api/{de|fr|it}/texts_of_law/{systematic_number}` on `gesetzessammlung.bs.ch`, `belex.sites.be.ch`, `bl.clex.ch`, `srl.lu.ch`, `bgs.zg.ch`, `gesetze.gl.ch`, `rechtsbuch.tg.ch`, `ar.clex.ch`, `ai.clex.ch`, `gesetze.nw.ch`, `rechtsbuch.ur.ch`, `sh.clex.ch` (OW not confirmed; ZH and GE serve PDFs instead).
- **Wire format:** JSON `{"text_of_law": {…}}`.
- **Sample:** BS 365.110 (dog-keeping ordinance), 356,907 B; BE 916.31 Hundegesetz, 315,130 B.
- **Fields (types):** `systematic_number` string, `title`, `abbreviation`, `enactment` ISO date, `date_of_decision` ISO date, `publication_enactment` ISO date, `text_of_law_dates_str` string, `pdf_link` URL, `canonical_link` URL (`/app/{lang}/texts_of_law/{nr}`), `abrogated` bool, `abrogated_scheduled` bool, `version_uid` string, `current_version {id int, version_dates_str string ("Aktuelle Version in Kraft seit: 01.04.2025 (Beschlussdatum: 14.01.2025)"), structured_document_id int, title, abbreviation}`, `selected_version {…, xhtml_tol string, xhtml_cac_tol, xhtml_cac_unified_tol, pdf_link_tol, materials, external_links, available_languages, annex_documents}`, `old_versions []`, `future_versions []`, `change_documents []`.
- **Article markup in `xhtml_tol`:** `<div class='article'>` with `article_number` (`§` + number) and `article_title`, followed by sibling `<div class='paragraph'>` blocks (`number` + `text_content`) until the next article or `level_1 title`. BS 365.110: 37 articles, 93 paragraphs.
- **Mapping:** one document per act: `identifier = "<canton> <systematic_number>"`, `url = canonical_link`, `language`, `valid_from` parsed from `version_dates_str` (DD.MM.YYYY inside a German sentence), `in_force = not abrogated`; one section per article, `heading_path = "§ N Title"`, `anchor = article number`, text = its paragraphs.
- **Authority:** `cantonal_law`. **Extent:** `CH-<canton>`. **Categories:** per act.
- **Licence:** cantonal law is not copyright-protected (Swiss Copyright Act art. 5, secondary source); portal terms not read.
- **Cadence:** on publication. **Paging:** n/a. **Enumeration:** no listing endpoint found on the portals; enumerate systematic numbers through LexFind (`https://www.lexfind.ch/api/fe/{lang}/entities`, `…/texts-of-law/{id}` → `systematic_number`, `original_url`) or opencaselaw `GET /api/legislation/search?canton=`.
- **Fetcher:** new (`cantonal_law_api`); issue #37 describes the opencaselaw route, this is the official-portal route to prefer.
- **Verify:** `curl -s https://www.gesetzessammlung.bs.ch/api/de/texts_of_law/365.110 | python3 -c "import sys,json; d=json.load(sys.stdin)['text_of_law']; print(d['title'], d['current_version'])"`.
- **Evidence:** assessment §3, Appendix B.7–B.10.

## 6. Cantonal law — Zurich and Geneva (PDF)

- **Zurich:** listing JSON `https://www.zh.ch/de/politik-staat/gesetze-beschluesse/gesetzessammlung/_jcr_content/main/lawcollectionsearch_312548694.zhweb-zhlex-ls.zhweb-cache.json?page=N` → `{data: [{link, referenceNumber, enactmentTitle, enactmentDate DD.MM.YYYY, withdrawalDate}], numberOfResults (capped 150), …}`; act page HTML holds metadata only; PDF at `https://www.notes.zh.ch/appl/zhlex_r.nsf/WebView/<docid>/$File/<file>.pdf` (the `OpenAttachment` link answers with a JavaScript redirect to it).
- **Geneva:** `https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_<code>.pdf` (461 KB for M 3 45); index is an ASP.NET app.
- **Mapping:** `pdf` strategy, one document per act, page sections; article structure lost. Prefer the API routes of entry 5 or opencaselaw for article text.
- **Evidence:** assessment §3.4, Appendix B.10.

## 7. Cantonal law — opencaselaw / LexFind (enumeration and fallback)

- **Links:** `https://mcp.opencaselaw.ch/api` (OpenAPI `/api/openapi.json`); `GET /legislation/search?q=&canton=&active_only=`; `GET /legislation/{lexfind_id}` → full article text; `GET /laws/{canton}/{sr_number}`; LexFind `https://www.lexfind.ch/api/fe/{lang}/texts-of-law/{id}`.
- **Wire format:** JSON; `articles[{article_num string, heading string, text string}]`, `urls.<lang>.original_url` (official portal), `current_version.active_since` DD.MM.YYYY, `is_active` bool. Errors arrive as HTTP 200 with an `error` key.
- **Authority:** `cantonal_law` when the text is verified against the official portal; provenance field recommended.
- **Licence:** CC0 packaging; act texts remain official publications. Monthly refresh on the 2nd.
- **Fetcher:** issue #37. **Evidence:** assessment §3.1, B.7, B.8.

## 8. Official gazettes — Amtsblattportal

- **Links:** `https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&…`, `/publications/{id}`, `/publications/{id}/xml`, `/rubrics`, `/tenants`; docs `/docs/api/`.
- **Wire format:** JSON index (`content[{meta{…}}], total`), XML body per notice (`<content>` with `announcementTitle`, `text`).
- **Fields:** `meta.id` uuid, `rubric`, `subRubric`, `language`, `registrationOffice.municipalityId` (BFS number, string), `cantons[]`, `publicationDate`, `expirationDate`, `title{de,fr,it,en}`, `publicationNumber`, `publicationState`.
- **Filters:** `tenants`, `rubrics`, `cantons`, `registrationOffice`, `municipalityId`, `publicationDate.start/.end`, `keyword`, `title`; `pageRequest.page/.size` (max 2,000).
- **Mapping:** one document per notice; `valid_from = publicationDate`, `valid_to = expirationDate`; extent from `municipalityId` → `location.bfs_id`, else canton, else CH; `authority: official_info` for every rubric.
- **Licence:** "freely accessible for anyone to use"; no completeness guarantee; legally binding only the signed PDF.
- **Volume:** tenant ZH 2,849,769 total, 11,348 per week → rubric allow-list mandatory; never the commercial-register rubrics.
- **Fetcher:** issue #39. **Evidence:** assessment §3.5, B.9.

## 9. Waste calendars — OpenERZ (YAML only)

- **Links:** `https://openerz.metaodi.ch/api/calendar?region=<r>&zip=<z>&start={start}&sort=date&limit=100`.
- **Wire format:** JSON `{"_metadata": {"total_count", "row_count"}, "result": [record]}`.
- **Record (types):** `date` "YYYY-MM-DD", `waste_type` enum (waste, organic, paper, cardboard, metal, bulky_goods, incombustibles, chipping_service, special, textile, cargotram, etram), `zip` int or "" (Basel), `area` string, `station`, `region`, `description`.
- **Regions with upcoming rows:** zurich 1407, winterthur 521, basel 470 (by area a–h), duebendorf 213, uster 161, horgen 158, wetzikon 151, waedenswil 138, thalwil 110, embrach 102, rueschlikon 79, richterswil 75, gossau-zh 71, kilchberg 69, adliswil 60, bassersdorf 60, wiesendangen 57, wangen-bruttisellen 50, hombrechtikon 44, oberrieden 43, langnau 41, seon 32; stgallen 0 (stale).
- **Mapping:** existing `api` strategy, clone `registry/sources/open_erz.yaml` per region (`event_date_field: date`, English templates, `llm_tagging: false`). Extent: the commune node.
- **Authority:** `official_info` for zurich/basel/stgallen (city open-data exports); `institutional` for the hand-transcribed regions (bassersdorf, embrach, hombrechtikon, wangen-bruttisellen, wiesendangen) and, absent a stated licence, the others.
- **Paging:** `offset`+`limit`; the strategy has none (issue #38).
- **Evidence:** assessment §2.1, B.1.

## 10. Municipal and cantonal open-data datasets — Opendatasoft and CKAN (YAML only)

- **Opendatasoft records:** `https://<host>/api/explore/v2.1/catalog/datasets/{id}/records?where=<field>>=date'{start}'&order_by=<field>&limit=100` → `{total_count, results[]}`; `offset` for paging.
  - Basel `data.bs.ch/100096` Abfuhrtermine: `termin` date, `art`, `wochentag`, `dayofweek` int, `zone` (A–H, GUF); 470 upcoming; CC BY 4.0.
  - Basel `data.bs.ch/100397` Schulferien: `year`, `name`, `start_date`, `end_date`; 88; CC BY 4.0.
  - Basel-Landschaft `data.bl.ch/13350` Schulferien: `schuljahr`, `name`, `startdatum`, `enddatum`; 58; CC BY.
  - St. Gallen `daten.stadt.sg.ch/abfuhrdaten-stadt-stgallen`: `gemeinde`, `abfuhrgebiet`, `datum`, `sammlung`, `zeit` datetime, `strasse`, `titel`; 72,826 upcoming, per street → filter by `abfuhrgebiet`; CC BY.
- **CKAN datastore (Zurich):** `https://data.stadt-zuerich.ch/api/3/action/datastore_search_sql?sql=SELECT * FROM "aad477f6-db39-4d1b-92d8-0885f2d363d1" WHERE start_date >= '{start}'` → `{result: {total, records[]}}`; school holidays 296 rows to 2030; CC0. `ckan.opendata.swiss` needs a browser User-Agent.
- **Mapping:** `api` strategy; `records_path: results` (Opendatasoft) or `result.records` (CKAN); `event_date_field` = the date field; extent = commune or canton node; `official_info`.
- **Evidence:** assessment §2.2, B.2, B.3.

## 11. Rule-bearing geodata — WFS and ArcGIS as GeoJSON (YAML only, some need #38)

- **Zurich Hundezonen:** `https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Hundezonen?service=WFS&version=1.1.0&request=GetFeature&typename=hundezone&outputFormat=GeoJSON&FILTER=<urlencoded OGC Filter XML>`; 69 leash zones, 7 free-run, 652 bans; `properties`: `zonenname`, `einschraenkungen`, `gesetzgebung` (HuG, STRB 1184/2021, § 205 PBG), `zusatzbedingung`; CC0. `maxFeatures` works, `CQL_FILTER` ignored, WFS 2.0 paging fails.
- **Zurich parking tariff zones:** WFS typename `tarifzonen`: `zone_bezeichnung`, `tarifzone`, `bedienungszeiten`; 2 features; CC0.
- **Bern Leinenpflicht:** `https://map.bern.ch/arcgis/rest/services/Geoportal/Hundeverordnung_Leinenpflicht/MapServer/0/query?where=1%3D1&outFields=*&f=geojson`; 37; `Flaechename`, `Beschrieb` (cites the 2010 dog ordinance); licence not stated.
- **Geneva SITG FeatureServers:** `https://vector.sitg.ge.ch/arcgis/rest/services/<SERVICE>/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson&resultRecordCount=N`; `FFP_CHIENS_INTERDITS` (`NOM`, `LOCALISATION`), `OTC_STATIONNEMENT_V_PUBLIQUE` (`NOM_RUES`, `TYPE_STATIONNEMENT`, `NOMBRE_PLACES`), `GOL_DECHETTERIE` (`COMMUNE`, `ADRESSE`, `TYPE_CENTRE`); `exceededTransferLimit` flags truncation; licence per SITG conditions (not read).
- **Mapping:** `api` strategy with `records_path: features` and templates such as `{properties[zonenname]}` (nested keys verified against `_render`). Extent: the city node. No `event_date`.
- **Not usable:** Basel Hundesignalisation and Geneva free-run spaces (no place names), Zurich street parking (no street name).
- **Evidence:** assessment §2.4, B.4, B.5.

## 12. Public holidays — OpenHolidays API (YAML only)

- **Link:** `https://openholidaysapi.org/PublicHolidays?countryIsoCode=CH&languageIsoCode=DE&validFrom={start}&validTo=<date>&subdivisionCode=CH-<canton>`.
- **Wire format:** JSON array (no wrapper → empty `records_path`) of `{id, startDate, endDate, type, name[{language,text}], regionalScope, temporalScope, nationwide bool}`.
- **Mapping:** `api` strategy, `event_date_field: startDate`, extent the canton node, category `schools`, `official_info`.
- **Evidence:** assessment §2.3, B.6.

## 13. Parliamentary material — Parliament OData and OpenParlData

- **Parliament OData:** `https://ws.parlament.ch/odata.svc/Business?$filter=BusinessShortNumber eq '04.465'&$format=json`; 50 collections; Business 339,265, Bill 372,275, Publication 71,189; fields `BusinessShortNumber`, `Title`, `SubmittedText` (HTML), `ReasonText` (HTML), `BusinessStatusText`; `$top`/`$skip`. Licence: attribution "Parlamentsdienste der Bundesversammlung, Bern", no content changes.
- **OpenParlData:** `https://api.openparldata.ch/v1/bodies/42/docs?limit=&offset=` (federal body 42; 97 bodies incl. all cantons); 905,261 docs overall; records carry a pre-extracted `text` for many and a PDF URL; offset paging with `next_page`. Licence not found.
- **Mapping:** one document per business or doc; sections from the HTML or `text`; `official_info`; extent CH (or the body's canton). Old admin.ch gazette PDF links are not fetchable by a plain client.
- **Fetcher:** new (`api` nearly fits; HTML stripping and paging needed).
- **Evidence:** Appendix C.9.

## 14. Court decisions — OpenCaseLaw (aggregator) and court portals

- **Links:** `GET https://mcp.opencaselaw.ch/api/decisions?query=&court=&canton=&date_from=&limit=&offset=`; `GET /citations/{decision_id}`; `GET /courts` (66 courts with counts); `GET /scholarship/cited-by-statute?sr_number=&article=`; Atom `/api/atom/{court}.xml`; bulk `huggingface.co/datasets/voilaj/swiss-caselaw` (CC0 parquet, one file per court, 36 fields, `graph/` with 9.65M citation edges and 12.4M statute→decision links).
- **Record:** `decision_id`, `court`, `court_name`, `court_level`, `canton`, `docket_number`, `decision_date`, `language`, `regeste`, `snippet`, `source_url`, `pdf_url`, `statutes[]` ("Art. 253a Abs. 1 OR"), `legal_area`, `citation_count`, `is_leading_case`, `full_text` (bulk).
- **Mapping:** one document per decision, sections per consideration; cite `source_url` (the court). Statute links need a relation table (schema gap).
- **Authority:** `official_info` from a court portal, `institutional` via the aggregator. No API rate limit published; data-quality warnings in the live `quality.json`.
- **Evidence:** Appendix C.11.

## 15. Background literature — Thommen, Introduction to Swiss Law (YAML only)

- **Link:** `https://www.open-ius.ch/literatur/thommen_introduction-to-swiss-law.pdf` (10.5 MB, 452 pages, CC BY 4.0, English).
- **Mapping:** `pdf` strategy (page sections today; chapter sections would need a TOC-aware splitter); `institutional`; CH; categories taxes and the competence chapters. Some pages have font-encoding corruption; check extraction per chapter.
- **One hop:** `sui-generis.ch/oai` (OAI-PMH, 89 records per page) and `suigeneris-verlag.ch/buecher/` (77 open-access law books with PDF links).
- **Evidence:** Appendix C.12.

## 16. Not sources

Tages-Anzeiger and 20 Minuten articles (commercial media; 20min forbids automated use), the UniDistance page, the Federal Assembly committee PDF as a standalone item (use entry 13), Basel's fixed-penalty and gazette-index datasets, Bern's leash layer over WMS only. Full reasons in Appendix C.

## Fetcher work map

| Fetcher | Entries | Tracking |
|---|---|---|
| `FedlexFetcher` extensions (English #43 / PR #41; taxonomy, history, formats #46) | 1, 2, 3, 4 | #43, #46 |
| `cantonal_law_api` (official portals, LexFind enumeration) | 5, 6, 7 | #37 (comment points to the portal route), #44 for the authority rule |
| `amtsblatt` (XML) | 8 | #39 |
| `api` pagination | 9, 10, 11, 13 | #38 |
| `api` / `pdf` YAML only | 9, 10, 11, 12, 15 | #45 (per-source config) |
| parliament / opencaselaw decisions + relation table | 13, 14 | #47 |
| authority and extent routing (ADR draft on the branch of closed PR #42) | all | #44 |
