# Connector and fetch changes the Run 3 sources need

**What this covers.** It turns the Run 3 compatibility check (`compatibility_report.md`, `compatibility.csv`) into instructions for the corpus pipeline.
- **Line references** point to `main` at `159ac23`; each was re-read before this file was written. Open PR #51 changes `html.py` and `politeness.py`, so their line numbers will shift.
- **Source ids** are rows of `compatibility.csv`.

**Covered elsewhere; not repeated here:**

| Topic | Where |
|---|---|
| Gazette connector for the Amtsblattportal API | issue #39. Our 13 `amtsblatt_*` rows and the query facts verified on 2026-09-23 are added there as a comment. |
| robots.txt checks for PDFs, Crawl-delay for PDFs, robots groups that name our product token | PR #51 |
| Counting dropped attachments, and PDFs beyond `max_pdfs` | issue #11 |
| Cantonal law through LexFind / opencaselaw | issue #37 |
| Law-platform registration (`municipal_law` for a commune's own collection) | issue #44 |
| Adding sources to the manifest | issue #45 |

**Where a new connector plugs in** (the same four places each time):
- **Manifest literal:** `connector: Literal["fedlex", "html"]` (`src/swiss_grounding/corpus/manifest.py:21`).
- **Database check:** `check (connector in ('fedlex','html'))` (`src/swiss_grounding/corpus/schema.sql:49`).
- **Connector map in `corpus fetch`:** `connectors = {"fedlex": …, "html": …}` (`src/swiss_grounding/cli/corpus_source_commands.py:159-160`).
- **Dispatch:** `connectors[spec.connector].run(spec, known)`; discovered PDFs are then handed to the PDF connector (`src/swiss_grounding/corpus/fetch_stage.py:82-85`).

**What a connector returns:** `ConnectorResult(documents, unchanged_urls, gone_urls, errors, pdfs)`, where every document is a `ParsedDocument`:
- `source_id, url, language, work_key, title, sections, identifier, valid_from, valid_to, status, published_at, modified_at, extraction, retrieved_via, etag, last_modified` (`src/swiss_grounding/corpus/models.py:48-83`);
- each section is a `ParsedSection(align_key, breadcrumb, anchor, text, …)` (`models.py:29-44`).

---

## 1. JSON / REST records connector (`connector: json`): new

Tracked in #55.

### Why
- Structured sources cannot enter the corpus today.
- The old pipeline's `api` strategy has no successor. Non-HTML responses are skipped (`corpus/connectors/html.py:257`), and PDFs come only from links found by the HTML crawl (`fetch_stage.py:84-85`).

### What it unlocks

| Rows | Source | Data | Evidence |
|---|---|---|---|
| `sz-schulferien` | data.sz.ch (Opendatasoft), `ferienplan-kanton-schwyz` | 90 records, CC BY 4.0 | fetched with 0 errors by the old `ApiFetcher` on 2026-09-23 (`../fetch_tests/`) |
| `bl_schulferien` | data.bl.ch (Opendatasoft), dataset 13350 | 58 records | same test |
| `bl_gerichte`, `bl_plone_rest` | Kanton BL through the Plone REST API at `https://bl-api.webcloud7.ch/<path>`, because the public www.baselland.ch answers a Cloudflare 403 | courts, dogs, road office, holidays, conciliation | the user decided on 2026-09-23 to use this API; `../agent_reports/run3-a.md`, section BL |
| `zg_steuerbuch_plone` | Zug tax manual through `https://wissen-backend.webcloud7.ch/steuerbuch` (Plone REST, `@type: Book`) | 1,343 items through `@search` | orchestrator re-check, `../consolidated_report.md` §9 |
| `sh_ch_guidance`, `sh_cms_json` | sh.ch: pages are JavaScript shells; the content comes from `https://sh.ch/CMS/content?contentid=<id>&language=DE` | JSON: `data_post_content` (HTML), `data_permalink`, `data_publication_date` | orchestrator re-check, `../consolidated_report.md` §9 |
| issue #45 | the JSON datasets already listed there (OpenERZ calendars, OpenHolidays, geodata layers) | — | — |

### Proposed manifest config
Draft; the key names are suggestions.
```yaml
- id: sz_schulferien
  connector: json
  config:
    url: "https://data.sz.ch/api/explore/v2.1/catalog/datasets/ferienplan-kanton-schwyz/records?limit={size}&offset={offset}"
    paging: {style: offset, size: 100, total_path: total_count}   # style: offset | page | none
    records_path: results                  # dotted path to the list
    id_template: "{schuljahr}-{name_schule}"
    title_template: "Schulferien {schuljahr}: {name_schule} (Bezirk {bezirk})"
    text_template: "Schuljahr {schuljahr}, {name_schule}: Herbstferien {herbstferien_start} bis {herbstferien_ende}; …"
    url_template: null                     # the public page to cite; default: endpoint URL + "#" + id
    date_fields: {valid_from: null, published_at: null}           # dotted paths
    detail_url_template: null              # optional second GET per record (Plone item, sh.ch content, gazette XML)
    detail_html_path: null                 # e.g. "data_post_content": HTML to split into sections
    window: null                           # e.g. {start_offset_days: 14} → fills {start} in url
    robots: null                           # e.g. {exempt: true, reason: "documented public API; user decision 2026-09-23"}
```

### Behaviour
- **Paging.** Page until `total_path` is reached or a page comes back empty. Use the shared throttle and `request_with_backoff` (`corpus/connectors/politeness.py`).
- **Templates.** Render with `str.format_map`, as the old `ingest/fetchers/api.py:32` did, so nested fields such as `{meta[title][de]}` work.
  - Treat a missing key or a `None` value as a per-record error in `ConnectorResult.errors`.
  - Never let it abort the run; a `TypeError` on `None` did abort in the old code.
- **One document per record.**

  | Field | Value |
  |---|---|
  | `work_key` | `source_id:id` |
  | `identifier` | the record id |
  | `url` | `url_template`, or the endpoint URL plus `#id` |
  | `language` | the source's first language |
  | `sections` | one section, or several when `detail_html_path` is split with `ingest/html_sections.html_to_page` |

  Dates come from `date_fields`. Calendar-style evidence keeps its dates in the text: `corpus.document` has no event-date column (`corpus/schema.sql:62-86`).
- **Rolling windows.**
  - A record that drops out of the date window is **not** gone; do not report it in `gone_urls`.
  - Report a record as gone only when the API says so (for example a cancelled state).
- **robots.txt.**
  - The default is to check it like the HTML connector.
  - A documented API that robots.txt disallows needs an explicit per-source exemption with a stated reason. Examples: amtsblattportal.ch serves `Disallow: /`, and bl-api.webcloud7.ch's robots.txt answers 403, which the HTML connector treats as "host blocked".
  - Record the exemption in the manifest so review can see it.
- **Plone REST specifics** (BL and ZG).
  - `GET <path>` with `Accept: application/json` returns `items` (the children), `slblocks{…}.text.data` (HTML; order given by `slblocks_layout`) and `modified`.
  - Walk `items`, or use `@search?path.query=<path>&portal_type=…&b_size=…`.
  - Files come from `<file>/@@download/file`; hand them to the PDF connector as `DiscoveredPdf`.
  - Rewrite the cited URL from `https://bl-api.webcloud7.ch/<path>` to `https://www.baselland.ch/<path>`. The one-to-one path mapping is inferred from matching URLs (`../agent_reports/run3-a.md`); check it on a sample.
- **Content.** Holidays stay documents (ADR 0014). Topics are assigned per chunk by the describe stage, so no category config is needed.

### Tests (offline)
- **Fixtures:** one saved response each: an Opendatasoft page, a Plone item plus `@search`, and an sh.ch content JSON.
- **Unit tests:**
  - paging stops at `total_count` or an empty page;
  - nested templates render;
  - a missing or `None` field becomes a per-record error, not an exception;
  - dates parse;
  - the window never produces `gone_urls`;
  - robots: a disallowed host is refused unless it is exempt, and the exemption is logged.

---

## 2. PDF discovery gaps in the HTML connector: small

Tracked in #56.

### 2a. Fixed list of PDF URLs (`config.pdf_urls`)

**Today.** PDFs come only from `<a href>` links on pages the crawl stores:
- `page_meta` scans `soup.find_all("a", href=True)` (`corpus/connectors/html_meta.py:189-192`);
- `record()` keeps them only when the page is emitted and in scope (`html.py:316-326`);
- a `.pdf` start URL is skipped (`SKIP_SUFFIXES`, `html.py:30-31`).

**Unlocks:**
- `gl-pdfs` (GL tax guide, linked from no page);
- `sh_ferien`;
- `stadt_bern_sssb_hunde_abfall_parkieren`;
- `stadt_bern_sssb`: its 246 numbers are sitemap entries `dgn-lex_<nr>`, which map to `https://stadtrecht.bern.ch/lex-<nr>.pdf`; a generated list would work;
- a fallback for the 7 rows in 2b, and for the single-PDF pins flagged in `manifest_candidates.yaml` (`ow_pdfs`, `ur_pdfs`, `tg_gerichte_merkblaetter`).

**Proposal**
- `pdf_urls: [{url, title_hint?}]`, appended to `ConnectorResult.pdfs` as `DiscoveredPdf` with the source's first language.
- It must pass `pdf_allow_prefixes`, and robots.txt once PR #51 merges.
- It counts against `max_pdfs`.

**Test:** a source with `pdf_urls` and no start page produces the PDFs; a URL outside the prefixes is refused and reported.

### 2b. Links inside attributes that hold JSON

**Today.**
- `page_meta` reads only `<a href>` (`html_meta.py:189`).
- `extract_links` reads `href` attributes on any element (`ingest/html_sections.py:197-211`), but never URLs inside other attributes.
- Checked on the pages agent B saved (`compatibility_report.md` §2): both CMSs below yield 0 PDF links.

**Two CMSs keep their document lists in JSON attributes:**
- **i-web:** `<table class="icms-dt" data-entities="…">`. The JSON rows carry `_dokumentList` → `/_doc/<id>` (a PDF) plus `_nummer` and `_rechtsgueltigkeit`.
- **stadt-zuerich.ch:** `<stzh-datatable rows="…">`, with the PDF under `/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/…`.

**Unlocks 7 rows now:** `stadt_thun_iweb`, `stadt_thun_abfall_parkieren`, `stadt_schaffhausen_iweb`, `stadt_schaffhausen_rs`, `ur_iweb_tables`, `nw_iweb_tables`, `nw-pdfs`. It also unlocks the Zürich Amtliche Sammlung under the already-declared `zuerich_city`.

| Collection | Size |
|---|---|
| Thun | 127 rows, 0 about dogs |
| Stadt Schaffhausen | 215 rows |
| UR | 444 decisions + 1,479 gazette issues |
| NW | 558 decisions + 1,748 publications |
| Zürich AS | 791 entries, 622 in force |

Evidence: the orchestrator re-counted Thun and Schaffhausen; the other counts come from the agent reports.

**Proposal**
```yaml
json_link_attributes:
  - {selector: "table.icms-dt", attribute: "data-entities"}
  - {selector: "stzh-datatable", attribute: "rows"}
```
- Parse the attribute as JSON and collect every string that is a URL or an absolute path.
- Make each one absolute against the page URL.
- Feed them through the same PDF check (`.pdf` suffix or `pdf_link_patterns`, for example `/_doc/\d+`) and the same scope checks.
- Optionally also queue non-PDF links as pages.

**Test:** fixtures from a saved Thun or Schaffhausen page. Expect 127 or 215 `/_doc/` links respectively.

### 2c. The page language loses to a conflicting language link

**Today.**
- A page's own entry among its language alternates wins over `<html lang>`. A page whose language is not declared is not emitted (`corpus/connectors/html_page.py:52-58`).
- `record()` returns before collecting PDFs when `page.emit` is false (`html.py:318-319`).

**Case:** `https://www.neuchatelville.ch/votre-commune/reglementation` is French (`<html lang="fr">`), but its language links name it as the German version. The page is therefore dropped, and its 79 regulation PDF links with it (offline test, `compatibility_report.md` §4).

**Proposal:** when the self-alternate and `<html lang>` disagree and only `<html lang>` is declared, trust `<html lang>`. Alternatively, collect PDF links from pages that are not emitted.

**Unlocks:** `neuchatel_ville_reglementation` without the unverified `/fr/` start-URL workaround in `manifest_candidates.yaml`.

---

## 3. Smaller fetch fixes (checklist)

Tracked in #57.

- [ ] **TLS per source.**
  - `corpus_http` builds one client with only headers and a timeout (`cli/corpus_source_commands.py:46-47`).
  - www.schulen-aargau.ch fails certificate verification because its chain is incomplete.
  - Add a per-source `ca_bundle`, or a `verify` option with a stated reason.
  - Unlocks `ag_schulferien`; that entry sits in section 2 of `manifest_candidates.yaml`.
- [ ] **PDF title order.**
  - The metadata title wins over the link text: `title = meta_title or title_hint or file name` (`corpus/connectors/pdf.py:64-65`).
  - In 21 saved PDFs that have a metadata title, 11 are junk: "Leer", "AMT FÜR EDV", `.indd` and `.xlsx` names, a stale school year, and a JU tariff titled with the office's street address. Each would override a good link text.
  - Prefer the link text when the metadata looks like a file or template name.
  - URL-decode the file-name fallback (`Schulferien%20202627-203031.pdf`).
  - Evidence: `evidence/`, `scripts/pdf_titles.py`.
- [ ] **Retry connection errors.**
  - `request_with_backoff` retries only 429 and 503 (`corpus/connectors/politeness.py:21-22,118-127`). The corpus client has no transport retries.
  - gerichte-zh.ch drops connections now and then (`RemoteProtocolError`, twice in three attempts on 2026-09-23).
  - Retry transport errors with backoff; the old client used `HTTPTransport(retries=2)`.
- [ ] **PDF size limit per source.** `MAX_PDF_BYTES = 30_000_000` (`pdf.py:37`). TI's `Istruzioni_PF_2025.pdf` is 43.7 MB and aborts (it is under the declared `ti_canton`).
- [ ] **Manifest validator.**
  1. Reject a start URL outside `allow_prefixes`: today the crawl skips it silently (`html.py:245-248` via `_allowed`), while the validator only checks that the keys exist (`manifest.py:29-32`).
  2. Warn about or reject unknown `config` keys, because `config: dict[str, Any]` (`manifest.py:24`) ignores misspelled keys.
- [ ] **Sitemap host rewrite.**
  - Child sitemaps are fetched exactly as the index lists them (`corpus/connectors/sitemap.py:127`).
  - ne.ch's index lists `http://ne-prod-admin.ne.ch/sitemap.xml?page=N`, a host that does not resolve. The same paths on `https://www.ne.ch` return 5,000 + 3,518 URLs.
  - Add an optional `sitemap_rewrite: {from, to}`.
  - Unlocks `ne_sitemap_rewrite`. The NE entries already work from their start URLs.

---

## 4. Connectors for single sources: low priority, listed so they are not lost

| Row | Kind | What it needs |
|---|---|---|
| `fr_ics_holidays` | ICS | `https://www.fr.ch/document/<id>` (`text/calendar`); 3 regional calendars per school year, 11 events per file. Holidays stay documents (ADR 0014): one document per calendar, one section per event. |
| `chaux_de_fonds_reglementation` | POST JSON | `POST https://www.chaux-de-fonds.ch/Api/Page.svc/detail` with body `{"page":"/rapports-et-reglements/reglementation/<theme>"}` → `DetailResult.Content` (HTML) → PDFs at `/rapports-et-reglements/reglementation/Documents/<nr>.pdf`. 9 themes, 175 PDFs (agent D). |
| `sh_lexican_steuer` | lexiCan | Get a session cookie from the project page, then `/api/OutlineApi/full?projectId=KArfO5bFd0CkaahGqsNmbQ` (168 nodes, 143 articles) → `/api/ArticlesApi/content?articleId=…` → `/Files/Download?…` PDF. |

---

## 5. Decisions needed before merging entries (not code)

- **Tier.**
  - `manifest_candidates.yaml` puts 9 entries in tier 1 (inside ADR 0009's scope), 63 in tier 2 and 3 in tier 3.
  - `corpus fetch` defaults to `--tier 1` (`cli/corpus_source_commands.py:148`).
  - The serving-track plan limits served places to 6 cantons and 7 municipalities. That reading is inferred from the plan, not from code.
- **Authority for three city law collections** (`lugano_legislazione`, `neuchatel_ville_reglementation`, `vernier_reglements`).
  - `municipal_law` follows #44's rule: "a commune's own compilation".
  - It holds only once the collection is registered in #44's host table.
  - All three sit on the city's general website, so registration needs a path prefix, not just a host.
- **fo.fr.ch (FR Feuille officielle).**
  - robots.txt allows `*` but blocks ClaudeBot, anthropic-ai, GPTBot and others by name.
  - Even after PR #51 our product token `swiss-grounding` falls under `*`, so the crawler would fetch it.
  - Recommended path: ask the Chancellerie (editor) or media f (delegated publisher). The entry stays out of `manifest_candidates.yaml` until then.
