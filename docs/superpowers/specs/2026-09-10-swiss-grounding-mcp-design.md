# Swiss Grounding MCP — Design

Date: 2026-09-10
Status: approved in discussion, pending written review
Research basis: `research/README.md` and `research/sources/`

## 1. Goal

An MCP server that lets any LLM find the right Swiss public source for a question, retrieve the relevant evidence, and cite it, without guessing the jurisdiction. Scope goes beyond law: official information pages, institutional guidance (e.g. hiking associations), and local service data are in scope. The server returns evidence only. The calling model writes the answer.

Primary consumer: Swisscom myAI. Secondary consumers: any MCP client, and a CLI for demos and evals.

## 2. Decisions taken

| Question | Decision |
|---|---|
| Location handling | Containment tree (CH > canton > municipality > neighborhood). Hard filter via the query node's ancestor path. Ranked by specificity. |
| Authority vs. extent | Separate fields. `extent` = which places a document is about. `authority` = federal_law, cantonal_law, municipal_law, official_info, institutional. |
| Category axis | Multi-label tags. Soft rerank signal only, never a filter. |
| Extent assignment | From the source registry by default. A place-entity pass may narrow to a descendant node for sources that allow it. Never widened. |
| Hackathon scope | One vertical slice at full depth: federal (Fedlex), canton Zurich, city Zurich with Kreise/Quartiere, three scenario categories, a few institutional sources each. |
| Server output | Evidence with structured citations only. No server-side LLM at query time. |
| Missing location | Return `needs_location`; the tool description instructs the model to ask the user for city, canton, or PLZ. |
| Freshness | Index up front; daily incremental re-ingestion with change detection and document versioning. |
| Language | English is the working language. Non-English sources are translated at ingestion; original text is kept and quoted in citations. |
| Storage | PostgreSQL 16 + pgvector. Hybrid dense + full-text retrieval with reciprocal rank fusion. |
| Language/runtime | Python. FastMCP for the server. |
| Source suggestions | Tool `swiss_suggest_source`. Official domains auto-approved with authority `official_info`; everything else goes to human review. |
| Evals | Three suites: location resolution, retrieval, end to end. Gold set LLM-generated from indexed documents and human-checked, plus hand-written routing cases. |

## 3. Architecture

Three deployable pieces share one PostgreSQL database and one Python library, the query core.

```
Ingestion pipeline (batch CLI)
  registry → fetch → change-detect → translate → narrow extent → tag → chunk → embed → store
                        │
                        ▼
              PostgreSQL + pgvector
   locations, sources, suggestions, documents (versioned), chunks, eval cases, eval runs
                        │
     ┌──────────────────┼──────────────────┐
     ▼                  ▼                  ▼
MCP server          CLI                Eval runner
(HTTP + stdio)      (thin client)      (three suites)
     └──────────── query core library ──────────┘
   resolve location → extent filter → hybrid search → rerank → diversify → cite
```

The query core has no MCP or CLI dependency. All three surfaces call it, so retrieval behavior is identical and testable in isolation.

Package layout:

```
swiss_grounding/
  locations/    tree model, alias matching, GeoAdmin resolver
  registry/     source definitions, suggestion handling, official-domain list
  ingest/       fetchers (fedlex_sparql, html_crawl, pdf, api), change detection,
                translation, extent narrowing, category tagging, chunking, embedding
  retrieval/    hybrid search, reranker, diversifier, citation builder
  mcp_server/   tool definitions, transports
  cli/          ingest, query, ask, sources, eval, serve
  evals/        gold-set generation, scorers, runners
```

Runtime dependencies: PostgreSQL with pgvector (Docker Compose), an embedding model (multilingual, e.g. bge-m3 or multilingual-e5), a translation model or API and an LLM for tagging (ingestion only), and an LLM API key for the CLI `ask` command and the end-to-end eval suite only.

## 4. Data model

Field names follow ELI and schema.org Legislation where an equivalent exists.

