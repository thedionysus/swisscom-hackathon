# Sub-national sources: communes, districts, associations, concordats, cantonal guidance

Status 2026-09-23. This file extends `source_catalogue.md` below the cantonal level. Every entry was checked with live
requests on 2026-09-23 by verification agents (a Sonnet 5 pilot plus five Opus 5.5 groups). The main session then re-ran
the key claims itself. Each entry says which: **[main]** = re-run by the main session, **[agent]** = agent evidence only.
Per-group evidence is in `docs/sources/verification_2026-09-23/`. The machine-readable list is `subnational_sources.csv`,
one row per source with a destination label.

The landing contract, authority rule and entry template are the ones in `source_catalogue.md`. Three code facts shape the
verdicts below:
- The `api` strategy accepts a list at the root of the response when `records_path: ""` (`ingest/fetchers/api.py:20-27`).
  Templates can index nested fields (`{attributes[x]}`, `{fields[x]}`) through `str.format_map`.
- There is **no per-record jurisdiction**. A document lands on `Source.default_extent_id`, or on the result of text narrowing
  when `allow_narrowing` is true, which is never allowed for law authorities (`ingest/enrich.py:42-44`, `registry/models.py`).
- Allowed categories: `dogs, health, hiking, housing, parking, safety, schools, taxes, transport, waste`. Content outside
  them is marked **category missing**.

## Destination labels
| Label | Meaning |
|---|---|
| `yaml-now:<api\|pdf\|html_crawl>` | An existing strategy ingests it today; only a source YAML is needed |
| `fetcher:<name>` | Reachable; needs the named fetcher class (section H) |
| `resolver` | Location or lookup data, not citable content |
| `design:<question>` | Ingestible, but the landing model cannot express it yet (section I) |
| `not-a-source` / `blocked:<why>` | Kept so nobody re-checks it |

---

## A. Law platforms: one API family on three levels (Sitrox LexWork)

### A1. LexWork cantonal law portals: 19 cantons
- **Links:** `https://<host>/api/{de|fr|it}/texts_of_law/lightweight_index` (listing), `…/texts_of_law/{nr}` and
  `…/texts_of_law/{nr}/show_as_json` (detail), `…/text_of_law_types`, `…/systematic_categories`, `…/status/recent_changes`
  and `…/status/future_changes` (change feed).
- **Hosts:** the 12 already in the catalogue plus **gesetzessammlungen.ag.ch, www.gesetzessammlung.sg.ch, www.gr-lex.gr.ch,
  bgs.so.ch, lex.vs.ch (fr), bdlf.fr.ch (fr), gdb.ow.ch**. SG and GR only answer on the `www.` host.
- **Wire format:** JSON. The listing is `{systematic_category_id: [{id, systematic_number, systematic_category_id, title, abrogated: bool,
  structured_document_id: int|null}]}`. The detail is `text_of_law` with `title, abbreviation, enactment, date_of_decision,
  canonical_link, pdf_link, abrogated, selected_version{xhtml_tol, pdf_link_tol, json_content.document}`.
- **Volume (active texts):** AG 463, SG 732, GR 419, SO 539, VS 690, FR 814, OW 517. **[main]** for AG, SG, GR, SO, FR, OW; the VS
  constitution was fetched with 242,785 chars of xhtml **[main]**.
- **Intercantonal agreements inside each collection:** text_of_law_type id 2 ("Interkantonale Vereinbarungen") on every portal
  checked. Cantonal copies often have xhtml where intlex only has a PDF (SG 211.41 HarmoS: 1,350 words) **[agent]**.
- **Mapping:** one document per text; one section per article (`json_content.document` nodes of type `article`, heading
  "Art. N Title"), else split `xhtml_tol`, else pypdf on `pdf_link_tol`. url = `canonical_link`, identifier = `<host>:<systematic_number>`,
  valid_from = the `enactment` or version date, in_force = `not abrogated`.
- **Authority:** `cantonal_law` (all 26 portal hosts are already in `LAW_PLATFORM_HOSTS` on branch `feat/authority-routing-rules`).
- **Destination:** `fetcher:lexwork`. This also closes the listing gap noted in `source_catalogue.md` §5.

### A2. intlex.ch: intercantonal agreements
- **What:** the official "Interkantonales Publikationsorgan iSR", running on LexWork.
- **Links:** `https://www.intlex.ch/api/de/texts_of_law/lightweight_index` (317 texts in 40 categories, all active **[main]**),
  `…/texts_of_law/4.2-2` (HarmoS **[main]**), `…/texts_of_law/9.5-3` (the gambling concordat GSK **[main]**),
  `…/status/recent_changes` (200 JSON with `change_type` and `change_date` **[main]**), PDF `…/api/de/versions/{id}/pdf_file`.
- **Content:** HarmoS 4.2-2, IVHB 7.1-1, hooligan concordat 5.3-3, IKAPOL 5.3-2 (in force 01.01.2025), ZPK 5.3-9, GSK 9.5-3,
  IKV 9.5-4, CORJA 9.5-5 and more. Most texts are PDF with a text layer; only 1 has a structured document **[agent]**.
