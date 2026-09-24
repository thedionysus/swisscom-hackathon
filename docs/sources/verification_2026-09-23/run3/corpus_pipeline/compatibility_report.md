# Run 3 sources and the new corpus pipeline: what fits, what doesn't

**Inputs**
- Run 3: commit c93ae3f on remote branch `sources/run3-discovery`. That is 108 ready YAMLs and 148 catalogue rows.
- New pipeline: `origin/main` at 159ac23. Every `path:line` below is in that worktree unless another file is named.

**How it was done**
- Everything was offline: no source website was contacted, no `corpus` command was run, no database was touched.
- Behaviour was checked two ways:
  - by reading the code;
  - by running the pipeline's own functions on the pages and PDFs the Run 3 agents saved (`scratchpad/run3-{a..e}`), and on mocked HTTP.
- The scripts and outputs are in `scratchpad/newpipe/`.
- Labels: **[verified]** means a tool output from this session; **[inferred]** means reasoning without such an output.

---

## 1. Summary

**Status of the 148 catalogue rows** (`run3_compatibility.csv`)

| Status | Rows | From old strategy |
|---|---:|---|
| convertible now | 79 | 53 html_crawl, 17 pdf, 9 with no old strategy (pdf-index, gazette and sitemap cases) |
| convertible with small pipeline change | 13 | 7 pdf, 6 with no old strategy |
| needs new connector | 25 | 15 api, 2 superseded api, 1 plone_rest, 1 sh_cms_json, 6 with no old strategy |
| already declared | 20 | 9 html_crawl, 7 pdf, 4 with no old strategy |
| not a document source | 10 | commune directories (resolver inputs) |
| blocked: decision pending | 1 | fo.fr.ch |

The sixth status is my addition. fo.fr.ch fits none of the five: the crawler would technically accept it, but the user's decision on it is still open.

**By connector**
- **html: 102 rows.**
  - 79 are converted now.
  - 20 fall inside a declared source.
  - 2 have entries that need a pipeline fix first.
  - 1 is fo.fr.ch.
- **unsupported: 36 rows.**
- **n/a: 10 rows.**

**Manifest**
- 81 rows map onto **75 candidate entries**:
  - 74 are in section 1 (convertible now);
  - 1 is in section 2 (valid config, blocked by TLS).
- Tiers: 9 in tier 1, 63 in tier 2, 3 in tier 3.
- The entries cover 24 cantons. Only BL and SH are missing.
- **Validation** [verified]:
  - `load_manifest` passes on the 75 candidates.
  - Merged with `declared-scope.yaml` (27 sources), all **102 sources pass**, with 0 prefix clashes and 0 duplicate ids.

**Key findings**
- **Only two connectors exist:** `fedlex` and `html` (`corpus/manifest.py:21`).
  - PDFs are fetched only when the html connector finds them as links (`corpus/fetch_stage.py:84-85`).
  - There is no JSON, ICS, XLSX or POST support.
  - So the 13 gazettes and 2 holiday datasets cannot be ingested.
- **Fixed PDF lists do not exist in the new schema.**
  - I rebuilt them as "crawl only the page that links the PDF, plus a `pdf_allow_prefixes` pinned to the PDF's folder or URL".
  - For every converted PDF source, the pipeline's own `page_meta`, run on the saved parent page, finds the PDF [verified].
- **Most old blockers are gone:**
  - The 4 LU sources work with `content_selector: "#mainContent"`: 21 of 21 saved LU pages give sections [verified].
  - JU's HEAD-404 is gone: the new connector sends GET only.
  - The i-web and ar.ch "Hauptinhalt"/"Inhalt" titles are gone.
- **Two blockers remain:**
  - TLS at schulen-aargau.ch: there is no verify or CA option.
  - PDFs ignore Crawl-delay.
- **Possibly most important, and outside this task's scope:**
  - At 159ac23 the server's search reads the old `public.chunk/document/source` tables (`retrieval/search.py:94-102`).
  - Nothing under `retrieval/`, `mcp_server/` or `app.py` mentions `corpus.`.
  - So sources ingested by the new pipeline are not yet what the server answers from [verified by grep; whether a later branch switches it: not checked].

---

## 2. Manifest schema essentials

### Fields of `SourceEntry` (`corpus/manifest.py:12-25`, `extra="forbid"` at :13)