### `location`
| field | notes |
|---|---|
| `id` | stable key: `CH`, `CH-ZH`, `CH-ZH-261`, `CH-ZH-261-K3` |
| `parent_id` | null only for `CH` |
| `level` | `country`, `canton`, `municipality`, `neighborhood` |
| `bfs_id` | BFS canton or commune number where one exists |
| `lindas_uri` | e.g. `https://ld.admin.ch/municipality/261`; null for neighborhoods |
| `names` | JSON: labels in de/fr/it/en plus aliases (`Kreis 3`, `Wiedikon`, `8003`) |
| `path` | materialized ancestor id list including self |

Neighborhoods come from Stadt Zürich open data (Stadtkreise, Quartiere). Postal codes are aliases, not nodes; a PLZ resolves to the smallest node that fully contains it.

### `source`
| field | notes |
|---|---|
| `id`, `name`, `base_url` | |
| `default_extent_id` | node this source speaks for |
| `authority` | `federal_law`, `cantonal_law`, `municipal_law`, `official_info`, `institutional` |
| `categories` | default tags applied to every document |
| `fetch_strategy` | `fedlex_sparql`, `html_crawl`, `pdf`, `api`, plus strategy config (SR ranges, path allowlist, endpoint) |
| `allow_narrowing` | true for institutional and info sites, false for law |
| `license` | shown in citations |
| `origin` | `seed`, `auto_approved`, `reviewed` |

### `source_suggestion`
| field | notes |
|---|---|
| `id`, `url`, `reason` | |
| `proposed_extent_id`, `proposed_authority`, `proposed_categories` | optional, from the suggesting client |
| `domain_class` | `official`, `swiss`, `other`, computed at submission |
| `status` | `pending`, `approved`, `rejected` |
| `suggested_by`, `suggested_at`, `reviewed_by`, `reviewed_at`, `review_note` | |
| `source_id` | set once approved |

### `document`
| field | notes |
|---|---|
| `id`, `source_id`, `url` | |
| `identifier` | ELI URI or SR number for law; null otherwise |
| `title_original`, `title_en` | |
| `language` | original language |
| `extent_id` | after narrowing |
| `extent_reason` | `source_default` or `narrowed:<matched entities>` |
| `authority` | copied from source |
| `categories` | multi-label with confidence |
| `valid_from`, `valid_to`, `in_force` | from JOLux for law; null otherwise |
| `published_at`, `retrieved_at` | freshness stamps |
| `content_hash` | gate for expensive stages |
| `version`, `superseded_by`, `status` | `current`, `superseded`, `withdrawn` |

### `chunk`
| field | notes |
|---|---|
| `id`, `document_id`, `ordinal` | |
| `text_original`, `text_en` | original for citation, English for search |
| `heading_path` | e.g. `Art. 12 > Abs. 2` or `Hiking > Safety` |
| `anchor` | URL fragment to the article or section |
| `embedding` | vector over `text_en` |
| `tsv` | full-text vector over `text_en` |
| `chunk_hash` | for chunk-level diffs between versions |
| `extent_id`, `authority`, `categories`, `document_status` | denormalized so the filter needs no join |

### `document_change`
| field | notes |
|---|---|
| `run_id`, `document_id`, `previous_document_id` | |
| `change_type` | `added`, `modified`, `withdrawn` |
| `chunks_added`, `chunks_removed`, `chunks_modified` | counts and chunk ids, matched by `chunk_hash` |

### `eval_case`, `eval_run`
Described in section 9.

## 5. Ingestion pipeline

Command: `ingest --source <id>` or `ingest --all`. Runs daily in production. Each stage is a pure function whose output is persisted, so a failed run resumes from the last completed stage.

1. **Fetch** per strategy.
   - `fedlex_sparql`: query the Fedlex SPARQL endpoint for acts in the configured SR ranges and their current consolidation; fetch Akoma Ntoso XML; read `dateApplicability`, `dateEndApplicability`, `inForceStatus`.
   - `html_crawl`: bounded crawl from `base_url`, same domain, path allowlist, robots.txt respected. HTML to Markdown with headings preserved.
   - `pdf`: download, layout-aware text extraction.
   - `api`: structured feed; each record becomes a small document.
