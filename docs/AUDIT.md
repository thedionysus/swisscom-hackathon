# Swiss Grounding MCP — Audit of the current system

Audited 2026-09-23 against commit `9c8fd14` (main), the live database at `localhost:5433`, and the documents in `docs/`, `CONTEXT.md` and `README.md`. Every claim about behaviour cites `path:line` at that commit; claims marked *measured* were run against the live database or endpoints during the audit; claims marked *inferred* are conclusions. Paths are relative to `src/swiss_grounding/` unless they start with `docs/`, `tests/`, `evals/` or are a root file.

The audit was read-only with one exception: `swiss-grounding eval probes` inserts into `eval_run` even without `--record` (`cli/eval_commands.py:124-128`), so the live probe run added 47 rows as run `01adb0d0a495`. Nothing else was written.

## 0. Summary

The prototype does one thing well and by design: **jurisdiction is a hard filter**. A question about Kreis 3 can only ever see chunks filed at `CH`, `CH-ZH`, `CH-ZH-261` or `CH-ZH-261-K3`, and the response says per level whether anything is indexed there. Topic became a second hard filter on 2026-09-21. Around that core, the things the brief cares about are mostly not there yet:

- **Everything is searched in English.** Documents are machine-translated at ingest, both indexes are built from the translation plus generated context, and the original text is stored but never indexed. A German keyword, an SR number or "Art. 336c" matches nothing in the keyword arm (*measured*, ADR 0004 addendum).
- **Within the jurisdiction, ranking is not principled.** A chunk within cosine distance 0.55 of the query — a constant the code itself calls uncalibrated — is ordered by how local it is, and only then by an additive score whose weights were hand-picked in the design spec and never tuned. A local chunk at distance 0.54 always outranks a federal article at 0.20. Nothing abstains on weak evidence: `no_evidence` fires only when the SQL filter returns zero rows.
- **The candidate pool is shared by the whole path.** Each retrieval arm keeps 50 chunks across federal, cantonal and municipal layers together; federal law is 563 of 719 chunks today and 4,710 of 5,195 in the larger database issue #34 measured. Local chunks compete with federal articles for pool slots before any specificity logic runs.
- **Ingestion covers three of four strategies, one language per source, and loses legal structure.** `Abs.`/`lit.` numbers and chapter headings are dropped from Fedlex; PDFs have no OCR and no registered source; DOCX/CSV/ICS/XML have no parser; a future Fedlex consolidation is stored as in force; a superseded consolidation never retires.
- **The evals cannot tell us whether answers are correct.** 47 hand-written probes check status, resolved extent and source membership on one canton, three categories and one language; there is no expected-document set, no recall/MRR, no `no_evidence` probe, and half of the committed judge baseline graded answers from a failed MCP connection as passes.
- **The live corpus is small and partly broken:** 108 documents, 719 chunks, three of six sources empty, canton ZH at 0 documents, generated context on 0 chunks, five Fedlex acts titled `SR nnn`, every Fedlex chunk tagged with all five topics. Live probes score 34/47, not the recorded 44/47.

Section 11 ranks the weaknesses. Sections 1–9 are the nine areas the brief asked for; section 10 is the live state.

## Architecture

```mermaid
flowchart LR
  subgraph Sources
    FX[Fedlex SPARQL + Akoma Ntoso XML]
    HT[HTML sites: ch.ch, zh.ch, stadt-zuerich.ch, schweizer-wanderwege.ch, geneve.ch]
    AP[Open ERZ JSON calendar]
    PD[PDF strategy: no source registered]
  end
  subgraph Ingest["Ingestion CLI (sequential, one transaction per run)"]
    F[fetchers/*] --> E[enrich.py: translate per section, narrow extent]
    E --> C[chunking.py: 1500 chars / 150 overlap]
    C --> D[context.py: per-document summary, per-chunk context + topics + boilerplate verdict]
    D --> P[persist.py: embed context+text, version, diff]
  end
  LLM[(Anthropic API\nclaude-sonnet-5)]
  EMB[(bge-m3 local\n1024-d)]
  FX & HT & AP & PD --> F
  E -. translate .-> LLM
  D -. describe .-> LLM
  P -. embed .-> EMB
  subgraph DB["PostgreSQL 16 + pgvector 0.8.6"]
    L[(location 2,183 nodes\npath text[])]
    S[(source)]
    DOC[(document\nversion, status, valid_from/to)]
    CH[(chunk\nembedding HNSW, tsv GIN,\nextent_id, categories)]
    ER[(eval_run, ingest_run,\nfetch_state, document_change)]
  end
  P --> DOC & CH
  subgraph Query["Query core (retrieval/query_core.py)"]
    R[resolve location\nlocations/resolver.py] --> T[resolve topics\nretrieval/topics.py]
    T --> H[hybrid_search: dense top-50 + lexical top-50\nunder FILTER, RRF]
    H --> RR[rerank: tier ⟵ hops if distance ≤ 0.55,\nthen additive score]
    RR --> DV[diversify: caps 2/doc, 3/series, 6 calendar\n+ force most-specific]
    DV --> CT[cite: tier, distance, snippets]
  end
  GEO[(GeoAdmin SearchServer)]
  R -. fallback .-> GEO
  L --> R
  CH & DOC --> H
  EMB --> H
  subgraph Surfaces
    MCP[MCP server: 6 tools\nstdio / streamable HTTP]
    CLI[CLI query]
    EV[eval probes / judge]
  end
  MCP & CLI & EV --> Query
```

External calls at query time: GeoAdmin only on a resolver miss (`locations/resolver.py:122-155`); the embedder runs in-process; **no model call is ever made while answering** (ADR 0004). External calls at ingest time: source fetches, Fedlex SPARQL, and one Anthropic call per section, per title, per document summary and per chunk description (§1.6).

## Data flow end to end

**Ingest** (`ingest/pipeline.py:66-75`, driven by `cli/main.py:209-226`):

1. `db seed` upserts the location tree (country, 26 cantons, 2,110 communes from `locations/data/communes.csv`, 12 Zurich Kreise + 34 Quartiere) and the seven YAML sources (`cli/main.py:91-103`).
2. `ingest --source X` opens **one connection for the whole run** (`cli/main.py:209`; commit only on exit, `db/connection.py:17`) and, per source, hands the fetcher the known URLs with their ETag/Last-Modified/content hash (`ingest/fetch_state.py:13-18`).
3. The fetcher returns `FetchedDocument`s: `(url, title, language, identifier, valid_from, valid_to, in_force, event_date, sections[heading_path, anchor, text])` (`ingest/models.py`). Fedlex: one section per `<article>`; HTML: one section per h1–h4; PDF: one per page; API: one per record.
4. `enrich` translates every section and the title to English with one Anthropic call each (skipped when `language == "en"`), then narrows the extent from the *English* title/headings/text under ADR 0002 rules (`ingest/enrich.py:21-51`).
5. `chunk_sections` splits the English text at 1,500 chars with 150 overlap; every piece keeps the **whole** original section (`ingest/chunking.py:11-12, 71`).
6. `describe_chunks` makes one summary call per document and one describe call per chunk returning `context`, `categories[{id, confidence}]`, `boilerplate` (`ingest/context.py:173-185`); furniture chunks are dropped; the summary is not stored.
7. `persist` compares `sha256(original section texts)` with the current row (`ingest/hashing.py:10-12`), and on change inserts a new document version, marks the old one `superseded`, embeds `context_en + " " + text_en` with bge-m3 and writes the chunk rows (`ingest/persist.py:69-82, 133-161`). URLs that disappeared become `withdrawn`.

**Query** (`retrieval/query_core.py:69-153`; every surface calls this):