| Field | Required | Allowed values |
|---|---|---|
| `id` | yes | `^[a-z0-9_]+$` (:15). Run 3 ids with `-` fail this, so I replaced `-` with `_` |
| `name`, `publisher` | yes | free text (:16-17). `publisher` goes into the description prompt (`describe.py:45,153`) |
| `authority` | yes | `federal_law`, `cantonal_law`, `municipal_law`, `official_info`, `institutional` (:18) |
| `level` | yes | `federal`, `cantonal`, `municipal` (:19) |
| `extent_id` | yes | any string at load time. The DB foreign key needs it in `public.location` (`corpus/schema.sql:48`); `check-manifest` checks this against the DB (`cli/corpus_source_commands.py:123-131`) |
| `connector` | yes | `fedlex` or `html` (:21) |
| `tier` | yes | 1–3 (:22). `select_sources` keeps sources with tier ≤ the requested tier (:123-131). `corpus fetch` defaults to `--tier 1` (`corpus_source_commands.py:148`) |
| `languages` | yes | at least 1 of `de, fr, it, en, rm`, no duplicates (:23, :36-38) |
| `config` | no | a free dict (:24). **Unknown keys are silently accepted** |
| `retrieved_via` | no | provenance string (:25) |

**Manifest-level rules**
- `version` and `sources` (:87-91).
- Ids must be unique (:93-99).
- **URL prefixes must be disjoint across sources.** Each source's `allow_prefixes` plus `pdf_allow_prefixes` must not be a string-prefix of another source's (:101-116).

**Connector requirements**
- `html` needs non-empty `start_urls` and `allow_prefixes` (:29-32).
- `fedlex` needs `sr_numbers` (:34-35).

### `html` config keys

| Key | Default | Checked at load | Meaning |
|---|---|---|---|
| `start_urls` | required | non-empty only | Placed first in the crawl queue (`crawl_queue.py:14-20`). A start URL outside `allow_prefixes`, or ending in a skipped suffix, is **silently skipped** (`html.py:196-199,247`). The loader does not check this; my converter does |
| `allow_prefixes` | required | non-empty only | **`str.startswith` on the full absolute URL**: scheme, host, path and query, case-sensitive (`html.py:186-188`). A redirect whose target is out of scope is dropped as "redirected outside scope" (`html.py:279-285`). Old rule for comparison: same host plus path prefix (`ingest/fetchers/html_crawl.py:86-94` at ec2d7ed) |
| `pdf_allow_prefixes` | = `allow_prefixes` | no | A discovered PDF is kept only inside these (`html.py:241-242,322-326`) |
| `pdf_link_patterns` | none | regex compiles (:66-71) | Marks links as PDFs beyond the `.pdf` suffix; the suffix test drops the query string first (`html_meta.py:150-151`). Matching links are never crawled as pages (`html.py:190-194`) |
| `max_pages` | 300 | no | Counts every fetched URL, and also caps sitemap seeds (`html.py:32,236,240,245-250`) |
| `max_pdfs` | **50** | no | First N PDFs in discovery order (`html.py:33,322-326`). So set `max_pdfs: 0` explicitly for sources without PDFs |
| `content_selector` | `<main>`, `<article>`, `[role=main]`, `<body>` | CSS compiles (:75-84) | Content root (`html_sections.py:30,43-51`) |
| `language_links_selector` | none | CSS compiles | Language-switcher alternates (`html_meta.py:81-92`) |
| `sitemap_urls` | none | absolute URLs (:72-74) | Seeds from sitemaps and sitemap indexes (`sitemap.py`) |
| `sitemap_include` | all | regex compiles | `re.search` on each page URL (`sitemap.py:129`). Seeds must also pass `allow_prefixes`, skipped suffixes and robots (`html.py:208-212`). **No host rewrite, no exclude list**, at most 200 sitemap files (`sitemap.py:26,102,127`) |
| `delay_seconds` | 0 | number ≥ 0 (:55-60) | Per-source minimum delay for pages and sitemaps (`html.py:238,169`), **not for PDFs** |

### The questions you asked about the connectors

- **Fixed PDF URL list: not supported.**
  - `PdfConnector.run_pdfs` only receives `DiscoveredPdf`s from the html result (`fetch_stage.py:84-85`, `pdf.py:148`).
  - A PDF given as a start URL is skipped (suffix check), or fetched and discarded as non-HTML (`html.py:257`).
