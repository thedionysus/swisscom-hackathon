# Encoding Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A manifest-driven, resumable, cost-capped pipeline that fetches the declared-scope Swiss sources in their original languages, chunks them by structure, links language versions, writes per-language descriptions and topics with OpenAI, OCRs scanned PDF pages, and embeds every chunk into two indexes — ready to run for real on 2026-09-24 when the API keys arrive.

**Architecture:** A new package `swiss_grounding/corpus/` and a new Postgres schema `corpus` beside the existing `public` tables (ADR 0010), so the current server keeps working until the serving track switches over. Stages are separate CLI commands that each persist their output and can be re-run: `fetch` → `ocr` → `describe` (documents, then chunks) → `embed` (OpenAI Batch, then local bge-m3) → `index`. Every paid stage estimates its cost first and refuses to exceed the budget ledger.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 16 + pgvector 0.8.6 (`halfvec`), `unaccent`, httpx, BeautifulSoup/lxml, pypdf, pypdfium2 + Pillow, OpenAI SDK (Batch API, chat completions, embeddings), Anthropic SDK (sync fallback), sentence-transformers (bge-m3), typer, pydantic, pytest.

---

## Decisions this plan implements (read before starting)

All of these were settled on 2026-09-23 and are recorded; do not re-open them while implementing.

| Decision | Where recorded |
|---|---|
| Primary index OpenAI `text-embedding-3-large` stored as `halfvec(3072)`; second index local `BAAI/bge-m3` `vector(1024)`; server answers from bge-m3 by default, keys needed only for ingestion | `docs/adr/0006-*.md` |
| 20 citizen topics with SR-number priors | `docs/adr/0007-*.md` |
| Cantonal law via official portals / opencaselaw is `cantonal_law` — **not in this plan's tier 1** (ADR 0009 moved it down) | `docs/adr/0008-*.md` |
| Declared scope: federal CH-wide, cantons ZH BE VD GE TI GR, cities Zürich Bern Lausanne Genève Lugano Chur Scuol | `docs/adr/0009-*.md` |
| One `corpus.chunk` table partitioned by language (de fr it en rm), per-language keyword config with accent folding, one embedding table per model | `docs/adr/0010-*.md` |
| Law chunk = article; an article over 1,800 chars is split into one chunk per paragraph (Abs.); Art./Abs./lit. labels stay in the text | this plan, Task 5 |
| Descriptions: document description per translation group with `gpt-5-mini`; chunk description per (translation group, aligned position) with `gpt-5-nano`; each written **in every language the group has** | `CONTEXT.md` (Chunk description) |
| Linked PDFs are ingested; scanned pages are OCR'd with `gpt-5-mini`, pilot of 10 pages first, separate **$10 sub-cap** | this plan, Task 16 |
| Budget cap **$100** for the whole run, enforced before every paid batch | this plan, Task 14 |
| robots.txt respected by default, switchable by `RESPECT_ROBOTS` | challenge rule; Task 9 |
| Calendars, premiums, transport, reference rate are **live lookups** (serving track), not encoded | `docs/adr/0009-*.md` |
| RAG review amendments E1–E5: bge-m3 sparse vectors as a multilingual keyword index (E1); repeated site furniture marked before describing (E2); descriptions and embeddings reused for unchanged chunks across versions (E3); bge-m3 sequence length 2,048 (E4); size and memory check before index builds (E5) | `docs/RAG-REVIEW.md`; Tasks 2, 11, 13, 17, 18, 21 |

Glossary for this plan (full definitions in `CONTEXT.md`): **language store** (a partition of `corpus.chunk`), **language version** (one document in one language), **translation group** (the versions of one document; key `translation_group_id`), **aligned chunk** (same `align_key` in another version of the group), **authentic version**, **document description**, **chunk description**, **breadcrumb**.

## Commands used throughout

```bash
uv run pytest tests/unit -q
DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration -q -m integration
uv run ruff check src tests
```

The integration suite creates and drops its own throwaway database (`tests/integration/conftest.py`), so pointing it at the dev server is safe. Commit messages: `<type>: <description>`, ending with the `Co-Authored-By` trailer the session's system reminder specifies.

## File structure

```
src/swiss_grounding/corpus/
  __init__.py
  schema.sql            corpus schema: sources, groups, documents, partitioned chunks, embedding tables, ledger, quarantine
  db.py                 apply the corpus schema
  topics.py             the 20 topics and the SR-number prior (ADR 0007)
  models.py             SourceSpec, ParsedSection, ParsedDocument, DiscoveredPdf, ConnectorResult, ChunkDraft, content_hash
  manifest.py           YAML manifest loading and validation
  chunker.py            structure-aware chunking
  artifacts.py          raw artifact storage on disk
  persist.py            write documents/chunks, versioning, supersede, fetch state, quarantine
  budget.py             prices, token estimate, spend ledger, cap enforcement
  providers.py          EmbeddingProvider / LLMProvider: OpenAI, local bge-m3, Anthropic, fakes
  runner.py             LlmTask/LlmOutcome, SyncRunner, OpenAI BatchRunner
  describe.py           document and chunk descriptions + topics
  ocr.py                OCR of scanned PDF pages
  embed.py              embedding text, OpenAI batch embeddings, local bge-m3 backfill, HNSW build
  fetch_stage.py        run connectors for a manifest, persist, quarantine
  connectors/
    __init__.py
    fedlex_akn.py       Akoma Ntoso → sections with breadcrumb, Abs./lit. labels
    fedlex.py           SPARQL, all languages, current + scheduled consolidation
    html_meta.py        hreflang alternates, canonical, dates, PDF links
    html.py             polite crawler with robots switch and new-first frontier
    pdf.py              text PDFs per page; scanned pages flagged and rendered for OCR
src/swiss_grounding/cli/corpus_commands.py   `swiss-grounding corpus ...`
manifests/declared-scope.yaml                the declared-scope source list
docs/ENCODING-RUNBOOK.md                     the step-by-step for 2026-09-24
tests/unit/corpus/...                        unit tests
tests/integration/test_corpus_*.py           integration tests
tests/fixtures/corpus/...                    fixtures
```

---

### Task 0: Branch, dependencies, settings, data directory

**Files:**
- Modify: `pyproject.toml`, `.gitignore`, `.env.example`, `src/swiss_grounding/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Create the branch**

```bash
git checkout -b feat/encoding-track
```

- [ ] **Step 2: Add dependencies**

```bash
uv add "openai>=1.60" "pypdfium2>=4.30" "pillow>=10.0"
```

Expected: `pyproject.toml` gains the three entries under `dependencies`; `uv.lock` updates. `sentence-transformers` stays in the `embed` extra.

- [ ] **Step 3: Ignore the data directory**

Append to `.gitignore`:

```
data/
```

- [ ] **Step 4: Write the failing settings test**

Append to `tests/unit/test_config.py`:

```python
def test_corpus_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    for key in ("OPENAI_API_KEY", "CORPUS_LLM_PROVIDER", "RESPECT_ROBOTS", "CORPUS_BUDGET_USD"):
        monkeypatch.delenv(key, raising=False)
    from swiss_grounding.config import Settings
    s = Settings(_env_file=None)
    assert s.corpus_llm_provider == "fake"
    assert s.corpus_doc_model == "gpt-5-mini"
    assert s.corpus_chunk_model == "gpt-5-nano"
    assert s.corpus_ocr_model == "gpt-5-mini"
    assert s.corpus_budget_usd == 100.0
    assert s.corpus_ocr_budget_usd == 10.0
    assert s.respect_robots is True
    assert s.data_dir == "data"


def test_openai_provider_needs_a_key(monkeypatch):
    import pytest
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from swiss_grounding.config import Settings
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, corpus_llm_provider="openai")
```

- [ ] **Step 5: Run it to see it fail**

Run: `uv run pytest tests/unit/test_config.py -q`
Expected: FAIL, `Settings` has no attribute `corpus_llm_provider`.

- [ ] **Step 6: Add the settings**

In `src/swiss_grounding/config.py`, add these fields to `Settings` after `user_agent`:

```python
    # Encoding track (corpus schema). Keys are needed only while ingesting (ADR 0006).
    openai_api_key: str | None = None
    corpus_llm_provider: Literal["openai", "anthropic", "fake"] = "fake"
    corpus_doc_model: str = "gpt-5-mini"
    corpus_chunk_model: str = "gpt-5-nano"
    corpus_ocr_model: str = "gpt-5-mini"
    corpus_anthropic_model: str = "claude-haiku-4-5-20251001"
    corpus_budget_usd: float = 100.0
    corpus_ocr_budget_usd: float = 10.0
    respect_robots: bool = True
    data_dir: str = "data"
```

and add a second validator below `_anthropic_needs_key`:

```python
    @model_validator(mode="after")
    def _corpus_provider_needs_key(self) -> "Settings":
        if self.corpus_llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when CORPUS_LLM_PROVIDER=openai")
        if self.corpus_llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when CORPUS_LLM_PROVIDER=anthropic")
        return self
```

Append to `.env.example`:

```
# Encoding track. OpenAI key is needed only while ingesting.
# OPENAI_API_KEY=
CORPUS_LLM_PROVIDER=fake
CORPUS_BUDGET_USD=100
CORPUS_OCR_BUDGET_USD=10
RESPECT_ROBOTS=true
DATA_DIR=data
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/unit/test_config.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .gitignore .env.example src/swiss_grounding/config.py tests/unit/test_config.py
git commit -m "chore: add encoding-track dependencies and settings"
```

---

### Task 1: The twenty topics and the SR prior

**Files:**
- Create: `src/swiss_grounding/corpus/__init__.py` (empty), `src/swiss_grounding/corpus/topics.py`
- Test: `tests/unit/corpus/__init__.py` (empty), `tests/unit/corpus/test_topics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_topics.py
import pytest

from swiss_grounding.corpus.topics import TOPIC_IDS, TOPICS, sr_prior


def test_twenty_topics_with_unique_ids():
    assert len(TOPICS) == 20
    assert len(TOPIC_IDS) == 20


@pytest.mark.parametrize("sr,article,expected", [
    ("220", 336, ("work",)),
    ("220", 270, ("housing",)),
    ("220", 1, ("business",)),
    ("220", None, ("business",)),
    ("832.10", None, ("health",)),
    ("831.10", None, ("social_security",)),
    ("814.600", None, ("waste",)),
    ("814.01", None, ("environment",)),
    ("142.20", None, ("residence",)),
    ("143.1", None, ("travel",)),
    ("161.1", None, ("politics",)),
    ("741.51", None, ("transport",)),
    ("455", None, ("animals",)),
    ("922.0", None, ("animals",)),
    ("921.0", None, ("environment",)),
    ("704", None, ("outdoors",)),
    ("211.412.11", None, ("building",)),
    ("210", None, ("family",)),
    ("999.9", None, ()),
])
def test_sr_prior_uses_the_longest_matching_prefix(sr, article, expected):
    assert sr_prior(sr, article) == expected
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/unit/corpus/test_topics.py -q`
Expected: FAIL, `ModuleNotFoundError: swiss_grounding.corpus`.

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/corpus/topics.py
"""The twenty citizen-facing topics (ADR 0007) and the SR-number prior for federal law."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    covers: str


TOPICS: tuple[Topic, ...] = (
    Topic("work", "Work and employment", "Employment contracts, notice and termination, working hours, holidays, wages, unemployment"),
    Topic("social_security", "Social security and pensions", "AHV/IV, pension funds, family allowances, social assistance, disability"),
    Topic("health", "Health and health insurance", "Compulsory health insurance, premiums and subsidies, doctors, hospitals, medicines, vaccinations, emergencies"),
    Topic("taxes", "Taxes", "Income, wealth, municipal and church tax, VAT, tax returns, deductions"),
    Topic("housing", "Housing and renting", "Renting, rent increases, deposits, tenancy disputes, home ownership"),
    Topic("building", "Building and land use", "Building permits, zoning, spatial planning, renovation, land register"),
    Topic("family", "Family and civil status", "Marriage, partnership, divorce, children, child support, names, inheritance, death"),
    Topic("residence", "Residence, migration and citizenship", "Permits, foreign nationals, asylum, naturalisation, registering a move"),
    Topic("politics", "Politics and voting", "Elections, popular votes, initiatives, political rights, authorities and their powers"),
    Topic("justice", "Justice, courts and criminal law", "Criminal law, fines, legal proceedings, debt collection, legal aid"),
    Topic("safety", "Public safety, police and civil protection", "Police, fire, civil protection, military service, weapons, public order, noise rules"),
    Topic("education", "Education and schools", "Compulsory school, school holidays, vocational training, universities, scholarships"),
    Topic("transport", "Transport, vehicles and parking", "Road traffic rules, driving licences, vehicles, parking and blue zones, public transport, cycling"),
    Topic("travel", "Travel, customs and borders", "Customs allowances, importing goods, identity documents, travelling abroad"),
    Topic("environment", "Environment, energy and nature", "Environmental protection, noise, water, forests, nature protection, energy"),
    Topic("animals", "Animals and pets", "Dog keeping and dog tax, leash rules, animal welfare, livestock, hunting and fishing"),
    Topic("waste", "Waste and recycling", "Collection days, fees, bulky and special waste, recycling points"),
    Topic("outdoors", "Leisure, sport and outdoors", "Hiking trails, mountains, sport, culture, public spaces and parks"),
    Topic("business", "Business and consumers", "Starting a company, commercial register, trades licences, consumer rights, contracts of sale"),
    Topic("municipal_services", "Municipal services and administration", "Opening hours, registration office, public holidays, municipal fees, documents and certificates"),
)
TOPIC_IDS: frozenset[str] = frozenset(t.id for t in TOPICS)

# (SR prefix, article range or None, topic). The longest matching prefix wins; among entries
# with that prefix, a range that contains the article wins over the open entry.
_SR_PRIORS: tuple[tuple[str, tuple[int, int] | None, str], ...] = (
    ("1", None, "politics"), ("14", None, "residence"), ("143", None, "travel"),
    ("210", None, "family"), ("211", None, "family"), ("211.4", None, "building"),
    ("22", None, "business"), ("220", None, "business"),
    ("220", (319, 362), "work"), ("220", (253, 274), "housing"),
    ("27", None, "justice"), ("28", None, "justice"), ("3", None, "justice"),
    ("41", None, "education"), ("415", None, "outdoors"),
    ("451", None, "environment"), ("455", None, "animals"),
    ("5", None, "safety"), ("514", None, "safety"),
    ("631", None, "travel"), ("64", None, "taxes"),
    ("700", None, "building"), ("704", None, "outdoors"),
    ("72", None, "transport"), ("73", None, "environment"), ("74", None, "transport"), ("76", None, "transport"),
    ("81", None, "health"), ("814", None, "environment"), ("814.6", None, "waste"),
    ("822", None, "work"), ("83", None, "social_security"), ("832", None, "health"),
    ("837", None, "work"), ("842", None, "housing"), ("85", None, "social_security"),
    ("916", None, "animals"), ("92", None, "environment"), ("922", None, "animals"), ("923", None, "animals"),
    ("94", None, "business"), ("95", None, "business"),
)


def sr_prior(sr: str, article: int | None = None) -> tuple[str, ...]:
    """The starting topic for an act's article, or () when no prior applies."""
    matches = [entry for entry in _SR_PRIORS if sr.startswith(entry[0])]
    if not matches:
        return ()
    longest = max(len(prefix) for prefix, _, _ in matches)
    best = [entry for entry in matches if len(entry[0]) == longest]
    if article is not None:
        for _, span, topic in best:
            if span is not None and span[0] <= article <= span[1]:
                return (topic,)
    for _, span, topic in best:
        if span is None:
            return (topic,)
    return ()
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/corpus/test_topics.py -q`
Expected: PASS (19 parametrised cases + 1).

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus tests/unit/corpus
git commit -m "feat: twenty citizen topics and SR-number prior (ADR 0007)"
```

---

### Task 2: The corpus schema

**Files:**
- Create: `src/swiss_grounding/corpus/schema.sql`, `src/swiss_grounding/corpus/db.py`
- Modify: `tests/integration/conftest.py` (add the `corpus_db` fixture)
- Test: `tests/integration/test_corpus_schema.py`

- [ ] **Step 1: Write the schema**

```sql
-- src/swiss_grounding/corpus/schema.sql
-- The corpus schema (ADR 0010). Idempotent: `corpus init` runs it on every call.
create extension if not exists vector;
create extension if not exists unaccent;
create schema if not exists corpus;

-- One keyword configuration per language store, each folding accents.
do $$
declare cfg record;
begin
  for cfg in select * from (values
      ('sg_german', 'german', 'german_stem'),
      ('sg_french', 'french', 'french_stem'),
      ('sg_italian', 'italian', 'italian_stem'),
      ('sg_english', 'english', 'english_stem'),
      ('sg_simple', 'simple', 'simple')) as t(name, copy_of, stem)
  loop
    if not exists (select 1 from pg_ts_config where cfgname = cfg.name) then
      execute format('create text search configuration public.%I (copy = pg_catalog.%I)', cfg.name, cfg.copy_of);
      execute format('alter text search configuration public.%I alter mapping for hword, hword_part, word with unaccent, %I',
                     cfg.name, cfg.stem);
    end if;
  end loop;
end $$;

create or replace function corpus.ts_config(lang text) returns regconfig
language sql immutable as $$
  select (case lang when 'de' then 'sg_german' when 'fr' then 'sg_french' when 'it' then 'sg_italian'
                    when 'en' then 'sg_english' else 'sg_simple' end)::regconfig
$$;

-- Breadcrumb weighs most, then the description, then the text (weights A, B, C).
create or replace function corpus.chunk_tsv(lang text, crumbs text[], description text, body text) returns tsvector
language sql immutable as $$
  select setweight(to_tsvector(corpus.ts_config(lang), coalesce(array_to_string(crumbs, ' '), '')), 'A')
      || setweight(to_tsvector(corpus.ts_config(lang), coalesce(description, '')), 'B')
      || setweight(to_tsvector(corpus.ts_config(lang), coalesce(body, '')), 'C')
$$;

create table if not exists corpus.source (
  id          text primary key,
  name        text not null,
  publisher   text not null,
  authority   text not null check (authority in
                ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
  level       text not null check (level in ('federal','cantonal','municipal')),
  extent_id   text not null references public.location(id),
  connector   text not null check (connector in ('fedlex','html')),
  tier        integer not null,
  languages   text[] not null,
  config      jsonb not null default '{}'
);

create table if not exists corpus.translation_group (
  id                   text primary key,
  work_key             text not null unique,
  description_by_lang  jsonb not null default '{}',
  topics               text[] not null default '{}'
);

create table if not exists corpus.document (
  id                    bigserial primary key,
  source_id             text not null references corpus.source(id),
  url                   text not null,
  language              text not null check (language in ('de','fr','it','en','rm')),
  translation_group_id  text not null references corpus.translation_group(id),
  title                 text not null,
  identifier            text,
  publisher             text not null,
  authority             text not null,
  extent_id             text not null references public.location(id),
  is_authentic          boolean not null default true,
  valid_from            date,
  valid_to              date,
  status                text not null check (status in ('current','scheduled','superseded','withdrawn')),
  published_at          date,
  modified_at           date,
  fetched_at            timestamptz not null,
  last_seen_at          timestamptz not null,
  content_hash          text not null,
  extraction            text not null default 'native' check (extraction in ('native','pdf_text','ocr')),
  retrieved_via         text,
  artifact_path         text,
  superseded_by         bigint references corpus.document(id)
);
create unique index if not exists document_live_url on corpus.document(url) where status in ('current','scheduled');
create index if not exists document_group_idx on corpus.document(translation_group_id, language, status);

create sequence if not exists corpus.chunk_id_seq;
create table if not exists corpus.chunk (
  id                    bigint not null default nextval('corpus.chunk_id_seq'),
  document_id           bigint not null references corpus.document(id) on delete cascade,
  language              text not null,
  translation_group_id  text not null,
  align_key             text not null,
  ordinal               integer not null,
  breadcrumb            text[] not null,
  anchor                text,
  text                  text not null,
  description           text not null default '',
  topics                text[] not null default '{}',
  extent_id             text not null,
  authority             text not null,
  status                text not null check (status in ('current','scheduled','superseded','withdrawn','boilerplate')),
  chunk_hash            text not null,
  needs_ocr             boolean not null default false,
  ocr_image             text,
  tsv                   tsvector generated always as (corpus.chunk_tsv(language, breadcrumb, description, text)) stored,
  primary key (id, language)
) partition by list (language);
alter sequence corpus.chunk_id_seq owned by corpus.chunk.id;

create table if not exists corpus.emb_openai_3l (
  chunk_id    bigint not null,
  language    text not null,
  text_hash   text not null,
  embedding   halfvec(3072) not null,
  primary key (chunk_id, language),
  foreign key (chunk_id, language) references corpus.chunk(id, language) on delete cascade
) partition by list (language);

create table if not exists corpus.emb_bge_m3 (
  chunk_id    bigint not null,
  language    text not null,
  text_hash   text not null,
  embedding   vector(1024) not null,
  -- bge-m3's learned sparse (lexical-weight) vector over its multilingual vocabulary (RAG review E1).
  -- Null when the dense-only fallback embedded the chunk. At most 1,000 non-zero entries (HNSW limit).
  sparse      sparsevec(250002),
  primary key (chunk_id, language),
  foreign key (chunk_id, language) references corpus.chunk(id, language) on delete cascade
) partition by list (language);

do $$
declare lang text;
begin
  foreach lang in array array['de','fr','it','en','rm'] loop
    execute format('create table if not exists corpus.chunk_%s partition of corpus.chunk for values in (%L)', lang, lang);
    execute format('create table if not exists corpus.emb_openai_3l_%s partition of corpus.emb_openai_3l for values in (%L)', lang, lang);
    execute format('create table if not exists corpus.emb_bge_m3_%s partition of corpus.emb_bge_m3 for values in (%L)', lang, lang);
  end loop;
end $$;

create index if not exists chunk_tsv_idx on corpus.chunk using gin (tsv);
create index if not exists chunk_align_idx on corpus.chunk (translation_group_id, align_key);
create index if not exists chunk_extent_idx on corpus.chunk (extent_id, status);
create index if not exists chunk_document_idx on corpus.chunk (document_id);

create table if not exists corpus.embedding_index (
  name        text primary key,
  provider    text not null,
  model       text not null,
  dim         integer not null,
  storage     text not null,
  created_at  timestamptz not null default now()
);
insert into corpus.embedding_index (name, provider, model, dim, storage) values
  ('openai-3l', 'openai', 'text-embedding-3-large', 3072, 'halfvec'),
  ('bge-m3', 'local', 'BAAI/bge-m3', 1024, 'vector')
on conflict (name) do nothing;

create table if not exists corpus.fetch_state (
  url            text primary key,
  source_id      text not null references corpus.source(id),
  etag           text,
  last_modified  text,
  content_hash   text not null,
  last_seen_at   timestamptz not null default now()
);

create table if not exists corpus.quarantine (
  id         bigserial primary key,
  source_id  text not null,
  url        text not null,
  stage      text not null,
  reason     text not null,
  attempts   integer not null default 1,
  first_at   timestamptz not null default now(),
  last_at    timestamptz not null default now(),
  unique (source_id, url, stage)
);

create table if not exists corpus.llm_spend (
  id             bigserial primary key,
  kind           text not null,
  model          text not null,
  usd            numeric not null,
  input_tokens   bigint not null default 0,
  output_tokens  bigint not null default 0,
  estimated      boolean not null,
  recorded_at    timestamptz not null default now()
);

create table if not exists corpus.batch_job (
  id             text primary key,
  kind           text not null,
  endpoint       text not null,
  status         text not null,
  request_count  integer not null,
  input_path     text not null,
  estimated_usd  numeric not null,
  created_at     timestamptz not null default now(),
  ingested_at    timestamptz
);
```

- [ ] **Step 2: Write `db.py`**

```python
# src/swiss_grounding/corpus/db.py
from importlib import resources

from swiss_grounding.db.connection import connect


def corpus_schema_sql() -> str:
    return resources.files("swiss_grounding.corpus").joinpath("schema.sql").read_text()


def apply_corpus_schema(database_url: str) -> None:
    """Create or bring up to date the corpus schema. Needs `public.location` to exist."""
    with connect(database_url) as conn:
        conn.execute(corpus_schema_sql())
```

- [ ] **Step 3: Add the `corpus_db` fixture**

Append to `tests/integration/conftest.py`:

```python
CORPUS_TABLES = (
    "corpus.emb_openai_3l, corpus.emb_bge_m3, corpus.chunk, corpus.document, corpus.translation_group, "
    "corpus.fetch_state, corpus.quarantine, corpus.llm_spend, corpus.batch_job, corpus.source"
)


@pytest.fixture
def corpus_db() -> str:
    """A database with the public schema, the location tree, and an empty corpus schema."""
    from swiss_grounding.corpus.db import apply_corpus_schema
    from swiss_grounding.db.connection import connect
    from swiss_grounding.db.migrate import apply_schema
    from swiss_grounding.locations.repository import upsert_locations
    from swiss_grounding.locations.seed import seed_locations

    url = os.environ["DATABASE_URL"]
    apply_schema(url, 8)
    apply_corpus_schema(url)
    with connect(url) as conn:
        if conn.execute("select count(*) as n from location").fetchone()["n"] == 0:
            upsert_locations(conn, seed_locations())
        conn.execute(f"truncate {CORPUS_TABLES} restart identity cascade")
    return url
```

If `upsert_locations` or `seed_locations` has a different signature, read `tests/integration/test_persist.py` and copy its setup call instead.

- [ ] **Step 4: Write the failing integration test**

```python
# tests/integration/test_corpus_schema.py
import pytest

from swiss_grounding.corpus.db import apply_corpus_schema
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def _seed_one_chunk(conn, language: str, text: str) -> None:
    conn.execute("insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages) "
                 "values ('s', 'S', 'P', 'official_info', 'federal', 'CH', 'html', 1, '{de,fr}')")
    conn.execute("insert into corpus.translation_group (id, work_key) values ('g', 'k')")
    doc = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, publisher, authority, "
        "extent_id, status, fetched_at, last_seen_at, content_hash) values "
        "('s', 'https://x', %s, 'g', 'T', 'P', 'official_info', 'CH', 'current', now(), now(), 'h') returning id",
        (language,)).fetchone()["id"]
    conn.execute(
        "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, text, "
        "extent_id, authority, status, chunk_hash) values (%s, %s, 'g', 'a', 0, '{Hundegesetz}', %s, 'CH', "
        "'official_info', 'current', 'c')", (doc, language, text))


def test_schema_is_idempotent(corpus_db):
    apply_corpus_schema(corpus_db)
    apply_corpus_schema(corpus_db)