1. Validate; refuse an `as_of` earlier than the oldest `valid_from` in the index.
2. Resolve `location` (or scan the question text for a place) to a node and its root-to-node path; ambiguity or no match → `needs_location`.
3. Build two query strings: dense = `question_en + " " + topic_en` (falls back to the verbatim question); lexical = the verbatim question (`retrieval/query_text.py:70-95`).
4. Resolve topics: caller's `topics` → deprecated `categories` → local bge-m3 classifier over the 10 category descriptions (`retrieval/topics.py:157-191`).
5. `hybrid_search`: dense `ORDER BY embedding <=> vector LIMIT 50` and lexical `websearch_to_tsquery('english', question) LIMIT 50`, both under `extent_id = ANY(path) AND categories && topics AND status/as_of`; RRF fusion; cosine distance backfilled for lexical-only hits (`retrieval/search.py:260-325`).
6. Coverage rows (documents per extent on the path) and, on an empty result, a census of which filter arm emptied it (`retrieval/search.py:160-190`, `retrieval/no_evidence.py`).
7. Rerank: `tier = hops` if `distance ≤ 0.55`; order by `(tier claimed?, tier, -score, chunk_id)`; nothing dropped (`retrieval/rerank.py:138-171`).
8. Diversify: caps 2 per document, 3 per calendar series, 6 upcoming calendar chunks; force-insert the single most specific candidate (`retrieval/diversify.py:122-165`).
9. Cite: 600-char snippets of `text_en` and `text_original`, `tier`, `distance`, extent, authority, `valid_from`, `retrieved_at`, `event_date` (`retrieval/cite.py:22-39`).

## 1. Ingestion

### 1.1 Strategies and formats

`FetchStrategy` has four values (`registry/models.py:29-33`); the seven registered sources use three of them:

| Source (`registry/sources/*.yaml`) | Strategy | Extent | Authority | Categories declared | Narrow | LLM tag |
|---|---|---|---|---|---|---|
| `fedlex` | fedlex_sparql | CH | federal_law | `[]` (16 SR numbers; 9 held back for issue #26) | no | yes |
| `ch_ch` | html_crawl (`/en/`) | CH | official_info | dogs, waste, taxes, transport, schools, health | yes | yes |
| `zh_ch` | html_crawl (3 `/de/` prefixes) | CH-ZH | official_info | hiking, dogs, waste, safety | yes | yes |
| `stadt_zuerich` | html_crawl (4 prefixes) | CH-ZH-261 | official_info | hiking, dogs, waste, parking | yes | yes |
| `ge_ville` | html_crawl (`/themes`, fr) | CH-GE-6621 | official_info | `[]` | yes | yes |
| `schweizer_wanderwege` | html_crawl | CH | institutional | hiking, safety | yes | yes |
| `open_erz` | api (JSON) | CH-ZH-261-K3 | official_info | waste | no | **no** |

`pdf` exists (`ingest/fetchers/pdf.py`) but no source uses it. `ge_ville` is in the repo but not in the database (`db seed` has not been re-run since commit `f4bb219`; *measured*).

| Strategy | Fetch | Parse | Structure kept | Structure lost |
|---|---|---|---|---|
| **fedlex_sparql** (`ingest/fetchers/fedlex.py`) | One SPARQL query per SR number (`:38-63`), `LIMIT 1` newest consolidation, one language per source (`:31,125`; `LANGUAGE_URI` knows de/fr/it only, `:23-27`); XML `GET` with retries (`:146-147`, `retry.py`) | Akoma Ntoso via `BeautifulSoup(xml, "xml")` (`:69`) | One section per `<article>` anywhere in the tree; `heading_path = "Art. N <heading>"`; `anchor = eId` (`:70-78`) | Chapter/title/section headings; `Abs.` and `lit.` numbers (only `<content>` is read, `:74`); footnotes and tables flattened; preamble and annex text outside `<article>` |
| **html_crawl** (`ingest/fetchers/html_crawl.py`, `ingest/html_sections.py`) | BFS from `start_paths`, same host, prefix allowlist, `max_pages` 200 (`html_crawl.py:41-52`); robots.txt with agent `*` (`:94`); fixed 0.5 s sleep; conditional requests; skips `.pdf .jpg … .xml .json .ics .csv` links (`:14`) | lxml + markdownify; content root = first of `main, article, [role=main], body`; drops `nav footer header script style noscript aside form` (`html_sections.py:10, 19`) | Sections split on h1–h4 with `heading_path = "H1 > H2 > H3"`; heading `id` as anchor; tables as Markdown pipe tables; lists as bullets (*measured offline*) | h5/h6 as structure; link targets; images and alt text; footnote links; `<aside>`/`<form>` content; `<meta>` dates; hreflang/alternate links; **every linked PDF** |
| **pdf** (`ingest/fetchers/pdf.py`) | `HEAD` then `GET` from a configured URL list | pypdf `extract_text()` per page (`:19-21`) | `heading_path = "Page N"`, `anchor = page=N` (`:57-60`) | **All** structure; **scanned pages yield nothing and the file is rejected** (`:59-63`, no OCR) |
| **api** (`ingest/fetchers/api.py`) | One `GET` with `{today}`/`{start}` rendered (`:44-58, 99-100`); no conditional request, retry, robots or delay | JSON records at `records_path` | One document per record; title/text from `str.format_map` templates; `event_date` from a named field (`:113-126`) | Every field not named in a template; pagination (one request, `limit=100`, issue #38) |

Not handled anywhere: DOCX/DOC, XLSX/CSV, ICS, Markdown files, generic XML, SPARQL other than Fedlex, JSON-LD. A `text/plain` response would go through the HTML parser (*inferred* from `html_crawl.py:107-109`).

### 1.2 Change detection, versioning, dedup

- Fetcher short-circuits: HTML 304 (`html_crawl.py:63-64`), PDF `Last-Modified` equality, Fedlex "URL already known" (`fedlex.py:142-144`), API none. Then `content_hash = sha256("\n␞".join(original section texts))` — **title, headings, anchors excluded** (`ingest/hashing.py:10-12`). The comparison runs *after* translation and description, so a page that changed trivially but was not served as 304 pays the full model bill (`ingest/pipeline.py:68-74`).
- Changed → new `document` row, `version + 1`, old row `superseded` with `superseded_by`, chunk diff by `sha256(text_en)` into `document_change` (`ingest/persist.py:73, 88-97, 147-160`). Because the diff hashes the *translation*, a non-deterministic re-translation reports unchanged articles as modified (*inferred*; no temperature set, `ingest/llm.py:276-279`).
- **Fedlex never supersedes.** A new consolidation is a new URL (the date is in the URL, `fedlex.py:108-111`), so it is `added`, and the fetcher never reports the old URL gone (`:162`); both stay `status = 'current'` (issue #30, live from 2026-09-30). README:130-132's versioning promise does not hold for Fedlex.
- **Future law is stored as in force.** The SPARQL filter excludes only *ended* consolidations (`fedlex.py:59`); the newest wins even if `dateApplicability` is in the future, and `in_force = (no end date)` (`:160`). *Measured:* SR 642.11 → 2029-01-01 (issue #26).
- Dedup: identity is `document.url` only (`persist.py:25-28`); no canonical-URL, cross-source or content dedup (issue #27). `fetch_state.url` is a global key, so a URL reached by two sources flips ownership (*inferred*).
- Transactions: **one for the entire `--all` run** (`cli/main.py:209`, `db/connection.py:17`; the per-document block at `pipeline.py:67` is a savepoint). A crash discards every source. `recontext`/`retitle` commit per chunk/document because of that lesson (`ingest/recontext.py:9-12`).
- Failures: per-document `try` (`pipeline.py:54-64`), reported as a count in `ingest_run.failed`; no quarantine table; failed URLs are re-fetched every run without limit. Exceptions outside that `try` (the fetch itself, `touch_unchanged`, `mark_withdrawn`) abort the run.

### 1.3 Provenance captured today

| Target field | Where | fedlex | html | pdf | api |
|---|---|---|---|---|---|
| Source URL / endpoint | `document.url` | consolidation page URL; the XML `fileUrl` actually fetched is **not stored** | requested URL (not the redirected one) | PDF URL | feed URL + `#record_id` |
| Publisher | none on the document; `source.name/base_url/license` via join at query time (`retrieval/search.py:15-16`) | | | | |
| Jurisdiction node(s) | `extent_id` (one node) + `extent_reason` | always `CH` | narrowed or default | default | default |
| Language | `document.language` | config or `de` | `<html lang>` or config or `de` | config or `de` | config or `en` |
| Category | `document.categories` jsonb roll-up; `chunk.categories text[]` (ids only) | per chunk | per chunk | per chunk | source fallback |
| Retrieval timestamp | `retrieved_at` — **refreshed on every unchanged sighting** (`persist.py:165`), so it means "last seen", not "fetched" | ✓ | ✓ | ✓ | ✓ |
| valid_from / valid_to / in_force | `document.*` | from JOLux | **NULL** | NULL | NULL |
| published_at | `document.published_at` | **never set by any fetcher** | NULL | NULL | NULL |
| Identifier | `document.identifier` | `SR n` | NULL | NULL | record id |

*Measured:* `valid_from` on 5 of 108 documents, `published_at` on 0. Consequence: any `as_of` excludes every non-Fedlex document, including the whole calendar (§7.2).

### 1.4 Language versions

None. No `hreflang`, `alternate`, `translation_group` or shared-identifier join exists anywhere in `src/`; the crawler reads `href` but never `rel`/`hreflang` (`html_sections.py:144-158`); allowlists confine each source to one language path; Fedlex fetches one language per source (`fedlex.py:125`). A second Fedlex source in `fr` would create documents sharing `identifier = "SR 455"` with nothing joining them. Issue #25 §2 and `docs/sources/source_catalogue.md:39-45` record the gap.

### 1.5 Maintenance commands (each encodes a past defect)

| Command | Does | Exists because |
|---|---|---|
| `retitle` (`ingest/retitle.py`) | Re-queries SPARQL for stored acts, rewrites titles (one translation call each), commits per document | The old query never bound `?title`; no re-ingest can repair a title (URL short-circuit + hash excludes titles) |
| `recontext` (`ingest/recontext.py`, 650 lines) | Re-describes every current chunk from stored English, writes `context_en`, topics, new embedding; deletes model-judged furniture; commits per chunk; refuses `SR nnn`-titled documents | ADR 0003/0005 changed what a chunk carries after the corpus was built and credits were gone |
| `reclean` (`ingest/reclean.py`) | Deletes chunks with heading `Navigation` or `Error Page (404)` and emptied documents | 79 canton/city chunks were pure navigation |
| `renarrow` (`ingest/renarrow.py`) | Re-runs narrowing over stored English text | Pre-ADR-0002 narrowing filed canton pages under the city |

Neither `retitle` nor `recontext` has run on the live database (API key returned 401 on 2026-09-22; plan §"Blocked").

### 1.6 Cost and scale

LLM calls per document (`ingest/enrich.py:33-43`, `ingest/context.py:173-185`, `ingest/llm.py:315-321`): S sections + 1 title (translation, skipped for English) + 1 summary + C chunks (describe) + up to C resamples. A Fedlex act with A articles ≈ 2A + 2 calls; `open_erz` = 0. Calls are synchronous `messages.create` with `max_tokens=4096` (`llm.py:13, 277`) and **no `stop_reason` check** — a heading-less page is one section (`html_sections.py:98, 122-123`), so long pages are silently truncated. No Batch API, no prompt caching, no per-section translation cache (a modified page re-translates every section).

What breaks at hundreds of sources: the run-wide transaction; strictly sequential I/O and model calls (0.5 s sleep per page → ≥100 s per 200-page site before any model call); crawl frontier starvation (known URLs are queued first and 304s count toward `max_pages`, `html_crawl.py:44-45, 52, 57` — a site with ≥200 known pages never discovers a new one); whole-source materialisation in memory (`ingest/models.py:46-50`); one SPARQL round trip per hand-listed SR number; YAML files + DB rows as the registry with no delete (issue #25 §5); the 10-category hard ceiling (`registry/models.py:57-63`); `CITY_DOMAINS` with one entry (`registry/official_domains.py:6-8`); narrowing rebuilding its name index per document over 2,183 nodes (`ingest/narrowing.py:175`).

## 2. Processing and chunking

- **Unit and size:** characters of the *English* text, `max_chars = 1500`, `overlap_chars = 150` (`ingest/chunking.py:11-12`). One chunk per section when it fits (`:21-22`); otherwise split at the last `". "` past the midpoint, else a hard cut mid-word (`:26-31`). No token counting.
- **Boundaries:** Fedlex article ↔ chunk 1:1 unless >1,500 chars; HTML section per h1–h4; API record ↔ chunk 1:1; PDF page ↔ chunk. Tables survive as Markdown but can be cut by the split.
- **Split sections carry the whole original.** Every piece of a split section stores the *entire* section's `text_original` with `original_is_parallel = False` (`chunking.py:71-72`). *Measured:* `schweizer_wanderwege` chunks hold up to 26,540 chars of original next to a 1,500-char English chunk. The 600-char `snippet_original` a citation shows is therefore the section's opening beside a later English passage (`retrieval/cite.py:33`).
- **Metadata per chunk** (`ingest/persist.py:74-82`, `db/schema.sql:82-104`): `document_id, ordinal, text_original, text_en, context_en, heading_path, anchor, embedding, chunk_hash, extent_id, authority, categories, document_status, tsv`. Not on the chunk: language, timestamp, source, tag confidence (discarded at `persist.py:82`), the document summary (never stored).
- **What is embedded and indexed:** `context_en + " " + text_en` for both the vector (`context.py:36, 41-49`; `persist.py:69`) and `tsv = to_tsvector('english', btrim(context_en || ' ' || text_en))` (`schema.sql:108-111`). `text_original`, `title_*`, `identifier`, `heading_path` are in **neither** index (issues #10, #24).
- **Generated context (ADR 0005):** one summary per document ("what this document is, what it covers", first 6,000 chars, `llm.py:39-44`) feeds one describe call per chunk that returns `context`, `categories`, `boilerplate` (`llm.py:45-64`). Templated sources get `"From {source}. {title}"` with no call. *Measured:* `context_en` is empty on all 719 live chunks.
- **Boilerplate:** two literal headings (`ingest/boilerplate.py:25-28`) plus the model's per-chunk verdict; the fake LLM never says `true` (`llm.py:231`). Issue #28 measured 8.5% junk on a real municipal crawl.

## 3. Jurisdiction hierarchy and location resolution

### 3.1 The tree

Four levels only: `country, canton, municipality, neighborhood` (`locations/models.py:6-10`; check constraint `db/schema.sql:7`). **No district/Bezirk level**: the register's `district` column (144 distinct values) is dropped at `locations/register.py:70-86`; *measured:* "Bezirk Horgen" → `CH-ZH` via `geoadmin_approximate`. Ids: `CH`, `CH-ZH`, `CH-ZH-261`, `CH-ZH-261-K3`, `CH-ZH-261-K3-ALT-WIEDIKON` (`locations/seed.py:70-108`, `register.py:82`). `path` is computed in Python and stored as `text[]` with a GIN index (`locations/tree.py:38-46`, `repository.py:38-51`).

*Measured live:* 1 country, 26 cantons, 2,110 municipalities, 46 neighbourhoods (12 Zurich Kreise + 34 Quartiere) = 2,183 nodes; `bfs_id` and `lindas_uri` on all cantons and communes, none on Kreise/Quartiere. Label languages: country and cantons de/fr/it/en; **every commune a single label stored under `"de"` whatever its real language** (`register.py:84` — `CH-GE-6621` is `{"de": "Genève"}`); Kreise de+en; Quartiere de only. PLZ aliases: 1,945 on 1,263 communes; 859 communes have none because all their PLZs are shared (`register.py:66, 73-75`); Zurich's PLZs sit on the Kreise. Romansh: the canton alias `Grischun` and nothing else.

### 3.2 Identifiers and names

Node ids are built from official identifiers (canton abbreviation + BFS number), and the GeoAdmin path looks up by BFS (`resolver.py:136`, `tree.py:62-64`). But **every lookup from user text is by normalised free-text name/alias** (`tree.py:8-12, 55-60`); nothing accepts an id or BFS number as input. Communes get generated aliases `Gemeinde X`, `Stadt X`, `X <AB>`, `X (<AB>)` (`register.py:64-67`). Bilingual slash names (`Biel/Bienne`, `Domat/Ems`, 11 communes) are one verbatim label with no half-name aliases.

Mergers: not handled. `register_fetch.parse_agvch` keeps Level-3 rows of one snapshot date and discards `HistoricalCode`, `ValidFrom`, `ValidTo` (`locations/register_fetch.py:49-56`); no eCH-0071 histId, no successor link, no `valid_to` on `location`. `prune_locations` keeps a stale node only if referenced, leaving it on no current path (`repository.py:10-27, 60-72`).

### 3.3 Resolver (`locations/resolver.py:67-84`)

Order: strip a level marker (`locations/markers.py:6-26`) → exact alias lookup, level-filtered when marked, **no fallback when the marked level has no match** (`:72-78`) → ambiguity rules (`:86-103`: neighbourhood-only matches that prefix a commune name, common words `city/hard/werd/enge`, several nodes off one path → `AmbiguousLocation`) → alias scan of the whole input (`question_scan.py`, `prose=False`) → GeoAdmin `SearchServer?origins=gg25&limit=5`, first hit only, accepted when its BFS is in the tree **and** every input token matches the label (`fuzzy.py:23-34`; `resolver.py:136-140`), or approximated to the canton when a token is shared (`:141-154`) → single-token fuzzy ≥6 chars within one edit (`:157-173`).

When no `location` is given, the question is scanned with `prose=True` (`question_scan.py:139-168`): n-gram alias hits, capitalisation and sentence-position guards, a Quartier requires its city to be named too (`:93-94`); GeoAdmin is never consulted. **Within one hit that maps to several nodes, `nodes[0]` is taken and the rest become `alternatives`** (`:165-167`) — no ambiguity is raised. *Measured:* "How do I pay dog tax in Wil?" → `CH-ZH-71` (Wil ZH) with `CH-SG-3427` as an alternative; "Rickenbach" → one of five. The explicit-`location` path does ask (`resolver.py:97-98`); this contradicts `CONTEXT.md:17-19`.

Other *measured* behaviour: Biel, Stadt Biel, Domat, Ems, Ilanz → `None` (contradicts `CONTEXT.md:29-31`); Genève/Luzern/St. Gallen → city but Geneva/Genf/Lucerne/Sankt Gallen → canton; "Stadt Genf", "Ville de Genève" → `None`; "Was gilt in St. Gallen?" → `None` (punctuation stripping vs dotted alias key, `question_scan.py:36-39`); Konstanz, Milano, Wien, Lörrach → `None` with the same message as a typo; **Lindau, Rheinfelden, Laufenburg, Stein am Rhein → Swiss communes and Freiburg → canton FR, silently, method `alias`**; "Emmental" → Langnau im Emmental via GeoAdmin because `tokens_covered` is one-directional (`fuzzy.py:31-34`).

### 3.4 Document → node mapping

Source default extent, then narrowing when `allow_narrowing` (never for law, `registry/models.py:65-69`), over the **English** text (`ingest/enrich.py:43-47`). `ingest/narrowing.py:172-194` implements ADR 0002: marker phrases anywhere (`:19-43`), bare names only in title/heading and never an ancestor of the default (`:141-161`), common-word Quartier *and* an undocumented common-word commune list (`:11-15`), PLZ in body only after a cue (`:121-128`), deepest common ancestor, never widen. Bare names resolve through a global name map where the **last-inserted duplicate wins** (`:58-61`), so a CH-default page titled "Rickenbach" files under the highest BFS number with no ambiguity check. The resolver's and narrowing's marker vocabularies differ (`markers.py:6-11` has `cantone/comune/quartiere`; `narrowing.py:19-36` has `ville de/commune de/town of`), so "Ville de Genève" narrows a document but does not resolve as a location. *Measured:* 106 documents `source_default`, 2 narrowed — both `schweizer_wanderwege` national pages wrongly filed under `CH-ZH-261` and `CH-GL` (plan §"Known gaps").

### 3.5 Inheritance and competence

Retrieval filters `chunk.extent_id = ANY(path)` (`retrieval/search.py:51`): ancestors are included, **descendants never** (issue #14 — asking about "Zurich" cannot see the Kreis-3 calendar). Specificity enters ranking as `hops = tree.distance(query_node, chunk_extent)` (`tree.py:48-53`; `rerank.py:46-71`). There is **no competence model**: nothing says a dog-tax question is municipal or a road-traffic question federal; the only level-related inputs are the hop count and the static `AUTHORITY_RANK` (`registry/models.py:20-26`).

## 4. Categories

Ten fixed `Category(id, label, description)` values, English only, flat (`registry/categories.py:11-22`): hiking, waste, dogs, taxes, housing, transport, parking, schools, health, safety. Adding one is a code change and unknown ids are rejected at source load, probe load and request validation (`registry/models.py:57-63`, `evals/probe_models.py:111`, `query_core.py:51`). `swiss_list_categories` returns `asdict` of the tuple.

Assignment at ingest: per chunk, inside the describe call, from the fixed list (`ingest/context.py:175-180`; prompt `llm.py:45-64`). **Every returned id is kept at any confidence** (`llm.py:113-117`); confidence is discarded when the chunk row is written (`persist.py:82`). Fallback to `source.categories` only when the model returned nothing *and* the source declares exactly one category or is templated (`context.py:52-70`); an untagged chunk of a multi-category source stores **no topic and is unreachable under the hard filter** (`context.py:79-84`). *Measured:* the backfill has not run, so all 563 Fedlex chunks still carry `{dogs, hiking, safety, transport, waste}` — the exact defect ADR 0003 describes — and `document.categories` still shows `dogs@0.3`-style tags from the old classifier.

At query time: topic is a hard filter (`&&` any-overlap, `search.py:52`), from the caller or from the local classifier (§7.1 step 5).

## 5. Language handling

Design (spec §2, ADR 0004): English is the working language; non-English sources are translated at ingest; the caller translates the question. In code:

- Documents: `language` from config/`<html lang>`; every section and title translated by one Claude call each (`ingest/enrich.py:31-43`); original kept in `text_original` for citation only.
- Indexes: both built from `context_en + text_en` (§2). Original text, original title and identifier are in neither.
- Query: the caller sends `question` (verbatim), `question_en`, `topic_en` (`mcp_server/server.py:105-115`); the dense arm embeds the English text, the lexical arm gets the verbatim question (`retrieval/query_text.py:70-95`). *Measured (ADR 0004 addendum, re-run 2026-09-23):* `Leinenpflicht` 0, `Hund` 0, `Abfall` 0, `SR 455` 0, `Zürich` 2 vs `Zurich` 89, `Graubünden` 6 vs `Graubunden` 0 — German words contribute nothing, names survive only when untranslated, there is no `unaccent`, and `websearch_to_tsquery` ANDs every term so whole sentences match nothing in any language.
- Probes never send `question_en`/`topic_en`/`topics` (`evals/runner.py:31-35`), so every eval runs the degrade path; ADR 0004:19's claim that probe files gained those fields is false (`grep` → 0).
- One language per source; no version linking (§1.4). Romansh: absent.

The user recorded on 2026-09-23 that this whole approach is being replaced (plan §"The language logic is being replaced").

## 6. Embeddings and storage

- **Model:** `BAAI/bge-m3` via sentence-transformers, 1,024-d, `normalize_embeddings=True`, CPU in-process (`retrieval/embedder.py:37-46`); `fake` hashed-bag-of-tokens embedder for tests (`:17-34`). Selected by `EMBEDDING_BACKEND`/`EMBEDDING_MODEL`/`EMBEDDING_DIM` (`config.py:13-15`). **No provider abstraction beyond these two backends**: no OpenAI, no Voyage, no Cohere; `Embedder` is a two-method protocol (`embedder.py:11-14`).
- **LLM:** `LLM_BACKEND ∈ {fake, anthropic}` (`config.py:19-21`); one `AnthropicLLM` class (`ingest/llm.py`). No OpenAI path.
- **Store:** PostgreSQL 16 + pgvector 0.8.6 (ADR 0018 records the SurrealDB evaluation). `chunk.embedding vector({{EMBEDDING_DIM}})` fixed at `db init` (`schema.sql:92`; README: changing it means `docker compose down -v`). **The index records no model name, version or dimension** beyond the column width; switching models silently invalidates every vector.
- **Index layout:** `hnsw (embedding vector_cosine_ops)` with defaults m=16, ef_construction=64 (`schema.sql:130`; *measured* reloptions NULL); `gin (tsv)`; `btree (extent_id, document_status)`. `hnsw.ef_search` is never set (`db/connection.py` has no `SET`; default 40) and iterative scans are off — a latent recall cap once the planner uses the index (issue #33, *measured* at 10× scale).
- **Sizes (live):** 719 vectors, HNSW index 5.9 MB, DB 24 MB. `DENSE_SQL` 11.6 ms mean, lexical 0.4 ms (issue #33/ADR 0018).
- **Latency:** the MCP server loads bge-m3 once at start; the CLI reloads it per call — *measured* 14.3–15.2 s per `query`, of which ~14 s is model load.

## 7. Retrieval and scoring (query core)

Entry point: `QueryCore.query` (`retrieval/query_core.py:69-153`). Every surface (MCP, CLI, eval runner) calls it, so this is the one path.

### 7.1 Pipeline, step by step

| # | Step | Where | What it does |
|---|---|---|---|
| 1 | Validate | `query_core.py:35-57` | Empty question → `invalid_request`; unknown topic/category id → `invalid_request`. |
| 2 | Validate `as_of` | `query_core.py:155-174`, `as_of.py:75-87`, `search.py:86-125` | A date before the oldest `valid_from` in the index (or any date when nothing carries one) is **refused** (`invalid_request`, field `as_of`). |
| 3 | Resolve location | `query_core.py:176-182` | `location` param → `LocationResolver.resolve`; otherwise scan the question text. Ambiguous or unresolved → `needs_location`. **No location means refusal, even for a purely federal question** (`server.py:153-159`). |
| 4 | Build the two query strings | `query_text.py:70-95` | Dense text = `question_en + " " + topic_en` (falls back to verbatim `question`). Lexical text = verbatim `question`, always. |
| 5 | Resolve topics | `topics.py:157-191` | Caller's `topics` → deprecated `categories` → local classifier (bge-m3 cosine vs. the 10 `"label. description"` strings; floor 0.42, margin 0.10, max 3 topics else no filter — `topics.py:64, 70, 87`; constants measured on a 23-question ad-hoc set). |
| 6 | Hybrid search | `search.py:260-325` | One dense query and one lexical query, each `LIMIT 50` (`CANDIDATE_TOP_N`, `query_core.py:27`), both under the same `FILTER`. RRF-fused (k=60). Cosine distance backfilled for lexical-only hits. |
| 7 | Coverage rows | `coverage.py:17-20` | Current-document count per extent on the path (ignores topic and date). |
| 8 | Empty result → cause census | `search.py:160-190`, `no_evidence.py:88-117` | Re-counts the path with one filter arm dropped at a time to name the cause: `extent`, `topic`, `as_of`, or both. |
| 9 | Rerank | `rerank.py:138-171` | Additive score × recency factor; ordered by `(tier claimed?, tier, -score, chunk_id)`. **Nothing is dropped.** |
| 10 | Diversify | `diversify.py:122-165` | Greedy top-down pick with caps: 2 chunks/document, 3 per calendar series, 6 upcoming calendar chunks in total; then force-inserts the single most specific candidate if it was cut. |
| 11 | Cite | `cite.py:22-39` | 600-char snippets of `text_en` and `text_original`; `tier` and `distance` published; internal `score` is not. |

### 7.2 The hard filter (`search.FILTER`, `search.py:51-70`)

```sql
c.extent_id = any(%(path)s)                                    -- extent arm: node and its ANCESTORS only
and (%(topics)s::text[] is null or c.categories && %(topics)s) -- topic arm: ANY overlap; null = no filter
and ( (%(as_of)s is null and d.status = 'current')
   or (%(as_of)s is not null and d.status in ('current','superseded')
       and d.valid_from is not null and d.valid_from <= %(as_of)s
       and (d.valid_to is null or d.valid_to > %(as_of)s)) )    -- as_of arm
```

Filtered on: jurisdiction path (ancestors, never descendants — issue #14), topic overlap, document status / validity. **Not** filtered on: language (no column is consulted), authority, source, publisher, country of origin (all sources are Swiss by registry construction, not by any check). Under `as_of`, every document without `valid_from` — 99 of 104 today, including the whole calendar — is excluded; the headline calendar question with an `as_of` returns no calendar (plan §"CORRECTION", probes city-001/018 red for that reason).

### 7.3 The two retrieval arms

**Dense** (`search.py:92-98`): `c.embedding <=> %(vector)s` over the filtered set, `ORDER BY distance LIMIT 50`. Query vector: bge-m3 over the dense text; stored vector: bge-m3 over `context_en + " " + text_en`.

**Lexical** (`search.py:100-107`): `websearch_to_tsquery('english', <verbatim question>)` against `tsv`, ranked by `ts_rank_cd`, `LIMIT 50`. *Measured* consequences (issue #32, ADR 0004 addendum): every bare word is ANDed **including the place name the path filter already handles**, so "What are the leash rules for dogs in Kanton Zürich?" yields the lexical arm **0** chunks on the Kreis-3 path (19 for the cardboard question, which happens to contain "8003"); identifiers, article numbers and original-language terms are not in `tsv`; no accent folding.

**Fusion** (`search.py:226-244`): plain RRF, `Σ 1/(60 + rank)` over the arms the chunk appears in; maximum 2/61 ≈ 0.0328.

### 7.4 The score formula, with every constant

`rerank.py:157-168`:

```
score = ( 0.5 · specificity            # RerankWeights.specificity   rerank.py:38
        + 0.3 · category_overlap       # RerankWeights.category      rerank.py:39
        + 0.2 · authority_rank         # RerankWeights.authority     rerank.py:40
        + 1.0 · 30 · rrf_score )       # rrf × rrf_scale             rerank.py:41-42
        × event_recency_factor         # rerank.py:109-116
```

| Term | Definition | Where | Range in practice |
|---|---|---|---|
| `specificity` | `1 / (1 + hops)`; hops = steps from the question's node up to the chunk's extent; 0 if off-path | `rerank.py:63-71`, `tree.py:48-53` | 1.0 (same node), 0.5, 0.33, 0.25 (federal root from a Kreis) → weighted 0.125–0.5 |
| `category_overlap` | `|topics ∩ chunk.categories| / |topics|`; 0 when no topics | `rerank.py:102-106` | With one topic **every hit scores exactly 1.0**, because the same topics are the hard filter (`query_core.py:147`) → a constant 0.3 that discriminates nothing. With 2–3 classifier topics: {⅓, ⅔, 1}. |
| `authority_rank` | federal_law 1.0, cantonal_law 0.9, municipal_law 0.8, official_info 0.6, institutional 0.4 | `registry/models.py:20-26` | weighted 0.08–0.2 (spread 0.12) |
| `rrf_score × 30` | RRF over the two arms | `search.py:226-244` | rank 1 in one arm 0.49; rank 50 in one arm 0.27; rank 1 in both 0.98. **Appearing in both arms is worth ≈0.5 — more than the entire specificity spread (0.375)**, and the lexical arm is empty for most place-naming questions. |
| `event_recency_factor` | 1.0 for non-events; **0.5** for a past event; `1 + 0.5/(1 + days/14)` for a future event | `rerank.py:10-14, 109-116` | 0.5–1.5; applied *after* authority is added (issue #25 §4) |

**But the score is not the primary ordering key.** `_order_key` (`rerank.py:119-135`) sorts by `(tier claimed?, tier, -score, chunk_id)`, where `tier = hops` is claimed only when `distance ≤ RELEVANCE_FLOOR = 0.55` (`rerank.py:30, 74-99`). The constant is documented in place as **uncalibrated**; on the one measured case a download link (0.5115) sat closer to the query than the page's only on-topic sentence (0.5257). So the effective ranking is:

> *All chunks within 0.55 of the query, most local first, score breaking ties within a level; then everything else by score.*

A local chunk at distance 0.54 always outranks a federal article at 0.20. Relevance decides only membership of the "may claim a tier" set, never order across tiers. Diversify then force-inserts `max(ranked, key=specificity)` regardless of its distance or score (`diversify.py:157-165`; issue #35), so one local chunk is guaranteed a slot whatever its quality.

*Measured on the live corpus:* "leash rules for dogs in Kanton Zürich" → 8 citations, all `CH` (7 Fedlex articles at distances 0.42–0.52, one wanderwege page), tier 1, coverage `CH-ZH: 0`; the first is SR 455 "Art. 23 Tierhalteverbote" (animal-keeping bans), not a leash rule. "Noise rules in Geneva" → the road-traffic act Art. 42 first, then two environmental-protection articles at 0.52.

### 7.5 What each component actually decides

| Component | Decides | Weight / threshold | Tuned on evals? |
|---|---|---|---|
| Extent path filter | membership | hard | n/a (rule) |
| Topic filter | membership | hard, any-overlap | no; classifier constants from a 23-question ad-hoc set |
| `as_of` arm | membership | hard | no |
| Cosine distance | tier eligibility only | 0.55 | **no** — stated uncalibrated |
| Specificity (hops) | outer ordering via tier; 0.5·1/(1+hops) inside the score | 0.5 | no — from the design spec |
| RRF | inner ordering | ×30, k=60 | no |
| Category overlap | inner ordering | 0.3 | no; mostly constant since ADR 0003 |
| Authority | inner ordering | 0.2 | no |
| Event recency | multiplies the inner score; cannot lift an event across a tier boundary | ×0.5 / up to ×1.5 | no |
| Diversify caps | membership of the final `limit` | 2 / 3 / 6 | no ("judgement call", `diversify.py:147`) |
| Most-specific promotion | forces one local chunk in regardless of score or distance | — | no (issue #35) |

No weight or threshold has been fitted to an eval set. `RerankWeights` is a dataclass with defaults instantiated as `RerankWeights()` at `app.py:25`; there is no config file, env override or per-query override.

### 7.6 Abstention

`no_evidence` is returned **only when the SQL filter returns zero rows** (`query_core.py:140-143`). There is no score- or distance-based abstention; `rerank.py:28-29` states "Nothing in this codebase may exclude a chunk on distance (decision D1)". A question about a subject the corpus does not cover, in a covered place with an on-topic tag somewhere, returns the 50 nearest chunks ordered as above, and the tool text tells the caller that `distance` "is NOT a relevance threshold you should apply yourself" (`server.py:185-187`). The only abstentions are `needs_location` and the three-arm `no_evidence` census.

### 7.7 Explainability

`ScoredHit` carries `specificity`, `category_overlap`, `authority_score`; `Hit` carries `rrf_score`, `dense_rank`, `lexical_rank` (`retrieval/models.py:33-59`). None reaches the `Citation` (`cite.py:29-39`); only `tier` and `distance` are published. No debug mode on the tool or CLI.

### 7.8 What the query side does not do

No query rewriting, decomposition, HyDE or multi-query; no reranker model (issue #36); no per-extent candidate quota (issue #34); no language store or cross-language step; no source-authority prior beyond 0.2·rank; no recency prior for non-event documents; no version/in-force prior beyond the `as_of` arm; no child-extent inclusion (issue #14).

## 8. MCP tool surface

Server: FastMCP, `mcp_server/server.py:74-304`; stdio and streamable HTTP; no authentication; every tool returns a JSON string with a fixed `notice` (`:59-62`). Six tools, verified against the code:

| Tool | Inputs | Output | Annotations |
|---|---|---|---|
| `swiss_resolve_location` (`:78-102`) | `query` | `found`, `location_id`, `label`, `level`, `path`, `method`, `alternatives`; or `ambiguous: true` + `candidates`; or `found: false` | read-only |
| `swiss_search` (`:104-206`) | `question` (verbatim), `question_en`, `topic_en`, `location`, `topics[]`, `categories[]` (deprecated alias), `as_of` (ISO), `limit` 1–25 default 8, `response_format` concise/detailed | `status ∈ {results, needs_location, no_evidence, invalid_request}`; `citations[]` (chunk_id, document_id, source_id, title_en, url, anchor, identifier, snippet_en, language, extent_id, extent_label, authority, categories, valid_from, tier, distance, event_date; `detailed` adds snippet_original, title_original, heading_path, license, retrieved_at); `resolved_location_*`; `coverage[]`; `resolution_note`; `categories_used`; `topic_decided_by`; `query_fields`; `message` | read-only |
| `swiss_get_document` (`:208-234`) | `document_id`, `chunk_id?` | document row + chunks (`text_en`, `text_original`, `heading_path`, `anchor`) | read-only |
| `swiss_list_categories` (`:236-241`) | — | the 10 categories | read-only |
| `swiss_coverage` (`:243-272`) | `location?` | per (extent, source): documents, last_retrieved, fixture_only, health from `ingest_run`; `by_extent`; `pending_suggestions` | read-only |
| `swiss_suggest_source` (`:274-302`) | `url`, `reason`, `proposed_extent?`, `proposed_authority?`, `proposed_categories?` | `status` approved/pending, `domain_class`, `source_id` | write |

How a client is expected to use them, from the ~80-line `swiss_search` docstring (`:116-195`): send the question verbatim *and* in English plus an English topic phrase; pick topic ids from `swiss_list_categories`; always supply a location or ask the user for one, never guess; read `tier`/`distance` as lower-is-better and do not threshold on `distance`; treat `event_date < today` as past; repeat the coverage gap and `resolution_note` in the answer. The protocol is entirely description-driven; nothing enforces it and only `query_fields`/`topic_decided_by` reveal afterwards whether the client followed it.

Not present: a language parameter or per-language result; a confidence or corroboration field; a debug/explain mode; MCP elicitation or sampling; pagination; document-level search. `swiss_suggest_source` fetches the submitted URL server-side to check reachability (`:29-31`, `registry/suggestions.py:47-55`) — an outbound-request surface on a tool exposed to any client. Contract changes already shipped: `Citation.score` → `tier` + `distance` (D1); `categories` deprecated for `topics`; `question_en`/`topic_en` added (ADR 0004). The README tool table still shows the old signature.

## 9. Evals

### 9.1 What exists

- **Probes:** 47 hand-written YAML cases in `evals/probes/{city,communes,lookalikes}.yaml` (20/15/12), model `evals/probe_models.py`. Each has `question`, `location`, `categories`, `as_of`, `limit` (default 8), `kind` structural/ranking, `failure_class`, `status` red/green, `judge`, and an `expect` block: `status`, `resolved` (id or label+level+parent), `method`, `alternatives_include`, `must_include`/`must_exclude` evidence rules (by source id, URL substring, extent id or `off_path`, authority — never by document id, title or text), `first_extent/authority/url_contains`, `first_event: nearest_future`, `coverage_empty/present`, `message_contains`. No expected answer, no expected document set.
- **Grading** (`evals/checker.py:159-191`): boolean pass/fail per probe; "top results" means the `limit` citations; `first_*` inspects index 0 only.
- **Runner** (`cli/eval_commands.py:88-135`): live DB + real embedder; one `eval_run` row per probe (git commit, tier, probe id, kind, failure class, passed, failures, observed — **no embedder, weights, chunking or corpus id**); `--record` rewrites the YAML (comments lost); **exit 3 = red/green bookkeeping mismatch**, not a pass-rate threshold.
- **Structural harness** (`tests/integration/test_probes_structural.py`): 16 fixture documents, `FakeEmbedder(dim=8)`, frozen clock; truncates the DB at `DATABASE_URL`; red probes `xfail(strict=True)`. Tests routing only (city-019's own note).
- **Judge** (`evals/judge_harness.py`, `evals/judge/rubric.md`): 15 probes marked `judge: true`, answered by four Claude models through `claude -p` with the MCP server, graded by a fixed Fable judge on **seven negative booleans** (no jurisdiction confusion, no authority inversion, no temporal misapplication, no entity substitution, under-coverage disclosed, URLs verbatim in evidence, coverage gap repeated — the last **true by definition when there is no coverage field**). `as_of` and `categories` are not passed to the answering model.
- **No CI configuration exists** in the repository.

### 9.2 What it measures — and the last results

*Measured:* recorded 44/47 at `6f3d42b` (2026-09-21); **live today 34/47** — the 2026-09-22 reclean deleted every `zh_ch`, `stadt_zuerich` and `ch_ch` document, and 8 of the 10 newly failing green probes require that evidence. The three red probes (city-007, city-020, com-015) are corpus gaps by their own notes; city-020's note ("SR 704 not in the registry") is stale — `fedlex.yaml:17` lists it.

The committed judge baseline (`evals/judge/results.json`, `3def861`): **all 15 Sonnet and all 15 Haiku records have empty evidence and an answer saying the MCP server failed to connect (`CONNECTION_CLOSED`), and the judge scored them 15/15 and 13–15/15.** `run_case` treats exit 0 as success and never checks that a tool was called (`judge_harness.py:129-137`); every rubric key is a "does not do X" that an empty answer satisfies. Only Fable vs Opus (30 records, all passing) is real signal, and Fable also judges itself.

### 9.3 Coverage matrix (47 probes)

| Dimension | Counts |
|---|---|
| Level of expected extent | neighborhood 12, municipality 23, canton 6, **federal 0**, abstain 6 |
| Geography | 44 inside canton ZH; 3 routing controls (Zug, Zurzach, Basel) with no local documents |
| Question language | EN 45, DE 2 (routing-only), **FR 0, IT 0** |
| Categories | dogs 34, waste 11, hiking 2 → **3 of 10** |
| Source type asserted | api-calendar 11, HTML 9, Fedlex XML 2, **PDF 0**, `ch_ch` 0, `ge_ville` 0; 29 probes name no source at all |
| `as_of` | 2 |
| Abstention expected | `needs_location` 6, **`no_evidence` 0** |
| Kind | structural 42, ranking 5 (three of them red for corpus reasons) |
| Failure class | jurisdiction_confusion 15, silent_under_coverage 8, entity_substitution 6, temporal 3, authority 3, none 12; **off-topic retrieval not representable** (`probe_models.py:11-18` lacks the class `CONTEXT.md:107` defines) |
| Distinct questions | ~12; "Do I need to leash my dog in the forest?" is **22 of 47** probes |
| Production contract exercised | **0** — `runner.to_request` sends no `question_en`/`topic_en`/`topics` (`evals/runner.py:31-35`) |

### 9.4 Gap analysis against the brief's target

| Target | Status |
|---|---|
| Federal / cantonal / municipal / neighborhood questions | federal absent; cantonal 6 (ZH only); municipal 23 (ZH + 3 controls); neighborhood 12 (Zurich only) |
| DE/FR/IT/EN + cross-lingual | EN only in practice; 2 DE routing checks; cross-lingual untested (probes cannot send `question_en`) |
| Every category, every source type | 3/10 categories; PDF, dataset, `ge_ville`, `ch_ch` absent |
| Jurisdiction traps (neighbouring canton, DE/AT/FR/IT rules) | sibling-commune leaks covered for indexed siblings; foreign rules absent (no foreign document in the corpus, no probe) |
| Freshness traps (superseded law, outdated page) | absent; calendar temporal covered (4 probes) |
| Exact-reference, multi-hop, ambiguous location, time-sensitive, unanswerable | ambiguous-location covered (6); calendar covered; exact-reference **absent** (and would fail — identifiers never reach `tsv`); multi-hop absent; `no_evidence` **absent** |
| Cross-language corroboration cases | absent (no concept in the data model) |
| Recall@k / MRR / nDCG | absent — no expected-document sets |
| Jurisdiction precision, language coverage, citation correctness, faithfulness, abstention accuracy, corroboration calibration, latency, cost | boolean proxies for the first, fourth (`url_grounded`) and fifth; the rest absent |
| Hundreds of cases, generation with review, held-out split, versioning, ablations, CI gate | all absent; the spec's Suite 2 (generated gold set, recall@5/MRR/sibling-leak) was never built, Suite 3 is not a holdout |

## 10. Live state (measured 2026-09-23)

| | |
|---|---|
| Corpus | 108 documents (104 current, 4 withdrawn), 719 chunks, 24 MB; PostgreSQL 16.15, pgvector 0.8.6 |
| By source | open_erz 89 docs / 89 chunks (en); schweizer_wanderwege 14 / 67 (de); fedlex 5 / 563 (de); **ch_ch, stadt_zuerich, zh_ch: 0** (deleted by reclean `e28665d`; their 29 URLs remain in `fetch_state`); ge_ville not seeded |
| By extent | CH 17 docs / 612 chunks; CH-ZH **0**; CH-ZH-261 1 (mis-narrowed wanderwege page); CH-ZH-261-K3 89; CH-GL 1 (mis-narrowed) |
| Dates | `valid_from` on 5 docs (Fedlex), `valid_to` 0, `published_at` 0, `event_date` 89; `version > 1` 0; `superseded_by` 0; `modified` changes 0 |
| Chunk enrichment | `context_en` non-empty: **0 / 719**; every Fedlex chunk carries dogs+waste+transport+safety+hiking; Fedlex titles `SR 451/455/741.01/814.01/921.0`, SR 455 `title_en = ''` |
| Chunk length (chars) | text_en avg 670 / p90 1,421 / max 1,500; text_original max 26,540 (wanderwege whole page per chunk) |
| Registry drift | DB has 6 sources, repo 7; DB `fedlex.categories` = 5 ids, YAML `[]`; 3 pending suggestions (`swiss`, awaiting review) |
| Ingest runs | last successful crawl runs 2026-09-14; open_erz 2026-09-21 (a run with 64 failures immediately before it); fedlex run took 755 s for 5 acts |
| Tests | unit 540 passed (18.7 s); structural probes 40 passed, 2 failed (city-001, city-018: the `as_of`/FakeEmbedder cases the plan documents) |
| Live probes | **34 / 47**, exit 3; 10 green probes now fail, 8 because their evidence was recleaned |
| Latency | CLI `query` 14.3–15.2 s per call (~14 s model load); `DENSE_SQL` 11.6 ms (issue #33) |
| Index | HNSW defaults, `hnsw.ef_search = 40`, iterative scan off |

## 11. Weaknesses ranked by impact on answer correctness

Ranked by how directly each one produces a wrong, missing or unjustified answer today or at the scale the brief targets. Each entry: what a user would see, why, where.

1. **Retrieval runs only over English translations, and the keyword arm cannot see the words that matter.** Ask "Gilt in Zürich Leinenpflicht?" or "What does Art. 336c OR say?" and the lexical arm returns nothing: `tsv` is built from `context_en || text_en` only (`db/schema.sql:108-111`), `text_original`, `title_original`, `identifier` and `heading_path` are indexed nowhere, there is no `unaccent`, and `websearch_to_tsquery` ANDs every term including the place name (`retrieval/search.py:100-107`; issues #10, #24, #32; *measured* in §5). The dense arm scores an English paraphrase whose fidelity is never checked. This is the opposite of the brief's four-language-store design and it is foundational to everything below.

2. **The candidate pool is shared across the whole jurisdiction path, so local evidence can be absent before ranking starts.** Each arm keeps 50 chunks over `CH` + canton + commune + Kreis together (`query_core.py:27`, `search.py:92-107`); federal law is 78% of chunks today and 91% in the larger DB issue #34 measured, and it grows fastest. Everything downstream — tier, specificity, the "most specific is represented" promotion — can only reorder what is in the pool. Compounded by the latent HNSW cap: `hnsw.ef_search = 40 < 50` with the extent filter applied *after* the scan (issue #33, *measured*).

3. **Within the pool, ranking is unprincipled: locality beats relevance absolutely, gated by an uncalibrated constant.** Order is `(tier, -score)` where `tier` is claimed at cosine distance ≤ 0.55 — a value the code calls uncalibrated and on which junk sat closer than content (`rerank.py:16-30, 119-135`). The additive score's weights (0.5/0.3/0.2/×30) come from the design spec and were never tuned (`rerank.py:38-43`, `app.py:25`); the category term is constant for single-topic queries; the authority term spans 0.12; appearing in both arms is worth more than being local. There is no reranker, no learned or fitted component, and the diversify promotion inserts the most specific chunk regardless of score (`diversify.py:157-165`, issue #35). *Measured:* the leash question in Kanton Zürich returns "Art. 23 Tierhalteverbote" first.

4. **Nothing abstains on weak evidence.** `no_evidence` fires only when the SQL filter returns zero rows (`query_core.py:140-143`); a distance-based cut is forbidden by design note (`rerank.py:28-29`) and the tool text tells the client not to apply one either (`server.py:185-187`). For any covered place and any topic tag present somewhere on the path, the caller gets the 50 nearest chunks presented as evidence. The brief's "no guessing" requires a calibrated abstention that does not exist.

5. **The topic hard filter is built from unthresholded per-chunk tags and a hand-tuned fallback classifier.** A 0.05-confidence tag becomes a hard-filter member (`ingest/llm.py:113-117`, `persist.py:82`); an untagged chunk of a multi-category source is unreachable (`ingest/context.py:79-84`); the query-side classifier's floor/margin/cap were set on 23 questions (`retrieval/topics.py:46-87`); the taxonomy is 10 English-only ids fixed in code (`registry/categories.py`). *Today* the backfill has not run, so all 563 Fedlex chunks carry five topics and the filter cannot separate acts at all. A wrong topic hides correct evidence rather than misranking it (ADR 0003 consequences).

6. **Temporal correctness is wrong for federal law in three ways.** (a) A consolidation scheduled for the future is fetched, stored `in_force = true` and served as current — *measured* SR 642.11 → 2029-01-01 (`ingest/fetchers/fedlex.py:59-62, 160`; issue #26). (b) A new consolidation is a new URL, so the old one is never superseded and both are `current` (`fedlex.py:142-144, 162`; `persist.py:141-153`; issue #30, live from 2026-09-30). (c) `as_of` excludes every document without `valid_from` — 99 of 104, the whole calendar included — so "what was the next cardboard collection as of 8 September" returns no calendar (`search.py:59-65`; plan §"CORRECTION"). The brief's "outdated content" failure mode is not guarded.

7. **Location resolution produces jurisdiction confusion in ways the glossary says it must not.** In-question duplicates are guessed, not asked: "dog tax in Wil" → Wil ZH (`locations/question_scan.py:161-167`, contradicts `CONTEXT.md:17-19`). Foreign lookalikes resolve silently to Swiss nodes: Lindau, Rheinfelden, Laufenburg, Freiburg → canton FR (`resolver.py:72, 99-103`). Biel/Bienne, Domat/Ems and other slash communes cannot be resolved from either half (`register.py:84`, `fuzzy.py:23-34`, contradicts `CONTEXT.md:29-31`). City vs canton flips with the language of the name (Genève → city, Geneva → canton). No Bezirk level (`models.py:6-10`); mergers unhandled (`register_fetch.py:49-56`); no competence model at all (§3.5).

8. **Ingestion loses legal structure and silently truncates.** `Abs.` and `lit.` numbers and chapter headings are dropped from Fedlex (`fedlex.py:71-74`), so a citation cannot say "Art. 6 Abs. 2" and the translate prompt's "preserve numbering" acts on text that already lost it. Translation is `max_tokens = 4096` with no `stop_reason` check (`ingest/llm.py:13, 277`), so the tail of a long single-section page vanishes without error. Split sections carry the whole original, so `snippet_original` does not match `snippet_en` (`chunking.py:71`, `cite.py:33`). PDFs: no OCR, no registered source; linked PDFs are never fetched (`html_crawl.py:14`). No DOCX/CSV/ICS/XML/dataset path.

9. **The evals cannot tell us whether the system answers correctly.** No expected-document sets, no recall/MRR/nDCG, no expected answers (`evals/checker.py:143-156`); 29 of 47 probes name no source; probes never send the production contract fields (`evals/runner.py:31-35`); 0 federal, 0 FR/IT, 0 `no_evidence`, 0 superseded-law, 0 exact-reference probes; 22 of 47 are one question; half the committed judge baseline graded a failed MCP connection as a pass (`judge_harness.py:129-137`, `rubric.md:15-21`); `eval_run` records no embedder, weights or corpus id (`schema.sql:185-199`); no held-out split; no CI. This is the multiplier on every other item: none of the fixes above can be shown to work.

10. **The live corpus is small, partly deleted and partly mis-filed.** Three of six sources hold 0 documents; canton ZH has 0; the only CH-ZH-261 document is a national hiking listicle narrowed to the city (ADR 0002 violation, plan §"Known gaps"); `context_en` is empty on every chunk; titles are `SR nnn`; registry drift between YAML and DB (`ge_ville`, `fedlex.categories`). Live probes are 34/47 against a recorded 44/47. Not a code defect, but every retrieval measurement taken today measures this state.

11. **Provenance is incomplete and one field is misleading.** `published_at` is never set (`ingest/models.py:22`); `valid_from/to` exist for Fedlex only; `retrieved_at` is refreshed by every 304 and so means "last seen" (`persist.py:165`) while the citation presents it as the retrieval date (`cite.py:36`); the XML actually fetched is not stored; publisher exists only as a join to `source`. The brief requires every citation to carry source, publisher, jurisdiction, language, category, retrieval timestamp and validity.

12. **One language per source and no language-version linking.** Fedlex is fetched in German only (`fedlex.py:31, 125`); FR/IT/EN editions, hreflang links and shared SR numbers are never joined (§1.4). The cross-language corroboration the brief centres on has no data to run on, and a French user's federal-law citation is an English rendering of the German text.

13. **The query protocol is fragile and returns no confidence.** Translation, topic choice and location are delegated to the calling model by docstring alone (`server.py:116-195`); a client that skips `question_en` silently gets a German vector against an English index, revealed only by `query_fields` afterwards; there is no server-side fallback translation, no elicitation, no confidence or corroboration field, no debug/explain output (§7.7, §8). The user has already recorded ADR 0004 as being replaced.

14. **Ingestion cannot run at hundreds of sources.** One transaction per run (`cli/main.py:209`, `db/connection.py:17`), fully sequential fetching and model calls, no Batch API or prompt caching, crawl frontier starvation at 200 known pages (`html_crawl.py:44-57`), whole-source in memory, no quarantine, no resumability mid-run, YAML+DB registry with no delete, hand-listed SR numbers (§1.6). A modified page re-buys every section's translation.

15. **No provider abstraction, and the index does not know which model made it.** Embeddings: `fake` or local bge-m3 (`retrieval/embedder.py:49-54`); LLM: `fake` or Anthropic (`config.py:19-21`). No OpenAI or Voyage path; no `EmbeddingProvider`/`LLMProvider` interface; the schema records only the vector width (`schema.sql:92`), so a model switch silently mixes incomparable vectors; re-embedding means `docker compose down -v`.

16. **Boilerplate and junk still reach the index on any new site.** Two literal headings plus a per-chunk model verdict (`ingest/boilerplate.py:25-28`, `context.py:181-183`); figure captions and CMS widget labels measured at 8.5% of a real municipal crawl (issue #28); soft-404 pages ingested as content (issue #20). Generated context enters the retrieval surface unchecked (ADR 0005 consequence).

17. **Smaller correctness items.** Bare-mention narrowing picks the last duplicate name (`narrowing.py:58-61`); child extents are invisible when asking about the parent (issue #14); calendar citations are ordered by nearness only within a tier, so a tier-qualified non-event outranks the next collection (`rerank.py:119-135`); event penalty applies after authority (issue #25 §4); `eval probes` writes to `eval_run` without `--record` (`cli/eval_commands.py:124`); `swiss_suggest_source` fetches arbitrary URLs server-side.

## Appendix A. Documentation that disagrees with the code

| Document | Says | Code |
|---|---|---|
| ADR 0005:8 | the SPARQL title binding never binds | the current query binds (`fedlex.py:52-56`, *measured* SR 455 → "Tierschutzgesetz…"); true only of stored rows until `retitle` |
| ADR 0004:19 | all probe files gained `question_en`/`topics` | none did (`grep` → 0; `probe_models.py` forbids extras) |
| README:130-132 | changed pages get a new version, old kept as superseded | not for Fedlex (§1.2) |
| README:166-168 | `llm_tagging: false` → no model call at all | translation still runs for a non-English feed (`enrich.py:31-37`) |
| README:172-175 | one call per document + one per chunk | omits per-section and title translation and resamples |
| README tool table | pre-ADR-0004 `swiss_search` signature | `question_en`, `topic_en`, `topics` (`server.py:105-115`) |
| `CONTEXT.md:17-19` | ambiguous location → ask, never guess | question scan guesses (`question_scan.py:161-167`) |
| `CONTEXT.md:29-31` | a place always resolves to its own node | Biel, Domat, Ilanz → `None` |
| `CONTEXT.md:61-63`, `markers.py` vs `narrowing.py` | one marker list | two divergent lists |
| Spec §9 / `eval_run` docstring | reranker config stored with each run; three suites | git commit only; Suite 2 absent, Suite 3 not a holdout |
| `models.py:42` (locations) | three resolution methods | six are emitted |
| README:113, diagrams | fourth level is "district" | code level is `neighborhood`; there is no district |
| `persist.py:93` | modified chunks paired by ordinal | paired by count (`:94-96`) |
| city-020 note | SR 704 not in the registry | `fedlex.yaml:17` lists it |

## Appendix B. Method

Four read-only sub-audits (ingestion; jurisdiction/registry/categories; evals; live database + test/probe/latency runs) plus a direct read of the retrieval, MCP and schema code by the author. Verification commands run: `uv run pytest tests/unit` (540 passed), `tests/integration/test_probes_structural.py` (40 passed, 2 failed), `swiss-grounding eval probes` (34/47, exit 3), three timed `query` calls, read-only SQL over every table, one read-only SPARQL query to Fedlex, and live resolver traces against the tree and GeoAdmin. No ingest, `recontext`, `retitle`, `reclean`, `renarrow`, `db seed` or `eval judge` was run and no Anthropic call was made. Raw measurements are in the session scratchpad and can be regenerated with the commands in `README.md` §Tests and §Evals.