- **Sitemap filtering: yes** (`sitemap_include`). **Host rewrite: no.**
- **JSON, ICS, XLSX, POST: none.**
  - Non-HTML responses are skipped (`html.py:257`); the PDF connector rejects non-PDF content types (`pdf.py:128-145`).
  - The only embedded JSON read anywhere is the federal CMS `__NUXT_DATA__`, and only for language alternates (`html_meta.py:95-147`).
  - Links inside JSON-valued attributes are **not** seen: `page_meta` reads `<a href>` (`html_meta.py:189`) and `extract_links` reads real `href` attributes (`html_sections.py:197-211`). This covers i-web `data-entities` and Zürich's `<stzh-datatable rows>` [verified on saved pages: 0 PDF links found].

---

## 3. Overlap with `declared-scope.yaml`

Method: every Run 3 URL (start pages, allowlists, PDF URLs, API URLs, catalogue entry points) was tested against every declared `allow_prefixes`/`pdf_allow_prefixes`, in both directions [verified, `convert_run3.py` → `conversion_report.json`]. **20 rows are already declared. Do not add them.**

| Declared source (its prefix) | Run 3 rows inside it |
|---|---|
| `vd_canton` (`/population`, `/formation`, `/mobilite`, `/fileadmin/`) | vd-dogs, vd-school-holidays, vd-san, vd-tax-instructions |
| `ge_canton` (`https://www.ge.ch/`, the whole host) | ge-ocv, ge-ocv-fees |
| `ti_canton` (`https://www4.ti.ch/`, `…/fileadmin/`) | ti_giudiziario_guidance, ti_uvc_cani, ti_sezione_circolazione, ti_calendario_scolastico, ti_dc_istruzioni_pf |
| `gr_canton` (`https://www.gr.ch/DE/`) | gr_alt_hundewesen, gr_stva, gr_schulferien, gr_stv_wegleitung, gr_steuer_praxis_pdfs |
| `zuerich_city` (`https://www.stadt-zuerich.ch/de/`) | stadt_zuerich_as, stadt_zuerich_as_hunde_abfall_parkieren |
| `lausanne_city` (`https://www.lausanne.ch/`) | lausanne_recueil |
| `geneve_city` (`https://www.geneve.ch/`) | geneve_ville_reglements |

**Declared entries that miss content Run 3 found.** These are manifest edits, for the colleague to decide:
- **`ge_canton`**
  - It has no `pdf_link_patterns`, so `/document/<id>/telecharger` PDFs are fetched as pages and discarded as non-HTML (`html_meta.py:150-151`, `html.py:257`).
  - Suggested pattern: `^https://www\.ge\.ch/document/\d+/telecharger$`.
- **`lausanne_city`**
  - Add the start URL `/apps/actualites/index_recueil.php`.
  - Add the pattern `serve\.php\?id=\d+&kind=recueil`.
  - Raise `max_pdfs` to about 200.
  - With that pattern, 193 PDF links are found on the saved page [verified].
- **`geneve_city`**
  - Add the start URL `/autorites-administration/administration-municipale/reglements-municipaux`.
  - Add the pattern `^https://www\.geneve\.ch/administration-municipale/reglements-municipaux/lc\d+`.
  - The saved list links `…/lc21111-…` pages [verified]. That they serve the PDF comes from `endpoints.md:82`.
- **`gr_canton`**
  - The tax-practice collection (88 PDFs) needs its page as a start URL and `max_pdfs` above 60.
- **`zuerich_city`**
  - The Amtliche Sammlung PDFs need the JSON-attribute change (§5) and `pdf_allow_prefixes …/dam/web/de/politik-verwaltung/politik-recht/amtliche-sammlung/`.
- **`ti_canton`**
  - `Istruzioni_PF_2025.pdf` is 43.7 MB, above `MAX_PDF_BYTES` = 30 MB (`pdf.py:37,134-143`), so the download aborts.

**Hosts shared without overlap**
- www.zh.ch: `zh_verwaltungsgericht` beside `zh_canton`.
- www.vd.ch: `vd_justice` beside `vd_canton`.
- www.lugano.ch: `lugano_legislazione` owns `/la-mia-citta/…/legislazione` and `/law/`.
- The validator accepts all three. Parallel crawls of one host share the per-host throttle (`politeness.py:1-6,37-58`).

---

## 4. Conversion results and validation