def test_language_partitions_exist(corpus_db):
    with connect(corpus_db) as conn:
        names = {r["relname"] for r in conn.execute(
            "select c.relname from pg_inherits i join pg_class c on c.oid = i.inhrelid "
            "join pg_class p on p.oid = i.inhparent where p.relname = 'chunk'").fetchall()}
    assert names == {"chunk_de", "chunk_fr", "chunk_it", "chunk_en", "chunk_rm"}


def test_german_keyword_index_stems_and_folds_accents(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "de", "Hunde müssen in Zürich an der Leine geführt werden.")
        hits = conn.execute(
            "select count(*) as n from corpus.chunk where language = 'de' "
            "and tsv @@ to_tsquery('sg_german', 'zurich & hund & leine')").fetchone()["n"]
    assert hits == 1


def test_breadcrumb_is_searchable(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "de", "Der Bundesrat erlässt Vorschriften.")
        hits = conn.execute("select count(*) as n from corpus.chunk "
                            "where tsv @@ to_tsquery('sg_german', 'hundegesetz')").fetchone()["n"]
    assert hits == 1


def test_description_update_refreshes_tsv(corpus_db):
    with connect(corpus_db) as conn:
        _seed_one_chunk(conn, "fr", "Le Conseil fédéral édicte des dispositions.")
        conn.execute("update corpus.chunk set description = 'Obligation de tenir les chiens en laisse'")
        hits = conn.execute("select count(*) as n from corpus.chunk "
                            "where tsv @@ to_tsquery('sg_french', 'laisse')").fetchone()["n"]
    assert hits == 1
```

- [ ] **Step 5: Run it to see it fail, then pass**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_corpus_schema.py -q`
Expected before Step 1–3: FAIL (module missing). After: PASS, 5 tests.

If `create text search configuration public.sg_simple (copy = pg_catalog.simple)` fails because the `simple` config's mapping names differ, replace the `alter mapping` for `sg_simple` with `alter mapping for hword, hword_part, word with unaccent, simple` (the dictionary is named `simple`) — the loop already does this; the check is that the test passes.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/schema.sql src/swiss_grounding/corpus/db.py tests/integration/conftest.py tests/integration/test_corpus_schema.py
git commit -m "feat: corpus schema with language-partitioned chunks and two embedding indexes (ADR 0010)"
```

---

### Task 3: Corpus models and the manifest

**Files:**
- Create: `src/swiss_grounding/corpus/models.py`, `src/swiss_grounding/corpus/manifest.py`
- Test: `tests/unit/corpus/test_manifest.py`, `tests/unit/corpus/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/corpus/test_models.py
from datetime import date

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, content_hash


def _doc(**kw):
    base = dict(source_id="s", url="https://x", language="de", work_key="k", title="Hundegesetz",
                sections=(ParsedSection(align_key="art_1", breadcrumb=("Hundegesetz", "Art. 1"), anchor="art_1",
                                        text="Zweck"),))
    base.update(kw)
    return ParsedDocument(**base)


def test_content_hash_changes_with_title_and_breadcrumb():
    a = content_hash(_doc())
    assert content_hash(_doc(title="Hundeverordnung")) != a
    changed = ParsedSection(align_key="art_1", breadcrumb=("Hundegesetz", "Art. 1 Zweck"), anchor="art_1", text="Zweck")
    assert content_hash(_doc(sections=(changed,))) != a


def test_content_hash_ignores_status_but_not_validity():
    a = content_hash(_doc())
    assert content_hash(_doc(status="scheduled")) == a
    assert content_hash(_doc(valid_from=date(2026, 1, 1))) != a
```

```python
# tests/unit/corpus/test_manifest.py
import pytest

from swiss_grounding.corpus.manifest import load_manifest, select_sources

MANIFEST = """
version: 1
sources:
  - id: fedlex
    name: Fedlex
    publisher: Federal Chancellery
    authority: federal_law
    level: federal
    extent_id: CH
    connector: fedlex
    tier: 1
    languages: [de, fr, it, en]
    config: {sr_numbers: ["220"]}
  - id: bern_city
    name: Stadt Bern
    publisher: Stadt Bern
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 2
    languages: [de, fr]
    config: {start_urls: ["https://www.bern.ch/"], allow_prefixes: ["https://www.bern.ch/"]}
"""


def test_loads_and_selects_by_tier(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    manifest = load_manifest(path)
    assert [s.id for s in select_sources(manifest, tier=1)] == ["fedlex"]
    assert [s.id for s in select_sources(manifest, tier=2)] == ["fedlex", "bern_city"]
    assert [s.id for s in select_sources(manifest, tier=2, source_ids=("bern_city",))] == ["bern_city"]


def test_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("id: bern_city", "id: fedlex"))
    with pytest.raises(ValueError, match="duplicate"):
        load_manifest(path)


def test_html_source_needs_start_urls(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace('start_urls: ["https://www.bern.ch/"], ', ""))
    with pytest.raises(ValueError, match="start_urls"):
        load_manifest(path)


def test_rejects_unknown_language(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST.replace("[de, fr]", "[de, xx]"))
    with pytest.raises(ValueError):
        load_manifest(path)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/unit/corpus/test_models.py tests/unit/corpus/test_manifest.py -q`
Expected: FAIL, modules missing.

- [ ] **Step 3: Implement `models.py`**

```python
# src/swiss_grounding/corpus/models.py
"""Value types that flow from connectors to persistence. None of them touches the database."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

Language = Literal["de", "fr", "it", "en", "rm"]
LANGUAGES: tuple[str, ...] = ("de", "fr", "it", "en", "rm")
DocStatus = Literal["current", "scheduled"]


@dataclass(frozen=True)
class SourceSpec:
    id: str
    name: str
    publisher: str
    authority: str
    level: str
    extent_id: str
    connector: str
    tier: int
    languages: tuple[str, ...]
    config: dict[str, Any] = field(default_factory=dict)
    retrieved_via: str | None = None


@dataclass(frozen=True)
class ParsedSection:
    """One structural unit: a law article, an HTML section, a PDF page.

    `align_key` is the position this section holds in its document's structure; for law it is
    the article's eId, which is the same in every language version, so aligned chunks share it.
    `paragraphs` holds (align_key, text) per paragraph for law articles, used to split long ones.
    """
    align_key: str
    breadcrumb: tuple[str, ...]
    anchor: str | None
    text: str
    paragraphs: tuple[tuple[str, str], ...] = ()
    needs_ocr: bool = False
    ocr_image: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    source_id: str
    url: str
    language: str
    work_key: str
    title: str
    sections: tuple[ParsedSection, ...]
    identifier: str | None = None
    is_authentic: bool = True
    valid_from: date | None = None
    valid_to: date | None = None
    status: DocStatus = "current"
    published_at: date | None = None
    modified_at: date | None = None
    extraction: str = "native"
    retrieved_via: str | None = None
    artifact_path: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class DiscoveredPdf:
    url: str
    language: str
    title_hint: str
    source_id: str


@dataclass(frozen=True)
class ConnectorResult:
    documents: tuple[ParsedDocument, ...] = ()
    unchanged_urls: tuple[str, ...] = ()
    gone_urls: tuple[str, ...] = ()
    errors: tuple[tuple[str, str], ...] = ()      # (url, reason)
    pdfs: tuple[DiscoveredPdf, ...] = ()


@dataclass(frozen=True)
class KnownState:
    etag: str | None
    last_modified: str | None
    content_hash: str


@dataclass(frozen=True)
class ChunkDraft:
    align_key: str
    ordinal: int
    breadcrumb: tuple[str, ...]
    anchor: str | None
    text: str
    needs_ocr: bool = False
    ocr_image: str | None = None


def content_hash(doc: ParsedDocument) -> str:
    """Hash of everything a reader sees: title, validity and every section.

    Status is excluded on purpose: a scheduled consolidation that comes into force changes status,
    not content, and persistence handles that as a status change rather than a new version.
    """
    payload = [doc.title, doc.valid_from.isoformat() if doc.valid_from else None,
               [[s.align_key, list(s.breadcrumb), s.text, s.ocr_image is not None] for s in doc.sections]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
```

- [ ] **Step 4: Implement `manifest.py`**

```python
# src/swiss_grounding/corpus/manifest.py
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from swiss_grounding.corpus.models import SourceSpec


class SourceEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    publisher: str
    authority: Literal["federal_law", "cantonal_law", "municipal_law", "official_info", "institutional"]
    level: Literal["federal", "cantonal", "municipal"]
    extent_id: str
    connector: Literal["fedlex", "html"]
    tier: int = Field(ge=1, le=3)
    languages: tuple[Literal["de", "fr", "it", "en", "rm"], ...] = Field(min_length=1)
    config: dict[str, Any] = {}
    retrieved_via: str | None = None

    @model_validator(mode="after")
    def _connector_config(self) -> "SourceEntry":
        if self.connector == "html":
            for key in ("start_urls", "allow_prefixes"):
                if not self.config.get(key):
                    raise ValueError(f"source {self.id}: html connector needs config.{key}")
        if self.connector == "fedlex" and not self.config.get("sr_numbers"):
            raise ValueError(f"source {self.id}: fedlex connector needs config.sr_numbers")
        return self

    def to_spec(self) -> SourceSpec:
        return SourceSpec(id=self.id, name=self.name, publisher=self.publisher, authority=self.authority,
                          level=self.level, extent_id=self.extent_id, connector=self.connector, tier=self.tier,
                          languages=tuple(self.languages), config=dict(self.config),
                          retrieved_via=self.retrieved_via)


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    sources: tuple[SourceEntry, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> "Manifest":
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source ids: {dupes}")
        return self


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(Path(path).read_text()))


def select_sources(manifest: Manifest, tier: int, source_ids: tuple[str, ...] = ()) -> tuple[SourceSpec, ...]:
    """Sources at or below `tier`, in manifest order; `source_ids` narrows further when given."""
    chosen = [s for s in manifest.sources if s.tier <= tier and (not source_ids or s.id in source_ids)]
    return tuple(s.to_spec() for s in chosen)
```

Pydantic raises `ValidationError`, which is a subclass of `ValueError`, so the `pytest.raises(ValueError)` checks hold.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/corpus -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/models.py src/swiss_grounding/corpus/manifest.py tests/unit/corpus
git commit -m "feat: corpus value types and source manifest"
```

---

### Task 4: Raw artifact storage

**Files:**
- Create: `src/swiss_grounding/corpus/artifacts.py`
- Test: `tests/unit/corpus/test_artifacts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_artifacts.py
from swiss_grounding.corpus.artifacts import save_artifact


def test_saves_under_source_with_stable_name(tmp_path):
    a = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<x/>", ".xml")
    b = save_artifact(tmp_path, "fedlex", "https://x/a.xml", b"<y/>", ".xml")
    assert a == b
    assert a.startswith(str(tmp_path / "raw" / "fedlex"))
    assert open(a, "rb").read() == b"<y/>"
```

- [ ] **Step 2: Run to fail** — `uv run pytest tests/unit/corpus/test_artifacts.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/corpus/artifacts.py
"""Raw fetched bytes kept on disk, so re-chunking and citation checks need no re-crawl (issue #12)."""
import hashlib
from pathlib import Path


def save_artifact(data_dir: Path | str, source_id: str, url: str, content: bytes, suffix: str) -> str:
    folder = Path(data_dir) / "raw" / source_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(url.encode()).hexdigest()[:24] + suffix)
    path.write_bytes(content)
    return str(path)
```

- [ ] **Step 4: Run to pass**, then **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/artifacts.py tests/unit/corpus/test_artifacts.py
git commit -m "feat: keep raw fetched artifacts on disk"
```

---

### Task 5: Structure-aware chunker

**Files:**
- Create: `src/swiss_grounding/corpus/chunker.py`
- Test: `tests/unit/corpus/test_chunker.py`

Rules: a section of ≤ 1,800 characters is one chunk. A longer section that has `paragraphs` (a law article) becomes one chunk per paragraph, each keyed by the paragraph's eId, so the split is the same in every language version. A longer section without paragraphs, or a single paragraph over 3,000 characters, is cut into windows of ≤ 1,800 characters at a sentence end with 150 characters of overlap, keyed `<align_key>#<n>`. A section flagged `needs_ocr` is one chunk with empty text.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_chunker.py
from swiss_grounding.corpus.chunker import HARD_MAX_CHARS, MAX_CHARS, chunk_document
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection

CRUMB = ("SR 220 Obligationenrecht", "Art. 336c Kündigung zur Unzeit")


def _doc(*sections):
    return ParsedDocument(source_id="s", url="u", language="de", work_key="k", title="OR", sections=sections)


def test_short_article_is_one_chunk():
    s = ParsedSection("art_336_c", CRUMB, "art_336_c", "1 Kurz.\n2 Auch kurz.",
                      paragraphs=(("art_336_c/para_1", "1 Kurz."), ("art_336_c/para_2", "2 Auch kurz.")))
    [chunk] = chunk_document(_doc(s))
    assert chunk.align_key == "art_336_c"
    assert chunk.text == "1 Kurz.\n2 Auch kurz."
    assert chunk.breadcrumb == CRUMB


def test_long_article_splits_per_paragraph_with_paragraph_keys():
    p1, p2 = "1 " + "A" * 1000 + ".", "2 " + "B" * 1000 + "."
    s = ParsedSection("art_336_c", CRUMB, "art_336_c", p1 + "\n" + p2,
                      paragraphs=(("art_336_c/para_1", p1), ("art_336_c/para_2", p2)))
    chunks = chunk_document(_doc(s))
    assert [c.align_key for c in chunks] == ["art_336_c/para_1", "art_336_c/para_2"]
    assert [c.ordinal for c in chunks] == [0, 1]
    assert chunks[0].text == p1
    assert all(c.anchor == "art_336_c" for c in chunks)


def test_long_prose_splits_into_overlapping_windows():
    text = " ".join(f"Satz {i} hat einige Wörter." for i in range(200))
    chunks = chunk_document(_doc(ParsedSection("de:3", ("Seite", "Abschnitt"), None, text)))
    assert len(chunks) > 1
    assert all(len(c.text) <= MAX_CHARS for c in chunks)
    assert [c.align_key for c in chunks] == [f"de:3#{i}" for i in range(len(chunks))]
    assert chunks[0].text[-100:] in text and chunks[1].text[:40] in chunks[0].text  # overlap


def test_huge_paragraph_is_windowed_under_its_own_key():
    big = "1 " + "Wort. " * 700
    s = ParsedSection("art_9", CRUMB, "art_9", big, paragraphs=(("art_9/para_1", big),))
    chunks = chunk_document(_doc(s))
    assert len(big) > HARD_MAX_CHARS
    assert chunks[0].align_key == "art_9/para_1#0"


def test_ocr_page_is_one_empty_chunk():
    s = ParsedSection("de:p2", ("Merkblatt", "p. 2"), "page=2", "", needs_ocr=True, ocr_image="/tmp/p2.png")
    [chunk] = chunk_document(_doc(s))
    assert chunk.needs_ocr and chunk.text == "" and chunk.ocr_image == "/tmp/p2.png"


def test_empty_sections_are_dropped():
    assert chunk_document(_doc(ParsedSection("de:0", ("T",), None, "   "))) == ()
```

- [ ] **Step 2: Run to fail** — `uv run pytest tests/unit/corpus/test_chunker.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/corpus/chunker.py
from swiss_grounding.corpus.models import ChunkDraft, ParsedDocument, ParsedSection

MAX_CHARS = 1800
HARD_MAX_CHARS = 3000
OVERLAP_CHARS = 150


def _windows(text: str) -> list[str]:
    """Cut `text` into pieces of at most MAX_CHARS, preferring a sentence end, overlapping by OVERLAP_CHARS."""
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut > start + MAX_CHARS // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return pieces


def _units(section: ParsedSection) -> list[tuple[str, str]]:
    """(align_key, text) units for one section, before numbering."""
    text = section.text.strip()
    if len(text) <= MAX_CHARS:
        return [(section.align_key, text)]
    if section.paragraphs:
        units: list[tuple[str, str]] = []
        for key, para in section.paragraphs:
            para = para.strip()
            if len(para) <= HARD_MAX_CHARS:
                units.append((key, para))
            else:
                units.extend((f"{key}#{i}", w) for i, w in enumerate(_windows(para)))
        return units
    return [(f"{section.align_key}#{i}", w) for i, w in enumerate(_windows(text))]


def chunk_document(doc: ParsedDocument) -> tuple[ChunkDraft, ...]:
    drafts: list[ChunkDraft] = []
    for section in doc.sections:
        if section.needs_ocr:
            drafts.append(ChunkDraft(align_key=section.align_key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                     anchor=section.anchor, text="", needs_ocr=True, ocr_image=section.ocr_image))
            continue
        for key, text in _units(section):
            if text:
                drafts.append(ChunkDraft(align_key=key, ordinal=len(drafts), breadcrumb=section.breadcrumb,
                                         anchor=section.anchor, text=text))
    return tuple(drafts)
```

- [ ] **Step 4: Run to pass** — `uv run pytest tests/unit/corpus/test_chunker.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/chunker.py tests/unit/corpus/test_chunker.py
git commit -m "feat: structure-aware chunker (article, paragraph, window)"
```

---

### Task 6: Akoma Ntoso parser with breadcrumb and Abs./lit. labels

**Files:**
- Create: `src/swiss_grounding/corpus/connectors/__init__.py` (empty), `src/swiss_grounding/corpus/connectors/fedlex_akn.py`
- Create: `tests/fixtures/corpus/akn_or.xml`
- Test: `tests/unit/corpus/test_fedlex_akn.py`

- [ ] **Step 1: Write the fixture**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="act">
    <preface><p><docTitle>Obligationenrecht</docTitle></p></preface>
    <body>
      <title eId="tit_10"><num>Zehnter Titel:</num><heading>Der Arbeitsvertrag</heading>
        <chapter eId="tit_10/chap_1"><num>Erster Abschnitt:</num><heading>Der Einzelarbeitsvertrag</heading>
          <article eId="art_336_c"><num>Art. 336<i>c</i></num><heading>Kündigung zur Unzeit<authorialNote><p>Fassung gemäss Ziff. I des BG vom 18. März 1988.</p></authorialNote></heading>
            <paragraph eId="art_336_c/para_1"><num>1</num><content><p>Nach Ablauf der Probezeit darf der Arbeitgeber das Arbeitsverhältnis nicht kündigen:</p>
              <blockList eId="art_336_c/para_1/lst_1">
                <item eId="art_336_c/para_1/lst_1/lit_a"><num>a.</num><p>während die andere Partei Militärdienst leistet;</p></item>
                <item eId="art_336_c/para_1/lst_1/lit_b"><num>b.</num><p>während der Arbeitnehmer ohne eigenes Verschulden durch Krankheit ganz oder teilweise an der Arbeitsleistung verhindert ist;</p></item>
              </blockList></content></paragraph>
            <paragraph eId="art_336_c/para_2"><num>2</num><content><p>Die Kündigung, die während einer der in Absatz 1 festgesetzten Sperrfristen erklärt wird, ist nichtig.</p></content></paragraph>
          </article>
        </chapter>
      </title>
      <article eId="art_1"><num>Art. 1</num><heading>Abschluss des Vertrages</heading>
        <paragraph eId="art_1/para_1"><content><p>Zum Abschlusse eines Vertrages ist die übereinstimmende gegenseitige Willensäusserung der Parteien erforderlich.</p></content></paragraph>
      </article>
    </body>
  </act>
</akomaNtoso>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/corpus/test_fedlex_akn.py
from pathlib import Path

from swiss_grounding.corpus.connectors.fedlex_akn import parse_akn

XML = (Path(__file__).parents[2] / "fixtures" / "corpus" / "akn_or.xml").read_text()


def _by_key(sections):
    return {s.align_key: s for s in sections}


def test_breadcrumb_carries_act_containers_and_article():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_336_c"]
    assert s.breadcrumb == ("SR 220 Obligationenrecht", "Zehnter Titel: Der Arbeitsvertrag",
                            "Erster Abschnitt: Der Einzelarbeitsvertrag", "Art. 336c Kündigung zur Unzeit")
    assert s.anchor == "art_336_c"


def test_paragraph_and_letter_labels_are_kept_and_footnotes_dropped():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_336_c"]
    assert s.text.startswith("1 Nach Ablauf der Probezeit")
    assert "\na. während die andere Partei" in s.text
    assert "\nb. während der Arbeitnehmer" in s.text
    assert "\n2 Die Kündigung" in s.text
    assert "Fassung gemäss" not in s.text and "Fassung gemäss" not in " ".join(s.breadcrumb)
    assert [k for k, _ in s.paragraphs] == ["art_336_c/para_1", "art_336_c/para_2"]


def test_top_level_article_has_only_the_act_above_it():
    s = _by_key(parse_akn(XML, act_title="Obligationenrecht", sr="220"))["art_1"]
    assert s.breadcrumb == ("SR 220 Obligationenrecht", "Art. 1 Abschluss des Vertrages")
    assert s.text.startswith("Zum Abschlusse eines Vertrages")
```

- [ ] **Step 3: Run to fail** — `uv run pytest tests/unit/corpus/test_fedlex_akn.py -q` → FAIL.

- [ ] **Step 4: Implement**

```python
# src/swiss_grounding/corpus/connectors/fedlex_akn.py
"""Akoma Ntoso (Fedlex) → one ParsedSection per article, with breadcrumb and paragraph/letter labels."""
from bs4 import BeautifulSoup, NavigableString, Tag

from swiss_grounding.corpus.models import ParsedSection

CONTAINERS = ("book", "part", "title", "chapter", "section", "subsection", "division")
LIST_ITEMS = ("item", "point")


def _flat(tag: Tag | None) -> str:
    return " ".join(tag.get_text("", strip=False).split()) if tag is not None else ""


def _label(element: Tag) -> str:
    num = _flat(element.find("num", recursive=False))
    heading = _flat(element.find("heading", recursive=False))
    return " ".join(part for part in (num, heading) if part)


def _containers_above(article: Tag) -> list[str]:
    labels: list[str] = []
    parent = article.parent
    while isinstance(parent, Tag):
        if parent.name in CONTAINERS:
            label = _label(parent)
            if label:
                labels.append(label)
        parent = parent.parent
    return list(reversed(labels))


def _render(block: Tag) -> str:
    """Text of a paragraph (or article body) keeping its number and one line per list item."""
    for item in block.find_all(LIST_ITEMS):
        item.insert_before(NavigableString("\n"))
    raw = block.get_text(" ", strip=False)
    lines = [" ".join(line.split()) for line in raw.split("\n")]
    return "\n".join(line for line in lines if line)


def parse_akn(xml: str, act_title: str, sr: str) -> tuple[ParsedSection, ...]:
    soup = BeautifulSoup(xml, "xml")
    for note in soup.find_all("authorialNote"):
        note.decompose()
    root_crumb = f"SR {sr} {act_title}".strip()
    sections: list[ParsedSection] = []
    for article in soup.find_all("article"):
        key = article.get("eId") or f"art_{len(sections)}"
        crumbs = (root_crumb, *_containers_above(article), _label(article))
        paragraphs: list[tuple[str, str]] = []
        for index, para in enumerate(article.find_all("paragraph", recursive=False), start=1):
            text = _render(para)
            if text:
                paragraphs.append((para.get("eId") or f"{key}/para_{index}", text))
        if paragraphs:
            body = "\n".join(text for _, text in paragraphs)
        else:
            body = "\n".join(t for t in (_render(c) for c in article.find_all("content")) if t)
        if body:
            sections.append(ParsedSection(align_key=key, breadcrumb=tuple(c for c in crumbs if c), anchor=key,
                                          text=body, paragraphs=tuple(paragraphs)))
    return tuple(sections)
```

Note on `_flat` for `num`: `Art. 336<i>c</i>` must become `Art. 336c`, which is why `get_text("")` joins without a separator.

- [ ] **Step 5: Run to pass** — `uv run pytest tests/unit/corpus/test_fedlex_akn.py -q` → PASS. If the `a.`/`b.` lines come out as `a. während …` only after a leading `1 Nach …` line, the assertion `"\na. während"` holds; if the paragraph `num` and `content` are joined with a double space, `" ".join(line.split())` collapses it.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/connectors tests/fixtures/corpus/akn_or.xml tests/unit/corpus/test_fedlex_akn.py
git commit -m "feat: Akoma Ntoso parser keeps Abs./lit. labels and chapter breadcrumb"
```

---

### Task 7: Fedlex connector — every language, current and scheduled

**Files:**
- Create: `src/swiss_grounding/corpus/connectors/fedlex.py`
- Test: `tests/unit/corpus/test_fedlex_connector.py`

Behaviour:
- For each SR number and each manifest language (`de fr it en`), one SPARQL query returns every consolidation that has not ended. In Python: **current** = latest with `dateApplicability ≤ today`; **scheduled** = earliest with `dateApplicability > today`. Fixes audit weakness 6 (future law served as current).
- Page URL `https://www.fedlex.admin.ch/eli/cc/<…>/<YYYYMMDD>/<lang>`; `work_key` = the abstract ELI URI (same for every language → one translation group).
- English: `is_authentic=False`; no English version is **not** an error.
- A URL already in `known` is `unchanged` without downloading.
- Raw XML saved with `save_artifact`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_fedlex_connector.py
import json
from datetime import date
from pathlib import Path

import httpx

from swiss_grounding.corpus.connectors.fedlex import FedlexConnector, choose_consolidations
from swiss_grounding.corpus.models import KnownState, SourceSpec

XML = (Path(__file__).parents[2] / "fixtures" / "corpus" / "akn_or.xml").read_text()
ABSTRACT = "https://fedlex.data.admin.ch/eli/cc/27/317_321_377"
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "en"),
                  config={"sr_numbers": ["220"]})


def _binding(applicability, file_url, title="Obligationenrecht"):
    return {"abstract": {"value": ABSTRACT}, "dateApplicability": {"value": applicability},
            "title": {"value": title}, "fileUrl": {"value": file_url}}


def _transport(bindings_by_lang):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = request.content.decode()
            lang = "en" if "ENG" in body else "de"
            return httpx.Response(200, json={"results": {"bindings": bindings_by_lang.get(lang, [])}})
        return httpx.Response(200, text=XML)
    return httpx.MockTransport(handler)


def test_choose_current_and_scheduled():
    rows = [
        {"applicability": date(2024, 1, 1)}, {"applicability": date(2025, 7, 1)}, {"applicability": date(2027, 1, 1)},
    ]
    current, scheduled = choose_consolidations(rows, today=date(2026, 9, 24))
    assert current["applicability"] == date(2025, 7, 1)
    assert scheduled["applicability"] == date(2027, 1, 1)


