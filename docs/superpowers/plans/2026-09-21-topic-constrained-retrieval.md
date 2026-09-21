# Topic-Constrained Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `swiss_search` return only evidence that is on the question's topic and inside its jurisdiction, and return nothing when no such evidence exists — instead of ranking whatever passed the extent filter.

**Architecture:** Four behaviour changes, in credit-cost order. (1) Remove what should never have been indexed: boilerplate chunks and an error page. (2) Stop asserting a source's declared categories on every document it produces. (3) Give every chunk generated context and its own topics, indexed with the text and never cited (ADR 0005). (4) Make topic a hard filter, order most-specific-first behind a relevance floor, and change the tool contract so the calling model supplies the English query and topic (ADR 0003, ADR 0004). Two reported defects — calendar evidence filling an answer, and unvalidated model output — are fixed early because they are cheap and independent.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 16 + pgvector, FastMCP, typer, pytest. Embeddings bge-m3 via sentence-transformers (local, free). Enrichment via the Anthropic API (ingestion only).

**Baseline measured on the live database at `ec2d7ed`:**

```
133 documents, 795 chunks
  fedlex                563 chunks / 5 docs   (112.6 per doc, 71% of corpus)
  open_erz               85 chunks / 85 docs
  schweizer_wanderwege    67 chunks / 14 docs
  zh_ch                   61 chunks / 13 docs   ← every chunk heading_path 'Navigation'
  stadt_zuerich           18 chunks / 15 docs   ← every chunk heading_path 'Navigation'
  ch_ch                    1 chunk  / 1 doc     ← 'Error Page (404)'

563 chunks assert {dogs, hiking, safety, transport, waste} simultaneously
  0 chunks mention dog tax, Hundesteuer, or dog registration
Probes: 47 total, 44 green, 3 red (city-007, city-020, com-015)
```

**Commands used throughout:**
```
export DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)"   # integration tests only; unset before CLI runs
uv run pytest tests/unit -q
uv run pytest tests/integration -q -m integration
uv run pytest tests/integration/test_probes_structural.py -q -rxX
uv run ruff check src tests
```
Commit messages: `<type>: <description>` ending with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

---

## Open decisions

Two of the reported findings are design questions, not defects. They block the tasks named and must be answered before those tasks start.

**D1 — What does `score` mean to a caller?** (blocks Task 9)
Scores are query-node-relative by construction: the same chunk scores 1.1918 at `CH` and 0.8168 at `8003`, and the entire difference is the specificity term. Measured across four scopes, the pool grew 18 → 132 documents with no effect on the retrieval component. Once a tier decides ordering, `score` informs nothing a caller can act on. Options: drop it from citations; keep it and document it as incomparable; or replace it with the tier rank. *Recommendation: replace with tier rank plus the raw retrieval distance, which is comparable across calls.*

**D2 — What should `as_of` do with no version history?** (blocks Task 11)
Only current consolidations are ingested, so every Fedlex document has `valid_from >= 2023`. `as_of: 2020-01-01` therefore excludes all law and returns only undated pages, which is worse than refusing. Documents with `valid_from is null` bypass the filter entirely. Options: reject an `as_of` earlier than the oldest indexed version with a structured error; return `no_evidence` with an explanation; or keep today's silent filtering. *Recommendation: reject with a structured error naming the earliest date the index can answer for.*

---

## File Structure

