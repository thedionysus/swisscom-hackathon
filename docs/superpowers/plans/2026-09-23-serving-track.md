# Serving Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer questions from the encoded `corpus` schema through a six-tool, keyless MCP server that ranks by a reranker score (later a fitted relevance probability), abstains honestly with five distinct statuses, and is gated by a golden-set evaluation.

**Architecture:** A new `swiss_grounding.serving` package reads only the `corpus` schema. It filters by jurisdiction and validity, gathers candidates per language store from three arms (bge-m3 dense, bge-m3 sparse, per-language keyword), merges them with RRF, collapses them into translation groups, reranks each group's best language version with a local cross-encoder, and decides a status per place in the fixed order of ADR 0013. Three lookup tools (`swiss_premium`, `swiss_connections`, `swiss_reference_rate`) sit beside search. The old public-schema tools are replaced in Task 19.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 16 + pgvector 0.8 (vector, sparsevec, HNSW), FastMCP, sentence-transformers `CrossEncoder`, FlagEmbedding (bge-m3 dense + sparse), httpx, scikit-learn (fitting only), typer.

---

## Before you start

**Validate first, then build.** This plan was written on 2026-09-23 before the encoding run. Several numbers in it (provisional thresholds, candidate counts, quotas) are starting values that Task 28 checks against the real encoded corpus. When a claim in this plan is contradicted by the corpus, fix the plan and the ADR, not the data.

**Branch.** Start from `feat/encoding-track` once its Task 21 has merged or is at least committed: `git checkout -b feat/serving-track`. This plan reads tables, functions and providers the encoding track created. If a name below does not exist yet, stop and check the encoding plan (`docs/superpowers/plans/2026-09-23-encoding-track.md`) rather than inventing one.

**Never run paid commands by accident.** Only Task 21 (`eval label`) and Task 23 (`eval generate`) call a paid API model, and only when `--confirm-spend` is passed. Task 24 (`eval faithfulness`) drives `claude -p` on the user's own plan. Every other task runs keyless.

## Decisions this plan implements (do not re-open)

| Decision | Where |
|---|---|
| Serving is keyless on bge-m3; OpenAI index only when a key is configured | ADR 0006 (amended) |
| Every language store searched with the question as asked; client translations are an optional boost | ADR 0011 |
| Candidates by RRF; reranker score orders and abstains; translation group scored by its question-language (else best) version; reranker chosen by hardware; logistic relevance probability once labels exist | ADR 0012, `docs/RESEARCH.md` §H1 |
| Corroboration = share of the group's other authentic versions among candidates; monolingual = not applicable; English federal law never counts; divergent versions flagged | `CONTEXT.md` Corroboration, Divergent versions |
| Status order: foreign → no place → Swiss place outside scope → lookup failure → below threshold | ADR 0013 |
| Three lookup tools; holidays and waste stay indexed documents | ADR 0014 |
| Six tools, multi-place search, `get_document` by reference and language, scope line on `no_evidence`; computed amounts and commercial register outside scope | ADR 0015 |
| Golden set, generated questions, relevance labels, pass thresholds | ADR 0016 |
| Prebuilt `pg_dump` without the OpenAI index; setup rebuilds vector indexes | ADR 0017 |
| `hnsw.ef_search = 100`, `iterative_scan = relaxed_order`, at least 10 of 30 candidates from the resolved canton or municipality | `docs/RESEARCH.md` §H2 |

## What the encoding track provides (read, never write)

- Tables `corpus.source`, `corpus.translation_group`, `corpus.document`, `corpus.chunk` (partitioned by `language`), `corpus.emb_bge_m3` (`embedding vector(1024)`, `sparse sparsevec(250002)`), `corpus.emb_openai_3l` (`halfvec(3072)`); function `corpus.ts_config(lang)`; generated column `corpus.chunk.tsv`. See `src/swiss_grounding/corpus/schema.sql`.
- `chunk.status` values: `current`, `scheduled`, `superseded`, `withdrawn`, `boilerplate`. `document.status`: `current`, `scheduled`, `superseded`, `withdrawn`. `document.is_authentic` is false for English federal law.
- `swiss_grounding.corpus.providers`: `LocalBgeM3` (`embed_with_sparse`, `has_sparse`), `FakeEmbeddings(dim)`, `OpenAILLM`, `FakeLLM`, `LlmTask`, `Usage`, `INDEXES`.
- `swiss_grounding.corpus.budget`: `cost_usd`, `record_spend`, `ensure_within`, `BudgetExceeded`.
- Test fixture `corpus_db` in `tests/integration/conftest.py`: public schema + location tree + empty corpus schema.

## File structure

```
src/swiss_grounding/serving/
  __init__.py
  models.py          value types: SearchRequest, Candidate, GroupHit, Citation, PlaceResult, SearchResponse
  language.py        detect the question's language (stopword counts)
  scope.py           declared scope: cantons, municipalities, lookups, not-covered list, statement
  places.py          place outcomes: none / resolved / ambiguous / foreign / unresolved
  rrf.py             reciprocal rank fusion (pure)
  candidates.py      SQL arms (dense, sparse, keyword), filters, level quotas
  groups.py          collapse candidates into translation groups, corroboration
  reranker.py        Reranker protocol, CrossEncoderReranker (hardware choice), OverlapReranker (tests)
  relevance.py       features, provisional threshold, logistic model from JSON
  coverage.py        document counts per extent on the path (corpus schema)
  status.py          per-place status decision (ADR 0013 order)
  passages.py        pick the supporting passage inside a chunk
  search_service.py  orchestration for swiss_search
  documents.py       swiss_get_document: by id, by reference, by language; small-to-big
  call_log.py        latency and outcome log per tool call
  schema.sql         serving schema: call_log, lookup_cache, premium tables
  db.py              apply_serving_schema
src/swiss_grounding/lookups/
  __init__.py
  premium_data.py    load BAG premium CSV and premium regions into serving.premium*
  premium.py         swiss_premium query
  connections.py     swiss_connections (transport.opendata.ch)
  reference_rate.py  swiss_reference_rate (BWO page, last good value)
src/swiss_grounding/corpus/calendar.py      OpenERZ Zürich calendar -> corpus documents
src/swiss_grounding/evals/golden_models.py  golden probe schema
src/swiss_grounding/evals/metrics.py        recall@k, precision@k, nDCG@k, status accuracy (pure)
src/swiss_grounding/evals/golden_runner.py  run golden set against SearchService
src/swiss_grounding/evals/labels.py         model-judged relevance labels + human-check sample
src/swiss_grounding/evals/fit.py            fit logistic relevance model, choose threshold
src/swiss_grounding/evals/generate.py       generated questions from known chunks
src/swiss_grounding/cli/serving_commands.py `serving`, `lookups`, `dump`, `setup` commands
src/swiss_grounding/cli/eval_commands.py    + `eval golden|label|fit|generate`; probes stop writing without --record
src/swiss_grounding/mcp_server/server.py    rewritten: six tools
evals/golden/*.yaml                         the golden set
evals/relevance_model.json                  fitted model (written by Task 22)
```

Tests mirror this under `tests/unit/serving/`, `tests/unit/lookups/`, `tests/unit/evals/`, `tests/integration/serving/`.

---

### Task 0: Settings and dependencies

**Files:**
- Modify: `src/swiss_grounding/config.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config.py`:

```python
def test_serving_defaults_are_keyless(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    from swiss_grounding.config import Settings
    s = Settings(_env_file=None)
    assert s.serving_index == "bge-m3"
    assert s.reranker_model == "auto"
    assert s.rerank_candidates == 30
    assert s.local_candidate_quota == 10
    assert s.hnsw_ef_search == 100
    assert s.transport_base_url == "https://transport.opendata.ch/v1"
    assert s.lookup_timeout_seconds == 8.0
    assert s.relevance_model_path == "evals/relevance_model.json"


def test_openai_serving_index_needs_a_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    import pytest
    from swiss_grounding.config import Settings
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, serving_index="openai-3l")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -k "serving_defaults or openai_serving" -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'serving_index'`

- [ ] **Step 3: Add the settings**

In `src/swiss_grounding/config.py`, add these fields after `data_dir` and a validator after `_corpus_provider_needs_key`:

```python
    # Serving track. Keyless by default (ADR 0006): bge-m3 embeds the question locally.
    serving_index: Literal["bge-m3", "openai-3l"] = "bge-m3"
    # "auto" picks by hardware (ADR 0012): bge-reranker-v2-m3 on MPS/CUDA, the small model on CPU.
    reranker_model: str = "auto"
    reranker_gpu_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_cpu_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    reranker_max_tokens: int = 512
    rerank_candidates: int = 30
    local_candidate_quota: int = 10
    hnsw_ef_search: int = 100
    relevance_model_path: str = "evals/relevance_model.json"
    transport_base_url: str = "https://transport.opendata.ch/v1"
    reference_rate_url: str = "https://www.bwo.admin.ch/de/referenzzinssatz"
    lookup_timeout_seconds: float = 8.0
    dump_release_url: str = "https://github.com/thedionysus/swisscom-hackathon/releases/download/corpus-latest"
```

```python
    @model_validator(mode="after")
    def _openai_serving_needs_key(self) -> "Settings":
        if self.serving_index == "openai-3l" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when SERVING_INDEX=openai-3l")
        return self
```

In `pyproject.toml`, add an optional group for fitting (the server never imports it):

```toml
eval = [
    "scikit-learn>=1.5",
]
```

Run: `uv sync --extra embed --extra eval`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/config.py pyproject.toml uv.lock tests/unit/test_config.py
git commit -m "chore: serving-track settings and eval dependency group"
```

---

### Task 1: Serving value types

**Files:**
- Create: `src/swiss_grounding/serving/__init__.py` (empty)
- Create: `src/swiss_grounding/serving/models.py`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, and `__init__.py` in each new test directory
- Modify: `pyproject.toml` (pytest `pythonpath`)
- Test: `tests/unit/serving/test_models.py`

- [ ] **Step 0: Make test helpers importable**

Later tests share helpers (`from tests.integration.serving.corpus_fixture import add_doc`, `from tests.unit.serving.test_groups import cand`). Make `tests` a package and put the repository root on pytest's path:

```bash
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
mkdir -p tests/unit/serving tests/unit/lookups tests/integration/serving
touch tests/unit/serving/__init__.py tests/unit/lookups/__init__.py tests/integration/serving/__init__.py
test -f tests/unit/evals/__init__.py || touch tests/unit/evals/__init__.py
```

In `pyproject.toml` under `[tool.pytest.ini_options]` add `pythonpath = ["."]`. Run `uv run pytest -q` and confirm the count of passing tests is unchanged from before this step (package names of existing test modules change; nothing else should).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_models.py
from datetime import date

import pytest

from swiss_grounding.serving.models import (
    LANGS, MAX_LOCATIONS, SearchRequest, overall_status,
)


def test_request_rejects_more_than_three_places():
    with pytest.raises(ValueError, match="at most 3"):
        SearchRequest(question="x", locations=("Bern", "Lausanne", "Chur", "Scuol"))


def test_request_drops_unknown_translation_languages():
    r = SearchRequest(question="x", translations={"fr": "bonjour", "xx": "?", "de": " "})
    assert r.translations == {"fr": "bonjour"}


def test_overall_status_is_results_when_any_place_has_results():
    assert overall_status(("no_evidence", "results")) == "results"


def test_overall_status_prefers_outside_scope_over_no_evidence():
    assert overall_status(("no_evidence", "outside_scope")) == "outside_scope"


def test_constants():
    assert LANGS == ("de", "fr", "it", "en", "rm")
    assert MAX_LOCATIONS == 3
    assert SearchRequest(question="q", as_of=date(2026, 1, 1)).limit == 8
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swiss_grounding.serving'`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/models.py
"""Value types of the serving track. Everything here is immutable."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

Lang = Literal["de", "fr", "it", "en", "rm"]
LANGS: tuple[str, ...] = ("de", "fr", "it", "en", "rm")
MAX_LOCATIONS = 3
DEFAULT_LIMIT = 8
MAX_LIMIT = 20

Status = Literal["results", "needs_location", "outside_scope", "source_unavailable",
                 "no_evidence", "invalid_request"]
# When several places disagree, the response's top-level status is the most informative one.
STATUS_PRIORITY: tuple[str, ...] = ("results", "outside_scope", "needs_location",
                                    "source_unavailable", "no_evidence", "invalid_request")
NOTICE = "Retrieved public information from Swiss sources. Not legal advice."


def overall_status(statuses: Sequence[str]) -> str:
    return min(statuses, key=STATUS_PRIORITY.index) if statuses else "no_evidence"


@dataclass(frozen=True)
class SearchRequest:
    question: str
    locations: tuple[str, ...] = ()
    translations: Mapping[str, str] = field(default_factory=dict)
    as_of: date | None = None
    limit: int = DEFAULT_LIMIT

    def __post_init__(self) -> None:
        if len(self.locations) > MAX_LOCATIONS:
            raise ValueError(f"at most {MAX_LOCATIONS} locations per search")
        clean = {k: v.strip() for k, v in self.translations.items() if k in LANGS and v and v.strip()}
        object.__setattr__(self, "translations", clean)
        object.__setattr__(self, "limit", max(1, min(self.limit, MAX_LIMIT)))


@dataclass(frozen=True)
class Candidate:
    """One chunk found by at least one arm, with what citing it needs."""
    chunk_id: int
    language: str
    document_id: int
    translation_group_id: str
    align_key: str
    extent_id: str
    authority: str
    url: str
    anchor: str | None
    title: str
    publisher: str
    breadcrumb: tuple[str, ...]
    text: str
    is_authentic: bool
    valid_from: date | None
    valid_to: date | None
    modified_at: date | None
    fetched_at: datetime
    extraction: str
    rrf: float = 0.0
    rrf_rank: int = 0
    arms: frozenset[str] = frozenset()
    query_langs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GroupHit:
    """A translation group's candidates at one align key, scored through one representative."""
    representative: Candidate
    others: tuple[Candidate, ...]
    corroboration: float | None
    corroboration_basis: str | None
    versions_diverge: bool


@dataclass(frozen=True)
class ScoredGroup:
    group: GroupHit
    rerank_score: float
    relevance: float
    tier: int | None


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    title: str
    url: str
    anchor: str | None
    breadcrumb: tuple[str, ...]
    passage: str
    language: str
    other_languages: tuple[str, ...]
    publisher: str
    authority: str
    extent_id: str
    extent_label: str
    tier: int | None
    relevance: float
    corroboration: float | None
    corroboration_basis: str | None
    versions_diverge: bool
    valid_from: date | None
    modified_at: date | None
    fetched_at: datetime
    extraction: str


@dataclass(frozen=True)
class CoverageRow:
    extent_id: str
    label: str
    documents: int


@dataclass(frozen=True)
class PlaceResult:
    place: str | None
    status: Status
    location_id: str | None = None
    location_label: str | None = None
    message: str = ""
    citations: tuple[Citation, ...] = ()
    coverage: tuple[CoverageRow, ...] = ()
    uncovered_levels: tuple[str, ...] = ()
    """Levels of the place outside the declared scope ("cantonal", "municipal"); ADR 0013 step 3."""


@dataclass(frozen=True)
class SearchResponse:
    status: str
    places: tuple[PlaceResult, ...]
    message: str = ""
    scope: str = ""
    notice: str = NOTICE
    field: str | None = None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_models.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving tests pyproject.toml
git commit -m "feat: serving value types; tests importable as a package"
```

---

### Task 2: Question language detection

The representative of a translation group is its version in the question's language (ADR 0012). The server has no model at question time, so it counts short function words. Romansh comes first in ties, because Romansh shares many words with Italian and a Romansh question must reach the Romansh store.

**Files:**
- Create: `src/swiss_grounding/serving/language.py`
- Test: `tests/unit/serving/test_language.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_language.py
import pytest

from swiss_grounding.serving.language import detect_language


@pytest.mark.parametrize(("text", "lang"), [
    ("Wann wird bei uns das nächste Mal Karton abgeholt?", "de"),
    ("Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?", "fr"),
    ("Premio mensile più basso per un adulto di 30 anni a Lugano con franchigia 2500?", "it"),
    ("Cura èn las vacanzas d'atun 2026 per la scola da Scuol?", "rm"),
    ("What is the notice period for a rented flat?", "en"),
])
def test_detects_the_four_national_languages_and_english(text, lang):
    assert detect_language(text) == lang


def test_returns_none_when_no_function_word_matches():
    assert detect_language("SR 220 Art. 266c") is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_language.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/language.py
"""Which language a question is in, from function words only (no model at question time)."""
import re

FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "rm": frozenset({"cura", "èn", "las", "ils", "da", "dal", "dals", "per", "la", "scola", "scoula",
                     "co", "tge", "vegn", "ha", "nus", "vus", "quai", "quel", "pli", "betg", "brich",
                     "nossa", "vossa", "vschinauncha", "vischnanca", "atun", "d'atun", "ed", "u"}),
    "de": frozenset({"der", "die", "das", "und", "ist", "wie", "wann", "wird", "bei", "uns", "ich",
                     "mein", "meine", "meinem", "nach", "für", "mit", "nicht", "ein", "eine", "im",
                     "den", "dem", "des", "zu", "auf", "was", "welche", "muss", "kann"}),
    "fr": frozenset({"le", "les", "des", "et", "est", "mon", "ma", "mes", "dans", "pour", "combien",
                     "quand", "comment", "une", "du", "au", "aux", "je", "que", "qui", "sur", "en",
                     "pas", "quel", "quelle", "doit", "peut"}),
    "it": frozenset({"il", "lo", "gli", "le", "di", "del", "della", "per", "con", "un", "una", "è",
                     "più", "quando", "come", "quanto", "mio", "mia", "che", "non", "sono", "nel",
                     "alla", "dove", "quale", "devo", "posso"}),
    "en": frozenset({"the", "is", "what", "when", "how", "for", "my", "of", "and", "to", "in", "do",
                     "does", "can", "which", "a", "an", "i", "must", "should"}),
}
# Order breaks ties: Romansh before Italian (shared words), German before English.
TIE_ORDER: tuple[str, ...] = ("rm", "de", "fr", "it", "en")
WORD = re.compile(r"[a-zà-ÿ']+")


def detect_language(text: str) -> str | None:
    words = WORD.findall(text.lower())
    counts = {lang: sum(1 for w in words if w in vocab) for lang, vocab in FUNCTION_WORDS.items()}
    best = max(counts.values(), default=0)
    if best == 0:
        return None
    return next(lang for lang in TIE_ORDER if counts[lang] == best)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_language.py -v`
Expected: 6 PASS. If the Romansh case fails because it ties with Italian and loses, check `TIE_ORDER` puts `rm` first; if a case genuinely scores higher for the wrong language, add the missing distinctive words to that language's set rather than changing the test.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/language.py tests/unit/serving/test_language.py
git commit -m "feat: detect the question language from function words"
```

---

### Task 3: Declared scope

**Files:**
- Create: `src/swiss_grounding/serving/scope.py`
- Test: `tests/unit/serving/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_scope.py
from swiss_grounding.serving.scope import (
    SCOPE_CANTONS, SCOPE_MUNICIPALITIES, covered_levels, scope_statement,
)


def test_scope_lists_six_cantons_and_seven_municipalities():
    assert SCOPE_CANTONS == ("CH-ZH", "CH-BE", "CH-VD", "CH-GE", "CH-TI", "CH-GR")
    assert len(SCOPE_MUNICIPALITIES) == 7 and "CH-GR-3762" in SCOPE_MUNICIPALITIES


def test_municipality_in_scope_covers_every_level():
    assert covered_levels(("CH", "CH-GR", "CH-GR-3762")) == ("federal", "cantonal", "municipal")


def test_neighbourhood_of_a_scope_city_is_covered():
    assert covered_levels(("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")) == ("federal", "cantonal", "municipal")


def test_other_municipality_in_a_scope_canton_is_cantonal_only():
    assert covered_levels(("CH", "CH-ZH", "CH-ZH-230")) == ("federal", "cantonal")


def test_basel_is_federal_only():
    assert covered_levels(("CH", "CH-BS", "CH-BS-2701")) == ("federal",)


def test_statement_names_what_is_not_covered():
    text = scope_statement()
    for phrase in ("commercial register", "tax bills", "weather", "Scuol"):
        assert phrase in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_scope.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/scope.py
"""The declared scope (ADR 0009, amended by ADR 0014 and ADR 0015), quotable by the server."""
from collections.abc import Sequence

SCOPE_CANTONS: tuple[str, ...] = ("CH-ZH", "CH-BE", "CH-VD", "CH-GE", "CH-TI", "CH-GR")
SCOPE_MUNICIPALITIES: tuple[str, ...] = (
    "CH-ZH-261",   # Zürich
    "CH-BE-351",   # Bern
    "CH-VD-5586",  # Lausanne
    "CH-GE-6621",  # Genève
    "CH-TI-5192",  # Lugano
    "CH-GR-3901",  # Chur
    "CH-GR-3762",  # Scuol
)
MUNICIPALITY_NAMES = "Zürich, Bern, Lausanne, Genève, Lugano, Chur and Scuol"
CANTON_NAMES = "Zurich, Bern, Vaud, Geneva, Ticino and Graubünden"
LOOKUPS = ("health insurance premiums", "public transport connections", "the reference interest rate")
NOT_COVERED = (
    "places outside Switzerland",
    "computed amounts such as tax bills or pensions (the official rules and calculators are cited instead)",
    "the commercial register",
    "statistics, geodata and weather",
    "cantonal and municipal rules outside the named cantons and municipalities",
)


def covered_levels(path: Sequence[str]) -> tuple[str, ...]:
    """Which levels of a resolved path the declared scope covers. Federal is always covered."""
    levels = ["federal"]
    if len(path) > 1 and path[1] in SCOPE_CANTONS:
        levels.append("cantonal")
        if len(path) > 2 and path[2] in SCOPE_MUNICIPALITIES:
            levels.append("municipal")
    return tuple(levels)


def scope_statement() -> str:
    return (
        "Covered: federal information for all of Switzerland; cantonal information for "
        f"{CANTON_NAMES}; municipal services for {MUNICIPALITY_NAMES}; lookups for "
        f"{', '.join(LOOKUPS)}. Not covered: {'; '.join(NOT_COVERED)}."
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_scope.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/scope.py tests/unit/serving/test_scope.py
git commit -m "feat: declared scope the server can quote"
```

---

### Task 4: Place outcomes (ADR 0013, steps 1–3)

A place is judged from the `locations` argument when the client sends one, otherwise from the question. We keep **no list of foreign places** (ADR 0013). A place argument that the Swiss register cannot resolve is an *unresolved place*, treated as outside Switzerland with a hint to retry a misspelling. A country other than Switzerland named in the argument, or in a question with no Swiss place, makes the question foreign. Country words are not place lists: there are only a handful, and they are complete.

**Files:**
- Create: `src/swiss_grounding/serving/places.py`
- Test: `tests/unit/serving/test_places.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_places.py
from swiss_grounding.locations.models import AmbiguousLocation, Level, Location, ResolvedLocation
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.places import place_outcomes

CH = Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"})
GR = Location("CH-GR", "CH", Level.CANTON, 18, None, {"de": "Graubünden"}, ("GR",))
SCUOL = Location("CH-GR-3762", "CH-GR", Level.MUNICIPALITY, 3762, None, {"de": "Scuol"})
BS = Location("CH-BS", "CH", Level.CANTON, 12, None, {"de": "Basel-Stadt"})
BASEL = Location("CH-BS-2701", "CH-BS", Level.MUNICIPALITY, 2701, None, {"de": "Basel"})
TREE = LocationTree.from_locations([CH, GR, SCUOL, BS, BASEL])


class StubResolver:
    def __init__(self, answers):
        self.answers = answers

    def resolve(self, text):
        return self.answers.get(text.strip())


def resolved(loc):
    return ResolvedLocation(loc, TREE.path(loc.id), "alias", loc.label())


def test_unknown_place_argument_is_unresolved():
    [o] = place_outcomes("Rundfunkbeitrag nach dem Umzug?", ("Konstanz",), StubResolver({}), TREE)
    assert o.kind == "unresolved" and o.text == "Konstanz"


def test_argument_with_a_foreign_country_is_foreign():
    [o] = place_outcomes("Rundfunkbeitrag?", ("Konstanz, Deutschland",), StubResolver({}), TREE)
    assert o.kind == "foreign"


def test_swiss_suffix_is_ignored():
    [o] = place_outcomes("q", ("Scuol, Schweiz",), StubResolver({"Scuol": resolved(SCUOL)}), TREE)
    assert o.kind == "resolved" and o.covered == ("federal", "cantonal", "municipal")


def test_swiss_place_outside_scope_is_resolved_with_federal_cover_only():
    [o] = place_outcomes("Hundesteuer?", ("Basel",), StubResolver({"Basel": resolved(BASEL)}), TREE)
    assert o.kind == "resolved" and o.covered == ("federal",)


def test_ambiguous_argument():
    amb = AmbiguousLocation("Wil", (SCUOL, BASEL), "two places")
    [o] = place_outcomes("q", ("Wil",), StubResolver({"Wil": amb}), TREE)
    assert o.kind == "ambiguous" and len(o.candidates) == 2


def test_question_naming_a_swiss_place_resolves_from_the_question():
    [o] = place_outcomes("Cura èn las vacanzas d'atun a Scuol?", (), StubResolver({}), TREE)
    assert o.kind == "resolved" and o.resolved.location.id == "CH-GR-3762"


def test_question_naming_only_a_foreign_country_is_foreign():
    [o] = place_outcomes("Wie melde ich mich in Deutschland an?", (), StubResolver({}), TREE)
    assert o.kind == "foreign" and o.text == "Deutschland"


def test_moving_from_a_swiss_place_abroad_stays_swiss():
    [o] = place_outcomes("Abmelden in Scuol vor dem Umzug nach Deutschland?", (), StubResolver({}), TREE)
    assert o.kind == "resolved"


def test_no_place_at_all():
    [o] = place_outcomes("Kündigungsfrist Mietwohnung?", (), StubResolver({}), TREE)
    assert o.kind == "none"


def test_three_places_give_three_outcomes():
    r = StubResolver({"Scuol": resolved(SCUOL), "Basel": resolved(BASEL)})
    kinds = [o.kind for o in place_outcomes("q", ("Scuol", "Basel", "Lindau (Bodensee)"), r, TREE)]
    assert kinds == ["resolved", "resolved", "unresolved"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_places.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/places.py
"""What the question's place is (ADR 0013). No list of foreign places is kept."""
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from swiss_grounding.locations.models import AmbiguousLocation, Location, ResolvedLocation
from swiss_grounding.locations.question_scan import resolve_from_question
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.scope import covered_levels

PlaceKind = Literal["none", "resolved", "ambiguous", "foreign", "unresolved"]
# Country names only (de/fr/it/en/rm), plus words for "abroad". Complete by construction.
FOREIGN_COUNTRY_WORDS: frozenset[str] = frozenset({
    "deutschland", "germany", "allemagne", "germania", "germania",
    "frankreich", "france", "francia", "frantscha",
    "italien", "italy", "italie", "italia", "italia",
    "österreich", "oesterreich", "austria", "autriche", "austria",
    "liechtenstein", "fürstentum",
    "ausland", "étranger", "etranger", "estero", "abroad", "exteriur",
})
SWISS_SUFFIX = re.compile(r",?\s*\b(schweiz|switzerland|suisse|svizzera|svizra|ch)\s*$", re.IGNORECASE)
WORD = re.compile(r"[a-zà-ÿ]+")


class Resolver(Protocol):
    def resolve(self, text: str) -> ResolvedLocation | AmbiguousLocation | None: ...


@dataclass(frozen=True)
class PlaceOutcome:
    kind: PlaceKind
    text: str | None = None
    resolved: ResolvedLocation | None = None
    candidates: tuple[Location, ...] = ()
    covered: tuple[str, ...] = ()


def _foreign_word(text: str) -> str | None:
    for raw in WORD.findall(text.lower()):
        if raw in FOREIGN_COUNTRY_WORDS:
            start = text.lower().find(raw)
            return text[start:start + len(raw)]
    return None


def _from_resolution(text: str, found) -> PlaceOutcome:
    if isinstance(found, AmbiguousLocation):
        return PlaceOutcome("ambiguous", text, candidates=found.candidates)
    if found is None:
        return PlaceOutcome("unresolved", text)
    return PlaceOutcome("resolved", text, resolved=found, covered=covered_levels(found.path))


def _from_argument(text: str, resolver: Resolver) -> PlaceOutcome:
    if _foreign_word(text):
        return PlaceOutcome("foreign", text.strip())
    cleaned = SWISS_SUFFIX.sub("", text).strip()
    return _from_resolution(text.strip(), resolver.resolve(cleaned))


def place_outcomes(question: str, locations: Sequence[str], resolver: Resolver,
                   tree: LocationTree) -> tuple[PlaceOutcome, ...]:
    """One outcome per place argument; one outcome for the question when no argument was sent."""
    if locations:
        return tuple(_from_argument(t, resolver) for t in locations)
    scanned = resolve_from_question(tree, question)
    if scanned is not None:
        return (_from_resolution(scanned.input_text, scanned),)
    foreign = _foreign_word(question)
    if foreign:
        return (PlaceOutcome("foreign", foreign),)
    return (PlaceOutcome("none"),)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_places.py -v`