2. **Change detection.**
   - HTML: conditional requests (`ETag`, `Last-Modified`), sitemap `lastmod` where present, then content hash of the extracted Markdown as the final arbiter.
   - Fedlex: SPARQL for consolidations with applicability date since the last run. A new consolidation is a new document version; the previous keeps its dates with `valid_to` set.
   - PDF: `HEAD` for size and modification date, then hash.
   - API: per-record hash.
   - Unchanged hash: skip stages 3 to 7, update `retrieved_at` only.
   - Changed: insert a new document version, mark the old `superseded`, compute the chunk-level diff into `document_change`.
   - Gone (404 or removed from sitemap/feed): mark `withdrawn`. Never delete.
3. **Translate** non-English text to English at document level. Keep the original.
4. **Narrow extent** if `allow_narrowing`. Match location names and aliases from the tree in the English text. If all matches fall under a single descendant of the source default, narrow to it and record the entities. Otherwise keep the default. Never widen.
5. **Tag categories.** Source defaults plus an LLM classifier over a fixed list of about ten categories (the full taxonomy). The three demo scenarios (hiking, waste, dogs) are the categories whose sources are populated; the other categories exist so tagging is stable when sources are added. Multi-label with confidence.
6. **Chunk** on structure: law at article boundaries, pages at headings, size cap with small overlap only when a section exceeds the cap. Store heading path and anchor.
7. **Embed and store.** Embed `text_en`, populate `tsv`, write chunks with denormalized fields.

Boundary validation: source definitions are schema-validated files; fetched content is checked for size and MIME type; Fedlex responses are validated for required fields before writing.

Initial registry for the Zurich slice: Fedlex (SR ranges for the three scenarios), ch.ch, zh.ch, stadt-zuerich.ch, Stadt Zürich Amtliche Sammlung PDFs, Open ERZ waste API, and two or three institutional sites per scenario (e.g. schweizer-wanderwege.ch, SAC).

## 6. Query pipeline (query core)

Input: `question`, optional `location`, optional `categories`, optional `as_of`, `limit`. Output: one of `results`, `needs_location`, `no_evidence`.

1. **Resolve location.** Match against tree names and aliases. Fall back to GeoAdmin SearchServer, map the returned commune's BFS number to a node. If no location is given and none is recognizable in the question, return `needs_location`.
2. **Extent filter.** `chunk.extent_id = ANY(node.path) AND document_status = 'current'`. `CH` resolves to path `[CH]`, so general questions surface only country-scoped documents. If `as_of` is given, use versions valid at that date instead of `current`, and add `valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)` for dated chunks.
3. **Hybrid retrieval.** Dense similarity top 50 and full-text rank top 50 over the filtered set; fuse with reciprocal rank fusion.
4. **Rerank** with a deterministic additive score, weights in one config file:
   - specificity: tree distance between chunk extent and query node, closer is better
   - category overlap: weighted overlap with query hints (caller-supplied or from a light question classifier)
   - authority: small bonus by authority level
5. **Diversify.** Cap results per document; guarantee at least one result from the most specific extent that matched.
6. **Cite.** Per result: original snippet, English snippet, titles in both languages, URL with anchor, identifier, extent label, authority, `valid_from`, `retrieved_at`, license. URLs are copied from the database, never generated.

Empty filtered set: return `no_evidence` with the resolved extent. The location filter is never relaxed to a sibling.

## 7. MCP tool surface

All tools return JSON with a fixed `notice` field ("retrieved public information, not legal advice"). `response_format` is `concise` (default) or `detailed`.

