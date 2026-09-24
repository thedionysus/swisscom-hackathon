# The new corpus pipeline on main (159ac23): what it does, what it enables, and what changed since 1cb7f49

**How to read the evidence.** A bare `path:line` is relative to the main worktree (WT = commit `159ac23`). A reference like `1cb7f49:path:line` is a line in the old baseline, read with `git show 1cb7f49:<path>`. "Plan:" marks text from `docs/superpowers/plans/*` or an ADR: a stated intention, not code. **Inferred** marks my own reading that no code, test or command output shows directly.

**What was run.** Nothing touched a database, the network or a paid API. The commands were:
- read-only `git` commands (`show`, `diff`, `log -S`, `branch -r`, `ls-tree`);
- `swiss-grounding --help`, `corpus --help` and `corpus fetch --help`, through the existing `.venv`, with `PYTHONDONTWRITEBYTECODE=1` so no bytecode files were written;
- two offline scripts in `scratchpad/newpipe/`: `cost_from_constants.py`, which only parses constants with `ast`, and `robots_semantics.py`, which checks urllib against protego on in-memory robots.txt texts.

This report has not been run through `/audit`.

---

## Summary

1. **Flow.** Sources are declared in one YAML file, `manifests/declared-scope.yaml`, which today holds 27 sources (26 `html`, 1 `fedlex`, all tier 1). The flow is: `corpus fetch` → persist, which also chunks → `corpus run`, which does OCR → describe documents and chunks (paid model, 20 topics) → embed (bge-m3 locally; the OpenAI index is optional) → HNSW index. Everything goes into a new `corpus.*` Postgres schema.
2. **The MCP server on main does not read `corpus.*` at all.** It still serves the old `public` schema, which is filled by the old registry and the `ingest` command, and it still filters on the old 10 categories. The six-tool contract (ADR 0015) exists only as a plan. **Sources added to the manifest are invisible to users until the serving track is merged.**
3. **Removed compared with the old pipeline:** the `api` strategy, standalone `pdf` URL lists, `categories`, `allow_narrowing` (narrowing), `llm_tagging`, translation to English, `license`, and event dates.
4. **No connector exists** for JSON APIs, ICS, XLSX/CSV, POST forms, Plone REST, JSON embedded in HTML, or JavaScript-rendered pages.
5. **Changed:**
   - Scope is set by absolute URL prefixes; a source may span several hosts, but two sources may not overlap.
   - `max_pages`, `max_pdfs` and the delay are set per source.
   - robots.txt is parsed with protego (longest rule wins). A robots.txt that answers 401/403/5xx now blocks the whole host. Rules are checked for `*` only.
   - Conditional GET is used only for revisits. PDFs are fetched by conditional GET, with no HEAD first.
   - Titles are better: hidden `<h1>` headings are skipped, and a PDF's metadata title is used.
   - 429/503 answers are retried with backoff, but connection errors are no longer retried.
6. **New:** sitemap seeding (index files and gzip too), language alternates grouped into translation groups, content and language-switcher selectors, PDF link regexes, OCR of scanned PDF pages, Fedlex in all four languages plus scheduled versions, a budget cap with a spend ledger, Batch API resume, and a quarantine table.
7. **Constraints for the ~150 new sources:**
   - `extent_id` must be an existing location node; there is no district level.
   - Prefixes may not overlap the existing entries: seven sources claim a whole host, and others claim whole language trees.
   - Cost, computed from the code's constants: about $0.07 per 1,000 one-language chunks on the OpenAI Batch API, against about $2.27 on Anthropic (sync only).
   - The planned serving scope is hard-coded to 6 cantons and 7 municipalities.

---

## 1. End-to-end flow on main

### 1.1 Two pipelines exist side by side on main

| | Old pipeline (still wired) | New pipeline (corpus / encoding track) |
|---|---|---|
| Where sources are declared | One YAML file per source in `src/swiss_grounding/registry/sources/*.yaml`, loaded into `public.source` by `db seed` (`src/swiss_grounding/cli/main.py:93-106`, `README.md:172-174,197-199`). Seven files, identical at 1cb7f49 and 159ac23 (`git ls-tree`; `git diff --stat` shows no difference). | `manifests/declared-scope.yaml`, read directly by `corpus fetch --manifest` (`src/swiss_grounding/cli/corpus_source_commands.py:146-156`) and upserted into `corpus.source` at fetch time (`src/swiss_grounding/corpus/fetch_stage.py:80`, `src/swiss_grounding/corpus/persist.py:67-75`). 27 sources, 26 `html` and 1 `fedlex`, all `tier: 1` (grep counts on the manifest). |
| Commands | `ingest`, `renarrow`, `reclean`, `retitle`, `recontext`, `db init/seed`, `sources …`, `query`, `serve`, `load-fixture` (`cli/main.py:16-31,85-418`; confirmed by `swiss-grounding --help`) | `corpus init / check-manifest / fetch / status / batches / estimate / ocr / describe / embed / index / run` (`corpus --help`; `cli/corpus_source_commands.py:214-217`; `cli/corpus_commands.py`; `cli/corpus_run.py:172`) |
| Storage | `public.document`, `public.chunk` (English `text_en`, one `embedding` column), `public.source`, `ingest_run` (`src/swiss_grounding/db/schema.sql:50-101,168`) | `corpus.*` schema (`src/swiss_grounding/corpus/schema.sql`) |
| Read by the MCP server | **Yes** | **No** |

ADR 0010 states this on purpose: *"The new schema sits beside the existing `public.document`/`public.chunk` tables … so the running server keeps working until the serving track switches to it"* (`docs/adr/0010-…md:10`; also `docs/superpowers/plans/2026-09-23-encoding-track.md:7`).

### 1.2 The stages in order

0. **Setup, needed once.** Every `corpus.source.extent_id` must reference a row of `public.location` (`corpus/schema.sql:48`); `corpus.document` has the same constraint (`:72`). `corpus init` only applies the public and corpus schemas (`corpus_source_commands.py:75-81`). The location rows come from `db seed` (`cli/main.py:93-101`). The plan's order is `db seed` → `corpus init` → `corpus check-manifest` (`encoding-track.md:4761-4766`). The runbook does not mention these setup commands; a grep for `check-manifest|corpus init|db seed` in `docs/ENCODING-RUNBOOK.md` found nothing. It assumes an existing database or a restored dump (`ENCODING-RUNBOOK.md:51-71`).
1. **Declare and validate.** `load_manifest` builds pydantic models and validates them (`corpus/manifest.py:119-120`). `select_sources` keeps sources with `tier <= --tier`, optionally narrowed by `--source` (`manifest.py:123-131`).
2. **Fetch, free.** Each source runs in its own thread; the default is 4 workers (`fetch_stage.py:105-112`, `corpus_source_commands.py:150`). Per source, in order:
   - upsert `corpus.source`;
   - load the known URL states from `corpus.fetch_state`;
   - run the connector: `html` or `fedlex`;
   - persist the documents;
   - then run the PDF connector on the PDFs the HTML crawl found (`fetch_stage.py:75-91`).

   After all sources finish, scheduled Fedlex versions whose date has arrived are made current (`fetch_stage.py:94-102`, `persist.py:226-251`). A source's documents are written only after its whole crawl finishes (`fetch_stage.py:82-85`, `AGENTS.md:50-51`).
3. **Persist and chunk, during fetch.** `persist_document` applies these rules:
   - it strips NUL bytes;
   - a URL that another source already holds live is left alone and counted as `duplicate` ("first owner wins");
   - an unchanged content hash only updates `last_seen_at`;
   - a changed hash creates a new row and supersedes the old one;
   - a dated Fedlex `current` version supersedes its peers (`persist.py:190-223`).

   Chunking happens inside `_insert` through `chunk_document` (`persist.py:134-143`). A chunk holds at most 1,800 characters; longer text is windowed with 150 characters of overlap and cut at sentence ends. A law article longer than that is split by paragraph, with a hard maximum of 3,000 (`corpus/chunker.py:5-7,39-93`). Each chunk carries the source's `extent_id` and `authority` (`persist.py:141`). Only Fedlex chunks start with topics, taken from the SR-number prior (`persist.py:84-88`). A chunk whose text is identical to one in an earlier version copies that chunk's description, topics and boilerplate verdict (`persist.py:148-163`).
4. **OCR, paid.** Chunks with `needs_ocr` and empty text are sent to the model as one vision task per page image; the transcription is written into `chunk.text` (`corpus/ocr.py:53-72,102-111`).
5. **Describe, paid.**
   - First, a chunk text that repeats in 3 or more live documents of one source is marked `boilerplate`, unless the source is law (`corpus/describe.py:216-232`).
   - Then one document description per translation group, in every language the group has (`describe.py:144-160`).
   - Then chunk descriptions, one task per (group, status, align_key), with at most 3 topic ids and a boilerplate verdict (`describe.py:165-213,309-318`).