def test_fetches_current_and_scheduled_in_german_and_skips_missing_english(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de-2025.xml"), _binding("2027-01-01", "https://f/de-2027.xml")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors == ()
    by_status = {d.status: d for d in result.documents}
    assert set(by_status) == {"current", "scheduled"}
    current = by_status["current"]
    assert current.url == "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"
    assert current.work_key == ABSTRACT
    assert current.valid_from == date(2025, 7, 1)
    assert current.identifier == "SR 220"
    assert current.is_authentic is True
    assert any(s.align_key == "art_336_c" for s in current.sections)
    assert Path(current.artifact_path).exists()


def test_english_is_not_authentic(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de.xml")],
                "en": [_binding("2025-07-01", "https://f/en.xml", title="Code of Obligations")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    en = [d for d in connector.run(SPEC, known={}).documents if d.language == "en"]
    assert len(en) == 1 and en[0].is_authentic is False and en[0].title == "Code of Obligations"


def test_known_url_is_unchanged_without_download(tmp_path):
    bindings = {"de": [_binding("2025-07-01", "https://f/de.xml")]}
    connector = FedlexConnector(httpx.Client(transport=_transport(bindings)), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    url = "https://www.fedlex.admin.ch/eli/cc/27/317_321_377/20250701/de"
    result = connector.run(SPEC, known={url: KnownState(None, None, "h")})
    assert result.unchanged_urls == (url,)
    assert result.documents == ()


def test_missing_german_is_an_error(tmp_path):
    connector = FedlexConnector(httpx.Client(transport=_transport({})), today=lambda: date(2026, 9, 24),
                                data_dir=tmp_path, sleep=lambda s: None)
    result = connector.run(SPEC, known={})
    assert result.errors and "SR 220" in result.errors[0][1]
```

- [ ] **Step 2: Run to fail** — `uv run pytest tests/unit/corpus/test_fedlex_connector.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/corpus/connectors/fedlex.py
import time
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

import httpx

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.connectors.fedlex_akn import parse_akn
from swiss_grounding.corpus.models import ConnectorResult, KnownState, ParsedDocument, SourceSpec

ENDPOINT = "https://fedlex.data.admin.ch/sparqlendpoint"
LANGUAGE_URI = {
    "de": "http://publications.europa.eu/resource/authority/language/DEU",
    "fr": "http://publications.europa.eu/resource/authority/language/FRA",
    "it": "http://publications.europa.eu/resource/authority/language/ITA",
    "en": "http://publications.europa.eu/resource/authority/language/ENG",
}
XML_FORMAT_URI = "http://publications.europa.eu/resource/authority/file-type/XML"
OPTIONAL_LANGUAGES = frozenset({"en"})   # English exists for ~290 acts only; its absence is not an error
QUERY = """
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?abstract ?dateApplicability ?dateEndApplicability ?title ?fileUrl WHERE {
  ?abstract a jolux:ConsolidationAbstract ;
            jolux:classifiedByTaxonomyEntry ?entry .
  ?entry skos:notation ?sr .
  FILTER(str(?sr) = "%(sr)s")
  ?consolidation jolux:isMemberOf ?abstract ;
                 jolux:dateApplicability ?dateApplicability ;
                 jolux:isRealizedBy ?expr .
  OPTIONAL { ?consolidation jolux:dateEndApplicability ?dateEndApplicability }
  ?expr jolux:language <%(lang)s> ;
        jolux:isEmbodiedBy ?manif .
  OPTIONAL {
    ?abstract jolux:isRealizedBy ?abstractExpr .
    ?abstractExpr jolux:language <%(lang)s> ;
                  jolux:title ?title .
  }
  ?manif jolux:format <%(xml)s> ;
         jolux:isExemplifiedBy ?fileUrl .
  FILTER(!bound(?dateEndApplicability) || ?dateEndApplicability >= now())
}
"""
ATTEMPTS = 3


def choose_consolidations(rows: list[dict], today: date) -> tuple[dict | None, dict | None]:
    """(current, scheduled): latest already applicable, earliest not yet applicable."""
    past = [r for r in rows if r["applicability"] <= today]
    future = [r for r in rows if r["applicability"] > today]
    current = max(past, key=lambda r: r["applicability"]) if past else None
    scheduled = min(future, key=lambda r: r["applicability"]) if future else None
    return current, scheduled


def _page_url(abstract: str, applicability: date, lang: str) -> str:
    base = abstract.replace("https://fedlex.data.admin.ch", "https://www.fedlex.admin.ch")
    return f"{base}/{applicability:%Y%m%d}/{lang}"


class FedlexConnector:
    def __init__(self, http: httpx.Client, today: Callable[[], date], data_dir: Path | str,
                 sleep: Callable[[float], None] = time.sleep):
        self._http = http
        self._today = today
        self._data_dir = data_dir
        self._sleep = sleep

    def _with_retry[T](self, call: Callable[[], T]) -> T:
        for attempt in range(1, ATTEMPTS + 1):
            try:
                return call()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                transient = isinstance(exc, httpx.TransportError) or exc.response.status_code >= 500
                if attempt == ATTEMPTS or not transient:
                    raise
                self._sleep(attempt * 1.0)
        raise AssertionError("unreachable")

    def _rows(self, sr: str, lang: str) -> list[dict]:
        def call() -> list[dict]:
            response = self._http.post(
                ENDPOINT, data={"query": QUERY % {"sr": sr, "lang": LANGUAGE_URI[lang], "xml": XML_FORMAT_URI}},
                headers={"accept": "application/sparql-results+json"}, timeout=60)
            response.raise_for_status()
            return response.json()["results"]["bindings"]
        rows = []
        for b in self._with_retry(call):
            rows.append({
                "abstract": b["abstract"]["value"],
                "applicability": date.fromisoformat(b["dateApplicability"]["value"][:10]),
                "end": date.fromisoformat(b["dateEndApplicability"]["value"][:10]) if "dateEndApplicability" in b else None,
                "title": b.get("title", {}).get("value", ""),
                "file_url": b["fileUrl"]["value"],
            })
        return rows

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, errors = [], [], []
        today = self._today()
        for sr in spec.config["sr_numbers"]:
            for lang in spec.languages:
                if lang not in LANGUAGE_URI:
                    continue
                try:
                    rows = self._rows(sr, lang)
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}] SPARQL failed: {exc}"))
                    continue
                if not rows:
                    if lang not in OPTIONAL_LANGUAGES:
                        errors.append((f"SR {sr} [{lang}]", f"SR {sr} [{lang}]: no in-force consolidation found"))
                    continue
                for row, status in zip(choose_consolidations(rows, today), ("current", "scheduled"), strict=True):
                    if row is None:
                        continue
                    url = _page_url(row["abstract"], row["applicability"], lang)
                    if url in known:
                        unchanged.append(url)
                        continue
                    try:
                        xml = self._with_retry(lambda u=row["file_url"]: self._fetch_xml(u))
                    except httpx.HTTPError as exc:
                        errors.append((url, f"XML download failed: {exc}"))
                        continue
                    title = row["title"] or f"SR {sr}"
                    sections = parse_akn(xml, act_title=title, sr=sr)
                    if not sections:
                        errors.append((url, "no articles parsed"))
                        continue
                    documents.append(ParsedDocument(
                        source_id=spec.id, url=url, language=lang, work_key=row["abstract"], title=title,
                        sections=sections, identifier=f"SR {sr}", is_authentic=lang != "en",
                        valid_from=row["applicability"], valid_to=row["end"], status=status,
                        artifact_path=save_artifact(self._data_dir, spec.id, url, xml.encode(), ".xml")))
                self._sleep(0.5)
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))

    def _fetch_xml(self, url: str) -> str:
        response = self._http.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        return response.text
```

- [ ] **Step 4: Run to pass** — `uv run pytest tests/unit/corpus/test_fedlex_connector.py -q` → PASS.

- [ ] **Step 5: Live smoke check (free, one act)**

```bash
uv run python -c "
import httpx; from datetime import date
from swiss_grounding.corpus.connectors.fedlex import FedlexConnector
from swiss_grounding.corpus.models import SourceSpec
spec = SourceSpec('fedlex','F','Federal Chancellery','federal_law','federal','CH','fedlex',1,('de','fr','it','en'),{'sr_numbers':['220']})
r = FedlexConnector(httpx.Client(headers={'user-agent':'swiss-grounding/0.2'}), date.today, '/tmp/sg').run(spec, {})
for d in r.documents: print(d.language, d.status, d.valid_from, d.title[:40], len(d.sections))
print(r.errors)"
```

Expected: four `current` documents (de, fr, it, en), each with ~1,600 sections; `errors` empty. If English is missing for SR 220, that is acceptable.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/connectors/fedlex.py tests/unit/corpus/test_fedlex_connector.py
git commit -m "feat: Fedlex connector for all languages, current and scheduled consolidations"
```

---

### Task 8: HTML metadata — alternates, dates, PDF links

**Files:**
- Create: `src/swiss_grounding/corpus/connectors/html_meta.py`
- Test: `tests/unit/corpus/test_html_meta.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_html_meta.py
from datetime import date

from swiss_grounding.corpus.connectors.html_meta import page_meta, work_key

HTML = """<html lang="de"><head>
<link rel="canonical" href="https://www.ch.ch/de/hund/">
<link rel="alternate" hreflang="de" href="https://www.ch.ch/de/hund/">
<link rel="alternate" hreflang="fr-CH" href="/fr/chien/">
<link rel="alternate" hreflang="x-default" href="/">
<meta property="article:modified_time" content="2026-03-12T08:00:00+01:00">
</head><body><main><h1>Hund</h1><p>Stand: 01.02.2026</p>
<a href="/files/merkblatt.pdf">Merkblatt Hundehaltung</a><a href="https://other.org/x.pdf">x</a>
</main></body></html>"""


def test_alternates_are_absolute_and_skip_x_default():
    meta = page_meta(HTML, "https://www.ch.ch/de/hund/")
    assert meta.alternates == {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"}
    assert meta.canonical == "https://www.ch.ch/de/hund/"


def test_modified_date_from_meta():
    assert page_meta(HTML, "https://www.ch.ch/de/hund/").modified == date(2026, 3, 12)


def test_modified_date_from_stand_text_when_no_meta():
    html = HTML.replace('<meta property="article:modified_time" content="2026-03-12T08:00:00+01:00">', "")
    assert page_meta(html, "https://www.ch.ch/de/hund/").modified == date(2026, 2, 1)


def test_pdf_links_with_text():
    links = page_meta(HTML, "https://www.ch.ch/de/hund/").pdf_links
    assert ("https://www.ch.ch/files/merkblatt.pdf", "Merkblatt Hundehaltung") in links


def test_work_key_is_shared_by_language_versions():
    de = work_key("https://www.ch.ch/de/hund/", {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"})
    fr = work_key("https://www.ch.ch/fr/chien/", {"de": "https://www.ch.ch/de/hund/", "fr": "https://www.ch.ch/fr/chien/"})
    assert de == fr
    assert work_key("https://x.ch/a", {}) == "html:https://x.ch/a"
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/connectors/html_meta.py
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

DATE_META = ("article:modified_time", "dcterms.modified", "last-modified", "dc.date.modified",
             "article:published_time", "dcterms.date", "date", "dc.date")
STAND = re.compile(r"(?:Stand|Letzte Änderung|Aktualisiert|Mise à jour|Mis à jour le|Aggiornato|"
                   r"Ultimo aggiornamento)\s*:?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.IGNORECASE)


@dataclass(frozen=True)
class PageMeta:
    alternates: Mapping[str, str] = field(default_factory=dict)
    canonical: str | None = None
    published: date | None = None
    modified: date | None = None
    pdf_links: tuple[tuple[str, str], ...] = ()


def _absolute(base: str, href: str) -> str:
    return urldefrag(urljoin(base, href))[0]


def _iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def page_meta(html: str, url: str) -> PageMeta:
    soup = BeautifulSoup(html, "lxml")
    alternates: dict[str, str] = {}
    for link in soup.find_all("link", hreflang=True, href=True):
        rel = link.get("rel") or []
        lang = link["hreflang"].split("-")[0].lower()
        if "alternate" in rel and lang != "x" and len(lang) == 2:
            alternates.setdefault(lang, _absolute(url, link["href"]))
    canonical_tag = soup.find("link", rel="canonical", href=True)
    canonical = _absolute(url, canonical_tag["href"]) if canonical_tag else None

    found: dict[str, date] = {}
    for meta in soup.find_all("meta", content=True):
        name = (meta.get("property") or meta.get("name") or "").lower()
        if name in DATE_META and (parsed := _iso_date(meta["content"])):
            found.setdefault(name, parsed)
    modified = next((found[n] for n in DATE_META[:4] if n in found), None)
    published = next((found[n] for n in DATE_META[4:] if n in found), None)
    if modified is None:
        if match := STAND.search(soup.get_text(" ")):
            day, month, year = (int(g) for g in match.groups())
            try:
                modified = date(year, month, day)
            except ValueError:
                modified = None

    pdfs: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        target = _absolute(url, a["href"])
        if target.lower().split("?")[0].endswith(".pdf"):
            pdfs.setdefault(target, " ".join(a.get_text(" ").split()))
    return PageMeta(alternates=alternates, canonical=canonical, published=published, modified=modified,
                    pdf_links=tuple(pdfs.items()))


def work_key(url: str, alternates: Mapping[str, str]) -> str:
    """One key for all language versions of a page: the smallest URL among the page and its alternates.

    Assumes alternates are listed symmetrically, which hreflang requires. A site that lists them
    asymmetrically yields two groups for one page; that costs corroboration, never correctness.
    """
    members = sorted({urldefrag(url)[0], *alternates.values()})
    return "html:" + members[0]
```

- [ ] **Step 4: Run to pass**, **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/connectors/html_meta.py tests/unit/corpus/test_html_meta.py
git commit -m "feat: read hreflang alternates, page dates and PDF links from HTML"
```

---

### Task 9: HTML connector — polite crawl, robots switch, new-first frontier

**Files:**
- Create: `src/swiss_grounding/corpus/connectors/html.py`
- Test: `tests/unit/corpus/test_html_connector.py`

Behaviour:
- Config keys: `start_urls` (absolute), `allow_prefixes` (absolute URL prefixes), optional `max_pages` (default 300), `max_pdfs` (default 50), `pdf_allow_prefixes` (default `allow_prefixes`).
- `CrawlPolicy(respect_robots, delay_seconds)`. When `respect_robots` is false, robots.txt is not fetched at all.
- Frontier: newly discovered URLs are visited before known URLs are re-checked, so a site with many known pages still discovers new ones (audit weakness 14).
- Each page → `ParsedDocument` with `work_key` from alternates, dates from `page_meta`, sections from the existing `html_to_page`, breadcrumb = page title + heading path, `align_key = "<lang>:<i>"` (HTML versions are grouped but not aligned by position).
- Alternate-language URLs and allowed links are queued. PDF links under `pdf_allow_prefixes` are returned as `DiscoveredPdf` (at most `max_pdfs`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_html_connector.py
import httpx

from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector
from swiss_grounding.corpus.models import KnownState, SourceSpec

PAGES = {
    "https://www.x.ch/de/": """<html lang="de"><head><link rel="alternate" hreflang="fr" href="https://www.x.ch/fr/">
      </head><body><main><h1>Start</h1><p>Willkommen.</p><a href="/de/hund">Hund</a>
      <a href="/de/merkblatt.pdf">Merkblatt</a><a href="https://elsewhere.ch/">x</a></main></body></html>""",
    "https://www.x.ch/fr/": """<html lang="fr"><head><link rel="alternate" hreflang="de" href="https://www.x.ch/de/">
      </head><body><main><h1>Accueil</h1><p>Bienvenue.</p></main></body></html>""",
    "https://www.x.ch/de/hund": """<html lang="de"><body><main><h1>Hund</h1><h2>Leine</h2><p>Leinenpflicht im Wald.</p>
      </main></body></html>""",
}


def _spec(**config):
    base = {"start_urls": ["https://www.x.ch/de/"], "allow_prefixes": ["https://www.x.ch/de/", "https://www.x.ch/fr/"]}
    base.update(config)
    return SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de", "fr"), config=base)


def _client(robots="User-agent: *\nAllow: /\n", seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots)
        if url in PAGES:
            return httpx.Response(200, text=PAGES[url], headers={"content-type": "text/html", "etag": '"e1"'})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_crawls_pages_and_groups_language_versions():
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known={})
    by_url = {d.url: d for d in result.documents}
    assert set(by_url) == set(PAGES)
    assert by_url["https://www.x.ch/de/"].work_key == by_url["https://www.x.ch/fr/"].work_key
    hund = by_url["https://www.x.ch/de/hund"]
    assert hund.sections[0].breadcrumb == ("Hund", "Leine")
    assert hund.sections[0].align_key == "de:0"
    assert hund.etag == '"e1"'


def test_pdf_links_are_discovered_not_fetched():
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known={})
    assert [p.url for p in result.pdfs] == ["https://www.x.ch/de/merkblatt.pdf"]
    assert result.pdfs[0].title_hint == "Merkblatt"


def test_robots_disallow_is_respected_only_when_switched_on():
    robots = "User-agent: *\nDisallow: /de/hund\n"
    on = HtmlConnector(_client(robots), CrawlPolicy(True, 0)).run(_spec(), known={})
    off = HtmlConnector(_client(robots), CrawlPolicy(False, 0)).run(_spec(), known={})
    assert "https://www.x.ch/de/hund" not in {d.url for d in on.documents}
    assert "https://www.x.ch/de/hund" in {d.url for d in off.documents}


def test_robots_file_is_not_requested_when_switched_off():
    seen: list[str] = []
    HtmlConnector(_client(seen=seen), CrawlPolicy(False, 0)).run(_spec(), known={})
    assert not any(u.endswith("/robots.txt") for u in seen)


def test_new_pages_are_visited_before_known_ones_are_rechecked():
    known = {f"https://www.x.ch/de/old{i}": KnownState(None, None, "h") for i in range(5)}
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(max_pages=3), known=known)
    assert {d.url for d in result.documents} == set(PAGES)


def test_known_page_gone_is_reported():
    known = {"https://www.x.ch/de/old": KnownState(None, None, "h")}
    result = HtmlConnector(_client(), CrawlPolicy(True, 0)).run(_spec(), known=known)
    assert "https://www.x.ch/de/old" in result.gone_urls
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/connectors/html.py
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx

from swiss_grounding.corpus.connectors.html_meta import page_meta, work_key
from swiss_grounding.corpus.models import (
    LANGUAGES, ConnectorResult, DiscoveredPdf, KnownState, ParsedDocument, ParsedSection, SourceSpec,
)
from swiss_grounding.ingest.html_sections import extract_links, html_to_page

SKIP_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".json", ".ics", ".csv",
                 ".docx", ".doc", ".xlsx", ".xls", ".mp4", ".mp3")
DEFAULT_MAX_PAGES = 300
DEFAULT_MAX_PDFS = 50


@dataclass(frozen=True)
class CrawlPolicy:
    respect_robots: bool
    delay_seconds: float


class HtmlConnector:
    def __init__(self, http: httpx.Client, policy: CrawlPolicy, sleep: Callable[[float], None] = time.sleep):
        self._http = http
        self._policy = policy
        self._sleep = sleep
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}

    def _robots_allow(self, url: str) -> bool:
        if not self._policy.respect_robots:
            return True
        host = urlparse(url)
        root = f"{host.scheme}://{host.netloc}"
        if root not in self._robots:
            parser = robotparser.RobotFileParser()
            try:
                response = self._http.get(root + "/robots.txt", timeout=20)
                parser.parse(response.text.splitlines() if response.status_code == 200 else [])
            except httpx.HTTPError:
                parser.parse([])
            self._robots[root] = parser
        return self._robots[root].can_fetch("*", url)

    @staticmethod
    def _in_prefixes(url: str, prefixes: tuple[str, ...]) -> bool:
        return any(url.startswith(p) for p in prefixes)

    def _allowed(self, url: str, prefixes: tuple[str, ...]) -> bool:
        path = urlparse(url).path.lower()
        return (self._in_prefixes(url, prefixes) and not path.endswith(SKIP_SUFFIXES)
                and self._robots_allow(url))

    def run(self, spec: SourceSpec, known: Mapping[str, KnownState]) -> ConnectorResult:
        cfg = spec.config
        prefixes = tuple(cfg["allow_prefixes"])
        pdf_prefixes = tuple(cfg.get("pdf_allow_prefixes", prefixes))
        max_pages = int(cfg.get("max_pages", DEFAULT_MAX_PAGES))
        max_pdfs = int(cfg.get("max_pdfs", DEFAULT_MAX_PDFS))
        frontier = deque(cfg["start_urls"])
        revisit = deque(u for u in known if u not in cfg["start_urls"])
        seen: set[str] = set()
        documents, unchanged, gone, errors = [], [], [], []
        pdfs: dict[str, DiscoveredPdf] = {}
        pages = 0
        while (frontier or revisit) and pages < max_pages:
            url = frontier.popleft() if frontier else revisit.popleft()
            if url in seen or not self._allowed(url, prefixes):
                continue
            seen.add(url)
            pages += 1
            prior = known.get(url)
            headers = {}
            if prior and prior.etag:
                headers["if-none-match"] = prior.etag
            if prior and prior.last_modified:
                headers["if-modified-since"] = prior.last_modified
            try:
                response = self._http.get(url, headers=headers, follow_redirects=True, timeout=30)
            except httpx.HTTPError as exc:
                errors.append((url, f"fetch failed: {exc}"))
                continue
            finally:
                if self._policy.delay_seconds:
                    self._sleep(self._policy.delay_seconds)
            if response.status_code == 304:
                unchanged.append(url)
                continue
            if response.status_code in (404, 410):
                (gone if url in known else errors).append(url if url in known else (url, f"HTTP {response.status_code}"))
                continue
            if response.status_code >= 400:
                errors.append((url, f"HTTP {response.status_code}"))
                continue
            if "html" not in response.headers.get("content-type", "text/html").lower():
                continue
            html = response.text
            default_lang = spec.languages[0]
            page = html_to_page(html, url=url, default_language=default_lang)
            meta = page_meta(html, url)
            lang = page.language if page.language in LANGUAGES else default_lang
            for link in (*extract_links(html, base_url=url), *meta.alternates.values()):
                if link not in seen and self._in_prefixes(link, prefixes):
                    frontier.append(link)
            for pdf_url, text in meta.pdf_links:
                if len(pdfs) < max_pdfs and pdf_url not in pdfs and self._in_prefixes(pdf_url, pdf_prefixes):
                    pdfs[pdf_url] = DiscoveredPdf(url=pdf_url, language=lang, title_hint=text or page.title,
                                                  source_id=spec.id)
            if not page.sections:
                continue
            title = page.title or url
            sections = []
            for i, s in enumerate(page.sections):
                parts = [p for p in s.heading_path.split(" > ") if p]
                crumbs = tuple(parts) if parts and parts[0] == title else (title, *parts)
                sections.append(ParsedSection(align_key=f"{lang}:{i}", breadcrumb=crumbs, anchor=s.anchor, text=s.text))
            documents.append(ParsedDocument(
                source_id=spec.id, url=url, language=lang, work_key=work_key(url, meta.alternates), title=title,
                sections=tuple(sections), published_at=meta.published, modified_at=meta.modified,
                retrieved_via=spec.retrieved_via, etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified")))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), gone_urls=tuple(gone),
                               errors=tuple(errors), pdfs=tuple(pdfs.values()))
```

Replace the one-line `(gone if …)` in the 404 branch with the explicit form if ruff flags it:

```python
            if response.status_code in (404, 410):
                if url in known:
                    gone.append(url)
                else:
                    errors.append((url, f"HTTP {response.status_code}"))
                continue
```

- [ ] **Step 4: Run to pass** — `uv run pytest tests/unit/corpus/test_html_connector.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/connectors/html.py tests/unit/corpus/test_html_connector.py
git commit -m "feat: HTML connector with robots switch, new-first frontier and language grouping"
```

---

### Task 10: PDF connector — text pages, scanned pages flagged and rendered

**Files:**
- Create: `src/swiss_grounding/corpus/connectors/pdf.py`
- Test: `tests/unit/corpus/test_pdf_connector.py` (uses the existing `tests/fixtures/sample.pdf`)

A page whose extracted text is shorter than 80 characters is treated as scanned: it is rendered to PNG at 150 dpi under `data/ocr/<source>/`, and its section is `needs_ocr` with empty text.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_pdf_connector.py
from pathlib import Path

import httpx
from pypdf import PdfWriter

from swiss_grounding.corpus.connectors.pdf import PdfConnector, parse_pdf
from swiss_grounding.corpus.models import DiscoveredPdf, SourceSpec

SAMPLE = (Path(__file__).parents[2] / "fixtures" / "sample.pdf").read_bytes()
SPEC = SourceSpec(id="x", name="X", publisher="X", authority="official_info", level="municipal",
                  extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    from io import BytesIO
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def test_text_pdf_has_one_section_per_page(tmp_path):
    doc = parse_pdf(SAMPLE, url="https://x.ch/a.pdf", language="de", title_hint="Merkblatt", source_id="x",
                    artifact_path="a", ocr_dir=tmp_path)
    assert doc.extraction == "pdf_text"
    assert doc.sections and all(not s.needs_ocr for s in doc.sections if s.text)
    assert doc.sections[0].anchor == "page=1"
    assert doc.sections[0].breadcrumb[-1] == "p. 1"
    assert doc.work_key == "pdf:https://x.ch/a.pdf"


def test_blank_page_is_flagged_for_ocr_and_rendered(tmp_path):
    doc = parse_pdf(_blank_pdf(), url="https://x.ch/scan.pdf", language="de", title_hint="Scan", source_id="x",
                    artifact_path="a", ocr_dir=tmp_path)
    [section] = doc.sections
    assert section.needs_ocr and section.text == ""
    assert Path(section.ocr_image).exists()


def test_connector_downloads_and_parses(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=SAMPLE, headers={"content-type": "application/pdf"})))
    result = PdfConnector(client, data_dir=tmp_path, sleep=lambda s: None).run_pdfs(
        SPEC, [DiscoveredPdf("https://x.ch/a.pdf", "de", "Merkblatt", "x")], known={})
    assert len(result.documents) == 1 and result.documents[0].title
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/connectors/pdf.py
import time
from collections.abc import Callable, Mapping, Sequence
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pypdfium2 as pdfium
from pypdf import PdfReader

from swiss_grounding.corpus.artifacts import save_artifact
from swiss_grounding.corpus.models import (
    ConnectorResult, DiscoveredPdf, KnownState, ParsedDocument, ParsedSection, SourceSpec,
)

MIN_TEXT_CHARS = 80
RENDER_SCALE = 150 / 72
MAX_PDF_BYTES = 30_000_000