Expected: 10 PASS. If `test_question_naming_a_swiss_place_resolves_from_the_question` fails because `resolve_from_question` rejects "Scuol" in that sentence, inspect its guards (`question_scan._keep`) rather than weakening the test: a Romansh question naming Scuol is a golden case.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/places.py tests/unit/serving/test_places.py
git commit -m "feat: place outcomes with foreign and unresolved places (ADR 0013)"
```

---

### Task 5: Rank fusion and the local quota (pure)

**Files:**
- Create: `src/swiss_grounding/serving/rrf.py`
- Test: `tests/unit/serving/test_rrf.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_rrf.py
from swiss_grounding.serving.rrf import RRF_K, fuse, select_with_quota


def test_fuse_sums_reciprocal_ranks_and_records_arms():
    fused = fuse({"dense": ["a", "b"], "sparse": ["b", "c"]})
    assert [key for key, _, _ in fused] == ["b", "a", "c"]
    score_b = 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert abs(fused[0][1] - score_b) < 1e-12
    assert fused[0][2] == frozenset({"dense", "sparse"})


def test_fuse_is_stable_for_ties():
    fused = fuse({"x": ["a"], "y": ["b"]})
    assert [key for key, _, _ in fused] == ["a", "b"]


def test_quota_pulls_local_items_into_the_top_n():
    order = ["f1", "f2", "f3", "l1", "f4", "l2"]
    chosen = select_with_quota(order, is_local=lambda k: k.startswith("l"), n=4, quota=2)
    assert chosen == ["f1", "f2", "l1", "l2"]


def test_quota_does_not_invent_local_items():
    chosen = select_with_quota(["f1", "f2", "f3"], is_local=lambda k: False, n=2, quota=2)
    assert chosen == ["f1", "f2"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_rrf.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/rrf.py
"""Reciprocal rank fusion and the local-candidate quota (RESEARCH §H2)."""
from collections.abc import Callable, Hashable, Mapping, Sequence

RRF_K = 60


def fuse(lists: Mapping[str, Sequence[Hashable]]) -> list[tuple[Hashable, float, frozenset[str]]]:
    """(key, score, arms that found it), best first; ties keep first-seen order."""
    scores: dict[Hashable, float] = {}
    arms: dict[Hashable, set[str]] = {}
    for arm, keys in lists.items():
        for rank, key in enumerate(keys, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            arms.setdefault(key, set()).add(arm)
    order = sorted(scores, key=lambda k: -scores[k])
    return [(k, scores[k], frozenset(arms[k])) for k in order]


def select_with_quota(order: Sequence[Hashable], *, is_local: Callable[[Hashable], bool],
                      n: int, quota: int) -> list[Hashable]:
    """The top `n` of `order`, guaranteeing up to `quota` local items, keeping `order`'s sequence."""
    local = [k for k in order if is_local(k)][:quota]
    rest = [k for k in order if k not in set(local)][: max(0, n - len(local))]
    keep = set(local) | set(rest)
    return [k for k in order if k in keep]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_rrf.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/rrf.py tests/unit/serving/test_rrf.py
git commit -m "feat: rank fusion with a local-candidate quota"
```

---

### Task 6: Candidate arms over the corpus schema

Three arms per search: dense (bge-m3, or OpenAI when configured), sparse (bge-m3 lexical weights), and keyword (one per language store, each with its own text-search configuration). Hard filters: extent on the resolved path, validity, and no boilerplate. When the client sent translations, each translated text is also embedded and searched in its own language store (ADR 0011).

**Files:**
- Create: `src/swiss_grounding/serving/candidates.py`
- Create: `tests/integration/serving/corpus_fixture.py`
- Test: `tests/integration/serving/test_candidates.py`

- [ ] **Step 1: Write the fixture helper**

```python
# tests/integration/serving/corpus_fixture.py
"""Insert small corpus documents for serving tests. Embeddings come from FakeEmbeddings(1024)."""
from datetime import UTC, date, datetime

from pgvector import SparseVector

from swiss_grounding.corpus.providers import FakeEmbeddings

EMB = FakeEmbeddings(1024)
NOW = datetime(2026, 9, 20, tzinfo=UTC)


def add_source(conn, source_id="src", extent="CH", level="federal", authority="federal_law"):
    conn.execute(
        "insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages) "
        "values (%s,%s,%s,%s,%s,%s,'html',1,'{de,fr,it,en}') on conflict (id) do nothing",
        (source_id, source_id, f"Publisher {source_id}", authority, level, extent))


def add_group(conn, group_id):
    conn.execute("insert into corpus.translation_group (id, work_key) values (%s,%s) on conflict do nothing",
                 (group_id, group_id))


def add_doc(conn, *, group, lang, text, extent="CH", source="src", authority="federal_law",
            align="art-1", authentic=True, status="current", valid_from=None, valid_to=None,
            chunk_status="current", sparse=None, url=None, title="Title", breadcrumb=("Art. 1",)):
    add_source(conn, source, extent, "federal" if extent == "CH" else "municipal", authority)
    add_group(conn, group)
    doc_id = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, publisher, "
        "authority, extent_id, is_authentic, valid_from, valid_to, status, fetched_at, last_seen_at, content_hash) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'h') returning id",
        (source, url or f"https://example.ch/{group}/{lang}/{align}", lang, group, title, f"Publisher {source}",
         authority, extent, authentic, valid_from, valid_to, status, NOW, NOW)).fetchone()["id"]
    chunk_id = conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
        "text, extent_id, authority, status, chunk_hash) values (%s,%s,%s,%s,0,%s,%s,%s,%s,%s,'c') returning id",
        (doc_id, lang, group, align, list(breadcrumb), text, extent, authority, chunk_status)).fetchone()["id"]
    vec = EMB.embed([text])[0]
    conn.execute(
        "insert into corpus.emb_bge_m3 (chunk_id, language, text_hash, embedding, sparse) values (%s,%s,'t',%s,%s)",
        (chunk_id, lang, vec, SparseVector(sparse, 250002) if sparse else None))
    return doc_id, chunk_id


DAY = date(2026, 1, 1)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/integration/serving/test_candidates.py
from datetime import date

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.candidates import ArmQuery, gather_candidates
from tests.integration.serving.corpus_fixture import EMB, add_doc

pytestmark = pytest.mark.integration
PATH_ZH = ("CH", "CH-ZH", "CH-ZH-261")


def _query(text, **kw):
    return ArmQuery(question=text, question_lang=kw.get("lang"), question_vec=EMB.embed([text])[0], question_sparse=None,
                    translations={}, translation_vecs={}, extent_path=kw.get("path", PATH_ZH),
                    local_extents=kw.get("local", ("CH-ZH", "CH-ZH-261")), as_of=kw.get("as_of"),
                    per_arm=10, top_n=kw.get("top_n", 30), local_quota=kw.get("quota", 10))