6. **Embed.** The embedded text is `breadcrumb (" > "-joined) + description + text`, cut at 12,000 characters (`corpus/embed.py:22,36-38`).
   - `bge-m3` runs locally. With FlagEmbedding installed it also stores the sparse vector (`corpus/providers.py:77-115`).
   - `openai-3l` (`halfvec(3072)`) is built only if it is listed in `CORPUS_INDEXES` (`cli/corpus_commands.py:152-172`, `config.py:38-40,65-76`).
   - A vector is re-used when its `text_hash` matches (`embed.py:89-115`).
7. **Index.** HNSW, one index per language partition, plus a sparse HNSW index for bge-m3 (`embed.py:298-319`).
8. **`corpus run`** runs stages 4–7 in order, within the budget, and can be re-run to continue (`cli/corpus_run.py:1-12,163-169`).
9. **Serving.** Nothing on main reads the corpus. A grep for `corpus\.` in `src/swiss_grounding/retrieval`, `mcp_server`, `app.py` and `locations` returns nothing. The planned `swiss_grounding.serving` package "reads only the `corpus` schema" (Plan: `serving-track.md:7`). It does not exist on main: `git ls-tree -d 159ac23 src/swiss_grounding/` shows no `serving/`, and no serving branch exists on origin (`git branch -r`).

### 1.3 What still uses the old registry/ingest code, and which schema the server queries

- **MCP server** (`src/swiss_grounding/mcp_server/server.py`):
  - it imports `ingest.run_log`, `registry.categories` and `registry.suggestions` (`:14-18`);
  - `swiss_search` goes through `build_query_core` → `retrieval.search`, whose SQL reads `chunk c join document d … join source s`, all `public` tables (`retrieval/search.py:12-17,92-107`);
  - `swiss_get_document` reads `document` and `chunk` (`server.py:211-228`);
  - `swiss_coverage` reads `document` and `ingest_run` health (`server.py:36-41,263-267`);
  - `swiss_suggest_source` writes `source_suggestion` and `public.source` through `upsert_sources` (`registry/suggestions.py:98,107,132`).
- **Topic filter at query time** still uses the old 10 ids: `registry/categories.py:11-22` on main, `retrieval/topics.py:37`, and `retrieval/query_core.py:10,50-57`, which rejects any other id.
- **The new pipeline reuses one old module:** `corpus/connectors/html_page.py:10` imports `extract_links` and `html_to_page` from `ingest/html_sections.py`.
- **Answer:** the server queries the **`public`** schema. The old pipeline is still the only one that feeds it.

---

## 2. Manifest schema

### 2.1 Top level (`manifest.py:87-111`)

- `version: int` and `sources: tuple[SourceEntry, …]`. The model is frozen with `extra="forbid"`, so an unknown top-level key or source-level key is an error.
- Source ids must be unique (`:93-99`).
- **Prefixes of different sources must be disjoint** (`:101-111`). For every pair of sources, each prefix in `allow_prefixes + pdf_allow_prefixes` is compared with `startswith` in both directions (`:114-116`). Any overlap raises a validation error.

### 2.2 `SourceEntry` fields (`manifest.py:12-45`)

| Field | Type / allowed values | Required? | Validation | Where it is used |
|---|---|---|---|---|
| `id` | `str`, pattern `^[a-z0-9_]+$` | yes | pattern, unique | primary key of `corpus.source`; `data/raw/<id>/` folder (`artifacts.py:9`) |
| `name` | `str` | yes | — | stored only (`persist.py:68-75`) |
| `publisher` | `str` | yes | — | stored on every document (`persist.py:130`); named in the document-description prompt (`describe.py:153`); `publisher` field of the planned citation (Plan: `serving-track.md:2516`) |
| `authority` | `federal_law`, `cantonal_law`, `municipal_law`, `official_info`, `institutional` | yes | Literal (`:18`); DB CHECK (`schema.sql:45-46`) | stored on documents and chunks (`persist.py:130,141`); law authorities are exempt from repeated-furniture marking (`describe.py:38,227`); planned relevance feature (ADR 0012:15) |
| `level` | `federal`, `cantonal`, `municipal` | yes | Literal (`:19`); DB CHECK (`schema.sql:47`) | **stored only** (`persist.py:71-75`; no other use in `corpus/`, grep) |
| `extent_id` | `str` | yes | **no format check in the model** (`:20`); must exist in `public.location` (FK `schema.sql:48,72`); `check-manifest` reports it if unknown (`corpus_source_commands.py:123-131`) | copied onto every document and chunk (`persist.py:131,141`); **no narrowing** |
| `connector` | `fedlex`, `html` | yes | Literal (`:21`); DB CHECK (`schema.sql:49`) | picks the connector (`corpus_source_commands.py:159-160`, `fetch_stage.py:82`) |
| `tier` | `int` from 1 to 3 | yes | `ge=1, le=3` (`:22`) | selection `tier <= --tier` (`manifest.py:130`); the runbook fetches `--tier 1` (`ENCODING-RUNBOOK.md:86`) |
| `languages` | tuple drawn from `de, fr, it, en, rm` | yes, at least 1 | Literal, `min_length=1`, no duplicates (`:23,36-38`) | HTML: the first entry is the default for pages that declare no language; pages in other languages are not stored (`html_page.py:52-58`). Fedlex: `rm` is skipped (`fedlex.py:19-24,168-170`) |
| `config` | `dict[str, Any]` | default `{}` | connector-specific checks only (§2.4) | read by the connectors |
| `retrieved_via` | `str` or null | default null | — | stored on documents as provenance (`persist.py:132`); intended for ADR 0008 (opencaselaw) |

### 2.3 `extent_id` format (from the location seed, not from the manifest)

- The format is:
  - `CH` for the country;
  - `CH-<canton abbreviation>` for a canton, for example `CH-ZH`;
  - `CH-<canton>-<BFS number>` for a commune, for example `CH-GR-3762`;
  - plus the Zürich city districts `CH-ZH-261-K<n>` and their quarters `CH-ZH-261-K<n>-<SLUG>`.
- Sources: `locations/seed.py:69-106` and `locations/register.py:70-86`.
- Levels are only country, canton, municipality and neighborhood (`locations/models.py:6-10`). **There is no district (Bezirk) node, and no node for inter-communal bodies.** The commune register CSV does have a `district` column, but it is not turned into a location (`register.py:17,70-86`).

### 2.4 `config` keys and how each is used (every key the code reads, from a grep of `cfg`/`config` reads)

**`html` connector**

| Key | Type / default | Checked when the manifest loads? | How it is used |
|---|---|---|---|
| `start_urls` | list of absolute URLs, **required** | only that it is present and non-empty (`manifest.py:29-32`) | seeds the frontier (`html.py:239`). **A start URL outside `allow_prefixes` is skipped silently** (`html.py:247`). A start URL ending in `.pdf` is skipped too (`SKIP_SUFFIXES`, `html.py:30-31`). |
| `allow_prefixes` | list of absolute URL prefixes, **required** | present and non-empty; overlap check | page scope, see §2.5 (`html.py:186-199,235`) |
| `pdf_allow_prefixes` | list; default = `allow_prefixes` (`html.py:241-242`) | overlap check only | a discovered PDF link is kept only if it starts with one of these (`html.py:322-324`) |
| `pdf_link_patterns` | list of regexes; default none | each regex must compile (`manifest.py:66-71`) | `re.search` against absolute link URLs. A matching link counts as a PDF even without a `.pdf` suffix (`html_meta.py:150-151`) and is never crawled as a page (`html.py:143-145,190-194`). |
| `language_links_selector` | CSS selector | must compile with soupsieve (`manifest.py:75-84`) | the site's language switcher, used for language alternates. The language comes from the link's `hreflang`/`lang`, else its text (a code or language name), else a `/xx/` path segment (`html_meta.py:65-92`). |
| `content_selector` | CSS selector | must compile with soupsieve | overrides the content root; the fallback order is `main`, `article`, `[role=main]`, `body` (`ingest/html_sections.py:30,43-51`) |
| `sitemap_urls` | list of absolute URLs | must start with `http(s)://` (`manifest.py:72-74`) | sitemap seeding (`html.py:201-217`, `sitemap.py`) |
| `sitemap_include` | list of regexes; empty means every URL | each regex must compile | `re.search` on each page URL in the sitemap (`sitemap.py:97,129`) |
| `max_pages` | int, default **300** (`html.py:32`) | **not checked** (converted with `int()` at run time, `html.py:236`) | counts every URL popped from the queue that passes the scope and robots checks, **including redirects, 304s, errors, non-HTML answers and pages in undeclared languages** (`html.py:245-258`). Also caps sitemap seeds (`html.py:240`). |
| `max_pdfs` | int, default **50** (`html.py:33`) | not checked | the first N distinct in-scope PDF links found (`html.py:323`); `0` means no PDFs |
| `delay_seconds` | number ≥ 0 | yes (`manifest.py:55-60`) | raises the host's minimum delay for pages, robots.txt and sitemaps (`html.py:164-170,182,238`); **not applied to PDF downloads** (§3.5) |