- **Member cantons:** each PDF has an "Änderungs- und Beitrittstabelle" (canton, accession date, entry into force). Parse it with the
  regex `^([A-Z]{2}) (\d\d\.\d\d\.\d{4})`. **Trap:** the tables miss withdrawals. SZ left IVHB on 22.09.2022 (BPUK PDF) but is
  still listed on intlex **[agent]**.
  - HarmoS: 15 members (ZH BE GL FR SO BS BL SH SG TI VD VS NE GE JU).
  - IVHB: 17 per BPUK (AG AI BE BL FR GR JU LU NE NW OW SH SO TG VS UR ZG).
  - GSK: all 26 cantons **[agent]**.
- **Authority:** `cantonal_law` in substance, but **intlex.ch is not in `LAW_PLATFORM_HOSTS`** and has no single-canton extent
  (see I1, I2).
- **Destination:** `fetcher:lexwork` + `fetcher:concordat-members` + `design:concordat-members`.
- Whether intlex is *complete* for all intercantonal law is not verified.

### A3. tlex.ch: commune law collections
- **What:** Sitrox hosts LexWork for communes at `<slug>.tlex.ch` (there is no wildcard DNS; a random slug does not resolve).
  Some communes use their own host: st.gallen.tlex.ch, lex.birsfelden.ch, reglemente.stadt-solothurn.ch,
  gesetzessammlung.chur.ch (its de index returns `{}`), and Delémont.