def test_finds_a_chunk_on_the_path_by_keyword_and_vector(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g1", lang="de", text="Kündigungsfrist für Wohnungen drei Monate")
        found = gather_candidates(conn, _query("Kündigungsfrist Wohnungen"), index="bge-m3", ef_search=100)
    assert found[0].translation_group_id == "g1"
    assert {"dense", "kw_de"} <= found[0].arms


def test_off_path_extents_are_filtered_out(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="bern", lang="de", text="Hundesteuer Bern", extent="CH-BE-351", source="bern")
        found = gather_candidates(conn, _query("Hundesteuer"), index="bge-m3", ef_search=100)
    assert found == []


def test_boilerplate_and_superseded_are_filtered_out(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="b", lang="de", text="Cookie Hinweis Datenschutz", chunk_status="boilerplate")
        add_doc(conn, group="s", lang="de", text="Cookie Hinweis alt", status="superseded")
        found = gather_candidates(conn, _query("Cookie Hinweis"), index="bge-m3", ef_search=100)
    assert found == []


def test_as_of_selects_the_version_valid_on_that_day(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="v", lang="de", text="Frist alt", status="superseded", align="a",
                valid_from=date(2020, 1, 1), valid_to=date(2026, 1, 1))
        add_doc(conn, group="v", lang="de", text="Frist neu", align="a", valid_from=date(2026, 1, 1))
        old = gather_candidates(conn, _query("Frist", as_of=date(2025, 6, 1)), index="bge-m3", ef_search=100)
    assert [c.text for c in old] == ["Frist alt"]


def test_keyword_arm_searches_every_language_store(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="sr", lang="fr", text="Art. 266c CO délai", align="266c")
        found = gather_candidates(conn, _query("266c"), index="bge-m3", ef_search=100)
    assert "kw_fr" in found[0].arms


def test_local_quota_keeps_municipal_chunks_in_the_pool(corpus_db):
    with connect(corpus_db) as conn:
        for i in range(5):
            add_doc(conn, group=f"fed{i}", lang="de", text=f"Abfall Bund Regel {i} Abfall")
        add_doc(conn, group="city", lang="de", text="Karton Sammlung Stadt", extent="CH-ZH-261", source="zh")
        found = gather_candidates(conn, _query("Abfall", top_n=3, quota=1), index="bge-m3", ef_search=100)
    assert "city" in {c.translation_group_id for c in found}
    assert len(found) == 3


def test_empty_path_searches_all_of_switzerland(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="bern", lang="de", text="Hundesteuer Bern", extent="CH-BE-351", source="bern")
        found = gather_candidates(conn, _query("Hundesteuer", path=(), local=()), index="bge-m3", ef_search=100)
    assert [c.extent_id for c in found] == ["CH-BE-351"]


def test_translation_is_searched_in_its_own_store(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g", lang="fr", text="délai de congé logement", align="x")
        q = _query("Kündigungsfrist Wohnung")
        vec = EMB.embed(["délai de congé logement"])[0]
        q = q.__class__(**{**q.__dict__, "translations": {"fr": "délai de congé logement"},
                           "translation_vecs": {"fr": vec}})
        found = gather_candidates(conn, q, index="bge-m3", ef_search=100)
    assert {"dense_fr", "kw_fr"} <= found[0].arms
    assert "fr" in found[0].query_langs
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/integration/serving/test_candidates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swiss_grounding.serving.candidates'`

- [ ] **Step 4: Write the implementation**

```python
# src/swiss_grounding/serving/candidates.py
"""Candidate generation over the corpus schema: dense, sparse and per-language keyword arms."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
import psycopg
from pgvector import SparseVector

from swiss_grounding.corpus.providers import BGE_M3_VOCAB
from swiss_grounding.serving.models import LANGS, Candidate
from swiss_grounding.serving.rrf import fuse, select_with_quota

COLUMNS = (
    "c.id as chunk_id, c.language, c.document_id, c.translation_group_id, c.align_key, c.extent_id, "
    "c.authority, d.url, c.anchor, d.title, d.publisher, c.breadcrumb, c.text, d.is_authentic, "
    "d.valid_from, d.valid_to, d.modified_at, d.fetched_at, d.extraction"
)
CURRENT = "d.status = 'current' and c.status = 'current'"
AS_OF = ("d.status in ('current','scheduled','superseded') and c.status <> 'boilerplate' "
         "and d.valid_from is not null and d.valid_from <= %(as_of)s "
         "and (d.valid_to is null or d.valid_to > %(as_of)s)")
EMB_TABLE = {"bge-m3": ("corpus.emb_bge_m3", "vector"), "openai-3l": ("corpus.emb_openai_3l", "halfvec")}


@dataclass(frozen=True)
class ArmQuery:
    question: str
    question_lang: str | None
    question_vec: np.ndarray
    question_sparse: Mapping[int, float] | None
    translations: Mapping[str, str]
    translation_vecs: Mapping[str, np.ndarray]
    extent_path: Sequence[str]
    local_extents: Sequence[str]
    as_of: date | None
    per_arm: int
    top_n: int
    local_quota: int


def filters(as_of: date | None, extents: Sequence[str]) -> str:
    """Validity filter, plus the extent filter unless the search spans all of Switzerland (no place)."""
    validity = AS_OF if as_of else CURRENT
    return validity + " and c.extent_id = any(%(extents)s)" if extents else validity


def _base(q: ArmQuery, extents: Sequence[str]) -> dict:
    return {"extents": list(extents), "as_of": q.as_of, "n": q.per_arm}


def _vector_arm(conn, q: ArmQuery, index: str, vec, extents, lang: str | None) -> list[dict]:
    table, cast = EMB_TABLE[index]
    lang_clause = " and c.language = %(lang)s" if lang else ""
    sql = (f"select {COLUMNS} from {table} e join corpus.chunk c on c.id = e.chunk_id and c.language = e.language "
           f"join corpus.document d on d.id = c.document_id where {filters(q.as_of, extents)}{lang_clause} "
           f"order by e.embedding <=> %(vec)s::{cast} limit %(n)s")
    return conn.execute(sql, {**_base(q, extents), "vec": vec, "lang": lang}).fetchall()


def _sparse_arm(conn, q: ArmQuery, extents) -> list[dict]:
    sql = (f"select {COLUMNS} from corpus.emb_bge_m3 e join corpus.chunk c on c.id = e.chunk_id "
           f"and c.language = e.language join corpus.document d on d.id = c.document_id "
           f"where e.sparse is not null and {filters(q.as_of, extents)} order by e.sparse <#> %(sparse)s limit %(n)s")
    sparse = SparseVector(dict(q.question_sparse), BGE_M3_VOCAB)
    return conn.execute(sql, {**_base(q, extents), "sparse": sparse}).fetchall()


def _keyword_arm(conn, q: ArmQuery, lang: str, text: str, extents) -> list[dict]:
    sql = (f"select {COLUMNS} from corpus.chunk c join corpus.document d on d.id = c.document_id "
           f"where c.language = %(lang)s and {filters(q.as_of, extents)} "
           f"and c.tsv @@ websearch_to_tsquery(corpus.ts_config(%(lang)s), %(text)s) "
           f"order by ts_rank_cd(c.tsv, websearch_to_tsquery(corpus.ts_config(%(lang)s), %(text)s)) desc "
           f"limit %(n)s")
    return conn.execute(sql, {**_base(q, extents), "lang": lang, "text": text}).fetchall()


def _arms(conn, q: ArmQuery, index: str, extents) -> dict[str, list[dict]]:
    arms = {"dense": _vector_arm(conn, q, index, q.question_vec, extents, None)}
    if q.question_sparse and index == "bge-m3":
        arms["sparse"] = _sparse_arm(conn, q, extents)
    for lang in LANGS:
        arms[f"kw_{lang}"] = _keyword_arm(conn, q, lang, q.translations.get(lang, q.question), extents)
    for lang, vec in q.translation_vecs.items():
        arms[f"dense_{lang}"] = _vector_arm(conn, q, index, vec, extents, lang)
    return arms


def _query_lang(arm: str, q: ArmQuery) -> str | None:
    """The language of the text an arm searched with: a translation's language, else the question's."""
    if arm.startswith("dense_"):
        return arm.split("_", 1)[1]
    if arm.startswith("kw_") and arm.split("_", 1)[1] in q.translations:
        return arm.split("_", 1)[1]
    return q.question_lang


def gather_candidates(conn: psycopg.Connection, q: ArmQuery, *, index: str, ef_search: int) -> list[Candidate]:
    conn.execute("select set_config('hnsw.ef_search', %s, true)", (str(ef_search),))
    conn.execute("select set_config('hnsw.iterative_scan', 'relaxed_order', true)")
    rows: dict[tuple[int, str], dict] = {}
    lists: dict[str, list[tuple[int, str]]] = {}
    scopes = {"": q.extent_path, "local_": q.local_extents} if q.local_extents else {"": q.extent_path}
    for prefix, extents in scopes.items():
        for arm, found in _arms(conn, q, index, extents).items():
            keys = [(r["chunk_id"], r["language"]) for r in found]
            rows.update({k: r for k, r in zip(keys, found, strict=True)})
            lists[prefix + arm] = keys
    fused = fuse(lists)
    local = set(q.local_extents)
    chosen = select_with_quota([k for k, _, _ in fused], is_local=lambda k: rows[k]["extent_id"] in local,
                               n=q.top_n, quota=q.local_quota)
    info = {k: (score, arms) for k, score, arms in fused}
    out = []
    for rank, key in enumerate(chosen, start=1):
        score, arms = info[key]
        plain = frozenset(a.removeprefix("local_") for a in arms)
        langs = frozenset(filter(None, (_query_lang(a, q) for a in plain)))
        row = rows[key]
        out.append(Candidate(**{**row, "breadcrumb": tuple(row["breadcrumb"]), "rrf": score, "rrf_rank": rank,
                                "arms": plain, "query_langs": langs}))
    return out
```

Notes for the implementer:
- `set_config(..., true)` scopes the setting to the current transaction, which `connect()` opens.
- `query_langs` records the language of the *text* that found a chunk: a translation's language for `dense_L` and for `kw_L` when a translation for `L` was sent, otherwise the detected question language. Task 7 uses it to tell `independent` from `cross_lingual` corroboration.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/serving/test_candidates.py -v`
Expected: 8 PASS. If `test_as_of_selects_the_version_valid_on_that_day` fails because the encoding track's persist sets `chunk.status = 'superseded'` on old versions, that is expected and the `AS_OF` filter already allows it; if it sets another value, extend the filter to that value and note it in the plan.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/serving/candidates.py tests/integration/serving
git commit -m "feat: dense, sparse and per-language keyword arms over the corpus schema"
```

---

### Task 7: Translation groups and corroboration

Candidates at the same `(translation_group_id, align_key)` are language versions of one passage. We score the group once, through its version in the question's language when one exists in the corpus (even if that version was not itself a candidate), otherwise through its best-ranked candidate (ADR 0012). Corroboration is the share of the group's *other authentic* versions found among the candidates. A group with no other authentic version gets `None` ("not applicable"). Versions with different `valid_from` are divergent and never corroborate (`CONTEXT.md`).

**Files:**
- Create: `src/swiss_grounding/serving/groups.py`
- Test: `tests/unit/serving/test_groups.py`
- Test: `tests/integration/serving/test_aligned_versions.py`

- [ ] **Step 1: Write the failing unit test**

```python
# tests/unit/serving/test_groups.py
from datetime import UTC, date, datetime

from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.models import Candidate

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def cand(lang, rank=1, group="g", align="a", authentic=True, valid_from=None, query_langs=("de",), cid=None):
    return Candidate(
        chunk_id=cid or hash((group, align, lang)) % 10_000, language=lang, document_id=1,
        translation_group_id=group, align_key=align, extent_id="CH", authority="federal_law",
        url=f"https://x/{lang}", anchor=None, title="t", publisher="p", breadcrumb=(), text=f"text {lang}",
        is_authentic=authentic, valid_from=valid_from, valid_to=None, modified_at=None, fetched_at=NOW,
        extraction="native", rrf=1 / (60 + rank), rrf_rank=rank, arms=frozenset({"dense"}),
        query_langs=frozenset(query_langs))


def test_question_language_version_represents_the_group_even_if_not_a_candidate():
    found = [cand("fr", rank=1)]
    versions = {("g", "a"): (cand("de"), cand("fr"), cand("it"), cand("en", authentic=False))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.representative.language == "de"
    assert g.representative.rrf_rank == 1


def test_corroboration_is_the_share_of_other_authentic_versions_found():
    found = [cand("de", 1), cand("fr", 2), cand("en", 3, authentic=False)]
    versions = {("g", "a"): (cand("de"), cand("fr"), cand("it"), cand("en", authentic=False))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.corroboration == 0.5          # fr found, it not; en never counts
    assert g.corroboration_basis == "cross_lingual"


def test_monolingual_group_is_not_applicable():
    [g] = collapse([cand("it")], {("g", "a"): (cand("it"),)}, question_lang="it")
    assert g.corroboration is None and g.corroboration_basis is None


def test_independent_basis_when_each_version_was_found_by_text_in_its_own_language():
    found = [cand("de", 1, query_langs=("de",)), cand("fr", 2, query_langs=("fr",))]
    versions = {("g", "a"): (cand("de"), cand("fr"))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.corroboration == 1.0 and g.corroboration_basis == "independent"


def test_divergent_versions_are_flagged_and_do_not_corroborate():
    found = [cand("de", 1, valid_from=date(2026, 1, 1)), cand("fr", 2, valid_from=date(2025, 1, 1))]
    versions = {("g", "a"): (found[0], found[1])}
    [g] = collapse(found, versions, question_lang="de")
    assert g.versions_diverge is True and g.corroboration == 0.0


def test_groups_keep_candidate_order():
    found = [cand("de", 1, group="b"), cand("de", 2, group="a")]
    groups = collapse(found, {}, question_lang="de")
    assert [g.representative.translation_group_id for g in groups] == ["b", "a"]
```

- [ ] **Step 2: Write the failing integration test**

```python
# tests/integration/serving/test_aligned_versions.py
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.groups import aligned_versions
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def test_loads_every_live_version_of_the_keys(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="g", lang="de", text="Frist", align="art_1")
        add_doc(conn, group="g", lang="fr", text="Délai", align="art_1")
        add_doc(conn, group="g", lang="it", text="Termine", align="art_2")
        versions = aligned_versions(conn, [("g", "art_1")], as_of=None)
    assert sorted(v.language for v in versions[("g", "art_1")]) == ["de", "fr"]
```

- [ ] **Step 3: Run both to verify they fail**

Run: `uv run pytest tests/unit/serving/test_groups.py tests/integration/serving/test_aligned_versions.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

```python
# src/swiss_grounding/serving/groups.py
"""Collapse candidates into translation groups; corroboration over authentic versions."""
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date

import psycopg

from swiss_grounding.serving.candidates import COLUMNS, filters
from swiss_grounding.serving.models import Candidate, GroupHit

Key = tuple[str, str]
VERSIONS_SQL = (
    f"select {COLUMNS} from corpus.chunk c join corpus.document d on d.id = c.document_id "
    "where (c.translation_group_id, c.align_key) in "
    "(select * from unnest(%(groups)s::text[], %(aligns)s::text[])) and {validity}"
)


def aligned_versions(conn: psycopg.Connection, keys: Sequence[Key], as_of: date | None) -> dict[Key, tuple[Candidate, ...]]:
    if not keys:
        return {}
    sql = VERSIONS_SQL.format(validity=filters(as_of, ()))
    rows = conn.execute(sql, {"groups": [k[0] for k in keys], "aligns": [k[1] for k in keys],
                              "as_of": as_of}).fetchall()
    out: dict[Key, list[Candidate]] = {}
    for r in rows:
        c = Candidate(**{**r, "breadcrumb": tuple(r["breadcrumb"])})
        out.setdefault((c.translation_group_id, c.align_key), []).append(c)
    return {k: tuple(v) for k, v in out.items()}


def _representative(found: Sequence[Candidate], versions: Sequence[Candidate], question_lang: str | None) -> Candidate:
    best = found[0]
    by_lang = {c.language: c for c in found}
    if question_lang in by_lang:
        return by_lang[question_lang]
    wanted = next((v for v in versions if v.language == question_lang), None)
    if wanted is None:
        return best
    return replace(wanted, rrf=best.rrf, rrf_rank=best.rrf_rank)


def _diverges(a: Candidate, b: Candidate) -> bool:
    return a.valid_from is not None and b.valid_from is not None and a.valid_from != b.valid_from


def _corroboration(rep: Candidate, others: Sequence[Candidate],
                   found: Sequence[Candidate]) -> tuple[float | None, str | None, bool]:
    authentic = [v for v in others if v.is_authentic]
    if not authentic:
        return None, None, False
    diverge = any(_diverges(rep, v) for v in authentic)
    found_by_lang = {c.language: c for c in found}
    hits = [v for v in authentic if v.language in found_by_lang and not _diverges(rep, v)]
    share = len(hits) / len(authentic)
    if not hits:
        return share, None, diverge
    independent = all(v.language in found_by_lang[v.language].query_langs for v in hits)
    return share, "independent" if independent else "cross_lingual", diverge


def collapse(candidates: Sequence[Candidate], versions: Mapping[Key, Sequence[Candidate]],
             question_lang: str | None) -> list[GroupHit]:
    order: list[Key] = []
    by_key: dict[Key, list[Candidate]] = {}
    for c in candidates:
        key = (c.translation_group_id, c.align_key)
        if key not in by_key:
            order.append(key)
        by_key.setdefault(key, []).append(c)
    groups = []
    for key in order:
        found = by_key[key]
        all_versions = tuple(versions.get(key) or found)
        rep = _representative(found, all_versions, question_lang)
        others = tuple(v for v in all_versions if v.language != rep.language)
        share, basis, diverge = _corroboration(rep, others, found)
        groups.append(GroupHit(rep, others, share, basis, diverge))
    return groups
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_groups.py tests/integration/serving/test_aligned_versions.py -v`
Expected: 7 PASS

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/serving/groups.py tests/unit/serving/test_groups.py tests/integration/serving/test_aligned_versions.py
git commit -m "feat: score translation groups through their question-language version; corroboration share"
```

---

### Task 8: Reranker chosen by hardware

**Files:**
- Create: `src/swiss_grounding/serving/reranker.py`
- Test: `tests/unit/serving/test_reranker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_reranker.py
import os

import pytest

from swiss_grounding.serving.reranker import OverlapReranker, choose_model, passage_text

GPU, CPU = "BAAI/bge-reranker-v2-m3", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


@pytest.mark.parametrize(("setting", "device", "expected"), [
    ("auto", "mps", GPU), ("auto", "cuda", GPU), ("auto", "cpu", CPU), ("my/model", "cpu", "my/model"),
])
def test_choose_model(setting, device, expected):
    assert choose_model(setting, gpu_model=GPU, cpu_model=CPU, device=device) == expected


def test_overlap_reranker_prefers_shared_words_and_stays_in_zero_one():
    r = OverlapReranker()
    scores = r.score("Kündigungsfrist Wohnung", ["Die Kündigungsfrist für eine Wohnung", "Hundesteuer"])
    assert scores[0] > scores[1] and all(0.0 <= s <= 1.0 for s in scores)


def test_passage_text_puts_the_breadcrumb_first():
    assert passage_text(("SR 220 OR", "Art. 266c"), "Text") == "SR 220 OR › Art. 266c\nText"


@pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="downloads a reranker model")
def test_cross_encoder_separates_relevant_from_irrelevant():
    from swiss_grounding.serving.reranker import CrossEncoderReranker
    r = CrossEncoderReranker(CPU, device="cpu", max_tokens=512)
    good, bad = r.score("Kündigungsfrist Mietwohnung", [
        "Bei der Miete von Wohnungen können die Parteien mit einer Frist von drei Monaten kündigen.",
        "Hundehaltende müssen ihren Hund innert zehn Tagen anmelden."])
    assert good > 0.5 > bad
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_reranker.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/reranker.py
"""The cross-encoder that scores (question, passage) pairs (ADR 0012)."""
import re
from collections.abc import Sequence
from typing import Protocol

BREADCRUMB_SEPARATOR = " › "
TOKEN = re.compile(r"[\wà-ÿ]{3,}|\d+[a-z]?", re.IGNORECASE)


class Reranker(Protocol):
    name: str

    def score(self, question: str, passages: Sequence[str]) -> list[float]: ...


def detect_device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def choose_model(setting: str, *, gpu_model: str, cpu_model: str, device: str) -> str:
    if setting != "auto":
        return setting
    return cpu_model if device == "cpu" else gpu_model


def passage_text(breadcrumb: Sequence[str], text: str) -> str:
    crumb = BREADCRUMB_SEPARATOR.join(breadcrumb)
    return f"{crumb}\n{text}" if crumb else text


class CrossEncoderReranker:
    def __init__(self, model: str, *, device: str, max_tokens: int):
        import torch
        from sentence_transformers import CrossEncoder
        self.name = model
        self._activation = torch.nn.Sigmoid()
        self._model = CrossEncoder(model, device=device, max_length=max_tokens)
        if device != "cpu":
            self._model.model.half()

    def score(self, question: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        scores = self._model.predict([(question, p) for p in passages], batch_size=16,
                                     activation_fn=self._activation)
        return [float(s) for s in scores]


class OverlapReranker:
    """Deterministic stand-in for tests: share of question tokens found in the passage."""
    name = "overlap"

    def score(self, question: str, passages: Sequence[str]) -> list[float]:
        wanted = {t.lower() for t in TOKEN.findall(question)}
        if not wanted:
            return [0.0 for _ in passages]
        return [len(wanted & {t.lower() for t in TOKEN.findall(p)}) / len(wanted) for p in passages]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_reranker.py -v`
Expected: 6 PASS, 1 SKIPPED. Then once: `RUN_MODEL_TESTS=1 uv run --extra embed pytest tests/unit/serving/test_reranker.py -k cross_encoder -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/reranker.py tests/unit/serving/test_reranker.py
git commit -m "feat: cross-encoder reranker chosen by hardware (ADR 0012)"
```

---

### Task 9: Relevance: features, provisional threshold, fitted model

Until the golden set is labelled, the reranker score is the relevance and a provisional threshold decides abstention. After Task 22 writes `evals/relevance_model.json`, a logistic model over the features below replaces it, but only if it was fitted for the same reranker model.

**Files:**
- Create: `src/swiss_grounding/serving/relevance.py`
- Test: `tests/unit/serving/test_relevance.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_relevance.py
import json
from datetime import date

import pytest

from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.relevance import (
    FEATURES, PROVISIONAL_THRESHOLD, LogisticRelevance, ProvisionalRelevance, feature_vector, load_relevance,
)
from tests.unit.serving.test_groups import cand

TODAY = date(2026, 9, 24)


def test_feature_vector_has_one_value_per_feature():
    [g] = collapse([cand("de", 1), cand("fr", 2)], {("g", "a"): (cand("de"), cand("fr"))}, "de")
    x = feature_vector(g, rerank_score=0.9, question_lang="de", tier=0, today=TODAY)
    assert len(x) == len(FEATURES)
    named = dict(zip(FEATURES, x, strict=True))
    assert named["same_language"] == 1.0 and named["corroboration"] == 1.0 and named["tier"] == 0.0


def test_provisional_uses_the_reranker_score():
    model = ProvisionalRelevance(threshold=PROVISIONAL_THRESHOLD)
    assert model.probability((0.0,) * len(FEATURES), rerank_score=0.42) == 0.42


def test_logistic_model_applies_weights():
    model = LogisticRelevance(weights=(1.0,) + (0.0,) * (len(FEATURES) - 1), bias=0.0, threshold=0.5,
                              reranker="r")
    assert model.probability((0.0,) * len(FEATURES), rerank_score=0.3) == 0.5


def test_load_falls_back_to_provisional_when_file_missing(tmp_path):
    assert isinstance(load_relevance(tmp_path / "none.json", "r"), ProvisionalRelevance)


def test_load_ignores_a_model_fitted_for_another_reranker(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"reranker": "other", "features": list(FEATURES),
                                "weights": [0.0] * len(FEATURES), "bias": 0.0, "threshold": 0.4}))
    assert isinstance(load_relevance(path, "r"), ProvisionalRelevance)


def test_load_rejects_a_model_with_different_features(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"reranker": "r", "features": ["x"], "weights": [1.0], "bias": 0.0,
                                "threshold": 0.4}))
    with pytest.raises(ValueError, match="features"):
        load_relevance(path, "r")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_relevance.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/relevance.py
"""Relevance probability (ADR 0012): reranker score until fitted, then a logistic model."""
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from swiss_grounding.serving.models import GroupHit

FEATURES: tuple[str, ...] = (
    "rerank_logit", "same_language", "rrf_reciprocal", "corroboration", "corroboration_na",
    "independent", "tier", "tier_na", "is_law", "age_years",
)
# Set from the probes in docs/RESEARCH.md §H1 (irrelevant ≈ 0.00-0.02, relevant ≥ 0.8); Task 28 re-checks it.
PROVISIONAL_THRESHOLD = 0.10
EPS = 1e-6


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def feature_vector(g: GroupHit, *, rerank_score: float, question_lang: str | None, tier: int | None,
                   today: date) -> tuple[float, ...]:
    rep = g.representative
    seen = rep.modified_at or rep.fetched_at.date()
    return (
        _logit(rerank_score),
        1.0 if rep.language == question_lang else 0.0,
        1.0 / rep.rrf_rank if rep.rrf_rank else 0.0,
        g.corroboration or 0.0,
        1.0 if g.corroboration is None else 0.0,
        1.0 if g.corroboration_basis == "independent" else 0.0,
        float(tier) if tier is not None else 0.0,
        1.0 if tier is None else 0.0,
        1.0 if rep.authority.endswith("_law") else 0.0,
        max(0.0, (today - seen).days / 365.25),
    )


@dataclass(frozen=True)
class ProvisionalRelevance:
    threshold: float
    fitted: bool = False

    def probability(self, features: Sequence[float], *, rerank_score: float) -> float:
        return rerank_score


@dataclass(frozen=True)
class LogisticRelevance:
    weights: tuple[float, ...]
    bias: float
    threshold: float
    reranker: str
    fitted: bool = True

    def probability(self, features: Sequence[float], *, rerank_score: float) -> float:
        z = self.bias + sum(w * x for w, x in zip(self.weights, features, strict=True))
        return 1.0 / (1.0 + math.exp(-z))


Relevance = ProvisionalRelevance | LogisticRelevance


def load_relevance(path: Path | str, reranker: str) -> Relevance:
    path = Path(path)
    if not path.exists():
        return ProvisionalRelevance(PROVISIONAL_THRESHOLD)
    data = json.loads(path.read_text())
    if data.get("reranker") != reranker:
        return ProvisionalRelevance(PROVISIONAL_THRESHOLD)
    if tuple(data["features"]) != FEATURES:
        raise ValueError(f"{path}: features {data['features']} do not match {list(FEATURES)}; refit")
    return LogisticRelevance(tuple(float(w) for w in data["weights"]), float(data["bias"]),
                             float(data["threshold"]), reranker)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_relevance.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/relevance.py tests/unit/serving/test_relevance.py
git commit -m "feat: relevance features, provisional threshold and fitted logistic model"
```

---

### Task 10: Status decision per place (ADR 0013)

**Files:**
- Create: `src/swiss_grounding/serving/status.py`
- Test: `tests/unit/serving/test_status.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_status.py
from dataclasses import replace

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.models import ScoredGroup
from swiss_grounding.serving.places import PlaceOutcome
from swiss_grounding.serving.status import decide, pre_search
from tests.unit.serving.test_groups import cand

TREE = LocationTree.from_locations([
    Location("CH", None, Level.COUNTRY, None, None, {"de": "Schweiz"}),
    Location("CH-ZH", "CH", Level.CANTON, 1, None, {"de": "Zürich"}),
    Location("CH-ZH-261", "CH-ZH", Level.MUNICIPALITY, 261, None, {"de": "Zürich"}),
    Location("CH-BE", "CH", Level.CANTON, 2, None, {"de": "Bern"}),
    Location("CH-BE-351", "CH-BE", Level.MUNICIPALITY, 351, None, {"de": "Bern"}),
])


def scored(extent="CH", relevance=0.9, group="g"):
    [g] = collapse([replace(cand("de", group=group), extent_id=extent)], {}, "de")
    return ScoredGroup(g, relevance, relevance, 0)


def test_foreign_place_is_outside_scope_and_sends_the_client_elsewhere():
    r = pre_search(PlaceOutcome("foreign", "Konstanz, Deutschland"))
    assert r.status == "outside_scope" and "outside Switzerland" in r.message
    assert "other sources" in r.message


def test_unresolved_place_is_outside_scope_with_a_spelling_hint():
    r = pre_search(PlaceOutcome("unresolved", "Konstanz"))
    assert r.status == "outside_scope" and "spelling" in r.message


def test_ambiguous_place_asks_which_one():
    loc = TREE.get("CH-ZH-261")
    r = pre_search(PlaceOutcome("ambiguous", "Zürich", candidates=(loc, TREE.get("CH-ZH"))))
    assert r.status == "needs_location"


def test_resolved_place_goes_on_to_search():
    assert pre_search(PlaceOutcome("resolved", "Bern")) is None


def test_nothing_above_threshold_is_no_evidence():
    status, _ = decide(PlaceOutcome("none"), [scored(relevance=0.05)], threshold=0.1, tree=TREE)
    assert status == "no_evidence"


def test_no_place_and_answers_from_two_cities_asks_for_the_place():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-BE-351", group="b")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "needs_location"


def test_no_place_but_a_federal_answer_answers():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-BE-351", group="b"), scored("CH", group="c")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "results"


def test_answers_from_one_path_do_not_ask():
    groups = [scored("CH-ZH-261", group="a"), scored("CH-ZH", group="b")]
    status, _ = decide(PlaceOutcome("none"), groups, threshold=0.1, tree=TREE)
    assert status == "results"


def test_swiss_place_outside_scope_with_nothing_relevant_is_outside_scope():
    outcome = PlaceOutcome("resolved", "Basel", covered=("federal",))
    status, message = decide(outcome, [scored(relevance=0.01)], threshold=0.1, tree=TREE)
    assert status == "outside_scope" and "Basel" in message
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/serving/test_status.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/status.py
"""Which status a place gets, in the fixed order of ADR 0013."""
from collections.abc import Sequence

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import PlaceResult, ScoredGroup
from swiss_grounding.serving.places import PlaceOutcome

FOREIGN = ("{place!r} is outside Switzerland. This server covers Swiss public sources only; "
           "look for the answer in other sources for that country.")
UNRESOLVED = ("{place!r} is not a Swiss municipality this server recognises, so it is treated as outside "
              "Switzerland: look for the answer in other sources. If it is a Swiss place, check the spelling "
              "or give the postal code and search again.")
AMBIGUOUS = "{place!r} matches several Swiss places ({options}). Ask the user which one they mean."
NEEDS_PLACE = ("The answer depends on the place, and relevant rules differ between {options}. "
               "Ask the user for their municipality, then search again.")
NO_EVIDENCE = "No passage in the indexed sources answers this question{where}."
OUT_OF_SCOPE_PLACE = ("{place!r} is in Switzerland, but its {levels} rules are outside this server's declared "
                      "scope. Only federal information applies here.")
UNCOVERED_NOTE = "Federal evidence only: the {levels} rules of {place!r} are not covered by this server."


def _levels(covered: Sequence[str]) -> str:
    return " and ".join(level for level in ("cantonal", "municipal") if level not in covered)


def pre_search(outcome: PlaceOutcome) -> PlaceResult | None:
    """Steps 1 of ADR 0013 and the ambiguity rule: statuses decided before any search."""
    if outcome.kind == "foreign":
        return PlaceResult(outcome.text, "outside_scope", message=FOREIGN.format(place=outcome.text))
    if outcome.kind == "unresolved":
        return PlaceResult(outcome.text, "outside_scope", message=UNRESOLVED.format(place=outcome.text))
    if outcome.kind == "ambiguous":
        options = ", ".join(f"{c.label('de')} ({c.id})" for c in outcome.candidates)
        return PlaceResult(outcome.text, "needs_location",
                           message=AMBIGUOUS.format(place=outcome.text, options=options))
    return None


def _several_places(extents: Sequence[str], tree: LocationTree) -> bool:
    local = [e for e in set(extents) if e != "CH"]
    if len(local) < 2:
        return False
    deepest = max(local, key=lambda e: len(tree.path(e)))
    path = tree.path(deepest)
    return any(e not in path for e in local)


def decide(outcome: PlaceOutcome, scored: Sequence[ScoredGroup], *, threshold: float,
           tree: LocationTree) -> tuple[str, str]:
    """Steps 2, 3 and 5 of ADR 0013, after the search."""
    relevant = [s for s in scored if s.relevance >= threshold]
    uncovered = _levels(outcome.covered) if outcome.kind == "resolved" else ""
    if not relevant:
        if uncovered:
            return "outside_scope", OUT_OF_SCOPE_PLACE.format(place=outcome.text, levels=uncovered)
        where = f" for {outcome.text}" if outcome.text else ""
        return "no_evidence", NO_EVIDENCE.format(where=where)
    extents = [s.group.representative.extent_id for s in relevant]
    if outcome.kind == "none" and "CH" not in extents and _several_places(extents, tree):
        options = ", ".join(sorted({tree.get(e).label("de") for e in extents if e != "CH"}))
        return "needs_location", NEEDS_PLACE.format(options=options)
    if uncovered:
        return "results", UNCOVERED_NOTE.format(levels=uncovered, place=outcome.text)
    return "results", ""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_status.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/status.py tests/unit/serving/test_status.py
git commit -m "feat: per-place status in the order of ADR 0013"
```

---

### Task 11: Coverage and the supporting passage

**Files:**
- Create: `src/swiss_grounding/serving/coverage.py`
- Create: `src/swiss_grounding/serving/passages.py`
- Test: `tests/unit/serving/test_passages.py`, `tests/integration/serving/test_coverage.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/serving/test_passages.py
from swiss_grounding.serving.passages import MAX_PASSAGE_CHARS, best_passage


def test_short_text_is_returned_whole():
    assert best_passage("Drei Monate.", ["Frist"]) == "Drei Monate."


def test_picks_the_window_sharing_most_words_with_the_queries():
    text = " ".join([f"Satz {i} über etwas anderes." for i in range(40)]
                    + ["Die Kündigungsfrist beträgt drei Monate."]
                    + [f"Nachsatz {i} ohne Bezug." for i in range(40)])
    passage = best_passage(text, ["Wie lange ist die Kündigungsfrist?"])
    assert "Kündigungsfrist beträgt drei Monate" in passage
    assert len(passage) <= MAX_PASSAGE_CHARS


def test_numbers_count_as_words():
    text = "Absatz eins über Hunde. " * 30 + "Art. 336c gilt hier. " + "Absatz zwei über Katzen. " * 30
    assert "336c" in best_passage(text, ["336c"])
```

```python
# tests/integration/serving/test_coverage.py
import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.serving.coverage import coverage_rows
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def test_counts_current_documents_per_extent_on_the_path(corpus_db):
    with connect(corpus_db) as conn:
        add_doc(conn, group="a", lang="de", text="x")
        add_doc(conn, group="b", lang="de", text="y", extent="CH-ZH-261", source="zh")
        tree = load_location_tree(conn)
        rows = coverage_rows(conn, tree, ("CH", "CH-ZH", "CH-ZH-261"))
    assert [(r.extent_id, r.documents) for r in rows] == [("CH", 1), ("CH-ZH", 0), ("CH-ZH-261", 1)]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/serving/test_passages.py tests/integration/serving/test_coverage.py -v`
Expected: FAIL with `ModuleNotFoundError` (and `ImportError` for `load_location_tree`, added in Step 3)

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/passages.py
"""The passage inside a chunk that supports the answer (practice case citation_support)."""
import re
from collections.abc import Sequence

MAX_PASSAGE_CHARS = 600
SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")
TOKEN = re.compile(r"[\wà-ÿ]{4,}|\d+[a-z]?", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN.findall(text)}


def _windows(sentences: Sequence[str]) -> list[str]:
    out = []
    for start in range(len(sentences)):
        window = ""
        for s in sentences[start:]:
            candidate = f"{window} {s}".strip()
            if len(candidate) > MAX_PASSAGE_CHARS:
                break
            window = candidate
        out.append(window or sentences[start][:MAX_PASSAGE_CHARS])
    return out


def best_passage(text: str, queries: Sequence[str]) -> str:
    if len(text) <= MAX_PASSAGE_CHARS:
        return text
    wanted = set().union(*(_tokens(q) for q in queries)) if queries else set()
    sentences = [s.strip() for s in SENTENCE.split(text) if s.strip()]
    windows = _windows(sentences)
    return max(windows, key=lambda w: (len(wanted & _tokens(w)), -windows.index(w)))
```

```python
# src/swiss_grounding/serving/coverage.py
"""Documents per extent on a resolved path, from the corpus schema (the coverage signal, ADR 0001)."""
from collections.abc import Sequence

import psycopg

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.models import CoverageRow

SQL = ("select extent_id, count(*) as n from corpus.document where status = 'current' "
       "and extent_id = any(%s) group by extent_id")


def coverage_rows(conn: psycopg.Connection, tree: LocationTree, path: Sequence[str]) -> tuple[CoverageRow, ...]:
    counts = {r["extent_id"]: r["n"] for r in conn.execute(SQL, (list(path),)).fetchall()}
    return tuple(CoverageRow(e, tree.get(e).label("de"), counts.get(e, 0)) for e in path)
```

In `src/swiss_grounding/app.py`, add a helper used by tests and by Task 13:

```python
def load_location_tree(conn) -> LocationTree:
    tree = load_tree(conn)
    if not tree.by_id:
        raise RuntimeError("location table is empty; run `swiss-grounding db seed` first")
    return tree
```

(import `LocationTree` from `swiss_grounding.locations.tree`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_passages.py tests/integration/serving/test_coverage.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/passages.py src/swiss_grounding/serving/coverage.py src/swiss_grounding/app.py tests/unit/serving/test_passages.py tests/integration/serving/test_coverage.py
git commit -m "feat: coverage rows from the corpus and the supporting passage of a citation"
```

---

### Task 12: Serving schema and the call log (RAG review S6)

**Files:**
- Create: `src/swiss_grounding/serving/schema.sql`
- Create: `src/swiss_grounding/serving/db.py`
- Create: `src/swiss_grounding/serving/call_log.py`
- Test: `tests/integration/serving/test_call_log.py`
- Modify: `tests/integration/conftest.py` (add `serving_db` fixture)

- [ ] **Step 1: Write the schema**

```sql
-- src/swiss_grounding/serving/schema.sql
-- Serving-side tables. Idempotent: `serving init` and `setup` run it on every call.
create schema if not exists serving;

create table if not exists serving.call_log (
  id           bigserial primary key,
  tool         text not null,
  started_at   timestamptz not null default now(),
  duration_ms  integer not null,
  status       text not null,
  places       integer not null default 0,
  citations    integer not null default 0,
  reranker     text,
  error        text
);
create index if not exists call_log_tool_idx on serving.call_log (tool, started_at);

-- Last good value of a live lookup, returned with source_unavailable when the source is down.
create table if not exists serving.lookup_cache (
  key             text primary key,
  value           jsonb not null,
  reference_date  date,
  source_url      text not null,
  fetched_at      timestamptz not null default now()
);

create table if not exists serving.premium_region (
  year    integer not null,
  bfs_id  integer not null,
  canton  text not null,
  region  integer not null,
  primary key (year, bfs_id)
);

create table if not exists serving.premium (
  id            bigserial primary key,
  year          integer not null,
  insurer_id    text not null,
  insurer_name  text not null,
  canton        text not null,
  region        integer not null,
  age_class     text not null check (age_class in ('child','young_adult','adult')),
  accident      boolean not null,
  model         text not null check (model in ('standard','family_doctor','hmo','telmed','other')),
  model_label   text not null,
  deductible    integer not null,
  premium_chf   numeric(8,2) not null,
  source_url    text not null
);
create index if not exists premium_lookup_idx
  on serving.premium (year, canton, region, age_class, accident, deductible);
```

```python
# src/swiss_grounding/serving/db.py
from importlib.resources import files

from swiss_grounding.db.connection import connect


def serving_schema_sql() -> str:
    return files("swiss_grounding.serving").joinpath("schema.sql").read_text()


def apply_serving_schema(database_url: str) -> None:
    with connect(database_url) as conn:
        conn.execute(serving_schema_sql())
```

Add to `tests/integration/conftest.py`:

```python
SERVING_TABLES = "serving.call_log, serving.lookup_cache, serving.premium_region, serving.premium"


@pytest.fixture
def serving_db(corpus_db) -> str:
    """corpus_db plus an empty serving schema."""
    from swiss_grounding.db.connection import connect
    from swiss_grounding.serving.db import apply_serving_schema
    apply_serving_schema(corpus_db)
    with connect(corpus_db) as conn:
        conn.execute(f"truncate {SERVING_TABLES} restart identity")
    return corpus_db
```

- [ ] **Step 2: Write the failing test**

```python
# tests/integration/serving/test_call_log.py
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.call_log import CallRecord, latency_summary, record_call

pytestmark = pytest.mark.integration


def test_records_calls_and_summarises_latency(serving_db):
    for ms in (100, 200, 300, 400):
        record_call(serving_db, CallRecord(tool="swiss_search", duration_ms=ms, status="results", places=1,
                                           citations=3, reranker="r"))
    record_call(serving_db, CallRecord(tool="swiss_search", duration_ms=50, status="no_evidence"))
    with connect(serving_db) as conn:
        [row] = latency_summary(conn)
    assert row["tool"] == "swiss_search" and row["calls"] == 5
    assert row["p50_ms"] == 200 and row["abstain_rate"] == 0.2


def test_logging_failure_never_raises():
    record_call("postgresql://nobody@127.0.0.1:1/none", CallRecord(tool="t", duration_ms=1, status="results"))
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/integration/serving/test_call_log.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

```python
# src/swiss_grounding/serving/call_log.py
"""Latency and outcome per tool call. Logging must never break a tool call."""
import logging
from dataclasses import dataclass

import psycopg

from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)
ABSTAIN = ("no_evidence", "outside_scope", "needs_location", "source_unavailable")
SUMMARY_SQL = """
select tool, count(*) as calls,
       percentile_disc(0.5) within group (order by duration_ms) as p50_ms,
       percentile_disc(0.95) within group (order by duration_ms) as p95_ms,
       avg(case when status = any(%s) then 1.0 else 0.0 end)::float as abstain_rate,
       avg(case when status = 'results' and citations = 0 then 1.0 else 0.0 end)::float as empty_rate
from serving.call_log group by tool order by tool
"""


@dataclass(frozen=True)
class CallRecord:
    tool: str
    duration_ms: int
    status: str
    places: int = 0
    citations: int = 0
    reranker: str | None = None
    error: str | None = None


def record_call(database_url: str, record: CallRecord) -> None:
    try:
        with connect(database_url) as conn:
            conn.execute(
                "insert into serving.call_log (tool, duration_ms, status, places, citations, reranker, error) "
                "values (%s,%s,%s,%s,%s,%s,%s)",
                (record.tool, record.duration_ms, record.status, record.places, record.citations,
                 record.reranker, record.error))
    except psycopg.Error as exc:
        log.warning("call log write failed for %s: %s", record.tool, exc)


def latency_summary(conn: psycopg.Connection) -> list[dict]:
    return conn.execute(SUMMARY_SQL, (list(ABSTAIN),)).fetchall()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/serving/test_call_log.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/serving/schema.sql src/swiss_grounding/serving/db.py src/swiss_grounding/serving/call_log.py tests/integration/conftest.py tests/integration/serving/test_call_log.py
git commit -m "feat: serving schema and per-call latency log"
```

---

### Task 13: The search service

Wires Tasks 2–12 together. One `SearchService.search` call handles every place in the request.

**Files:**
- Create: `src/swiss_grounding/serving/search_service.py`
- Test: `tests/integration/serving/test_search_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/serving/test_search_service.py
from datetime import date

import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.serving.models import SearchRequest
from swiss_grounding.serving.relevance import ProvisionalRelevance
from swiss_grounding.serving.reranker import OverlapReranker
from swiss_grounding.serving.search_service import SearchService, query_embedder
from tests.integration.serving.corpus_fixture import EMB, add_doc

pytestmark = pytest.mark.integration


class TreeResolver:
    """Resolves exact names from the tree only; no GeoAdmin calls in tests."""
    def __init__(self, tree):
        self.tree = tree

    def resolve(self, text):
        everything = self.tree.find(text)
        found = [f for f in everything if f.level.value == "municipality"] or list(everything)
        if len(found) != 1:
            return None
        return ResolvedLocation(found[0], self.tree.path(found[0].id), "alias", text)


def service(url, threshold=0.3):
    with connect(url) as conn:
        tree = load_location_tree(conn)
    return SearchService(database_url=url, tree=tree, resolver=TreeResolver(tree), embed=query_embedder(EMB),
                         reranker=OverlapReranker(), relevance=ProvisionalRelevance(threshold), index="bge-m3",
                         rerank_candidates=30, local_quota=10, ef_search=100, today=lambda: date(2026, 9, 24))


def test_national_question_without_a_place_answers_from_federal_law(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c",
                breadcrumb=("SR 220 OR", "Art. 266c"))
        add_doc(conn, group="or", lang="fr", text="délai de congé habitation trois mois", align="art_266_c")
    resp = service(serving_db).search(SearchRequest(question="Kündigungsfrist Wohnung?"))
    assert resp.status == "results"
    [place] = resp.places
    assert place.citations[0].language == "de" and place.citations[0].other_languages == ("fr",)
    assert place.citations[0].corroboration is not None


def test_foreign_place_needs_no_search(serving_db):
    resp = service(serving_db).search(SearchRequest(question="Rundfunkbeitrag?", locations=("Konstanz",)))
    assert resp.status == "outside_scope" and "Covered:" in resp.scope


def test_local_question_without_a_place_asks_for_it(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="zh", lang="de", text="Karton Abfuhr Termine", extent="CH-ZH-261", source="zh")
        add_doc(conn, group="be", lang="de", text="Karton Abfuhr Termine Bern", extent="CH-BE-351", source="be")
    resp = service(serving_db).search(SearchRequest(question="Wann ist die Karton Abfuhr?"))
    assert resp.status == "needs_location"


def test_two_places_are_answered_separately(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="zh", lang="de", text="Anmeldung Einwohner Zürich", extent="CH-ZH-261", source="zh")
        add_doc(conn, group="be", lang="de", text="Anmeldung Einwohner Bern", extent="CH-BE-351", source="be")
    resp = service(serving_db).search(SearchRequest(question="Anmeldung Einwohner?",
                                                    locations=("Zürich", "Bern")))
    zh, be = resp.places
    assert {c.extent_id for c in zh.citations} == {"CH-ZH-261"}
    assert {c.extent_id for c in be.citations} == {"CH-BE-351"}


def test_nothing_relevant_is_no_evidence_with_the_scope_statement(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="x", lang="de", text="Hundesteuer")
    resp = service(serving_db).search(SearchRequest(question="Wetter morgen?"))
    assert resp.status == "no_evidence" and "weather" in resp.scope
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/integration/serving/test_search_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/search_service.py
"""swiss_search: places → candidates → groups → reranker → relevance → status → citations."""
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.serving.candidates import ArmQuery, gather_candidates
from swiss_grounding.serving.coverage import coverage_rows
from swiss_grounding.serving.groups import aligned_versions, collapse
from swiss_grounding.serving.language import detect_language
from swiss_grounding.serving.models import (
    Citation, GroupHit, PlaceResult, ScoredGroup, SearchRequest, SearchResponse, overall_status,
)
from swiss_grounding.serving.passages import best_passage
from swiss_grounding.serving.places import PlaceOutcome, Resolver, place_outcomes
from swiss_grounding.serving.relevance import Relevance, feature_vector
from swiss_grounding.serving.reranker import Reranker, passage_text
from swiss_grounding.serving.scope import scope_statement
from swiss_grounding.serving.status import decide, pre_search

Embedded = tuple[np.ndarray, dict[int, float] | None]
EmbedFn = Callable[[Sequence[str]], list[Embedded]]
EMPTY_QUESTION = "The question is empty. Send the user's question as they wrote it."


def query_embedder(provider) -> EmbedFn:
    """bge-m3 gives dense + sparse; any other provider gives dense only."""
    if hasattr(provider, "embed_with_sparse"):
        return provider.embed_with_sparse
    return lambda texts: [(v, None) for v in provider.embed(texts)]


@dataclass(frozen=True)
class _Query:
    request: SearchRequest
    lang: str | None
    vec: np.ndarray
    sparse: dict[int, float] | None
    translation_vecs: dict[str, np.ndarray]


@dataclass(frozen=True)
class SearchService:
    database_url: str
    tree: LocationTree
    resolver: Resolver
    embed: EmbedFn
    reranker: Reranker
    relevance: Relevance
    index: str
    rerank_candidates: int
    local_quota: int
    ef_search: int
    today: Callable[[], date] = date.today

    def search(self, request: SearchRequest) -> SearchResponse:
        if not request.question.strip():
            return SearchResponse("invalid_request", (), message=EMPTY_QUESTION, field="question")
        outcomes = place_outcomes(request.question, request.locations, self.resolver, self.tree)
        decided = [pre_search(o) for o in outcomes]
        query = self._embed(request) if any(d is None for d in decided) else None
        places = tuple(d if d is not None else self._place(o, query) for o, d in zip(outcomes, decided, strict=True))
        status = overall_status([p.status for p in places])
        needs_scope = any(p.status in ("no_evidence", "outside_scope") for p in places)
        return SearchResponse(status, places, scope=scope_statement() if needs_scope else "")

    def _embed(self, request: SearchRequest) -> _Query:
        langs = list(request.translations)
        embedded = self.embed([request.question, *(request.translations[lang] for lang in langs)])
        vec, sparse = embedded[0]
        tvecs = {lang: embedded[i + 1][0] for i, lang in enumerate(langs)}
        return _Query(request, detect_language(request.question), vec, sparse, tvecs)

    def _scope_path(self, o: PlaceOutcome) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if o.kind != "resolved" or o.resolved is None:
            return (), ()
        full = o.resolved.path
        path = full if "municipal" in o.covered else full[: len(o.covered)]
        return path, path[1:]

    def _place(self, o: PlaceOutcome, q: _Query) -> PlaceResult:
        path, local = self._scope_path(o)
        arm = ArmQuery(q.request.question, q.lang, q.vec, q.sparse, q.request.translations, q.translation_vecs,
                       path, local, q.request.as_of, self.rerank_candidates, self.rerank_candidates,
                       self.local_quota if local else 0)
        with connect(self.database_url) as conn:
            cands = gather_candidates(conn, arm, index=self.index, ef_search=self.ef_search)
            keys = list(dict.fromkeys((c.translation_group_id, c.align_key) for c in cands))
            versions = aligned_versions(conn, keys, q.request.as_of)
            coverage = coverage_rows(conn, self.tree, path) if path else ()
        scored = self._score(collapse(cands, versions, q.lang), q, path)
        status, message = decide(o, scored, threshold=self.relevance.threshold, tree=self.tree)
        citations = ()
        if status == "results":
            queries = [q.request.question, *q.request.translations.values()]
            keep = [s for s in scored if s.relevance >= self.relevance.threshold][: q.request.limit]
            citations = tuple(self._cite(s, queries) for s in keep)
        loc = o.resolved.location if o.resolved else None
        uncovered = tuple(lv for lv in ("cantonal", "municipal") if o.kind == "resolved" and lv not in o.covered)
        return PlaceResult(o.text, status, loc.id if loc else None, loc.label("de") if loc else None,
                           message, citations, coverage, uncovered)

    def _tier(self, extent: str, path: Sequence[str]) -> int | None:
        return len(path) - 1 - path.index(extent) if extent in path else None

    def _score(self, groups: list[GroupHit], q: _Query, path: Sequence[str]) -> list[ScoredGroup]:
        reps = [g.representative for g in groups]
        scores = self.reranker.score(q.request.question, [passage_text(r.breadcrumb, r.text) for r in reps])
        today = q.request.as_of or self.today()
        out = []
        for g, score in zip(groups, scores, strict=True):
            tier = self._tier(g.representative.extent_id, path)
            x = feature_vector(g, rerank_score=score, question_lang=q.lang, tier=tier, today=today)
            out.append(ScoredGroup(g, score, self.relevance.probability(x, rerank_score=score), tier))
        return sorted(out, key=lambda s: -s.relevance)

    def _cite(self, s: ScoredGroup, queries: Sequence[str]) -> Citation:
        g, rep = s.group, s.group.representative
        return Citation(
            chunk_id=rep.chunk_id, document_id=rep.document_id, title=rep.title, url=rep.url, anchor=rep.anchor,
            breadcrumb=rep.breadcrumb, passage=best_passage(rep.text, queries), language=rep.language,
            other_languages=tuple(sorted({o.language for o in g.others})), publisher=rep.publisher,
            authority=rep.authority, extent_id=rep.extent_id, extent_label=self.tree.get(rep.extent_id).label("de"),
            tier=s.tier, relevance=round(s.relevance, 4), corroboration=g.corroboration,
            corroboration_basis=g.corroboration_basis, versions_diverge=g.versions_diverge,
            valid_from=rep.valid_from, modified_at=rep.modified_at, fetched_at=rep.fetched_at,
            extraction=rep.extraction)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/serving/test_search_service.py -v`
Expected: 5 PASS. With `FakeEmbeddings` and `OverlapReranker`, relevance is word overlap; if `test_local_question_without_a_place_asks_for_it` returns `results` because one city scores below 0.3, lower the test's threshold rather than changing `decide`.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/search_service.py tests/integration/serving/test_search_service.py
git commit -m "feat: search service over places, groups, reranker and relevance"
```

---

### Task 14: `swiss_get_document` by id, reference or language; small-to-big

A law hit is often one paragraph of a long article. The document tool returns the whole article around it: every chunk of the document with the same `anchor` (Fedlex article eId, e.g. `art_336_c`; paragraphs are `art_336_c/para_1`). It also accepts an official reference ("Art. 336c OR", "SR 220 Art. 336c") or an official URL, and a `language` to switch to another version of the same translation group.

**Files:**
- Create: `src/swiss_grounding/serving/documents.py`
- Test: `tests/unit/serving/test_references.py`, `tests/integration/serving/test_documents.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/serving/test_references.py
import pytest

from swiss_grounding.serving.documents import Reference, parse_reference


@pytest.mark.parametrize(("text", "expected"), [
    ("Art. 336c OR", Reference(sr="220", article="art_336_c")),
    ("art. 266c CO", Reference(sr="220", article="art_266_c")),
    ("SR 741.51 Art. 44", Reference(sr="741.51", article="art_44")),
    ("Artikel 12bis AIG", Reference(sr="142.20", article="art_12_bis")),
    ("https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de#art_336_c",
     Reference(url="https://www.fedlex.admin.ch/eli/cc/27/317_321_377/de", article="art_336_c")),
    ("SR 220", Reference(sr="220")),
])
def test_parses_references(text, expected):
    assert parse_reference(text) == expected


def test_unknown_abbreviation_is_none():
    assert parse_reference("Art. 5 XYZ") is None
```

```python
# tests/integration/serving/test_documents.py
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.serving.documents import get_document
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration


def _law(conn, lang, url):
    doc, c1 = add_doc(conn, group="or", lang=lang, text=f"Abs 1 {lang}", align="art_336_c/para_1", url=url)
    conn.execute("update corpus.document set identifier = 'SR 220' where id = %s", (doc,))
    conn.execute("update corpus.chunk set anchor = 'art_336_c' where id = %s", (c1,))
    c2 = conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
        "text, extent_id, authority, status, chunk_hash, anchor) values (%s,%s,'or','art_336_c/para_2',1,"
        "'{Art. 336c}',%s,'CH','federal_law','current','c2','art_336_c') returning id",
        (doc, lang, f"Abs 2 {lang}")).fetchone()["id"]
    return doc, c1, c2


def test_chunk_id_returns_the_whole_article(corpus_db):
    with connect(corpus_db) as conn:
        doc, c1, _ = _law(conn, "de", "https://fedlex/or/de")
        out = get_document(conn, document_id=doc, chunk_id=c1)
    assert [c["text"] for c in out["chunks"]] == ["Abs 1 de", "Abs 2 de"]


def test_reference_finds_the_article_in_the_requested_language(corpus_db):
    with connect(corpus_db) as conn:
        _law(conn, "de", "https://fedlex/or/de")
        _law(conn, "fr", "https://fedlex/or/fr")
        out = get_document(conn, reference="Art. 336c OR", language="fr")
    assert out["document"]["language"] == "fr"
    assert [c["text"] for c in out["chunks"]] == ["Abs 1 fr", "Abs 2 fr"]
    assert out["available_languages"] == ["de", "fr"]


def test_language_switch_maps_the_chunk_by_align_key(corpus_db):
    with connect(corpus_db) as conn:
        doc, c1, _ = _law(conn, "de", "https://fedlex/or/de")
        _law(conn, "fr", "https://fedlex/or/fr")
        out = get_document(conn, document_id=doc, chunk_id=c1, language="fr")
    assert out["document"]["language"] == "fr" and out["chunks"][0]["text"] == "Abs 1 fr"


def test_unknown_reference_is_an_error_not_an_exception(corpus_db):
    with connect(corpus_db) as conn:
        out = get_document(conn, reference="Art. 999 OR")
    assert "error" in out
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/serving/test_references.py tests/integration/serving/test_documents.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/serving/documents.py
"""swiss_get_document: whole articles around a hit, by id, official reference, or URL; any language version."""
import re
from dataclasses import dataclass

import psycopg

# Abbreviations of the acts in the declared scope (DE / FR / IT), to their SR number.
ACTS: dict[str, str] = {
    "BV": "101", "CST": "101", "COST": "101",
    "ZGB": "210", "CC": "210",
    "OR": "220", "CO": "220",
    "STGB": "311.0", "CP": "311.0",
    "AIG": "142.20", "LEI": "142.20", "LSTRI": "142.20",
    "SVG": "741.01", "LCR": "741.01", "LCSTR": "741.01",
    "VZV": "741.51", "OAC": "741.51", "OAC-TI": "741.51",
    "MWSTG": "641.20", "LTVA": "641.20", "LIVA": "641.20",
    "AHVG": "831.10", "LAVS": "831.10",
    "KVG": "832.10", "LAMAL": "832.10",
    "AVIG": "837.0", "LACI": "837.0", "LADI": "837.0",
}
ARTICLE = re.compile(r"\b(?:art\.?|artikel|article|articolo)\s*(\d+)\s*([a-z]{0,9})\b", re.IGNORECASE)
SR = re.compile(r"\bSR\s*(\d{1,3}(?:\.\d+)*)", re.IGNORECASE)
URL = re.compile(r"^(https?://\S+?)(?:#(\S+))?$")
WORD = re.compile(r"\b([A-Za-z]{2,6})\b")
MAX_CHUNKS = 120
DOC_COLUMNS = ("id, source_id, url, language, translation_group_id, title, identifier, publisher, authority, "
               "extent_id, is_authentic, valid_from, valid_to, status, modified_at, fetched_at, extraction")
CHUNK_COLUMNS = "id as chunk_id, align_key, ordinal, breadcrumb, anchor, text"


@dataclass(frozen=True)
class Reference:
    sr: str | None = None
    article: str | None = None
    url: str | None = None


def _article_eid(number: str, suffix: str) -> str:
    return f"art_{number}_{suffix.lower()}" if suffix else f"art_{number}"


def parse_reference(text: str) -> Reference | None:
    text = text.strip()
    if m := URL.match(text):
        return Reference(url=m.group(1), article=m.group(2))
    art = ARTICLE.search(text)
    article = _article_eid(art.group(1), art.group(2)) if art else None
    if m := SR.search(text):
        return Reference(sr=m.group(1), article=article)
    rest = ARTICLE.sub(" ", text)
    act = next((ACTS[w.upper()] for w in WORD.findall(rest) if w.upper() in ACTS), None)
    return Reference(sr=act, article=article) if act else None


def _find_by_reference(conn, ref: Reference, language: str | None) -> dict | None:
    lang = language or "de"
    if ref.url:
        return conn.execute(f"select {DOC_COLUMNS} from corpus.document where url = %s and status = 'current'",
                            (ref.url,)).fetchone()
    return conn.execute(f"select {DOC_COLUMNS} from corpus.document where identifier = %s and language = %s "
                        "and status = 'current'", (f"SR {ref.sr}", lang)).fetchone()


def _switch_language(conn, doc: dict, language: str) -> dict | None:
    return conn.execute(f"select {DOC_COLUMNS} from corpus.document where translation_group_id = %s "
                        "and language = %s and status = 'current'",
                        (doc["translation_group_id"], language)).fetchone()


def _chunks(conn, doc_id: int, anchor: str | None, align_key: str | None) -> list[dict]:
    if anchor:
        sql = f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and anchor = %s order by ordinal"
        return conn.execute(sql, (doc_id, anchor)).fetchall()
    if align_key:
        sql = f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and align_key = %s order by ordinal"
        return conn.execute(sql, (doc_id, align_key)).fetchall()
    sql = (f"select {CHUNK_COLUMNS} from corpus.chunk where document_id = %s and status <> 'boilerplate' "
           f"order by ordinal limit {MAX_CHUNKS + 1}")
    return conn.execute(sql, (doc_id,)).fetchall()


def get_document(conn: psycopg.Connection, *, document_id: int | None = None, chunk_id: int | None = None,
                 reference: str | None = None, language: str | None = None) -> dict:
    anchor = align_key = None
    if reference:
        ref = parse_reference(reference)
        if ref is None:
            return {"error": f"could not read the reference {reference!r}; use e.g. 'Art. 336c OR' or an official URL"}
        doc = _find_by_reference(conn, ref, language)
        anchor = ref.article
    elif document_id is not None:
        doc = conn.execute(f"select {DOC_COLUMNS} from corpus.document where id = %s", (document_id,)).fetchone()
        if doc and chunk_id is not None:
            chunk = conn.execute("select anchor, align_key from corpus.chunk where id = %s and document_id = %s",
                                 (chunk_id, document_id)).fetchone()
            if chunk is None:
                return {"error": f"chunk {chunk_id} is not part of document {document_id}"}
            anchor, align_key = chunk["anchor"], chunk["align_key"]
    else:
        return {"error": "give document_id, or reference"}
    if doc is None:
        return {"error": f"no current document for {reference or document_id!r}"}
    if language and doc["language"] != language:
        switched = _switch_language(conn, doc, language)
        if switched is None:
            return {"error": f"no {language} version of this document"}
        doc = switched
    chunks = _chunks(conn, doc["id"], anchor, None if anchor else align_key)
    if (anchor or align_key) and not chunks:
        return {"error": f"{anchor or align_key} not found in document {doc['id']}"}
    langs = conn.execute("select distinct language from corpus.document where translation_group_id = %s "
                         "and status = 'current' order by language", (doc["translation_group_id"],)).fetchall()
    return {"document": doc, "chunks": chunks[:MAX_CHUNKS], "truncated": len(chunks) > MAX_CHUNKS,
            "available_languages": [r["language"] for r in langs]}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/serving/test_references.py tests/integration/serving/test_documents.py -v`
Expected: 11 PASS. Check one real Fedlex eId after encoding (`select distinct anchor from corpus.chunk where anchor like 'art_336%'`): if suffixed articles are spelled differently (e.g. `art_336c`), change `_article_eid` and the test cases together.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/serving/documents.py tests/unit/serving/test_references.py tests/integration/serving/test_documents.py
git commit -m "feat: get_document by reference and language, returning whole articles"
```

---

### Task 15: Zürich waste calendar as corpus documents (ADR 0014)

The old OpenERZ calendar lives in the public tables, which the new server no longer reads. We import it into the corpus: one German document per Zürich postal code, one chunk per waste type listing its upcoming dates. It is indexed and cited like any other page. Its reference date is `fetched_at`, and the answer picks the first date after today.

**Files:**
- Create: `src/swiss_grounding/corpus/calendar.py`
- Test: `tests/unit/corpus/test_calendar.py`, `tests/integration/serving/test_calendar_persist.py`

- [ ] **Step 1: Write the failing unit test**

```python
# tests/unit/corpus/test_calendar.py
from datetime import date

from swiss_grounding.corpus.calendar import OPENERZ_SOURCE, calendar_document

EVENTS = [
    {"date": "2026-09-17", "waste_type": "cardboard", "zip": 8003},
    {"date": "2026-10-01", "waste_type": "cardboard", "zip": 8003},
    {"date": "2026-09-16", "waste_type": "organic", "zip": 8003},
    {"date": "2026-08-01", "waste_type": "paper", "zip": 8003},
]


def test_one_document_per_zip_one_section_per_waste_type_future_dates_only():
    doc = calendar_document(8003, EVENTS, today=date(2026, 9, 10))
    assert doc.source_id == OPENERZ_SOURCE.id and doc.language == "de"
    assert doc.work_key == "openerz-8003"
    keys = [s.align_key for s in doc.sections]
    assert keys == ["cardboard", "organic"]
    cardboard = doc.sections[0]
    assert "Karton" in cardboard.text and "17.09.2026" in cardboard.text and "01.10.2026" in cardboard.text
    assert cardboard.breadcrumb == ("Abfuhrkalender Stadt Zürich", "PLZ 8003", "Karton")


def test_no_future_events_gives_no_document():
    assert calendar_document(8003, EVENTS, today=date(2027, 1, 1)) is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/corpus/test_calendar.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/corpus/calendar.py
"""OpenERZ (Stadt Zürich waste collection) as corpus documents: one per postal code."""
from collections.abc import Sequence
from datetime import UTC, date, datetime

import httpx

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec

OPENERZ_URL = "https://openerz.metaodi.ch/api/calendar"
ZURICH_ZIPS: tuple[int, ...] = (8001, 8002, 8003, 8004, 8005, 8006, 8008, 8032, 8037, 8038, 8041, 8044, 8045,
                                8046, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8055, 8057, 8064)
WASTE_DE: dict[str, str] = {
    "cardboard": "Karton", "paper": "Papier", "organic": "Grüngut", "textile": "Textilien",
    "special": "Sonderabfall (Mobil)", "cargotram": "Cargo-Tram", "etram": "E-Tram", "waste": "Kehricht",
    "incombustibles": "Unbrennbares", "metal": "Metall", "bulky_goods": "Sperrgut", "chipping_service": "Häckseldienst",
}
OPENERZ_SOURCE = SourceSpec(
    id="open_erz", name="Abfuhrkalender Stadt Zürich (OpenERZ)", publisher="Entsorgung + Recycling Zürich",
    authority="official_info", level="municipal", extent_id="CH-ZH-261", connector="html", tier=1,
    languages=("de",), config={"kind": "openerz"}, retrieved_via="openerz.metaodi.ch")
MAX_DATES = 26


def _format(d: str) -> str:
    return date.fromisoformat(d).strftime("%d.%m.%Y")


def calendar_document(zip_code: int, events: Sequence[dict], today: date) -> ParsedDocument | None:
    by_type: dict[str, list[str]] = {}
    for e in sorted(events, key=lambda e: e["date"]):
        if date.fromisoformat(e["date"]) >= today:
            by_type.setdefault(e["waste_type"], []).append(e["date"])
    if not by_type:
        return None
    sections = []
    for waste, dates in by_type.items():
        label = WASTE_DE.get(waste, waste)
        text = (f"{label}-Abfuhr in Zürich, Postleitzahl {zip_code}. Nächste Termine: "
                f"{', '.join(_format(d) for d in dates[:MAX_DATES])}. Am Abfuhrtag bis 7 Uhr bereitstellen.")
        sections.append(ParsedSection(align_key=waste, breadcrumb=("Abfuhrkalender Stadt Zürich", f"PLZ {zip_code}",
                                                                   label), anchor=waste, text=text))
    return ParsedDocument(source_id=OPENERZ_SOURCE.id, url=f"{OPENERZ_URL}?region=zurich&zip={zip_code}",
                          language="de", work_key=f"openerz-{zip_code}",
                          title=f"Abfuhrkalender Stadt Zürich, PLZ {zip_code}", sections=tuple(sections),
                          modified_at=today)


def fetch_events(client: httpx.Client, zip_code: int, start: date) -> list[dict]:
    params = {"region": "zurich", "zip": zip_code, "start": start.isoformat(), "sort": "date", "limit": 500}
    response = client.get(OPENERZ_URL, params=params)
    response.raise_for_status()
    return response.json()["result"]


def now() -> datetime:
    return datetime.now(UTC)
```

- [ ] **Step 4: Write the failing integration test**

```python
# tests/integration/serving/test_calendar_persist.py
from datetime import UTC, date, datetime

import pytest

from swiss_grounding.corpus.calendar import OPENERZ_SOURCE, calendar_document
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def test_calendar_document_persists_as_municipal_chunks(corpus_db):
    doc = calendar_document(8003, [{"date": "2026-09-17", "waste_type": "cardboard", "zip": 8003}],
                            today=date(2026, 9, 10))
    with connect(corpus_db) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        assert persist_document(conn, doc, OPENERZ_SOURCE, datetime(2026, 9, 10, tzinfo=UTC)) == "added"
        row = conn.execute("select extent_id, text from corpus.chunk").fetchone()
    assert row["extent_id"] == "CH-ZH-261" and "17.09.2026" in row["text"]
```

Run: `uv run pytest tests/unit/corpus/test_calendar.py tests/integration/serving/test_calendar_persist.py -v`
Expected: 3 PASS

- [ ] **Step 5: Add the CLI command**

In `src/swiss_grounding/cli/serving_commands.py` (created here; Tasks 16, 19 and 26 add to it):

```python
"""`serving`, `lookups`, `dump` and `setup` commands."""
from datetime import date

import httpx
import typer

from swiss_grounding.config import load_settings
from swiss_grounding.corpus.calendar import (
    OPENERZ_SOURCE, ZURICH_ZIPS, calendar_document, fetch_events, now,
)
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect

serving_app = typer.Typer(help="Serving: schema, calendars, latency stats.")


@serving_app.command("calendar")
def calendar_cmd() -> None:
    """Import the Zürich waste calendar (OpenERZ) as corpus documents. Run `corpus embed` afterwards."""
    settings = load_settings()
    today = date.today()
    with httpx.Client(timeout=settings.fetch_timeout_seconds,
                      headers={"user-agent": settings.corpus_user_agent}) as client, \
            connect(settings.database_url) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        for zip_code in ZURICH_ZIPS:
            doc = calendar_document(zip_code, fetch_events(client, zip_code, today), today)
            if doc is not None:
                typer.echo(f"{zip_code}: {persist_document(conn, doc, OPENERZ_SOURCE, now())}")
```

Register it in `src/swiss_grounding/cli/main.py` next to the other `add_typer` calls:

```python
from swiss_grounding.cli.serving_commands import serving_app
app.add_typer(serving_app, name="serving")
```

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/calendar.py src/swiss_grounding/cli/serving_commands.py src/swiss_grounding/cli/main.py tests/unit/corpus/test_calendar.py tests/integration/serving/test_calendar_persist.py
git commit -m "feat: Zürich waste calendar as corpus documents"
```

---

### Task 16: `swiss_premium` from the BAG premium table

**Files:**
- Create: `src/swiss_grounding/lookups/__init__.py` (empty)
- Create: `src/swiss_grounding/lookups/premium_data.py`
- Create: `src/swiss_grounding/lookups/premium.py`
- Create: `tests/fixtures/premium/premiums_sample.csv`, `tests/fixtures/premium/regions_sample.csv`
- Test: `tests/unit/lookups/test_premium_data.py`, `tests/integration/serving/test_premium.py`

- [ ] **Step 1: Look at the real files before writing the parser**

Download the current premium dataset and the premium-region list from https://opendata.swiss/de/dataset/health-insurance-premiums and https://www.bag.admin.ch/de/krankenversicherung-praemienregionen into `data/premium/` (gitignored). Print the header and three rows of each:

```bash
mkdir -p data/premium && ls data/premium
uv run python -c "import csv,sys; r=csv.reader(open(sys.argv[1], encoding='utf-8-sig'), delimiter=';'); [print(next(r)) for _ in range(4)]" data/premium/<premium file>.csv
```

The parser below expects these column names and codes, which is how BAG has published the file in recent years: `Versicherer`, `Kanton`, `Region` (`PR-REG CH0`…`CH3`), `Altersklasse` (`AKL-KIN`, `AKL-JUG`, `AKL-ERW`), `Unfalleinschluss` (`MIT-UNF`, `OHN-UNF`), `Geschäftsjahr`, `Tariftyp` (`TAR-BASE`, `TAR-HAM`, `TAR-HMO`, `TAR-DIV`), `Tarifbezeichnung`, `Franchise` (`FRA-2500`), `Prämie`. The region list: `Kanton`, `BFS-Nr.`, `Region`. **If the real headers or codes differ, change `COLUMNS`, the code maps and both fixtures together**, then continue. If the region list is only published as XLSX, save it as CSV (`;`-separated, UTF-8) with LibreOffice or `uv run --with openpyxl python -c ...` and commit the conversion command to the runbook, not the data.

- [ ] **Step 2: Write the fixtures**

`tests/fixtures/premium/premiums_sample.csv`:

```
Versicherer;Kanton;Region;Altersklasse;Unfalleinschluss;Geschäftsjahr;Tariftyp;Tarifbezeichnung;Franchise;Prämie
1509;TI;PR-REG CH1;AKL-ERW;MIT-UNF;2026;TAR-BASE;Base;FRA-2500;401.20
1509;TI;PR-REG CH1;AKL-ERW;OHN-UNF;2026;TAR-HMO;HMO Ticino;FRA-2500;330.55
0032;TI;PR-REG CH1;AKL-ERW;OHN-UNF;2026;TAR-HAM;Hausarzt;FRA-2500;345.00
0032;TI;PR-REG CH1;AKL-ERW;OHN-UNF;2026;TAR-BASE;Base;FRA-300;520.00
0032;TI;PR-REG CH2;AKL-ERW;OHN-UNF;2026;TAR-BASE;Base;FRA-2500;300.00
```

`tests/fixtures/premium/regions_sample.csv`:

```
Kanton;BFS-Nr.;Gemeinde;Region
TI;5192;Lugano;1
TI;5002;Bellinzona;2
```

- [ ] **Step 3: Write the failing unit test**

```python
# tests/unit/lookups/test_premium_data.py
from pathlib import Path

from swiss_grounding.lookups.premium_data import age_class, read_premiums, read_regions

FIX = Path("tests/fixtures/premium")


def test_reads_premium_rows_with_normalised_codes():
    rows = list(read_premiums(FIX / "premiums_sample.csv", insurer_names={"1509": "Kasse A"}))
    first = rows[0]
    assert (first.year, first.canton, first.region, first.age_class, first.accident, first.model,
            first.deductible, first.premium_chf) == (2026, "TI", 1, "adult", True, "standard", 2500, 401.20)
    assert first.insurer_name == "Kasse A" and rows[2].insurer_name == "0032"
    assert rows[1].model == "hmo" and rows[2].model == "family_doctor"


def test_reads_regions():
    assert {(r.bfs_id, r.region) for r in read_regions(FIX / "regions_sample.csv", year=2026)} == {(5192, 1), (5002, 2)}


def test_age_class_boundaries():
    assert [age_class(a) for a in (0, 18, 19, 25, 26, 30)] == ["child", "child", "young_adult", "young_adult",
                                                               "adult", "adult"]
```

- [ ] **Step 4: Run it to verify it fails, then implement**

Run: `uv run pytest tests/unit/lookups/test_premium_data.py -v` → FAIL (`ModuleNotFoundError`).

```python
# src/swiss_grounding/lookups/premium_data.py
"""Read the BAG premium table and premium regions; load them into serving.premium*."""
import csv
from collections.abc import Iterator, Mapping
from dataclasses import astuple, dataclass
from pathlib import Path

import psycopg

SOURCE_URL = "https://opendata.swiss/de/dataset/health-insurance-premiums"
COLUMNS = {"insurer": "Versicherer", "canton": "Kanton", "region": "Region", "age": "Altersklasse",
           "accident": "Unfalleinschluss", "year": "Geschäftsjahr", "model": "Tariftyp",
           "label": "Tarifbezeichnung", "deductible": "Franchise", "premium": "Prämie"}
AGE = {"AKL-KIN": "child", "AKL-JUG": "young_adult", "AKL-ERW": "adult"}
MODEL = {"TAR-BASE": "standard", "TAR-HAM": "family_doctor", "TAR-HMO": "hmo", "TAR-DIV": "other"}
CHILD_MAX_AGE = 18
YOUNG_ADULT_MAX_AGE = 25


@dataclass(frozen=True)
class PremiumRow:
    year: int
    insurer_id: str
    insurer_name: str
    canton: str
    region: int
    age_class: str
    accident: bool
    model: str
    model_label: str
    deductible: int
    premium_chf: float
    source_url: str = SOURCE_URL


@dataclass(frozen=True)
class RegionRow:
    year: int
    bfs_id: int
    canton: str
    region: int


def age_class(age: int) -> str:
    if age <= CHILD_MAX_AGE:
        return "child"
    return "young_adult" if age <= YOUNG_ADULT_MAX_AGE else "adult"


def _rows(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


def _model(code: str, label: str) -> str:
    model = MODEL.get(code, "other")
    return "telmed" if model == "other" and "tel" in label.lower() else model


def read_premiums(path: Path, insurer_names: Mapping[str, str]) -> Iterator[PremiumRow]:
    c = COLUMNS
    for r in _rows(path):
        insurer = r[c["insurer"]].strip()
        yield PremiumRow(
            year=int(r[c["year"]]), insurer_id=insurer, insurer_name=insurer_names.get(insurer, insurer),
            canton=r[c["canton"]].strip(), region=int(r[c["region"]].rsplit("CH", 1)[1]),
            age_class=AGE[r[c["age"]].strip()], accident=r[c["accident"]].strip() == "MIT-UNF",
            model=_model(r[c["model"]].strip(), r[c["label"]]), model_label=r[c["label"]].strip(),
            deductible=int(r[c["deductible"]].removeprefix("FRA-")), premium_chf=float(r[c["premium"]]))


def read_regions(path: Path, year: int) -> Iterator[RegionRow]:
    for r in _rows(path):
        yield RegionRow(year, int(r["BFS-Nr."]), r["Kanton"].strip(), int(r["Region"]))


def load_premiums(conn: psycopg.Connection, premiums: Path, regions: Path, year: int,
                  insurer_names: Mapping[str, str]) -> tuple[int, int]:
    conn.execute("delete from serving.premium where year = %s", (year,))
    conn.execute("delete from serving.premium_region where year = %s", (year,))
    prem = [astuple(p) for p in read_premiums(premiums, insurer_names) if p.year == year]
    regs = [astuple(r) for r in read_regions(regions, year)]
    with conn.cursor() as cur:
        cur.executemany("insert into serving.premium (year, insurer_id, insurer_name, canton, region, age_class, "
                        "accident, model, model_label, deductible, premium_chf, source_url) "
                        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", prem)
        cur.executemany("insert into serving.premium_region (year, bfs_id, canton, region) values (%s,%s,%s,%s)",
                        regs)
    return len(prem), len(regs)
```

Run: `uv run pytest tests/unit/lookups/test_premium_data.py -v` → 3 PASS.

- [ ] **Step 5: Write the failing integration test for the lookup**

```python
# tests/integration/serving/test_premium.py
from pathlib import Path

import pytest

from swiss_grounding.app import load_location_tree
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium import cheapest_premiums
from swiss_grounding.lookups.premium_data import load_premiums

pytestmark = pytest.mark.integration
FIX = Path("tests/fixtures/premium")


def test_cheapest_premiums_for_lugano_adult_2500(serving_db):
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI-5192", age=30, deductible=2500, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "results" and out["premium_region"] == 1
    assert [o["premium_chf"] for o in out["premiums"]] == [330.55, 345.00]


def test_invalid_deductible_is_explained(serving_db):
    with connect(serving_db) as conn:
        load_premiums(conn, FIX / "premiums_sample.csv", FIX / "regions_sample.csv", 2026, {})
        tree = load_location_tree(conn)
        out = cheapest_premiums(conn, tree, location_id="CH-TI-5192", age=30, deductible=750, accident=False,
                                model="any", year=2026, limit=5)
    assert out["status"] == "invalid_request" and "2500" in out["message"]
```

- [ ] **Step 6: Implement the lookup**

```python
# src/swiss_grounding/lookups/premium.py
"""swiss_premium: cheapest basic-insurance premiums for a municipality, age and deductible."""
import psycopg

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.lookups.premium_data import SOURCE_URL, age_class

DEDUCTIBLES = {"child": (0, 100, 200, 300, 400, 500, 600),
               "young_adult": (300, 500, 1000, 1500, 2000, 2500),
               "adult": (300, 500, 1000, 1500, 2000, 2500)}
MODELS = ("any", "standard", "family_doctor", "hmo", "telmed", "other")
SQL = ("select p.insurer_name, p.model, p.model_label, p.premium_chf from serving.premium p "
       "where p.year = %(year)s and p.canton = %(canton)s and p.region = %(region)s and p.age_class = %(age)s "
       "and p.accident = %(accident)s and p.deductible = %(deductible)s "
       "and (%(model)s = 'any' or p.model = %(model)s) order by p.premium_chf limit %(limit)s")


def _bad(message: str) -> dict:
    return {"status": "invalid_request", "message": message}


def cheapest_premiums(conn: psycopg.Connection, tree: LocationTree, *, location_id: str, age: int,
                      deductible: int, accident: bool, model: str, year: int, limit: int) -> dict:
    klass = age_class(age)
    if deductible not in DEDUCTIBLES[klass]:
        return _bad(f"A {klass.replace('_', ' ')} can choose a deductible of {DEDUCTIBLES[klass]} CHF.")
    if model not in MODELS:
        return _bad(f"model must be one of {MODELS}.")
    loc = tree.get(location_id)
    if loc.bfs_id is None:
        return _bad("Give a municipality (not a canton or district): premiums depend on the premium region.")
    region = conn.execute("select canton, region from serving.premium_region where year = %s and bfs_id = %s",
                          (year, loc.bfs_id)).fetchone()
    if region is None:
        return {"status": "no_evidence", "message": f"No {year} premium region is loaded for {loc.label('de')}."}
    rows = conn.execute(SQL, {"year": year, "canton": region["canton"], "region": region["region"], "age": klass,
                              "accident": accident, "deductible": deductible, "model": model,
                              "limit": limit}).fetchall()
    return {"status": "results" if rows else "no_evidence", "municipality": loc.label("de"),
            "canton": region["canton"], "premium_region": region["region"], "year": year, "age_class": klass,
            "deductible": deductible, "accident_included": accident,
            "premiums": [{**r, "premium_chf": float(r["premium_chf"])} for r in rows],
            "unit": "CHF per month", "source_url": SOURCE_URL}
```

Run: `uv run pytest tests/integration/serving/test_premium.py -v` → 2 PASS.

- [ ] **Step 7: Add the load command**

Append to `src/swiss_grounding/cli/serving_commands.py`:

```python
from pathlib import Path

from swiss_grounding.lookups.premium_data import load_premiums

lookups_app = typer.Typer(help="Lookup data: premiums.")


@lookups_app.command("load-premiums")
def load_premiums_cmd(premiums: Path, regions: Path, year: int,
                      insurers: Path | None = typer.Option(None, help="CSV 'id;name' of insurers")) -> None:
    names = {}
    if insurers:
        names = dict(line.strip().split(";", 1) for line in insurers.read_text(encoding="utf-8-sig").splitlines()
                     if ";" in line)
    with connect(load_settings().database_url) as conn:
        n_prem, n_reg = load_premiums(conn, premiums, regions, year, names)
    typer.echo(f"loaded {n_prem} premiums and {n_reg} municipalities for {year}")
```

Register in `main.py`: `app.add_typer(lookups_app, name="lookups")`.

- [ ] **Step 8: Commit**

```bash
git add src/swiss_grounding/lookups tests/fixtures/premium tests/unit/lookups tests/integration/serving/test_premium.py src/swiss_grounding/cli
git commit -m "feat: swiss_premium lookup over the BAG premium table"
```

---

### Task 17: `swiss_connections`

**Files:**
- Create: `src/swiss_grounding/lookups/connections.py`
- Test: `tests/unit/lookups/test_connections.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/lookups/test_connections.py
import httpx

from swiss_grounding.lookups.connections import find_connections

REPLY = {"connections": [{
    "from": {"station": {"name": "Zürich HB"}, "departure": "2026-09-24T10:02:00+0200", "platform": "7"},
    "to": {"station": {"name": "Bern"}, "arrival": "2026-09-24T10:58:00+0200", "platform": "5"},
    "duration": "00d00:56:00", "transfers": 0, "products": ["IC 1"]}]}


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://transport.opendata.ch/v1")


def test_returns_trimmed_connections_with_the_source():
    def handler(request):
        assert request.url.params["from"] == "Zürich HB" and request.url.params["limit"] == "4"
        return httpx.Response(200, json=REPLY)
    out = find_connections(client(handler), origin="Zürich HB", destination="Bern", date=None, time=None, limit=4)
    assert out["status"] == "results"
    assert out["connections"][0] == {"departure": "2026-09-24T10:02:00+0200", "arrival": "2026-09-24T10:58:00+0200",
                                     "from": "Zürich HB", "to": "Bern", "platform": "7", "duration": "00d00:56:00",
                                     "transfers": 0, "products": ["IC 1"]}
    assert out["source_url"].startswith("https://transport.opendata.ch")


def test_timeout_is_source_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("slow")
    out = find_connections(client(handler), origin="A", destination="B", date=None, time=None, limit=4)
    assert out["status"] == "source_unavailable" and "timetable service" in out["message"]


def test_no_connection_is_no_evidence():
    out = find_connections(client(lambda r: httpx.Response(200, json={"connections": []})),
                           origin="A", destination="B", date=None, time=None, limit=4)
    assert out["status"] == "no_evidence"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/lookups/test_connections.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/swiss_grounding/lookups/connections.py
"""swiss_connections: public transport connections from transport.opendata.ch (keyless, live)."""
from datetime import UTC, datetime

import httpx

SOURCE_URL = "https://transport.opendata.ch"
UNAVAILABLE = ("The Swiss timetable service could not be reached ({reason}). No connection data is shown; "
               "try again later or check sbb.ch.")
MAX_LIMIT = 6


def _trim(c: dict) -> dict:
    return {"departure": c["from"]["departure"], "arrival": c["to"]["arrival"],
            "from": c["from"]["station"]["name"], "to": c["to"]["station"]["name"],
            "platform": c["from"].get("platform"), "duration": c.get("duration"),
            "transfers": c.get("transfers"), "products": c.get("products", [])}


def find_connections(client: httpx.Client, *, origin: str, destination: str, date: str | None, time: str | None,
                     limit: int) -> dict:
    params = {"from": origin, "to": destination, "limit": max(1, min(limit, MAX_LIMIT))}
    params |= {k: v for k, v in (("date", date), ("time", time)) if v}
    try:
        response = client.get("/connections", params=params)
        response.raise_for_status()
        found = response.json().get("connections", [])
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "source_unavailable", "message": UNAVAILABLE.format(reason=type(exc).__name__),
                "source_url": SOURCE_URL}
    status = "results" if found else "no_evidence"
    return {"status": status, "connections": [_trim(c) for c in found], "source_url": SOURCE_URL,
            "retrieved_at": datetime.now(UTC).isoformat()}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/lookups/test_connections.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/lookups/connections.py tests/unit/lookups/test_connections.py
git commit -m "feat: swiss_connections lookup with source_unavailable on failure"
```

---

### Task 18: `swiss_reference_rate` with the last good value

**Files:**
- Create: `src/swiss_grounding/lookups/reference_rate.py`
- Create: `tests/fixtures/bwo_referenzzinssatz.html`
- Test: `tests/unit/lookups/test_reference_rate.py`, `tests/integration/serving/test_reference_rate.py`

- [ ] **Step 1: Save the real page as the fixture**

```bash
curl -sL -A "Mozilla/5.0 (compatible; swiss-grounding/0.2)" "https://www.bwo.admin.ch/de/referenzzinssatz" -o tests/fixtures/bwo_referenzzinssatz.html
grep -o -i "referenzzinssatz[^<]\{0,200\}" tests/fixtures/bwo_referenzzinssatz.html | head
```

If the URL redirects or 404s, find the current page from https://www.bwo.admin.ch (search "Referenzzinssatz"), update `Settings.reference_rate_url` (Task 0) and re-save. Read the snippet: note how the rate (e.g. `1,25 %`) and the publication date appear. The parser below assumes the sentence shape "Der Referenzzinssatz beträgt X,XX %" and a date written "1. September 2026" or "01.09.2026" in the same block; adjust `RATE`/`DATE` to the real page if needed and keep the unit test asserting the values you read.

- [ ] **Step 2: Write the failing unit test**

```python
# tests/unit/lookups/test_reference_rate.py
from datetime import date

from swiss_grounding.lookups.reference_rate import parse_rate

HTML = """<html><body><h1>Referenzzinssatz</h1>
<p>Der hypothekarische Referenzzinssatz beträgt 1,25 % und gilt seit dem 2. September 2025.</p>
<p>Nächste Publikation: 1. Dezember 2025</p></body></html>"""


def test_parses_rate_and_effective_date():
    assert parse_rate(HTML) == (1.25, date(2025, 9, 2))


def test_returns_none_when_the_page_changed_shape():
    assert parse_rate("<html>Wartung</html>") is None


def test_real_page_fixture_parses():
    from pathlib import Path
    parsed = parse_rate(Path("tests/fixtures/bwo_referenzzinssatz.html").read_text(encoding="utf-8"))
    assert parsed is not None and 0 < parsed[0] < 10
```

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/lookups/reference_rate.py
"""swiss_reference_rate: the mortgage reference interest rate from BWO, with its effective date."""
import json
import re
from datetime import date

import httpx
import psycopg
from bs4 import BeautifulSoup

CACHE_KEY = "reference_rate"
RATE = re.compile(r"Referenzzinssatz[^%]{0,80}?(\d+[.,]\d{1,2})\s*%", re.IGNORECASE)
MONTHS = {m: i for i, m in enumerate(["januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
                                      "september", "oktober", "november", "dezember"], start=1)}
DATE_WORDS = re.compile(r"(\d{1,2})\.\s*(" + "|".join(MONTHS) + r")\s+(\d{4})", re.IGNORECASE)
DATE_DOTS = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
UNAVAILABLE = "The BWO page could not be reached ({reason}); showing the last value retrieved on {when}."
UNAVAILABLE_NO_CACHE = "The BWO page could not be reached ({reason}) and no earlier value is stored."


def _first_date(text: str) -> date | None:
    if m := DATE_WORDS.search(text):
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    if m := DATE_DOTS.search(text):
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def parse_rate(html: str) -> tuple[float, date | None] | None:
    text = " ".join(BeautifulSoup(html, "html.parser").get_text(" ").split())
    m = RATE.search(text)
    if m is None:
        return None
    return float(m.group(1).replace(",", ".")), _first_date(text[m.end(): m.end() + 200])


def _cached(conn) -> dict | None:
    return conn.execute("select value, reference_date, source_url, fetched_at from serving.lookup_cache "
                        "where key = %s", (CACHE_KEY,)).fetchone()


def reference_rate(conn: psycopg.Connection, client: httpx.Client, url: str) -> dict:
    try:
        response = client.get(url)
        response.raise_for_status()
        parsed = parse_rate(response.text)
        if parsed is None:
            raise ValueError("page no longer states the rate")
    except (httpx.HTTPError, ValueError) as exc:
        reason = type(exc).__name__ if isinstance(exc, httpx.HTTPError) else str(exc)
        row = _cached(conn)
        if row is None:
            return {"status": "source_unavailable", "message": UNAVAILABLE_NO_CACHE.format(reason=reason),
                    "source_url": url}
        return {"status": "source_unavailable", **row["value"], "effective_date": row["reference_date"],
                "source_url": row["source_url"], "retrieved_at": row["fetched_at"],
                "message": UNAVAILABLE.format(reason=reason, when=row["fetched_at"].date().isoformat())}
    rate, effective = parsed
    conn.execute("insert into serving.lookup_cache (key, value, reference_date, source_url, fetched_at) "
                 "values (%s, %s, %s, %s, now()) on conflict (key) do update set value = excluded.value, "
                 "reference_date = excluded.reference_date, source_url = excluded.source_url, fetched_at = now()",
                 (CACHE_KEY, json.dumps({"rate_percent": rate}), effective, url))
    return {"status": "results", "rate_percent": rate, "effective_date": effective, "source_url": url,
            "publisher": "Bundesamt für Wohnungswesen BWO"}
```

- [ ] **Step 4: Write the integration test for the fallback**

```python
# tests/integration/serving/test_reference_rate.py
import httpx
import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.reference_rate import reference_rate
from tests.unit.lookups.test_reference_rate import HTML

pytestmark = pytest.mark.integration
URL = "https://www.bwo.admin.ch/de/referenzzinssatz"


def test_live_value_is_cached_and_returned_when_the_source_is_down(serving_db):
    up = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=HTML)))
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with connect(serving_db) as conn:
        assert reference_rate(conn, up, URL)["rate_percent"] == 1.25
        out = reference_rate(conn, down, URL)
    assert out["status"] == "source_unavailable" and out["rate_percent"] == 1.25
    assert "last value" in out["message"]


def test_down_without_cache(serving_db):
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with connect(serving_db) as conn:
        out = reference_rate(conn, down, URL)
    assert out["status"] == "source_unavailable" and "rate_percent" not in out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/lookups/test_reference_rate.py tests/integration/serving/test_reference_rate.py -v`
Expected: 5 PASS

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/lookups/reference_rate.py tests/fixtures/bwo_referenzzinssatz.html tests/unit/lookups/test_reference_rate.py tests/integration/serving/test_reference_rate.py
git commit -m "feat: swiss_reference_rate with the last good value when BWO is down"
```

---

### Task 19: The six-tool MCP server (ADR 0015)

Replace the server with six read-only tools. Each call is timed into `serving.call_log`. The old tools (`swiss_resolve_location`, `swiss_coverage`, `swiss_list_categories`, `swiss_suggest_source`) and the old `question_en`/`topic_en`/`topics`/`categories` parameters are removed. The legacy `retrieval` package and the `query` CLI command stay in the repository for the old probes until the golden set replaces them; nothing in the server imports them any more.

**Files:**
- Modify: `src/swiss_grounding/app.py` (add `build_search_service`, `build_reranker`, `build_query_provider`)
- Rewrite: `src/swiss_grounding/mcp_server/server.py`
- Rewrite: `tests/integration/test_mcp_server.py`
- Modify: `tests/integration/conftest.py` (`FAKE_BACKENDS` gains `"RERANKER_MODEL": "overlap"`)

- [ ] **Step 1: Wire the service in `app.py`**

Add to `src/swiss_grounding/app.py`:

```python
from swiss_grounding.corpus.providers import FakeEmbeddings, LocalBgeM3, OpenAIEmbeddings
from swiss_grounding.serving.relevance import load_relevance
from swiss_grounding.serving.reranker import (
    CrossEncoderReranker, OverlapReranker, Reranker, choose_model, detect_device,
)
from swiss_grounding.serving.search_service import SearchService, query_embedder

FAKE_QUERY_DIM = 1024  # the corpus tables are vector(1024) even in tests


def build_query_provider(settings: Settings):
    if settings.embedding_backend == "fake":
        return FakeEmbeddings(FAKE_QUERY_DIM)
    if settings.serving_index == "openai-3l":
        return OpenAIEmbeddings(settings.openai_api_key)
    return LocalBgeM3()


def build_reranker(settings: Settings) -> Reranker:
    if settings.reranker_model == "overlap":
        return OverlapReranker()
    device = detect_device()
    model = choose_model(settings.reranker_model, gpu_model=settings.reranker_gpu_model,
                         cpu_model=settings.reranker_cpu_model, device=device)
    return CrossEncoderReranker(model, device=device, max_tokens=settings.reranker_max_tokens)


def build_search_service(settings: Settings, today: Callable[[], date] = date.today) -> SearchService:
    with connect(settings.database_url) as conn:
        tree = load_location_tree(conn)
    geo = GeoAdminClient.from_settings(settings.geoadmin_base_url, settings.geoadmin_timeout_seconds)
    reranker = build_reranker(settings)
    return SearchService(
        database_url=settings.database_url, tree=tree, resolver=LocationResolver(tree, geo),
        embed=query_embedder(build_query_provider(settings)), reranker=reranker,
        relevance=load_relevance(settings.relevance_model_path, reranker.name), index=settings.serving_index,
        rerank_candidates=settings.rerank_candidates, local_quota=settings.local_candidate_quota,
        ef_search=settings.hnsw_ef_search, today=today)
```

- [ ] **Step 2: Write the failing server test**

Replace `tests/integration/test_mcp_server.py` with:

```python
import json
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium_data import load_premiums
from swiss_grounding.mcp_server.server import build_server
from tests.integration.serving.corpus_fixture import add_doc

pytestmark = pytest.mark.integration
TOOLS = {"swiss_search", "swiss_get_document", "swiss_scope", "swiss_premium", "swiss_connections",
         "swiss_reference_rate"}


@pytest.fixture
def server(serving_db):
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate", align="art_266_c")
        load_premiums(conn, Path("tests/fixtures/premium/premiums_sample.csv"),
                      Path("tests/fixtures/premium/regions_sample.csv"), 2026, {})
    return build_server(Settings(database_url=serving_db, embedding_backend="fake", reranker_model="overlap",
                                 _env_file=None))


async def call(server, name, args):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args)
        return json.loads(result.content[0].text)


async def test_exactly_six_read_only_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS and len(tools) == 6
    assert all(t.annotations.readOnlyHint for t in tools)


async def test_search_returns_places_and_is_logged(server, serving_db):
    out = await call(server, "swiss_search", {"question": "Kündigungsfrist Wohnung?"})
    assert out["status"] == "results" and out["places"][0]["citations"]
    assert "notice" in out
    with connect(serving_db) as conn:
        assert conn.execute("select count(*) as n from serving.call_log where tool = 'swiss_search'"
                            ).fetchone()["n"] == 1


async def test_search_with_a_foreign_place(server):
    out = await call(server, "swiss_search", {"question": "Rundfunkbeitrag?", "locations": ["Konstanz, Deutschland"]})
    assert out["status"] == "outside_scope" and "Covered:" in out["scope"]


async def test_scope_tool(server):
    out = await call(server, "swiss_scope", {})
    assert "Scuol" in out["scope"] and "commercial register" in out["scope"]


async def test_premium_tool_resolves_the_municipality(server):
    out = await call(server, "swiss_premium", {"municipality": "Lugano", "age": 30, "deductible": 2500,
                                               "year": 2026})
    assert out["status"] == "results" and out["premiums"][0]["premium_chf"] == 330.55


async def test_premium_tool_outside_switzerland(server):
    out = await call(server, "swiss_premium", {"municipality": "Konstanz, Deutschland", "age": 30,
                                               "deductible": 2500})
    assert out["status"] == "outside_scope"
```

Add `"RERANKER_MODEL": "overlap"` to `FAKE_BACKENDS` in `tests/integration/conftest.py`.

Run: `uv run pytest tests/integration/test_mcp_server.py -v`
Expected: FAIL (old tool names)

- [ ] **Step 3: Rewrite the server**

```python
# src/swiss_grounding/mcp_server/server.py
"""The MCP server: six read-only tools (ADR 0015)."""
import json
from dataclasses import asdict
from datetime import date, datetime
from time import perf_counter
from typing import Annotated, Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from swiss_grounding.app import build_search_service
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.connections import find_connections
from swiss_grounding.lookups.premium import cheapest_premiums
from swiss_grounding.lookups.reference_rate import reference_rate
from swiss_grounding.serving.call_log import CallRecord, record_call
from swiss_grounding.serving.documents import get_document
from swiss_grounding.serving.models import MAX_LIMIT, NOTICE, SearchRequest
from swiss_grounding.serving.places import place_outcomes
from swiss_grounding.serving.scope import scope_statement
from swiss_grounding.serving.status import pre_search

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
LIVE = ToolAnnotations(readOnlyHint=True, idempotentHint=False, openWorldHint=True)
INSTRUCTIONS = (
    "Swiss public information: federal law and federal offices, six cantons, seven cities, and three lookups. "
    "Search in the user's own language; pass every place the user names in `locations`. Cite the URLs you are "
    "given and never invent one. When a tool says a question is outside scope, tell the user it is not covered. "
    + scope_statement()
)


def _encode(value: Any) -> str:
    return value.isoformat() if isinstance(value, (date, datetime)) else str(value)


def _json(obj: dict) -> str:
    return json.dumps({**obj, "notice": NOTICE}, default=_encode, ensure_ascii=False)


def build_server(settings: Settings) -> FastMCP:
    service = build_search_service(settings)
    mcp = FastMCP("swiss-grounding", instructions=INSTRUCTIONS)

    def timed(tool: str, fn, reranker: str | None = None) -> str:
        started = perf_counter()
        try:
            out = fn()
        except Exception as exc:
            record_call(settings.database_url, CallRecord(tool, int((perf_counter() - started) * 1000),
                                                          "error", error=type(exc).__name__))
            raise
        places = out.get("places", [])
        record_call(settings.database_url, CallRecord(
            tool, int((perf_counter() - started) * 1000), out.get("status", "results"), places=len(places),
            citations=sum(len(p.get("citations", [])) for p in places), reranker=reranker))
        return _json(out)

    @mcp.tool(annotations=READ_ONLY)
    def swiss_search(
        question: str,
        locations: Annotated[list[str] | None, Field(max_length=3)] = None,
        translations: dict[Literal["de", "fr", "it", "en"], str] | None = None,
        as_of: str | None = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = 8,
    ) -> str:
        """Find passages in official Swiss sources that answer a question, for up to three places.

        question: the user's question exactly as they wrote it, in any language (German, French,
        Italian, Romansh, English). Every language store is searched with it; do not translate first.
        locations: every place the user names, one entry each (max 3), e.g. ["Lausanne", "Bern"].
        Add the country when the user names one ("Konstanz, Deutschland"). Leave empty when the user
        names no place: national questions are answered without one, and the server asks for a place
        only when the answer differs between places. Results come back grouped per place, never merged.
        translations: optional, the same question in other languages ({"fr": "...", "it": "..."});
        improves keyword matching in those stores. Never required.
        as_of: optional ISO date for the rules in force on that day (default: today).

        status per place and overall: results (cite the passages), needs_location (ask the user for
        their municipality), outside_scope (say it is not covered; for a place outside Switzerland,
        suggest other sources), no_evidence (say the indexed sources hold no answer; `scope` says what
        is covered). Each citation has a supporting `passage`, its `url`, `publisher`, `extent_label`,
        `tier` (0 = the asked place, rising toward federal), `relevance` (0-1), and dates
        (`valid_from`, `modified_at`, `fetched_at`). `uncovered_levels` lists cantonal or municipal rules
        of a place that this server does not cover: say so. Not covered at all: computed amounts (tax
        bills, pensions), the commercial register, statistics, geodata, weather."""
        try:
            parsed = date.fromisoformat(as_of) if as_of else None
            request = SearchRequest(question, tuple(locations or ()), dict(translations or {}), parsed, limit)
        except ValueError as exc:
            return _json({"status": "invalid_request", "message": str(exc)})
        return timed("swiss_search", lambda: asdict(service.search(request)), service.reranker.name)

    @mcp.tool(annotations=READ_ONLY)
    def swiss_get_document(document_id: int | None = None, chunk_id: int | None = None,
                           reference: str | None = None, language: Literal["de", "fr", "it", "en", "rm"] | None = None
                           ) -> str:
        """Read the whole article or section around a search hit, or look one up by official reference.

        Give document_id (and chunk_id) from a swiss_search citation, or a reference such as
        "Art. 336c OR", "SR 741.51 Art. 44" or an official URL. language switches to another language
        version of the same text (available_languages lists them). Federal law is authentic in de, fr, it;
        en is for information only."""
        def run() -> dict:
            with connect(settings.database_url) as conn:
                out = get_document(conn, document_id=document_id, chunk_id=chunk_id, reference=reference,
                                   language=language)
            return {"status": "invalid_request" if "error" in out else "results", **out}
        return timed("swiss_get_document", run)

    @mcp.tool(annotations=READ_ONLY)
    def swiss_scope() -> str:
        """What this server covers and what it does not. Quote it when telling a user a question is not covered."""
        return timed("swiss_scope", lambda: {"status": "results", "scope": scope_statement()})

    def _municipality(text: str) -> tuple[str | None, dict | None]:
        [outcome] = place_outcomes("", (text,), service.resolver, service.tree)
        refused = pre_search(outcome)
        if refused is not None:
            return None, {"status": refused.status, "message": refused.message}
        return outcome.resolved.location.id, None

    @mcp.tool(annotations=READ_ONLY)
    def swiss_premium(municipality: str, age: Annotated[int, Field(ge=0, le=120)], deductible: int,
                      accident: bool = False,
                      model: Literal["any", "standard", "family_doctor", "hmo", "telmed"] = "any",
                      year: int | None = None, limit: Annotated[int, Field(ge=1, le=20)] = 5) -> str:
        """Cheapest monthly basic health-insurance premiums (BAG data) for a Swiss municipality, age and deductible.

        accident: include accident cover (false for employees covered at work). model: insurance model.
        year: premium year (default: the latest loaded). Returns insurer, model, CHF per month, premium region."""
        def run() -> dict:
            location_id, refused = _municipality(municipality)
            if refused:
                return refused
            with connect(settings.database_url) as conn:
                latest = year or conn.execute("select max(year) as y from serving.premium").fetchone()["y"]
                if latest is None:
                    return {"status": "source_unavailable", "message": "No premium data is loaded."}
                return cheapest_premiums(conn, service.tree, location_id=location_id, age=age,
                                         deductible=deductible, accident=accident, model=model, year=latest,
                                         limit=limit)
        return timed("swiss_premium", run)

    @mcp.tool(annotations=LIVE)
    def swiss_connections(origin: str, destination: str, date: str | None = None, time: str | None = None,
                          limit: Annotated[int, Field(ge=1, le=6)] = 4) -> str:
        """Next public transport connections between two Swiss stops (live timetable).

        origin/destination: station or address names. date: YYYY-MM-DD, time: HH:MM (default: now).
        status source_unavailable means the timetable service is down: say so, do not guess times."""
        def run() -> dict:
            with httpx.Client(base_url=settings.transport_base_url, timeout=settings.lookup_timeout_seconds,
                              headers={"user-agent": settings.corpus_user_agent}) as client:
                return find_connections(client, origin=origin, destination=destination, date=date, time=time,
                                        limit=limit)
        return timed("swiss_connections", run)

    @mcp.tool(annotations=LIVE)
    def swiss_reference_rate() -> str:
        """The current Swiss mortgage reference interest rate for rents (BWO), with its effective date.

        If BWO cannot be reached, status is source_unavailable and the last stored value is returned with
        the date it was retrieved: tell the user it may be out of date."""
        def run() -> dict:
            with httpx.Client(timeout=settings.lookup_timeout_seconds, follow_redirects=True,
                              headers={"user-agent": settings.corpus_user_agent}) as client, \
                    connect(settings.database_url) as conn:
                return reference_rate(conn, client, settings.reference_rate_url)
        return timed("swiss_reference_rate", run)

    return mcp
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_mcp_server.py -v`
Expected: 6 PASS

Then the whole suite: `uv run pytest -q`. Tests that exercised the removed tools through the server (for example in `tests/integration/test_query_contract.py`) now fail. For each: if it tests the legacy `QueryCore` directly, keep it; if it goes through `build_server` and a removed tool, delete that test and name it in the commit message.

- [ ] **Step 5: Add a CLI command to ask the new service**

Append to `src/swiss_grounding/cli/serving_commands.py`:

```python
import json as _json_module
from dataclasses import asdict

from swiss_grounding.app import build_search_service
from swiss_grounding.serving.call_log import latency_summary
from swiss_grounding.serving.models import SearchRequest


@serving_app.command("ask")
def ask_cmd(question: str, location: list[str] = typer.Option([], "--location", "-l"),
            as_of: str | None = typer.Option(None, "--as-of")) -> None:
    """Run swiss_search from the command line and print the JSON response."""
    service = build_search_service(load_settings())
    request = SearchRequest(question, tuple(location), {}, date.fromisoformat(as_of) if as_of else None)
    typer.echo(_json_module.dumps(asdict(service.search(request)), default=str, ensure_ascii=False, indent=2))


@serving_app.command("stats")
def stats_cmd() -> None:
    """p50/p95 latency, abstention and empty-result rate per tool."""
    with connect(load_settings().database_url) as conn:
        for row in latency_summary(conn):
            typer.echo(f"{row['tool']:<22} calls={row['calls']:<5} p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
                       f"abstain={row['abstain_rate']:.0%} empty={row['empty_rate']:.0%}")
```

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/app.py src/swiss_grounding/mcp_server/server.py src/swiss_grounding/cli/serving_commands.py tests/integration/test_mcp_server.py tests/integration/conftest.py
git commit -m "feat: six-tool MCP server on the serving track (ADR 0015)"
```

---

### Task 20: Golden set schema, metrics and runner (ADR 0016)

**Files:**
- Create: `src/swiss_grounding/evals/golden_models.py`
- Create: `src/swiss_grounding/evals/metrics.py`
- Create: `src/swiss_grounding/evals/golden_runner.py`
- Modify: `src/swiss_grounding/cli/eval_commands.py` (`eval golden`; `eval probes` writes to the database only with `--record`)
- Test: `tests/unit/evals/test_metrics.py`, `tests/unit/evals/test_golden_models.py`, `tests/integration/serving/test_golden_runner.py`

A citation is identified across runs by its **key**: `url` plus `#anchor` when it has one. Relevance labels (Task 21) are stored per `(probe id, key)`.

- [ ] **Step 1: Write the failing metric tests**

```python
# tests/unit/evals/test_metrics.py
import math

from swiss_grounding.evals.metrics import THRESHOLDS, ndcg_at_k, passes, precision_at_k, recall_at_k


def test_recall_is_the_share_of_expected_sources_in_the_top_k():
    ranked = ["https://a", "https://b#x", "https://c"]
    assert recall_at_k(ranked, ["b#x", "zzz"], k=2) == 0.5


def test_precision_counts_only_judged_items():
    assert precision_at_k([True, None, False, True, None, True], k=5) == 2 / 3


def test_precision_of_nothing_judged_is_none():
    assert precision_at_k([None, None], k=5) is None


def test_ndcg_binary():
    assert ndcg_at_k([True, False, True], k=5) == (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))


def test_passes_against_thresholds():
    ok = {"status_accuracy": 0.95, "recall@5": 0.85, "precision@5": 0.75, "ndcg@5": 0.72}
    assert passes(ok) == {name: True for name in ok}
    assert passes({**ok, "recall@5": 0.5})["recall@5"] is False
    assert set(THRESHOLDS) >= set(ok)
```

- [ ] **Step 2: Write the failing schema test**

```python
# tests/unit/evals/test_golden_models.py
import pytest
from pydantic import ValidationError

from swiss_grounding.evals.golden_models import GoldenSet

GOOD = {"version": "2026-09-24.1", "probes": [{
    "id": "g-rm-scuol-holidays", "question": "Cura èn las vacanzas d'atun 2026 per la scola da Scuol?",
    "language": "rm", "area": "school_holidays", "level": "municipal", "split": "dev",
    "expect": {"status": "results", "sources": ["scuol"], "key_fact": "Herbstferien 2026 Scuol"}}]}


def test_valid_golden_set():
    assert GoldenSet.model_validate(GOOD).probes[0].locations == ()


def test_results_probe_needs_a_source_and_a_key_fact():
    bad = {**GOOD, "probes": [{**GOOD["probes"][0], "expect": {"status": "results"}}]}
    with pytest.raises(ValidationError, match="sources"):
        GoldenSet.model_validate(bad)


def test_ids_are_unique():
    with pytest.raises(ValidationError, match="duplicate"):
        GoldenSet.model_validate({**GOOD, "probes": GOOD["probes"] * 2})
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/unit/evals/test_metrics.py tests/unit/evals/test_golden_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement metrics and schema**

```python
# src/swiss_grounding/evals/metrics.py
"""Retrieval and status metrics with the pass thresholds of ADR 0016. Pure functions."""
import math
from collections.abc import Mapping, Sequence

THRESHOLDS: dict[str, float] = {"status_accuracy": 0.9, "recall@5": 0.8, "precision@5": 0.7, "ndcg@5": 0.7,
                                "faithfulness": 0.9}


def recall_at_k(ranked_keys: Sequence[str], expected: Sequence[str], k: int) -> float:
    """Share of expected-source fragments that some top-k citation key contains."""
    if not expected:
        return 1.0
    top = ranked_keys[:k]
    return sum(1 for frag in expected if any(frag in key for key in top)) / len(expected)


def precision_at_k(labels: Sequence[bool | None], k: int) -> float | None:
    judged = [x for x in labels[:k] if x is not None]
    return sum(judged) / len(judged) if judged else None


def ndcg_at_k(labels: Sequence[bool | None], k: int) -> float | None:
    gains = [1.0 if x else 0.0 for x in labels[:k]]
    positives = sum(1 for x in labels if x)
    if positives == 0:
        return None
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(positives, k)))
    return dcg / ideal