**Files**
- `run3_manifest_candidates.yaml`: 75 entries; one comment per entry names the Run 3 rows and the evidence.
- `run3_compatibility.csv`: the columns you asked for, plus `manifest_id`.
- `conversion_report.json`: overlaps and per-entry checks.
- Generated by `convert_run3.py` and `make_csv.py`, with per-source decisions in `run3_decisions.py`.

**Values I chose**
- **id:** the Run 3 id with `-` replaced by `_`.
- **level:** from the extent (`CH-XX` is cantonal, `CH-XX-<BFS>` is municipal).
- **languages:** `fetch_config.language` (default `de`).
- **tier:**
  - 1 for extents inside ADR 0009's declared scope (ZH, BE, VD, GE, TI, GR and the seven declared communes). That is 9 entries: `zh_verwaltungsgericht`, `gerichte_zh_themen`, `be_zsg_themen`, `be_vgb_themen`, `be_schulferien_volksschule`, `vd_justice`, `ge_justice_themes`, `gr_justiz_guidance`, `lugano_legislazione`.
  - 2 for other cantons and cities: "moves to a lower priority tier" (`docs/adr/0009-declared-scope.md:18`).
  - 3 for bulk or gazette collections: `tg_rechtsprechung` (6,350 pages), `ju_journal_officiel`, `vd_faovd`.
  - Tier 1 is what `corpus fetch` crawls by default, so merging adds these 9 to the default crawl.
- **publisher:** the canton written as the declared entries do (e.g. "Kanton Bern"), or the court or office named in the Run 3 name.
- **authority:**
  - `official_info` everywhere except 3 municipal law collections, which get `municipal_law`: `lugano_legislazione`, `neuchatel_ville_reglementation`, `vernier_reglements`.
  - This follows your authority rule (memory, 2026-09-22: legal text from an official collection gets a law authority). It departs from the Run 3 YAMLs, which say `official_info`.
- **max_pages:** Stage 0 sitemap URLs under each prefix [verified: `prefix_counts.py`], plus headroom (about 25%, at least 10). Where no sitemap exists, from the reports. For single-page PDF parents, 1–4.
- **max_pdfs:** 0 unless the source is about PDFs; 25 entries collect PDFs (sum 799).
- **content_selector:** only where an agent report documents the container:
  - `#maincontent` on sg.ch (`run3-c.md:26,48`);
  - `#mainCol` on ar.ch (`:212,224`);
  - `#content` on ai.ch (`:290`).
  - ne.ch's documented `<main>` is already the default root.
  - **Exception: LU `#mainContent`.** No report documents it. I found it in the saved LU pages, and it is flagged in the YAML for review.
- **delay_seconds 5:** for sz.ch, gl.ch and glarus-nord.ch. The first two come from `run3-b.md:93,186` ("5 s spacing gave 0 × 429"); glarus-nord.ch is [inferred], the same CMS.
- **Sitemap seeding:** on 7 entries, using Stage 0 or `endpoints.md` URLs. The seeds were checked against the saved sitemaps: 249, 119, 390, 195, 137, 559 and 6,350 URLs accepted [verified].
- **VS sources get `max_pdfs: 0`:** vs.ch robots.txt disallows `*.pdf`, and PDF downloads are never checked against robots.txt (see §7d).

**How the 31 `pdf` sources were converted**
- Each became, or was folded into, an html entry:
  - start = the page that links the PDF;
  - `allow_prefixes` = that page;
  - `pdf_allow_prefixes` = the PDF folder or exact URL;
  - plus `pdf_link_patterns` for links without `.pdf`: `.pdf/download` (ai.ch), `/document/\d+` (fr.ch), `/law/\d+/` (Lugano), `/_doc/\d+` (i-web).
- **Folds**, forced by the disjoint-prefix rule because the parent page sits inside another source:
  - `ai_ferienplan` into `ai_guidance`;
  - `sg_gerichte_kostenmerkblatt` into `sg_gerichte_info`;
  - `zg-pdfs` into `zg_hunde_ferien`;
  - `ju-court-tariff` into `ju_justice`.
- **Merges:**
  - `sg_steuerbuch` and `sg_steuerbuch_pdfs` into `sg_steuerbuch` (248 PDFs);
  - `lugano_legislazione` and `lugano_legislazione_all` into `lugano_legislazione` (122 PDFs).