**`fedlex` connector:** `sr_numbers` is a list of SR numbers as strings and is **required** (`manifest.py:34-35`, `fedlex.py:166`).

**Not validated.**
- `config` is a free `dict[str, Any]` (`manifest.py:24`), so a misspelled optional key such as `max_page` or `content_selectors` is **ignored silently**. Evidence: the checks look only at the named keys (`manifest.py:63-84`), and the connector reads keys with `.get()` and a default (`html.py:236-242`).
- Keys from the old pipeline (`path_allowlist`, `start_paths`, `language`, `urls`, `records_path`, …) are not read anywhere in `corpus/` (grep of `cfg`/`config` reads).

### 2.5 How `allow_prefixes` is matched

- The test is plain `url.startswith(prefix)` on the absolute URL, fragment removed, query string kept (`html.py:186-188`; links are made absolute and defragged in `ingest/html_sections.py:208` and `html_meta.py:39-40`).
- **Case-sensitive, and scheme and host must match exactly.** `https://www.x.ch/` does not match `https://x.ch/…` or `http://www.x.ch/…`. `ti_canton` therefore lists both `https://` and `http://` PDF prefixes (`declared-scope.yaml:366`).
- **A trailing slash matters.** `…/de/steuern-finanzen` also matches `…/de/steuern-finanzen.html` and `…/de/steuern-finanzen-xyz`, while `…/de/` matches the whole German tree (examples at `declared-scope.yaml:303` and `:71`).
- **Several hosts are allowed.** One source can list prefixes on different hosts; `meteoswiss` uses four hosts (`declared-scope.yaml:264-267`). The old "same host as `base_url`" rule is gone (compare `1cb7f49:src/swiss_grounding/ingest/fetchers/html_crawl.py:88-89`).
- **Redirects.** If a page redirects, the **final** URL must also be inside a prefix; otherwise the error is "redirected outside scope" (`html.py:276-285`).

---

## 3. Connectors: what each can and cannot do

### 3.1 `html` (`corpus/connectors/html.py`)

- **Frontier.** The first queue holds the start URLs, then the sitemap seeds, then links found during this run. Language alternates jump to the front of the queue. Known URLs that nothing linked to this run go to a second, revisit queue that is processed last (`crawl_queue.py:1-8,40-49`; `html.py:265-272`).
- **Scope per URL.** A URL must match a prefix, must not end in one of `SKIP_SUFFIXES`, must not match a PDF pattern (when it is queued), and must be allowed by robots.txt (`html.py:190-199`).
  - `SKIP_SUFFIXES` = `.pdf .jpg .jpeg .png .gif .svg .zip .xml .json .ics .csv .docx .doc .xlsx .xls .mp4 .mp3` (`html.py:30-31`).
  - **A URL refused by robots.txt or by prefix is skipped silently**, with no quarantine entry (`html.py:247`).
- **Responses.**
  - Redirects are followed.
  - `304` → unchanged.
  - `404`/`410` on a known URL → withdrawn.
  - A known URL that now redirects → withdrawn, and the target is fetched as a new URL.
  - Other `4xx`/`5xx` → error, which goes to quarantine (`html.py:276-299`, `fetch_stage.py:58-64`).
  - A response whose `content-type` does not contain `html` is skipped silently; a missing header counts as HTML (`html.py:257`).
- **Language.**
  - The page's language comes from its own entry in its alternates, else from `<html lang>`, else from the first entry of `languages`.
  - A page in a language that is not declared is **not stored, but its links are still followed** (`html_page.py:52-58`; `html.py:265-273` runs before `record()`; `record()` returns early when `emit` is false, `html.py:318-319`).
- **Links.** Every `href` on the **whole** page is followed, including nav, header and footer links and custom tags. `<link>`, `<base>`, `<script>` and `<style>` are ignored (`ingest/html_sections.py:194-211`, called on the full HTML at `html_page.py:67`). `rel=nofollow` and `meta robots noindex` are **not handled** (grep).
- **JavaScript pages: not supported.**
  - Pages are fetched with plain `httpx` GET and parsed with BeautifulSoup. There is no JavaScript renderer (a grep for playwright, selenium or headless finds nothing).
  - The Nuxt `__NUXT_DATA__` payload is read **only for language alternates** (`html_meta.py:95-147`).
  - Plan: the survey found "no headless browser needed anywhere" for the current 21 HTML sites (`encoding-track.md:4930`).
- **Content extraction** (reused from `ingest/html_sections.py`).
  - Content root: `content_selector` if given, else `main`, `article`, `[role=main]`, `body` (`:43-51`).
  - Inside the root, it drops `nav, footer, script, style, noscript, aside, form`, then drops `header` once the title has been found (`:11,27-28,180-182`), and removes headings that are visually hidden (`:187-189`).
  - It splits into sections at `h1`–`h4`; `h5`/`h6` are not section breaks (`:29,117-166`).
  - Tables and lists stay whole and are converted to Markdown; link targets and images are removed (`:33,108-110`).
  - HTML comments and CMS marker lines (TYPO3SEARCH, Start_/End_Module, bracket runs) are dropped (`:143-144`; `html_page.py:12-27`).
  - **Inferred:** because `form` is dropped, a site whose entire content sits inside `<form>` (ASP.NET WebForms or SharePoint pages) would lose all content unless `content_selector` points inside the form. `gr_canton` does exactly that with `div.pageContent` (`declared-scope.yaml:383`). This was not tested against a live page.
- **Output.** One document per page that produced at least one section (`html.py:327-332`). The section `align_key` is `"<lang>:<index>"` (`html_page.py:64`), so **HTML chunks are never aligned across languages**; only whole pages are grouped. The plan accepts this: "HTML versions are grouped but not aligned by position" (`encoding-track.md:4882`).
- **Translation groups.** Two pages are grouped only when **each lists the other** as an alternate (connected components of that relation). A component that contains two pages in the same language falls back to one key per page (`html.py:94-140`).

### 3.2 `html_meta` and `html_page`: the metadata that is extracted

| Metadata | How it is obtained | Evidence |
|---|---|---|
| Title | The first **visible** `<h1>` inside the content root. Hidden means the `hidden` attribute, `aria-hidden="true"`, inline `display:none` or `visibility:hidden`, or one of the classes `sr-only, visually-hidden, visuallyhidden, invisible, screen-reader-text, element-invisible, u-visually-hidden, show-for-sr, access, offscreen`. Otherwise `<title>` with its last `\| …` segment removed; otherwise the URL. | `ingest/html_sections.py:17-21,60-99`; `html_page.py:59` |
| Breadcrumb | The page title followed by the heading path (`h1`–`h4`) above the section. **Not** the site's breadcrumb navigation, which is inside `nav` and dropped. | `html_page.py:61-65`; `html_sections.py:11,136` |
| Section anchor | The heading's `id` attribute, which may be absent (null) | `html_sections.py:158` |
| Dates | `published_at` from the meta tags `article:published_time`, `dcterms.date`, `date`, `dc.date`. `modified_at` from `article:modified_time`, `dcterms.modified`, `last-modified`, `dc.date.modified`, else from a regex over the **whole page text** matching `Stand:` / `Letzte Änderung` / `Aktualisiert` / `Mise à jour` / `Mis à jour le` / `Aggiornato` / `Ultimo aggiornamento` followed by `dd.mm.yyyy`. | `html_meta.py:13-16,173-185`; stored at `persist.py:127-133` |
| Language and alternates | `hreflang` alternates first; missing languages are filled from `language_links_selector`, then from the Nuxt payload. Only `de, fr, it, en, rm` are kept. | `html_meta.py:50-53,154-169` |
| Canonical URL | Parsed, but **not used**: it is not a field of `CrawledPage`. | `html_meta.py:170-171`; `html_page.py:30-41` |
| PDF links | Any `<a href>` on the page whose URL, before the query string, ends in `.pdf`, or that matches `pdf_link_patterns`. The link text becomes `title_hint`. | `html_meta.py:150-151,187-192` |

### 3.3 `pdf` (`corpus/connectors/pdf.py`)

- **How PDFs are found.** *Only* as links on in-scope HTML pages that were crawled and stored.
  - There is no key for a fixed list of PDF URLs (§2.4).
  - A `.pdf` start URL or sitemap entry is dropped, because `.pdf` is in `SKIP_SUFFIXES` and sitemap seeds must pass `_crawlable` (`html.py:190-194,208-209`).
  - A PDF takes the language of the page that linked it (`html.py:325`).
- **No HEAD request.** Each PDF is one streamed GET, conditional with `If-None-Match` / `If-Modified-Since` when the PDF is already known (`pdf.py:118-160`).
  - `304` → unchanged.
  - `404`/`410` → withdrawn if known, **otherwise an error in quarantine**.
  - Any other status ≥ 400 → error (`pdf.py:171-182`).
- **Guards.**
  - Maximum 30 MB, checked against `Content-Length` and again while streaming (`pdf.py:37,134-143`).
  - `content-type` must contain `pdf`. A generic type such as `application/octet-stream` is accepted only if the body starts with `%PDF` within the first 1 KB (`pdf.py:39-41,130-133,144-145`).