```
src/swiss_grounding/ingest/
  boilerplate.py              classify a chunk as page furniture (pure)
  context.py                  generate per-chunk context + topics from stored text
  enrich.py                   modified: per-chunk topics, source categories as fallback only
  llm.py                      modified: reject empty model output; add describe()
  chunking.py                 modified: carry context onto ChunkDraft
  persist.py                  modified: embed context + text; write context_en
  recontext.py                backfill context and topics for stored chunks (no re-crawl)
  fetchers/fedlex.py          modified: real act titles, not SR-number fallbacks
src/swiss_grounding/retrieval/
  topics.py                   local topic classifier over category descriptions (no API)
  search.py                   modified: topic filter in FILTER; expanded query
  rerank.py                   modified: specificity tier + relevance floor
  diversify.py                modified: cap calendar evidence in aggregate
  models.py                   modified: QueryRequest gains question_en/topic_en/topics
  query_core.py               modified: topic resolution, no_evidence when off-topic
src/swiss_grounding/db/
  schema.sql                  modified: chunk.context_en, tsv over context_en || text_en
src/swiss_grounding/cli/main.py    + `reclean`, + `recontext`
src/swiss_grounding/mcp_server/server.py   new swiss_search signature
tests/unit/ingest/     test_boilerplate.py, test_context.py, test_llm_validation.py
tests/unit/            test_topics.py, test_rerank_tier.py, test_diversify_calendar.py
tests/integration/     test_reclean.py, test_recontext.py, test_topic_filter.py
```

---

## Task 1: Drop boilerplate chunks and the error page

Do this first so nothing is paid to enrich page furniture. `heading_path = 'Navigation'` identifies all 79 of them exactly; the `ch_ch` document is a 404 body ingested as content.

**Files:** Create `src/swiss_grounding/ingest/boilerplate.py`, `tests/unit/ingest/test_boilerplate.py`, `tests/integration/test_reclean.py`. Modify `src/swiss_grounding/cli/main.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/ingest/test_boilerplate.py
from swiss_grounding.ingest.boilerplate import is_boilerplate

def test_navigation_heading_is_boilerplate():
    assert is_boilerplate(heading_path="Navigation", text_en="Read page aloud  Environment and Energy")

def test_error_page_title_is_boilerplate():
    assert is_boilerplate(heading_path="Error Page (404)", text_en="The page could not be found")

def test_real_article_is_not_boilerplate():
    assert not is_boilerplate(
        heading_path="Art. 28 Übrige Widerhandlungen",
        text_en="Anyone who intentionally, provided Article 26 is not applicable, is punished",
    )

def test_real_page_section_is_not_boilerplate():
    assert not is_boilerplate(
        heading_path="Der Wegweiser erklärt",
        text_en="Yellow signposts mark hiking trails and give walking times to the next destination.",
    )
```

- [ ] **Step 2: Implement `is_boilerplate`** as a pure predicate over `heading_path` and text. Heading-based rules only for now; the model-generated judgement arrives in Task 5 and supersedes the heuristic.

- [ ] **Step 3: Add `swiss-grounding reclean`**, a sibling of `renarrow`: delete matching chunks, delete documents left with no chunks, report `dropped_chunks=N dropped_documents=N` per source. No network, no model calls.

- [ ] **Step 4: Integration test** — load the fixture, insert a `Navigation` chunk, run `reclean`, assert it is gone and that a real chunk survives.

- [ ] **Step 5: Run `reclean` against the live database.** Expected: 80 chunks and 29 documents dropped; `swiss_coverage("Zurich")` then reports `CH-ZH: 0` and `CH-ZH-261: 0`. **This is the intended outcome** — see ADR 0005. Record the before/after counts in the commit message.

**Verification:** `uv run pytest tests/unit/ingest/test_boilerplate.py -q` and the integration test pass; live counts recorded.

---

## Task 2: Source categories stop asserting what a document is about

`_merge_tags` writes every `source.categories` entry at confidence 1.0, overwriting the classifier. This is the cause of 563 chunks carrying five topics each.

**Files:** Modify `src/swiss_grounding/ingest/enrich.py`, `tests/unit/ingest/test_enrich.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_source_categories_do_not_override_the_classifier():
    tags = _merge_tags(defaults=("dogs", "hiking"), llm_tags=(CategoryTag("waste", 0.9),))
    assert {t.id for t in tags} == {"waste"}

def test_source_categories_apply_only_when_the_classifier_is_silent():
    tags = _merge_tags(defaults=("waste",), llm_tags=())
    assert {t.id for t in tags} == {"waste"}
    assert tags[0].confidence < SOURCE_DEFAULT_CONFIDENCE  # a fallback is not a certainty
```