| tool | purpose | parameters | annotations |
|---|---|---|---|
| `swiss_resolve_location` | free text to tree node, for confirmation before searching | `query` | read-only |
| `swiss_search` | main tool; runs the query core | `question`, `location?`, `categories?`, `as_of?`, `limit?`, `response_format?` | read-only |
| `swiss_get_document` | full document or chunk by id | `document_id`, `chunk_id?` | read-only |
| `swiss_list_categories` | category list with descriptions | none | read-only |
| `swiss_coverage` | indexed sources and extents with `retrieved_at`, pending suggestions, withdrawn documents | `location?` | read-only |
| `swiss_suggest_source` | propose a source for ingestion | `url`, `reason`, `proposed_extent?`, `proposed_authority?`, `proposed_categories?` | not read-only |

`swiss_search` description carries the routing rule: if the question concerns a specific place and no location is given, call `swiss_resolve_location` or ask the user before searching.

`swiss_suggest_source` validation: URL well-formed and reachable; not already a source or suggestion; `domain_class` computed from an official-domain list (`*.admin.ch`, cantonal and city domains) and TLD. `official` suggestions are approved immediately with extent from the domain list, authority `official_info`, `allow_narrowing` true, `origin = auto_approved`, and join the next ingestion run. Others stay `pending` until `sources review`. Law authority levels are only ever assigned by a human reviewer.

Transports: Streamable HTTP for remote clients, stdio for local clients, from the same FastMCP app.

## 8. CLI

- `ingest --source <id> | --all`
- `query "<question>" --location "<place>" [--categories ...] [--as-of DATE] [--json]`
- `ask "<question>" --location "<place>"`: runs `query`, sends question plus evidence to a configured model, prints a grounded answer with citations. The only command needing a model API key at query time.
- `sources list | review | approve <id> | reject <id> --note ...`
- `eval generate --suite retrieval` and `eval run --suite location|retrieval|e2e`
- `serve --transport http|stdio`

## 9. Evaluation

Results are written to `eval_run` with git commit hash and reranker config so changes show as before-and-after diffs.

**Suite 1, location resolution.** About 60 hand-written cases: input string, expected node, optional acceptable alternatives. Covers canton names in four languages, city names, Kreis and Quartier names, PLZ, misspellings, ambiguous inputs. Metric: exact-match accuracy, plus accuracy on the ambiguous subset.

**Suite 2, retrieval.** Generated by `eval generate` from indexed documents, reviewed by a human in a review file before use. Per document, two or three questions tagged with extent and categories. Each case records expected document ids (top 5), forbidden document ids (same category, sibling extent), and a query location, sometimes one level below the document extent to test the ancestor walk. Metrics: recall@5, MRR, sibling-leak rate (forbidden id in top 10), specificity rate (most specific matching extent ranks first).

**Suite 3, end to end.** About 30 hand-written questions, including ten that must trigger `needs_location` and five that must yield `no_evidence`. A model with the MCP tools answers each. An LLM judge scores citation precision, citation recall, groundedness, and jurisdiction correctness, with the four Stanford error types (jurisdiction confusion, authority-hierarchy violation, temporal misapplication, entity substitution) in the judge prompt. Refusal and clarification cases are scored by behavior.

Reranker weights and chunk size are tuned on suite 2 only. Suite 3 is a holdout.

**Tests.** Unit tests for pure functions: path construction, extent narrowing, change detection decisions, chunk boundaries, reranker score, citation building, suggestion validation. Integration tests: ingest one fixture source into a test database, query it, and re-ingest a modified fixture to verify versioning and the change diff.

## 10. Error handling

- Every fetcher fails per document, not per source; failures are logged with URL and reason and the run continues.
- Fedlex and GeoAdmin calls have timeouts and bounded retries; a resolver outage returns `needs_location` with a reason rather than a guess.
- Translation or tagging failures leave the document in a `pending_enrichment` state that the next run retries; such documents are excluded from retrieval until complete.
- Tool inputs are schema-validated; invalid input returns a structured error with the offending field.
- No secrets in code. Model and database credentials come from environment variables, checked at startup.

## 11. Out of scope for the hackathon

- Cantons other than Zurich and municipalities other than the city of Zurich (the tree supports them; the registry does not populate them).
- Answer generation inside the server.
- Learned routing or learned rerankers.
- Authentication on the MCP server beyond what the deployment host provides.
- Case law.