def _render(content: bytes, index: int, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(content)
    document[index].render(scale=RENDER_SCALE).to_pil().save(path)
    return str(path)


def parse_pdf(content: bytes, *, url: str, language: str, title_hint: str, source_id: str,
              artifact_path: str | None, ocr_dir: Path | str) -> ParsedDocument:
    reader = PdfReader(BytesIO(content))
    meta_title = (reader.metadata.title if reader.metadata and reader.metadata.title else "").strip()
    title = meta_title or title_hint.strip() or Path(urlparse(url).path).name
    stem = Path(artifact_path).stem if artifact_path else Path(urlparse(url).path).stem
    sections = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        crumbs = (title, f"p. {number}")
        if len(text) < MIN_TEXT_CHARS:
            image = _render(content, number - 1, Path(ocr_dir) / source_id / f"{stem}-p{number}.png")
            sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                          anchor=f"page={number}", text="", needs_ocr=True, ocr_image=image))
        else:
            sections.append(ParsedSection(align_key=f"{language}:p{number}", breadcrumb=crumbs,
                                          anchor=f"page={number}", text=text))
    return ParsedDocument(source_id=source_id, url=url, language=language, work_key=f"pdf:{url}", title=title,
                          sections=tuple(sections), extraction="pdf_text", artifact_path=artifact_path)


class PdfConnector:
    def __init__(self, http: httpx.Client, data_dir: Path | str, sleep: Callable[[float], None] = time.sleep,
                 delay_seconds: float = 0.5):
        self._http = http
        self._data_dir = Path(data_dir)
        self._sleep = sleep
        self._delay = delay_seconds

    def run_pdfs(self, spec: SourceSpec, pdfs: Sequence[DiscoveredPdf],
                 known: Mapping[str, KnownState]) -> ConnectorResult:
        documents, unchanged, errors = [], [], []
        for pdf in pdfs:
            prior = known.get(pdf.url)
            headers = {"if-none-match": prior.etag} if prior and prior.etag else {}
            try:
                response = self._http.get(pdf.url, headers=headers, follow_redirects=True, timeout=60)
            except httpx.HTTPError as exc:
                errors.append((pdf.url, f"fetch failed: {exc}"))
                continue
            finally:
                self._sleep(self._delay)
            if response.status_code == 304:
                unchanged.append(pdf.url)
                continue
            if response.status_code >= 400:
                errors.append((pdf.url, f"HTTP {response.status_code}"))
                continue
            if len(response.content) > MAX_PDF_BYTES:
                errors.append((pdf.url, f"PDF larger than {MAX_PDF_BYTES} bytes"))
                continue
            path = save_artifact(self._data_dir, spec.id, pdf.url, response.content, ".pdf")
            try:
                doc = parse_pdf(response.content, url=pdf.url, language=pdf.language, title_hint=pdf.title_hint,
                                source_id=spec.id, artifact_path=path, ocr_dir=self._data_dir / "ocr")
            except Exception as exc:  # a malformed PDF fails one document, never the run
                errors.append((pdf.url, f"PDF parse failed: {exc}"))
                continue
            documents.append(ParsedDocument(**{**doc.__dict__, "etag": response.headers.get("etag"),
                                               "last_modified": response.headers.get("last-modified"),
                                               "retrieved_via": spec.retrieved_via}))
        return ConnectorResult(documents=tuple(documents), unchanged_urls=tuple(unchanged), errors=tuple(errors))
```

`ParsedDocument(**{**doc.__dict__, ...})` works because the dataclass is frozen but not slotted; if ruff or a reviewer prefers, use `dataclasses.replace(doc, etag=..., last_modified=..., retrieved_via=...)` instead — it is equivalent.

- [ ] **Step 4: Run to pass** — `uv run pytest tests/unit/corpus/test_pdf_connector.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/connectors/pdf.py tests/unit/corpus/test_pdf_connector.py
git commit -m "feat: PDF connector with per-page text and scanned-page rendering for OCR"
```

---

### Task 11: Persistence — versions, supersede, fetch state, quarantine

**Files:**
- Create: `src/swiss_grounding/corpus/persist.py`
- Test: `tests/integration/test_corpus_persist.py`

Rules:
1. Same URL, same content hash → touch `last_seen_at`; if the status changed (scheduled → current), update it in place and supersede the other current version of the group/language/source. Outcome `unchanged`.
2. Same URL, different hash → old row `superseded`, new row inserted, `superseded_by` set. Outcome `modified`.
3. New URL with status `current` → any other `current` row for the same (translation group, language, source) is superseded. Outcome `added`. This is how a new Fedlex consolidation retires the old one (audit weakness 6).
4. `fetched_at` is the time this content was fetched; `last_seen_at` is when it was last confirmed (audit weakness 11).
5. Chunks carry document status, extent, authority, and for Fedlex the SR prior topics.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_corpus_persist.py
from datetime import UTC, date, datetime

import pytest

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import (
    group_id, known_state, persist_document, quarantine, touch_unchanged, upsert_source, withdraw,
)
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, 8, tzinfo=UTC)
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de",),
                  config={"sr_numbers": ["220"]})
ABSTRACT = "https://fedlex.data.admin.ch/eli/cc/27/317_321_377"


def _doc(url, text="1 Nach Ablauf der Probezeit.", status="current", valid_from=date(2025, 7, 1), lang="de"):
    section = ParsedSection("art_336_c", ("SR 220 OR", "Art. 336c"), "art_336_c", text)
    return ParsedDocument(source_id="fedlex", url=url, language=lang, work_key=ABSTRACT, title="Obligationenrecht",
                          sections=(section,), identifier="SR 220", valid_from=valid_from, status=status)


def _rows(conn):
    return conn.execute("select url, status, superseded_by, valid_to from corpus.document order by id").fetchall()


def test_new_document_writes_chunks_with_prior_topics(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        assert persist_document(conn, _doc("u1"), SPEC, NOW) == "added"
        chunk = conn.execute("select * from corpus.chunk").fetchone()
    assert chunk["language"] == "de" and chunk["align_key"] == "art_336_c"
    assert chunk["topics"] == ["work"]
    assert chunk["translation_group_id"] == group_id(ABSTRACT)
    assert chunk["status"] == "current" and chunk["extent_id"] == "CH" and chunk["authority"] == "federal_law"


def test_new_version_reuses_descriptions_of_unchanged_chunks(corpus_db):
    """RAG review E3: a refresh pays only for chunks whose text changed."""
    unchanged = ParsedSection("art_1", ("SR 220 OR", "Art. 1"), "art_1", "Zum Abschlusse eines Vertrages.")
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        old = _doc("u2024", valid_from=date(2024, 1, 1))
        persist_document(conn, ParsedDocument(**{**old.__dict__, "sections": (unchanged, *old.sections)}), SPEC, NOW)
        conn.execute("update corpus.chunk set description = 'Vertragsabschluss', topics = '{business}' "
                     "where align_key = 'art_1'")
        conn.execute("update corpus.chunk set description = 'Kündigungsschutz' where align_key = 'art_336_c'")
        new = _doc("u2025", valid_from=date(2025, 7, 1), text="1 Geänderter Text.")
        persist_document(conn, ParsedDocument(**{**new.__dict__, "sections": (unchanged, *new.sections)}), SPEC, NOW)
        rows = {r["align_key"]: r for r in conn.execute(
            "select align_key, description, topics from corpus.chunk where status = 'current'").fetchall()}
    assert rows["art_1"]["description"] == "Vertragsabschluss" and rows["art_1"]["topics"] == ["business"]
    assert rows["art_336_c"]["description"] == ""          # changed text is described again


def test_same_content_is_unchanged(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert persist_document(conn, _doc("u1"), SPEC, NOW) == "unchanged"
        assert len(_rows(conn)) == 1


def test_changed_content_at_same_url_supersedes(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert persist_document(conn, _doc("u1", text="1 Neu."), SPEC, NOW) == "modified"
        rows = _rows(conn)
    assert [r["status"] for r in rows] == ["superseded", "current"]
    assert rows[0]["superseded_by"] is not None


def test_new_consolidation_retires_the_old_one(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u2024", valid_from=date(2024, 1, 1)), SPEC, NOW)
        persist_document(conn, _doc("u2025", valid_from=date(2025, 7, 1), text="1 Neu."), SPEC, NOW)
        rows = _rows(conn)
        stale = conn.execute("select count(*) as n from corpus.chunk where status = 'current'").fetchone()["n"]
    assert [r["status"] for r in rows] == ["superseded", "current"]
    assert rows[0]["valid_to"] == date(2025, 7, 1)
    assert stale == 1


def test_scheduled_version_coexists_then_takes_over(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("now"), SPEC, NOW)
        persist_document(conn, _doc("later", status="scheduled", valid_from=date(2027, 1, 1), text="1 Neu."), SPEC, NOW)
        assert [r["status"] for r in _rows(conn)] == ["current", "scheduled"]
        persist_document(conn, _doc("later", status="current", valid_from=date(2027, 1, 1), text="1 Neu."), SPEC, NOW)
        assert [r["status"] for r in _rows(conn)] == ["superseded", "current"]


def test_languages_of_one_act_share_a_group_and_do_not_supersede_each_other(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("de"), SPEC, NOW)
        persist_document(conn, _doc("fr", lang="fr", text="1 Après le temps d'essai."), SPEC, NOW)
        groups = conn.execute("select distinct translation_group_id from corpus.document").fetchall()
        statuses = [r["status"] for r in _rows(conn)]
    assert len(groups) == 1 and statuses == ["current", "current"]


def test_fetch_state_touch_withdraw_and_quarantine(corpus_db):
    with connect(corpus_db) as conn:
        upsert_source(conn, SPEC)
        persist_document(conn, _doc("u1"), SPEC, NOW)
        assert "u1" in known_state(conn, "fedlex")
        touch_unchanged(conn, "u1", NOW)
        withdraw(conn, "u1")
        assert _rows(conn)[0]["status"] == "withdrawn"
        quarantine(conn, "fedlex", "u9", "fetch", "HTTP 500")
        quarantine(conn, "fedlex", "u9", "fetch", "HTTP 503")
        q = conn.execute("select attempts, reason from corpus.quarantine").fetchone()
    assert q["attempts"] == 2 and q["reason"] == "HTTP 503"
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/persist.py
import hashlib
import json
import re
from datetime import datetime

import psycopg

from swiss_grounding.corpus.chunker import chunk_document
from swiss_grounding.corpus.models import ChunkDraft, KnownState, ParsedDocument, SourceSpec, content_hash
from swiss_grounding.corpus.topics import sr_prior

ARTICLE_NUMBER = re.compile(r"^art_(\d+)")


def group_id(work_key: str) -> str:
    return "g_" + hashlib.sha1(work_key.encode()).hexdigest()[:16]


def upsert_source(conn: psycopg.Connection, spec: SourceSpec) -> None:
    conn.execute(
        "insert into corpus.source (id, name, publisher, authority, level, extent_id, connector, tier, languages, config) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do update set name=excluded.name, "
        "publisher=excluded.publisher, authority=excluded.authority, level=excluded.level, "
        "extent_id=excluded.extent_id, connector=excluded.connector, tier=excluded.tier, "
        "languages=excluded.languages, config=excluded.config",
        (spec.id, spec.name, spec.publisher, spec.authority, spec.level, spec.extent_id, spec.connector,
         spec.tier, list(spec.languages), json.dumps(spec.config)))


def known_state(conn: psycopg.Connection, source_id: str) -> dict[str, KnownState]:
    rows = conn.execute("select url, etag, last_modified, content_hash from corpus.fetch_state where source_id = %s",
                        (source_id,)).fetchall()
    return {r["url"]: KnownState(r["etag"], r["last_modified"], r["content_hash"]) for r in rows}


def _prior_topics(doc: ParsedDocument, draft: ChunkDraft) -> list[str]:
    if not (doc.identifier and doc.identifier.startswith("SR ")):
        return []
    match = ARTICLE_NUMBER.match(draft.align_key)
    return list(sr_prior(doc.identifier[3:], int(match.group(1)) if match else None))


def _set_status(conn: psycopg.Connection, doc_ids: list[int], status: str) -> None:
    if doc_ids:
        conn.execute("update corpus.document set status = %s where id = any(%s)", (status, doc_ids))
        conn.execute("update corpus.chunk set status = %s where document_id = any(%s) and status <> 'boilerplate'",
                     (status, doc_ids))


def _supersede_others(conn, gid: str, language: str, source_id: str, keep_id: int, valid_to) -> None:
    rows = conn.execute(
        "select id from corpus.document where translation_group_id = %s and language = %s and source_id = %s "
        "and status = 'current' and id <> %s", (gid, language, source_id, keep_id)).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        conn.execute("update corpus.document set superseded_by = %s, valid_to = coalesce(valid_to, %s) "
                     "where id = any(%s)", (keep_id, valid_to, ids))
        _set_status(conn, ids, "superseded")


def _insert(conn, doc: ParsedDocument, spec: SourceSpec, gid: str, digest: str, now: datetime) -> int:
    doc_id = conn.execute(
        "insert into corpus.document (source_id, url, language, translation_group_id, title, identifier, publisher, "
        "authority, extent_id, is_authentic, valid_from, valid_to, status, published_at, modified_at, fetched_at, "
        "last_seen_at, content_hash, extraction, retrieved_via, artifact_path) values "
        "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
        (doc.source_id, doc.url, doc.language, gid, doc.title, doc.identifier, spec.publisher, spec.authority,
         spec.extent_id, doc.is_authentic, doc.valid_from, doc.valid_to, doc.status, doc.published_at,
         doc.modified_at, now, now, digest, doc.extraction, doc.retrieved_via or spec.retrieved_via,
         doc.artifact_path)).fetchone()["id"]
    drafts = chunk_document(doc)
    with conn.cursor() as cur:
        cur.executemany(
            "insert into corpus.chunk (document_id, language, translation_group_id, align_key, ordinal, breadcrumb, "
            "anchor, text, topics, extent_id, authority, status, chunk_hash, needs_ocr, ocr_image) values "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [(doc_id, doc.language, gid, d.align_key, d.ordinal, list(d.breadcrumb), d.anchor, d.text,
              _prior_topics(doc, d), spec.extent_id, spec.authority, doc.status,
              hashlib.sha256((d.text or d.ocr_image or "").encode()).hexdigest(), d.needs_ocr, d.ocr_image)
             for d in drafts])
    _reuse_descriptions(conn, doc_id)
    return doc_id


def _reuse_descriptions(conn, doc_id: int) -> None:
    """Copy description, topics and a boilerplate verdict from an earlier version's identical chunk.

    RAG review E3: a chunk whose text did not change between versions keeps what was already paid for.
    Identity is (translation group, language, align_key, chunk_hash), so a changed text is described again.
    """
    conn.execute(
        "update corpus.chunk n set description = o.description, topics = o.topics, "
        "status = case when o.status = 'boilerplate' then 'boilerplate' else n.status end "
        "from corpus.chunk o where n.document_id = %s and o.document_id <> n.document_id "
        "and o.translation_group_id = n.translation_group_id and o.language = n.language "
        "and o.align_key = n.align_key and o.chunk_hash = n.chunk_hash and o.description <> ''",
        (doc_id,))


def _upsert_fetch_state(conn, doc: ParsedDocument, digest: str, now: datetime) -> None:
    conn.execute(
        "insert into corpus.fetch_state (url, source_id, etag, last_modified, content_hash, last_seen_at) "
        "values (%s,%s,%s,%s,%s,%s) on conflict (url) do update set source_id=excluded.source_id, "
        "etag=excluded.etag, last_modified=excluded.last_modified, content_hash=excluded.content_hash, "
        "last_seen_at=excluded.last_seen_at",
        (doc.url, doc.source_id, doc.etag, doc.last_modified, digest, now))


def persist_document(conn: psycopg.Connection, doc: ParsedDocument, spec: SourceSpec, now: datetime) -> str:
    """Write one parsed document. Returns 'added', 'modified' or 'unchanged'."""
    gid = group_id(doc.work_key)
    conn.execute("insert into corpus.translation_group (id, work_key) values (%s, %s) on conflict (id) do nothing",
                 (gid, doc.work_key))
    digest = content_hash(doc)
    retire_date = doc.valid_from or now.date()
    live = conn.execute("select id, content_hash, status from corpus.document "
                        "where url = %s and status in ('current','scheduled')", (doc.url,)).fetchone()
    if live and live["content_hash"] == digest:
        conn.execute("update corpus.document set last_seen_at = %s where id = %s", (now, live["id"]))
        if live["status"] != doc.status:
            _set_status(conn, [live["id"]], doc.status)
            if doc.status == "current":
                _supersede_others(conn, gid, doc.language, doc.source_id, live["id"], retire_date)
        _upsert_fetch_state(conn, doc, digest, now)
        return "unchanged"
    if live:
        _set_status(conn, [live["id"]], "superseded")
    doc_id = _insert(conn, doc, spec, gid, digest, now)
    if live:
        conn.execute("update corpus.document set superseded_by = %s, valid_to = coalesce(valid_to, %s) where id = %s",
                     (doc_id, retire_date, live["id"]))
    if doc.status == "current":
        _supersede_others(conn, gid, doc.language, doc.source_id, doc_id, retire_date)
    _upsert_fetch_state(conn, doc, digest, now)
    return "modified" if live else "added"


def touch_unchanged(conn: psycopg.Connection, url: str, now: datetime) -> None:
    conn.execute("update corpus.document set last_seen_at = %s where url = %s and status in ('current','scheduled')",
                 (now, url))
    conn.execute("update corpus.fetch_state set last_seen_at = %s where url = %s", (now, url))


def withdraw(conn: psycopg.Connection, url: str) -> None:
    ids = [r["id"] for r in conn.execute(
        "select id from corpus.document where url = %s and status in ('current','scheduled')", (url,)).fetchall()]
    _set_status(conn, ids, "withdrawn")
    conn.execute("delete from corpus.fetch_state where url = %s", (url,))


def quarantine(conn: psycopg.Connection, source_id: str, url: str, stage: str, reason: str) -> None:
    conn.execute(
        "insert into corpus.quarantine (source_id, url, stage, reason) values (%s,%s,%s,%s) "
        "on conflict (source_id, url, stage) do update set attempts = corpus.quarantine.attempts + 1, "
        "reason = excluded.reason, last_at = now()", (source_id, url, stage, reason[:2000]))
```

- [ ] **Step 4: Run to pass**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_corpus_persist.py -q`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/persist.py tests/integration/test_corpus_persist.py
git commit -m "feat: persist corpus documents with versioning and supersede across consolidations"
```

---

### Task 12: Fetch stage — run a manifest's connectors

**Files:**
- Create: `src/swiss_grounding/corpus/fetch_stage.py`
- Test: `tests/integration/test_corpus_fetch_stage.py`

Each source runs in its own thread (hosts differ, so politeness is per connector); each document commits on its own; errors and exceptions go to quarantine; PDFs discovered by the HTML connector are fetched by the PDF connector for the same source.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_corpus_fetch_stage.py
from datetime import UTC, datetime

import pytest

from swiss_grounding.corpus.fetch_stage import run_fetch
from swiss_grounding.corpus.models import ConnectorResult, DiscoveredPdf, ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, tzinfo=UTC)


def _spec(sid, connector="html"):
    return SourceSpec(id=sid, name=sid, publisher=sid, authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector=connector, tier=1, languages=("de",),
                      config={"start_urls": ["https://x/"], "allow_prefixes": ["https://x/"]})


def _doc(sid, url):
    return ParsedDocument(source_id=sid, url=url, language="de", work_key=f"html:{url}", title="T",
                          sections=(ParsedSection("de:0", ("T",), None, "Inhalt der Seite."),))


class FakeHtml:
    def run(self, spec, known):
        if spec.id == "boom":
            raise RuntimeError("site exploded")
        return ConnectorResult(documents=(_doc(spec.id, f"https://x/{spec.id}"),),
                               errors=((f"https://x/{spec.id}/bad", "HTTP 500"),),
                               pdfs=(DiscoveredPdf("https://x/a.pdf", "de", "A", spec.id),))


class FakePdf:
    def run_pdfs(self, spec, pdfs, known):
        return ConnectorResult(documents=tuple(_doc(spec.id, p.url) for p in pdfs))


def test_runs_sources_persists_and_quarantines(corpus_db):
    report = run_fetch(corpus_db, [_spec("bern"), _spec("boom")], {"html": FakeHtml()}, FakePdf(),
                       now=lambda: NOW, workers=2)
    with connect(corpus_db) as conn:
        urls = {r["url"] for r in conn.execute("select url from corpus.document").fetchall()}
        q = {(r["url"], r["stage"]) for r in conn.execute("select url, stage from corpus.quarantine").fetchall()}
    assert urls == {"https://x/bern", "https://x/a.pdf"}
    assert ("https://x/bern/bad", "fetch") in q
    assert ("source:boom", "fetch") in q
    assert report["bern"]["added"] == 2
    assert report["boom"]["failed"] == 1
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/fetch_stage.py
import logging
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from swiss_grounding.corpus.models import ConnectorResult, SourceSpec
from swiss_grounding.corpus.persist import (
    known_state, persist_document, quarantine, touch_unchanged, upsert_source, withdraw,
)
from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)


def _persist_result(database_url: str, spec: SourceSpec, result: ConnectorResult, now: datetime,
                    tally: Counter) -> None:
    with connect(database_url) as conn:
        for doc in result.documents:
            try:
                with conn.transaction():
                    tally[persist_document(conn, doc, spec, now)] += 1
            except Exception as exc:
                log.exception("persist failed for %s", doc.url)
                quarantine(conn, spec.id, doc.url, "persist", repr(exc))
                tally["failed"] += 1
            conn.commit()
        for url in result.unchanged_urls:
            touch_unchanged(conn, url, now)
            tally["unchanged"] += 1
        for url in result.gone_urls:
            withdraw(conn, url)
            tally["withdrawn"] += 1
        for url, reason in result.errors:
            quarantine(conn, spec.id, url, "fetch", reason)
            tally["failed"] += 1
        conn.commit()


def _run_source(database_url: str, spec: SourceSpec, connectors: Mapping, pdf_connector,
                now: Callable[[], datetime]) -> Counter:
    tally: Counter = Counter()
    with connect(database_url) as conn:
        upsert_source(conn, spec)
        known = known_state(conn, spec.id)
    try:
        result = connectors[spec.connector].run(spec, known)
        _persist_result(database_url, spec, result, now(), tally)
        if result.pdfs and pdf_connector is not None:
            _persist_result(database_url, spec, pdf_connector.run_pdfs(spec, result.pdfs, known), now(), tally)
    except Exception as exc:
        log.exception("source %s failed", spec.id)
        with connect(database_url) as conn:
            quarantine(conn, spec.id, f"source:{spec.id}", "fetch", repr(exc))
        tally["failed"] += 1
    log.info("source %s: %s", spec.id, dict(tally))
    return tally


def run_fetch(database_url: str, specs: Sequence[SourceSpec], connectors: Mapping, pdf_connector,
              now: Callable[[], datetime], workers: int = 4) -> dict[str, Counter]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {spec.id: pool.submit(_run_source, database_url, spec, connectors, pdf_connector, now)
                   for spec in specs}
        return {sid: future.result() for sid, future in futures.items()}
```

- [ ] **Step 4: Run to pass**, **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/fetch_stage.py tests/integration/test_corpus_fetch_stage.py
git commit -m "feat: fetch stage runs manifest sources in parallel with per-document commits and quarantine"
```

---

### Task 13: Providers — embeddings and LLM (OpenAI, local bge-m3, Anthropic, fakes)

**Files:**
- Create: `src/swiss_grounding/corpus/providers.py`
- Test: `tests/unit/corpus/test_providers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_providers.py
import json

import pytest

from swiss_grounding.corpus.providers import (
    INDEXES, FakeEmbeddings, FakeLLM, OpenAILLM, Usage, extract_json,
)


def test_index_registry_matches_the_schema():
    assert INDEXES["openai-3l"].dim == 3072 and INDEXES["openai-3l"].table == "corpus.emb_openai_3l"
    assert INDEXES["bge-m3"].dim == 1024 and INDEXES["bge-m3"].table == "corpus.emb_bge_m3"


def test_fake_embeddings_have_the_index_dimension():
    vectors = FakeEmbeddings(3072).embed(["Hund", "chien"])
    assert len(vectors) == 2 and vectors[0].shape == (3072,)


def test_top_sparse_keeps_the_heaviest_positive_terms():
    from swiss_grounding.corpus.providers import top_sparse
    weights = {"12": 0.1, "7": 0.9, "3": 0.0, "44": 0.5}
    assert top_sparse(weights, limit=2) == {7: 0.9, 44: 0.5}


def test_extract_json_tolerates_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_fake_llm_calls_the_responder():
    llm = FakeLLM(lambda task: {"echo": task.custom_id})
    from swiss_grounding.corpus.runner import LlmTask
    data, usage = llm.complete(LlmTask("t1", "m", "sys", "user"))
    assert data == {"echo": "t1"} and isinstance(usage, Usage)


def test_openai_chat_body_uses_json_mode_and_minimal_reasoning():
    from swiss_grounding.corpus.runner import LlmTask
    body = OpenAILLM.chat_body(LlmTask("t", "gpt-5-nano", "sys", "user", image_png_b64="AAAA", max_output_tokens=500))
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "minimal"
    assert body["max_completion_tokens"] == 500
    content = body["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    json.dumps(body)
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement `runner.py`'s task types first** (they are shared)

```python
# src/swiss_grounding/corpus/runner.py  (first part; Task 15 appends the runners)
from dataclasses import dataclass


@dataclass(frozen=True)
class LlmTask:
    custom_id: str
    model: str
    system: str
    user: str
    image_png_b64: str | None = None
    max_output_tokens: int = 800


@dataclass(frozen=True)
class LlmOutcome:
    custom_id: str
    data: dict | None
    input_tokens: int
    output_tokens: int
    error: str | None = None
```

- [ ] **Step 4: Implement `providers.py`**

```python
# src/swiss_grounding/corpus/providers.py
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from swiss_grounding.corpus.runner import LlmTask
from swiss_grounding.retrieval.embedder import FakeEmbedder


@dataclass(frozen=True)
class IndexSpec:
    name: str
    provider: str
    model: str
    dim: int
    table: str
    opclass: str


INDEXES: dict[str, IndexSpec] = {
    "openai-3l": IndexSpec("openai-3l", "openai", "text-embedding-3-large", 3072, "corpus.emb_openai_3l",
                           "halfvec_cosine_ops"),
    "bge-m3": IndexSpec("bge-m3", "local", "BAAI/bge-m3", 1024, "corpus.emb_bge_m3", "vector_cosine_ops"),
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]: ...