- [ ] **Step 2: Rewrite `_merge_tags`** so defaults are a fallback used only for an empty classifier result, at a confidence below 1.0.

**Verification:** unit tests pass; no re-ingest needed yet — Task 6 backfills.

---

## Task 3: Cap calendar evidence in aggregate, not per series

Reported finding: a dog-tax question in German returned nine waste-collection citations. Measured cause: `PER_SERIES_CAP = 3` applies per series, and five series have upcoming events (waste 15, organic 15, cardboard 15, mobile 12, paper 7). Five series × three = fifteen slots, more than any `limit <= 25`. The per-series cap can never bound calendar evidence as a whole.

**Files:** Modify `src/swiss_grounding/retrieval/diversify.py`, `src/swiss_grounding/retrieval/query_core.py`, `tests/unit/test_diversify.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_diversify_calendar.py
def test_calendar_evidence_cannot_fill_an_answer(today):
    """Five series of upcoming events must not crowd out non-calendar evidence."""
    events = [scored_event(series=s, days_ahead=d) for s in
              ("waste", "organic", "cardboard", "mobile", "paper") for d in (1, 8, 15)]
    prose = [scored_chunk(score=0.4) for _ in range(5)]
    chosen = diversify(sort_by_score(events + prose), limit=10, today=today)
    assert sum(1 for c in chosen if c.hit.chunk.event_date) <= CALENDAR_CAP
    assert any(c.hit.chunk.event_date is None for c in chosen)

def test_a_single_series_still_keeps_its_nearest_dates(today):
    events = [scored_event(series="cardboard", days_ahead=d) for d in (1, 8, 15, 22, 29)]
    chosen = diversify(events, limit=10, today=today)
    assert [c.hit.chunk.event_date for c in chosen] == sorted(c.hit.chunk.event_date for c in chosen)
```

- [ ] **Step 2: Add `CALENDAR_CAP`** — a ceiling on calendar evidence across all series, applied in `_select` alongside the existing per-series cap. Keep the per-series cap; it still stops one series dominating within the ceiling.

- [ ] **Step 3: Keep the past-event exemption** — `_capped_series` returning `None` for past events is deliberate (probe `city-003` asks about a missed collection) and must not regress.

**Verification:** `uv run pytest tests/unit/test_diversify_calendar.py tests/unit/test_diversify.py -q`; probes `city-001`, `city-003`, `city-004`, `city-011` stay green.

---

## Task 4: Reject empty model output, and fetch real Fedlex titles

Two defects with one theme: text that was never checked. `AnthropicLLM._ask` returns `"".join(...)` with no validation, which is why document 3 has `title_en = ''`. The same path silently drops a section whose translation comes back empty, because `chunk_sections` skips falsy text while the section-count check still passes. Separately, the Fedlex SPARQL binds `?title` as `OPTIONAL` and it never binds, so all five acts are titled by their SR number — no act name exists anywhere in the index.

**Files:** Modify `src/swiss_grounding/ingest/llm.py`, `src/swiss_grounding/ingest/fetchers/fedlex.py`, `tests/unit/ingest/test_llm_validation.py`, `tests/unit/ingest/test_fedlex.py`.

- [ ] **Step 1: Write the failing tests**

```python
def test_empty_translation_is_an_error_not_an_empty_string():
    llm = AnthropicLLM(model="m", client=FakeClient(returns=""))
    with pytest.raises(EnrichmentError):
        llm.translate("Tierschutzgesetz", "de")

def test_a_dropped_section_is_an_error_not_a_silent_loss():
    with pytest.raises(EnrichmentError):
        chunk_sections(original=(Section("Art. 1", None, "Text"),),
                       english=(Section("Art. 1", None, "   "),), limits=ChunkLimits())

def test_fedlex_title_is_the_act_title_not_the_sr_number():
    doc = fetch_one(binding_with_title="Tierschutzgesetz vom 16. Dezember 2005")
    assert doc.title == "Tierschutzgesetz vom 16. Dezember 2005"
```

