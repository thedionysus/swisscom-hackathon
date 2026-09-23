# Run 3: data endpoints confirmed on 2026-09-23

These are the machine-readable endpoints the Run 3 agents found and used. Every row names who verified it:
- **orchestrator** means the endpoint was re-requested independently (see `consolidated_report.md` §9).
- **agent X** means only that agent requested it. The request and its sample are in `agent_reports/run3-x.md`.

The agent report is the authority on details.

## Gazettes: Amtsblattportal (eSHAB, SECO)
Decision (2026-09-23): use this API (see `consolidated_report.md` §2).

| Endpoint | Format | Notes | Verified by |
|---|---|---|---|
| `GET https://amtsblattportal.ch/api/v1/publications?publicationStates=PUBLISHED&tenant=kab<xx>&rubrics=<code>[,<code>…]&publicationDate.start=YYYY-MM-DD&pageRequest.page=N&pageRequest.size=M` | JSON `{content:[{meta:{…}}], total}` | Returns **401 without `publicationStates=PUBLISHED`**. Page size: default 100, maximum 2,000 (`ogd_lists_assessment.md` B.9). ZG with its 12 own codes → 2,213 | orchestrator |
| `GET …/api/v1/publications/xml?…` (same query), `…/csv?…` | XML with `<total>`, or CSV | Bulk export. BA-SO from 1 to 23 Sept → 248 | orchestrator (xml), agent A (csv) |
| `GET …/api/v1/publications/<id>/xml` | XML with the notice text | e.g. "Handänderung, Härkingen … Grundbuch Nr. 236" | agent A, agent B |
| `GET …/api/v1/tenants` | JSON list | 29 tenants. `external: true` for kabfr, kabvd, kabne, kabge, kabju (and kablu, kabur, kabgl) | orchestrator (Romandie flags), agent B |
| `GET …/api/v1/rubrics` | JSON list with `code`, `tenantId` | Own rubric codes per tenant. 14 cantons own rubrics; GR owns only AA-GR | orchestrator (from agent B's saved copy) |
| Filter `cantons=XX` | – | Includes federal SHAB notices: TI 356 of 500 are `shab` | orchestrator |
| Filter `tenants=` | – | **Ignored**: returns the same total as no filter | orchestrator |

`meta` fields: `id`, `publicationNumber`, `primaryTenantCode`, `cantons`, `publicationDate`, `rubric`, `subRubric`, `title{de,fr,it,en}` and `registrationOffice{displayName, municipalityId}` (a BFS number when present) [agent B].

**Checked by the orchestrator on 2026-09-23:**
- In every notice sampled, the title is filled in all four languages.
- The 14-day volume per canton is at most 551 (ZH), so one request with `pageRequest.size=2000` holds a whole window.

**This works with the existing `api` fetcher. No new fetcher is needed.**
- `ready_sources/amtsblatt_<xx>.yaml` holds 13 cantons: AR, BE, BL, BS, NW, OW, SH, SO, SZ, TI, VS, ZG, ZH.
- Each uses `publicationDate.start={start}` with `start_offset_days: 14`, `records_path: content`, `id_template: "{meta[id]}"` and `title_template: "{meta[title][de|fr|it]}"`.
- Live test: all 13 returned documents (ZH 551, VS 490, SO 354, BE 337, TI 319, BL 302, BS 226, SZ 205, ZG 155, SH 40, NW 39, OW 36, AR 32), with 0 errors.
- GR is left out: its one own rubric had no notices in the last 14 days.

**Limits:**
- There is no notice text; that needs a per-notice `/xml` request.
- `event_date` stays empty, because the fetcher reads only top-level fields.
- Each document's URL is the API feed.

Robots and personal data:
- robots.txt is `Disallow: /` on amtsblattportal.ch and every checked tenant front end [orchestrator].
- There are 732 ZH notices titled "Todesanzeige" [orchestrator].

## Other gazettes, per canton

| Canton | Endpoint | Format | Access | Verified by |
|---|---|---|---|---|
| VD | `https://www.faovd.ch/rubrique/<rubric>/` | HTML | open; no robots.txt | orchestrator (robots), agent D |
| JU | `https://rsju.jura.ch/fr/Sommaire/Journal-officiel.html` → weekly PDFs | PDF with text layer | open; no Disallow | orchestrator (robots), agent D |
| FR | `https://fo.fr.ch/archive/<year>/<no>/<rubric>` | HTML | `*` allowed; ClaudeBot, anthropic-ai, GPTBot and others blocked by name. **Decision: find another way** | orchestrator |
| UR | `https://www.ur.ch/amtsblatt`: i-web table (1,479 issues) → `/_doc/<id>` PDF | HTML table + PDF | open | orchestrator (robots), agent B |
| AG | `https://amtsblatt.ag.ch/ekab/<nr>/publikation/` | HTML (TYPO3) | robots.txt disallows `/publikationen/` and `/ekab/` | orchestrator |
| GR | `https://www.kantonsamtsblatt.gr.ch/publikationen/` (DIAM) | HTML | robots.txt disallows `/publikationen/` and `/ekab/` | orchestrator |

## Cantonal content APIs

| Endpoint | Format | Serves | Verified by |
|---|---|---|---|
| `https://bl-api.webcloud7.ch/<path>` with `Accept: application/json`, `@search?SearchableText=&path.query=&portal_type=&b_size=`, `<file>/@@download/file` | Plone REST JSON: `slblocks[*].text.data` (HTML), `items`, `modified` | All of Kanton BL (courts, dogs, road office, holidays, conciliation) behind the www.baselland.ch Cloudflare wall. **Decision: use it** | orchestrator (root), agent A |
| `https://wissen-backend.webcloud7.ch/steuerbuch` plus `@search` | Plone REST JSON; Book, 1,343 items | ZG Steuerbuch | orchestrator |
| `https://sh.ch/CMS/content?contentid=<id>&language=DE` | JSON: `data_post_content` (HTML), `data_permalink`, `data_publication_date` | Every sh.ch page (the HTML pages are JS shells) | orchestrator |
| `https://sh.lexican.cloud`: GET the project page for the session cookie, then `/api/OutlineApi/full?projectId=KArfO5bFd0CkaahGqsNmbQ`, `/api/ArticlesApi/content?articleId=…`, `/Files/Download?…` | JSON outline (168 nodes, 143 articles) + PDF | SH tax manual (Dienstanleitung) | orchestrator (outline), agent C |
| `https://steuerpraxis.tg.ch/sitemap.xml` (7 versions; newest `/steuerpraxis/2026-09/`) | sitemap + server HTML | TG tax practice (3,866 URLs; 558 in 2026-09) | orchestrator |
| `https://rechtsprechung.tg.ch/sitemap.xml` | sitemap + server HTML | TG decisions (6,350 URLs) | orchestrator |
| `https://www.ne.ch/sitemap.xml?page=1` and `?page=2`. The index points at `ne-prod-admin.ne.ch`, which does not resolve; rewrite the host | sitemap | All NE pages (8,518) | orchestrator |
| `https://api-justsearche.vs.ch/api/search/?offset=&limit=&sort=_score`, `/api/documents/{id}/file/` | JSON `{count, offset, facets, results[]}` | VS court decisions (5,006) | orchestrator (search), agent E |
| `https://www.vs.ch/web/communes/-/<slug>` | HTML (BFS number, website, commune judge) | 122 VS communes | agent E |
| `https://www.fr.ch/document/<id>` (e.g. 508696) | `text/calendar` ICS | FR school holidays, 3 regional calendars × school years | orchestrator |
| `https://www.ge.ch/document/39777/telecharger` | ICS | GE school holidays | agent D (g5) |
| Opendatasoft `https://data.sz.ch/api/explore/v2.1/catalog/datasets/ferienplan-kanton-schwyz/records` | JSON | SZ holidays, 90 records, CC BY 4.0. **Fetched with the repo's ApiFetcher: 90 documents, 0 errors** | orchestrator |
| Opendatasoft `https://data.bl.ch/…/datasets/13350/records` and `…/10510/records` | JSON | BL holidays (58; **ApiFetcher: 58 documents, 0 errors**) and BL communes (86, with `website`) | orchestrator |
| Opendatasoft `https://data.bs.ch/…/datasets/100397/records` | JSON | BS holidays | g5 (agent A cited) |
| `https://gerichte.lu.ch/recht_sprechung/lgve/Ajax?EnId=<id>` | HTML fragment per decision | LU LGVE decisions | agent B |

## City law

| City | Endpoint | Format | Verified by |
|---|---|---|---|
| Bern | `https://stadtrecht.bern.ch/sitemap.xml` (2,593 locs, 246 `dgn-lex_` numbers) → `https://stadtrecht.bern.ch/lex-<nr>.pdf` or `.docx` | PDF with text layer / DOCX | orchestrator |
| Zürich | Amtliche Sammlung group pages `/amtliche-sammlung/<n>/<nnn>.html`; detail pages carry `<stzh-datatable rows="…">` JSON (AS number, Inkrafttreten, PDF link) | HTML + embedded JSON + PDF | agent A |
| Lausanne | `https://www.lausanne.ch/apps/actualites/index_recueil.php` → `Next/serve.php?id=N&kind=recueil` | HTML list + PDF (193) | orchestrator (count) |
| La Chaux-de-Fonds | `POST https://www.chaux-de-fonds.ch/Api/Page.svc/detail`, body `{"page":"/rapports-et-reglements/reglementation/<theme>"}` → `/rapports-et-reglements/reglementation/Documents/<nr>.pdf` | JSON `DetailResult{Content,…}` + PDF | orchestrator (API, 9 themes), agent D (175 PDFs) |
| Genève (Ville) | `https://www.geneve.ch/autorites-administration/administration-municipale/reglements-municipaux?page=0…24` → `…/lc<nr>-<slug>` (serves the PDF) | HTML list + PDF | orchestrator (pages) |
| Neuchâtel | `https://www.neuchatelville.ch/votre-commune/reglementation` (+ `/anciennes-communes/reglementation-*`) | HTML list + PDF (79) | orchestrator (count) |
| Thun, Schaffhausen (and UR/NW/OW publication lists) | i-web `<table class="icms-dt" data-entities="…">` JSON → `/_doc/<id>` PDF | HTML-embedded JSON + PDF | orchestrator (Thun 127, Schaffhausen 215) |
| Lugano | `https://www.lugano.ch/la-mia-citta/amministrazione/legislazione.html` → `/law/<id>/<slug>` | HTML list + PDF (122) | orchestrator |

## Law platforms (legal basis of fees, dogs, holidays)

| Platform | Endpoint | Verified by |
|---|---|---|
| LexWork (19 cantons + intlex) | `/api/{lang}/texts_of_law/{nr}`, `/show_as_json`, `/api/{lang}/texts_of_law/lightweight_index`. Some hosts redirect: sh.clex.ch → rechtsbuch.sh.ch | orchestrator (AG 221.150 `abrogated: true`; SH 173.200), brief v4 |
| VD BLV | `https://prestations.vd.ch/pub/blv-publication/api/actes/CONSOLIDE?id=<uuid>&cote=<nr>` → `api/actes/<id>/html` (robots.txt answers 403) | agent D; orchestrator (robots) |
| NE RSN | `https://rsn.ne.ch/DATA/program/books/rsne/pdf/<nr>.pdf`. robots.txt: `Disallow: /` + `Allow: /DATA/`; Python's `robotparser` denies `/DATA/` | orchestrator |
| GE silgeneve | `https://silgeneve.ch/legis/program/books/RSG/pdf/rsg_<nr>.pdf` | agent D |
| JU RSJU | `https://rsju.jura.ch/…` (viewdocument, download=1) | agent D |
| SZ | SRSZ PDFs on sz.ch (`/public/upload/assets/<id>/<nr>.pdf`), found through LexFind entity 19 | agent B |

## Decision portals (opencaselaw already covers them; listed for completeness)

| Portal | Pattern | Verified by |
|---|---|---|
| opencaselaw Atom | `https://mcp.opencaselaw.ch/api/atom/{court}.xml` (50 entries; dockets contain raw spaces) | orchestrator (GR) |
| entscheidsuche scrapers | `github.com/entscheidsuche/NeueScraper`: AGPL-3.0, 57 spiders, portal and platform for all 26 cantons | orchestrator (licence), agent E (table) |
| Omnis FindInfo | ZH VGR `vgrzh.djiktzh.ch/cgi-bin/nph-omniscgi.exe?…Schema=ZH_VG_WEB…`; BS `rechtsprechung.gerichte.bs.ch`; SO `gerichtsentscheide.so.ch` (needs a cookie jar); TI `www.sentenze.ti.ch`; VD `jurisprudence.vd.ch` (robots.txt `Disallow: /`); NE `jurisprudence.ne.ch` | agents A, D, E; orchestrator (VD robots) |
| Tribuna (JavaScript apps) | BE `*.apps.be.ch/tribunapublikation/`; FR `publicationtc.fr.ch`; JU `jurisprudence.jura.ch`; GR `entscheidsuche.gr.ch` (GWT-RPC); SZ `gerichte.sz.ch`; ZG `obergericht.zg.ch` (cookie check) | agents A, B, D, E |
| Down or login | AG `agve.weblaw.ch` (503, re-checked); `decwork.ag.ch` (login) | orchestrator |
