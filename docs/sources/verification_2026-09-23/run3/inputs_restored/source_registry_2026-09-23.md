# Source registry: sub-national sources, labelled for ingestion (2026-09-23)

Companion data file: `source_registry_2026-09-23.csv` (50 rows, one per source or source family; columns: id, name, entry_url, level,
jurisdiction, data_type, destination, authority, categories, category_missing, coverage, value, verified_by, report, notes).
Evidence: `verification_results_2026-09-23.md` and `reports/*.md`. `verified_by = main` means the main session re-ran the claim
with its own request. `agent` means only the agent's curl evidence backs it.

---

## A. Labels: where each source goes

| Label | Meaning | What happens next |
|---|---|---|
| `yaml-now:api` / `yaml-now:pdf` / `yaml-now:html_crawl` | An existing strategy reads it today | Write a source YAML in `registry/sources/`, then validate with the fake-backend loop |
| `fetcher:<name>` | Reachable, but needs a new fetcher class (catalogue in B) | Implement the fetcher once; every source with the label lands |
| `resolver` | Location or lookup data, not citable content | Feeds jurisdiction mapping, not the index |
| `design:<question>` | Ingestible, but the landing model cannot express it yet | Decide the design (section D) before ingesting |
| `not-a-source` | Nothing a resident question can cite, or a non-official mirror | Keep the record so nobody re-checks it |
| `blocked:<why>` | Technically or legally not harvestable | Use the named alternative |

Several labels can apply ("`yaml-now:pdf → fetcher:pdf-index`" means: a listed-URL YAML works now; the fetcher removes the manual list).

## B. Fetcher catalogue: data type → how it lands

The landing contract (`src/swiss_grounding/ingest/models.py:14-28`) is: `url, title, language, sections[heading_path, anchor, text],
identifier, published_at, valid_from, valid_to, in_force, event_date`. Jurisdiction = `Source.default_extent_id`, or the result of text
narrowing when `allow_narrowing` is true (never for law authorities; `registry/models.py`, `enrich.py:42-44`).
Allowed categories: `dogs, health, hiking, housing, parking, safety, schools, taxes, transport, waste`.