class FakeEmbeddings:
    def __init__(self, dim: int):
        self.dim = dim
        self._inner = FakeEmbedder(dim=dim)

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return self._inner.embed(texts)


class OpenAIEmbeddings:
    """Synchronous OpenAI embeddings, for `--sync` and small runs. Large runs use the Batch API (Task 17)."""
    dim = 3072

    def __init__(self, api_key: str, model: str = "text-embedding-3-large"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self.last_usage = 0

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        response = self._client.embeddings.create(model=self._model, input=list(texts))
        self.last_usage = response.usage.prompt_tokens
        return [np.asarray(item.embedding, dtype=np.float32) for item in response.data]


BGE_M3_VOCAB = 250002
MAX_SPARSE_TERMS = 1000     # pgvector's HNSW limit on non-zero entries of a sparsevec
BGE_MAX_TOKENS = 2048       # RAG review E4: breadcrumb + description + a long paragraph exceeds 1,024


def top_sparse(weights: dict, limit: int = MAX_SPARSE_TERMS) -> dict[int, float]:
    """bge-m3 lexical weights ({token_id: weight}) trimmed to the `limit` heaviest, keys as ints."""
    items = sorted(((int(k), float(v)) for k, v in weights.items() if float(v) > 0), key=lambda kv: -kv[1])
    return dict(items[:limit])


class LocalBgeM3:
    """bge-m3 on this machine: Apple GPU when available, else CPU. Measured 12.4 chunks/s on an M1 Pro GPU.

    With FlagEmbedding installed it returns the dense vector and bge-m3's learned sparse vector from the
    same forward pass (RAG review E1); without it, it falls back to sentence-transformers, dense only.
    """
    dim = 1024

    def __init__(self, model: str = "BAAI/bge-m3", batch_size: int = 16):
        import torch
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._batch_size = batch_size
        try:
            from FlagEmbedding import BGEM3FlagModel
            self._flag = BGEM3FlagModel(model, use_fp16=False, devices=self._device)
            self._st = None
        except ImportError:
            from sentence_transformers import SentenceTransformer
            self._flag = None
            self._st = SentenceTransformer(model, device=self._device)
            self._st.max_seq_length = BGE_MAX_TOKENS

    @property
    def has_sparse(self) -> bool:
        return self._flag is not None

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return [dense for dense, _ in self.embed_with_sparse(texts)]

    def embed_with_sparse(self, texts: Sequence[str]) -> list[tuple[np.ndarray, dict[int, float] | None]]:
        if self._flag is not None:
            out = self._flag.encode(list(texts), batch_size=self._batch_size, max_length=BGE_MAX_TOKENS,
                                    return_dense=True, return_sparse=True, return_colbert_vecs=False)
            return [(np.asarray(d, dtype=np.float32), top_sparse(s))
                    for d, s in zip(out["dense_vecs"], out["lexical_weights"], strict=True)]
        arr = self._st.encode(list(texts), batch_size=self._batch_size, normalize_embeddings=True)
        return [(np.asarray(row, dtype=np.float32), None) for row in arr]


def extract_json(text: str) -> dict:
    """The outermost JSON object in a model reply, tolerating code fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model reply")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("model reply is not a JSON object")
    return value


class LLMProvider(Protocol):
    def complete(self, task: LlmTask) -> tuple[dict, Usage]: ...


class FakeLLM:
    def __init__(self, responder: Callable[[LlmTask], dict]):
        self._responder = responder

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        return self._responder(task), Usage(len(task.user) // 3, 50)


class OpenAILLM:
    def __init__(self, api_key: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    @staticmethod
    def chat_body(task: LlmTask) -> dict:
        if task.image_png_b64:
            user_content: list | str = [
                {"type": "text", "text": task.user},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{task.image_png_b64}"}},
            ]
        else:
            user_content = task.user
        return {
            "model": task.model,
            "messages": [{"role": "system", "content": task.system}, {"role": "user", "content": user_content}],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": task.max_output_tokens,
            # gpt-5 models bill reasoning tokens as output; descriptions and OCR need none.
            "reasoning_effort": "minimal",
        }

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        response = self._client.chat.completions.create(**self.chat_body(task))
        text = response.choices[0].message.content or ""
        return extract_json(text), Usage(response.usage.prompt_tokens, response.usage.completion_tokens)


class AnthropicLLM:
    """Synchronous fallback on Claude. The Batch path is OpenAI-only (ADR 0006: OpenAI is the main provider)."""

    def __init__(self, api_key: str, model: str):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        content: list[dict] = [{"type": "text", "text": task.user}]
        if task.image_png_b64:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                           "data": task.image_png_b64}})
        response = self._client.messages.create(model=self._model, max_tokens=task.max_output_tokens,
                                                system=task.system, messages=[{"role": "user", "content": content}])
        text = "".join(block.text for block in response.content if block.type == "text")
        return extract_json(text), Usage(response.usage.input_tokens, response.usage.output_tokens)
```

- [ ] **Step 5: Run to pass** — `uv run pytest tests/unit/corpus/test_providers.py -q` → PASS.

- [ ] **Step 6: Spike — does FlagEmbedding run bge-m3 on the Mac GPU? (15 minutes, free)**

```bash
uv add --optional embed "FlagEmbedding>=1.3"
uv sync --extra embed
uv run python -c "
import time; from swiss_grounding.corpus.providers import LocalBgeM3
m = LocalBgeM3(); print('sparse available:', m.has_sparse, 'device:', m._device)
texts = ['SR 220 OR > Art. 336c\nKündigungsschutz bei Krankheit\n1 Nach Ablauf der Probezeit darf der Arbeitgeber nicht kündigen.'] * 64
t = time.time(); out = m.embed_with_sparse(texts); dt = time.time() - t
print(f'{64/dt:.1f} chunks/s; dense dim {out[0][0].shape}; sparse terms {len(out[0][1] or {})}')"
```

Expected: `sparse available: True`, dense dim `(1024,)`, a few dozen sparse terms, and a speed within about 30% of the 12.4 chunks/s measured with sentence-transformers. **If FlagEmbedding fails to import or crashes on `mps`**, try `devices="cpu"` for the sparse pass only if CPU speed is acceptable for the corpus size (≈4 chunks/s); otherwise remove the extra (`uv remove --optional embed FlagEmbedding`) and continue: `LocalBgeM3` falls back to dense only and `sparse` stays null. Record the outcome in the commit message.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/swiss_grounding/corpus/providers.py src/swiss_grounding/corpus/runner.py tests/unit/corpus/test_providers.py
git commit -m "feat: embedding and LLM providers; bge-m3 dense + sparse in one pass"
```

---

### Task 14: Budget — prices, estimates, ledger, cap

**Files:**
- Create: `src/swiss_grounding/corpus/budget.py`
- Test: `tests/unit/corpus/test_budget.py`, `tests/integration/test_corpus_budget.py`

Prices are OpenAI **Batch** prices per 1M tokens as published on 2026-09-23 (https://developers.openai.com/api/docs/pricing). **Verify them on the day** before the first paid batch and edit `PRICES` if they changed. Synchronous calls cost twice the batch price.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/corpus/test_budget.py
import pytest

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens


def test_token_estimate_is_conservative():
    assert estimate_tokens("a" * 300) == 100


def test_batch_cost_and_sync_doubles_it():
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000) == pytest.approx(0.225)
    assert cost_usd("gpt-5-nano", 1_000_000, 1_000_000, batch=False) == pytest.approx(0.45)
    assert cost_usd("text-embedding-3-large", 1_000_000, 0) == pytest.approx(0.065)


def test_unknown_model_is_refused():
    with pytest.raises(KeyError):
        cost_usd("gpt-99", 1, 1)
```

```python
# tests/integration/test_corpus_budget.py
import pytest

from swiss_grounding.corpus.budget import BudgetExceeded, ensure_within, record_spend, spent
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration


def test_ledger_and_caps(corpus_db):
    with connect(corpus_db) as conn:
        record_spend(conn, kind="describe", model="gpt-5-nano", usd=60.0, input_tokens=1, output_tokens=1, estimated=False)
        record_spend(conn, kind="ocr", model="gpt-5-mini", usd=9.0, input_tokens=1, output_tokens=1, estimated=False)
        assert spent(conn) == pytest.approx(69.0)
        assert spent(conn, kind="ocr") == pytest.approx(9.0)
        ensure_within(conn, estimate=30.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="total"):
            ensure_within(conn, estimate=32.0, total_cap=100.0)
        with pytest.raises(BudgetExceeded, match="ocr"):
            ensure_within(conn, estimate=2.0, total_cap=100.0, kind="ocr", kind_cap=10.0)
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/budget.py
import psycopg

# USD per 1M tokens on the Batch API: (input, output). Verify on the day of the run.
PRICES: dict[str, tuple[float, float]] = {
    "text-embedding-3-large": (0.065, 0.0),
    "gpt-5-mini": (0.125, 1.0),
    "gpt-5-nano": (0.025, 0.2),
}
SYNC_MULTIPLIER = 2.0
CHARS_PER_TOKEN = 3          # conservative for German/French/Italian
OCR_IMAGE_TOKENS = 1500      # per page image; replaced by the pilot's measured value (Task 16)


class BudgetExceeded(RuntimeError):
    pass


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def cost_usd(model: str, input_tokens: int, output_tokens: int, batch: bool = True) -> float:
    price_in, price_out = PRICES[model]
    usd = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    return usd if batch else usd * SYNC_MULTIPLIER


def record_spend(conn: psycopg.Connection, *, kind: str, model: str, usd: float, input_tokens: int,
                 output_tokens: int, estimated: bool) -> None:
    conn.execute("insert into corpus.llm_spend (kind, model, usd, input_tokens, output_tokens, estimated) "
                 "values (%s,%s,%s,%s,%s,%s)", (kind, model, usd, input_tokens, output_tokens, estimated))


def spent(conn: psycopg.Connection, kind: str | None = None) -> float:
    row = conn.execute("select coalesce(sum(usd), 0) as usd from corpus.llm_spend where %s::text is null or kind = %s",
                       (kind, kind)).fetchone()
    return float(row["usd"])


def ensure_within(conn: psycopg.Connection, *, estimate: float, total_cap: float,
                  kind: str | None = None, kind_cap: float | None = None) -> None:
    total = spent(conn)
    if total + estimate > total_cap:
        raise BudgetExceeded(f"total budget: spent ${total:.2f} + estimate ${estimate:.2f} > cap ${total_cap:.2f}")
    if kind and kind_cap is not None:
        part = spent(conn, kind)
        if part + estimate > kind_cap:
            raise BudgetExceeded(f"{kind} budget: spent ${part:.2f} + estimate ${estimate:.2f} > cap ${kind_cap:.2f}")
```

- [ ] **Step 4: Run to pass** (unit and integration), **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/budget.py tests/unit/corpus/test_budget.py tests/integration/test_corpus_budget.py
git commit -m "feat: spend ledger with total and per-kind caps"
```

---

### Task 15: Task runners — synchronous and OpenAI Batch

**Files:**
- Modify: `src/swiss_grounding/corpus/runner.py` (append)
- Test: `tests/unit/corpus/test_runner.py`

`SyncRunner` calls an `LLMProvider` in a thread pool. `BatchRunner` writes JSONL files of ≤ 50,000 requests, uploads them, creates batches, polls every 60 s, downloads results and yields `LlmOutcome`s; it records each batch in `corpus.batch_job` so an interrupted run resumes by collecting unfinished batches before building new ones. The OpenAI client is injected so the test uses a fake.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/corpus/test_runner.py
import json

from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import BatchRunner, LlmTask, SyncRunner, parse_batch_line


def test_sync_runner_returns_one_outcome_per_task():
    runner = SyncRunner(FakeLLM(lambda t: {"id": t.custom_id}), workers=2)
    out = list(runner.run([LlmTask("a", "m", "s", "u"), LlmTask("b", "m", "s", "u")]))
    assert sorted(o.custom_id for o in out) == ["a", "b"]
    assert all(o.data == {"id": o.custom_id} for o in out)


def test_sync_runner_turns_exceptions_into_errors():
    def boom(task):
        raise ValueError("bad reply")
    [out] = SyncRunner(FakeLLM(boom), workers=1).run([LlmTask("a", "m", "s", "u")])
    assert out.data is None and "bad reply" in out.error


def test_parse_batch_line_for_chat_completion():
    line = {"custom_id": "a", "response": {"status_code": 200, "body": {
        "choices": [{"message": {"content": '{"x": 1}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}}}
    out = parse_batch_line(json.dumps(line))
    assert out.data == {"x": 1} and out.input_tokens == 10 and out.output_tokens == 5


def test_parse_batch_line_error():
    out = parse_batch_line(json.dumps({"custom_id": "a", "response": None, "error": {"message": "rate"}}))
    assert out.data is None and "rate" in out.error


class FakeOpenAI:
    """Stands in for the openai client's files and batches resources."""
    def __init__(self):
        self.submitted = []
        outer = self

        class Files:
            def create(self, file, purpose):
                outer.submitted.append([json.loads(line) for line in file.read().decode().splitlines()])
                return type("F", (), {"id": f"file-{len(outer.submitted)}"})()

            def content(self, file_id):
                n = int(file_id.split("-")[-1])
                lines = [json.dumps({"custom_id": r["custom_id"], "response": {"status_code": 200, "body": {
                    "choices": [{"message": {"content": json.dumps({"ok": r["custom_id"]})}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2}}}}) for r in outer.submitted[n - 1]]
                return type("C", (), {"text": "\n".join(lines)})()

        class Batches:
            def create(self, input_file_id, endpoint, completion_window):
                return type("B", (), {"id": "batch-" + input_file_id.split("-")[-1]})()

            def retrieve(self, batch_id):
                n = batch_id.split("-")[-1]
                return type("B", (), {"status": "completed", "output_file_id": f"out-{n}", "error_file_id": None})()

        self.files, self.batches = Files(), Batches()


def test_batch_runner_splits_files_and_collects_results(tmp_path):
    client = FakeOpenAI()
    runner = BatchRunner(client, work_dir=tmp_path, max_per_file=2, poll_seconds=0, record=lambda *a: None)
    tasks = [LlmTask(str(i), "gpt-5-nano", "s", "u") for i in range(5)]
    out = list(runner.run(tasks, kind="describe"))
    assert len(client.submitted) == 3
    assert sorted(o.custom_id for o in out) == ["0", "1", "2", "3", "4"]
    assert all(o.data == {"ok": o.custom_id} for o in out)
```

- [ ] **Step 2: Run to fail**, then **Step 3: Append to `runner.py`**

```python
# src/swiss_grounding/corpus/runner.py  (append below LlmTask / LlmOutcome)
import json
import logging
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

log = logging.getLogger(__name__)
CHAT_ENDPOINT = "/v1/chat/completions"
EMBEDDINGS_ENDPOINT = "/v1/embeddings"
TERMINAL = {"completed", "failed", "expired", "cancelled"}


class SyncRunner:
    def __init__(self, llm, workers: int = 8):
        self._llm = llm
        self._workers = workers

    def run(self, tasks: Sequence[LlmTask], kind: str = "") -> Iterator[LlmOutcome]:
        def one(task: LlmTask) -> LlmOutcome:
            try:
                data, usage = self._llm.complete(task)
                return LlmOutcome(task.custom_id, data, usage.input_tokens, usage.output_tokens)
            except Exception as exc:
                return LlmOutcome(task.custom_id, None, 0, 0, error=repr(exc))
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            for future in as_completed([pool.submit(one, t) for t in tasks]):
                yield future.result()


def parse_batch_line(line: str) -> LlmOutcome:
    from swiss_grounding.corpus.providers import extract_json
    record = json.loads(line)
    custom_id = record["custom_id"]
    response = record.get("response")
    if not response or response.get("status_code") != 200:
        message = (record.get("error") or {}).get("message") or json.dumps(response)[:300]
        return LlmOutcome(custom_id, None, 0, 0, error=message)
    body = response["body"]
    usage = body.get("usage", {})
    try:
        data = extract_json(body["choices"][0]["message"]["content"] or "")
    except (ValueError, KeyError, IndexError) as exc:
        return LlmOutcome(custom_id, None, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                          error=f"unparseable reply: {exc}")
    return LlmOutcome(custom_id, data, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class BatchRunner:
    """OpenAI Batch API: half price, results within 24 hours.

    `record(batch_id, kind, endpoint, request_count, input_path)` is called after each submission so the
    CLI can store it in corpus.batch_job; `pending()` in the CLI re-attaches to unfinished batches.
    """

    def __init__(self, client, work_dir: Path | str, max_per_file: int = 50_000, poll_seconds: float = 60,
                 record: Callable[..., None] = lambda *a: None, sleep: Callable[[float], None] = time.sleep):
        self._client = client
        self._dir = Path(work_dir)
        self._max = max_per_file
        self._poll = poll_seconds
        self._record = record
        self._sleep = sleep

    def _submit(self, lines: list[dict], kind: str, endpoint: str, index: int) -> str:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{kind}-{int(time.time())}-{index}.jsonl"
        path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines))
        with path.open("rb") as handle:
            uploaded = self._client.files.create(file=handle, purpose="batch")
        batch = self._client.batches.create(input_file_id=uploaded.id, endpoint=endpoint, completion_window="24h")
        self._record(batch.id, kind, endpoint, len(lines), str(path))
        log.info("submitted %s batch %s with %d requests", kind, batch.id, len(lines))
        return batch.id

    def collect(self, batch_id: str) -> Iterator[str]:
        """Wait for one batch and yield its raw result lines (successes and errors)."""
        while True:
            batch = self._client.batches.retrieve(batch_id)
            if batch.status in TERMINAL:
                break
            self._sleep(self._poll)
        for file_id in (batch.output_file_id, getattr(batch, "error_file_id", None)):
            if file_id:
                yield from (line for line in self._client.files.content(file_id).text.splitlines() if line.strip())

    def submit_lines(self, lines: Sequence[dict], kind: str, endpoint: str) -> list[str]:
        return [self._submit(list(lines[i:i + self._max]), kind, endpoint, i // self._max)
                for i in range(0, len(lines), self._max)]

    def run(self, tasks: Sequence[LlmTask], kind: str) -> Iterator[LlmOutcome]:
        from swiss_grounding.corpus.providers import OpenAILLM
        lines = [{"custom_id": t.custom_id, "method": "POST", "url": CHAT_ENDPOINT, "body": OpenAILLM.chat_body(t)}
                 for t in tasks]
        for batch_id in self.submit_lines(lines, kind, CHAT_ENDPOINT):
            for line in self.collect(batch_id):
                yield parse_batch_line(line)
```

- [ ] **Step 4: Run to pass** — `uv run pytest tests/unit/corpus/test_runner.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/runner.py tests/unit/corpus/test_runner.py
git commit -m "feat: synchronous and OpenAI Batch task runners"
```

---

### Task 16: OCR stage

**Files:**
- Create: `src/swiss_grounding/corpus/ocr.py`
- Test: `tests/integration/test_corpus_ocr.py`

Selects chunks with `needs_ocr = true`, builds one `LlmTask` per page image (model `corpus_ocr_model`, 2,500 output tokens), writes the transcription into `chunk.text`, clears `needs_ocr`, sets the document's `extraction = 'ocr'`, records spend under kind `ocr`. `estimate_ocr` prices the pending pages with `OCR_IMAGE_TOKENS` input and 700 output tokens each. A reply without a `text` string, or with empty text, quarantines the page.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_corpus_ocr.py
from datetime import UTC, datetime

import pytest
from PIL import Image

from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.ocr import OCR_PROMPT, build_ocr_tasks, estimate_ocr, run_ocr
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import SyncRunner
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
SPEC = SourceSpec(id="ahv", name="AHV", publisher="AHV/IV Informationsstelle", authority="official_info",
                  level="federal", extent_id="CH", connector="html", tier=1, languages=("de",), config={})


def _seed(conn, tmp_path):
    image = tmp_path / "p1.png"
    Image.new("RGB", (10, 10), "white").save(image)
    doc = ParsedDocument(source_id="ahv", url="https://ahv/m.pdf", language="de", work_key="pdf:https://ahv/m.pdf",
                         title="Merkblatt", extraction="pdf_text",
                         sections=(ParsedSection("de:p1", ("Merkblatt", "p. 1"), "page=1", "", needs_ocr=True,
                                                 ocr_image=str(image)),))
    upsert_source(conn, SPEC)
    persist_document(conn, doc, SPEC, datetime(2026, 9, 24, tzinfo=UTC))


def test_ocr_fills_text_and_marks_document(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
        assert len(tasks) == 1 and tasks[0].image_png_b64 and tasks[0].user == OCR_PROMPT
        assert estimate_ocr(conn, model="gpt-5-mini") > 0
    runner = SyncRunner(FakeLLM(lambda t: {"text": "1 Die AHV-Rente wird berechnet."}), workers=1)
    report = run_ocr(corpus_db, runner, tasks, model="gpt-5-mini", batch=False)
    with connect(corpus_db) as conn:
        chunk = conn.execute("select text, needs_ocr from corpus.chunk").fetchone()
        doc = conn.execute("select extraction from corpus.document").fetchone()
        spend = conn.execute("select kind from corpus.llm_spend").fetchone()
    assert chunk["text"].startswith("1 Die AHV-Rente") and chunk["needs_ocr"] is False
    assert doc["extraction"] == "ocr" and spend["kind"] == "ocr"
    assert report == {"done": 1, "failed": 0}


def test_empty_transcription_is_quarantined(corpus_db, tmp_path):
    with connect(corpus_db) as conn:
        _seed(conn, tmp_path)
        tasks = build_ocr_tasks(conn, model="gpt-5-mini", limit=None)
    report = run_ocr(corpus_db, SyncRunner(FakeLLM(lambda t: {"text": ""}), workers=1), tasks,
                     model="gpt-5-mini", batch=False)
    with connect(corpus_db) as conn:
        assert conn.execute("select count(*) as n from corpus.quarantine where stage = 'ocr'").fetchone()["n"] == 1
    assert report == {"done": 0, "failed": 1}
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/ocr.py
import base64

import psycopg

from swiss_grounding.corpus.budget import OCR_IMAGE_TOKENS, cost_usd, record_spend
from swiss_grounding.corpus.persist import quarantine
from swiss_grounding.corpus.runner import LlmTask
from swiss_grounding.db.connection import connect

OCR_SYSTEM = "You transcribe scanned pages of official Swiss documents. Reply with JSON only."
OCR_PROMPT = (
    "Transcribe this scanned page verbatim in its original language. Keep headings, article and paragraph "
    "numbers, list letters and table rows (one row per line, cells separated by ' | '). Do not correct, "
    "translate, summarise or complete anything. Write [illegible] where text cannot be read. "
    'Reply as {"text": "<the transcription>"}.'
)
OCR_OUTPUT_TOKENS = 700
OCR_MAX_OUTPUT_TOKENS = 2500


def _pending(conn: psycopg.Connection, limit: int | None) -> list[dict]:
    return conn.execute(
        "select id, language, ocr_image from corpus.chunk where needs_ocr and text = '' "
        "and status in ('current','scheduled') order by id limit %s", (limit,)).fetchall()


def build_ocr_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    tasks = []
    for row in _pending(conn, limit):
        with open(row["ocr_image"], "rb") as handle:
            image = base64.b64encode(handle.read()).decode()
        tasks.append(LlmTask(custom_id=f"ocr|{row['language']}|{row['id']}", model=model, system=OCR_SYSTEM,
                             user=OCR_PROMPT, image_png_b64=image, max_output_tokens=OCR_MAX_OUTPUT_TOKENS))
    return tasks


def estimate_ocr(conn: psycopg.Connection, model: str, image_tokens: int = OCR_IMAGE_TOKENS) -> float:
    pages = conn.execute("select count(*) as n from corpus.chunk where needs_ocr and text = '' "
                         "and status in ('current','scheduled')").fetchone()["n"]
    return pages * cost_usd(model, image_tokens + 200, OCR_OUTPUT_TOKENS)


def run_ocr(database_url: str, runner, tasks: list[LlmTask], model: str, batch: bool) -> dict[str, int]:
    report = {"done": 0, "failed": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="ocr"):
            _, language, chunk_id = outcome.custom_id.split("|")
            if outcome.input_tokens or outcome.output_tokens:
                record_spend(conn, kind="ocr", model=model, usd=cost_usd(model, outcome.input_tokens,
                             outcome.output_tokens, batch=batch), input_tokens=outcome.input_tokens,
                             output_tokens=outcome.output_tokens, estimated=False)
            text = (outcome.data or {}).get("text") if outcome.data else None
            if not isinstance(text, str) or not text.strip():
                quarantine(conn, "ocr", f"chunk:{chunk_id}", "ocr", outcome.error or "empty transcription")
                report["failed"] += 1
            else:
                row = conn.execute(
                    "update corpus.chunk set text = %s, needs_ocr = false where id = %s and language = %s "
                    "returning document_id", (text.strip(), int(chunk_id), language)).fetchone()
                conn.execute("update corpus.document set extraction = 'ocr' where id = %s", (row["document_id"],))
                report["done"] += 1
            conn.commit()
    return report
```

- [ ] **Step 4: Run to pass**, **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/ocr.py tests/integration/test_corpus_ocr.py
git commit -m "feat: OCR scanned PDF pages with a vision model under its own spend kind"
```

---

### Task 17: Describe stage — document and chunk descriptions in every language of the group

**Files:**
- Create: `src/swiss_grounding/corpus/describe.py`
- Test: `tests/unit/corpus/test_describe_parse.py`, `tests/integration/test_corpus_describe.py`

Two passes:
1. **Documents** — one task per translation group that has live documents and no description. Input: every live language version's title, publisher and first 3,000 characters. Output `{"descriptions": {lang: str}, "topics": [ids]}`. Model `corpus_doc_model`. Written to `translation_group.description_by_lang` and `topics`.
2. **Chunks** — one task per (translation group, status, align_key) whose chunks have no description. Input: each language's breadcrumb and text (≤ 2,500 chars), the group's document description, the prior topics. Output `{"descriptions": {lang: str}, "topics": [ids], "boilerplate": bool}`. Model `corpus_chunk_model`. Each language's chunk gets its own-language description; the tsv refreshes automatically (generated column). `boilerplate: true` sets chunk status `boilerplate`.

Validation (`parse_*`): every requested language must have a non-empty string (trimmed to 600 chars); topics filtered to the 20 ids, at most 3, falling back to the prior when none remain; `boilerplate` must be a real boolean. A failure quarantines the task and leaves the chunk undescribed, so a re-run retries it.

- [ ] **Step 1: Write the failing unit test**

```python
# tests/unit/corpus/test_describe_parse.py
import pytest

from swiss_grounding.corpus.describe import parse_chunk_reply, parse_doc_reply


def test_doc_reply_needs_every_language():
    ok = parse_doc_reply({"descriptions": {"de": "Das OR.", "fr": "Le CO."}, "topics": ["work", "nonsense"]},
                         languages=("de", "fr"))
    assert ok == ({"de": "Das OR.", "fr": "Le CO."}, ["work"])
    with pytest.raises(ValueError, match="fr"):
        parse_doc_reply({"descriptions": {"de": "Das OR."}, "topics": []}, languages=("de", "fr"))


def test_chunk_reply_falls_back_to_prior_topics_and_caps_three():
    descriptions, topics, boilerplate = parse_chunk_reply(
        {"descriptions": {"de": "x"}, "topics": [], "boilerplate": False}, languages=("de",), prior=["work"])
    assert topics == ["work"] and boilerplate is False
    _, topics, _ = parse_chunk_reply(
        {"descriptions": {"de": "x"}, "topics": ["work", "health", "taxes", "family"], "boilerplate": False},
        languages=("de",), prior=[])
    assert topics == ["work", "health", "taxes"]


def test_chunk_reply_rejects_non_boolean_boilerplate():
    with pytest.raises(ValueError, match="boilerplate"):
        parse_chunk_reply({"descriptions": {"de": "x"}, "topics": [], "boilerplate": "no"}, ("de",), [])


def test_long_descriptions_are_trimmed():
    [(_, text)] = parse_doc_reply({"descriptions": {"de": "a" * 2000}, "topics": []}, ("de",))[0].items()
    assert len(text) == 600
```

- [ ] **Step 2: Write the failing integration test**

```python
# tests/integration/test_corpus_describe.py
from datetime import UTC, datetime

import pytest

from swiss_grounding.corpus.describe import (
    build_chunk_tasks, build_doc_tasks, estimate_describe, run_chunk_descriptions, run_doc_descriptions,
)
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import FakeLLM
from swiss_grounding.corpus.runner import SyncRunner
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 24, tzinfo=UTC)
SPEC = SourceSpec(id="fedlex", name="Fedlex", publisher="Federal Chancellery", authority="federal_law",
                  level="federal", extent_id="CH", connector="fedlex", tier=1, languages=("de", "fr"),
                  config={"sr_numbers": ["220"]})
TEXT = {"de": "1 Nach Ablauf der Probezeit darf der Arbeitgeber nicht kündigen.",
        "fr": "1 Après le temps d'essai, l'employeur ne peut pas résilier le contrat."}


def _seed(conn):
    upsert_source(conn, SPEC)
    for lang in ("de", "fr"):
        persist_document(conn, ParsedDocument(
            source_id="fedlex", url=f"https://f/{lang}", language=lang, work_key="eli/220", title=f"OR {lang}",
            identifier="SR 220", sections=(ParsedSection("art_336_c", (f"SR 220 OR {lang}", "Art. 336c"), "art_336_c",
                                                         TEXT[lang]),)), SPEC, NOW)


def _responder(task):
    langs = ("de", "fr")
    if task.custom_id.startswith("doc|"):
        return {"descriptions": {l: f"Obligationenrecht [{l}]" for l in langs}, "topics": ["work", "business"]}
    return {"descriptions": {"de": "Kündigungsschutz bei Krankheit", "fr": "Protection contre le licenciement"},
            "topics": ["work"], "boilerplate": False}


def test_documents_then_chunks_are_described_in_each_language(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        doc_tasks = build_doc_tasks(conn, model="gpt-5-mini", limit=None)
        assert len(doc_tasks) == 1 and '"de"' in doc_tasks[0].user and '"fr"' in doc_tasks[0].user
        assert estimate_describe(doc_tasks, model="gpt-5-mini", languages_per_task=2) > 0
    runner = SyncRunner(FakeLLM(_responder), workers=1)
    assert run_doc_descriptions(corpus_db, runner, doc_tasks, model="gpt-5-mini", batch=False) == {"done": 1, "failed": 0}
    with connect(corpus_db) as conn:
        chunk_tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
        assert len(chunk_tasks) == 1                       # one task for the aligned DE+FR pair
        assert "Obligationenrecht [de]" in chunk_tasks[0].user
    run_chunk_descriptions(corpus_db, runner, chunk_tasks, model="gpt-5-nano", batch=False)
    with connect(corpus_db) as conn:
        rows = {r["language"]: r for r in conn.execute("select language, description, topics from corpus.chunk")}
        found = conn.execute("select count(*) as n from corpus.chunk "
                             "where tsv @@ to_tsquery('sg_french', 'licenciement')").fetchone()["n"]
        assert build_chunk_tasks(conn, model="gpt-5-nano", limit=None) == []
    assert rows["de"]["description"] == "Kündigungsschutz bei Krankheit"
    assert rows["fr"]["description"] == "Protection contre le licenciement"
    assert found == 1


def test_repeated_site_furniture_is_marked_before_describing(corpus_db):
    """RAG review E2: the same chunk on three pages of one site is furniture, found without a model call."""
    from swiss_grounding.corpus.describe import mark_repeated_furniture
    site = SourceSpec(id="city", name="City", publisher="City", authority="official_info", level="municipal",
                      extent_id="CH-BE-351", connector="html", tier=1, languages=("de",), config={})
    footer = ParsedSection("de:9", ("Seite",), None, "Kontakt: Stadtverwaltung, Bundesgasse 1, 3011 Bern")
    with connect(corpus_db) as conn:
        upsert_source(conn, site)
        for i in range(3):
            persist_document(conn, ParsedDocument(
                source_id="city", url=f"https://city/{i}", language="de", work_key=f"html:{i}", title=f"Seite {i}",
                sections=(ParsedSection("de:0", ("Seite",), None, f"Eigener Inhalt {i}."), footer)), site, NOW)
        assert mark_repeated_furniture(conn, min_documents=3) == 3
        statuses = {r["text"][:7]: r["status"] for r in conn.execute("select text, status from corpus.chunk")}
        assert len(build_chunk_tasks(conn, model="gpt-5-nano", limit=None)) == 3   # only the own-content chunks
    assert statuses["Kontakt"] == "boilerplate" and statuses["Eigener"] == "current"


def test_boilerplate_chunks_leave_the_live_set(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        tasks = build_chunk_tasks(conn, model="gpt-5-nano", limit=None)
    runner = SyncRunner(FakeLLM(lambda t: {"descriptions": {"de": "Menü", "fr": "Menu"}, "topics": [],
                                           "boilerplate": True}), workers=1)
    run_chunk_descriptions(corpus_db, runner, tasks, model="gpt-5-nano", batch=False)
    with connect(corpus_db) as conn:
        assert {r["status"] for r in conn.execute("select status from corpus.chunk")} == {"boilerplate"}
```

- [ ] **Step 3: Run both to fail**, then **Step 4: Implement**

```python
# src/swiss_grounding/corpus/describe.py
import json

import psycopg

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens, record_spend
from swiss_grounding.corpus.persist import quarantine
from swiss_grounding.corpus.runner import LlmTask
from swiss_grounding.corpus.topics import TOPIC_IDS, TOPICS
from swiss_grounding.db.connection import connect

MAX_DESCRIPTION_CHARS = 600
MAX_TOPICS = 3
DOC_EXCERPT_CHARS = 3000
CHUNK_TEXT_CHARS = 2500
OUTPUT_TOKENS_PER_LANGUAGE = 90
TOPIC_LIST = "\n".join(f"- {t.id}: {t.label} ({t.covers})" for t in TOPICS)

SYSTEM = "You describe official Swiss public information for a multilingual search index. Reply with JSON only."
DOC_PROMPT = """Below are the language versions of one document published by {publisher}.
For EACH language key in the versions, write one or two sentences IN THAT LANGUAGE that say what the document is
(name the act, page or leaflet explicitly), who publishes it, and which jurisdiction it applies to ({jurisdiction}).
Then choose up to three topic ids from this list that the whole document is about:
{topics}
Reply as {{"descriptions": {{"<language>": "<sentence(s)>"}}, "topics": ["<id>"]}}.

Versions:
{versions}"""
CHUNK_PROMPT = """Document: {document}
Below is one passage of this document in each language it is published in.
For EACH language key, write one or two sentences IN THAT LANGUAGE saying what the passage covers and which
questions a resident could answer with it, using the words a resident would use. Keep legal references (article,
paragraph, letter) exact. Do not add facts that are not in the passage.
Choose up to three topic ids from the list below; the starting guess is {prior}.
Set "boilerplate" to true only if the passage is navigation, a cookie notice, contact details or other page
furniture with no substantive content.
{topics}
Reply as {{"descriptions": {{"<language>": "<sentence(s)>"}}, "topics": ["<id>"], "boilerplate": false}}.

Passage:
{versions}"""


def _descriptions(reply: dict, languages: tuple[str, ...]) -> dict[str, str]:
    given = reply.get("descriptions")
    if not isinstance(given, dict):
        raise ValueError("descriptions missing")
    out = {}
    for lang in languages:
        text = given.get(lang)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"description missing for {lang}")
        out[lang] = text.strip()[:MAX_DESCRIPTION_CHARS]
    return out


def _topics(reply: dict, prior: list[str]) -> list[str]:
    raw = reply.get("topics") if isinstance(reply.get("topics"), list) else []
    chosen = [t for t in dict.fromkeys(raw) if isinstance(t, str) and t in TOPIC_IDS][:MAX_TOPICS]
    return chosen or list(prior)


def parse_doc_reply(reply: dict, languages: tuple[str, ...]) -> tuple[dict[str, str], list[str]]:
    return _descriptions(reply, languages), _topics(reply, [])


def parse_chunk_reply(reply: dict, languages: tuple[str, ...], prior: list[str]) -> tuple[dict[str, str], list[str], bool]:
    boilerplate = reply.get("boilerplate", False)
    if not isinstance(boilerplate, bool):
        raise ValueError("boilerplate must be true or false")
    return _descriptions(reply, languages), _topics(reply, prior), boilerplate


def build_doc_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    groups = conn.execute(
        "select g.id from corpus.translation_group g where g.description_by_lang = '{}'::jsonb and exists "
        "(select 1 from corpus.document d where d.translation_group_id = g.id and d.status in ('current','scheduled')) "
        "order by g.id limit %s", (limit,)).fetchall()
    tasks = []
    for group in groups:
        docs = conn.execute(
            "select distinct on (d.language) d.id, d.language, d.title, d.publisher, l.names->'labels'->>'en' as place "
            "from corpus.document d join public.location l on l.id = d.extent_id "
            "where d.translation_group_id = %s and d.status in ('current','scheduled') "
            "order by d.language, (d.status = 'current') desc, d.id desc", (group["id"],)).fetchall()
        versions = {}
        for d in docs:
            excerpt = conn.execute("select left(string_agg(text, ' ' order by ordinal), %s) as t from corpus.chunk "
                                   "where document_id = %s", (DOC_EXCERPT_CHARS, d["id"])).fetchone()["t"] or ""
            versions[d["language"]] = {"title": d["title"], "excerpt": excerpt}
        user = DOC_PROMPT.format(publisher=docs[0]["publisher"], jurisdiction=docs[0]["place"] or "Switzerland",
                                 topics=TOPIC_LIST, versions=json.dumps(versions, ensure_ascii=False, indent=1))
        tasks.append(LlmTask(custom_id=f"doc|{group['id']}|{','.join(sorted(versions))}", model=model,
                             system=SYSTEM, user=user,
                             max_output_tokens=OUTPUT_TOKENS_PER_LANGUAGE * len(versions) + 100))
    return tasks


def build_chunk_tasks(conn: psycopg.Connection, model: str, limit: int | None) -> list[LlmTask]:
    rows = conn.execute(
        "select c.translation_group_id as gid, c.status, c.align_key, g.description_by_lang as doc, "
        "jsonb_object_agg(c.language, jsonb_build_object('breadcrumb', c.breadcrumb, 'text', left(c.text, %s))) as v, "
        "(array_agg(c.topics))[1] as prior "
        "from corpus.chunk c join corpus.translation_group g on g.id = c.translation_group_id "
        "where c.status in ('current','scheduled') and c.description = '' and c.text <> '' "
        "group by c.translation_group_id, c.status, c.align_key, g.description_by_lang "
        "order by c.translation_group_id, c.align_key limit %s", (CHUNK_TEXT_CHARS, limit)).fetchall()
    tasks = []
    for r in rows:
        languages = sorted(r["v"])
        doc = r["doc"] or {}
        document = next((doc[l] for l in languages if l in doc), next(iter(doc.values()), ""))
        user = CHUNK_PROMPT.format(document=document, prior=r["prior"] or [], topics=TOPIC_LIST,
                                   versions=json.dumps(r["v"], ensure_ascii=False, indent=1))
        tasks.append(LlmTask(custom_id=f"chunk|{r['gid']}|{r['status']}|{','.join(languages)}|{r['align_key']}",
                             model=model, system=SYSTEM, user=user,
                             max_output_tokens=OUTPUT_TOKENS_PER_LANGUAGE * len(languages) + 80))
    return tasks


def mark_repeated_furniture(conn: psycopg.Connection, min_documents: int = 3) -> int:
    """Set status 'boilerplate' on chunks whose exact text recurs in `min_documents`+ live documents of one source.

    RAG review E2: a footer, contact block or cookie notice that survived HTML cleaning is the same chunk on
    every page; finding it by repetition is free, where the model's verdict is paid per copy. Law is exempt:
    identical articles across acts ("Aufgehoben") are rare, legitimate, and carry different breadcrumbs.
    Returns the number of chunks marked.
    """
    return conn.execute(
        "with live as (select c.id, c.language, c.chunk_hash, d.source_id, c.document_id from corpus.chunk c "
        "join corpus.document d on d.id = c.document_id where c.status in ('current','scheduled') "
        "and c.text <> '' and d.authority not in ('federal_law','cantonal_law','municipal_law')), "
        "repeated as (select source_id, chunk_hash from live group by source_id, chunk_hash "
        "having count(distinct document_id) >= %s) "
        "update corpus.chunk c set status = 'boilerplate' from live l join repeated r "
        "on r.source_id = l.source_id and r.chunk_hash = l.chunk_hash "
        "where c.id = l.id and c.language = l.language", (min_documents,)).rowcount


def estimate_describe(tasks: list[LlmTask], model: str, languages_per_task: float = 2.0) -> float:
    input_tokens = sum(estimate_tokens(t.system + t.user) for t in tasks)
    output_tokens = int(len(tasks) * (OUTPUT_TOKENS_PER_LANGUAGE * languages_per_task + 40))
    return cost_usd(model, input_tokens, output_tokens)


def _spend(conn, kind: str, model: str, outcome, batch: bool) -> None:
    if outcome.input_tokens or outcome.output_tokens:
        record_spend(conn, kind=kind, model=model,
                     usd=cost_usd(model, outcome.input_tokens, outcome.output_tokens, batch=batch),
                     input_tokens=outcome.input_tokens, output_tokens=outcome.output_tokens, estimated=False)


def run_doc_descriptions(database_url: str, runner, tasks: list[LlmTask], model: str, batch: bool) -> dict[str, int]:
    report = {"done": 0, "failed": 0}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-doc"):
            _, gid, langs = outcome.custom_id.split("|")
            _spend(conn, "describe", model, outcome, batch)
            try:
                if outcome.data is None:
                    raise ValueError(outcome.error or "no reply")
                descriptions, topics = parse_doc_reply(outcome.data, tuple(langs.split(",")))
            except ValueError as exc:
                quarantine(conn, "describe", f"group:{gid}", "describe-doc", str(exc))
                report["failed"] += 1
            else:
                conn.execute("update corpus.translation_group set description_by_lang = %s, topics = %s where id = %s",
                             (json.dumps(descriptions, ensure_ascii=False), topics, gid))
                report["done"] += 1
            conn.commit()
    return report


def run_chunk_descriptions(database_url: str, runner, tasks: list[LlmTask], model: str,
                           batch: bool) -> dict[str, int]:
    report = {"done": 0, "failed": 0}
    priors = {}
    with connect(database_url) as conn:
        for outcome in runner.run(tasks, kind="describe-chunk"):
            _, gid, status, langs, align_key = outcome.custom_id.split("|", 4)
            languages = tuple(langs.split(","))
            _spend(conn, "describe", model, outcome, batch)
            if (gid, align_key) not in priors:
                row = conn.execute("select topics from corpus.chunk where translation_group_id = %s and align_key = %s "
                                   "limit 1", (gid, align_key)).fetchone()
                priors[(gid, align_key)] = row["topics"] if row else []
            try:
                if outcome.data is None:
                    raise ValueError(outcome.error or "no reply")
                descriptions, topics, boilerplate = parse_chunk_reply(outcome.data, languages,
                                                                      priors[(gid, align_key)])
            except ValueError as exc:
                quarantine(conn, "describe", f"chunk:{gid}:{align_key}", "describe-chunk", str(exc))
                report["failed"] += 1
            else:
                for lang, text in descriptions.items():
                    conn.execute(
                        "update corpus.chunk set description = %s, topics = %s, "
                        "status = case when %s then 'boilerplate' else status end "
                        "where translation_group_id = %s and align_key = %s and language = %s and status = %s",
                        (text, topics, boilerplate, gid, align_key, lang, status))
                report["done"] += 1
            conn.commit()
    return report
```

- [ ] **Step 5: Run both to pass**

Run: `uv run pytest tests/unit/corpus/test_describe_parse.py -q` and the integration file. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/corpus/describe.py tests/unit/corpus/test_describe_parse.py tests/integration/test_corpus_describe.py
git commit -m "feat: per-language document and chunk descriptions with topics, one call per translation group"
```

---

### Task 18: Embed stage — OpenAI Batch, local bge-m3, HNSW build

**Files:**
- Create: `src/swiss_grounding/corpus/embed.py`
- Test: `tests/unit/corpus/test_embed_text.py`, `tests/integration/test_corpus_embed.py`

The embedded text is `breadcrumb (joined by " > ")` + newline + `description` + newline + `text`, truncated to 12,000 characters. `text_hash` is its SHA-256; a chunk whose stored `text_hash` differs from the current text (description or text changed) is re-embedded. Chunks with status `current` or `scheduled` and non-empty text are eligible; `--require-description` (default on) skips undescribed chunks so nothing is embedded twice.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/corpus/test_embed_text.py
from swiss_grounding.corpus.embed import MAX_EMBED_CHARS, embedding_text


def test_embedding_text_joins_breadcrumb_description_and_text():
    assert embedding_text(["SR 220 OR", "Art. 336c"], "Kündigungsschutz", "1 Nach Ablauf") == \
        "SR 220 OR > Art. 336c\nKündigungsschutz\n1 Nach Ablauf"


def test_embedding_text_skips_empty_parts_and_truncates():
    assert embedding_text([], "", "x") == "x"
    assert len(embedding_text(["a"], "b", "c" * 20000)) == MAX_EMBED_CHARS
```

```python
# tests/integration/test_corpus_embed.py
from datetime import UTC, datetime

import pytest

from swiss_grounding.corpus.embed import build_vector_indexes, embed_local, pending_for_index
from swiss_grounding.corpus.models import ParsedDocument, ParsedSection, SourceSpec
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.corpus.providers import INDEXES, FakeEmbeddings
from swiss_grounding.db.connection import connect

pytestmark = pytest.mark.integration
SPEC = SourceSpec(id="s", name="S", publisher="P", authority="official_info", level="federal", extent_id="CH",
                  connector="html", tier=1, languages=("de",), config={})


def _seed(conn):
    upsert_source(conn, SPEC)
    persist_document(conn, ParsedDocument(source_id="s", url="u", language="de", work_key="k", title="T",
                     sections=(ParsedSection("de:0", ("T",), None, "Leinenpflicht im Wald."),)),
                     SPEC, datetime(2026, 9, 24, tzinfo=UTC))
    conn.execute("update corpus.chunk set description = 'Hunde an der Leine'")


@pytest.mark.parametrize("index", ["bge-m3", "openai-3l"])
def test_local_embedding_fills_the_index_once(corpus_db, index):
    with connect(corpus_db) as conn:
        _seed(conn)
        assert len(pending_for_index(conn, INDEXES[index], require_description=True, limit=None)) == 1
    written = embed_local(corpus_db, INDEXES[index], FakeEmbeddings(INDEXES[index].dim), batch_size=8)
    with connect(corpus_db) as conn:
        assert written == 1
        assert pending_for_index(conn, INDEXES[index], require_description=True, limit=None) == []
        conn.execute("update corpus.chunk set description = 'geändert'")
        assert len(pending_for_index(conn, INDEXES[index], require_description=True, limit=None)) == 1


class FakeSparseBge:
    dim = 1024

    def embed_with_sparse(self, texts):
        return [(FakeEmbeddings(1024).embed([t])[0], {7: 0.9, 42: 0.3}) for t in texts]


def test_bge_m3_stores_the_sparse_vector(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["bge-m3"], FakeSparseBge(), batch_size=8)
    with connect(corpus_db) as conn:
        row = conn.execute("select sparse::text as s from corpus.emb_bge_m3").fetchone()
    assert row["s"] == "{8:0.9,43:0.3}/250002"          # pgvector prints 1-based indices


def test_unchanged_chunk_of_a_new_version_reuses_the_vector(corpus_db):
    """RAG review E3: identical embedded text is copied, not re-embedded."""
    calls = []

    class CountingFake(FakeEmbeddings):
        def embed(self, texts):
            calls.append(len(texts))
            return super().embed(texts)

    with connect(corpus_db) as conn:
        _seed(conn)
    embed_local(corpus_db, INDEXES["bge-m3"], CountingFake(1024), batch_size=8)
    with connect(corpus_db) as conn:
        persist_document(conn, ParsedDocument(source_id="s", url="u2", language="de", work_key="k", title="T",
                         sections=(ParsedSection("de:0", ("T",), None, "Leinenpflicht im Wald."),)),
                         SPEC, datetime(2026, 9, 25, tzinfo=UTC))
        conn.execute("update corpus.chunk set description = 'Hunde an der Leine' where description = ''")
    embed_local(corpus_db, INDEXES["bge-m3"], CountingFake(1024), batch_size=8)
    with connect(corpus_db) as conn:
        n = conn.execute("select count(*) as n from corpus.emb_bge_m3").fetchone()["n"]
    assert calls == [1] and n == 2


def test_undescribed_chunks_wait(corpus_db):
    with connect(corpus_db) as conn:
        _seed(conn)
        conn.execute("update corpus.chunk set description = ''")
        assert pending_for_index(conn, INDEXES["bge-m3"], require_description=True, limit=None) == []


def test_hnsw_indexes_are_built_per_language(corpus_db):
    build_vector_indexes(corpus_db, INDEXES["bge-m3"])
    with connect(corpus_db) as conn:
        names = {r["indexname"] for r in conn.execute(
            "select indexname from pg_indexes where schemaname = 'corpus' and indexname like 'emb_bge_m3_%%_hnsw'")}
    assert names == {f"emb_bge_m3_{l}_hnsw" for l in ("de", "fr", "it", "en", "rm")}
    with connect(corpus_db) as conn:
        sparse = {r["indexname"] for r in conn.execute(
            "select indexname from pg_indexes where schemaname = 'corpus' and indexname like '%%_sparse_hnsw'")}
    assert len(sparse) == 5
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/corpus/embed.py
import hashlib
import json
import logging

import numpy as np
import psycopg
from pgvector import HalfVector, SparseVector

from swiss_grounding.corpus.budget import cost_usd, estimate_tokens, record_spend
from swiss_grounding.corpus.providers import IndexSpec
from swiss_grounding.corpus.runner import EMBEDDINGS_ENDPOINT
from swiss_grounding.db.connection import connect

log = logging.getLogger(__name__)
MAX_EMBED_CHARS = 12_000
LANGS = ("de", "fr", "it", "en", "rm")


def embedding_text(breadcrumb, description: str, text: str) -> str:
    parts = [" > ".join(breadcrumb or []), description or "", text or ""]
    return "\n".join(p for p in parts if p)[:MAX_EMBED_CHARS]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def pending_for_index(conn: psycopg.Connection, index: IndexSpec, require_description: bool,
                      limit: int | None) -> list[dict]:
    rows = conn.execute(
        f"select c.id, c.language, c.breadcrumb, c.description, c.text, e.text_hash as stored "
        f"from corpus.chunk c left join {index.table} e on e.chunk_id = c.id and e.language = c.language "
        f"where c.status in ('current','scheduled') and c.text <> '' "
        f"and (not %s or c.description <> '') order by c.id limit %s",
        (require_description, limit)).fetchall()
    out = []
    for r in rows:
        text = embedding_text(r["breadcrumb"], r["description"], r["text"])
        digest = _hash(text)
        if r["stored"] != digest:
            out.append({"id": r["id"], "language": r["language"], "text": text, "hash": digest})
    return out


SPARSE_DIM = 250002   # bge-m3 vocabulary size; matches corpus.emb_bge_m3.sparse


def _write(conn: psycopg.Connection, index: IndexSpec, rows: list[tuple]) -> None:
    """rows: (chunk_id, language, text_hash, dense[, sparse dict or None])."""
    wrap = HalfVector if index.opclass.startswith("halfvec") else (lambda v: v)
    with_sparse = index.name == "bge-m3"
    cols = "chunk_id, language, text_hash, embedding" + (", sparse" if with_sparse else "")
    marks = "%s,%s,%s,%s" + (",%s" if with_sparse else "")
    update = "text_hash = excluded.text_hash, embedding = excluded.embedding" + (
        ", sparse = excluded.sparse" if with_sparse else "")
    values = []
    for row in rows:
        cid, lang, digest, vec = row[:4]
        item = [cid, lang, digest, wrap(np.asarray(vec, dtype=np.float32))]
        if with_sparse:
            sparse = row[4] if len(row) > 4 else None
            item.append(SparseVector(sparse, SPARSE_DIM) if sparse else None)
        values.append(tuple(item))
    with conn.cursor() as cur:
        cur.executemany(f"insert into {index.table} ({cols}) values ({marks}) "
                        f"on conflict (chunk_id, language) do update set {update}", values)


def reuse_embeddings(conn: psycopg.Connection, index: IndexSpec) -> int:
    """Copy vectors from an earlier version's chunk with the identical embedded text (RAG review E3).

    Identity is the text_hash of breadcrumb + description + text, so anything that would change the vector
    is re-embedded instead. Returns the number of vectors copied.
    """
    sparse_col = ", sparse" if index.name == "bge-m3" else ""
    pending = pending_for_index(conn, index, require_description=True, limit=None)
    if not pending:
        return 0
    copied = 0
    with conn.cursor() as cur:
        for p in pending:
            cur.execute(
                f"insert into {index.table} (chunk_id, language, text_hash, embedding{sparse_col}) "
                f"select %s, %s, e.text_hash, e.embedding{sparse_col.replace(', ', ', e.')} from {index.table} e "
                f"where e.text_hash = %s and e.language = %s limit 1 "
                f"on conflict (chunk_id, language) do update set text_hash = excluded.text_hash, "
                f"embedding = excluded.embedding{', sparse = excluded.sparse' if sparse_col else ''}",
                (p["id"], p["language"], p["hash"], p["language"]))
            copied += cur.rowcount
    return copied


def embed_local(database_url: str, index: IndexSpec, provider, batch_size: int = 256,
                require_description: bool = True) -> int:
    """Embed pending chunks with an in-process provider, committing every batch (resumable).

    Vectors of unchanged chunks are copied first; a provider with `embed_with_sparse` also fills `sparse`.
    """
    written = 0
    with connect(database_url) as conn:
        if require_description:
            log.info("%s: reused %d vector(s) from earlier versions", index.name, reuse_embeddings(conn, index))
            conn.commit()
        pending = pending_for_index(conn, index, require_description, None)
        for start in range(0, len(pending), batch_size):
            part = pending[start:start + batch_size]
            texts = [p["text"] for p in part]
            if hasattr(provider, "embed_with_sparse"):
                pairs = provider.embed_with_sparse(texts)
            else:
                pairs = [(v, None) for v in provider.embed(texts)]
            _write(conn, index, [(p["id"], p["language"], p["hash"], dense, sparse)
                                 for p, (dense, sparse) in zip(part, pairs, strict=True)])
            conn.commit()
            written += len(part)
            log.info("%s: %d / %d embedded", index.name, written, len(pending))
    return written


def estimate_embeddings(pending: list[dict], model: str) -> float:
    return cost_usd(model, sum(estimate_tokens(p["text"]) for p in pending), 0)


def embed_openai_batch(database_url: str, index: IndexSpec, batch_runner, pending: list[dict]) -> int:
    """Embed through the Batch API (half price). custom_id = '<lang>|<chunk_id>|<hash>'."""
    lines = [{"custom_id": f"{p['language']}|{p['id']}|{p['hash']}", "method": "POST", "url": EMBEDDINGS_ENDPOINT,
              "body": {"model": index.model, "input": p["text"]}} for p in pending]
    written = 0
    for batch_id in batch_runner.submit_lines(lines, "embed", EMBEDDINGS_ENDPOINT):
        with connect(database_url) as conn:
            tokens, rows = 0, []
            for raw in batch_runner.collect(batch_id):
                record = json.loads(raw)
                response = record.get("response") or {}
                if response.get("status_code") != 200:
                    continue
                lang, cid, digest = record["custom_id"].split("|")
                body = response["body"]
                tokens += body.get("usage", {}).get("prompt_tokens", 0)
                rows.append((int(cid), lang, digest, body["data"][0]["embedding"]))
                if len(rows) >= 1000:
                    _write(conn, index, rows)
                    written += len(rows)
                    rows = []
            if rows:
                _write(conn, index, rows)
                written += len(rows)
            record_spend(conn, kind="embed", model=index.model, usd=cost_usd(index.model, tokens, 0),
                         input_tokens=tokens, output_tokens=0, estimated=False)
    return written


def build_vector_indexes(database_url: str, index: IndexSpec) -> None:
    """HNSW per language partition. Build after bulk loading: inserting into a live HNSW index is far slower."""
    table = index.table.split(".")[1]
    with connect(database_url) as conn:
        conn.execute("set maintenance_work_mem = '1GB'")
        for lang in LANGS:
            conn.execute(f"create index if not exists {table}_{lang}_hnsw on corpus.{table}_{lang} "
                         f"using hnsw (embedding {index.opclass}) with (m = 16, ef_construction = 64)")
            if index.name == "bge-m3":
                # Inner product is the scoring bge-m3's lexical weights are trained for (RAG review E1).
                conn.execute(f"create index if not exists {table}_{lang}_sparse_hnsw on corpus.{table}_{lang} "
                             f"using hnsw (sparse sparsevec_ip_ops) with (m = 16, ef_construction = 64)")
            conn.commit()
```

If `pgvector.HalfVector` is missing, upgrade: `uv add "pgvector>=0.3.2"` (the `HalfVector` type and its psycopg adapter arrived in 0.3.0).

- [ ] **Step 4: Run to pass**, **Step 5: Commit**

```bash
git add src/swiss_grounding/corpus/embed.py tests/unit/corpus/test_embed_text.py tests/integration/test_corpus_embed.py
git commit -m "feat: embed chunks into the OpenAI and bge-m3 indexes, re-embedding on change"
```

---

### Task 19: The `corpus` CLI

**Files:**
- Create: `src/swiss_grounding/cli/corpus_commands.py`
- Modify: `src/swiss_grounding/cli/main.py` (register the sub-app next to `eval_app`)
- Test: `tests/integration/test_corpus_cli.py`

Commands:

| Command | Does |
|---|---|
| `corpus init` | `apply_schema` (public, EMBEDDING_DIM) + `apply_corpus_schema` |
| `corpus check-manifest PATH` | validates the manifest; every `extent_id` exists; for html sources GETs each start URL and prints status, final URL, robots verdict, hreflang count; for fedlex queries each SR in German; exit 1 on any problem |
| `corpus fetch --manifest PATH --tier N [--source ID]... [--workers 4]` | Task 12 with real connectors |
| `corpus estimate` | prints pending OCR pages, document tasks, chunk tasks, embeddings per index, with USD estimates and the ledger total |
| `corpus ocr [--pilot N] [--sync] [--limit N] [--dry-run]` | `--pilot N`: sync OCR of N pages, prints measured USD per page and the projection for all pending pages; otherwise checks the OCR sub-cap and runs in batch |
| `corpus describe --what docs|chunks [--sync] [--limit N] [--dry-run]` | Task 17 with the cap check |
| `corpus embed --index openai-3l|bge-m3 [--sync] [--limit N] [--dry-run] [--allow-undescribed]` | OpenAI via Batch (or sync), bge-m3 locally |
| `corpus index --index NAME` | builds HNSW |
| `corpus status` | documents by source/language/status, chunks described, embeddings per index, spend per kind, quarantine count |

Every paid command runs `ensure_within(total_cap=settings.corpus_budget_usd, …)` before submitting, and `--dry-run` only prints.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_corpus_cli.py
import pytest
from typer.testing import CliRunner

from swiss_grounding.cli.main import app

pytestmark = pytest.mark.integration
MANIFEST = """
version: 1
sources:
  - id: tiny
    name: Tiny
    publisher: Tiny
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 1
    languages: [de]
    config: {start_urls: ["http://127.0.0.1:9/"], allow_prefixes: ["http://127.0.0.1:9/"]}
"""


def test_init_status_and_estimate_run(corpus_db):
    runner = CliRunner()
    assert runner.invoke(app, ["corpus", "init"]).exit_code == 0
    status = runner.invoke(app, ["corpus", "status"])
    assert status.exit_code == 0 and "spend" in status.output.lower()
    assert runner.invoke(app, ["corpus", "estimate"]).exit_code == 0


def test_check_manifest_reports_an_unreachable_start_url(corpus_db, tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MANIFEST)
    result = CliRunner().invoke(app, ["corpus", "check-manifest", str(path)])
    assert result.exit_code == 1 and "tiny" in result.output


def test_describe_dry_run_spends_nothing(corpus_db):
    result = CliRunner().invoke(app, ["corpus", "describe", "--what", "chunks", "--dry-run"])
    assert result.exit_code == 0 and "estimate" in result.output.lower()
```

- [ ] **Step 2: Run to fail**, then **Step 3: Implement**

```python
# src/swiss_grounding/cli/corpus_commands.py
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import typer

from swiss_grounding.config import Settings, load_settings
from swiss_grounding.corpus.budget import ensure_within, spent
from swiss_grounding.corpus.connectors.fedlex import FedlexConnector
from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.connectors.pdf import PdfConnector
from swiss_grounding.corpus.db import apply_corpus_schema
from swiss_grounding.corpus.describe import (
    build_chunk_tasks, build_doc_tasks, estimate_describe, mark_repeated_furniture, run_chunk_descriptions,
    run_doc_descriptions,
)
from swiss_grounding.corpus.embed import (
    build_vector_indexes, embed_local, embed_openai_batch, estimate_embeddings, pending_for_index,
)
from swiss_grounding.corpus.fetch_stage import run_fetch
from swiss_grounding.corpus.manifest import load_manifest, select_sources
from swiss_grounding.corpus.ocr import build_ocr_tasks, estimate_ocr, run_ocr
from swiss_grounding.corpus.providers import (
    INDEXES, AnthropicLLM, FakeEmbeddings, FakeLLM, LocalBgeM3, OpenAIEmbeddings, OpenAILLM,
)
from swiss_grounding.corpus.runner import BatchRunner, SyncRunner
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

corpus_app = typer.Typer(help="Encoding track: fetch, describe, OCR and embed the declared-scope corpus.")


def _http(settings: Settings) -> httpx.Client:
    return httpx.Client(headers={"user-agent": settings.user_agent}, timeout=settings.fetch_timeout_seconds)


def _record_batch(database_url: str):
    def record(batch_id, kind, endpoint, count, path):
        with connect(database_url) as conn:
            conn.execute("insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, "
                         "estimated_usd) values (%s,%s,%s,'submitted',%s,%s,0) on conflict (id) do nothing",
                         (batch_id, kind, endpoint, count, path))
    return record


def _llm(settings: Settings):
    if settings.corpus_llm_provider == "openai":
        return OpenAILLM(settings.openai_api_key)
    if settings.corpus_llm_provider == "anthropic":
        return _AnthropicModelOverride(AnthropicLLM(settings.anthropic_api_key, settings.corpus_anthropic_model))
    return FakeLLM(_fake_reply)


class _AnthropicModelOverride:
    """Anthropic ignores the OpenAI model names in tasks and uses its configured model."""
    def __init__(self, inner):
        self._inner = inner

    def complete(self, task):
        return self._inner.complete(task)


def _fake_reply(task) -> dict:
    langs = task.custom_id.split("|")[3 if task.custom_id.startswith("chunk|") else 2].split(",") \
        if not task.custom_id.startswith("ocr|") else []
    if task.custom_id.startswith("ocr|"):
        return {"text": "[fake transcription]"}
    return {"descriptions": {l: f"[fake description {l}]" for l in langs}, "topics": [], "boilerplate": False}


def _runner(settings: Settings, sync: bool):
    if sync or settings.corpus_llm_provider != "openai":
        return SyncRunner(_llm(settings), workers=8), False
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    return BatchRunner(client, Path(settings.data_dir) / "batches", record=_record_batch(settings.database_url)), True


@corpus_app.command("init")
def init_cmd() -> None:
    settings = load_settings()
    apply_schema(settings.database_url, settings.embedding_dim)
    apply_corpus_schema(settings.database_url)
    typer.echo("corpus schema ready")


@corpus_app.command("check-manifest")
def check_manifest_cmd(path: Path) -> None:
    settings = load_settings()
    manifest = load_manifest(path)
    problems = 0
    with connect(settings.database_url) as conn:
        extents = {r["id"] for r in conn.execute("select id from location").fetchall()}
    http = _http(settings)
    for entry in manifest.sources:
        if entry.extent_id not in extents:
            typer.echo(f"{entry.id}: unknown extent {entry.extent_id}")
            problems += 1
        if entry.connector == "html":
            for url in entry.config["start_urls"]:
                try:
                    response = http.get(url, follow_redirects=True)
                    alternates = len(page_meta(response.text, str(response.url)).alternates)
                    ok = response.status_code < 400
                    typer.echo(f"{entry.id}: {response.status_code} {url} -> {response.url} hreflang={alternates}")
                except httpx.HTTPError as exc:
                    ok = False
                    typer.echo(f"{entry.id}: FAILED {url} ({exc})")
                problems += 0 if ok else 1
    typer.echo(f"{problems} problem(s)")
    raise typer.Exit(1 if problems else 0)


@corpus_app.command("fetch")
def fetch_cmd(manifest: Path = typer.Option(..., "--manifest"), tier: int = typer.Option(1, "--tier"),
              source: list[str] = typer.Option([], "--source"), workers: int = typer.Option(4, "--workers")) -> None:
    settings = load_settings()
    specs = select_sources(load_manifest(manifest), tier=tier, source_ids=tuple(source))
    http = _http(settings)
    policy = CrawlPolicy(respect_robots=settings.respect_robots, delay_seconds=settings.crawl_delay_seconds)
    connectors = {"fedlex": FedlexConnector(http, date.today, settings.data_dir),
                  "html": HtmlConnector(http, policy)}
    report = run_fetch(settings.database_url, specs, connectors, PdfConnector(http, settings.data_dir),
                       now=lambda: datetime.now(tz=UTC), workers=workers)
    for sid, tally in report.items():
        typer.echo(f"{sid}: " + " ".join(f"{k}={v}" for k, v in sorted(tally.items())))


@corpus_app.command("estimate")
def estimate_cmd() -> None:
    settings = load_settings()
    with connect(settings.database_url) as conn:
        ocr = estimate_ocr(conn, settings.corpus_ocr_model)
        docs = build_doc_tasks(conn, settings.corpus_doc_model, None)
        chunks = build_chunk_tasks(conn, settings.corpus_chunk_model, None)
        pending = {name: pending_for_index(conn, idx, require_description=False, limit=None)
                   for name, idx in INDEXES.items()}
        total = spent(conn)
    typer.echo(f"ocr: estimate ${ocr:.2f}")
    typer.echo(f"describe docs: {len(docs)} tasks, estimate ${estimate_describe(docs, settings.corpus_doc_model):.2f}")
    typer.echo(f"describe chunks: {len(chunks)} tasks (lower bound: documents not yet described add context), "
               f"estimate ${estimate_describe(chunks, settings.corpus_chunk_model):.2f}")
    typer.echo(f"embed openai-3l: {len(pending['openai-3l'])} chunks, estimate "
               f"${estimate_embeddings(pending['openai-3l'], 'text-embedding-3-large'):.2f}")
    typer.echo(f"embed bge-m3: {len(pending['bge-m3'])} chunks, local (free)")
    typer.echo(f"spent so far: ${total:.2f} of ${settings.corpus_budget_usd:.2f}")


@corpus_app.command("ocr")
def ocr_cmd(pilot: int = typer.Option(0, "--pilot"), sync: bool = typer.Option(False, "--sync"),
            limit: int | None = typer.Option(None, "--limit"), dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    settings = load_settings()
    model = settings.corpus_ocr_model
    with connect(settings.database_url) as conn:
        estimate = estimate_ocr(conn, model)
        typer.echo(f"ocr estimate for all pending pages: ${estimate:.2f}")
        if dry_run:
            return
        tasks = build_ocr_tasks(conn, model, pilot or limit)
        if not tasks:
            typer.echo("no pages need OCR")
            return
        ensure_within(conn, estimate=estimate if not pilot else estimate * pilot / max(1, len(tasks)),
                      total_cap=settings.corpus_budget_usd, kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
        before = spent(conn, "ocr")
    runner, batch = _runner(settings, sync or bool(pilot))
    report = run_ocr(settings.database_url, runner, tasks, model=model, batch=batch)
    if pilot:
        with connect(settings.database_url) as conn:
            per_page = (spent(conn, "ocr") - before) / max(1, report["done"])
            remaining = conn.execute("select count(*) as n from corpus.chunk where needs_ocr").fetchone()["n"]
        typer.echo(f"pilot: {report} — ${per_page:.4f} per page (sync price); batch projection for {remaining} "
                   f"remaining pages: ${per_page / 2 * remaining:.2f}")
    else:
        typer.echo(str(report))


@corpus_app.command("describe")
def describe_cmd(what: str = typer.Option(..., "--what"), sync: bool = typer.Option(False, "--sync"),
                 limit: int | None = typer.Option(None, "--limit"),
                 dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    if what not in ("docs", "chunks"):
        raise typer.BadParameter("--what must be docs or chunks")
    settings = load_settings()
    model = settings.corpus_doc_model if what == "docs" else settings.corpus_chunk_model
    with connect(settings.database_url) as conn:
        if what == "chunks" and not dry_run:
            typer.echo(f"marked {mark_repeated_furniture(conn)} repeated furniture chunk(s) as boilerplate")
            conn.commit()
        tasks = (build_doc_tasks if what == "docs" else build_chunk_tasks)(conn, model, limit)
        estimate = estimate_describe(tasks, model)
        typer.echo(f"{what}: {len(tasks)} tasks, estimate ${estimate:.2f}")
        if dry_run or not tasks:
            return
        ensure_within(conn, estimate=estimate, total_cap=settings.corpus_budget_usd)
    runner, batch = _runner(settings, sync)
    run = run_doc_descriptions if what == "docs" else run_chunk_descriptions
    typer.echo(str(run(settings.database_url, runner, tasks, model=model, batch=batch)))


@corpus_app.command("embed")
def embed_cmd(index: str = typer.Option(..., "--index"), sync: bool = typer.Option(False, "--sync"),
              limit: int | None = typer.Option(None, "--limit"), dry_run: bool = typer.Option(False, "--dry-run"),
              allow_undescribed: bool = typer.Option(False, "--allow-undescribed")) -> None:
    settings = load_settings()
    spec = INDEXES[index]
    with connect(settings.database_url) as conn:
        pending = pending_for_index(conn, spec, require_description=not allow_undescribed, limit=limit)
        estimate = estimate_embeddings(pending, spec.model) if spec.provider == "openai" else 0.0
        typer.echo(f"{index}: {len(pending)} chunks pending, estimate ${estimate:.2f}")
        if dry_run or not pending:
            return
        if spec.provider == "openai":
            ensure_within(conn, estimate=estimate, total_cap=settings.corpus_budget_usd)
    if spec.provider == "local":
        provider = FakeEmbeddings(spec.dim) if settings.embedding_backend == "fake" else LocalBgeM3(spec.model)
        typer.echo(f"written: {embed_local(settings.database_url, spec, provider, batch_size=64, require_description=not allow_undescribed)}")
    elif sync or settings.corpus_llm_provider != "openai":
        provider = OpenAIEmbeddings(settings.openai_api_key) if settings.openai_api_key else FakeEmbeddings(spec.dim)
        typer.echo(f"written: {embed_local(settings.database_url, spec, provider, batch_size=128, require_description=not allow_undescribed)}")
    else:
        runner, _ = _runner(settings, sync=False)
        typer.echo(f"written: {embed_openai_batch(settings.database_url, spec, runner, pending)}")


@corpus_app.command("index")
def index_cmd(index: str = typer.Option(..., "--index")) -> None:
    settings = load_settings()
    build_vector_indexes(settings.database_url, INDEXES[index])
    typer.echo(f"{index}: HNSW indexes built")


@corpus_app.command("status")
def status_cmd() -> None:
    settings = load_settings()
    with connect(settings.database_url) as conn:
        for r in conn.execute("select source_id, language, status, count(*) as n from corpus.document "
                              "group by 1,2,3 order by 1,2,3").fetchall():
            typer.echo(f"documents {r['source_id']:<28} {r['language']} {r['status']:<11} {r['n']}")
        c = conn.execute("select count(*) filter (where status in ('current','scheduled')) as live, "
                         "count(*) filter (where status in ('current','scheduled') and description <> '') as described, "
                         "count(*) filter (where needs_ocr) as ocr from corpus.chunk").fetchone()
        typer.echo(f"chunks live={c['live']} described={c['described']} awaiting_ocr={c['ocr']}")
        for name, spec in INDEXES.items():
            n = conn.execute(f"select count(*) as n from {spec.table}").fetchone()["n"]
            typer.echo(f"embeddings {name}: {n}")
        for r in conn.execute("select kind, sum(usd) as usd from corpus.llm_spend group by kind").fetchall():
            typer.echo(f"spend {r['kind']}: ${float(r['usd']):.2f}")
        typer.echo(f"spend total: ${spent(conn):.2f} of ${settings.corpus_budget_usd:.2f}")
        q = conn.execute("select count(*) as n from corpus.quarantine").fetchone()["n"]
        typer.echo(f"quarantine: {q}")
```

Register it in `src/swiss_grounding/cli/main.py`, next to where `eval_app` is added:

```python
from swiss_grounding.cli.corpus_commands import corpus_app
...
app.add_typer(corpus_app, name="corpus")
```

(Find the existing `app.add_typer(eval_app, ...)` line with `grep -n add_typer src/swiss_grounding/cli/main.py` and add the new line beneath it.)

Simplify `_fake_reply` while implementing if you prefer — it only has to return valid replies for the three custom_id shapes `doc|gid|langs`, `chunk|gid|status|langs|align_key` and `ocr|lang|id`. Delete `_AnthropicModelOverride` if you make `AnthropicLLM.complete` ignore `task.model` directly (it already does, since it uses its own `self._model`); the wrapper is redundant and may be removed.

- [ ] **Step 4: Run to pass**

Run: `DATABASE_URL=... uv run pytest tests/integration/test_corpus_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Full suite and lint**

Run: `uv run pytest tests/unit -q && DATABASE_URL=... uv run pytest tests/integration -q -m integration && uv run ruff check src tests`
Expected: all pass (the two pre-existing structural-probe failures `city-001`/`city-018` documented in `docs/AUDIT.md` §10 may remain; nothing new fails).

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/cli/corpus_commands.py src/swiss_grounding/cli/main.py tests/integration/test_corpus_cli.py
git commit -m "feat: corpus CLI with estimates, cost caps, batch and sync modes"
```

---

### Task 20: The declared-scope manifest

**Files:**
- Create: `manifests/declared-scope.yaml`

Start URLs below are best guesses from 2026-09-23. **Every html entry must pass `corpus check-manifest` before the run**; fix a failing URL by opening the site and copying the real section URL, keeping the same `allow_prefixes` idea (the topic section in each language). Tier 1 is the declared scope (ADR 0009); tier 2 widens breadth.

- [ ] **Step 1: Write the manifest**

```yaml
version: 1
sources:
  # ---------------- Federal: law ----------------
  - id: fedlex
    name: Fedlex — Systematic Compilation of Federal Law
    publisher: Swiss Federal Chancellery
    authority: federal_law
    level: federal
    extent_id: CH
    connector: fedlex
    tier: 1
    languages: [de, fr, it, en]
    config:
      sr_numbers: ["101", "141.0", "142.20", "142.201", "161.1", "210", "220", "221.213.11", "281.1", "311.0",
                   "455", "631.0", "641.20", "642.11", "704", "741.01", "741.11", "741.51", "784.40", "814.01",
                   "814.600", "822.11", "831.10", "831.40", "832.10", "832.102", "837.0", "451"]

  # ---------------- Federal: citizen portal and offices ----------------
  - id: ch_ch
    name: ch.ch — the Swiss authorities online
    publisher: Swiss Confederation, cantons and communes (ch.ch)
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en, rm]
    config:
      start_urls: ["https://www.ch.ch/de/", "https://www.ch.ch/fr/", "https://www.ch.ch/it/", "https://www.ch.ch/en/", "https://www.ch.ch/rm/"]
      allow_prefixes: ["https://www.ch.ch/de/", "https://www.ch.ch/fr/", "https://www.ch.ch/it/", "https://www.ch.ch/en/", "https://www.ch.ch/rm/"]
      max_pages: 2500
      max_pdfs: 0
  - id: sem
    name: State Secretariat for Migration
    publisher: State Secretariat for Migration SEM
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en]
    config:
      start_urls: ["https://www.sem.admin.ch/sem/de/home/themen/aufenthalt.html", "https://www.sem.admin.ch/sem/fr/home/themen/aufenthalt.html", "https://www.sem.admin.ch/sem/it/home/themen/aufenthalt.html", "https://www.sem.admin.ch/sem/en/home/themen/aufenthalt.html"]
      allow_prefixes: ["https://www.sem.admin.ch/sem/de/home/themen/", "https://www.sem.admin.ch/sem/fr/home/themen/", "https://www.sem.admin.ch/sem/it/home/themen/", "https://www.sem.admin.ch/sem/en/home/themen/"]
      max_pages: 600
      max_pdfs: 40
  - id: bag_kv
    name: Federal Office of Public Health — health insurance
    publisher: Federal Office of Public Health FOPH
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en]
    config:
      start_urls: ["https://www.bag.admin.ch/bag/de/home/versicherungen/krankenversicherung.html", "https://www.bag.admin.ch/bag/fr/home/versicherungen/krankenversicherung.html", "https://www.bag.admin.ch/bag/it/home/versicherungen/krankenversicherung.html", "https://www.bag.admin.ch/bag/en/home/versicherungen/krankenversicherung.html"]
      allow_prefixes: ["https://www.bag.admin.ch/bag/de/home/versicherungen/krankenversicherung", "https://www.bag.admin.ch/bag/fr/home/versicherungen/krankenversicherung", "https://www.bag.admin.ch/bag/it/home/versicherungen/krankenversicherung", "https://www.bag.admin.ch/bag/en/home/versicherungen/krankenversicherung"]
      max_pages: 400
      max_pdfs: 20
  - id: bwo
    name: Federal Office for Housing — tenancy law and reference rate
    publisher: Federal Office for Housing FOH
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it]
    config:
      start_urls: ["https://www.bwo.admin.ch/bwo/de/home/mietrecht.html", "https://www.bwo.admin.ch/bwo/fr/home/mietrecht.html", "https://www.bwo.admin.ch/bwo/it/home/mietrecht.html"]
      allow_prefixes: ["https://www.bwo.admin.ch/bwo/de/home/mietrecht", "https://www.bwo.admin.ch/bwo/fr/home/mietrecht", "https://www.bwo.admin.ch/bwo/it/home/mietrecht"]
      max_pages: 200
      max_pdfs: 20
  - id: bk_votes
    name: Federal Chancellery — political rights and votes
    publisher: Swiss Federal Chancellery
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en, rm]
    config:
      start_urls: ["https://www.bk.admin.ch/bk/de/home/politische-rechte.html", "https://www.bk.admin.ch/bk/fr/home/politische-rechte.html", "https://www.bk.admin.ch/bk/it/home/politische-rechte.html", "https://www.bk.admin.ch/bk/en/home/politische-rechte.html", "https://www.bk.admin.ch/bk/rm/home/politische-rechte.html"]
      allow_prefixes: ["https://www.bk.admin.ch/bk/de/home/politische-rechte", "https://www.bk.admin.ch/bk/fr/home/politische-rechte", "https://www.bk.admin.ch/bk/it/home/politische-rechte", "https://www.bk.admin.ch/bk/en/home/politische-rechte", "https://www.bk.admin.ch/bk/rm/home/politische-rechte"]
      max_pages: 300
      max_pdfs: 0
  - id: bazg
    name: Federal Office for Customs and Border Security — private individuals
    publisher: Federal Office for Customs and Border Security FOCBS
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en]
    config:
      start_urls: ["https://www.bazg.admin.ch/bazg/de/home/information-private.html", "https://www.bazg.admin.ch/bazg/fr/home/information-private.html", "https://www.bazg.admin.ch/bazg/it/home/information-private.html", "https://www.bazg.admin.ch/bazg/en/home/information-private.html"]
      allow_prefixes: ["https://www.bazg.admin.ch/bazg/de/home/information-private", "https://www.bazg.admin.ch/bazg/fr/home/information-private", "https://www.bazg.admin.ch/bazg/it/home/information-private", "https://www.bazg.admin.ch/bazg/en/home/information-private"]
      max_pages: 300
      max_pdfs: 10
  - id: arbeit_swiss
    name: arbeit.swiss — unemployment insurance
    publisher: State Secretariat for Economic Affairs SECO
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en]
    config:
      start_urls: ["https://www.arbeit.swiss/secoalv/de/home.html", "https://www.arbeit.swiss/secoalv/fr/home.html", "https://www.arbeit.swiss/secoalv/it/home.html", "https://www.arbeit.swiss/secoalv/en/home.html"]
      allow_prefixes: ["https://www.arbeit.swiss/secoalv/de/", "https://www.arbeit.swiss/secoalv/fr/", "https://www.arbeit.swiss/secoalv/it/", "https://www.arbeit.swiss/secoalv/en/"]
      max_pages: 400
      max_pdfs: 20
  - id: ahv_iv
    name: AHV/IV information centre — leaflets
    publisher: AHV/IV Information Centre
    authority: official_info
    level: federal
    extent_id: CH
    connector: html
    tier: 1
    languages: [de, fr, it, en]
    config:
      start_urls: ["https://www.ahv-iv.ch/de/Merkbl%C3%A4tter-Formulare/Merkbl%C3%A4tter", "https://www.ahv-iv.ch/fr/M%C3%A9mentos-Formulaires/M%C3%A9mentos", "https://www.ahv-iv.ch/it/Opuscoli-Moduli/Opuscoli", "https://www.ahv-iv.ch/en/Leaflets-forms/Leaflets"]
      allow_prefixes: ["https://www.ahv-iv.ch/de/", "https://www.ahv-iv.ch/fr/", "https://www.ahv-iv.ch/it/", "https://www.ahv-iv.ch/en/"]
      pdf_allow_prefixes: ["https://www.ahv-iv.ch/"]
      max_pages: 300
      max_pdfs: 150

  # ---------------- Cantons ----------------
  - id: zh_canton
    name: Kanton Zürich
    publisher: Kanton Zürich
    authority: official_info
    level: cantonal
    extent_id: CH-ZH
    connector: html
    tier: 1
    languages: [de]
    config:
      start_urls: ["https://www.zh.ch/de/steuern-finanzen.html", "https://www.zh.ch/de/migration-integration.html", "https://www.zh.ch/de/mobilitaet.html", "https://www.zh.ch/de/bildung.html", "https://www.zh.ch/de/soziales.html"]
      allow_prefixes: ["https://www.zh.ch/de/steuern-finanzen", "https://www.zh.ch/de/migration-integration", "https://www.zh.ch/de/mobilitaet", "https://www.zh.ch/de/bildung", "https://www.zh.ch/de/soziales", "https://www.zh.ch/de/umwelt-tiere"]
      max_pages: 800
      max_pdfs: 60
  - id: be_canton
    name: Kanton Bern / Canton de Berne
    publisher: Kanton Bern
    authority: official_info
    level: cantonal
    extent_id: CH-BE
    connector: html
    tier: 1
    languages: [de, fr]
    config:
      start_urls: ["https://www.be.ch/de/start.html", "https://www.be.ch/fr/start.html"]
      allow_prefixes: ["https://www.be.ch/de/", "https://www.be.ch/fr/"]
      max_pages: 800
      max_pdfs: 60
  - id: vd_canton
    name: Canton de Vaud
    publisher: Canton de Vaud
    authority: official_info
    level: cantonal
    extent_id: CH-VD
    connector: html
    tier: 1
    languages: [fr]
    config:
      start_urls: ["https://www.vd.ch/mobilite", "https://www.vd.ch/fiscalite", "https://www.vd.ch/population", "https://www.vd.ch/formation"]
      allow_prefixes: ["https://www.vd.ch/mobilite", "https://www.vd.ch/fiscalite", "https://www.vd.ch/population", "https://www.vd.ch/formation", "https://www.vd.ch/sante-soins-et-handicap"]
      max_pages: 800
      max_pdfs: 60
  - id: ge_canton
    name: République et canton de Genève
    publisher: République et canton de Genève
    authority: official_info
    level: cantonal
    extent_id: CH-GE
    connector: html
    tier: 1
    languages: [fr]
    config:
      start_urls: ["https://www.ge.ch/vivre-geneve", "https://www.ge.ch/dossier/vacances-scolaires"]
      allow_prefixes: ["https://www.ge.ch/"]
      max_pages: 800
      max_pdfs: 60
  - id: ti_canton
    name: Repubblica e Cantone Ticino
    publisher: Repubblica e Cantone Ticino
    authority: official_info
    level: cantonal
    extent_id: CH-TI
    connector: html
    tier: 1
    languages: [it]
    config:
      start_urls: ["https://www4.ti.ch/dfe/dc/", "https://www4.ti.ch/di/sc/", "https://www4.ti.ch/decs/"]
      allow_prefixes: ["https://www4.ti.ch/"]
      max_pages: 800
      max_pdfs: 60
  - id: gr_canton
    name: Kanton Graubünden / Chantun Grischun / Cantone dei Grigioni
    publisher: Kanton Graubünden
    authority: official_info
    level: cantonal
    extent_id: CH-GR
    connector: html
    tier: 1
    languages: [de, rm, it]
    config:
      start_urls: ["https://www.gr.ch/DE/Seiten/welcome.aspx", "https://www.gr.ch/RM/Seiten/welcome.aspx", "https://www.gr.ch/IT/Seiten/welcome.aspx"]
      allow_prefixes: ["https://www.gr.ch/DE/", "https://www.gr.ch/RM/", "https://www.gr.ch/IT/"]
      max_pages: 800
      max_pdfs: 60

  # ---------------- Municipalities ----------------
  - id: zuerich_city
    name: Stadt Zürich
    publisher: Stadt Zürich
    authority: official_info
    level: municipal
    extent_id: CH-ZH-261
    connector: html
    tier: 1
    languages: [de, en]
    config:
      start_urls: ["https://www.stadt-zuerich.ch/de/stadtleben.html", "https://www.stadt-zuerich.ch/de/umwelt-und-energie.html", "https://www.stadt-zuerich.ch/de/politik-und-verwaltung.html"]
      allow_prefixes: ["https://www.stadt-zuerich.ch/de/", "https://www.stadt-zuerich.ch/en/"]
      max_pages: 800
      max_pdfs: 60
  - id: bern_city
    name: Stadt Bern
    publisher: Stadt Bern
    authority: official_info
    level: municipal
    extent_id: CH-BE-351
    connector: html
    tier: 1
    languages: [de, fr]
    config:
      start_urls: ["https://www.bern.ch/themen", "https://www.bern.ch/politik-und-verwaltung"]
      allow_prefixes: ["https://www.bern.ch/"]
      max_pages: 800
      max_pdfs: 60
  - id: lausanne_city
    name: Ville de Lausanne
    publisher: Ville de Lausanne
    authority: official_info
    level: municipal
    extent_id: CH-VD-5586
    connector: html
    tier: 1
    languages: [fr]
    config:
      start_urls: ["https://www.lausanne.ch/vie-pratique.html", "https://www.lausanne.ch/officiel.html"]
      allow_prefixes: ["https://www.lausanne.ch/"]
      max_pages: 800
      max_pdfs: 60
  - id: geneve_city
    name: Ville de Genève
    publisher: Ville de Genève
    authority: official_info
    level: municipal
    extent_id: CH-GE-6621
    connector: html
    tier: 1
    languages: [fr]
    config:
      start_urls: ["https://www.geneve.ch/themes"]
      allow_prefixes: ["https://www.geneve.ch/themes"]
      max_pages: 600
      max_pdfs: 40
  - id: lugano_city
    name: Città di Lugano
    publisher: Città di Lugano
    authority: official_info
    level: municipal
    extent_id: CH-TI-5192
    connector: html
    tier: 1
    languages: [it]
    config:
      start_urls: ["https://www.lugano.ch/it/vivere-lugano/", "https://www.lugano.ch/it/servizi/"]
      allow_prefixes: ["https://www.lugano.ch/it/"]
      max_pages: 600
      max_pdfs: 40
  - id: chur_city
    name: Stadt Chur
    publisher: Stadt Chur
    authority: official_info
    level: municipal
    extent_id: CH-GR-3901
    connector: html
    tier: 1
    languages: [de]
    config:
      start_urls: ["https://www.chur.ch/"]
      allow_prefixes: ["https://www.chur.ch/"]
      max_pages: 500
      max_pdfs: 40
  - id: scuol_commune
    name: Vschinauncha Scuol / Gemeinde Scuol
    publisher: Gemeinde Scuol
    authority: official_info
    level: municipal
    extent_id: CH-GR-3762
    connector: html
    tier: 1
    languages: [rm, de]
    config:
      start_urls: ["https://www.scuol.net/"]
      allow_prefixes: ["https://www.scuol.net/"]
      max_pages: 300
      max_pdfs: 40
```

- [ ] **Step 2: Validate the manifest (free, needs the network)**

```bash
uv run swiss-grounding db seed          # location tree must exist
uv run swiss-grounding corpus init
uv run swiss-grounding corpus check-manifest manifests/declared-scope.yaml
```

Expected: every line `200` (or a redirect ending in `200`); `0 problem(s)`. For each failure, open the site, find the real section URL in each language, update `start_urls` and `allow_prefixes`, and re-run until clean. Record anything notable (a site blocking robots, a canton with no Romansh) in the commit message.

- [ ] **Step 3: Commit**

```bash
git add manifests/declared-scope.yaml
git commit -m "feat: declared-scope source manifest (ADR 0009), start URLs verified"
```

---

### Task 21: End-to-end rehearsal on fakes, then a free real fetch

**Files:**
- Create: `docs/ENCODING-RUNBOOK.md`

- [ ] **Step 1: Rehearse the whole pipeline with fake providers (free)**

```bash
export CORPUS_LLM_PROVIDER=fake EMBEDDING_BACKEND=fake
uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 1 --source fedlex --source ch_ch --workers 2
uv run swiss-grounding corpus estimate
uv run swiss-grounding corpus ocr --sync --limit 5
uv run swiss-grounding corpus describe --what docs --sync --limit 20
uv run swiss-grounding corpus describe --what chunks --sync --limit 200
uv run swiss-grounding corpus embed --index bge-m3 --limit 200
uv run swiss-grounding corpus status
```

Expected: fetch reports `added=` counts for both sources; the other commands run without error; `status` shows described chunks and bge-m3 embeddings. With `CORPUS_LLM_PROVIDER=fake`, the ledger must stay at `$0.00`.

Note for fake mode: set `DATA_DIR` to a scratch directory if you do not want the real crawl artifacts kept, and reset with `truncate` of the corpus tables before the real run (Step 3).

- [ ] **Step 2: Run the full real fetch (free — no model calls)**

```bash
unset CORPUS_LLM_PROVIDER EMBEDDING_BACKEND
uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 1 --workers 6
uv run swiss-grounding corpus status
uv run swiss-grounding corpus estimate
```

Expected: documents in every declared source and language; the estimate prints the paid stages. **If the estimate is above $90 in total, reduce `max_pages` on the largest HTML sources and re-fetch before the paid run** — the cap will refuse anything above $100 anyway.

- [ ] **Step 2b: Size and memory check (RAG review E5, free)**

```bash
uv run python -c "
import psycopg; c = psycopg.connect('postgresql://swiss:swiss@localhost:5433/swiss_grounding')
for r in c.execute(\"select language, count(*) from corpus.chunk where status in ('current','scheduled') group by 1 order by 1\"): print(r)
print(c.execute(\"select pg_size_pretty(pg_database_size(current_database()))\").fetchone())"
docker stats --no-stream swisscom-hackathon-db-1
docker info --format '{{.MemTotal}}'
```

Expected for the declared scope: roughly 100k–150k live chunks. Budget per language partition at build time: OpenAI `halfvec(3072)` ≈ 6 KB/vector (≈ 0.9 GB per 150k), HNSW index about the same again; bge-m3 ≈ 4 KB/vector. **If Docker's memory total is under 6 GB, raise it in Docker Desktop (Settings → Resources) before `corpus index`.** Then time one partition: build the smallest language first (`rm` or `it`), note the minutes, and extrapolate to `de`/`fr` before starting them. Write the counts, sizes and the build time into the runbook's step 12 record.

- [ ] **Step 3: Write the runbook for 2026-09-24**

```markdown
# Encoding runbook — 2026-09-24

Pre-conditions: `corpus fetch` for tier 1 has run (free); `corpus status` shows documents in every source.

1. Put the keys in `.env`: `OPENAI_API_KEY=...`, `CORPUS_LLM_PROVIDER=openai`, `CORPUS_BUDGET_USD=100`,
   `CORPUS_OCR_BUDGET_USD=10`. Check the organisation's rate limits and Batch queue limit on the OpenAI dashboard
   (Settings → Limits). If the Batch queue limit is below the embedding request count, run stages in smaller
   `--limit` slices.
2. Check prices at https://developers.openai.com/api/docs/pricing and edit `corpus/budget.py` `PRICES` if they changed.
3. `uv run swiss-grounding corpus fetch --manifest manifests/declared-scope.yaml --tier 1` (picks up changes; free).
4. `uv run swiss-grounding corpus estimate` — note the numbers.
5. OCR pilot: `uv run swiss-grounding corpus ocr --pilot 10`. Read the per-page cost and the projection.
   If the projection exceeds $10, lower `max_pdfs` or accept that only the first pages are OCR'd with
   `corpus ocr --limit N` sized to the sub-cap.
6. `uv run swiss-grounding corpus ocr` (batch).
7. `uv run swiss-grounding corpus describe --what docs --limit 5 --sync` — read the five descriptions in
   `corpus.translation_group` for quality (languages right? act named? jurisdiction right?). Then
   `uv run swiss-grounding corpus describe --what docs`.
8. `uv run swiss-grounding corpus describe --what chunks --limit 20 --sync` — spot-check; then
   `uv run swiss-grounding corpus describe --what chunks`.
9. `uv run swiss-grounding corpus embed --index openai-3l --dry-run`, then without `--dry-run`.
   (`describe --what chunks` has already marked repeated site furniture as boilerplate, so it is neither
   described nor embedded.)
10. Before building: check `docker stats` / Docker's memory limit (≥ 6 GB) and the chunk count per language
    (plan Task 21 Step 2b). Then `uv run swiss-grounding corpus index --index openai-3l`.
11. Local index (free, overnight, laptop plugged in): `uv sync --extra embed` then
    `uv run swiss-grounding corpus embed --index bge-m3` then `uv run swiss-grounding corpus index --index bge-m3`.
    With FlagEmbedding installed this also fills the sparse vectors; check with
    `select count(*) filter (where sparse is not null), count(*) from corpus.emb_bge_m3;`.
12. `uv run swiss-grounding corpus status` — record the final numbers and the spend in the commit or PR.
13. Quarantine review: `select stage, count(*) from corpus.quarantine group by 1;` — re-run a stage to retry.

If a batch step is interrupted, re-run the same command: described chunks, embedded chunks and OCR'd pages are
skipped, and submitted batches are listed in `corpus.batch_job`.
```

- [ ] **Step 4: Commit**

```bash
git add docs/ENCODING-RUNBOOK.md
git commit -m "docs: encoding runbook for the paid run"
```

- [ ] **Step 5: Open the PR**

Push over HTTPS with the gh credential helper (the SSH key belongs to another account), then open a PR from `feat/encoding-track` to `main` with the summary, the rehearsal numbers from Step 1–2, and the test plan.

---

## Self-review notes

- **RAG review amendments:** E1 sparse vectors (Tasks 2, 13 Step 6 spike, 18); E2 repeated furniture (Task 17, CLI describe); E3 reuse of descriptions (Task 11) and vectors (Task 18); E4 sequence length 2,048 (Task 13); E5 size and memory check (Task 21 Step 2b, runbook step 10).
- **Coverage of grill #1 decisions:** halfvec(3072) + bge-m3 (Tasks 2, 18); keys only at ingestion (serving is not touched); 20 topics + SR prior (1, 11, 17); law = article, split per Abs. (5, 6); descriptions per translation group in each language, nano/mini (17); OCR with pilot and $10 sub-cap (16, 19); $100 cap (14, 19); robots switch (9, 19); declared-scope sources (20); fresh schema beside the old one (ADR 0010, Task 2); language stores incl. `rm` (2); Fedlex current + scheduled + supersede (7, 11); raw artifacts kept (4).
- **Deliberately not here (serving track):** query-time search over `corpus.*`, corroboration, fusion, abstention, `outside_scope`/`source_unavailable`, live lookups, the MCP contract, the prebuilt-dump download, the README scope declaration.
- **Known limits accepted for tomorrow:** HTML versions are grouped but not aligned by position (corroboration for HTML works at document level); the Batch resume path re-attaches only when the same command is re-run; `max_pages` caps are guesses sized to the budget and should be tuned after the free fetch; cantonal law (ADR 0008) is not in tier 1.
- **Cost check before the paid run:** the free fetch in Task 21 Step 2 produces the real chunk counts; `corpus estimate` must be under the cap with room for re-runs.

---

## Amendments from plan review (2026-09-23) — these override the task text above

Found while checking the plan against the codebase before implementation. None re-opens a settled decision; each fixes a bug in the planned code. Implementers apply the amendments listed for their task, with a test for each.

**A1 — HTML pages of one language must never share a translation group (Tasks 9, 11).**
`work_key` = smallest URL among a page and its hreflang alternates. Many sites point every page's `fr` alternate at the French homepage when no translation exists, so unrelated German pages get the same key. Persistence rule 3 then supersedes page A when page B is stored, and chunk descriptions for `(group, align_key, language)` cross between pages. Two fixes:
- *Task 11:* rule 3 (a new URL retires the other `current` row of the group/language/source) applies only when `doc.valid_from is not None` — i.e. dated consolidations such as Fedlex. Undated documents (HTML, PDF) are versioned by URL only. Test: two undated documents with the same `work_key`, same language, different URLs → both stay `current`.
- *Task 9:* `HtmlConnector.run` assigns `work_key` after the crawl, from **symmetric** alternates only: page P and Q are grouped when P lists Q as an alternate and Q lists P. Groups are the connected components of those mutual links; if a component holds two pages of the same language, every page in it falls back to its own key `html:<url>`. A page whose alternates were not crawled in this run keeps `html:<url>`. Keep `html_meta.work_key` for the key format (`html:` + smallest member URL). Test: two German pages whose `fr` alternate is the same French homepage (which lists only one of them back) → different `work_key`s; the symmetric pair from the existing test still shares one.

**A2 — `build_chunk_tasks` must not `array_agg` text arrays (Task 17).**
`(array_agg(c.topics))[1]` fails with "cannot accumulate empty arrays" for every chunk whose `topics` is `'{}'` (all HTML chunks), and a one-index subscript into the resulting 2-D array returns NULL anyway. Use `(array_agg(to_jsonb(c.topics)))[1] as prior` (psycopg returns a list).

**A3 — Batch jobs are resumable and count against the cap while in flight (Tasks 14, 15, 19).**
As written, a killed process loses its submitted batches (re-running submits and pays again), and spend is recorded only after results are ingested, so a second run can pass `ensure_within` while the first run's batches are still pending.
- *Task 14:* `ensure_within` adds `sum(estimated_usd)` of `corpus.batch_job` rows with `ingested_at is null` and a status not in `('failed','expired','cancelled')` to the spent total (and per kind: batch_job.kind values are `ocr`, `describe-doc`, `describe-chunk`, `embed`; map `describe-*` to ledger kind `describe`). Test it.
- *Task 15:* `BatchRunner.__init__` takes `record(batch_id, kind, endpoint, request_count, input_path, estimated_usd)` and `mark_done(batch_id, status)`; `run(tasks, kind, estimated_usd)` and `submit_lines(lines, kind, endpoint, estimated_usd)` split the estimate across files pro rata. `collect(batch_id)` calls `mark_done(batch_id, status)` after its last line has been yielded. Add `resume(batch_ids) -> Iterator[LlmOutcome]` that collects already-submitted chat batches and parses their lines. Test resume with the fake client.
- *Task 19:* every paid command, before building tasks, looks up `corpus.batch_job` rows of its kind with `ingested_at is null` and status not terminal-failed, and ingests them first through the same `run_*` function (a small adapter runner whose `run()` yields `batch_runner.resume(ids)`); for `embed`, collect them through the same path `embed_openai_batch` uses. `mark_done` sets `status` and `ingested_at = now()`. Only then are new tasks built (so already-answered work is skipped) and submitted. Add a `corpus batches` command listing batch_job rows.

**A4 — Batch input files are split by size as well as count (Task 15).**
OpenAI caps a batch input file at 200 MB. 50,000 chunk-description lines (~10 KB each) or a few hundred OCR lines (base64 PNG) exceed it. `submit_lines` starts a new file when adding a line would pass `max_bytes` (default 150_000_000) or `max_per_file`. Test with a small `max_bytes`.

**A5 — Scheduled consolidations are promoted when their date arrives (Tasks 11, 12).**
The Fedlex connector reports a known URL as unchanged without re-emitting it, so a `scheduled` row never becomes `current` on a later fetch. Add `promote_due(conn, today) -> int` in `persist.py`: every `scheduled` document with `valid_from <= today` becomes `current` (chunks too, `boilerplate` kept) and supersedes the other `current` row of its group/language/source with `valid_to = valid_from`. `run_fetch` calls it once after all sources finish (`today = now().date()`). Test it.

**A6 — Jurisdiction name in document prompts (Task 17).**
`public.location.names` is flat (`{"de": "Bern", "en": "Bern", ...}`); there is no `labels` key. Use `l.names->>'en'`, else every document is described as applying to "Switzerland". Assert the place name appears in the doc task's prompt in the integration test (seed a municipal source).

**A7 — Reuse vectors on the paid path, and index the lookup (Tasks 2, 18, 19).**
- *Task 2:* add `create index if not exists emb_openai_3l_hash_idx on corpus.emb_openai_3l (text_hash, language)` and the same for `emb_bge_m3`.
- *Task 18/19:* `reuse_embeddings` runs before `pending_for_index` in the OpenAI paths too (batch and sync), so an unchanged chunk of a new version is never paid for twice. Do it in one set-based `insert … select` rather than one query per pending chunk if convenient.

**A8 — Integration tests always use fake corpus providers (Task 0).**
Tomorrow's `.env` will set `CORPUS_LLM_PROVIDER=openai`. Add `"CORPUS_LLM_PROVIDER": "fake"` to `FAKE_BACKENDS` in `tests/integration/conftest.py`, and in Task 19 the CLI must never construct an OpenAI client when the provider is `fake`.

**A9 — Estimates use the price actually paid (Tasks 16, 17, 18, 19).**
- `estimate_ocr` / `estimate_describe` / `estimate_embeddings` take `batch: bool = True` and pass it to `cost_usd`; sync commands check the cap with `batch=False`.
- `ocr --pilot N` checks the cap with the cost of N pages at sync price, not the estimate for all pending pages (as written it multiplies the full estimate by `pilot / len(tasks)` = 1, which can block the pilot itself).
- Sync OpenAI embeddings (`embed_local` with `OpenAIEmbeddings`) record spend under kind `embed` using `last_usage` at sync price.

**A10 — Akoma Ntoso text survives pretty-printed XML (Task 6).**
Real Fedlex XML may put newlines between `<num>` and `<content>`; splitting `get_text` on `"\n"` would put `1` and its text on separate lines. In `_render`, collapse whitespace inside every text node first, insert an explicit marker (e.g. `" "`) before each list item, then split on the marker. Add a fixture variant with pretty-printed whitespace between `<num>1</num>` and `<content>` and assert the paragraph still starts `1 Nach Ablauf`.

**A11 — Site adaptations found by a live survey of every declared source (new Task 9b; Task 20).**
A survey of all 21 html sources on 2026-09-23 (no headless browser needed anywhere) found:
- *User agent:* ch.ch (S3 + CloudFront prerender) serves a 404 shell to any user agent without a browser-style prefix. The corpus crawler's user agent is `Mozilla/5.0 (compatible; swiss-grounding/0.2; +https://github.com/thedionysus/swisscom-hackathon)` (setting `corpus_user_agent`), the conventional honest-bot form.
- *Language alternates beyond hreflang* (hreflang exists only on sem, arbeit.swiss, scuol): `page_meta` also reads (a) links matched by an optional per-source CSS selector `config.language_links_selector` (e.g. ch.ch `nav#language a[href]`, bern.ch's language switcher), language taken from the link's `hreflang`/`lang` attribute, else from its text or the URL's `/xx/` segment; (b) the federal new-CMS Nuxt payload `<script id="__NUXT_DATA__">` (bag, bazg, bwo, bk admin.ch sites): resolve the integer-reference array, find the dict with `groupId` and `translationPages`, alternates are `/{lang}/{slug}` on the same host. The A1 symmetric-grouping rule applies unchanged.
- *PDFs without a .pdf extension:* optional `config.pdf_link_patterns` (regexes on absolute URLs, e.g. `^https://www\.ahv-iv\.ch/p/`) also count as PDF links; the PDF connector checks the response `content-type` is PDF.
- *Content root:* optional `config.content_selector` (CSS) overrides `<main>`/`<article>`/body for sites without `<main>`; the page title prefers the `<h1>` inside the content root, else `<title>`.
- *Sitemap seeding:* optional `config.sitemap_urls` plus `config.sitemap_include` (regexes on URLs): URLs from those sitemaps matching a pattern are added to the frontier after the start URLs (for flat-URL federal sites, filter by keyword; for geneve.ch, `/themes/.+/.+`). Handles sitemap indexes and gzip; respects `max_pages`.
- *Task 20 start URLs* are corrected from the survey (bag_kv, bazg, bwo, bk_votes, arbeit_swiss, ge_canton, geneve_city, lugano_city), and the federal new-CMS sources use `allow_prefixes` of `https://www.{office}.admin.ch/{lang}/` with sitemap seeding filtered by topic keywords.
Survey evidence and scripts: scratchpad `probe.py`, `probe.json`, `nuxtpage.py`.