- **Text.** pypdf `extract_text()` per page, one section per page, with anchor `page=N` and `align_key` `"<lang>:p<N>"` (`pdf.py:70-85`).
- **Title.** The PDF metadata title, else the link text or page title, else the file name (`pdf.py:64-65`).
  - **Inferred:** a PDF with no metadata title can end up titled with link text such as "Download".
  - **Inferred:** a PDF can also carry a producer-generated metadata title such as "Microsoft Word - x.docx".
- **Scanned pages.** A page with fewer than 80 characters of text is rendered to PNG at 150 dpi (`data/ocr/<source>/<stem>-p<N>.png`) and marked `needs_ocr` (`pdf.py:35-36,75-82`). The paid OCR stage transcribes it later (§1.2 step 4). The raw PDF is saved to `data/raw/<source>/<sha24>.pdf` (`pdf.py:183`, `artifacts.py:8-20`).
- **Politeness.**
  - PDFs are **not checked against robots.txt**: `robots` does not occur in `pdf.py` or `fetch_stage.py`, and `record()` filters PDF links by prefix only (`html.py:322-324`).
  - PDF requests are spaced by `CRAWL_DELAY_SECONDS` (0.5 s) per host, ignoring the robots `Crawl-delay` and `config.delay_seconds` (§3.5).

### 3.4 `sitemap` (`corpus/connectors/sitemap.py`)

- **Seeding.** Enabled only when `sitemap_urls` is set (`html.py:205-206`). Seeds are added to the frontier after the start URLs (`html.py:215-216`).
- **What is followed and parsed.**
  - Sitemap index files are followed through `<sitemap><loc>`, and page URLs come from `<url><loc>`. Namespaced `loc` elements such as `image:loc` are ignored (`sitemap.py:69-83,127`).
  - Gzip is detected from the magic bytes, whatever the `content-type` (`sitemap.py:1-5,56-66`).
  - At most 200 sitemap files and 50 MB per file (`sitemap.py:25-26`).
- **Filters on a page URL.**
  - It must match any `sitemap_include` regex.
  - It must pass `_crawlable`: inside `allow_prefixes`, not a skipped suffix, not a PDF pattern.
  - It must not already be known or queued.
  - Seeding stops at `max_pages` new URLs (`html.py:201-217`, `sitemap.py:128-132`).
- **Each sitemap file** is checked against robots.txt; a refusal is logged as an error (`sitemap.py:107-109`). A 429/503 answer is retried with backoff (`sitemap.py:111`). A file that cannot be read becomes an error, and the crawl continues without it (`sitemap.py:112-126`).
- **It cannot rewrite a wrong host.** Child sitemap URLs are fetched exactly as listed (`sitemap.py:127`). A page URL on another host or scheme fails the prefix check and is **dropped silently** (`sitemap.py:129` + `html.py:190-194`). No code rewrites URLs (read in full).

### 3.5 `politeness` (`corpus/connectors/politeness.py`, plus robots.txt handling in `html.py`)

- **Parser.** robots.txt is parsed with **protego**, which applies RFC 9309 longest-match (`html.py:9,46-62`; `pyproject.toml:24`).
  - Offline check (`scratchpad/newpipe/robots_semantics.py`): with be.ch's rules (`Disallow: /content/`, `Allow: /content/dam/`), urllib.robotparser answered `False` for `/content/dam/x.pdf`, and protego answered `True`.
  - The unit tests `test_longest_match_*` pin the same behaviour (`tests/unit/corpus/test_html_connector.py:357-374`).
- **When robots.txt cannot be read.** A fetch failure, `401`, `403` or `5xx` makes the **whole host disallowed** and logs a warning once. Any other non-200 answer, such as 404, allows everything. The robots.txt request follows redirects (`html.py:46-62`; tests `:262-274`).
- **Which user-agent the rules are checked for.** Always `"*"` (`html.py:38,69,183-184`).
  - Offline check: with a robots.txt that disallows the `swiss-grounding` agent and allows `*`, protego answered **True** when asked for `*` and **False** when asked for the agent string actually sent. The crawler asks for `*`, so an agent-specific block is ignored.
- **Switch.** `RESPECT_ROBOTS` defaults to true (`config.py:48`). When it is off, robots.txt is not fetched at all, so its `Crawl-delay` is not read either (`html.py:172-174`).
- **User-agent sent.** `Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)` (`config.py:51-53`, `corpus_source_commands.py:46-47`). The old one was `swiss-grounding/0.1 (+https://github.com/thedionysus/swisscom-hackathon)` (`1cb7f49:src/swiss_grounding/config.py:27`).
- **Delays.**
  - A per-host throttle is shared by all threads and connectors (`politeness.py:1-6,24-58`).
  - For pages, robots.txt and sitemaps, the host delay is the largest of: `CRAWL_DELAY_SECONDS` (0.5 s, `config.py:25`), the source's `delay_seconds`, and the robots `Crawl-delay` for `*`. That `Crawl-delay` is **capped at 30 s** (`html.py:37,74-85,164-184`).
  - **PDF downloads use only 0.5 s** (`corpus_source_commands.py:161`, `pdf.py:115-116`). The robots delay is kept privately in `HtmlConnector._delays` (`html.py:156,182`); the shared throttle only raises its minimum after a 429/503 (`politeness.py:46,60-74`).
  - **Inferred:** PDFs on a host with `Crawl-delay: 10` (be.ch, according to the manifest comment at `declared-scope.yaml:319`) are requested every 0.5 s.
- **Backoff.** Only on `429` and `503`, with at most 3 attempts in total (`politeness.py:17-21,108-127`).
  - `Retry-After` is honoured as seconds or an HTTP date, capped at 120 s, default 30 s (`politeness.py:80-96`).
  - After each such answer, the host's delay is doubled (minimum 2 s, maximum 30 s) for the rest of the run (`politeness.py:60-74`).
- **Other failures are not retried.** Connection errors, timeouts and other 5xx answers become errors in quarantine (`html.py:253-255`, `pdf.py:167-169`). The corpus HTTP client has no transport retries (`corpus_source_commands.py:46-47`; a grep for `HTTPTransport` matches only the old fetchers).
- **Timeouts.** The client default is 20 s (`FETCH_TIMEOUT_SECONDS`). Individual calls override it: pages 30 s (`html.py:231`), robots.txt 20 s (`:55`), sitemaps 60 s (`sitemap.py:42`), PDFs 60 s (`pdf.py:124`), Fedlex 60 s (`fedlex.py:122,216`).
- **TLS.** The httpx defaults: no `verify=` anywhere (grep). HTTP/2 is not enabled.

### 3.6 `crawl_queue` (`corpus/connectors/crawl_queue.py`)

- There are two queues.
- **Frontier** (full GET): start URLs, sitemap seeds and links found this run.
- **Revisit queue** (conditional GET): URLs that are known but that nothing reachable in this run linked to. It is processed only after the frontier is empty (`:40-49`). A known URL that shows up as a link is promoted to the frontier (`:25-38`).
- **Inferred:** if the frontier alone uses up `max_pages`, known pages that were not linked are neither re-checked nor withdrawn in that run, and they stay `current`.

### 3.7 `fedlex` (`corpus/connectors/fedlex.py`, `fedlex_akn.py`)

- **Query.** SPARQL `POST` to `fedlex.data.admin.ch`, one request per SR number and language: de, fr and it are required, en is optional, rm is not supported (`fedlex.py:18-26,115-124`).
- **Versions.** It keeps the current consolidation plus the next scheduled one (`:60-66,140-161`). If none is in force for English, it falls back to the newest English version (`:153-161`).
- **Parsing.**
  - Akoma Ntoso XML, one section per article, whose `align_key` is the article's `eId`, so the same article lines up across languages.
  - The breadcrumb is `SR <n> <title>` › container › article.
  - Paragraphs are kept, footnotes removed (`fedlex_akn.py:74-97`).
  - An article longer than the maximum is split by paragraph **in every language version** (`fedlex.py:74-92`).
- **Document fields.** Title from SPARQL, else `SR <n>`. `is_authentic = lang != "en"`, `valid_from`/`valid_to` from the consolidation, URL `https://www.fedlex.admin.ch/eli/…/<yyyymmdd>/<lang>`, and the XML is saved (`fedlex.py:69-71,195-211`).
- **Retries.** 3 attempts on transport errors, 5xx and 429, sleeping 1 s and then 2 s (`fedlex.py:103-113`).
- **Incremental.** An SR number and status whose language URLs are all known is skipped (`fedlex.py:188-191`).

### 3.8 What no connector can do today

A source that needs any of the following cannot be added through the manifest.