- [ ] **Step 2: Raise `EnrichmentError`** on empty translation or classification output, so the document lands in `pending_enrichment` and the next run retries it, as spec §10 requires.

- [ ] **Step 3: Fix the SPARQL title binding.** Investigate why `?title` never binds — likely the title hangs off the expression's `jolux:titleShort`/`jolux:titleAlternative` rather than `jolux:title`. Query the endpoint directly before changing the query; if no title predicate is reachable, fall back to the `<act>` heading in the Akoma Ntoso XML, which is already downloaded.

**Verification:** unit tests pass; a live `ingest --source fedlex` run (five documents, cheap) shows real act titles.

---

## Task 5: Chunk context and per-chunk topics

ADR 0005. One model call per chunk returns a short description of what the document is about and what this chunk covers, the chunk's topics, and whether the chunk is page furniture. Context is indexed and never cited.

**Files:** Create `src/swiss_grounding/ingest/context.py`, `tests/unit/ingest/test_context.py`. Modify `llm.py`, `chunking.py`, `persist.py`, `db/schema.sql`.

- [ ] **Step 1: Schema change** (idempotent, as the repo requires):
```sql
alter table chunk add column if not exists context_en text not null default '';
-- tsv becomes a generated column over context and text together
```
The `tsv` generated column must be dropped and recreated; write it as a guarded `do $$ ... $$` block so `db init` stays idempotent.

- [ ] **Step 2: Write the failing test**

```python
def test_context_is_indexed_but_never_cited():
    chunk = persisted_chunk(context_en="From the Animal Welfare Act. Sets penalties.",
                            text_en="Anyone who intentionally...")
    assert "Animal Welfare Act" in indexed_text(chunk)      # embedding and tsv see it
    citation = build_citation(scored(chunk), tree)
    assert "Animal Welfare Act" not in citation.snippet_en  # the caller never does
    assert citation.snippet_en == "Anyone who intentionally..."

def test_context_keeps_the_original_term():
    """A German compound with no English cognate stays reachable in an English index."""
    ctx = describe(text_en="Collection of green waste", text_original="Grüngutabfuhr", ...)
    assert "Grüngutabfuhr" in ctx.context_en
```

- [ ] **Step 3: Add `LLM.describe()`** returning context, topics and a boilerplate verdict in one call. One call per chunk; batch by document to share the document summary.

- [ ] **Step 4: Embed `context_en + text_en`** in `persist.py`, not `text_en` alone. Citations continue to read `text_en` and `text_original` only.

- [ ] **Step 5: Skip templated sources.** `open_erz` records are already self-describing and `llm_tagging: false`; generate their context from the existing template rather than a model call.

**Verification:** unit tests pass; integration test asserts a citation never contains generated text.

---

## Task 6: Backfill stored chunks without re-crawling

`recontext`, a sibling of `renarrow`: re-enrich every stored chunk from text already in the database. This is what makes the redesign affordable while translation credits are unavailable — it reads stored English text and never re-fetches or re-translates.

**Files:** Create `src/swiss_grounding/ingest/recontext.py`, `tests/integration/test_recontext.py`. Modify `cli/main.py`.