- **Offline proof on the saved parent pages**, with the pipeline's own `page_meta` [verified, `pdf_discovery_batch.py`, `convert_run3.py` checks]:
  - every pinned PDF was found: 34 of 34 pins across 20 entries;
  - PDFs found in scope on the saved pages: SG Steuerbuch 248, AR tax 53, AI tax 51 (with the pattern), Lugano 122, Neuchâtel 79, RSJU Journal officiel 33, faovd 15, UR 16, OW 3.
- **JU court tariff:** the circulars page now links a newer tariff (`24c70508…modif.du17.12.2024.pdf`) than Run 3's `ff78dbf9…` URL. The pin follows what the page links.

**Offline parse of the candidates.** I ran the new parser on every saved page inside the candidates' prefixes [verified, `dry_parse_all.py`]:
- 187 pages: 184 emit sections, 1 is empty (a scan-ne.ch page), 2 are not emitted (Neuchâtel, below).
- 72 of 75 entries have at least one saved in-scope HTML page.
- `ur_pdfs` and `ju_journal_officiel` were checked through their saved aliases (the `/_rte/` page and the RSJU slug file).
- `vernier_reglements` has none: its saved list is an error page.

**Caveats**, all flagged in the YAML
- **`neuchatel_ville_reglementation`: the workaround is unverified.**
  - The page is French (`<html lang="fr">`), but its hreflang names the unprefixed URL as the `de` alternate.
  - The parser gives the hreflang self-match priority (`html_page.py:52-58`). So the page is not emitted, and its PDF links are dropped with it (`html.py:318-322`) [verified offline].
  - I start at the site's own `fr` alternate `/fr/votre-commune/reglementation` instead. That this URL serves the page without redirecting is not checked.
- **`vernier_reglements`: unverified.** The saved list page is a Drupal error message.
- **`ow_pdfs`, `ur_pdfs`, `tg_gerichte_merkblaetter`:** 1 PDF each has no verified parent page. They are the OW Wegleitung, the UR Tarifordnung and TG 99108.
- **`gerichte_zh_themen`:** the server drops connections. Transport errors are not retried (`politeness.py:21,121-127` retries only 429/503).
- **Content-addressed pins (jura.ch, cdn.zg.ch jcr ids, av.tg.ch asset ids):** a new file version gets a new URL, so it needs a manifest edit. Folder pins avoid this where the folder is topical.
- **`tg_steuerpraxis`** pins the 2026-09 edition.

**Validation output** [verified: `convert_run3.py`, re-run and byte-identical after the Run 3 folder was restored]
```
candidates: PASS: 75 sources                          (load_manifest)
per_entry: pass 75, fail 0                            (SourceEntry.model_validate each)
merged_with_declared: PASS: 102 sources (27 declared + 75 candidates)   (Manifest.model_validate)
prefix_clashes_all_pairs: []    duplicate_ids: []
self-checks: start_urls inside allow_prefixes, extents in seed_locations() (2,183 ids), pins inside pdf prefixes: no problems
```
The extent check used `locations.seed.seed_locations()`, not the live database.

---

## 5. Unsupported sources and the pipeline changes they need

Ranked by how many catalogue rows each change would unlock.