| Capability | Status on main | Evidence |
|---|---|---|
| JSON API (the old `api` strategy) | **None.** The old `ApiFetcher` still exists but is reachable only through the old `ingest` command. | `manifest.py:21` (`Literal["fedlex","html"]`), `schema.sql:49`, `corpus_source_commands.py:159-161`; old `ingest/fetchers/api.py` |
| ICS calendars | **None**: `.ics` is skipped | `html.py:30-31` |
| XLSX, XLS or CSV | **None**: skipped | `html.py:30-31` |
| POST requests or forms | **None** for HTML and PDF, which use GET only. Only Fedlex SPARQL uses POST. | `html.py:229-231`, `pdf.py:124`, `fedlex.py:119` |
| Plone REST (`++api++`, JSON) | **None**. JSON URLs are skipped and only HTML content types are parsed. | `html.py:30-31,257` |
| JSON embedded in HTML (tables or data in `<script>`) | **None.** `script` is dropped from the content. The Nuxt payload is read only for alternates. HTML `<table>` elements *are* kept, as Markdown. | `html_sections.py:11,33,108-110`; `html_meta.py:95-147` |
| JavaScript-rendered content | **None** (no browser) | grep; `encoding-track.md:4930` |
| Calendar event dates | **None**: `corpus.document` has no `event_date` column | `schema.sql:62-86` |

Plan: the serving track would import the Zürich OpenERZ calendar with a **dedicated module**, `corpus/calendar.py`, not a manifest connector. It builds `ParsedDocument`s in code, from a hard-coded `SourceSpec` whose `config` is `{"kind": "openerz"}` (`serving-track.md:2769-2771,2833-2836`).

---

## 4. Topics

### 4.1 The 20 topics (`corpus/topics.py:12-33`; ADR 0007)

| id | Label |
|---|---|
| `work` | Work and employment |
| `social_security` | Social security and pensions |
| `health` | Health and health insurance |
| `taxes` | Taxes |
| `housing` | Housing and renting |
| `building` | Building and land use |
| `family` | Family and civil status |
| `residence` | Residence, migration and citizenship |
| `politics` | Politics and voting |
| `justice` | Justice, courts and criminal law |
| `safety` | Public safety, police and civil protection |
| `education` | Education and schools |
| `transport` | Transport, vehicles and parking |
| `travel` | Travel, customs and borders |
| `environment` | Environment, energy and nature |
| `animals` | Animals and pets |
| `waste` | Waste and recycling |
| `outdoors` | Leisure, sport and outdoors |
| `business` | Business and consumers |
| `municipal_services` | Municipal services and administration |

### 4.2 How a chunk gets its topics

- **Per chunk, by the model, in the paid describe stage.**
  - The prompt lists all 20 topics and asks for at most three (`describe.py:54-66`).
  - The reply is kept only for known ids, at most 3 (`describe.py:27,84-87`).
  - If the reply has no valid topic, the "prior" is used (`describe.py:87`).
  - The result is written to `chunk.topics` (`describe.py:309-318`).
- **The prior exists only for Fedlex.** It comes from the SR-number table (`topics.py:36-72`, applied in `persist.py:84-88`). HTML and PDF chunks start with an empty prior, so **they may end up with no topic at all**.
- **Not from the manifest.** There is no topics or categories field (`manifest.py:12-25`).
- **Document level.** The document-description reply also carries up to 3 topics, stored on `corpus.translation_group.topics` (`describe.py:281-287`). They are not copied onto chunks.

### 4.3 Old 10 categories mapped to the 20 topics

The mechanical map: *"`dogs` → `animals`, `hiking` → `outdoors`, `parking` → `transport`, `schools` → `education`; the others keep their ids"* (ADR 0007:40). The old definitions are in `1cb7f49:src/swiss_grounding/registry/categories.py:11-22`.

| Old | New | Change in meaning (old definition vs new "covers" text) |
|---|---|---|
| hiking | outdoors | nature protection now fits `environment` |
| waste | waste | — |
| dogs | animals | — |
| taxes | taxes | — |
| housing | housing | the old category also covered "building permits, zoning", which now belong to `building` |
| transport | transport | — |
| parking | transport | — |
| schools | education | — |
| health | health | — |
| safety | safety | — |

### 4.4 Courts, justice, official notices and gazettes

- **Courts and justice: yes.** `justice` covers "Criminal law, fines, legal proceedings, debt collection, legal aid" (`topics.py:22`).
- **Official notices and gazettes (Amtsblatt): no dedicated topic** (`topics.py:12-33`). The nearest are `politics` ("authorities and their powers") and `municipal_services` ("documents and certificates", "municipal fees").
- **Inferred:** because topics are chosen per chunk from its content, a gazette notice would be filed by its subject; a building-permit notice, for example, would go under `building`.

### 4.5 Caveat on main

The server still validates and filters on the **old 10 ids** (`registry/categories.py:11-22`, `retrieval/query_core.py:50-57`, `retrieval/topics.py:37`). The corpus writes the **new 20 ids**. The two meet only when the serving track lands.

Plan: ADR 0015 removes the topic filter that clients choose, and keeps topic as an internal signal (0015:18). ADR 0007 leaves open whether topic will be a hard filter or a ranking signal (0007:41).

---

## 5. Serving and MCP

### 5.1 What main actually serves: the old six tools (`mcp_server/server.py`)

| Tool | Inputs | Returns | Reads |
|---|---|---|---|
| `swiss_resolve_location` | `query` | location id, label, level, path, or candidates when ambiguous (`:78-102`) | location tree |
| `swiss_search` | `question`, `question_en`, `topic_en`, `location`, `topics` / `categories` (old 10 ids), `as_of`, `limit`, `response_format` (`:104-115`) | citations with `url`, `anchor`, `snippet_en`, `snippet_original`, `extent_id`, `authority`, `categories`, `valid_from`, `event_date`, `license`, `tier`, `distance` (`retrieval/cite.py:22-38`) | `public` chunk, document, source |
| `swiss_get_document` | `document_id`, `chunk_id` | document row and chunks with `text_en` / `text_original` (`:208-234`) | `public` |
| `swiss_list_categories` | — | the old 10 categories (`:236-241`) | code |
| `swiss_coverage` | `location` | per source and extent: document counts, health, pending suggestions (`:243-272`) | `public` document, `ingest_run`, `source_suggestion` |
| `swiss_suggest_source` | `url`, `reason`, … | a write: creates or approves a registry source for the old pipeline (`:274-302`) | `public` |

Citation links today: `url` and `anchor` are separate fields; the CLI joins them as `url#anchor` (`cli/main.py:43-47`). The README's "six tools" (`README.md:117,146-153`) are these old tools.

### 5.2 ADR 0015's six tools: planned, not implemented

A grep for `swiss_scope`, `swiss_premium`, `swiss_connections` and `swiss_reference_rate` in `src/` and `tests/` finds nothing. The signatures below come from the plan (`serving-track.md:3530,3808-3935`).

| Tool | Inputs | Returns |
|---|---|---|
| `swiss_search` | `question` (as written, any language), `locations` (up to 3), `translations` ({de, fr, it, en, rm}), `as_of`, `limit` | a status per place: `results`, `needs_location`, `outside_scope`, `source_unavailable` or `no_evidence`; citations with `passage`, `url`, `anchor`, `breadcrumb`, `publisher`, `extent_label`, `tier`, `relevance`, corroboration, `valid_from`, `modified_at`, `fetched_at`, `extraction` (ADR 0015:13; Plan `serving-track.md:362-384,2511-2521`) |
| `swiss_get_document` | `document_id`, `chunk_id`, `reference` (for example "Art. 336c OR" or an official URL), `language` | the article or section around a hit, or another language version (ADR 0015:14) |
| `swiss_scope` | — | the declared-scope statement, including what is not covered. It replaces `swiss_coverage` and `swiss_list_categories` (ADR 0015:15). |
| `swiss_premium` | `municipality`, `age`, `deductible`, `accident`, `model`, `year`, `limit` | the cheapest BAG premiums, read from a table shipped in the dump (ADR 0014:11) |
| `swiss_connections` | `origin`, `destination`, `date`, `time`, `limit` | a live call to transport.opendata.ch (ADR 0014:12) |
| `swiss_reference_rate` | — | the BWO reference rate, or the last good value with `source_unavailable` (ADR 0014:13) |

Removed by ADR 0015: `swiss_resolve_location`, `swiss_suggest_source`, `question_en` / `topic_en`, and the topic filter chosen by clients (0015:18).

### 5.3 The ADRs that decide what can be served