- [ ] **Step 1:** Integration test — seed chunks with stale topics, run `recontext_all`, assert topics are replaced, `context_en` is populated, embeddings are recomputed, and the report counts `updated=N skipped=N failed=N`.
- [ ] **Step 2:** Implement, committing per document so a long run is resumable (see issue #13 — do not repeat that mistake here).
- [ ] **Step 3:** Run against the live database. Expected scope after Task 1: ~715 chunks, of which ~630 need a model call. Record cost and duration in the commit message.

**Verification:** after the run, no chunk carries five topics; spot-check that SR 814.01 Art. 35a no longer carries `dogs`.

---

## Task 7: Local topic classifier

ADR 0004 makes the caller the primary source of the topic. This is the fallback when they supply none. No API call: embed the ten category descriptions once at startup with the model already loaded for search.

**Files:** Create `src/swiss_grounding/retrieval/topics.py`, `tests/unit/test_topics.py`.

- [ ] **Step 1: Write the failing test** — the measured cases, with the margin band that rescues near-ties:

```python
@pytest.mark.parametrize("question,expected", [
    ("How much is the dog tax?", {"dogs"}),
    ("When is cardboard collected?", {"waste"}),
    ("Who maintains the hiking trails?", {"hiking"}),
    ("Which cantonal rules apply to dogs on hiking trails?", {"dogs", "hiking"}),
])
def test_classifies_within_the_margin_band(question, expected):
    assert expected <= classify_topics(question, embedder)

def test_an_unrelated_question_filters_on_nothing():
    """Below the confidence floor, return no topics rather than the nearest by accident."""
    assert classify_topics("What is the capital of Peru?", embedder) == ()
```

- [ ] **Step 2: Implement** — keep every category within `TOPIC_MARGIN` (0.10) of the best; return `()` when the best is below `TOPIC_FLOOR` (0.45) so an unrecognised question degrades to no filter rather than a wrong one.

**Verification:** `uv run pytest tests/unit/test_topics.py -q`. Measured baseline to beat: 14/15 top-1, 15/15 within the band.

---

## Task 8: Topic as a hard filter, and an on-topic empty result

ADR 0003. A chunk that does not carry the topic is not evidence.

**Files:** Modify `search.py`, `query_core.py`, `models.py`, `tests/integration/test_topic_filter.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_a_chunk_without_the_topic_is_not_returned(corpus):
    resp = core.query(QueryRequest(question="When is cardboard collected?",
                                   location="8003", topics=("waste",)))
    assert all("waste" in c.categories for c in resp.citations)

def test_no_evidence_when_nothing_on_the_path_carries_the_topic(corpus):
    resp = core.query(QueryRequest(question="Which schools are nearby?",
                                   location="8003", topics=("schools",)))
    assert resp.status == "no_evidence"
    assert "schools" in resp.message
    assert resp.coverage  # the coverage signal still reports what IS there
```

- [ ] **Step 2:** Add the topic predicate to `FILTER` in `search.py`. Both arms, one predicate.
- [ ] **Step 3:** `no_evidence` must distinguish the two causes in its message: no documents on the path (ADR 0001) versus documents on the path but none on topic (ADR 0003).

**Verification:** integration tests pass; `swiss_coverage` is unaffected, since coverage is about places, not topics.

---

## Task 9: Specificity tier and relevance floor

*Blocked on decision D1.* Ordering becomes `(extent distance, -score)` rather than `-score` alone, so the tool description's "most specific first" becomes true. The floor governs **tier eligibility only** — a chunk below it still appears, ranked by score, so the floor can never cause a false `no_evidence`.

**Files:** Modify `rerank.py`, `models.py` (carry raw distance on `Hit`), `tests/unit/test_rerank_tier.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_local_evidence_leads_when_it_clears_the_floor():
    ranked = rerank_tiered([federal(dist=0.40), municipal(dist=0.48)], floor=0.55, ...)
    assert ranked[0].hit.chunk.extent_id == "CH-ZH-261"

def test_a_weak_local_chunk_does_not_leapfrog_but_is_still_returned():
    ranked = rerank_tiered([federal(dist=0.40), municipal(dist=0.72)], floor=0.55, ...)
    assert ranked[0].hit.chunk.extent_id == "CH"
    assert any(s.hit.chunk.extent_id == "CH-ZH-261" for s in ranked)   # not excluded
```

- [ ] **Step 2:** Carry the raw cosine distance from `hybrid_search` onto `Hit`; it is comparable across calls, unlike `score`. A chunk retrieved only by the lexical arm has no distance and does not claim a tier.
- [ ] **Step 3:** `RELEVANCE_FLOOR` goes in the same config as the rerank weights. **Do not calibrate it against the current corpus** — it is 71% federal and 100% boilerplate below canton level. Ship the documented default, calibrate after Task 6.

**Verification:** unit tests pass; probes re-recorded in Task 12.

---

## Task 10: New `swiss_search` contract

ADR 0004. The tool asks the caller for the question as written, the question in English, and a short English description of the topic.

**Files:** Modify `mcp_server/server.py`, `retrieval/models.py`, `cli/main.py`, `tests/integration/test_mcp_server.py`.

- [ ] **Step 1:** `QueryRequest` gains `question_en`, `topic_en`, `topics`. `question` stays the verbatim text and still feeds the lexical arm, so original-language terms have something to match against.
- [ ] **Step 2:** The search query embedded becomes `question_en + topic_en`; the lexical query stays the verbatim question.
- [ ] **Step 3:** Rewrite the tool docstring. It currently promises "most specific first" (untrue until Task 9) and an `as_of` that retrieves law "as it stood on that date" (untrue, see D2). Both claims must match behaviour.
- [ ] **Step 4:** Absent `question_en`, fall back to `question` and the local classifier, so an un-updated client degrades rather than breaks.

**Verification:** `uv run pytest tests/integration/test_mcp_server.py -q`; manual `/mcp` check that six tools still register.

---

## Task 11: `as_of` behaviour

*Blocked on decision D2.* Implement whichever option is chosen, plus the `valid_from is null` bypass, which is a defect under any of them.

**Files:** Modify `search.py`, `query_core.py`, `tests/unit/test_query_core_clock.py`.

- [ ] **Step 1:** Test that an `as_of` before the earliest indexed version is refused (or handled per D2) rather than silently returning only undated documents.
- [ ] **Step 2:** Test that a document with `valid_from is null` does not bypass an `as_of` filter.

---

## Task 12: Probes, re-record, and reconcile

Every probe file gains the fields the new contract requires. Ordering changes, so expectations change.

- [ ] **Step 1:** Add `question_en` and `topics` to all 47 probes, written by hand — a probe stays deterministic and must not depend on a model (`CONTEXT.md`, *Probe*).
- [ ] **Step 2:** Run the structural harness. Any probe that flips reports `XPASS(strict)`; flip its `status` in the same commit.
- [ ] **Step 3:** `uv run swiss-grounding eval probes --record` against the live database; reconcile red/green.
- [ ] **Step 4:** Expected movement — `com-015` and `city-007` should go green on the tier; `city-020` stays red, because SR 704 is not in the registry and no ranking change creates a missing source.
- [ ] **Step 5:** Update `README.md`: the `swiss_search` row in the tool table, the probe counts, and the note that `ingest` commits per source (issue #13) if Task 6 fixed it.

---

## Known gaps this plan does not close

- **No dog-tax or dog-registration content exists in the index** (0 chunks). Contextual retrieval makes evidence findable; it cannot make absent evidence present. Closing this needs new sources — a registry task, not a retrieval one.
- **Issue #10** (retrieval runs on the English translation) is only partly addressed. Keeping original terms in the generated context puts `Grüngutabfuhr` into the English index, but the dense arm still scores English text. The measured German penalty on category matching was ~0.18 similarity; the equivalent number for document retrieval has not been measured.
- **Issues #11, #12, #13, #14, #15** are untouched. #13 in particular should be fixed before Task 6, since a long backfill that commits only at the end repeats exactly the failure #13 describes.
- **The relevance floor is uncalibrated.** It ships with a documented default and must be fitted after Task 6, against a corpus that is neither 71% federal nor 100% boilerplate below canton level.

---

## Self-review notes

- Task order is by credit cost, not by importance. Tasks 1–4 need no model calls at all; Tasks 5–6 need roughly 630, reading only stored text; nothing in this plan requires a re-crawl or a re-translation.
- Task 1 makes coverage numbers *fall*. That is the honest number and the point of ADR 0005, but it will look like a regression to anyone reading the demo without the ADR.
- Generated context entering the retrieval surface is the riskiest change here. The test that citations never contain it is the guard, and it should not be relaxed.
- Two tasks are blocked on decisions D1 and D2. They are sequenced late so the rest is not held up.