| # | Change | Rows unlocked | Size |
|---|---|---|---|
| 1 | **JSON records connector** (spec below) | 17: 13 `amtsblatt_*`, `ar_amtsblatt` and `sh_amtsblatt_regierung` (superseded), `bl_schulferien`, `sz-schulferien`. Extended to Plone REST and JSON-by-id: +5 (`bl_gerichte`, `bl_plone_rest`, `zg_steuerbuch_plone`, `sh_cms_json`, `sh_ch_guidance`) | new connector plus a new `connector` value (`manifest.py:21`) |
| 2 | **Links inside JSON-valued attributes** (i-web `data-entities`, `<stzh-datatable rows>`) in `page_meta`/`extract_links` | 9: `ur_iweb_tables` (444 decisions, 1,479 gazette issues), `nw_iweb_tables`, `stadt_thun_iweb`, `stadt_schaffhausen_iweb`, `stadt_thun_abfall_parkieren`, `stadt_schaffhausen_rs`, `nw-pdfs` (NW part), `stadt_zuerich_as`, `stadt_zuerich_as_hunde_abfall_parkieren` | small: parse the attribute, then the HTML strings inside it |
| 3 | **Fixed-URL PDF list** (e.g. `config.pdf_urls`, allowed without crawling pages) | 7 in full: `gl-pdfs`, `sh_ferien`, `stadt_bern_sssb_hunde_abfall_parkieren`, `nw-pdfs`, and the three city samples as a fallback to #2. 3 partly: `ur-pdfs`, `ow-pdfs`, `tg_gerichte_merkblaetter` | small |
| 4 | Keep PDF links of non-emitted pages, or let `<html lang>` win when hreflang conflicts | 1 (Neuchâtel). It is also a silent-loss safeguard | small |
| 5 | TLS: per-source CA bundle or verify option in `corpus_http` (`corpus_source_commands.py:46-47`) | 1: `ag_schulferien` | small |
| 6 | Sitemap host rewrite | 1: `ne_sitemap_rewrite` (8,518 URLs). NE sources work without it | small |
| 7 | Sitemap loc → PDF rewrite (`dgn-lex_<nr>` → `lex-<nr>.pdf`) | 1: `stadt_bern_sssb` (246 numbers in the saved sitemap [verified]) | small (or #3 with a generated list) |
| 8 | Configurable `MAX_PDF_BYTES` | 1: `ti_dc_istruzioni_pf` (declared) | trivial |
| 9 | ICS, POST-JSON and lexican connectors | 1 each: `fr_ics_holidays`, `chaux_de_fonds_reglementation`, `sh_lexican_steuer` | new connectors |

**Quality fixes that unlock no row**
- Crawl-delay for PDFs (§7f).
- PDF title precedence (§7e).
- Deny patterns: needed by the fr.ch arrêts archive, the JU revue archive, the NE jurisprudence lists and ai.ch's `ftw-simplelayout`/`/view`/`/download` URLs.
- Retrying transport errors (`gerichte_zh_themen`).
- Validator checks: start URLs inside `allow_prefixes`; unknown config keys.

**Policy prerequisites**
- amtsblattportal.ch robots.txt is `Disallow: /` (`endpoints.md:39-40`).
- bl-api.webcloud7.ch robots.txt answers 403.
- `load_robots` turns both into "disallow host" (`html.py:56-61`) [verified, mock].
- A JSON connector that reuses it would refuse these hosts. It needs an explicit, recorded per-source exemption, which matches the user's gazette decision (`README.md:57`).

**JSON records connector: short spec**
- **Manifest shape:** `connector: json` with
  - `url` containing `{start}` and `{page}`;
  - `start_offset_days` (window start = today in Europe/Zurich minus N);
  - `page_param` and `page_size`;
  - `total_path` and `records_path`;
  - `id_template`, `title_template`, `text_template`, all `str.format` over the record;
  - optional `url_template` (the public page to cite);
  - optional `detail_url_template` (e.g. `…/publications/{meta[id]}/xml` for the notice text);
  - `date_fields` as **dotted paths** (the old `api.py` read top-level fields only, per `README.md:42`);
  - `language`;
  - `robots_exempt: true` plus a reason.
- **Output:** one `ParsedDocument` per record, with `work_key` `json:<source>:<id>`, one section, and `published_at` from the date field.
- **Politeness:** requests go through `request_with_backoff` and `HostThrottle`.
- **Rolling window:** records that leave the window must not be reported as `gone_urls`, or every run would withdraw last week's notices.
- **Still open:**
  - the public notice URL to cite;
  - excluding personal-data rubrics (732 ZH "Todesanzeige", `endpoints.md:41`).

**What ADR 0014 means for holidays**
- Holidays are answered from indexed documents (`0014-…md:15`). The manifest must include holiday pages of every **declared** canton and city (`:25`).
- Run 3 adds BE's plan as `be_schulferien_volksschule` (tier 1).
- VD, GE, TI and GR holiday pages already sit inside declared entries.
- SZ and BL are outside the declared scope, so nothing there is mandatory.
  - If they are wanted, a JSON connector would index one document per record.
  - For SZ, the html route via its Ferienplan PDF (`…/85734/…`, `run3-b.md:88`) needs its linking page first.
- The corpus schema has **no event-date column** [verified: grep finds no `event` in `corpus/schema.sql`, `models.py` or `persist.py`]. So "calendar evidence" (CONTEXT.md) cannot be represented in `corpus.*`: dates stay in the text.

---

## 6. Topic mapping

| Run 3 category (count in 108 YAMLs) | New topic(s) (`corpus/topics.py:12-33`) |
|---|---|
| dogs (21) | `animals` (ADR 0007:40) |
| taxes (16) | `taxes` |
| schools (24) | `education`, whose description covers school holidays (ADR 0007:40) |
| transport (18) | `transport` |
| parking (4) | `transport` ("parking and blue zones"; ADR 0007:40) |
| waste (5) | `waste` |
| housing (4) | `housing` (renting, tenancy disputes); permits and zoning go to `building` |
| *courts* (missing, 24 rows) | `justice` ("legal proceedings, debt collection, legal aid"). Rent conciliation also fits `housing` |
| *official notices / gazette* (missing, 15 rows) | no single topic. Tagged by content: `politics`, `building` (building permits), `business` (commercial register), `justice` (debt collection), `municipal_services` [inferred] |

**Topics are assigned automatically, per chunk. No manifest field is needed, or possible.**
- The describe model picks up to 3 topics per document and per chunk (`describe.py:27,48,59-62,84-99,315-318`).
- The only prior is the SR-number prior for Fedlex (`persist.py:84-88`).
- `SourceEntry` has no categories field and forbids extra keys (`manifest.py:13`).
- So Run 3's "category missing: courts" problem disappears in the corpus pipeline.

**Caveat:** the query-time fallback classifier still embeds the **ten old categories** (`retrieval/topics.py:37,101-103`, `registry/categories.py:11-22`). New chunks carry the new ids (e.g. `animals`, not `dogs`) [inferred consequence: a fallback-classified question could filter on ids new chunks never carry].

---

## 7. The old pipeline problems, re-checked

**(a) LU pages gave 0 sections**
- The new html connector uses the same splitter, `ingest.html_sections` (`html_page.py:10,49`). What is new is `content_selector` and hidden-heading handling.
- Root cause [verified offline on 21 saved LU pages]:
  - there is no `<main>`, `<article>` or `[role=main]`, so the root is `<body>`;
  - a page-wide `<form id="mainform">` is removed by `DROP_TAGS` (`html_sections.py:11,54-57,180`), which leaves 0 sections.
- **Fix: `content_selector: "#mainContent"`** (the div inside the form), which gives 1–15 sections per page. Applied to the 5 LU entries.

**(b) JU PDFs answer HEAD with 404**
- There is no HEAD anywhere in `corpus/`: a grep for `.head(` finds only the old `ingest/fetchers/pdf.py:37`.
- `PdfConnector` streams a GET, with `If-None-Match`/`If-Modified-Since` when known (`pdf.py:124,152-157`).
- A mocked run sent only GET for robots.txt, the page and the PDF [verified]. **The blocker is gone.**

**(c) TLS failure at schulen-aargau.ch**
- There is no verify or CA option: `httpx.Client(headers=…, timeout=…)` (`corpus_source_commands.py:46-47`), and the config has no TLS setting.
- httpx 0.28.1 (pinned at `uv.lock:836-837`) honours `SSL_CERT_FILE`/`SSL_CERT_DIR` when `trust_env` is on (`httpx/_config.py:33-38`). But that replaces the CA bundle for the whole process.
- **Still blocked.** The entry is in section 2.

**(d) robots.txt rule order**
- The parser is **protego** (`html.py:9,46-62`), which applies longest-match (docstring `:50-52`).
- With rsn.ne.ch's rules (`Disallow: /` then `Allow: /DATA/`), protego allows `/DATA/…pdf` and `urllib.robotparser` refuses it. be.ch's `/content/dam/` is also allowed [verified: `verify_politeness.py`; the rule texts are rebuilt from the report's quotes].
- A robots.txt that fails to load, or answers 401/403/5xx, disallows the whole host (`:56-61`).
- **robots.txt is never checked for PDFs.** `record()` filters PDFs by prefix only (`html.py:322-326`), and `pdf.py` has no robots logic. That is why VS sources get `max_pdfs: 0`.
- The comment at `declared-scope.yaml:319-320` ("robotparser … refused") is out of date.

**(e) Titles**
- **HTML:** the title is the first **visible** h1 in the content root, else `<title>` before its last "|", else the URL (`html_sections.py:82-99`, `html_page.py:59`).
  - i-web's `<h1 class="sr-only">Hauptinhalt</h1>` and ar.ch's `<h1 class="visually-hidden">Inhalt</h1>` are in `_HIDDEN_CLASSES` (`:17-20`), so they are skipped.
  - The new parser gives real titles on all 8 saved NW pages and on the AR pages [verified].
- **PDFs:** the title is the PDF metadata title, else the link text, else the linking page's title, else the file name (`pdf.py:64-65`, `html.py:325-326`). That beats the old file-name title (`ingest/fetchers/pdf.py:65` at ec2d7ed), with two defects:
  - Of 40 saved PDFs parsed offline, 21 have a metadata title, and 11 of those are junk or misleading. Examples: "Leer", "AMT FÜR EDV", "_ERZIEHUNGSDIREKTION_", "…indd", "…xlsx", a stale "Schulferienplan … bis Schuljahr 2006/07", and JU's tariff titled "Service de l'économie – 12, rue de la Préfecture". Each would override a good link text such as "Tarif des avances, émoluments et débours" [verified].
  - The file-name fallback is not URL-decoded (`Schulferien%20202627-203031.pdf`).
- Suggested fix: prefer the link text when the metadata title looks like a file or template name, and unquote the file name.

**(f) Crawl-delay**
- For pages and sitemaps, it is honoured: the delay is max(policy, robots `Crawl-delay` for `*`), capped at 30 s (`html.py:37,74-85,172-184`). The mock applied 10 s [verified].
- **Not for PDFs:** `PdfConnector` uses `crawl_delay_seconds` = 0.5 s (`corpus_source_commands.py:161`, `pdf.py:115-116`, `config.py:25`). The mock fetched the PDF 0.5 s after the page on a host that asks for 10 s [verified].
- This affects the BE hosts and www.bs.ch, which Stage 0 recorded at 10 s. That includes the declared `be_canton` (max_pdfs 60).

**(g) User agent and named bots**
- Every corpus request sends `Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)` (`config.py:51-53`, `corpus_source_commands.py:47`). The mock saw it on the robots.txt, page and PDF requests [verified].
- Robots rules are evaluated for `*` only (`html.py:38,184`; `robots_verdict` `:69`). Named-bot groups are never consulted, and neither would a `swiss-grounding` group be.
- With fo.fr.ch-style rules, `*` is allowed while ClaudeBot is refused [verified]. **The crawler would crawl fo.fr.ch.** That is why it is not in the manifest (decision pending).

---

## 8. Open questions

1. **Does the server read `corpus.*`?**
   - At 159ac23, `retrieval/search.py` reads the old public tables (`db/schema.sql:15,50,82`).
   - Until that switches, sources ingested by the new pipeline are not served. Is a branch pending?
2. **Tier 1:** do you accept the 9 tier-1 additions? They enter the default `corpus fetch --tier 1` crawl, and the paid run.
3. **LU `#mainContent`:** it comes from the offline check, not from an agent report. Keep it?
4. **Unverified entries:** Neuchâtel's `/fr/` workaround, Vernier's list, OW `/publikationen/40733`. Should they be merged before someone checks them live?
5. **`municipal_law`** for the Lugano, Neuchâtel and Vernier collections: this follows your authority rule, not the Run 3 YAMLs. Confirm.
6. **Gazettes:**
   - a robots exemption for amtsblattportal.ch in the new pipeline;
   - which rubrics to exclude for personal data;
   - tier 3 for faovd and the RSJU Journal officiel.
7. **fo.fr.ch:** should the crawler honour named-bot rules? Today it cannot tell them apart.
8. **For the colleague:**
   - Crawl-delay for PDFs;
   - PDF title precedence;
   - `MAX_PDF_BYTES`;
   - a check that start URLs sit inside `allow_prefixes`;
   - rejecting unknown config keys;
   - the out-of-date robots comment in `declared-scope.yaml`;
   - the old-categories fallback classifier.
9. **Content-addressed pins** (jura.ch, zg jcr, av.tg.ch, the TG steuerpraxis edition) need manual updates when files change. Accept that, or wait for folder-level ownership via source merges?
10. **During this session, the Run 3 folder was removed by another session and then restored.**
    - I exported c93ae3f (`sources/run3-discovery`) into `newpipe/run3_copy/` with `git archive`.
    - The restored folder is byte-identical, and the regenerated outputs are identical.

**Scripts** (all under `newpipe/`, all offline)
- `convert_run3.py`, `run3_decisions.py`, `make_csv.py`
- `saved_pages.py` (URL to saved-file index), `offline_parse.py`, `selector_compare.py`, `inspect_containers.py`
- `pdf_discovery_batch.py`, `pdf_titles.py`, `verify_politeness.py`
- `dry_parse_all.py`, `check_sitemap_seeds.py`, `prefix_counts.py`