| ADR | Decision | Status on main |
|---|---|---|
| 0005 | Generated context (the descriptions) is indexed and embedded but **never cited**; citations use source text only (0005:10,17) | Corpus: descriptions are embedded and indexed (`embed.py:36-38`; tsvector weights crumb A > description B > text C at `schema.sql:34-39`). Plan: the citation `passage` is built from chunk `text` only (`serving-track.md:2515`). Not served yet. |
| 0008 | Cantonal law comes from 12 official portal APIs and from opencaselaw for the other 14, labelled `cantonal_law`, citing the official portal URL, with `retrieved_via: opencaselaw` (0008:8) | **Not implemented.** No such connector exists (grep for opencaselaw, lexfind, lexwork finds nothing); only the `retrieved_via` field exists (`manifest.py:25`). ADR 0009 moved cantonal law for other cantons to a lower tier (0009:18). |
| 0009 | Declared scope: federal for all of Switzerland; 6 cantons (ZH, BE, VD, GE, TI, GR); 7 municipalities (Zürich, Bern, Lausanne, Genève, Lugano, Chur, Scuol); everything else gets an explicit "outside scope" answer (0009:8) | Manifest: 27 tier-1 sources match it. Plan: `SCOPE_CANTONS` and `SCOPE_MUNICIPALITIES` are hard-coded (`serving-track.md:582-590`). The planned search **cuts the searched path to the covered levels** with `path = full if "municipal" in o.covered else full[: len(o.covered)]` (`serving-track.md:2464-2468`). **Inferred:** the planned server would therefore never retrieve cantonal or municipal documents for places outside those lists, even if they were encoded, until the lists change. |
| 0010 | One `corpus.chunk` table with list partitions per language (de, fr, it, en, rm); per-language keyword configurations; one embedding table per model (0010:8) | Implemented (`schema.sql:7-39,91-143`) |
| 0011 | Every language store is searched with the question as asked; translations are an optional boost (0011:9) | Plan only (serving) |
| 0014 | Three lookup tools. **School holidays and waste stay indexed documents**; the manifest must include the holiday and waste pages of every declared canton and city (0014:15,25). | Lookups: plan only. Holiday and waste pages are ordinary HTML/PDF sources. A keyword grep of the manifest (ferien, vacances, vacanze, abfall, entsorgung, déchets, rifiuti) finds only two start URLs: `ge.ch/vacances-scolaires-jours-feries` and `chur.ch/entsorgungrecycling` (`declared-scope.yaml:350,479`). Pages under broader prefixes may still be crawled; that was not checked. |
| 0017 | A prebuilt `pg_dump` without the OpenAI index, attached to a release of the **private** repository (0017:11) | Plan |

### 5.4 What source data can reach users, and how links are formed

- **Today: nothing from the corpus reaches users.** Only the old `public` index is served (§1.3).
- **Once the serving track lands (Plan).** Only **text passages** of corpus chunks become evidence:
  - HTML sections;
  - PDF pages, including OCR text (`document.extraction` is set to `ocr`, `ocr.py:108`);
  - Fedlex articles.
- **Structured data** can be served only in two ways: a lookup tool (three are planned), or bespoke import code that turns rows into `ParsedDocument` text, as the planned OpenERZ module does (§3.8).
- **Links** (Plan, `serving-track.md:2514`):
  - `url` is the document URL that was **stored**. For HTML that is the **final URL after redirects** (`html.py:256,329`); for PDFs, the discovered link; for Fedlex, the `www.fedlex.admin.ch/eli/…/<date>/<lang>` page (`fedlex.py:69-71`).
  - `anchor` is kept separately: the heading `id` for HTML (it may be null), `page=N` for PDFs, and the article `eId` for Fedlex (`html_sections.py:158`, `pdf.py:81,85`, `fedlex_akn.py:95`).
  - **Inferred:** joining them as `url#anchor` gives `…pdf#page=N`, which browsers open at that page. For Fedlex, the `eId` does not look like a fragment the Fedlex website uses (not verified).
- **Language.** Chunks keep their original language; nothing is translated (§7). The planned citation lists `other_languages` (`serving-track.md:371`).

---

## 6. Cost and operations of adding a source

### 6.1 Which stages cost money, and the providers

| Stage | Paid? | Model | Evidence |
|---|---|---|---|
| `corpus fetch` | free | — | `README.md:77-79` |
| `ocr` | paid | `gpt-5-mini` (`CORPUS_OCR_MODEL`), or Claude Haiku 4.5 with Anthropic | `config.py:36-37`; `corpus_commands.py:103-109` |
| `describe` documents | paid | `gpt-5-mini`, or Haiku 4.5 | `config.py:34` |
| `describe` chunks | paid | `gpt-5-nano`, or Haiku 4.5 | `config.py:35` |
| `embed bge-m3` | free (local; `uv sync --extra embed`) | BAAI/bge-m3, plus sparse vectors with FlagEmbedding | `pyproject.toml:27-31`; `providers.py:77-115` |
| `embed openai-3l` | paid; **only** if listed in `CORPUS_INDEXES` | text-embedding-3-large | `config.py:38-40,74-75`; `corpus_commands.py:158-172` |

- **Providers.** `CORPUS_LLM_PROVIDER` is `openai`, `anthropic` or `fake` (the default is `fake`; `config.py:33`).
  - **OpenAI** uses the **Batch API** unless `--sync` is passed (`corpus_commands.py:95-96,212-215`).
  - **Anthropic runs synchronously only**, with 8 workers (`corpus_commands.py:76,212-215`; `providers.py:189-209`).
  - With `fake`, a paid command refuses to write to a non-test database unless `--allow-fake` is passed (`corpus_commands.py:112-122`).

### 6.2 Budget caps

- `CORPUS_BUDGET_USD` defaults to **$100** and is a hard cap on **all spend recorded in `corpus.llm_spend`, cumulative across runs**, plus batches still in flight (`config.py:41`; `budget.py:42-78`).
- `CORPUS_OCR_BUDGET_USD` defaults to **$10**, a sub-cap for OCR (`config.py:42`).
- **When the cap is checked.** Before every paid stage and before each batch file (`corpus_commands.py:196-201,256-269`; `runner.py:244-255`).
- **What happens when it is reached.**
  - A standalone command refuses to run and says how many tasks would fit.
  - `corpus run` runs only the part that fits (`corpus_commands.py:280-300`; `corpus_run.py:8-11`).
- **Inferred operational consequence:** after the first full run, adding sources needs headroom under the same cumulative ledger. AGENTS.md rule 1 says to set the cap to the real credit (`AGENTS.md:32-34`).

### 6.3 Prices and cost per unit

Prices, in USD per 1M tokens on the batch basis (`budget.py:4-11`; sync costs ×2, `budget.py:12`):
- `gpt-5-nano`: 0.025 input / 0.2 output;
- `gpt-5-mini`: 0.125 / 1.0;
- `text-embedding-3-large`: 0.065;
- Haiku 4.5: 0.5 / 2.5, which is half the list price, so the sync price works out to $1 / $5.

**Computed per-unit estimates.** `scratchpad/newpipe/cost_from_constants.py` rebuilds the prompts from `describe.py` and applies the pipeline's own estimator: tokens = characters ÷ 3 (`budget.py:13`), output 110 tokens per language + 40 (`describe.py:35-36`). OCR uses the placeholder of 1,500 image tokens (`budget.py:14`), which the pilot replaces with a measured value.

| Unit | OpenAI Batch (nano/mini) | OpenAI sync | Anthropic (sync, Haiku 4.5) |
|---|---|---|---|
| 1 chunk description, 1 language, ~1,000 characters (about 1,523 tokens in, 150 out) | $0.000068 | $0.000136 | $0.002273 |
| 1,000 such chunks | **≈ $0.07** | ≈ $0.14 | **≈ $2.27** |
| 1 document description, 1 language, 3,000-character excerpt | $0.000405 | $0.000810 | $0.002790 |
| 1 OCR page | $0.000913 | $0.001825 | $0.005200 |

**Multipliers you need to apply.**
- **Every HTML or PDF chunk is its own task per language.** The `align_key` contains the language (`html_page.py:64`, `pdf.py:80,84`), and tasks are grouped by `align_key` (`describe.py:165-171`). A bilingual site therefore pays twice per chunk. Fedlex articles share one task across languages (`fedlex_akn.py:81`).
- **Each chunk task also includes** the 2,413-character topic list and the ~700-character prompt (script output), which is why even short chunks cost about 1,300 input tokens.

**Documented data points (not verified).**
- About 130k chunks cost "roughly $14 at batch prices" (`README.md:90-91`).
- Fedlex ≈ $2.70 (`ENCODING-RUNBOOK.md:171-172`).
- bge-m3 runs at 12.4 chunks/s on an M1 Pro (ADR 0006:8).

### 6.4 How to estimate a new source

1. Fetch it for free (§6.6).
2. Run `corpus estimate`. It prints OCR, document, chunk and projected-chunk estimates, the embedding estimate for each index, batches in flight, spend so far, and a "total estimate" line (`corpus_commands.py:339-360`; `ENCODING-RUNBOOK.md:153-172`).
   - **It has no per-source filter**: `estimate_cmd` takes no options (`corpus_commands.py:341`), and `describe` and `run` also process *all* pending work (`corpus_commands.py:504-507`, `corpus_run.py:174-177`). The difference against the previous total is the new source's share.
3. `corpus ocr --pilot 10` measures the real OCR cost per page (`ENCODING-RUNBOOK.md:174-184`).
4. `corpus run --dry-run` prints the plan and the estimates without writing anything (`corpus_run.py:136-153`).

### 6.5 Incremental fetch