def mean(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def passes(summary: Mapping[str, float | None]) -> dict[str, bool]:
    return {name: value is not None and value >= THRESHOLDS[name]
            for name, value in summary.items() if name in THRESHOLDS}
```

```python
# src/swiss_grounding/evals/golden_models.py
"""The golden set (ADR 0016): hand-written probes with expected status, source and key fact."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# The sixteen topic areas of the challenge README, plus none for outside-scope probes.
Area = Literal["health_insurance", "taxes", "law", "waste", "moving", "permits", "pensions", "work",
               "school_holidays", "transport", "driving", "housing", "voting", "companies", "customs",
               "statistics", "none"]
GOLDEN_DIR = Path("evals/golden")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenExpect(_Strict):
    status: Literal["results", "needs_location", "outside_scope", "source_unavailable", "no_evidence"]
    place_statuses: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    key_fact: str | None = None

    @model_validator(mode="after")
    def _results_need_evidence(self) -> "GoldenExpect":
        if self.status == "results" and (not self.sources or not self.key_fact):
            raise ValueError("a results probe needs sources and a key_fact")
        return self


class GoldenProbe(_Strict):
    id: str = Field(min_length=3)
    question: str = Field(min_length=3)
    locations: tuple[str, ...] = ()
    language: Literal["de", "fr", "it", "rm", "en"]
    area: Area
    level: Literal["federal", "cantonal", "municipal", "none"]
    split: Literal["dev", "holdout"]
    tool: Literal["swiss_search", "swiss_premium", "swiss_connections", "swiss_reference_rate"] = "swiss_search"
    as_of: str | None = None
    note: str = ""
    expect: GoldenExpect


class GoldenSet(_Strict):
    version: str
    probes: tuple[GoldenProbe, ...]

    @model_validator(mode="after")
    def _unique(self) -> "GoldenSet":
        ids = [p.id for p in self.probes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate probe ids")
        return self


def load_golden(directory: Path = GOLDEN_DIR) -> GoldenSet:
    """All *.yaml files in the directory merged; they must share one version."""
    sets = [GoldenSet.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
            for p in sorted(directory.glob("*.yaml"))]
    versions = {s.version for s in sets}
    if len(versions) != 1:
        raise ValueError(f"golden files disagree on version: {sorted(versions)}")
    return GoldenSet(version=versions.pop(), probes=tuple(p for s in sets for p in s.probes))
```

Run: `uv run pytest tests/unit/evals/test_metrics.py tests/unit/evals/test_golden_models.py -v` → 8 PASS.

- [ ] **Step 5: Write the failing runner test**

```python
# tests/integration/serving/test_golden_runner.py
import pytest

from swiss_grounding.evals.golden_models import GoldenSet
from swiss_grounding.evals.golden_runner import run_golden
from tests.integration.serving.corpus_fixture import add_doc
from tests.integration.serving.test_search_service import service

pytestmark = pytest.mark.integration

GOLDEN = GoldenSet.model_validate({"version": "t", "probes": [
    {"id": "g1", "question": "Kündigungsfrist Wohnung?", "language": "de", "area": "housing", "level": "federal",
     "split": "dev", "expect": {"status": "results", "sources": ["/or/"], "key_fact": "drei Monate"}},
    {"id": "g2", "question": "Rundfunkbeitrag?", "locations": ["Konstanz"], "language": "de", "area": "none",
     "level": "none", "split": "dev", "expect": {"status": "outside_scope"}},
]})


def test_run_reports_status_accuracy_and_recall(serving_db):
    from swiss_grounding.db.connection import connect
    with connect(serving_db) as conn:
        add_doc(conn, group="or", lang="de", text="Kündigungsfrist Wohnung drei Monate",
                url="https://fedlex/or/de")
    report = run_golden(service(serving_db), GOLDEN, labels={}, split="all")
    assert report.summary["status_accuracy"] == 1.0
    assert report.summary["recall@5"] == 1.0
    assert report.summary["precision@5"] is None
    assert [o.probe_id for o in report.outcomes] == ["g1", "g2"]
```

- [ ] **Step 6: Implement the runner**

```python
# src/swiss_grounding/evals/golden_runner.py
"""Run the golden set against the search service and summarise against the thresholds."""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from swiss_grounding.evals.golden_models import GoldenProbe, GoldenSet
from swiss_grounding.evals.metrics import mean, ndcg_at_k, precision_at_k, recall_at_k
from swiss_grounding.serving.models import Citation, SearchRequest
from swiss_grounding.serving.search_service import SearchService

K = 5
Labels = Mapping[tuple[str, str], bool]


def citation_key(c: Citation) -> str:
    return f"{c.url}#{c.anchor}" if c.anchor else c.url


@dataclass(frozen=True)
class ProbeOutcome:
    probe_id: str
    expected_status: str
    status: str
    keys: tuple[str, ...]
    recall: float | None
    precision: float | None
    ndcg: float | None


@dataclass(frozen=True)
class GoldenReport:
    version: str
    split: str
    outcomes: tuple[ProbeOutcome, ...]
    summary: dict[str, float | None]


def _run_one(service: SearchService, probe: GoldenProbe, labels: Labels) -> ProbeOutcome:
    as_of = date.fromisoformat(probe.as_of) if probe.as_of else None
    resp = service.search(SearchRequest(probe.question, probe.locations, {}, as_of, 10))
    keys = tuple(citation_key(c) for p in resp.places for c in p.citations)
    judged = [labels.get((probe.id, k)) for k in keys]
    status_ok = resp.status if not probe.expect.place_statuses else ",".join(p.status for p in resp.places)
    expected = probe.expect.status if not probe.expect.place_statuses else ",".join(probe.expect.place_statuses)
    results = probe.expect.status == "results"
    return ProbeOutcome(probe.id, expected, status_ok, keys,
                        recall_at_k(keys, probe.expect.sources, K) if results else None,
                        precision_at_k(judged, K) if results else None,
                        ndcg_at_k(judged, K) if results else None)


def run_golden(service: SearchService, golden: GoldenSet, *, labels: Labels, split: str) -> GoldenReport:
    probes = [p for p in golden.probes if p.tool == "swiss_search" and split in ("all", p.split)]
    outcomes = tuple(_run_one(service, p, labels) for p in probes)
    summary = {
        "status_accuracy": mean([1.0 if o.status == o.expected_status else 0.0 for o in outcomes]),
        "recall@5": mean([o.recall for o in outcomes]),
        "precision@5": mean([o.precision for o in outcomes]),
        "ndcg@5": mean([o.ndcg for o in outcomes]),
    }
    return GoldenReport(golden.version, split, outcomes, summary)
```

Run: `uv run pytest tests/integration/serving/test_golden_runner.py -v` → PASS.

- [ ] **Step 7: Add `eval golden` and stop `eval probes` writing without `--record`**

In `src/swiss_grounding/cli/eval_commands.py`, change the `probes_cmd` block that calls `insert_results` so it runs only under `--record`:

```python
    if record:
        with connect(settings.database_url) as conn:
            for t, rs in grouped.items():
                insert_results(conn, run_id=run_id, git_commit=commit, tier=t, results=rs)
```

and update its docstring to "Run probes against the live database; with --record, store results in eval_run and write observed blocks." Add a test in `tests/unit/test_cli_eval.py` that runs `eval probes` with `insert_results` monkeypatched to raise and asserts it is not called without `--record`.

Add the golden command:

```python
GOLDEN_RUNS = Path("evals/golden/runs")
LABELS_PATH = Path("evals/golden/labels.jsonl")


def _load_labels(path: Path) -> dict[tuple[str, str], bool]:
    import json
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(r["probe_id"], r["key"]): bool(r["relevant"]) for r in rows}


@eval_app.command("golden")
def golden_cmd(
    split: str = typer.Option("dev", "--split", help="dev, holdout or all"),
    record: bool = typer.Option(False, "--record", help="write the report to evals/golden/runs/"),
) -> None:
    """Run the golden set; print per-probe results and the summary against ADR 0016 thresholds."""
    import json
    from dataclasses import asdict

    from swiss_grounding.app import build_search_service
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.golden_runner import run_golden
    from swiss_grounding.evals.metrics import passes

    settings = load_settings()
    service = build_search_service(settings, today=_today)
    report = run_golden(service, load_golden(), labels=_load_labels(LABELS_PATH), split=split)
    for o in report.outcomes:
        mark = "ok " if o.status == o.expected_status else "BAD"
        typer.echo(f"{mark} {o.probe_id:<32} {o.status:<16} (want {o.expected_status}) recall={o.recall}")
    verdict = passes(report.summary)
    for name, value in report.summary.items():
        shown = "n/a" if value is None else f"{value:.3f}"
        typer.echo(f"{name:<16} {shown:<7} {'PASS' if verdict.get(name) else 'FAIL'}")
    if record:
        GOLDEN_RUNS.mkdir(parents=True, exist_ok=True)
        config = {"reranker": service.reranker.name, "fitted": service.relevance.fitted,
                  "threshold": service.relevance.threshold, "index": settings.serving_index,
                  "rerank_candidates": settings.rerank_candidates, "git_commit": _git_commit()}
        path = GOLDEN_RUNS / f"{datetime.now(SWISS_TZ):%Y%m%dT%H%M%S}-{split}.json"
        path.write_text(json.dumps({"config": config, **asdict(report)}, ensure_ascii=False, indent=2,
                                   default=str), encoding="utf-8")
        typer.echo(f"report written to {path}")
```

- [ ] **Step 8: Run the eval unit tests and commit**

Run: `uv run pytest tests/unit/evals tests/unit/test_cli_eval.py tests/integration/serving/test_golden_runner.py -v`
Expected: all PASS

```bash
git add src/swiss_grounding/evals src/swiss_grounding/cli/eval_commands.py tests/unit/evals tests/unit/test_cli_eval.py tests/integration/serving/test_golden_runner.py
git commit -m "feat: golden-set runner with ADR 0016 thresholds; probes write only with --record"
```

---

### Task 21: Relevance labels by a model judge, checked by a human (paid, < $1)

For every dev and holdout golden probe with expected status `results`, the top 10 citations are judged relevant or not by gpt-5-mini. A random sample of 100 judgements is exported for a human to check; labels are used only when agreement is at least 85% (ADR 0016).

**Files:**
- Create: `src/swiss_grounding/evals/labels.py`
- Modify: `src/swiss_grounding/cli/eval_commands.py` (`eval label`, `eval label-check`)
- Test: `tests/unit/evals/test_labels.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_labels.py
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.evals.labels import LABEL_KIND, agreement, judge_pairs, label_task, sample_for_review

PAIR = {"probe_id": "g1", "key": "https://x#a", "question": "Kündigungsfrist?", "passage": "drei Monate"}


def test_task_asks_for_a_json_verdict_with_minimal_tokens():
    task = label_task(PAIR, model="gpt-5-mini")
    assert task.custom_id == "g1|https://x#a" and "relevant" in task.system and task.max_output_tokens <= 200


def test_judge_pairs_records_verdicts_and_spend():
    spent = []
    llm = FakeLLM(lambda t: {"relevant": True, "reason": "states the period"})
    rows = judge_pairs([PAIR], llm, model="gpt-5-mini", on_usage=lambda usd: spent.append(usd))
    assert rows == [{**PAIR, "relevant": True, "reason": "states the period", "judge": "gpt-5-mini"}]
    assert spent and spent[0] > 0 and LABEL_KIND == "eval_label"


def test_sample_is_deterministic():
    rows = [{**PAIR, "key": str(i), "relevant": True} for i in range(300)]
    assert sample_for_review(rows, 100, seed=7) == sample_for_review(rows, 100, seed=7)
    assert len(sample_for_review(rows, 100, seed=7)) == 100


def test_agreement():
    judged = [{"probe_id": "a", "key": "1", "relevant": True}, {"probe_id": "a", "key": "2", "relevant": False}]
    human = {("a", "1"): True, ("a", "2"): True}
    assert agreement(judged, human) == 0.5
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/evals/test_labels.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/evals/labels.py
"""Relevance labels: a model judges (question, passage) pairs; a human checks a sample (ADR 0016)."""
import random
from collections.abc import Callable, Mapping, Sequence

from swiss_grounding.corpus.budget import cost_usd
from swiss_grounding.corpus.providers import LLMProvider
from swiss_grounding.corpus.runner import LlmTask

LABEL_KIND = "eval_label"
MIN_AGREEMENT = 0.85
SYSTEM = ("You judge search results for a Swiss public-information service. Given a user's question and one "
          "passage from an official source, decide whether the passage answers the question or states a fact "
          "needed to answer it for the place asked about. Answer JSON: {\"relevant\": true|false, "
          "\"reason\": \"<one short sentence>\"}.")


def label_task(pair: Mapping, model: str) -> LlmTask:
    return LlmTask(custom_id=f"{pair['probe_id']}|{pair['key']}", model=model, system=SYSTEM,
                   user=f"Question: {pair['question']}\n\nPassage:\n{pair['passage']}", max_output_tokens=120)


def judge_pairs(pairs: Sequence[Mapping], llm: LLMProvider, *, model: str,
                on_usage: Callable[[float], None]) -> list[dict]:
    rows = []
    for pair in pairs:
        reply, usage = llm.complete(label_task(pair, model))
        on_usage(cost_usd(model, usage.input_tokens, usage.output_tokens, batch=False))
        rows.append({**pair, "relevant": bool(reply.get("relevant")), "reason": str(reply.get("reason", "")),
                     "judge": model})
    return rows


def sample_for_review(rows: Sequence[Mapping], n: int, seed: int) -> list[Mapping]:
    return random.Random(seed).sample(list(rows), min(n, len(rows)))


def agreement(judged: Sequence[Mapping], human: Mapping[tuple[str, str], bool]) -> float:
    compared = [(r["relevant"], human[(r["probe_id"], r["key"])]) for r in judged
                if (r["probe_id"], r["key"]) in human]
    return sum(1 for a, b in compared if a == b) / len(compared) if compared else 0.0
```

Run: `uv run pytest tests/unit/evals/test_labels.py -v` → 4 PASS.

- [ ] **Step 4: Add the commands**

In `eval_commands.py`:

```python
LABEL_BUDGET_USD = 2.0
REVIEW_PATH = Path("evals/golden/label_review.csv")


@eval_app.command("label")
def label_cmd(confirm_spend: bool = typer.Option(False, "--confirm-spend", help="required: calls gpt-5-mini"),
              top: int = typer.Option(10, "--top")) -> None:
    """Judge the top citations of every results probe with gpt-5-mini; write evals/golden/labels.jsonl."""
    import json

    from swiss_grounding.app import build_search_service
    from swiss_grounding.corpus.budget import ensure_within, record_spend
    from swiss_grounding.corpus.providers import OpenAILLM
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.golden_runner import citation_key
    from swiss_grounding.evals.labels import LABEL_KIND, judge_pairs, sample_for_review
    from swiss_grounding.serving.models import SearchRequest

    if not confirm_spend:
        typer.echo("This calls gpt-5-mini (about $0.30 for 1,500 pairs). Re-run with --confirm-spend.", err=True)
        raise typer.Exit(code=1)
    settings = load_settings()
    service = build_search_service(settings, today=_today)
    pairs = []
    for probe in load_golden().probes:
        if probe.expect.status != "results" or probe.tool != "swiss_search":
            continue
        resp = service.search(SearchRequest(probe.question, probe.locations, {}, None, top))
        for c in [c for p in resp.places for c in p.citations][:top]:
            pairs.append({"probe_id": probe.id, "key": citation_key(c), "question": probe.question,
                          "passage": f"{' › '.join(c.breadcrumb)}\n{c.passage}"})
    done = _load_labels(LABELS_PATH)
    todo = [p for p in pairs if (p["probe_id"], p["key"]) not in done]
    with connect(settings.database_url) as conn:
        ensure_within(conn, estimate=0.0005 * len(todo), total_cap=settings.corpus_budget_usd,
                      kind=LABEL_KIND, kind_cap=LABEL_BUDGET_USD)
        rows = judge_pairs(todo, OpenAILLM(settings.openai_api_key), model=settings.corpus_doc_model,
                           on_usage=lambda usd: record_spend(conn, kind=LABEL_KIND, model=settings.corpus_doc_model,
                                                             usd=usd, input_tokens=0, output_tokens=0,
                                                             estimated=False))
    with LABELS_PATH.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    review = sample_for_review(rows, 100, seed=20260924)
    REVIEW_PATH.write_text("probe_id;key;question;passage;model_says;human_says\n" + "".join(
        f"{r['probe_id']};{r['key']};{r['question']};{r['passage'][:300].replace(';', ',').replace(chr(10), ' ')};"
        f"{r['relevant']};\n" for r in review), encoding="utf-8")
    typer.echo(f"{len(rows)} pairs judged; fill the human_says column of {REVIEW_PATH} (true/false), "
               "then run `eval label-check`.")


@eval_app.command("label-check")
def label_check_cmd() -> None:
    """Agreement between the model judge and the human-checked sample; must be ≥ 0.85 (ADR 0016)."""
    import csv
    import json

    from swiss_grounding.evals.labels import MIN_AGREEMENT, agreement

    rows = [json.loads(x) for x in LABELS_PATH.read_text(encoding="utf-8").splitlines() if x.strip()]
    with REVIEW_PATH.open(encoding="utf-8") as f:
        human = {(r["probe_id"], r["key"]): r["human_says"].strip().lower() == "true"
                 for r in csv.DictReader(f, delimiter=";") if r["human_says"].strip()}
    score = agreement(rows, human)
    typer.echo(f"agreement on {len(human)} checked pairs: {score:.2f} (need {MIN_AGREEMENT})")
    if score < MIN_AGREEMENT:
        raise typer.Exit(code=1)
```

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/labels.py src/swiss_grounding/cli/eval_commands.py tests/unit/evals/test_labels.py
git commit -m "feat: model-judged relevance labels with a human-checked sample"
```

---

### Task 22: Fit the relevance probability and choose the abstention threshold

The model is fitted on the **dev** split's labelled pairs and the threshold is chosen on the **holdout** split, as the lowest probability at which precision is at least 0.9 (so that "not covered" or "no evidence" is said rather than a wrong passage cited). Fitting runs offline; the server only reads the JSON.

**Files:**
- Create: `src/swiss_grounding/evals/fit.py`
- Modify: `src/swiss_grounding/cli/eval_commands.py` (`eval fit`)
- Test: `tests/unit/evals/test_fit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_fit.py
import json

import numpy as np

from swiss_grounding.evals.fit import choose_threshold, fit_model, write_model
from swiss_grounding.serving.relevance import FEATURES, LogisticRelevance, load_relevance


def test_threshold_is_the_lowest_probability_reaching_the_target_precision():
    probs = [0.9, 0.8, 0.7, 0.4, 0.3]
    labels = [True, True, False, True, False]
    assert choose_threshold(probs, labels, target_precision=0.75) == 0.4


def test_fit_separates_a_separable_feature():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, len(FEATURES)))
    y = x[:, 0] > 0
    weights, bias = fit_model(x, y)
    assert weights[0] > 1.0


def test_written_model_loads_as_logistic(tmp_path):
    path = tmp_path / "m.json"
    write_model(path, weights=[0.1] * len(FEATURES), bias=-1.0, threshold=0.4, reranker="r",
                meta={"pairs": 10})
    assert isinstance(load_relevance(path, "r"), LogisticRelevance)
    assert json.loads(path.read_text())["meta"]["pairs"] == 10
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --extra eval pytest tests/unit/evals/test_fit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/evals/fit.py
"""Fit the logistic relevance model (sigmoid, not isotonic: < 1,000 pairs; RESEARCH §H1)."""
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from swiss_grounding.serving.relevance import FEATURES

TARGET_PRECISION = 0.9
REGULARISATION_C = 1.0


def fit_model(x: np.ndarray, y: np.ndarray) -> tuple[list[float], float]:
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression(C=REGULARISATION_C, max_iter=1000).fit(x, y)
    return [float(w) for w in model.coef_[0]], float(model.intercept_[0])


def choose_threshold(probs: Sequence[float], labels: Sequence[bool], target_precision: float) -> float:
    """Lowest probability p such that the pairs scoring >= p reach the target precision."""
    order = sorted(zip(probs, labels, strict=True), key=lambda t: -t[0])
    best, hits = max(probs), 0
    for i, (p, label) in enumerate(order, start=1):
        hits += label
        if hits / i >= target_precision:
            best = p
    return best


def write_model(path: Path, *, weights: Sequence[float], bias: float, threshold: float, reranker: str,
                meta: Mapping) -> None:
    path.write_text(json.dumps({"reranker": reranker, "features": list(FEATURES), "weights": list(weights),
                                "bias": bias, "threshold": threshold, "fitted_at": datetime.now(UTC).isoformat(),
                                "meta": dict(meta)}, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Add `eval fit`**

The command re-runs search for each labelled probe to rebuild the feature vector of each labelled citation (features depend on the live pipeline), fits on dev, picks the threshold on holdout, prints holdout precision/recall at that threshold, and writes `evals/relevance_model.json`:

```python
@eval_app.command("fit")
def fit_cmd(out: Path = typer.Option(Path("evals/relevance_model.json"), "--out")) -> None:
    """Fit the relevance probability on dev labels; choose the abstention threshold on holdout."""
    import numpy as np

    from swiss_grounding.app import build_search_service
    from swiss_grounding.evals.fit import TARGET_PRECISION, choose_threshold, fit_model, write_model
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.golden_runner import citation_key
    from swiss_grounding.serving.models import SearchRequest
    from swiss_grounding.serving.relevance import ProvisionalRelevance, feature_vector

    settings = load_settings()
    base = build_search_service(settings, today=_today)
    service = replace(base, relevance=ProvisionalRelevance(threshold=0.0))  # keep every candidate
    labels = _load_labels(LABELS_PATH)
    rows: dict[str, list[tuple[list[float], bool]]] = {"dev": [], "holdout": []}
    for probe in load_golden().probes:
        if probe.expect.status != "results":
            continue
        for scored, key in service.scored_for_eval(SearchRequest(probe.question, probe.locations, {}, None, 10)):
            if (probe.id, key) in labels:
                rows[probe.split].append((list(scored), labels[(probe.id, key)]))
    x_dev = np.array([r[0] for r in rows["dev"]])
    y_dev = np.array([r[1] for r in rows["dev"]])
    weights, bias = fit_model(x_dev, y_dev)
    z = [bias + sum(w * v for w, v in zip(weights, r[0], strict=True)) for r in rows["holdout"]]
    probs = [1 / (1 + np.exp(-v)) for v in z]
    threshold = choose_threshold(probs, [r[1] for r in rows["holdout"]], TARGET_PRECISION)
    write_model(out, weights=weights, bias=bias, threshold=float(threshold), reranker=base.reranker.name,
                meta={"dev_pairs": len(rows["dev"]), "holdout_pairs": len(rows["holdout"]),
                      "dataset_version": load_golden().version, "git_commit": _git_commit()})
    typer.echo(f"fitted on {len(rows['dev'])} pairs, threshold {threshold:.3f} from {len(rows['holdout'])}; "
               f"wrote {out}")
```

(`from dataclasses import replace` at the top of `eval_commands.py`.) This needs one small method on `SearchService` that returns `(feature_vector, citation_key)` for every scored group of a single-place request. Add it in `search_service.py`, with a unit-level integration test in `tests/integration/serving/test_search_service.py` asserting it yields `len(FEATURES)`-long tuples:

```python
    def scored_for_eval(self, request: SearchRequest) -> list[tuple[tuple[float, ...], str]]:
        """(features, citation key) of every scored group for the request's first place; evals only."""
        [outcome] = place_outcomes(request.question, request.locations[:1], self.resolver, self.tree)
        if pre_search(outcome) is not None:
            return []
        q = self._embed(request)
        path, local = self._scope_path(outcome)
        arm = ArmQuery(request.question, q.lang, q.vec, q.sparse, request.translations, q.translation_vecs, path,
                       local, request.as_of, self.rerank_candidates, self.rerank_candidates,
                       self.local_quota if local else 0)
        with connect(self.database_url) as conn:
            cands = gather_candidates(conn, arm, index=self.index, ef_search=self.ef_search)
            versions = aligned_versions(conn, list(dict.fromkeys((c.translation_group_id, c.align_key)
                                                                 for c in cands)), request.as_of)
        groups = collapse(cands, versions, q.lang)
        reps = [g.representative for g in groups]
        scores = self.reranker.score(request.question, [passage_text(r.breadcrumb, r.text) for r in reps])
        today = request.as_of or self.today()
        out = []
        for g, score in zip(groups, scores, strict=True):
            rep = g.representative
            x = feature_vector(g, rerank_score=score, question_lang=q.lang, tier=self._tier(rep.extent_id, path),
                               today=today)
            out.append((x, f"{rep.url}#{rep.anchor}" if rep.anchor else rep.url))
        return out
```

- [ ] **Step 5: Run the tests and commit**

Run: `uv run --extra eval pytest tests/unit/evals/test_fit.py tests/integration/serving/test_search_service.py -v`
Expected: all PASS

```bash
git add src/swiss_grounding/evals/fit.py src/swiss_grounding/serving/search_service.py src/swiss_grounding/cli/eval_commands.py tests/unit/evals/test_fit.py tests/integration/serving/test_search_service.py
git commit -m "feat: fit the relevance probability and pick the abstention threshold on holdout"
```

---

### Task 23: Generated questions for recall (paid, < $1)

gpt-5-mini writes one question per sampled chunk, in the chunk's language, that the chunk answers. We measure recall@5 of the chunk's own key. Used for recall only, never for tuning (ADR 0016).

**Files:**
- Create: `src/swiss_grounding/evals/generate.py`
- Modify: `src/swiss_grounding/cli/eval_commands.py` (`eval generate`, `eval recall`)
- Test: `tests/unit/evals/test_generate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_generate.py
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.evals.generate import SAMPLE_SQL, generate_questions

CHUNK = {"chunk_id": 1, "language": "fr", "url": "https://x", "anchor": "a", "extent_id": "CH-VD",
         "breadcrumb": ["Permis"], "text": "Le permis étranger doit être échangé dans les 12 mois."}


def test_generates_a_question_in_the_chunk_language_with_its_key():
    llm = FakeLLM(lambda t: {"question": "Dans quel délai dois-je échanger mon permis?"})
    [row] = generate_questions([CHUNK], llm, model="gpt-5-mini", on_usage=lambda usd: None)
    assert row["key"] == "https://x#a" and row["language"] == "fr" and row["question"].endswith("?")


def test_sample_sql_is_stratified_by_language_and_level():
    assert "partition by c.language" in SAMPLE_SQL and "tablesample" not in SAMPLE_SQL
```

- [ ] **Step 2: Implement**

```python
# src/swiss_grounding/evals/generate.py
"""Generated questions (ADR 0016): one per sampled chunk, answerable by that chunk. Recall only."""
from collections.abc import Callable, Mapping, Sequence

from swiss_grounding.corpus.budget import cost_usd
from swiss_grounding.corpus.providers import LLMProvider
from swiss_grounding.corpus.runner import LlmTask

GENERATE_KIND = "eval_generate"
SYSTEM = ("Write one question a resident of Switzerland might ask that the passage answers. Write it in the "
          "passage's language, as a person would type it, without quoting the passage or naming its article "
          "number. Answer JSON: {\"question\": \"...\"}.")
# Up to `per_stratum` random current chunks per (language, source level), skipping boilerplate and tiny chunks.
SAMPLE_SQL = """
select * from (
  select c.id as chunk_id, c.language, d.url, c.anchor, c.extent_id, c.breadcrumb, c.text,
         row_number() over (partition by c.language, s.level order by md5(c.id::text || %(seed)s)) as n
  from corpus.chunk c join corpus.document d on d.id = c.document_id join corpus.source s on s.id = d.source_id
  where c.status = 'current' and d.status = 'current' and length(c.text) > 200
) t where n <= %(per_stratum)s
"""


def generate_questions(chunks: Sequence[Mapping], llm: LLMProvider, *, model: str,
                       on_usage: Callable[[float], None]) -> list[dict]:
    rows = []
    for c in chunks:
        task = LlmTask(custom_id=str(c["chunk_id"]), model=model, system=SYSTEM,
                       user=f"Passage ({c['language']}):\n{' › '.join(c['breadcrumb'])}\n{c['text'][:2000]}",
                       max_output_tokens=120)
        reply, usage = llm.complete(task)
        on_usage(cost_usd(model, usage.input_tokens, usage.output_tokens, batch=False))
        key = f"{c['url']}#{c['anchor']}" if c["anchor"] else c["url"]
        rows.append({"chunk_id": c["chunk_id"], "key": key, "language": c["language"],
                     "extent_id": c["extent_id"], "question": str(reply.get("question", "")).strip()})
    return [r for r in rows if r["question"]]
```

- [ ] **Step 3: Add the commands**

`eval generate --confirm-spend --per-stratum 35` samples with `SAMPLE_SQL` (5 languages × 3 levels × 35 ≈ 500), guards spend exactly as `eval label` does (kind `eval_generate`, cap $2), and writes `evals/generated/questions.jsonl`. `eval recall` runs each generated question through `SearchService.search` with `locations=(extent label,)` when the chunk's extent is below `CH`, and prints recall@5 overall and per language:

```python
@eval_app.command("recall")
def recall_cmd(path: Path = typer.Option(Path("evals/generated/questions.jsonl"), "--path")) -> None:
    """Recall@5 of generated questions: is the chunk that inspired the question in the top 5?"""
    import json
    from collections import defaultdict

    from swiss_grounding.app import build_search_service
    from swiss_grounding.evals.golden_runner import citation_key
    from swiss_grounding.serving.models import SearchRequest

    service = build_search_service(load_settings(), today=_today)
    hits: dict[str, list[float]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        place = () if row["extent_id"] == "CH" else (service.tree.get(row["extent_id"]).label("de"),)
        resp = service.search(SearchRequest(row["question"], place, {}, None, 5))
        keys = [citation_key(c) for p in resp.places for c in p.citations][:5]
        hits[row["language"]].append(1.0 if row["key"] in keys else 0.0)
    total = [v for vs in hits.values() for v in vs]
    for lang, vs in sorted(hits.items()):
        typer.echo(f"{lang}: recall@5 {sum(vs) / len(vs):.3f} over {len(vs)}")
    typer.echo(f"all: recall@5 {sum(total) / len(total):.3f} over {len(total)}")
```

- [ ] **Step 4: Run the tests and commit**

Run: `uv run pytest tests/unit/evals/test_generate.py -v` → 2 PASS

```bash
git add src/swiss_grounding/evals/generate.py src/swiss_grounding/cli/eval_commands.py tests/unit/evals/test_generate.py
git commit -m "feat: generated questions and a recall@5 run over them"
```

---

### Task 24: Faithfulness end to end through the MCP

A model answers each golden `results` probe through the MCP server with `claude -p` (the existing judge harness), and a judge checks every claim of the answer against the passages the tools returned. Faithfulness = share of answers the judge finds fully supported. Target ≥ 0.9 (ADR 0016).

**Files:**
- Create: `evals/judge/faithfulness.md`
- Modify: `src/swiss_grounding/evals/judge_harness.py` (accept a question string instead of a legacy `Probe`)
- Modify: `src/swiss_grounding/cli/eval_commands.py` (`eval faithfulness`)
- Test: `tests/unit/evals/test_judge_harness.py`

- [ ] **Step 1: Write the rubric**

```markdown
<!-- evals/judge/faithfulness.md -->
You grade one answer given to a resident of Switzerland. You see the question, the evidence the answering model
received from the tools (verbatim), and the answer.

Return JSON: {"faithful": true|false, "unsupported_claims": ["..."], "cited_urls_in_evidence": true|false}

- faithful is true only if every factual claim in the answer (numbers, dates, deadlines, fees, rules, places)
  is stated in or directly implied by the evidence. Advice to contact an office is not a factual claim.
- An answer that says the question is not covered, or asks for the user's place, is faithful when the evidence
  says so (status outside_scope / needs_location / no_evidence).
- cited_urls_in_evidence is false if the answer cites any URL that does not appear in the evidence.
```

- [ ] **Step 2: Generalise the harness entry point**

`run_case(probe, model, rubric)` takes a legacy `Probe` and grades the fixed `VERDICT_KEYS`. Give `parse_verdict` a `keys` parameter (default `VERDICT_KEYS`, so existing callers are unchanged) and add a question-based sibling with the same error handling as `run_case`:

```python
FAITHFULNESS_KEYS = ("faithful", "cited_urls_in_evidence")


def parse_verdict(text: str, keys: Sequence[str] = VERDICT_KEYS) -> tuple[dict[str, bool], bool]:
    """Verdict keyed True/False, and whether a JSON object was found at all (last-object-wins)."""
    raw = _last_json_object(text)
    parsed = raw is not None
    raw = raw or {}
    return {k: _is_true(raw.get(k)) for k in keys}, parsed


def run_question(question: str, case_id: str, model: str, rubric: str,
                 keys: Sequence[str] = FAITHFULNESS_KEYS) -> dict:
    """Answer `question` with `model` through the MCP server; grade it with the fixed JUDGE_MODEL."""
    try:
        stream = _claude(question, model, mcp=True, stream=True)
        evidence, answer = extract_tool_results(stream)
        verdict_text = _claude(build_judge_prompt(rubric, question, evidence, answer), JUDGE_MODEL,
                               mcp=False, stream=False)
        verdict, parsed = parse_verdict(verdict_text, keys)
        return {"id": case_id, "model": model, "answer": answer, "evidence": evidence, "verdict": verdict,
                "verdict_parsed": parsed, "error": None}
    except Exception as exc:  # noqa: BLE001 - one bad case must not end a run
        return {"id": case_id, "model": model, "answer": "", "evidence": [],
                "verdict": dict.fromkeys(keys, False), "verdict_parsed": False, "error": str(exc)}
```

Also update `ANSWER_SYSTEM` to the new contract: "Answer the user's question using only the swiss-grounding tools. Cite the URLs the tools return. If a tool says the question is outside scope or that the rules of a place are not covered, say so." Add a test in `tests/unit/evals/test_judge_harness.py`:

```python
def test_parse_verdict_with_faithfulness_keys():
    from swiss_grounding.evals.judge_harness import FAITHFULNESS_KEYS, parse_verdict
    verdict, parsed = parse_verdict('{"faithful": true, "unsupported_claims": [], "cited_urls_in_evidence": true}',
                                    FAITHFULNESS_KEYS)
    assert parsed and verdict == {"faithful": True, "cited_urls_in_evidence": True}
```

- [ ] **Step 3: Add `eval faithfulness`**

```python
@eval_app.command("faithfulness")
def faithfulness_cmd(model: str = typer.Option("claude-sonnet-5", "--model"),
                     split: str = typer.Option("holdout", "--split"),
                     out: Path = typer.Option(Path("evals/judge/faithfulness.json"), "--out")) -> None:
    """Answer golden results probes through the MCP with `claude -p` and grade faithfulness (target 0.9)."""
    import json

    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.judge_harness import run_question

    rubric = Path("evals/judge/faithfulness.md").read_text(encoding="utf-8")
    probes = [p for p in load_golden().probes if split in ("all", p.split)]
    records = []
    for p in probes:
        question = p.question if not p.locations else f"{p.question} ({', '.join(p.locations)})"
        records.append(run_question(question, p.id, model, rubric))
    scored = [r for r in records if r["verdict_parsed"]]
    rate = sum(1 for r in scored if r["verdict"].get("faithful")) / len(scored) if scored else 0.0
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"faithfulness {rate:.3f} over {len(scored)} graded answers ({len(records) - len(scored)} unparsed)")
```

- [ ] **Step 4: Run the tests and commit**

Run: `uv run pytest tests/unit/evals/test_judge_harness.py -v` → all PASS

```bash
git add evals/judge/faithfulness.md src/swiss_grounding/evals/judge_harness.py src/swiss_grounding/cli/eval_commands.py tests/unit/evals/test_judge_harness.py
git commit -m "feat: end-to-end faithfulness over the golden set"
```

---

### Task 25: Write the golden set (content, with the encoded corpus open)

About 150 probes in `evals/golden/*.yaml`, all with `version: 2026-09-24.1`. This is writing, not coding: each expected source is found by reading official sites, not by trusting what the server returns. One in four probes per stratum gets `split: holdout`; never tune thresholds or weights while looking at holdout results.

**Files:**
- Create: `evals/golden/challenge.yaml` (the probes below, written in full)
- Create: `evals/golden/federal.yaml`, `evals/golden/cantonal.yaml`, `evals/golden/municipal.yaml`, `evals/golden/scope.yaml`
- Test: `tests/unit/evals/test_golden_files.py`

**Quotas** (≈150):

| Stratum | Count | Notes |
|---|---|---|
| `results`, federal | 40 | Areas 1, 3, 6, 7, 8, 12, 13, 15; ≥ 8 each in de/fr/it, ≥ 4 rm, ≥ 4 en |
| `results`, cantonal | 30 | 5 per declared canton, in that canton's language(s) |
| `results`, municipal | 30 | ≥ 4 per declared city, incl. school holidays and waste |
| `outside_scope` | 20 | 8 foreign places (with and without a country word), 6 Swiss places outside scope, 6 out-of-scope topics (register, weather, tax amount, pension amount) |
| `needs_location` | 15 | Local topics asked with no place (waste, school holidays, dog tax, residents' office) |
| multi-place (`place_statuses`) | 10 | Two or three declared cities |
| lookups (`tool:` premium / connections / reference_rate) | 5 | Not run by `eval golden`; used by `eval faithfulness` and the demo. Source failure is covered by the mocked-outage integration tests (Tasks 17, 18). |

- [ ] **Step 1: Write `evals/golden/challenge.yaml` exactly**

```yaml
version: 2026-09-24.1
probes:
  - id: g-sample-karton
    question: Wann wird bei uns das nächste Mal Karton abgeholt?
    language: de
    area: waste
    level: municipal
    split: dev
    note: Challenge sample 1 / practice missing_location. Asking for the municipality is correct.
    expect: {status: needs_location}
  - id: g-sample-vaud-licence
    question: Échanger mon permis de conduire étranger dans le canton de Vaud, et en combien de temps?
    language: fr
    area: driving
    level: cantonal
    split: dev
    note: Challenge sample 2. Cantonal procedure page plus the 12-month rule (VZV/OAC SR 741.51).
    expect: {status: results, sources: [vd.ch], key_fact: "Le permis étranger doit être échangé dans les 12 mois suivant l'arrivée en Suisse."}
  - id: g-sample-lugano-premium
    question: Premio mensile più basso, adulto 30 anni, Lugano, franchigia 2500?
    language: it
    area: health_insurance
    level: federal
    split: dev
    tool: swiss_premium
    note: Challenge sample 3. Lookup, not retrieval.
    expect: {status: results, sources: [opendata.swiss], key_fact: "Cheapest 2026 premium for premium region TI-1, adult, deductible 2500."}
  - id: g-sample-scuol-holidays
    question: Cura èn las vacanzas d'atun 2026 per la scola da Scuol?
    language: rm
    area: school_holidays
    level: municipal
    split: dev
    note: Challenge sample 4 / practice romansh_locality.
    expect: {status: results, sources: [scuol], key_fact: "Dates of the 2026 autumn holidays of the Scuol school."}
  - id: g-sample-konstanz-with-place
    question: Wie hoch ist der Rundfunkbeitrag nach meinem Umzug nach Konstanz?
    locations: [Konstanz]
    language: de
    area: none
    level: none
    split: dev
    note: Challenge sample 5 / practice cross_border, as a client that passes the place.
    expect: {status: outside_scope}
  - id: g-sample-konstanz-no-place
    question: Wie hoch ist der Rundfunkbeitrag nach meinem Umzug nach Konstanz?
    language: de
    area: none
    level: none
    split: holdout
    note: >-
      Known risk (ADR 0013, no foreign-place list): a client that does not pass the place leaves the server
      only the question text, where "Konstanz" is not a Swiss name and no country is named. Kept to measure it.
    expect: {status: outside_scope}
  - id: g-practice-geneva-holidays
    question: Quelles sont les dates des vacances scolaires 2026 à Genève?
    language: fr
    area: school_holidays
    level: cantonal
    split: dev
    note: Practice enough_context. Do not ask back.
    expect: {status: results, sources: [ge.ch], key_fact: "The 2026 school holiday dates of the canton of Geneva."}
  - id: g-practice-paired-registration
    question: Comment m'annoncer à la commune après un déménagement?
    locations: [Lausanne, Bern]
    language: fr
    area: moving
    level: municipal
    split: dev
    note: Practice paired_jurisdiction. Two separate answers.
    expect: {status: results, place_statuses: [results, results], sources: [lausanne.ch, bern.ch], key_fact: "Registration with the residents' office within the local deadline, per city."}
  - id: g-practice-citation-licence
    question: Welche Quelle belegt die Frist von 12 Monaten für den Umtausch des ausländischen Führerausweises?
    language: de
    area: driving
    level: federal
    split: dev
    note: Practice citation_support. The passage must state the deadline.
    expect: {status: results, sources: ["741.51"], key_fact: "Art. 44 VZV: foreign licence holders must obtain a Swiss licence within 12 months."}
  - id: g-practice-reference-rate
    question: Wie hoch ist der aktuelle Referenzzinssatz für Mieten?
    language: de
    area: housing
    level: federal
    split: dev
    tool: swiss_reference_rate
    note: Practice rate_freshness and source_failure (mocked outage in Task 18 tests).
    expect: {status: results, sources: [bwo.admin.ch], key_fact: "Current reference rate and its effective date."}
  - id: g-national-notice-period
    question: Wie lange ist die Kündigungsfrist für eine Mietwohnung?
    language: de
    area: law
    level: federal
    split: dev
    note: National question; asking for a place would be wrong.
    expect: {status: results, sources: [art_266_c], key_fact: "Three months to a customary local term (Art. 266c OR)."}
  - id: g-basel-dog-tax
    question: Wie hoch ist die Hundesteuer?
    locations: [Basel]
    language: de
    area: none
    level: municipal
    split: dev
    note: Swiss place outside the declared scope; no federal dog tax exists.
    expect: {status: outside_scope}
  - id: g-register-lookup
    question: Ist die Muster AG im Handelsregister eingetragen?
    language: de
    area: companies
    level: none
    split: dev
    note: Out-of-scope topic. Expected no_evidence with the scope statement, which names the commercial register.
    expect: {status: no_evidence}
```

- [ ] **Step 2: Write the file test**

```python
# tests/unit/evals/test_golden_files.py
from collections import Counter

from swiss_grounding.evals.golden_models import load_golden


def test_golden_set_loads_and_meets_quotas():
    golden = load_golden()
    assert len(golden.probes) >= 140
    statuses = Counter(p.expect.status for p in golden.probes)
    assert statuses["outside_scope"] >= 20 and statuses["needs_location"] >= 15
    assert sum(1 for p in golden.probes if p.expect.place_statuses) >= 10
    assert Counter(p.language for p in golden.probes)["rm"] >= 4
    holdout = sum(1 for p in golden.probes if p.split == "holdout")
    assert 0.2 <= holdout / len(golden.probes) <= 0.3
```

- [ ] **Step 3: Write the remaining files by stratum**

For each probe: (1) write the question as a resident would type it, in the stratum's language; (2) find the answering page on the official site in a browser; (3) check it is in the corpus: `uv run swiss-grounding serving ask "<question>" -l "<place>"` and `select url from corpus.document where url like '%<fragment>%'`; if the page is missing, add its URL to `manifests/declared-scope.yaml`, run the free fetch for that source and `corpus embed`, and note it in the runbook; (4) set `sources` to URL fragments (or Fedlex eIds such as `art_266_c`) that identify the right page, and `key_fact` to the fact the answer must state. Do not copy expected sources from the server's output without checking them.

- [ ] **Step 4: Run and commit**

Run: `uv run pytest tests/unit/evals/test_golden_files.py -v` → PASS; `uv run swiss-grounding eval golden --split dev` → prints a table (first numbers, not yet gating).

```bash
git add evals/golden tests/unit/evals/test_golden_files.py
git commit -m "test: golden set of about 150 probes across areas, languages, levels and statuses"
```

---

### Task 26: Prebuilt dump and one-command setup (ADR 0017)

**Files:**
- Create: `src/swiss_grounding/serving/dump.py`
- Modify: `src/swiss_grounding/cli/serving_commands.py` (`dump export`, `setup`)
- Test: `tests/unit/serving/test_dump.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/serving/test_dump.py
import pytest

from swiss_grounding.serving.dump import build_manifest, join_parts, split_file, verify_parts


def test_split_join_round_trip_with_checksums(tmp_path):
    src = tmp_path / "corpus.dump"
    src.write_bytes(bytes(range(256)) * 40)
    parts = split_file(src, tmp_path / "out", part_bytes=3000)
    assert len(parts) == 4
    manifest = build_manifest(parts, meta={"git_commit": "abc"})
    verify_parts(tmp_path / "out", manifest)
    joined = join_parts(tmp_path / "out", manifest, tmp_path / "joined.dump")
    assert joined.read_bytes() == src.read_bytes()


def test_corrupt_part_is_refused(tmp_path):
    src = tmp_path / "corpus.dump"
    src.write_bytes(b"x" * 5000)
    parts = split_file(src, tmp_path / "out", part_bytes=3000)
    manifest = build_manifest(parts, meta={})
    parts[0].write_bytes(b"y" * 3000)
    with pytest.raises(ValueError, match="checksum"):
        verify_parts(tmp_path / "out", manifest)
```

- [ ] **Step 2: Implement**

```python
# src/swiss_grounding/serving/dump.py
"""Split, checksum and reassemble the prebuilt database dump (ADR 0017)."""
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path

PART_BYTES = 1_900 * 1024 * 1024        # under GitHub's 2 GiB per release asset
MANIFEST_NAME = "corpus.manifest.json"
CHUNK = 1024 * 1024
# Table data left out of the default dump: legacy public-schema tables, the OpenAI vectors (optional asset),
# and per-installation logs.
EXCLUDE_DATA = ("public.chunk", "public.document", "public.document_change", "public.eval_run",
                "corpus.emb_openai_3l*", "serving.call_log", "serving.lookup_cache")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def split_file(src: Path, out_dir: Path, part_bytes: int = PART_BYTES) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    with src.open("rb") as f:
        index = 0
        while data := f.read(part_bytes):
            part = out_dir / f"{src.name}.part{index:02d}"
            part.write_bytes(data)
            parts.append(part)
            index += 1
    return parts


def build_manifest(parts: Sequence[Path], meta: Mapping) -> dict:
    return {"parts": [{"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)} for p in parts],
            **dict(meta)}


def verify_parts(directory: Path, manifest: Mapping) -> None:
    for part in manifest["parts"]:
        path = directory / part["name"]
        if not path.exists() or _sha256(path) != part["sha256"]:
            raise ValueError(f"checksum mismatch or missing part: {part['name']}; delete it and re-run setup")


def join_parts(directory: Path, manifest: Mapping, target: Path) -> Path:
    with target.open("wb") as out:
        for part in manifest["parts"]:
            with (directory / part["name"]).open("rb") as f:
                while block := f.read(CHUNK):
                    out.write(block)
    return target
```

Run: `uv run pytest tests/unit/serving/test_dump.py -v` → 2 PASS.

- [ ] **Step 3: Add `dump export` and `setup`**

Both drive `pg_dump`/`pg_restore` inside the `db` container of `docker-compose.yml`, so the host needs no Postgres client.

```python
import json
import subprocess
import time
from datetime import UTC, datetime

from swiss_grounding.serving.db import apply_serving_schema
from swiss_grounding.serving.dump import (
    EXCLUDE_DATA, MANIFEST_NAME, build_manifest, join_parts, split_file, verify_parts,
)

dump_app = typer.Typer(help="Prebuilt database dump.")
DB_ARGS = ["-U", "swiss", "-d", "swiss_grounding"]
DUMP_DIR = Path("data/dump")


def _compose(*args: str, stdout=None) -> None:
    subprocess.run(["docker", "compose", *args], check=True, stdout=stdout)


@dump_app.command("export")
def dump_export_cmd(out: Path = typer.Option(Path("dist"), "--out"),
                    openai: bool = typer.Option(False, "--openai", help="also export the OpenAI vectors")) -> None:
    """Write the default dump (no OpenAI vectors) split into release-sized parts, plus a manifest."""
    out.mkdir(parents=True, exist_ok=True)
    excludes = [f"--exclude-table-data={t}" for t in EXCLUDE_DATA]
    with (out / "corpus.dump").open("wb") as f:
        _compose("exec", "-T", "db", "pg_dump", *DB_ARGS, "-Fc", "-Z", "6", *excludes, stdout=f)
    parts = split_file(out / "corpus.dump", out)
    (out / "corpus.dump").unlink()
    manifest = build_manifest(parts, meta={"created_at": datetime.now(UTC).isoformat(), "kind": "default"})
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))
    if openai:
        with (out / "openai.dump").open("wb") as f:
            _compose("exec", "-T", "db", "pg_dump", *DB_ARGS, "-Fc", "--data-only", "-t", "corpus.emb_openai_3l*",
                     stdout=f)
    typer.echo(f"{len(parts)} parts and {MANIFEST_NAME} in {out}; upload them to the 'corpus-latest' release")


def _download(client: httpx.Client, url: str, target: Path) -> None:
    with client.stream("GET", url) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for block in r.iter_bytes():
                f.write(block)

```

Add `setup` as a top-level command, registered on the main app with `app.command("setup")(setup_cmd)` in `main.py`:

```python
def setup_cmd(skip_models: bool = typer.Option(False, "--skip-models", help="do not pre-download models")) -> None:
    """Download the prebuilt database, verify it, restore it, and pre-download the local models."""
    settings = load_settings()
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        manifest = client.get(f"{settings.dump_release_url}/{MANIFEST_NAME}").raise_for_status().json()
        for part in manifest["parts"]:
            target = DUMP_DIR / part["name"]
            if not target.exists() or target.stat().st_size != part["bytes"]:
                typer.echo(f"downloading {part['name']} ({part['bytes'] // 2**20} MiB)")
                _download(client, f"{settings.dump_release_url}/{part['name']}", target)
    verify_parts(DUMP_DIR, manifest)
    dump = join_parts(DUMP_DIR, manifest, DUMP_DIR / "corpus.dump")
    _compose("up", "-d", "--wait", "db")
    _compose("cp", str(dump), "db:/tmp/corpus.dump")
    _compose("exec", "-T", "db", "pg_restore", *DB_ARGS, "--clean", "--if-exists", "--no-owner", "-j", "4",
             "/tmp/corpus.dump")
    apply_serving_schema(settings.database_url)
    typer.echo(f"database restored and indexes rebuilt in {time.perf_counter() - started:.0f}s")
    if not skip_models:
        from swiss_grounding.app import build_query_provider, build_reranker
        build_query_provider(settings).embed(["warm up"])
        build_reranker(settings).score("warm up", ["warm up"])
        typer.echo("bge-m3 and the reranker are downloaded")
```

Register `dump_app` with `app.add_typer(dump_app, name="dump")`. `pg_restore` exits non-zero on warnings such as pre-existing extensions; if that happens on a clean volume, capture the message in the runbook and add `--exit-on-error` only if every warning is understood.

- [ ] **Step 4: Rehearse locally and commit**

Run `uv run swiss-grounding dump export --out dist`, then on a fresh volume (`docker compose down -v`) serve `dist/` with `python -m http.server 8765 -d dist` and run `DUMP_RELEASE_URL=http://localhost:8765 uv run swiss-grounding setup --skip-models`. Record part sizes and the restore time for the README.

```bash
git add src/swiss_grounding/serving/dump.py src/swiss_grounding/cli tests/unit/serving/test_dump.py
git commit -m "feat: prebuilt dump export and one-command setup (ADR 0017)"
```

---

### Task 27: README: declared scope, keyless setup, tools, robots switch, results

**Files:**
- Modify: `README.md`
- Create: `docs/SERVING-RUNBOOK.md`

- [ ] **Step 1: Rewrite the README top half** with these sections, in this order:
  1. *What it answers*: the output of `swiss_scope` verbatim (covered and not covered), and the five challenge samples with what the server does for each.
  2. *Setup (no API key)*: `docker compose up -d db`, `uv sync --extra embed`, `uv run swiss-grounding setup`, `uv run swiss-grounding serve`; MCP client config snippet (the one in `evals/judge/mcp.json`).
  3. *Tools*: the six tools with one line each (from their docstrings).
  4. *How it ranks and when it abstains*: one paragraph each from ADR 0012 and ADR 0013.
  5. *Rebuilding the index*: the encoding runbook (`docs/ENCODING-RUNBOOK.md`), `RESPECT_ROBOTS=true` as the documented default switch, and the build scripts.
  6. *Evaluation*: paste the output of `eval golden --split holdout --record`, `eval recall`, `eval faithfulness`, and `serving stats` from the run you are submitting, with the date and git commit. Do not round up numbers or omit failing rows.
  Move the old quick start under a "Legacy pipeline" heading at the end.

- [ ] **Step 2: Write `docs/SERVING-RUNBOOK.md`**: the order of commands after encoding: `serving init` (apply schema), `serving calendar` + `corpus embed`, `lookups load-premiums`, `eval golden --split dev`, `eval label --confirm-spend`, `label-check`, `eval fit`, `eval golden --split holdout --record`, `eval generate --confirm-spend`, `eval recall`, `eval faithfulness`, `dump export`, upload release. Add the `serving init` command to `serving_commands.py`:

```python
@serving_app.command("init")
def init_cmd() -> None:
    """Create or update the serving schema (idempotent)."""
    apply_serving_schema(load_settings().database_url)
    typer.echo("serving schema ready")
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/SERVING-RUNBOOK.md src/swiss_grounding/cli/serving_commands.py
git commit -m "docs: README declares scope, keyless setup, tools and evaluation; serving runbook"
```

---

### Task 28: Validate this plan's claims against the encoded corpus

Run every check below on the real corpus before Task 25 and again before submitting. Each check has a pass rule. When one fails, fix the named value or ADR, record the measured number in `docs/RESEARCH.md` (new section H3, dated), and re-run the check.

- [ ] **1. Volume.** `select language, count(*) from corpus.chunk where status='current' group by 1;` and the same per `corpus.source.level`. *Pass:* every declared canton and city has chunks; rm > 0.
- [ ] **2. Holiday and waste pages exist** for each declared canton and city: `select s.id, count(*) from corpus.document d join corpus.source s on s.id=d.source_id where d.status='current' and (d.url ilike any (array['%ferien%','%vacances%','%vacanze%','%vacanzas%','%abfall%','%dechets%','%déchets%','%rifiuti%','%entsorgung%'])) group by 1;` *Pass:* ≥ 1 per declared city/canton; otherwise add URLs to the manifest (ADR 0014 consequence).
- [ ] **3. Cross-language reranker bias on real text.** Pick 20 Fedlex articles present in de/fr/it; score a German question against each language version with both rerankers. *Pass:* the German version scores highest in ≥ 18/20 for bge-reranker-v2-m3 (confirms grouping is needed). Record the mmarco numbers too.
- [ ] **4. Reranker latency** for 30 real candidates (`serving stats` after 20 `serving ask` calls), MPS and `RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` on CPU. *Pass:* p95 ≤ 4 s for search. Otherwise lower `RERANK_CANDIDATES` to 20 or `RERANKER_MAX_TOKENS` to 256 and re-measure.
- [ ] **5. Provisional threshold.** `eval golden --split dev` with thresholds 0.05, 0.10, 0.20 (edit `PROVISIONAL_THRESHOLD`). *Pass:* keep the value with the best status accuracy; commit it.
- [ ] **6. Local quota.** For the 30 municipal golden probes, count citations whose extent is the city. *Pass:* ≥ 1 in the top 5 for ≥ 80% of them; otherwise raise `LOCAL_CANDIDATE_QUOTA`.
- [ ] **7. Fedlex eIds of suffixed articles** (`select distinct anchor from corpus.chunk where anchor ~ '^art_[0-9]+_?[a-z]'` limit 20). *Pass:* `_article_eid` in Task 14 produces the same spelling.
- [ ] **8. Language detection** on the golden questions: `detect_language(p.question) == p.language`. *Pass:* ≥ 95%; add function words for the misses.
- [ ] **9. Konstanz without a place.** From `eval faithfulness` records, count how often each model passed `locations` for place-naming questions. Report it in the README evaluation section whatever the result (ADR 0013 accepted this risk).
- [ ] **10. Dump.** Size of each part and restore time on a clean volume. *Pass:* every part < 2 GiB; restore time written in the README.
- [ ] **11. Thresholds of ADR 0016** on holdout after `eval fit`. *Pass:* all five pass. If one fails, the README says which and by how much; no threshold is lowered to make it pass.

```bash
git add docs/RESEARCH.md src/swiss_grounding/serving evals README.md
git commit -m "docs: validate serving-track claims against the encoded corpus"
```

---

## Self-review: decisions to tasks

| Decision | Task(s) |
|---|---|
| Keyless serving on bge-m3; OpenAI only with a key (ADR 0006) | 0, 19 |
| Every store searched as asked; optional translations (ADR 0011) | 6, 13, 19 |
| RRF candidates; reranker orders and abstains; group by translation group; reranker by hardware; logistic later (ADR 0012) | 5, 6, 7, 8, 9, 13, 22 |
| Corroboration share, n/a, English excluded, divergence flag | 7 |
| Status order; foreign and unresolved places; ask back only when the results differ by place (ADR 0013) | 4, 10, 13 |
| Three lookups; holidays and waste as documents (ADR 0014) | 15, 16, 17, 18, 28 (check 2) |
| Six tools; multi-place; get_document by reference and language; scope on no_evidence (ADR 0015) | 3, 13, 14, 19 |
| Golden set, generated questions, labels with human check, thresholds; `--record` only (ADR 0016) | 20, 21, 22, 23, 24, 25 |
| Prebuilt dump without OpenAI index; setup (ADR 0017) | 26, 27 |
| ef_search 100, relaxed iterative scan, local quota (RESEARCH §H2) | 0, 5, 6, 28 (check 6) |
| Latency logging (RAG S6) | 12, 19 |
| Small-to-big (RAG S3) | 14 |
| Description ablation (RAG S7) | Not in this plan: embed a text-only variant into a scratch table with the encoding track's `corpus embed` and compare with `eval golden`. Deferred until the golden set exists. |