| Fetcher | Input data type | Discovery | Parse → sections | Field mapping | Serves (ids) | Coverage |
|---|---|---|---|---|---|---|
| **lexwork** | JSON API (xhtml or JSON article tree), PDF fallback | `GET /api/{lang}/texts_of_law/lightweight_index` → `{category: [{id, systematic_number, title, abrogated, structured_document_id}]}`; incremental: `/status/recent_changes` | `show_as_json` → `json_content.document` nodes (`article`/`paragraph`/`title`, `html_content`) → one section per article, heading "Art. N Title"; else `xhtml_tol`; else pypdf on `pdf_link_tol` | url=`canonical_link`, title=title (+abbreviation), identifier=`<host>:<systematic_number>`, valid_from=`enactment` or version date, in_force=`not abrogated` | S01 S02 S03 | 19 cantons + intlex (317) + 49+ communes |
| **iweb-table** | HTML with inline JSON (`data-entities`) → PDF | try `/reglemente`, `/reglements`, `/rechtssammlung`, `/gesetzessammlung`, or the homepage link | JSON rows → follow `/_rte/publikation/<id>` → `/_doc/<id>` → pypdf, sections per page or per "Art. N" | title=`name`/`title`, identifier=`_nummer` or publication id, valid_from=`datum`/`_rechtsgueltigkeit` | S31 (+ school sites) | 438 communes, 18,418 rows |
| **pdf-index** | HTML index page → PDF links | homepage `<a>` matching `r[eè]glement\|reglemente\|rechtssammlung`, or a configured index URL; collect `.pdf`, `/_doc/`, `public/upload/assets/`, `dl.php?ddl=` | pypdf; split on "Art. N"; flag empty text (scanned) | title=link text or filename, identifier=systematic number in the filename (e.g. `73.732.100`), valid_from=date in the filename or "gültig ab" on page 1 | S14–S16 S25 S32 S34 S45 | generic: 102/119 FR, 401/542 Romandie homepages, govis ~264 |
| **sitemap-crawl** | Sitemap index → child sitemaps → server HTML | read the index, open the children, filter `<loc>` by regex allowlist, use `lastmod` for change detection | existing `html_to_page` | url=loc, title=`<h1>`, valid_from=header fields where present (ZH: "Erlassdatum", "Gültig ab") | S37 S38 | ZH, GE, BS, BE offices |
| **ics** | text/calendar | a configured URL per commune/tour (REAL: `?gemid=N&calendar[format]=ics…`; entsorglos: `<slug>.entsorglos.swiss/calendar.ics`; GE: `/document/<n>/telecharger`) | one document per VEVENT | title=`SUMMARY`, event_date=`DTSTART`, identifier=`UID` or summary+date, url=feed URL#uid | S26 S27 S40 | ~32 communes + GE |
| **oereb** | ÖREB extract JSON/XML → PDF | one sample point per commune → `getegrid` → `extract/json?EGRID=` → distinct `LegalProvisions` | pypdf (OCR-quality in SZ) | title=provision title, url=document link, jurisdiction=`MunicipalityCode`, plus the responsible office | S21 | every canton runs the service; confirmed SZ, ZH |
| **ogc-features** | OGC API Features JSON | `/collections/<coll>/items?f=json&crs=…2056`, follow `next` | `dokument` → Rechtsvorschrift PDF → pypdf | as oereb | S22 | ~20 cantons (not ZH/TI/GL) |
| **paginated-json** (#38) | ODS/CKAN JSON over 100 rows | `limit=100&offset=N`, or ODS `/exports/json` (all rows in one GET) | as `api` | as `api` | S25 | many ODS portals |
| **concordat-members** | Intlex PDF accession table | per intlex text | regex `^([A-Z]{2}) (\d\d\.\d\d\.\d{4})` after "Kanton Beitritt" | output = member-canton set (for design D2) | S02 | 317 agreements |
| **lexfind-enum** | JSON | `entities/{id}/systematics?tols_for_systematics[]=` (≤100 per call; 414 above) → `texts-of-law/{id}` → `original_url` | hand-off to the platform fetcher | aggregator: cite `original_url` | S08 | seeds S04–S07 |
| vd-blv / ne-rsn / ti-rleggi / ju-rsju | JSON+XHTML / windows-1252 HTML / HTML / PDF | seeded from lexfind-enum `original_url` | per platform | per platform | S04–S07 | 4 cantons |
| weblication / govis / wp-media / plone-rest | CMS-specific lists → PDF | see brief v4, platform signatures | pypdf | as pdf-index | S33 S34 S17 S35 | ~113 / ~264 / many / 12 |
| xlsx | Excel table | configured URL | one document per row (Schulgemeinde × period) | event_date from Excel serial dates | S41 | ZH 185 Schulgemeinden |
| wfs-gml | WFS 1.1 GML | `GetFeature` per layer | one document per feature, rule text from attributes | title from attributes | S47 | Lausanne |
| phonemos | SSR HTML with `vike_pageContext` JSON (ProseMirror) | crawl links, no sitemap | ProseMirror tree → sections | title=`wikipage.title` | S44 | BE TaxInfo ≥591 pages |
| ocr-pdf | scanned PDF | as pdf-index | OCR, used when pypdf returns empty text | as pdf-index | S28 S30 (S21 quality) | few |

**Build order suggested by coverage × value:** lexwork → iweb-table → pdf-index → sitemap-crawl → ics → (probe coverage, then) oereb.

## C. Sources by destination (ids refer to the CSV)

**Ready today, YAML only:** S42 BS/BL school holidays (api) · S46 Bern waste zones (api) · S43 BE school holidays (pdf) · S37 ZH Steuerbuch, 159 entries
(html_crawl with listed start paths) · S39 GE GeTax · S18 gerichte-zh · S19 BE RSTA · S11 KKPKS · S09 BPUK IVHB · S10 KKJPD · S12 GESPA ·
S14/S15/S16 SZ district collections (listed PDFs) · S25 ZAB calendars (listed PDFs) · S29 Diessenhofen · S20 ZH regional plans ·
S48 SBB fare networks (**only after testing narrowing**).

**Needs a fetcher:** lexwork S01 S02 S03 · iweb-table S31 · pdf-index S32 S34 S45 · sitemap-crawl S38 · ics S26 S27 S40 · oereb S21 ·
ogc-features S22 · paginated-json S25 · per-platform S04–S07 · xlsx S41 · wfs-gml S47 · phonemos S44 · ocr-pdf S28 S30 · CMS lists S33 S35 S17.

**Resolver:** S24 BFS snapshot (commune → district) · S23 geobasisdaten (topic → law → authority).

**Not a source / blocked:** S36 terrara (commercial mirror) · S50 z-a-v, amicus, Lugano, Winterthur, ivhb.ch, Bio Suisse, Preisüberwacher · S13 edudoc (WAF + robot policy; use intlex).

## D. Design questions blocking some sources
| Code | Question | Affects |
|---|---|---|
| `design:multi-commune` | A body serving several communes (ZAB 33–35 across SG+TG, REAL 22, SRFWL 7 across BL+SO, SIGE 8–10, Bezirk Höfe/Schwyz) cannot sit on one node | S17 S25 S26 S28 S30 |
| `design:concordat-members` | An agreement applies to a *set* of cantons; intlex tables miss withdrawals (SZ left IVHB in 2022) | S02 S09 S10 |
| `design:per-record-extent` | `api` has no per-record jurisdiction; one row per commune needs narrowing or per-commune sources | S48 (also any national per-commune dataset) |
| `design:schulgemeinde-map` | ZH school holidays are per Schulgemeinde, not per commune | S41 |
| `design:categories` | No category for building, water, fire service, gambling, courts, family law | S09 S12 S18 S19 S21 S22 S28 S30 |
| `design:law-platform-hosts` | `LAW_PLATFORM_HOSTS` (`registry/official_domains.py`, only on branch `feat/authority-routing-rules`, commit 0f4f764) already lists all 26 cantonal portals (the `www.` prefix is stripped). **Missing: `intlex.ch` (intercantonal: which extent?) and the tlex commune hosts** (`<slug>.tlex.ch` → CH-XX-BFS, plus own hosts such as lex.birsfelden.ch) | S02 S03 |
| `design:internal-audience` | BE TaxInfo labels itself "intern und Gemeinden" | S44 |
| (finding) | Resident fees are usually set per commune, even when an association runs the service; parking rules are municipal | S25 S28 S29 S30 |

## E. Open verification gaps (agent-only, worth one request each before building)
ÖREB and geodienste coverage per canton · tlex own-host texts (447) and population · St. Gallen structured texts completeness (only 2 article nodes seen) ·
the SBB narrowing hit rate · the govis count (264 vs 254) · the share of scanned PDFs in commune collections · GE OCV pages · BS dog PDFs.