- The known URLs come from `corpus.fetch_state` for that source (`persist.py:78-81`).
- The frontier is always fetched in full; only the revisit queue is sent conditionally (§3.6).
- Unchanged content: `unchanged` / touched. Changed content: a new version, with the old one superseded. `404`/`410` or a redirect: withdrawn (`persist.py:190-223,254-264`; `html.py:276-299`).
- **Descriptions and vectors are re-used for identical chunk text**, so re-fetching costs nothing for unchanged chunks (`persist.py:148-163`; `embed.py:89-115`).
- Only new or changed chunks create new describe and embed work (`describe.py:165-173`; `embed.py:45-61`).
- Never run two fetches of the same source at once (`AGENTS.md:48-51`).
- **Inferred:** narrowing a source's `allow_prefixes` later does not withdraw documents already stored outside the new prefixes. Out-of-scope URLs in the revisit queue are skipped (`html.py:247`), and there is no other path that deletes or withdraws them.
- **Inferred:** because `corpus index` uses `create index if not exists` (`embed.py:313-318`), vectors added after the first HNSW build go into the existing indexes as they are inserted. The code notes that inserting into a live HNSW index is "far slower" (`embed.py:300`).

### 6.6 Steps to add a source on main (runbook, AGENTS.md, plan)

1. **Add an entry** to `manifests/declared-scope.yaml` (AGENTS.md:56-60; `ENCODING-RUNBOOK.md:70-71`). The skeleton below is derived from the model; the placeholders are yours to fill.
   ```yaml
   - id: <a-z0-9_>
     name: <display name>
     publisher: <office or commune>
     authority: official_info          # or federal_law | cantonal_law | municipal_law | institutional
     level: municipal                  # or federal | cantonal (stored only)
     extent_id: CH-<XX>-<BFS>          # must exist in public.location
     connector: html
     tier: 1                           # the runbook fetches --tier 1 only
     languages: [de]                   # the first entry is the default for pages without a declared language
     config:
       start_urls: ["https://…"]       # must fall inside allow_prefixes, or they are skipped silently
       allow_prefixes: ["https://…/"]  # must not overlap any other source (including their pdf_allow_prefixes)
       # optional: pdf_allow_prefixes, pdf_link_patterns, content_selector, language_links_selector,
       #           sitemap_urls, sitemap_include, max_pages (300), max_pdfs (50), delay_seconds
   ```
2. **Once per database:** `db seed` and then `corpus init`. **Recommended:** `corpus check-manifest manifests/declared-scope.yaml`, which needs the database and the network. It checks extents and requests every start URL, printing the status, robots verdict and number of alternates (Plan `encoding-track.md:4436,4761-4766`; `corpus_source_commands.py:118-137`). Note that it prints neither titles nor section counts.
3. **Make sure no fetch is running:** `pgrep -f "corpus fetch"` must print nothing (`ENCODING-RUNBOOK.md:75-79`).
4. **Fetch:** `corpus fetch --manifest manifests/declared-scope.yaml --tier 1 --source <id>` (repeat `--source` for more sources), then `corpus status` (`ENCODING-RUNBOOK.md:84-88`; `--source` at `corpus_source_commands.py:149`).
5. **Smoke-test the key:** `corpus describe --what docs --limit 1 --sync` (`AGENTS.md:35-37`).
6. **Estimate:** `corpus estimate`, then `corpus run --dry-run` (`ENCODING-RUNBOOK.md:18-19`).
7. **Run:** `corpus run` inside tmux; re-run it to continue (`ENCODING-RUNBOOK.md:20-28`).
8. **Check:** `corpus status` and review the quarantine (`ENCODING-RUNBOOK.md:310-329`).
9. **Before users see it:** the serving track must switch the server to `corpus.*` (§1.2 step 9). For places outside the 6 + 7 lists, the planned `scope.py` would also need to change (§5.3).

### 6.7 Constraints that matter for the ~150 sub-national sources

- **Prefix overlaps are rejected when the manifest loads** (`manifest.py:101-116`).
  - Whole hosts are already claimed: `https://www.ge.ch/`, `https://www4.ti.ch/`, `https://www.bern.ch/`, `https://www.lausanne.ch/`, `https://www.geneve.ch/`, `https://www.chur.ch/`, `https://www.scuol.net/` (`declared-scope.yaml:351,365,413,430,447,480,498`).
  - Whole language trees are claimed on `www.ch.ch`, `www.stadt-zuerich.ch/de|en/`, `www.be.ch/de|fr/` (plus `/content/dam/`), `www.gr.ch/DE|RM|IT/`, seven `*.admin.ch/{lang}/` trees (bag, bwo, bk, bazg, bj, estv, kmu), and `arbeit.swiss/{lang}/` and `ahv-iv.ch/{lang}/` (`:38,399,318,321,380,71,92,112,133,194,214,235,154,170`).
  - `zh.ch`'s PDF area `/content/dam/` is claimed (`:304`).
  - A new source on any of these needs the existing entry to be narrowed. At the document level, the first source that stores a URL owns it (`persist.py:196-199`).
- **Extents.**
  - Districts, regions, inter-communal bodies and concordats have no node (§2.3).
  - **Inferred:** such sources can only be filed at canton or commune level.
  - There is no narrowing, so every page of a source gets the source's single extent (`persist.py:131,141`).
- **Tier.**
  - Tier 2 or 3 sources are not fetched by the runbook's `--tier 1` command (`manifest.py:130`).
  - Plan: the planned scope logic ignores tiers and uses the hard-coded lists (§5.3).
- **Unsupported formats.** Sources whose value lies in JSON, ICS, XLSX, POST or JS-rendered data need new code (§3.8). Adding a connector type touches the manifest `Literal` (`manifest.py:21`), the database CHECK constraint (`schema.sql:49`) and the connector map in `fetch_cmd` (`corpus_source_commands.py:159-161`). **Inferred** from those three places.
- **Politeness gaps** (§3.5): PDFs are not checked against robots.txt and get only a 0.5 s delay; robots rules are checked for `*` only; a robots.txt that answers 403 blocks the whole host.

---

## 7. What changed from the old pipeline (1cb7f49) to main

Scope note: the old fetchers `html_crawl.py`, `pdf.py`, `retry.py` and `fetchers/__init__.py` are **identical** at 1cb7f49 and 159ac23 (`git diff --stat` is empty). Their old behaviour is still what `ingest` does on main.