- **Volume:** 45 tlex subdomains with texts, **3,555 texts, 2,671 structured** **[main, from the agent's counts file]**, plus 4 communes on
  own hosts (447 texts **[agent]**) = **49 communes**. Uznach's instance is empty. The full host list with BFS numbers is in the appendix.
  All 11 ZG communes are included, plus Winterthur (270), Biel/Bienne (152, de+fr), Luzern, Aarau, Frauenfeld, Wil, Rapperswil-Jona
  and Kloten. The ~846k inhabitants figure is **[agent]**.
- **API:** identical to A1 (checked on baar.tlex.ch: 153 texts, 48 structured **[main]**). `/api/de/settings` returns
  `entity_description` (e.g. "Einwohnergemeinde Baar"). Detect new hosts via `<title>LexWork</title>` or a JSON answer from `/api/de/settings`.
- **Sample:** St. Gallen 412.9 "Hundereglement", enactment 2020-11-01 **[main]**. The JSON tree has 2 article and 3 paragraph nodes; whether
  that is the whole regulation is not verified.
- **Authority:** `municipal_law`, but **the tlex hosts are not in `LAW_PLATFORM_HOSTS`** (I2).
- **Destination:** `fetcher:lexwork` (the same class as A1) + `design:law-platform-hosts`.

### A4. The four non-LexWork cantons
LexFind reports these counts of active texts **[agent]**:

| Canton | Platform | How to get the text | Active | Destination |
|---|---|---|---|---|
| VD | prestations.vd.ch/pub/blv-publication (Angular + JSON API) | `api/recueil-systematique` (tree), `api/actes/CONSOLIDE?id=<uuid>&cote=<nr>` (versions), `api/actes/<htmlId>/html` (XHTML), `/pdf`. The UUID comes from the LexFind `original_url` | 902 | `fetcher:vd-blv` |
| NE | rsn.ne.ch (static) | `/DATA/program/books/rsne/htm/{nr}.htm` (windows-1252) or `/pdf/{nr}.pdf` | 823 | `fetcher:ne-rsn` |
| TI | www3.ti.ch (root returns 403) | `/CAN/RLeggi/public/index.php/raccolta-leggi/legge/num/{n}` (server HTML) | 622 | `fetcher:ti-rleggi` |
| JU | rsju.jura.ch (ASP.NET) | `viewdocument.html?idn=20002&id=X&download=1` returns the PDF | 855 | `fetcher:ju-rsju` |

### A5. LexFind as enumerator
- `GET https://www.lexfind.ch/api/fe/{lang}/entities` returns 28 entities: CH, Intlex (id 28) and the 26 cantons. **There are no communes.**
- The listing, which `ogd_lists_assessment.md:206` says does not exist, works like this:
  `GET /api/fe/{lang}/entities/{id}/systematics?active_only=true&tols_for_systematics[]=<node>…`
  - Without the parameter it returns 0 texts; with the 55 Intlex node ids it returns **317** **[main]**.
  - More than about 100 ids in one request gives HTTP 414, so send them in batches.
  - `texts-of-law/{id}` then gives `original_url`, which seeds A4.
- **Authority:** an aggregator. Cite `original_url` and never give it a law authority. **Destination:** `fetcher:lexfind-enum`.

---

## B. Commune bylaws beyond LexWork (Hundereglement, Abfallreglement, Parkierung, Gebühren)

The agents scanned the homepages of all 2,103 communes in `commune_sites.csv` that list a website; 2,060 answered 200. They then
looked for CMS and vendor signatures in each page **[agent]**.
**No canton publishes a central index of its communes' bylaws.** FR, SO, VD and BE only publish templates.
Fribourg's Art. 42b ARGG obliges FR communes to publish their bylaws online.

### B1. i-web / i-CMS regulations table: 438 communes
- **Signature:** `stats.i-web.ch` or `pcdn1.i-web.ch`, `<table class="icms-dt" data-entities='…'>`. It appears on 496 of the 2,060
  homepages (ZH 91, AG 54, BE 50, SG 45, SO 44, VD 30, LU 27, FR 23).
- **Paths:** `/reglemente` (274), `/gesetzessammlung` (45), `/rechtssammlung` (42), `/reglements` (27).
- **Wire format:** the whole table is inline JSON, with no pagination. There are two variants:
  - "publikation": `name` (link to `/_rte/publikation/<id>`), `datum` "DD.MM.YYYY", `datum-sort`, `kategorieId` "reglement", `herausgeber`.
    The detail page, or a redirect, leads to `/_doc/<id>` (the PDF).
  - "rechtssammlung": `title`, `_nummer` "510.1", `_rechtsgueltigkeit`, `_dokumentList` → `/_doc/<id>`.
- **Volume:** 355 publikation + 83 rechtssammlung = **438 communes, 18,418 rows** **[main, recount of the agent's crawl file]**.
  In a sample of 6, every list contained a dog or waste regulation **[agent]**.
- **Mapping:** one document per row (the PDF through pypdf), sections per "Art. N" or per page. Title from `name` or `title`,
  identifier from `_nummer` or the publication id, valid_from from `datum` or `_rechtsgueltigkeit`. Extent `CH-XX-<BFS>` from commune_sites.csv.
- **Authority:** under ADR 0003 the law authority requires a registered law platform. So this is `municipal_law` once the commune's host is
  registered in `LAW_PLATFORM_HOSTS`, and `official_info` until then (I2). Fee pages are `official_info`. The same CMS runs school sites (Schule Zollikon, Schule Dietikon) and Uster.
- **Destination:** `fetcher:iweb-table`.

### B2. Generic commune regulations page: the fallback
- **Coverage:** 102 of 119 FR homepages and 401 of 542 Romandie homepages (VD 238/293, VS 82/121, JU 42/50, GE 26/45, NE 13/22) link to a
  regulations page **[agent]**. Common paths are `/reglements` and `/reglements-communaux`.
- **CMS mix, FR:** TYPO3 30, WordPress 33, i-web 23, other 33. **Romandie:** WordPress 142, i-web 56, Quicksite 38 (VD), TYPO3 35, Joomla 22.
- **Format:** HTML index pages with PDF lists. A sample of 10 FR pages had no article HTML. PDFs usually have a text layer (Tafers, Wetzikon checked);
  the share of scanned PDFs is unknown.
- **Examples:**
  - Wetzikon (CH-ZH-121): `/de/verwaltung/rechtssammlung/`, **191 PDFs** at `/wAssets/docs/Rechtssammlung/<n>/…pdf`
    (633.1 Abfallreglement, 502.1 Polizeiverordnung, 852.1 Parkierungsreglement) **[main]**.
  - Köniz (CH-BE-355): `/verwaltung/reglementeverordnungen.page/952`, 91 PDFs, including the Hundetaxe **[agent]**.
  - ville-fribourg.ch/reglements-tarifs/<code>: server HTML with articles. Code 410-2: "L'impôt sur les chiens est fixé à 120 francs" **[main]**.
- **Mapping:** find the homepage `<a>` matching `r[eè]glement|reglemente|rechtssammlung`, collect links to `.pdf`, `/_doc/`,
  `public/upload/assets/` or `dl.php?ddl=`, then run pypdf. The title comes from the link text; the systematic number and date often come
  from the file name. **Destination:** `fetcher:pdf-index`.

### B3. CMS-specific lists
| CMS | Signature | How to list | Coverage | Destination |
|---|---|---|---|---|
| govis (backslash AG) | `public/upload/assets/<id>/<name>.pdf?fp=N` | scrape the Reglemente page (e.g. Diessenhofen `/gemeinde/politik/reglemente-verordnungen.html/40`, Küssnacht) | ~264 homepages [agent]; group g1 counted "GOViS 254", not reconciled | `fetcher:pdf-index` |
| Weblication (Talus) | `/wAssets/docs/`, `stats.talus.ch` | `/de/verwaltung/dokumente/` + `/weblication/grid5/scripts/wList.php?action=createListAjaxOfData&listId=…&pageId=N` | ~113 homepages, BE 79 [agent] | `fetcher:weblication` |
| WordPress | `wp-content` | `/wp-json/wp/v2/media?mime_type=application/pdf&search=reglement&per_page=100`, `x-wp-total` header | many | `fetcher:wp-media` |
| Plone (Kanton BL, webcloud7) | `bl-api.webcloud7.ch` | `Accept: application/json`, `@search?SearchableText=`, paging with `b_start` | 12 small BL communes, 682 "Reglement" items [agent] | `fetcher:plone-rest` |

### B4. Not sources
- **terrara.ch:** a commercial PDF mirror of 1,484 building regulations (`servepdf.php?gemainde=&canton=`), `institutional`. Use the commune originals.
- **LexFind for communes:** it has none.
- **"Talus Cloud RIO"** and **"Axsos / iPrime"** were not found.
- **gemeinde.ch** is Talus's demo site.

---

## C. Districts, courts, regional planning

### C1. Schwyz districts: autonomous law-makers
- GOG SZ (SRSZ 152.100) §1 Abs. 2 applies the rules for communes to the districts. District law is **not** in the cantonal SRSZ,
  and data.sz.ch has none **[agent]**.

| District | Extent | Collection | Format | Volume | Destination |
|---|---|---|---|---|---|
| Küssnacht | CH-SZ-1331 (single commune) | `https://www.kuessnacht.ch/politik/rechtssammlung.html/436` | govis HTML + PDF text | **72 PDFs [main]**: Abfallreglement 73.732.100 and its fees, parking 61.612.x, Baureglement | `yaml-now:pdf` → `fetcher:pdf-index` |
| Einsiedeln | CH-SZ-1301 (single commune) | `https://www.einsiedeln.ch/verwaltung/rechtssammlung` | HTML + `libraries.files/sre_NNNNNN.pdf` | **215 PDFs [main]**: fee order, Abfallreglement 440.200, parking 460.100 | same |
| Gersau | CH-SZ-1311 (single commune) | `https://www.gersau.ch/topics/verwaltung/reglemente` | OneGov + `/storage/<sha256>` PDFs | 22: dog tax "Fr. 100.00" per additional dog [agent] | same |
| Höfe, Schwyz | 3 / 15 communes | WordPress media API | JSON + PDF | little resident content | `fetcher:wp-media` + `design:multi-commune` |
| March | 9 communes | i-web, JS-loaded | – | unresolved | – |

Rate limits: the Küssnacht sitemap answered 429.

### C2. Courts and district offices
- **gerichte-zh.ch** (`official_info`, CH-ZH): Drupal, `/sitemap.xml` has 454 URLs, 249 under `/de/themen/` (court costs, family,
  employment, debt enforcement, inheritance). The Bezirksgericht Zürich GO is a PDF (12 pages, text). The fee ordinance is not hosted there;
  `/jsonapi` returns 404. **Destination:** `yaml-now:html_crawl` (`start_paths: [/de/themen]`, `path_allowlist: [/de/themen/]`; extract `<main>`,
  pages are ~600 KB). Category missing: courts, family law **[agent]**.
- **BE Regierungsstatthalterämter** (`https://www.rsta.dij.be.ch`, `official_info`): AEM, 66 sitemap URLs. Guidance on appeals against communal
  decisions, hospitality, inheritance and fire bans; **no published decisions**. robots.txt sets Crawl-delay 10 and disallows `/content/`
  except `/content/dam/`. **Destination:** `yaml-now:html_crawl` (`start_paths: [/de/start/themen.html]`) **[agent]**.

### C3. Regional planning (low value)
- **ZH regional Richtpläne:** 11 texts at `https://maps.zh.ch/system/docs/are_rp/RegRicht/<code>text.pdf`, e.g. the Planungsgruppe
  Pfannenstil text: 103 pages, text layer.
- **Region Oberaargau:** `oberaargau.ch/downloads/richtplan-abbau-deponie-transporte` (Wix, 4 PDFs).
- The AI list had both domains wrong (the real sites are zpp.ch and oberaargau.ch). `yaml-now:pdf`, multi-commune **[agent]**.

---

## D. Geodata that carries legal links

### D1. ÖREB-Kataster LegalProvisions: communal building regulations
- **Links:** the cantonal services listed on `https://www.cadastre.ch/de/oereb-webservice` (maps.zh.ch/oereb/v2, map.geo.sz.ch/oereb,
  oereb2.apps.be.ch, api.geo.ag.ch/v2/oereb, …). Call `getegrid/json?EN=<x>,<y>`, then `extract/json?EGRID=<egrid>` (also xml and pdf).
- **Content:** each restriction lists `LegalProvisions`, with links to the commune's binding Baureglement and the responsible office.
  - SZ sample: Küssnacht, `MunicipalityCode` 1331, "Baureglement; Genehmigung vom 22. August 2006" →
    `https://oereblex.sz.ch/api/attachments/1800` (53 pages, **OCR-quality text**), ResponsibleOffice "Bezirk Küssnacht".
  - ZH sample: `https://oerebdocs.zh.ch/getDoc?docid=N` **[agent]**.
- **Trap:** the JSON shape differs per implementation (SZ uses `extract`, ZH uses `Extract`).
- **Coverage:** every canton runs the service, but the legal-document links are **confirmed only in SZ and ZH**. Probe the other
  cantons before building.
- **Correction:** `ogd_lists_assessment.md:301` lists ÖREB under "Not useful". That holds for the geometry, not for these links.
- **Authority:** `municipal_law` for the Baureglement text once the document host (e.g. oereblex.sz.ch, oerebdocs.zh.ch) is registered as a law
  platform, otherwise `official_info` (I2). Category missing: building.
- **Destination:** `fetcher:oereb`.

### D2. geodienste.ch Nutzungsplanung (OGC API Features)
- **Links:**
  - `https://www.geodienste.ch/info/services.json?base_topics=<t>&language=de` lists the service per canton.
  - `https://geodienste.ch/db/<topic_version>/deu/ogcapi/collections/<coll>/items?f=json&crs=http://www.opengis.net/def/crs/EPSG/0/2056`
    returns the features; it gives 403 without `crs`. Page with the `next` link.
- **Content:** `grundnutzung` features have a `dokument` JSON with `Rechtsvorschrift` links. BE sample: Bauordnung der Stadt Bern,
  Baureglement Ostermundigen (129 pages, text), Baureglement Meikirch. In the SZ sample the field was null **[agent]**.
- **Coverage:** npl_nutzungsplanung is free in about 20 cantons. **ZH, TI and GL are "Im Aufbau"; NW, OW and VD need approval.**
  Also rule-bearing: noise sensitivity levels (22 free), water protection zones (23), wildlife rest zones (16). No dog zones.
- **Licence:** mostly "Freie Nutzung. Quellenangabe ist Pflicht."
- **Destination:** `fetcher:ogc-features` (overlaps with D1).

### D3. Resolvers
- **geobasisdaten.ch:** `https://api.geobasisdaten.ch/api/v1`, found in the SPA's JS bundle.
  - `corp/` returns 79 bodies **[main]** (25 cantons; **SZ is missing**).
  - `legislative-entry/?legislative_corp=<id>` (ZH: 305 entries), a detail endpoint, and `export-xlsx`.
  - Per topic it gives the legal basis (code, URL, paragraphs), the responsible authority and whether ÖREB applies.
  - Destination: `resolver` (topic → law → authority).
- **BFS commune snapshot:** `https://www.agvchapp.bfs.admin.ch/api/communes/snapshot?date=01-01-2026` returns CSV **[main]** with 2,110 communes and
  144 districts; `Parent` gives commune → district. The repo's `locations/data/communes.csv` already has a `district` column **[main]**.
- **swisstopo PLZ directory** (STAC CSV): has no district. `resolver`.

---

## E. Associations of communes, calendars, city data

### E1. Waste
- **ZAB Bazenheid** (33–35 communes, SG+TG):
  - `https://zab.ch/sammelstellen/` has 35 per-commune "Abfall-Agenda" PDFs with text layers **[agent]**.
  - `daten.sg.ch` has the Opendatasoft dataset `sammelstellen-siedlungsabfalle-des-zweckverband-abfallverwertung-bazenheid-zab`:
    **1,116** collection points **[main]**, with fields `ort_name, standort_typ, kanton, plz, standort_name, rubriken_abfallcode`, coordinates.
  - The Organisationsreglement is on publikationen.sg.ch (in force 2000). An SG-published statute that also binds TG communes.
  - **No fee schedule was found.**
  - Destination: `yaml-now:pdf` + `fetcher:paginated-json` + `design:multi-commune`.
- **REAL Luzern** (22 communes):
  - ICS per commune: `https://real-luzern.ch/abfall/abfallkalender/?gemid=<n>&abfk_calendar_download=1&calendar[tourId]=<t>&calendar[gemeinde]=<name>&calendar[format]=ics&calendar[Kehricht]=1&…`
    returns `text/calendar`, 120 events for Dietwil **[main]**. Use `curl -g` because of the brackets.
  - `tourId` and categories come from `data-tourid` and `data-categories` on the `?gemid=N` page. The city of Luzern has street tours
    (AJAX `get_streets`, not tested).
  - Fees are uniform and in server HTML at `/abfall/sammeldienst-gebuehren/` ("CHF –.30 pro kg").
  - Destination: `fetcher:ics` (fees: `yaml-now:html_crawl`).
- **entsorglos.swiss:** `https://<slug>.entsorglos.swiss/calendar.ics`, no auth, filters `?region=&type=`. 10 communes (the EZI Zimmerberg
  communes); Wädenswil has 411 events **[agent]**. Destination: `fetcher:ics`.
- **Vendor notes:** Sammelkalender (5 central-Swiss associations) needs auth (401). A-Region runs on anthrazit.
  z-a-v.ch is only a forum of 5 ZH incinerator operators: `not-a-source`.
- **Bern city waste zones** (CH-BE-351) **[main]**:
  - `https://map.bern.ch/arcgis/rest/services/Geoportal/Abfallsammelquartiere/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=json`
    returns 7 zones.
  - Example record: `Zone_hauskehricht` "A", `Sammelgebiete_hauskehricht` "Montag und Donnerstag", `Sammelgebiete_papier`
    "jeden zweiten Mittwoch", `Sammelgebiete_bereitstellung` "Bereitstellung bis 7 Uhr, maximal 12 Stunden vorher".
  - Destination: `yaml-now:api`:
  ```yaml
  fetch_strategy: api
  fetch_config:
    url: https://map.bern.ch/arcgis/rest/services/Geoportal/Abfallsammelquartiere/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=json
    records_path: features
    id_template: "bern-abfallquartier-{attributes[Objectid]}"
    title_template: "Bern Abfallzone {attributes[Zone_hauskehricht]}"
    text_template: "Kehricht {attributes[Sammelgebiete_hauskehricht]}; Papier {attributes[Sammelgebiete_papier]}; Grüngut {attributes[Sammelgebiete_gruengut]}; {attributes[Sammelgebiete_bereitstellung]}"
    language: de
  ```

### E2. Fire service, water, schools: fees are usually set by each commune
- **Feuerwehr-Zweckverband Diessenhofen** (CH-TG-4536 + 4545):
  - Regulation 708.11 at `https://www.diessenhofen.ch/public/upload/assets/3259/…Rglement.pdf?fp=1` (7 pages, text).
  - It says the exemption tax "wird jährlich von jeder Verbandsgemeinde festgelegt", so the regulation itself has no rate.
  - `yaml-now:pdf`. Category missing: fire service.
- **SRFWL Liestal** (7 communes, BL+SO):
  - Documents at `https://srfwl.ch/reglemente-der-srfwl/`. **The 2025 Statuten and Verordnung are scanned.**
  - The rate is in each commune's law, e.g. Liestal ESL 762.2 (`https://www.liestal.ch/_doc/2663452`): "0,4% vom steuerbaren Einkommen,
    mindestens CHF 100.-, im Maximum CHF 1000.-".
  - Destination: `fetcher:ocr-pdf` + `design:multi-commune`.
- **SIGE Vevey** (water for 8 communes, wastewater for 10):
  - Tariff PDFs through `https://www.sige.ch/wp-json/wp/v2/media?search=tarif`: "CHF 1.75 par m3".
  - The 2025 water tariff PDF is mostly scanned.
- **Abwasserverband Schöftland** (6 AG communes): its statutes only split costs between the communes.
- **Schule Zollikon** (CH-ZH-161) and **Schule Dietikon** (CH-ZH-243): single-commune schools on i-CMS, not joint bodies.
  - Zollikon Tarifordnung 400.12 (in force 01.08.2026).
  - Dietikon Tarifreglement (in force 01.01.2025) and holiday plans.
  - `yaml-now:pdf` or `fetcher:iweb-table`.
- **Preisüberwacher fee comparison:** reached through an HTML form, and the data looks outdated (VAT shown as 7.6%). Low value.

### E3. Transport
- **SBB Tarifverbundkarte:**
  - `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/tarifverbundkarte/exports/json?select=id,name,partners,tarifverbund_urls`
    returns a list of **2,137** communes in one GET **[main]**, e.g. `{"id":"3424","name":"Mörigen","partners":"Libero","tarifverbund_urls":"https://www.sbb.ch/…"}`.
  - The `api` strategy reads it with `records_path: ""`.
  - **Jurisdiction:** as one source it lands on CH, unless narrowing finds the commune in `{name}`. The hit rate is untested; about 1,909 of
    2,137 names match commune_sites labels exactly, and names like "Muri (AG)" differ.
  - Authority: institutional or official_info (to decide).
  - Destination: `yaml-now:api` + `design:per-record-extent`.
- **Fare rules** as open data: none found. OJP Fare needs an API key (401). ZVV zones exist as a WFS, but without communes or prices.

### E4. City open data (rule-bearing only)
- **Lausanne** (CH-VD-5586):
  - WFS `https://map.lausanne.ch/mapserv_proxy?ogcserver=source+for+image%2Fpng&SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=ms:<layer>`
    (GML only).
  - Layers: `planville_zones_chiens` **225 [main]** (interdit, en laisse, en laisse selon saison, ébat sécurisé),
    `planville_zones_chiens_forets` 308 ("En laisse du 1er avril au 15 juillet"), `mobilite_stationnement_macarons_zones` 16,
    `mobilite_stationnement_zpayantes` 571.
  - Destination: `fetcher:wfs-gml`.
- **Biel** (CH-BE-371): 4,027 parking fields as GeoJSON, without tariffs. Low value.
- **Lugano, Winterthur, amicus.ch:** no rule-bearing data. `not-a-source`. Winterthur's waste calendar is already covered by OpenERZ.

---

## F. Cantonal guidance for residents (ZH, GE, BE, BS)

- **One sitemap-seeded crawler covers all four cantons [agent]:**
  - ZH: `https://www.zh.ch/bin/zhweb/publish/sitemap.xml` is an **index of 44 child sitemaps**.
  - GE: 27,978 URLs in 14 pages.
  - BS: 27,209 URLs, Crawl-delay 10.
  - BE: one host per office, each with `/de/sitemap.xml` and `/fr/sitemap.xml` (svsa, sv.fin, weu, bkd).
  - All sampled pages are server HTML. Destination: `fetcher:sitemap-crawl`.
- **ZH Steuerbuch:** `https://www.zh.ch/de/steuern-finanzen.zhweb-sitemap.xml` lists **159** `zstb-*.html` entries **[main]**, plus 245 PDFs.
  Each entry has a header with Erlassdatum, Gültig ab and ZStB-Nummer. `yaml-now:html_crawl` with listed start paths. taxes.
- **Dogs:**
  - ZH: `zh.ch/de/umwelt-tiere/tiere/haustiere-heimtiere/hunde.html` + 15 subpages (the revised Hundegesetz, in force 1 June 2025).
  - GE: `ge.ch/detenir-chien`, `/impot-chiens`.
  - BE: `weu.be.ch/…/hunde-im-kanton-bern.html`.
  - BS: `bs.ch/gd/veterinaeramt/hundehaltende`.
  - All server HTML, `yaml-now:html_crawl` **[agent]**.
  - The AI's "ZH dog rules" PDF is a Ukraine pet-import guide.
- **Road traffic:** ZH `/de/mobilitaet/…` plus a fee order PDF; GE topic pages; BE svsa (229 URLs); BS MFK.
  **Parking rules are municipal.** The BS resident parking card costs CHF 47/month **[agent]**.
- **Tax guides:**
  - GE GeTax `https://www.getax.ch/support/guide/declaration2025/` (98 chapter pages, server HTML; that the AFC runs it is inferred from
    the page title) and a PDF.
  - BS: 61 PDFs on two index pages (`fetcher:pdf-index`). "Steuerwissen A–Z" no longer exists.
  - **BE TaxInfo** `https://www.taxinfo.sv.fin.be.ch/` is a phonemos wiki: server HTML with `vike_pageContext` JSON (a ProseMirror tree),
    at least 591 pages in de+fr. **It labels itself "TaxInfo intern und Gemeinden" [main].** Confirm it is meant to be public before ingesting.
    `fetcher:phonemos` + `design:internal-audience`.
- **School holidays:**
  - BS `data.bs.ch` 100397 (88 rows **[main]**) and BL `data.bl.ch` 13350 (58 rows **[main]**): `yaml-now:api`.
  - GE: `.ics` per school year 2024/25–2030/31 at `https://www.ge.ch/document/<n>/telecharger` (39777 = 2027/28: 10 VEVENTs **[main]**).
    `fetcher:ics`.
  - ZH: `schulferien_ganzer_kanton_zuerich_2025_2026.xlsx` covers 185 Schulgemeinden × 6 periods, as Excel serial dates.
    `fetcher:xlsx` + `design:schulgemeinde-map`.
  - BE: a PDF for the German part (6 years) plus a French sibling for Jura bernois. `yaml-now:pdf` **[main]**.

## G. Intercantonal agreements outside intlex (conference pages)
| Source | Link | Format | Destination | Authority |
|---|---|---|---|---|
| BPUK IVHB | `https://www.bpuk.ch/bpuk/konkordate/ivhb` + text, Anhang 1, member-status PDFs | HTML + PDF text | `yaml-now:pdf` | official_info |
| KKJPD | `https://www.kkjpd.ch/de/dokumentation/interkantonale-vereinbarungen` (files via `?action=get_file&…`) | PDF text | `yaml-now:pdf` | official_info |
| KKPKS | `https://www.kkpks.ch/de/polizeilandschaft/konkordate` + /clcpc /pknw /zpk /ostpol | HTML + PDF | `yaml-now:html_crawl` | official_info |
| GESPA | `https://www.gespa.ch/de/gesetze-und-bewilligungen/regulierungsgrundlagen` (comlot.ch redirects there) | HTML + PDF text | `yaml-now:pdf` | official_info |
| EDK (edudoc.ch) | `https://edk.ch/de/dokumentation/rechtstexte-beschluesse/rechtssammlung` | PDFs behind an AWS WAF (202, 0 bytes); the OAI policy forbids robots | `blocked` → use intlex | – |
| ivhb.ch | – | a private law firm's site | `not-a-source` | institutional |

Police concordat members (KKPKS):
- Westschweiz: FR GE JU NE VD VS
- PKNW: AG BL BS BE SO
- ZPK: LU NW OW SZ UR ZG
- Ostpol: AR AI GL GR SH SG TG

ZH and TI belong to none **[agent]**. Category missing: gambling, building. Safety covers the police texts.

---

## H. Fetcher catalogue (build order by coverage × value)
| # | Fetcher | Input | Serves | Coverage |
|---|---|---|---|---|
| 1 | `lexwork` | LexWork JSON (index → detail → articles, PDF fallback, change feed) | A1 A2 A3 | 19 cantons + intlex + 49 communes |
| 2 | `iweb-table` | inline `data-entities` JSON → `/_doc/` PDF | B1, school sites | 438 communes |
| 3 | `pdf-index` | HTML index → PDF links → pypdf | B2, govis, C1, BS tax, ZAB | generic fallback |
| 4 | `sitemap-crawl` | sitemap index → children → regex allowlist → HTML | F | ZH GE BS BE |
| 5 | `ics` | text/calendar → one document per VEVENT (event_date = DTSTART) | E1, GE holidays | ~32 communes + GE |
| 6 | `oereb` | ÖREB extract → LegalProvisions → PDF | D1 | probe coverage first |
| 7 | `ogc-features` | OGC API Features → `dokument` → PDF | D2 | ~20 cantons |
| 8 | `paginated-json` (#38) | ODS `offset` or `/exports/json` | ZAB points, large ODS datasets | many |
| 9 | `lexfind-enum`, `vd-blv`, `ne-rsn`, `ti-rleggi`, `ju-rsju` | per platform | A4 A5 | 4 cantons |
| 10 | `weblication`, `wp-media`, `plone-rest`, `xlsx`, `wfs-gml`, `phonemos`, `ocr-pdf`, `concordat-members` | per source | B3, E, F | single platforms |

## I. Design questions
1. **`design:concordat-members`:** an agreement applies to a *set* of cantons, and intlex tables miss withdrawals.
2. **`design:law-platform-hosts`:** `LAW_PLATFORM_HOSTS` (branch `feat/authority-routing-rules`, 0f4f764) has all 26 cantonal portals
   but **not intlex.ch and not the tlex commune hosts**. The lookup matches exact hosts after stripping `www.`, so tlex needs one entry per
   commune (the appendix gives slug → BFS) or a pattern rule. intlex needs an extent decision (I1). The same question applies to every commune's own
   collection (B1, B2, C1) and to the ÖREB document hosts (D1): until a host is registered, its texts are `official_info`. Tracked on issue #44.
3. **`design:multi-commune`:** ZAB, REAL, SRFWL, SIGE, Bezirk Höfe/Schwyz each serve several communes, and ZAB and SRFWL span two cantons.
4. **`design:per-record-extent`:** the `api` strategy puts every record on one extent. National per-commune datasets (SBB) need
   narrowing or one source per commune.
5. **`design:schulgemeinde-map`:** the ZH holidays are per Schulgemeinde, not per commune.
6. **`design:categories`:** there is no category for building, water, fire service, gambling, courts or family law.
7. **`design:internal-audience`:** BE TaxInfo.
8. **Finding:** resident fees are usually set per commune, even when an association runs the service. Parking rules are municipal.

## Open gaps (one request each, before building)
- ÖREB and geodienste link coverage per canton.
- The tlex own-host text counts and the population figure.
- Completeness of the structured tlex texts.
- The SBB narrowing hit rate.
- The govis count (264 vs 254).
- The share of scanned PDFs in commune collections.
- The GE OCV pages and the BS dog PDFs.

## Appendix: tlex hosts (slug → BFS, texts, structured) [main, from the agent's counts file]
Uznach (3339) has 0 texts. ERR means the host did not answer as a tlex subdomain because the commune runs its own host.

| Host | BFS | Texts | Struct. | Host | BFS | Texts | Struct. |
|---|---|---|---|---|---|---|---|
| aarau | 4001 | 119 | 102 | kloten | 62 | 93 | 91 |
| aarburg | 4271 | 45 | 41 | luzern | 1061 | 37 | 37 |
| aesch-bl | 2761 | 56 | 54 | menzingen | 1704 | 41 | 41 |
| arlesheim | 2763 | 131 | 60 | muttenz | 2770 | 102 | 102 |
| baar | 1701 | 153 | 48 | neuenkirch | 1093 | 58 | 54 |
| badragaz | 3291 | 70 | 70 | neuheim | 1705 | 54 | 46 |
| bergdietikon | 4023 | 35 | 35 | nidau | 743 | 94 | 60 |
| biel-bienne | 371 | 152 | 152 | oberaegeri | 1706 | 66 | 51 |
| birsfelden (own host) | 2766 | ERR | – | oberrieden | 137 | 50 | 49 |
| bischofszell | 4471 | 49 | 49 | rapperswil-jona | 3340 | 95 | 90 |
| bonaduz | 3721 | 30 | 29 | reinach-bl | 2773 | 116 | 76 |
| cham | 1702 | 122 | 66 | rheinfelden | 4258 | 137 | 31 |
| chur (own host) | 3901 | ERR | – | risch | 1707 | 53 | 49 |
| delemont (own host) | 6711 | ERR | – | silvaplana | 3790 | 14 | 14 |
| domat-ems | 3722 | 42 | 42 | sirnach | 4761 | 24 | 23 |
| ehrendingen | 4049 | 41 | 38 | sissach | 2861 | 70 | 61 |
| ettingen | 2768 | 64 | 49 | solothurn (own host) | 2601 | ERR | – |
| frauenfeld | 4566 | 58 | 58 | spreitenbach | 4040 | 104 | 73 |
| glarus-nord | 1630 | 79 | 78 | steinhausen | 1708 | 52 | 50 |
| glarus-sued | 1631 | 11 | 11 | unteraegeri | 1709 | 48 | 48 |
| glarus | 1632 | 119 | 46 | uznach | 3339 | 0 | 0 |
| grellingen | 2786 | 57 | 41 | walchwil | 1710 | 39 | 39 |
| huenenberg | 1703 | 62 | 48 | weesen | 3316 | 55 | 55 |
| ilanz-glion | 3619 | 62 | 62 | wil-sg | 3427 | 127 | 122 |
| | | | | winterthur | 230 | 270 | 150 |
| | | | | zug | 1711 | 199 | 80 |

St. Gallen (3203) is at st.gallen.tlex.ch and has 175 texts, all structured **[agent]**.