| Capability | Old (1cb7f49) | New (corpus, 159ac23) | Verdict | Evidence |
|---|---|---|---|---|
| Source declaration | One YAML file per source in the registry, then `db seed` into `public.source` | One manifest file, read by `corpus fetch` | **Changed** | `1cb7f49:src/swiss_grounding/registry/loader.py:19-22`; `manifest.py:119-131` |
| Source fields | `id, name, base_url, default_extent_id, authority, categories, fetch_strategy, fetch_config, allow_narrowing, llm_tagging, license, origin` | `id` (pattern), `name`, `publisher`, `authority`, `level`, `extent_id`, `connector`, `tier`, `languages`, `config`, `retrieved_via` | **Changed** | `1cb7f49:…/registry/models.py:36-53`; `manifest.py:12-25` |
| `fetch_strategy: api` (JSON feed, templates, `event_date`) | `ApiFetcher` | no connector | **Removed** (old path only) | `1cb7f49:…/fetchers/api.py:83-126`; `manifest.py:21` |
| `fetch_strategy: pdf` (fixed `urls` list) | `PdfFetcher` over `fetch_config.urls` | PDFs only as links from crawled pages | **Removed as a strategy** | `1cb7f49:…/fetchers/pdf.py:31-35`; `html.py:317-326` |
| `html_crawl` → `html` | `base_url` + `path_allowlist` path prefixes + `start_paths`; **same host only** | absolute `start_urls` and `allow_prefixes`, several hosts allowed, disjointness enforced | **Changed** | `1cb7f49:…/html_crawl.py:40-45,86-94`; `html.py:186-199`; `manifest.py:101-111` |
| `fedlex_sparql` → `fedlex` | de, fr, it; current consolidation only (`LIMIT 1`) | de, fr, it + optional en; current and scheduled; article breadcrumbs and paragraphs; titles; XML saved | **Changed** | `1cb7f49:…/fetchers/fedlex.py:20-49`; `fedlex.py:19-26,60-66,163-213` |
| `categories` (10) | stamped on every document of the source at confidence 1.0 and merged with the model's tags | no source-level topics; 20 topics per chunk from the model, plus the SR prior for Fedlex | **Removed / replaced** | `1cb7f49:…/ingest/enrich.py:24-39`; `describe.py:84-87`; `persist.py:84-88` |
| `allow_narrowing` / narrowing | `narrow_extent` moved documents to more specific extents (never for law sources) | none; always the source's `extent_id` | **Removed** | `1cb7f49:…/enrich.py:40-44`; `1cb7f49:…/registry/models.py:63-67`; `persist.py:131,141`; grep |
| `llm_tagging` | `false` skipped the model classifier and used the source's categories | none; every non-boilerplate chunk goes through the paid describe stage | **Removed** | `1cb7f49:…/enrich.py:38`; `describe.py:165-173` |
| Translation to English | a model call per section and for the title | none; the original language is stored; descriptions per language; cross-language matching by bge-m3 (ADR 0011) | **Removed** | `1cb7f49:…/enrich.py:15-21,35-37`; `describe.py:45-66` |
| `license` | field on the source, returned in citations | no field | **Removed** | `1cb7f49:…/registry/models.py:52`; grep `license` in `corpus/` and the manifest |
| Calendar `event_date` | `document.event_date` from the api fetcher | no column | **Removed** | `1cb7f49:…/fetchers/api.py:72-80`; `schema.sql:62-86` |
| Conditional requests | **every** known URL sent with If-None-Match / If-Modified-Since, so a 304 hid the page's links | only revisit-queue URLs are conditional; the frontier is always fetched in full | **Changed** | `1cb7f49:…/html_crawl.py:45,96-101`; `crawl_queue.py:1-8`; `html.py:219-231` |
| PDF change detection | **HEAD first**: HEAD `404`/`410` → skipped (reported gone if known, **dropped silently if unknown**); `Last-Modified` equal → unchanged | **no HEAD**: conditional GET (ETag and Last-Modified); a 404 on an unknown PDF is recorded as an error | **Changed** | `1cb7f49:…/fetchers/pdf.py:36-47`; `pdf.py:148-182` |
| PDF text and OCR | pypdf per page; empty pages dropped; the document fails if there is no text at all | pypdf per page; pages under 80 characters are rendered and **OCR'd** by the paid model; 30 MB cap; content-type and `%PDF` checks | **Changed / new** | `1cb7f49:…/fetchers/pdf.py:53-63`; `pdf.py:35-41,61-90,118-146`; `ocr.py` |
| Crawl limits | global `CRAWL_MAX_PAGES=200` for every source | `max_pages` per source (default 300) and `max_pdfs` (default 50); `CRAWL_MAX_PAGES` is unused by the corpus | **Changed** | `1cb7f49:…/config.py:22`; `1cb7f49:…/fetchers/__init__.py:27-28`; `html.py:32-33,236,241`; grep |
| Delay | a fixed `time.sleep(0.5)` after each page, one thread | per-host throttle across threads; base 0.5 s, `delay_seconds`, robots `Crawl-delay` (capped at 30 s), 429/503 escalation; PDFs 0.5 s only | **Changed** | `1cb7f49:…/html_crawl.py:72-73`; `html.py:74-85,164-184`; `politeness.py:24-74` |
| robots.txt | `urllib.robotparser`, `can_fetch("*")`, **first matching rule wins** (offline check: be.ch PDF → `False`); non-200 or failure → **allow everything** (offline check: `True`); no redirect follow, no Crawl-delay | protego, **longest match** (be.ch PDF → `True`); failure/401/403/5xx → **host blocked**; 404 → allow; follows redirects; `Crawl-delay` honoured; still `"*"` only; `RESPECT_ROBOTS` switch; PDFs not checked | **Changed** | `1cb7f49:…/html_crawl.py:77-84,94`; `html.py:38,46-62,172-184`; `robots_semantics.py` output |
| HTTP client and TLS | httpx, `HTTPTransport(retries=2)`, timeout 20 s, UA `swiss-grounding/0.1 (+https://github.com/thedionysus/swisscom-hackathon)`, default TLS verification | httpx, **no transport retries**, per-call timeouts of 20–60 s, UA `Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)`, default TLS verification | **Changed** | `1cb7f49:…/fetchers/__init__.py:13-17`; `corpus_source_commands.py:46-47`; `config.py:51-53`; grep `verify=` |
| Retries | connection-level retries on every request; Fedlex RetryPolicy (3 attempts, 0.5 s×n) | HTML, PDF and sitemaps: 429/503 only (3 attempts, Retry-After); Fedlex: 3 attempts on transport errors, 5xx and 429 | **Changed** | `1cb7f49:…/fetchers/__init__.py:15,20-21`; `politeness.py:108-127`; `fedlex.py:103-113` |
| HTML title | first `<h1>` in the root, **hidden or not**; else `<title>`; else URL | first **visible** `<h1>` (hidden-heading detection); `content_selector` can move the root | **Changed** | `git diff 1cb7f49 159ac23 -- ingest/html_sections.py`; `html_sections.py:60-99`; `html_page.py:59` |
| "Hauptinhalt" titles on one CMS | old rule picked the first `<h1>` | fixed **only if** that `<h1>` is hidden by one of the recognised conventions, **or** a `content_selector` excludes it | **Not verified**: no fixture or test covers it (grep finds "Hauptinhalt" only in skip links in two fixtures) | `html_sections.py:17-21,60-71`; grep |
| PDF title | the file name (`url.rsplit("/",1)[-1]`) | metadata title → link text or page title → file name | **Changed** | `1cb7f49:…/fetchers/pdf.py:65`; `pdf.py:64-65` |
| Content extraction | `html_sections` with no selector | the same module plus `content_selector`, hidden-heading removal, comment and CMS-marker stripping | **Changed** (it is shared code) | `html_page.py:10,12-27`; diff of `html_sections.py` |
| Language handling | one `fetch_config.language` (default `de`) + `<html lang>` | several `languages`; alternates from hreflang, switcher and Nuxt; translation groups; pages in undeclared languages are not stored | **Changed** | `1cb7f49:…/html_crawl.py:110`; `html_meta.py:154-169`; `html.py:94-140`; `html_page.py:52-58` |
| Sitemaps | — | seeding, index files, gzip, include regexes | **New** | `sitemap.py` |
| PDF discovery by regex | — | `pdf_link_patterns` | **New** | `html_meta.py:150-151` |
| Storage | `public` schema, English text, one embedding column | `corpus` schema, partitioned by language, separate embedding tables (bge-m3 dense and sparse; optional OpenAI `halfvec(3072)`) | **Changed** | `db/schema.sql:50-101`; `corpus/schema.sql:91-143` |
| Budget, ledger, Batch API and resume, quarantine | — | `llm_spend`, `batch_job`, `quarantine`, caps | **New** | `schema.sql:176-209`; `budget.py`; `runner.py` |
| Fetch unit of commit | the whole `ingest` run commits when it exits (per the README) | each document is committed on its own, but only after that source's crawl finishes | **Changed** | `README.md:177-178`; `fetch_stage.py:1-6,43-64,82-85` |
| Served by the MCP server | yes | **no** (§1.3) | — | `retrieval/search.py:92-107`; grep |

---

## Open questions

1. **When does serving switch to `corpus.*`?** There is no serving branch on origin (`git branch -r`). Until then, sources added to the manifest are not visible to users. Adding them in parallel to the old registry and `ingest` would still work technically (`cli/main.py:198-228`), but it goes through the old pipeline, with translation and the old categories. Is that wanted?
2. **Will the declared scope grow?** The planned `scope.py` hard-codes 6 cantons and 7 municipalities, and the planned search cuts the searched path to those levels (`serving-track.md:582-610,2464-2468`). Sub-national sources outside those lists would never be retrieved unless the lists are widened. Which of the ~150 sources are inside the 6 + 7?
3. **Tiers.** Should the new sources be tier 1? Otherwise the runbook's `--tier 1` skips them. And how should tier relate to the scope lists?
4. **Overlapping hosts.** Many new sources probably sit on hosts that existing entries already claim (§6.7). Should those entries be split or narrowed? Changing an existing prefix also changes what that source keeps crawling. Documents already stored outside new prefixes are not withdrawn (inferred, §6.5).
5. **Extents below canton and above commune** (districts, regions, special-purpose associations). Should they go at canton level, or should the location tree get new nodes?
6. **Non-HTML data** (JSON, ICS, XLSX, POST, Plone REST). Who writes a connector or a bespoke importer (the OpenERZ pattern)? What would it produce: text documents, or new lookup tools (ADR 0015 allows adding a tool that "does a job no other tool does", 0015:30)?
7. **Politeness gaps** (§3.5). Should PDFs be checked against robots.txt and the host's Crawl-delay, and should robots rules be evaluated for the agent actually sent? Today a site that blocks this bot by name is not respected (offline check).
8. **Stale comment.** The be.ch comment in the manifest (`declared-scope.yaml:319-320`, "Python's robotparser … refused") was added in 524dd99 (14:03) **before** the protego fix d16ad2e (14:11) (`git log`). It no longer describes the code.
9. **"Hauptinhalt" titles.** Does the new hidden-`<h1>` rule fix that CMS, or does it need a `content_selector`? This needs a fetched sample; `check-manifest` does not show titles.
10. **Provider choice for the extra volume.** With only an Anthropic key, chunk descriptions cost about 30× more per chunk than on the OpenAI Batch API, using the code's own price table (§6.3). The prices in `budget.py` are marked "Verify on the day of the run" (`budget.py:3`).
11. **Cantonal law (ADR 0008)** has no connector yet. Is it still planned, and at which tier?
12. **README is out of date.** "How it works" (`README.md:10-19`) and "Tools" (`:144-156`) still describe the old pipeline and tools.
