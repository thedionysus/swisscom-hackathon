# Swiss Grounding MCP — Plan 1: Core (database, locations, registry, query core, MCP server)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A runnable MCP server and CLI that resolve a location, filter chunks by the location containment tree, run hybrid retrieval, rerank, and return structured citations, working against fixture documents loaded into PostgreSQL.

**Architecture:** One PostgreSQL database with pgvector. A pure-Python query core library (`retrieval/`) that the MCP server and CLI both call. Location tree and source registry as small, immutable models loaded from the database. Real ingestion is Plan 2; this plan ships a fixture loader so everything downstream is testable end to end.

**Tech Stack:** Python 3.12, uv, psycopg 3, pgvector, pydantic 2, pydantic-settings, PyYAML, httpx, typer, mcp (FastMCP), sentence-transformers (optional at runtime, never in tests), pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`

**Conventions used throughout:**
- All models are frozen dataclasses or pydantic models. Functions return new objects; nothing mutates.
- Unit tests need no database. Integration tests need `DATABASE_URL` pointing at the Docker Compose database and are marked `@pytest.mark.integration`.
- Every task ends with a commit.

---

## File structure

```
pyproject.toml
docker-compose.yml
.env.example
.gitignore
README.md
src/swiss_grounding/__init__.py
src/swiss_grounding/config.py                  settings from environment
src/swiss_grounding/db/__init__.py
src/swiss_grounding/db/connection.py           connect(), transaction helper
src/swiss_grounding/db/schema.sql              DDL for all Plan 1 tables
src/swiss_grounding/db/migrate.py              apply schema.sql
src/swiss_grounding/locations/__init__.py
src/swiss_grounding/locations/models.py        Location, Level, ResolvedLocation
src/swiss_grounding/locations/tree.py          LocationTree: lookup, ancestors, distance, alias index
src/swiss_grounding/locations/seed.py          builds CH, cantons, Zurich city, Kreise, Quartiere
src/swiss_grounding/locations/repository.py    load/insert locations
src/swiss_grounding/locations/geoadmin.py      GeoAdmin SearchServer client
src/swiss_grounding/locations/resolver.py      resolve text → ResolvedLocation
src/swiss_grounding/registry/__init__.py
src/swiss_grounding/registry/models.py         Source, Authority, FetchStrategy
src/swiss_grounding/registry/categories.py     fixed category list
src/swiss_grounding/registry/loader.py         load + validate YAML source definitions
src/swiss_grounding/registry/repository.py     upsert/load sources
src/swiss_grounding/registry/sources/*.yaml    seed source definitions
src/swiss_grounding/retrieval/__init__.py
src/swiss_grounding/retrieval/models.py        Chunk, Hit, Citation, QueryRequest, QueryResponse
src/swiss_grounding/retrieval/embedder.py      Embedder protocol, FakeEmbedder, SentenceTransformerEmbedder
src/swiss_grounding/retrieval/search.py        dense + lexical SQL, reciprocal rank fusion
src/swiss_grounding/retrieval/rerank.py        deterministic scoring
src/swiss_grounding/retrieval/diversify.py     per-document cap, most-specific guarantee
src/swiss_grounding/retrieval/cite.py          Hit → Citation
src/swiss_grounding/retrieval/query_core.py    orchestration
src/swiss_grounding/ingest/__init__.py
src/swiss_grounding/ingest/fixture_loader.py   load JSON fixture documents + chunks
src/swiss_grounding/mcp_server/__init__.py
src/swiss_grounding/mcp_server/server.py       FastMCP app and tool registration
src/swiss_grounding/cli/__init__.py
src/swiss_grounding/cli/main.py                typer app
tests/conftest.py
tests/unit/...
tests/integration/...
tests/fixtures/zurich_hiking.json
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`, `src/swiss_grounding/__init__.py`, `tests/conftest.py`, `tests/unit/test_scaffold.py`

- [ ] **Step 1: Initialise git and uv project**

```bash
cd "/Users/arlind/Documents/Personal Projects/swisscom-hackathon"
git init -b main
uv init --lib --name swiss-grounding --python 3.12 .
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "swiss-grounding"
version = "0.1.0"
description = "Swiss Grounding MCP: jurisdiction-aware retrieval over Swiss public sources"
requires-python = ">=3.12"
dependencies = [
    "psycopg[binary,pool]>=3.2",
    "pgvector>=0.3",
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    "pyyaml>=6.0",
    "httpx>=0.27",
    "typer>=0.12",
    "mcp>=1.2",
    "numpy>=1.26",
]

[project.optional-dependencies]
embed = ["sentence-transformers>=3.0"]

[project.scripts]
swiss-grounding = "swiss_grounding.cli.main:app"

[dependency-groups]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/swiss_grounding"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: needs DATABASE_URL and a running PostgreSQL"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 3: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: swiss
      POSTGRES_PASSWORD: swiss
      POSTGRES_DB: swiss_grounding
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U swiss -d swiss_grounding"]
      interval: 5s
      timeout: 3s
      retries: 10
volumes:
  pgdata:
```

- [ ] **Step 4: Write `.env.example` and `.gitignore`**

`.env.example`:
```
DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding
EMBEDDING_BACKEND=fake
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
GEOADMIN_BASE_URL=https://api3.geo.admin.ch
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.ruff_cache/
dist/
```

- [ ] **Step 5: Write `README.md`**

```markdown
# Swiss Grounding MCP

Jurisdiction-aware retrieval over Swiss public sources, exposed as an MCP server and a CLI.

## Quick start

    cp .env.example .env
    docker compose up -d db
    uv sync
    uv run swiss-grounding db init
    uv run swiss-grounding db seed
    uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json
    uv run swiss-grounding query "Do I need to leash my dog on hiking trails?" --location "Wiedikon"
    uv run swiss-grounding serve --transport stdio

## Tests

    uv run pytest tests/unit
    DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration

Design: `docs/superpowers/specs/2026-09-10-swiss-grounding-mcp-design.md`
Research: `research/README.md`
```

- [ ] **Step 6: Write `src/swiss_grounding/__init__.py`**

```python
"""Swiss Grounding MCP."""

__version__ = "0.1.0"
```

- [ ] **Step 7: Write `tests/conftest.py`**

```python
import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="DATABASE_URL not set; integration tests skipped")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 8: Write `tests/unit/test_scaffold.py`**

```python
import swiss_grounding


def test_version():
    assert swiss_grounding.__version__ == "0.1.0"
```

- [ ] **Step 9: Install and run**

Run: `uv sync --all-extras --group dev && uv run pytest tests/unit -v`
Expected: `1 passed`

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: scaffold swiss-grounding project"
```

---

### Task 2: Settings

**Files:**
- Create: `src/swiss_grounding/config.py`, `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_config.py
from swiss_grounding.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    s = Settings()
    assert s.database_url == "postgresql://u:p@h:1/db"
    assert s.embedding_backend == "fake"
    assert s.embedding_dim == 8


def test_settings_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:1/db")
    monkeypatch.setenv("EMBEDDING_BACKEND", "magic")
    import pytest

    with pytest.raises(ValueError):
        Settings()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: swiss_grounding.config`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/config.py
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every value comes from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    database_url: str
    embedding_backend: Literal["fake", "sentence_transformers"] = "fake"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    geoadmin_base_url: str = "https://api3.geo.admin.ch"
    geoadmin_timeout_seconds: float = 5.0


def load_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/config.py tests/unit/test_config.py
git commit -m "feat: add environment-based settings"
```

---

### Task 3: Database connection and schema

**Files:**
- Create: `src/swiss_grounding/db/__init__.py`, `src/swiss_grounding/db/connection.py`, `src/swiss_grounding/db/schema.sql`, `src/swiss_grounding/db/migrate.py`, `tests/integration/test_schema.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_schema.py
import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {
    "location", "source", "source_suggestion", "document", "chunk", "document_change",
}


def test_schema_creates_tables():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema='public'"
        ).fetchall()
    names = {r["table_name"] for r in rows}
    assert EXPECTED_TABLES <= names
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose up -d db && DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `connection.py`**

```python
# src/swiss_grounding/db/connection.py
from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row


@contextmanager
def connect(database_url: str) -> Iterator[psycopg.Connection]:
    """Open a connection with dict rows and pgvector registered. Commits on success."""
    conn = psycopg.connect(database_url, row_factory=dict_row)
    try:
        conn.execute("create extension if not exists vector")
        register_vector(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Write `schema.sql`**

The placeholder `{{EMBEDDING_DIM}}` is substituted by `migrate.py`.

```sql
-- src/swiss_grounding/db/schema.sql
create extension if not exists vector;

create table if not exists location (
    id          text primary key,
    parent_id   text references location(id),
    level       text not null check (level in ('country','canton','municipality','neighborhood')),
    bfs_id      integer,
    lindas_uri  text,
    names       jsonb not null,
    path        text[] not null
);
create index if not exists location_path_idx on location using gin (path);

create table if not exists source (
    id                 text primary key,
    name               text not null,
    base_url           text not null,
    default_extent_id  text not null references location(id),
    authority          text not null check (authority in
        ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
    categories         text[] not null default '{}',
    fetch_strategy     text not null,
    fetch_config       jsonb not null default '{}',
    allow_narrowing    boolean not null default false,
    license            text,
    origin             text not null default 'seed' check (origin in ('seed','auto_approved','reviewed'))
);

create table if not exists source_suggestion (
    id                   bigserial primary key,
    url                  text not null unique,
    reason               text not null,
    proposed_extent_id   text references location(id),
    proposed_authority   text,
    proposed_categories  text[] not null default '{}',
    domain_class         text not null check (domain_class in ('official','swiss','other')),
    status               text not null default 'pending' check (status in ('pending','approved','rejected')),
    suggested_by         text,
    suggested_at         timestamptz not null default now(),
    reviewed_by          text,
    reviewed_at          timestamptz,
    review_note          text,
    source_id            text references source(id)
);

create table if not exists document (
    id              bigserial primary key,
    source_id       text not null references source(id),
    url             text not null,
    identifier      text,
    title_original  text not null,
    title_en        text not null,
    language        text not null,
    extent_id       text not null references location(id),
    extent_reason   text not null default 'source_default',
    authority       text not null,
    categories      jsonb not null default '[]',
    valid_from      date,
    valid_to        date,
    in_force        boolean,
    published_at    timestamptz,
    retrieved_at    timestamptz not null default now(),
    content_hash    text not null,
    version         integer not null default 1,
    superseded_by   bigint references document(id),
    status          text not null default 'current' check (status in ('current','superseded','withdrawn','pending_enrichment'))
);
create index if not exists document_url_idx on document(url);
create index if not exists document_status_idx on document(status);

create table if not exists chunk (
    id               bigserial primary key,
    document_id      bigint not null references document(id) on delete cascade,
    ordinal          integer not null,
    text_original    text not null,
    text_en          text not null,
    heading_path     text not null default '',
    anchor           text,
    embedding        vector({{EMBEDDING_DIM}}) not null,
    tsv              tsvector generated always as (to_tsvector('english', text_en)) stored,
    chunk_hash       text not null,
    extent_id        text not null references location(id),
    authority        text not null,
    categories       text[] not null default '{}',
    document_status  text not null default 'current'
);
create index if not exists chunk_extent_idx on chunk(extent_id, document_status);
create index if not exists chunk_tsv_idx on chunk using gin (tsv);
create index if not exists chunk_embedding_idx on chunk using hnsw (embedding vector_cosine_ops);

create table if not exists document_change (
    id                    bigserial primary key,
    run_id                text not null,
    document_id           bigint references document(id),
    previous_document_id  bigint references document(id),
    change_type           text not null check (change_type in ('added','modified','withdrawn')),
    chunks_added          bigint[] not null default '{}',
    chunks_removed        bigint[] not null default '{}',
    chunks_modified       bigint[] not null default '{}',
    changed_at            timestamptz not null default now()
);
```

- [ ] **Step 5: Write `migrate.py`**

```python
# src/swiss_grounding/db/migrate.py
from importlib import resources

from swiss_grounding.db.connection import connect


def render_schema(embedding_dim: int) -> str:
    sql = resources.files("swiss_grounding.db").joinpath("schema.sql").read_text()
    return sql.replace("{{EMBEDDING_DIM}}", str(embedding_dim))


def apply_schema(database_url: str, embedding_dim: int) -> None:
    with connect(database_url) as conn:
        conn.execute(render_schema(embedding_dim))
```

Write an empty `src/swiss_grounding/db/__init__.py`.

- [ ] **Step 6: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_schema.py -v`
Expected: `1 passed`

- [ ] **Step 7: Commit**

```bash
git add src/swiss_grounding/db tests/integration/test_schema.py
git commit -m "feat: add database connection and schema"
```

---

### Task 4: Location models and tree

**Files:**
- Create: `src/swiss_grounding/locations/__init__.py`, `src/swiss_grounding/locations/models.py`, `src/swiss_grounding/locations/tree.py`, `tests/unit/test_location_tree.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_location_tree.py
import pytest

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree


def small_tree() -> LocationTree:
    return LocationTree.from_locations([
        Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None, lindas_uri=None,
                 names={"en": "Switzerland", "de": "Schweiz"}, aliases=("Swiss",)),
        Location(id="CH-ZH", parent_id="CH", level=Level.CANTON, bfs_id=1, lindas_uri=None,
                 names={"en": "Zurich", "de": "Zürich"}, aliases=("ZH", "Kanton Zürich")),
        Location(id="CH-ZH-261", parent_id="CH-ZH", level=Level.MUNICIPALITY, bfs_id=261,
                 lindas_uri=None, names={"en": "Zurich", "de": "Zürich"}, aliases=("Stadt Zürich",)),
        Location(id="CH-ZH-261-K3", parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None,
                 lindas_uri=None, names={"de": "Kreis 3"}, aliases=("Wiedikon", "8003")),
        Location(id="CH-BS", parent_id="CH", level=Level.CANTON, bfs_id=12, lindas_uri=None,
                 names={"en": "Basel-Stadt"}, aliases=("BS",)),
    ])


def test_path_is_ancestors_including_self():
    t = small_tree()
    assert t.path("CH-ZH-261-K3") == ("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")
    assert t.path("CH") == ("CH",)


def test_distance_between_node_and_ancestor():
    t = small_tree()
    assert t.distance("CH-ZH-261-K3", "CH-ZH-261-K3") == 0
    assert t.distance("CH-ZH-261-K3", "CH-ZH") == 2
    assert t.distance("CH-ZH-261-K3", "CH") == 3


def test_distance_to_non_ancestor_is_none():
    t = small_tree()
    assert t.distance("CH-ZH-261-K3", "CH-BS") is None


def test_find_by_alias_is_case_and_accent_insensitive():
    t = small_tree()
    assert [m.id for m in t.find("wiedikon")] == ["CH-ZH-261-K3"]
    assert [m.id for m in t.find("kanton zurich")] == ["CH-ZH"]
    assert [m.id for m in t.find("8003")] == ["CH-ZH-261-K3"]


def test_find_ambiguous_returns_most_specific_first():
    t = small_tree()
    ids = [m.id for m in t.find("Zürich")]
    assert ids == ["CH-ZH-261", "CH-ZH"]


def test_find_unknown_returns_empty():
    assert small_tree().find("Atlantis") == ()


def test_by_bfs_id():
    t = small_tree()
    assert t.by_bfs_id(261).id == "CH-ZH-261"
    assert t.by_bfs_id(999) is None


def test_unknown_id_raises():
    with pytest.raises(KeyError):
        small_tree().path("nope")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_location_tree.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `models.py`**

```python
# src/swiss_grounding/locations/models.py
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class Level(StrEnum):
    COUNTRY = "country"
    CANTON = "canton"
    MUNICIPALITY = "municipality"
    NEIGHBORHOOD = "neighborhood"


LEVEL_DEPTH: Mapping[Level, int] = {
    Level.COUNTRY: 0,
    Level.CANTON: 1,
    Level.MUNICIPALITY: 2,
    Level.NEIGHBORHOOD: 3,
}


@dataclass(frozen=True)
class Location:
    id: str
    parent_id: str | None
    level: Level
    bfs_id: int | None
    lindas_uri: str | None
    names: Mapping[str, str]
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def label(self, lang: str = "en") -> str:
        return self.names.get(lang) or self.names.get("de") or next(iter(self.names.values()))

    def all_names(self) -> tuple[str, ...]:
        return tuple(self.names.values()) + self.aliases


@dataclass(frozen=True)
class ResolvedLocation:
    location: Location
    path: tuple[str, ...]
    method: str            # "alias" | "geoadmin" | "geoadmin_approximate"
    input_text: str
    alternatives: tuple[Location, ...] = field(default_factory=tuple)
```

- [ ] **Step 4: Write `tree.py`**

```python
# src/swiss_grounding/locations/tree.py
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

from swiss_grounding.locations.models import LEVEL_DEPTH, Location


def normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace. Used for alias matching."""
    stripped = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in stripped if not unicodedata.combining(c))
    return " ".join(ascii_only.lower().split())


@dataclass(frozen=True)
class LocationTree:
    by_id: Mapping[str, Location]
    alias_index: Mapping[str, tuple[str, ...]]
    bfs_index: Mapping[int, str]

    @classmethod
    def from_locations(cls, locations: Iterable[Location]) -> "LocationTree":
        by_id = {loc.id: loc for loc in locations}
        alias_acc: dict[str, list[str]] = {}
        for loc in by_id.values():
            for name in loc.all_names():
                ids = alias_acc.setdefault(normalize(name), [])
                if loc.id not in ids:          # en/de names may normalize identically
                    ids.append(loc.id)
        alias_index = {k: tuple(v) for k, v in alias_acc.items()}
        bfs_index = {loc.bfs_id: loc.id for loc in by_id.values() if loc.bfs_id is not None}
        return cls(by_id=by_id, alias_index=alias_index, bfs_index=bfs_index)

    def get(self, location_id: str) -> Location:
        return self.by_id[location_id]

    def path(self, location_id: str) -> tuple[str, ...]:
        """Ancestor ids from root to the node, inclusive."""
        chain: list[str] = []
        current: str | None = location_id
        while current is not None:
            loc = self.by_id[current]
            chain.append(loc.id)
            current = loc.parent_id
        return tuple(reversed(chain))

    def distance(self, node_id: str, ancestor_id: str) -> int | None:
        """Number of steps from node up to ancestor; None if ancestor is not on the path."""
        p = self.path(node_id)
        if ancestor_id not in p:
            return None
        return len(p) - 1 - p.index(ancestor_id)

    def find(self, text: str) -> tuple[Location, ...]:
        """Exact alias match, most specific level first."""
        ids = self.alias_index.get(normalize(text), ())
        found = [self.by_id[i] for i in ids]
        found.sort(key=lambda loc: -LEVEL_DEPTH[loc.level])
        return tuple(found)

    def by_bfs_id(self, bfs_id: int) -> Location | None:
        location_id = self.bfs_index.get(bfs_id)
        return self.by_id[location_id] if location_id else None

    def all(self) -> tuple[Location, ...]:
        return tuple(self.by_id.values())
```

Write an empty `src/swiss_grounding/locations/__init__.py`.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/unit/test_location_tree.py -v`
Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/locations tests/unit/test_location_tree.py
git commit -m "feat: add location models and containment tree"
```

---

### Task 5: Location seed data (Switzerland, cantons, Zurich city, Kreise, Quartiere)

**Files:**
- Create: `src/swiss_grounding/locations/seed.py`, `tests/unit/test_location_seed.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_location_seed.py
from swiss_grounding.locations.models import Level
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree


def test_seed_has_country_and_26_cantons():
    locs = seed_locations()
    assert sum(1 for l in locs if l.level == Level.COUNTRY) == 1
    assert sum(1 for l in locs if l.level == Level.CANTON) == 26


def test_seed_has_zurich_city_12_kreise_34_quartiere():
    locs = seed_locations()
    tree = LocationTree.from_locations(locs)
    assert tree.by_bfs_id(261).id == "CH-ZH-261"
    kreise = [l for l in locs if l.parent_id == "CH-ZH-261"]
    assert len(kreise) == 12
    quartiere = [l for l in locs if l.level == Level.NEIGHBORHOOD and l.parent_id.startswith("CH-ZH-261-K")]
    assert len(quartiere) == 34


def test_seed_ids_are_unique_and_parents_exist():
    locs = seed_locations()
    ids = [l.id for l in locs]
    assert len(ids) == len(set(ids))
    for l in locs:
        assert l.parent_id is None or l.parent_id in ids


def test_seed_aliases_resolve():
    tree = LocationTree.from_locations(seed_locations())
    assert tree.find("Wiedikon")[0].id == "CH-ZH-261-K3-ALT-WIEDIKON"
    assert tree.find("Kreis 3")[0].id == "CH-ZH-261-K3"
    assert tree.find("8003")[0].id == "CH-ZH-261-K3"
    assert tree.find("Genève")[0].id == "CH-GE"
    assert tree.find("Basel")[0].id == "CH-BS"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_location_seed.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `seed.py`**

Note for the engineer: canton numbers are BFS canton numbers. Kreis and Quartier names are the official Stadt Zürich Stadtkreise and Statistische Quartiere. PLZ aliases are attached to a Kreis only where the postal code lies entirely inside one Kreis; verify against `data.stadt-zuerich.ch` before adding more.

```python
# src/swiss_grounding/locations/seed.py
from swiss_grounding.locations.models import Level, Location

# (bfs_id, abbreviation, de, fr, it, en, extra aliases)
CANTONS: tuple[tuple[int, str, str, str, str, str, tuple[str, ...]], ...] = (
    (1, "ZH", "Zürich", "Zurich", "Zurigo", "Zurich", ("Kanton Zürich", "Canton of Zurich")),
    (2, "BE", "Bern", "Berne", "Berna", "Bern", ("Kanton Bern", "Canton of Bern")),
    (3, "LU", "Luzern", "Lucerne", "Lucerna", "Lucerne", ("Kanton Luzern",)),
    (4, "UR", "Uri", "Uri", "Uri", "Uri", ("Kanton Uri",)),
    (5, "SZ", "Schwyz", "Schwytz", "Svitto", "Schwyz", ("Kanton Schwyz",)),
    (6, "OW", "Obwalden", "Obwald", "Obvaldo", "Obwalden", ("Kanton Obwalden",)),
    (7, "NW", "Nidwalden", "Nidwald", "Nidvaldo", "Nidwalden", ("Kanton Nidwalden",)),
    (8, "GL", "Glarus", "Glaris", "Glarona", "Glarus", ("Kanton Glarus",)),
    (9, "ZG", "Zug", "Zoug", "Zugo", "Zug", ("Kanton Zug",)),
    (10, "FR", "Freiburg", "Fribourg", "Friburgo", "Fribourg", ("Kanton Freiburg", "Canton de Fribourg")),
    (11, "SO", "Solothurn", "Soleure", "Soletta", "Solothurn", ("Kanton Solothurn",)),
    (12, "BS", "Basel-Stadt", "Bâle-Ville", "Basilea Città", "Basel-Stadt", ("Basel", "Kanton Basel-Stadt")),
    (13, "BL", "Basel-Landschaft", "Bâle-Campagne", "Basilea Campagna", "Basel-Landschaft", ("Baselland", "Kanton Basel-Landschaft")),
    (14, "SH", "Schaffhausen", "Schaffhouse", "Sciaffusa", "Schaffhausen", ("Kanton Schaffhausen",)),
    (15, "AR", "Appenzell Ausserrhoden", "Appenzell Rhodes-Extérieures", "Appenzello Esterno", "Appenzell Ausserrhoden", ()),
    (16, "AI", "Appenzell Innerrhoden", "Appenzell Rhodes-Intérieures", "Appenzello Interno", "Appenzell Innerrhoden", ()),
    (17, "SG", "St. Gallen", "Saint-Gall", "San Gallo", "St. Gallen", ("Kanton St. Gallen", "Sankt Gallen")),
    (18, "GR", "Graubünden", "Grisons", "Grigioni", "Grisons", ("Kanton Graubünden", "Grischun")),
    (19, "AG", "Aargau", "Argovie", "Argovia", "Aargau", ("Kanton Aargau",)),
    (20, "TG", "Thurgau", "Thurgovie", "Turgovia", "Thurgau", ("Kanton Thurgau",)),
    (21, "TI", "Tessin", "Tessin", "Ticino", "Ticino", ("Kanton Tessin", "Cantone Ticino")),
    (22, "VD", "Waadt", "Vaud", "Vaud", "Vaud", ("Kanton Waadt", "Canton de Vaud")),
    (23, "VS", "Wallis", "Valais", "Vallese", "Valais", ("Kanton Wallis", "Canton du Valais")),
    (24, "NE", "Neuenburg", "Neuchâtel", "Neuchâtel", "Neuchâtel", ("Kanton Neuenburg", "Canton de Neuchâtel")),
    (25, "GE", "Genf", "Genève", "Ginevra", "Geneva", ("Kanton Genf", "Canton de Genève", "Geneve")),
    (26, "JU", "Jura", "Jura", "Giura", "Jura", ("Kanton Jura", "Canton du Jura")),
)

# Kreis number -> (quartiere, plz aliases that lie fully within the Kreis)
ZURICH_KREISE: dict[int, tuple[tuple[str, ...], tuple[str, ...]]] = {
    1: (("Rathaus", "Hochschulen", "Lindenhof", "City"), ("8001",)),
    2: (("Wollishofen", "Leimbach", "Enge"), ("8002", "8038", "8041")),
    3: (("Alt-Wiedikon", "Friesenberg", "Sihlfeld"), ("8003", "8045", "8055")),
    4: (("Werd", "Langstrasse", "Hard"), ("8004",)),
    5: (("Gewerbeschule", "Escher Wyss"), ("8005",)),
    6: (("Unterstrass", "Oberstrass"), ("8006", "8057")),
    7: (("Fluntern", "Hottingen", "Hirslanden", "Witikon"), ("8032", "8044", "8053")),
    8: (("Seefeld", "Mühlebach", "Weinegg"), ("8008",)),
    9: (("Albisrieden", "Altstetten"), ("8047", "8048", "8064")),
    10: (("Höngg", "Wipkingen"), ("8037", "8049")),
    11: (("Affoltern", "Oerlikon", "Seebach"), ("8046", "8050", "8052")),
    12: (("Saatlen", "Schwamendingen-Mitte", "Hirzenbach"), ("8051",)),
}

# Common names for Quartiere that differ from the statistical name
QUARTIER_ALIASES: dict[str, tuple[str, ...]] = {
    "Alt-Wiedikon": ("Wiedikon",),
    "Escher Wyss": ("Zürich West",),
    "Rathaus": ("Niederdorf", "Altstadt"),
    "City": ("Bahnhofstrasse",),
    "Schwamendingen-Mitte": ("Schwamendingen",),
}


def _slug(text: str) -> str:
    return (
        text.upper()
        .replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
        .replace(" ", "-")
    )


def seed_locations() -> tuple[Location, ...]:
    country = Location(
        id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None,
        lindas_uri="https://ld.admin.ch/country/CHE",
        names={"de": "Schweiz", "fr": "Suisse", "it": "Svizzera", "en": "Switzerland"},
        aliases=("CH", "Swiss", "Confederation", "Eidgenossenschaft", "Confédération"),
    )
    cantons = tuple(
        Location(
            id=f"CH-{abbr}", parent_id="CH", level=Level.CANTON, bfs_id=bfs,
            lindas_uri=f"https://ld.admin.ch/canton/{bfs}",
            names={"de": de, "fr": fr, "it": it, "en": en},
            aliases=(abbr, f"CH-{abbr}") + extra,
        )
        for bfs, abbr, de, fr, it, en, extra in CANTONS
    )
    city = Location(
        id="CH-ZH-261", parent_id="CH-ZH", level=Level.MUNICIPALITY, bfs_id=261,
        lindas_uri="https://ld.admin.ch/municipality/261",
        names={"de": "Zürich", "fr": "Zurich", "it": "Zurigo", "en": "Zurich"},
        aliases=("Stadt Zürich", "City of Zurich", "Zuerich", "Zurich city"),
    )
    kreise: list[Location] = []
    quartiere: list[Location] = []
    for number, (names, plzs) in ZURICH_KREISE.items():
        kreis_id = f"CH-ZH-261-K{number}"
        kreise.append(Location(
            id=kreis_id, parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None,
            lindas_uri=None,
            names={"de": f"Kreis {number}", "en": f"District {number}"},
            aliases=(f"Zürich Kreis {number}", f"Kreis{number}") + plzs,
        ))
        for name in names:
            quartiere.append(Location(
                id=f"{kreis_id}-{_slug(name)}", parent_id=kreis_id, level=Level.NEIGHBORHOOD,
                bfs_id=None, lindas_uri=None,
                names={"de": name},
                aliases=QUARTIER_ALIASES.get(name, ()),
            ))
    return (country,) + cantons + (city,) + tuple(kreise) + tuple(quartiere)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_location_seed.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/locations/seed.py tests/unit/test_location_seed.py
git commit -m "feat: seed Switzerland, cantons, Zurich Kreise and Quartiere"
```

---

### Task 6: Location repository

**Files:**
- Create: `src/swiss_grounding/locations/repository.py`, `tests/integration/test_location_repository.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_location_repository.py
import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    return u


def test_upsert_and_load_roundtrip(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        tree = load_tree(conn)
    assert len(tree.all()) == len(locs)
    assert tree.path("CH-ZH-261-K3") == ("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3")
    assert tree.find("Wiedikon")[0].id == "CH-ZH-261-K3-ALT-WIEDIKON"


def test_upsert_is_idempotent(url):
    locs = seed_locations()
    with connect(url) as conn:
        upsert_locations(conn, locs)
        upsert_locations(conn, locs)
        count = conn.execute("select count(*) as n from location").fetchone()["n"]
    assert count == len(locs)
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_location_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/locations/repository.py
import json
from typing import Iterable

import psycopg

from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree

UPSERT = """
insert into location (id, parent_id, level, bfs_id, lindas_uri, names, path)
values (%(id)s, %(parent_id)s, %(level)s, %(bfs_id)s, %(lindas_uri)s, %(names)s, %(path)s)
on conflict (id) do update set
    parent_id = excluded.parent_id, level = excluded.level, bfs_id = excluded.bfs_id,
    lindas_uri = excluded.lindas_uri, names = excluded.names, path = excluded.path
"""


def upsert_locations(conn: psycopg.Connection, locations: Iterable[Location]) -> None:
    """Insert or update locations. Parents are written before children."""
    tree = LocationTree.from_locations(locations)
    ordered = sorted(tree.all(), key=lambda loc: len(tree.path(loc.id)))
    for loc in ordered:
        conn.execute(UPSERT, {
            "id": loc.id,
            "parent_id": loc.parent_id,
            "level": loc.level.value,
            "bfs_id": loc.bfs_id,
            "lindas_uri": loc.lindas_uri,
            "names": json.dumps({"labels": dict(loc.names), "aliases": list(loc.aliases)}),
            "path": list(tree.path(loc.id)),
        })


def load_tree(conn: psycopg.Connection) -> LocationTree:
    rows = conn.execute(
        "select id, parent_id, level, bfs_id, lindas_uri, names from location"
    ).fetchall()
    locations = tuple(
        Location(
            id=r["id"], parent_id=r["parent_id"], level=Level(r["level"]), bfs_id=r["bfs_id"],
            lindas_uri=r["lindas_uri"], names=r["names"]["labels"],
            aliases=tuple(r["names"]["aliases"]),
        )
        for r in rows
    )
    return LocationTree.from_locations(locations)
```

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_location_repository.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/locations/repository.py tests/integration/test_location_repository.py
git commit -m "feat: persist and load the location tree"
```

---

### Task 7: GeoAdmin client and location resolver

**Files:**
- Create: `src/swiss_grounding/locations/geoadmin.py`, `src/swiss_grounding/locations/resolver.py`, `tests/unit/test_geoadmin.py`, `tests/unit/test_resolver.py`

- [ ] **Step 1: Write the failing tests for the GeoAdmin client**

```python
# tests/unit/test_geoadmin.py
import httpx
import pytest

from swiss_grounding.locations.geoadmin import GeoAdminClient, GeoAdminHit

SAMPLE = {
    "results": [
        {"attrs": {"origin": "gg25", "label": "<b>Uster (ZH)</b>", "featureId": "198",
                   "detail": "uster zh", "lat": 47.35, "lon": 8.72}},
        {"attrs": {"origin": "address", "label": "Bahnhofstrasse 1 Uster", "featureId": "x"}},
    ]
}


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://geo.test")
    return GeoAdminClient(http=http)


def test_parses_commune_hits_only():
    def handler(request):
        assert request.url.path == "/rest/services/api/SearchServer"
        assert request.url.params["searchText"] == "Uster"
        return httpx.Response(200, json=SAMPLE)

    hits = make_client(handler).search_communes("Uster")
    assert hits == (GeoAdminHit(bfs_id=198, label="Uster (ZH)"),)


def test_http_error_raises_clear_message():
    def handler(request):
        return httpx.Response(503)

    with pytest.raises(RuntimeError, match="GeoAdmin"):
        make_client(handler).search_communes("Uster")


def test_malformed_payload_is_skipped():
    def handler(request):
        return httpx.Response(200, json={"results": [{"attrs": {"origin": "gg25"}}]})

    assert make_client(handler).search_communes("x") == ()
```

- [ ] **Step 2: Write the failing tests for the resolver**

```python
# tests/unit/test_resolver.py
from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree


class FakeGeo:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search_communes(self, text):
        self.calls.append(text)
        return self.hits


def tree():
    return LocationTree.from_locations(seed_locations())


def test_alias_hit_does_not_call_geoadmin():
    geo = FakeGeo(())
    r = LocationResolver(tree(), geo).resolve("Wiedikon")
    assert r.location.id == "CH-ZH-261-K3-ALT-WIEDIKON"
    assert r.method == "alias"
    assert r.path[-1] == r.location.id
    assert geo.calls == []


def test_ambiguous_alias_picks_most_specific_and_lists_alternatives():
    r = LocationResolver(tree(), FakeGeo(())).resolve("Zürich")
    assert r.location.id == "CH-ZH-261"
    assert [a.id for a in r.alternatives] == ["CH-ZH"]


def test_geoadmin_known_commune():
    geo = FakeGeo((GeoAdminHit(bfs_id=261, label="Zürich (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Zueri city")
    assert r.location.id == "CH-ZH-261"
    assert r.method == "geoadmin"


def test_geoadmin_unknown_commune_falls_back_to_canton_via_label():
    geo = FakeGeo((GeoAdminHit(bfs_id=198, label="Uster (ZH)"),))
    r = LocationResolver(tree(), geo).resolve("Uster")
    assert r.location.id == "CH-ZH"
    assert r.method == "geoadmin_approximate"


def test_nothing_found_returns_none():
    assert LocationResolver(tree(), FakeGeo(())).resolve("Atlantis") is None


def test_geoadmin_failure_returns_none():
    class Broken:
        def search_communes(self, text):
            raise RuntimeError("GeoAdmin down")

    assert LocationResolver(tree(), Broken()).resolve("Uster") is None


def test_empty_input_returns_none():
    assert LocationResolver(tree(), FakeGeo(())).resolve("   ") is None
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/unit/test_geoadmin.py tests/unit/test_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write `geoadmin.py`**

```python
# src/swiss_grounding/locations/geoadmin.py
import re
from dataclasses import dataclass

import httpx

TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class GeoAdminHit:
    bfs_id: int
    label: str


class GeoAdminClient:
    """Thin client for the swisstopo SearchServer. Only commune hits (origin gg25) are returned."""

    def __init__(self, http: httpx.Client):
        self._http = http

    @classmethod
    def from_settings(cls, base_url: str, timeout_seconds: float) -> "GeoAdminClient":
        return cls(http=httpx.Client(base_url=base_url, timeout=timeout_seconds))

    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]:
        try:
            response = self._http.get(
                "/rest/services/api/SearchServer",
                params={"searchText": text, "type": "locations", "origins": "gg25", "limit": 5},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"GeoAdmin lookup failed for {text!r}: {exc}") from exc
        hits: list[GeoAdminHit] = []
        for item in payload.get("results", []):
            attrs = item.get("attrs", {})
            if attrs.get("origin") != "gg25":
                continue
            try:
                bfs_id = int(attrs["featureId"])
                label = TAG_RE.sub("", attrs["label"]).strip()
            except (KeyError, TypeError, ValueError):
                continue
            hits.append(GeoAdminHit(bfs_id=bfs_id, label=label))
        return tuple(hits)
```

- [ ] **Step 5: Write `resolver.py`**

```python
# src/swiss_grounding/locations/resolver.py
import re
from typing import Protocol

from swiss_grounding.locations.geoadmin import GeoAdminHit
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.locations.tree import LocationTree

CANTON_IN_LABEL = re.compile(r"\(([A-Z]{2})\)\s*$")


class CommuneSearch(Protocol):
    def search_communes(self, text: str) -> tuple[GeoAdminHit, ...]: ...


class LocationResolver:
    """Alias match against the tree first; GeoAdmin as fallback. Never guesses."""

    def __init__(self, tree: LocationTree, geo: CommuneSearch):
        self._tree = tree
        self._geo = geo

    def resolve(self, text: str) -> ResolvedLocation | None:
        cleaned = text.strip()
        if not cleaned:
            return None
        matches = self._tree.find(cleaned)
        if matches:
            best = matches[0]
            return ResolvedLocation(
                location=best, path=self._tree.path(best.id), method="alias",
                input_text=cleaned, alternatives=tuple(matches[1:]),
            )
        return self._resolve_via_geoadmin(cleaned)

    def _resolve_via_geoadmin(self, text: str) -> ResolvedLocation | None:
        try:
            hits = self._geo.search_communes(text)
        except RuntimeError:
            return None
        if not hits:
            return None
        hit = hits[0]
        exact = self._tree.by_bfs_id(hit.bfs_id)
        if exact is not None:
            return ResolvedLocation(
                location=exact, path=self._tree.path(exact.id), method="geoadmin", input_text=text,
            )
        canton_match = CANTON_IN_LABEL.search(hit.label)
        if canton_match:
            canton = self._tree.find(canton_match.group(1))
            if canton:
                return ResolvedLocation(
                    location=canton[0], path=self._tree.path(canton[0].id),
                    method="geoadmin_approximate", input_text=text,
                )
        return None
```

- [ ] **Step 6: Run to verify they pass**

Run: `uv run pytest tests/unit/test_geoadmin.py tests/unit/test_resolver.py -v`
Expected: `10 passed`

- [ ] **Step 7: Commit**

```bash
git add src/swiss_grounding/locations/geoadmin.py src/swiss_grounding/locations/resolver.py tests/unit/test_geoadmin.py tests/unit/test_resolver.py
git commit -m "feat: resolve free-text locations via aliases and GeoAdmin"
```

---

### Task 8: Source registry models, categories, YAML loader

**Files:**
- Create: `src/swiss_grounding/registry/__init__.py`, `src/swiss_grounding/registry/models.py`, `src/swiss_grounding/registry/categories.py`, `src/swiss_grounding/registry/loader.py`, `src/swiss_grounding/registry/sources/fedlex.yaml`, `src/swiss_grounding/registry/sources/zh_ch.yaml`, `src/swiss_grounding/registry/sources/stadt_zuerich.yaml`, `src/swiss_grounding/registry/sources/ch_ch.yaml`, `src/swiss_grounding/registry/sources/schweizer_wanderwege.yaml`, `tests/unit/test_registry_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_registry_loader.py
import pytest

from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.registry.loader import load_source_yaml, load_seed_sources
from swiss_grounding.registry.models import Authority, FetchStrategy

VALID = """
id: zh_ch
name: Kanton Zürich
base_url: https://www.zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: [hiking, dogs]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/de/umwelt-tiere", "/de/sicherheit"]
allow_narrowing: true
license: "zh.ch terms of use"
"""


def test_loads_valid_source():
    s = load_source_yaml(VALID)
    assert s.id == "zh_ch"
    assert s.authority == Authority.OFFICIAL_INFO
    assert s.fetch_strategy == FetchStrategy.HTML_CRAWL
    assert s.categories == ("hiking", "dogs")
    assert s.allow_narrowing is True
    assert s.fetch_config["path_allowlist"] == ["/de/umwelt-tiere", "/de/sicherheit"]


def test_rejects_unknown_category():
    with pytest.raises(ValueError, match="category"):
        load_source_yaml(VALID.replace("dogs", "unicorns"))


def test_rejects_unknown_authority():
    with pytest.raises(ValueError):
        load_source_yaml(VALID.replace("official_info", "supreme"))


def test_rejects_narrowing_on_law():
    text = VALID.replace("official_info", "cantonal_law")
    with pytest.raises(ValueError, match="allow_narrowing"):
        load_source_yaml(text)


def test_seed_sources_load_and_reference_valid_categories():
    sources = load_seed_sources()
    ids = {s.id for s in sources}
    assert {"fedlex", "zh_ch", "stadt_zuerich", "ch_ch", "schweizer_wanderwege"} <= ids
    for s in sources:
        assert set(s.categories) <= set(CATEGORY_IDS)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_registry_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `categories.py`**

```python
# src/swiss_grounding/registry/categories.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    description: str


CATEGORIES: tuple[Category, ...] = (
    Category("hiking", "Hiking and outdoor recreation", "Trails, safety, nature protection, alpine rules"),
    Category("waste", "Waste and recycling", "Collection schedules, fees, disposal rules"),
    Category("dogs", "Dogs and pets", "Dog tax, leash rules, registration, training requirements"),
    Category("taxes", "Taxes", "Income, wealth and municipal taxes, filing"),
    Category("housing", "Housing and building", "Renting, building permits, zoning"),
    Category("transport", "Transport and mobility", "Public transport, road traffic rules, cycling"),
    Category("parking", "Parking", "Blue zones, permits, fees"),
    Category("schools", "Schools and education", "Compulsory school, holidays, enrolment"),
    Category("health", "Health", "Insurance, hospitals, emergencies"),
    Category("safety", "Public safety and police", "Police, emergencies, public order"),
)

CATEGORY_IDS: tuple[str, ...] = tuple(c.id for c in CATEGORIES)
```

- [ ] **Step 4: Write `models.py`**

```python
# src/swiss_grounding/registry/models.py
from enum import StrEnum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from swiss_grounding.registry.categories import CATEGORY_IDS


class Authority(StrEnum):
    FEDERAL_LAW = "federal_law"
    CANTONAL_LAW = "cantonal_law"
    MUNICIPAL_LAW = "municipal_law"
    OFFICIAL_INFO = "official_info"
    INSTITUTIONAL = "institutional"


LAW_AUTHORITIES = frozenset({Authority.FEDERAL_LAW, Authority.CANTONAL_LAW, Authority.MUNICIPAL_LAW})

AUTHORITY_RANK: Mapping[Authority, float] = {
    Authority.FEDERAL_LAW: 1.0,
    Authority.CANTONAL_LAW: 0.9,
    Authority.MUNICIPAL_LAW: 0.8,
    Authority.OFFICIAL_INFO: 0.6,
    Authority.INSTITUTIONAL: 0.4,
}


class FetchStrategy(StrEnum):
    FEDLEX_SPARQL = "fedlex_sparql"
    HTML_CRAWL = "html_crawl"
    PDF = "pdf"
    API = "api"


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    base_url: str
    default_extent_id: str
    authority: Authority
    categories: tuple[str, ...] = ()
    fetch_strategy: FetchStrategy
    fetch_config: dict[str, Any] = {}
    allow_narrowing: bool = False
    license: str | None = None
    origin: str = "seed"

    @field_validator("categories")
    @classmethod
    def _known_categories(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [c for c in value if c not in CATEGORY_IDS]
        if unknown:
            raise ValueError(f"unknown category ids: {unknown}")
        return value

    @model_validator(mode="after")
    def _law_never_narrows(self) -> "Source":
        if self.authority in LAW_AUTHORITIES and self.allow_narrowing:
            raise ValueError("allow_narrowing must be false for law sources")
        return self
```

- [ ] **Step 5: Write `loader.py`**

```python
# src/swiss_grounding/registry/loader.py
from importlib import resources

import yaml
from pydantic import ValidationError

from swiss_grounding.registry.models import Source


def load_source_yaml(text: str) -> Source:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("source definition must be a mapping")
    try:
        return Source.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid source definition: {exc}") from exc


def load_seed_sources() -> tuple[Source, ...]:
    folder = resources.files("swiss_grounding.registry").joinpath("sources")
    files = sorted(p for p in folder.iterdir() if p.name.endswith(".yaml"))
    return tuple(load_source_yaml(p.read_text()) for p in files)
```

- [ ] **Step 6: Write the five seed YAML files**

`src/swiss_grounding/registry/sources/fedlex.yaml`:
```yaml
id: fedlex
name: Fedlex (Federal law, Classified Compilation)
base_url: https://www.fedlex.admin.ch
default_extent_id: CH
authority: federal_law
categories: [hiking, waste, dogs, safety, transport]
fetch_strategy: fedlex_sparql
fetch_config:
  sr_numbers: ["451", "455", "741.01", "814.01", "921.0"]
allow_narrowing: false
license: "Fedlex terms for third-party users (commercial reuse permitted)"
```

`src/swiss_grounding/registry/sources/zh_ch.yaml`:
```yaml
id: zh_ch
name: Kanton Zürich
base_url: https://www.zh.ch
default_extent_id: CH-ZH
authority: official_info
categories: [hiking, dogs, waste, safety]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/de/umwelt-tiere", "/de/sicherheit", "/de/planen-bauen"]
allow_narrowing: true
license: "zh.ch terms of use"
```

`src/swiss_grounding/registry/sources/stadt_zuerich.yaml`:
```yaml
id: stadt_zuerich
name: Stadt Zürich
base_url: https://www.stadt-zuerich.ch
default_extent_id: CH-ZH-261
authority: official_info
categories: [hiking, dogs, waste, parking]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/de/umwelt-und-verkehr", "/de/stadtleben", "/de/politik-und-verwaltung/politik-und-recht/amtliche-sammlung"]
allow_narrowing: true
license: "stadt-zuerich.ch terms of use"
```

`src/swiss_grounding/registry/sources/ch_ch.yaml`:
```yaml
id: ch_ch
name: ch.ch (Confederation, cantons and communes portal)
base_url: https://www.ch.ch
default_extent_id: CH
authority: official_info
categories: [dogs, waste, taxes, transport, schools, health]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/en/"]
allow_narrowing: true
license: "ch.ch terms of use"
```

`src/swiss_grounding/registry/sources/schweizer_wanderwege.yaml`:
```yaml
id: schweizer_wanderwege
name: Schweizer Wanderwege
base_url: https://www.schweizer-wanderwege.ch
default_extent_id: CH
authority: institutional
categories: [hiking, safety]
fetch_strategy: html_crawl
fetch_config:
  path_allowlist: ["/de/wandern", "/de/sicherheit"]
allow_narrowing: true
license: "schweizer-wanderwege.ch terms of use"
```

Write an empty `src/swiss_grounding/registry/__init__.py`.

- [ ] **Step 7: Run to verify they pass**

Run: `uv run pytest tests/unit/test_registry_loader.py -v`
Expected: `5 passed`

- [ ] **Step 8: Commit**

```bash
git add src/swiss_grounding/registry tests/unit/test_registry_loader.py
git commit -m "feat: add source registry models, categories and seed definitions"
```

---

### Task 9: Source repository

**Files:**
- Create: `src/swiss_grounding/registry/repository.py`, `tests/integration/test_source_repository.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_source_repository.py
import os

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import load_sources, upsert_sources

pytestmark = pytest.mark.integration


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        upsert_locations(conn, seed_locations())
    return u


def test_upsert_and_load_sources(url):
    seeds = load_seed_sources()
    with connect(url) as conn:
        upsert_sources(conn, seeds)
        upsert_sources(conn, seeds)
        loaded = load_sources(conn)
    assert {s.id for s in loaded} == {s.id for s in seeds}
    fedlex = next(s for s in loaded if s.id == "fedlex")
    assert fedlex.fetch_config["sr_numbers"][0] == "451"
    assert fedlex.allow_narrowing is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_source_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/registry/repository.py
import json
from typing import Iterable

import psycopg

from swiss_grounding.registry.models import Source

UPSERT = """
insert into source (id, name, base_url, default_extent_id, authority, categories,
                    fetch_strategy, fetch_config, allow_narrowing, license, origin)
values (%(id)s, %(name)s, %(base_url)s, %(default_extent_id)s, %(authority)s, %(categories)s,
        %(fetch_strategy)s, %(fetch_config)s, %(allow_narrowing)s, %(license)s, %(origin)s)
on conflict (id) do update set
    name = excluded.name, base_url = excluded.base_url,
    default_extent_id = excluded.default_extent_id, authority = excluded.authority,
    categories = excluded.categories, fetch_strategy = excluded.fetch_strategy,
    fetch_config = excluded.fetch_config, allow_narrowing = excluded.allow_narrowing,
    license = excluded.license, origin = excluded.origin
"""


def upsert_sources(conn: psycopg.Connection, sources: Iterable[Source]) -> None:
    for s in sources:
        conn.execute(UPSERT, {
            "id": s.id, "name": s.name, "base_url": s.base_url,
            "default_extent_id": s.default_extent_id, "authority": s.authority.value,
            "categories": list(s.categories), "fetch_strategy": s.fetch_strategy.value,
            "fetch_config": json.dumps(s.fetch_config), "allow_narrowing": s.allow_narrowing,
            "license": s.license, "origin": s.origin,
        })


def load_sources(conn: psycopg.Connection) -> tuple[Source, ...]:
    rows = conn.execute("select * from source order by id").fetchall()
    return tuple(
        Source(
            id=r["id"], name=r["name"], base_url=r["base_url"],
            default_extent_id=r["default_extent_id"], authority=r["authority"],
            categories=tuple(r["categories"]), fetch_strategy=r["fetch_strategy"],
            fetch_config=r["fetch_config"], allow_narrowing=r["allow_narrowing"],
            license=r["license"], origin=r["origin"],
        )
        for r in rows
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_source_repository.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/registry/repository.py tests/integration/test_source_repository.py
git commit -m "feat: persist and load source registry"
```

---

### Task 10: Retrieval models and embedder

**Files:**
- Create: `src/swiss_grounding/retrieval/__init__.py`, `src/swiss_grounding/retrieval/models.py`, `src/swiss_grounding/retrieval/embedder.py`, `tests/unit/test_embedder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_embedder.py
import numpy as np

from swiss_grounding.retrieval.embedder import FakeEmbedder, build_embedder


def test_fake_embedder_is_deterministic_and_unit_norm():
    e = FakeEmbedder(dim=16)
    a = e.embed(["leash rules for dogs"])[0]
    b = e.embed(["leash rules for dogs"])[0]
    assert a.shape == (16,)
    assert np.allclose(a, b)
    assert abs(np.linalg.norm(a) - 1.0) < 1e-6


def test_fake_embedder_similar_texts_share_tokens():
    e = FakeEmbedder(dim=64)
    dog1, dog2, waste = e.embed(["dog leash trail", "dog leash park", "waste collection calendar"])
    assert float(dog1 @ dog2) > float(dog1 @ waste)


def test_build_embedder_fake():
    e = build_embedder("fake", model_name="ignored", dim=8)
    assert e.dim == 8
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_embedder.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `models.py`**

```python
# src/swiss_grounding/retrieval/models.py
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from swiss_grounding.registry.models import Authority


@dataclass(frozen=True)
class ChunkRecord:
    """A chunk as loaded from the database, with the document fields needed for citation."""
    chunk_id: int
    document_id: int
    ordinal: int
    text_original: str
    text_en: str
    heading_path: str
    anchor: str | None
    extent_id: str
    authority: Authority
    categories: tuple[str, ...]
    url: str
    identifier: str | None
    title_original: str
    title_en: str
    language: str
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    source_id: str


@dataclass(frozen=True)
class Hit:
    chunk: ChunkRecord
    rrf_score: float
    dense_rank: int | None
    lexical_rank: int | None


@dataclass(frozen=True)
class ScoredHit:
    hit: Hit
    score: float
    specificity: float
    category_overlap: float
    authority_score: float


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    document_id: int
    source_id: str
    title_en: str
    title_original: str
    url: str
    anchor: str | None
    identifier: str | None
    snippet_en: str
    snippet_original: str
    language: str
    heading_path: str
    extent_id: str
    extent_label: str
    authority: str
    categories: tuple[str, ...]
    valid_from: date | None
    retrieved_at: datetime
    license: str | None
    score: float


@dataclass(frozen=True)
class QueryRequest:
    question: str
    location: str | None = None
    categories: tuple[str, ...] = ()
    as_of: date | None = None
    limit: int = 8


NOTICE = "Retrieved public information from Swiss sources. Not legal advice."


@dataclass(frozen=True)
class QueryResponse:
    status: Literal["results", "needs_location", "no_evidence"]
    citations: tuple[Citation, ...] = ()
    resolved_location_id: str | None = None
    resolved_location_label: str | None = None
    resolution_method: str | None = None
    alternatives: tuple[str, ...] = ()
    message: str = ""
    notice: str = NOTICE
    categories_used: tuple[str, ...] = field(default_factory=tuple)
```

- [ ] **Step 4: Write `embedder.py`**

```python
# src/swiss_grounding/retrieval/embedder.py
import hashlib
import re
from typing import Protocol, Sequence

import numpy as np

TOKEN_RE = re.compile(r"[a-zA-Z0-9äöüéèàç]+")


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]: ...


class FakeEmbedder:
    """Deterministic bag-of-hashed-tokens embedding. For tests and offline demos only."""

    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, dim: int):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        arr = self._model.encode(list(texts), normalize_embeddings=True)
        return [np.asarray(row, dtype=np.float32) for row in arr]


def build_embedder(backend: str, model_name: str, dim: int) -> Embedder:
    if backend == "fake":
        return FakeEmbedder(dim=dim)
    if backend == "sentence_transformers":
        return SentenceTransformerEmbedder(model_name=model_name, dim=dim)
    raise ValueError(f"unknown embedding backend: {backend}")
```

Write an empty `src/swiss_grounding/retrieval/__init__.py`.

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/unit/test_embedder.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/retrieval tests/unit/test_embedder.py
git commit -m "feat: add retrieval models and embedder abstraction"
```

---

### Task 11: Fixture loader and fixture data

**Files:**
- Create: `src/swiss_grounding/ingest/__init__.py`, `src/swiss_grounding/ingest/fixture_loader.py`, `tests/fixtures/zurich_hiking.json`, `tests/integration/test_fixture_loader.py`

- [ ] **Step 1: Write the fixture file**

Each document has an extent, authority and categories; chunks are short. Basel documents exist so sibling-leak tests are meaningful.

```json
{
  "documents": [
    {
      "source_id": "fedlex",
      "url": "https://www.fedlex.admin.ch/eli/cc/2008/414/de#art_6",
      "identifier": "SR 455 Art. 6",
      "title_original": "Tierschutzgesetz",
      "title_en": "Animal Welfare Act",
      "language": "de",
      "extent_id": "CH",
      "authority": "federal_law",
      "categories": ["dogs"],
      "valid_from": "2008-09-01",
      "chunks": [
        {"heading_path": "Art. 6", "anchor": "art_6",
         "text_original": "Wer ein Tier hält, muss es angemessen nähren, pflegen und ihm die für sein Wohlergehen notwendige Beschäftigung gewähren.",
         "text_en": "Anyone who keeps an animal must feed and care for it appropriately and provide the activity necessary for its well-being. Dog owners must ensure the dog does not endanger people or other animals."}
      ]
    },
    {
      "source_id": "fedlex",
      "url": "https://www.fedlex.admin.ch/eli/cc/1991/1052_1052_1052/de#art_1",
      "identifier": "SR 704 Art. 1",
      "title_original": "Bundesgesetz über Fuss- und Wanderwege",
      "title_en": "Federal Act on Footpaths and Hiking Trails",
      "language": "de",
      "extent_id": "CH",
      "authority": "federal_law",
      "categories": ["hiking"],
      "valid_from": "1987-01-01",
      "chunks": [
        {"heading_path": "Art. 1", "anchor": "art_1",
         "text_original": "Dieses Gesetz regelt die Planung, Anlage und Erhaltung von Fuss- und Wanderwegnetzen.",
         "text_en": "This Act governs the planning, construction and maintenance of footpath and hiking trail networks. Cantons are responsible for hiking trail networks and their signposting."}
      ]
    },
    {
      "source_id": "zh_ch",
      "url": "https://www.zh.ch/de/umwelt-tiere/tiere/hunde.html",
      "identifier": null,
      "title_original": "Hunde im Kanton Zürich",
      "title_en": "Dogs in the Canton of Zurich",
      "language": "de",
      "extent_id": "CH-ZH",
      "authority": "official_info",
      "categories": ["dogs", "hiking"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Leinenpflicht", "anchor": "leinenpflicht",
         "text_original": "Im Kanton Zürich gilt vom 1. April bis 31. Juli im Wald und am Waldrand Leinenpflicht für Hunde.",
         "text_en": "In the Canton of Zurich, dogs must be kept on a leash in forests and at forest edges from 1 April to 31 July to protect wildlife. This applies on hiking trails through forest."}
      ]
    },
    {
      "source_id": "stadt_zuerich",
      "url": "https://www.stadt-zuerich.ch/de/stadtleben/parks/hunde.html",
      "identifier": null,
      "title_original": "Hunde in städtischen Parks",
      "title_en": "Dogs in city parks",
      "language": "de",
      "extent_id": "CH-ZH-261",
      "authority": "official_info",
      "categories": ["dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Parks", "anchor": null,
         "text_original": "In den Parkanlagen der Stadt Zürich sind Hunde an der Leine zu führen. Ausgenommen sind markierte Hundefreilaufzonen.",
         "text_en": "In the parks of the City of Zurich dogs must be kept on a leash, except in marked off-leash dog zones. A list of off-leash zones is published by Grün Stadt Zürich."}
      ]
    },
    {
      "source_id": "stadt_zuerich",
      "url": "https://www.stadt-zuerich.ch/de/stadtleben/parks/kreis-3.html",
      "identifier": null,
      "title_original": "Parks im Kreis 3",
      "title_en": "Parks in Kreis 3",
      "language": "de",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["dogs", "hiking"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Kreis 3 > Hundefreilaufzonen", "anchor": null,
         "text_original": "Im Kreis 3 befindet sich eine Hundefreilaufzone im Fritschiwiese-Park in Wiedikon.",
         "text_en": "In Kreis 3 there is an off-leash dog zone at Fritschiwiese park in Wiedikon. Dogs may run free there; on the Uetliberg hiking trails they must be leashed in the forest season."}
      ]
    },
    {
      "source_id": "schweizer_wanderwege",
      "url": "https://www.schweizer-wanderwege.ch/de/sicherheit/hunde",
      "identifier": null,
      "title_original": "Wandern mit Hund",
      "title_en": "Hiking with a dog",
      "language": "de",
      "extent_id": "CH",
      "authority": "institutional",
      "categories": ["hiking", "dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Sicherheit", "anchor": null,
         "text_original": "Auf Alpweiden mit Mutterkühen Hunde an die Leine nehmen und Abstand halten.",
         "text_en": "On alpine pastures with suckler cows keep your dog on a leash and keep your distance. Leash rules on hiking trails differ by canton; check the cantonal rules before you go."}
      ]
    },
    {
      "source_id": "ch_ch",
      "url": "https://www.ch.ch/en/dogs",
      "identifier": null,
      "title_original": "Dogs",
      "title_en": "Dogs",
      "language": "en",
      "extent_id": "CH",
      "authority": "official_info",
      "categories": ["dogs", "taxes"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Dog tax", "anchor": null,
         "text_original": "Dog tax is levied by the cantons and communes; the amount varies by commune.",
         "text_en": "Dog tax is levied by the cantons and communes; the amount varies by commune. Ask your commune for the rate and registration procedure."}
      ]
    },
    {
      "source_id": "ch_ch",
      "url": "https://www.ch.ch/en/dogs/basel-stadt",
      "identifier": null,
      "title_original": "Hunde in Basel-Stadt",
      "title_en": "Dogs in Basel-Stadt",
      "language": "de",
      "extent_id": "CH-BS",
      "authority": "official_info",
      "categories": ["dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Basel-Stadt", "anchor": null,
         "text_original": "In Basel-Stadt gilt in allen öffentlichen Parks ganzjährig Leinenpflicht für Hunde.",
         "text_en": "In Basel-Stadt dogs must be leashed in all public parks all year round. There are no seasonal exceptions on hiking trails in the canton."}
      ]
    }
  ]
}
```

- [ ] **Step 2: Write the failing integration test**

```python
# tests/integration/test_fixture_loader.py
import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    return u


def test_load_fixture_inserts_documents_and_chunks(url):
    with connect(url) as conn:
        report = load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        docs = conn.execute("select count(*) as n from document").fetchone()["n"]
        chunks = conn.execute("select count(*) as n from chunk").fetchone()["n"]
        sample = conn.execute(
            "select extent_id, authority, categories, document_status from chunk limit 1"
        ).fetchone()
    assert report.documents == 8
    assert report.chunks == 8
    assert docs == 8 and chunks == 8
    assert sample["document_status"] == "current"


def test_load_fixture_twice_is_idempotent(url):
    with connect(url) as conn:
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        docs = conn.execute("select count(*) as n from document").fetchone()["n"]
    assert docs == 8


def test_fixture_with_unknown_source_fails_clearly(url, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"documents":[{"source_id":"nope","url":"u","title_original":"t","title_en":"t","language":"de","extent_id":"CH","authority":"official_info","categories":[],"chunks":[]}]}')
    with connect(url) as conn, pytest.raises(ValueError, match="unknown source"):
        load_fixture(conn, bad, FakeEmbedder(dim=8))
```

- [ ] **Step 3: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_fixture_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement**

```python
# src/swiss_grounding/ingest/fixture_loader.py
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import psycopg
from pydantic import BaseModel, ConfigDict

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.embedder import Embedder


class FixtureChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading_path: str = ""
    anchor: str | None = None
    text_original: str
    text_en: str


class FixtureDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    url: str
    identifier: str | None = None
    title_original: str
    title_en: str
    language: str
    extent_id: str
    authority: Authority
    categories: list[str] = []
    valid_from: date | None = None
    chunks: list[FixtureChunk] = []


class Fixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[FixtureDocument]


@dataclass(frozen=True)
class LoadReport:
    documents: int
    chunks: int


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_fixture(conn: psycopg.Connection, path: Path, embedder: Embedder) -> LoadReport:
    """Insert fixture documents and chunks. Re-running with the same URL and content is a no-op."""
    fixture = Fixture.model_validate(json.loads(path.read_text()))
    known_sources = {r["id"] for r in conn.execute("select id from source").fetchall()}
    known_locations = {r["id"] for r in conn.execute("select id from location").fetchall()}
    docs_written = 0
    chunks_written = 0
    for doc in fixture.documents:
        if doc.source_id not in known_sources:
            raise ValueError(f"unknown source id {doc.source_id!r} in fixture {path}")
        if doc.extent_id not in known_locations:
            raise ValueError(f"unknown extent id {doc.extent_id!r} in fixture {path}")
        content_hash = _hash("\n".join(c.text_en for c in doc.chunks))
        existing = conn.execute(
            "select id from document where url = %s and content_hash = %s and status = 'current'",
            (doc.url, content_hash),
        ).fetchone()
        if existing:
            continue
        row = conn.execute(
            """
            insert into document (source_id, url, identifier, title_original, title_en, language,
                                  extent_id, authority, categories, valid_from, content_hash)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id
            """,
            (doc.source_id, doc.url, doc.identifier, doc.title_original, doc.title_en,
             doc.language, doc.extent_id, doc.authority.value, json.dumps(doc.categories),
             doc.valid_from, content_hash),
        ).fetchone()
        document_id = row["id"]
        docs_written += 1
        vectors = embedder.embed([c.text_en for c in doc.chunks]) if doc.chunks else []
        for ordinal, (chunk, vector) in enumerate(zip(doc.chunks, vectors)):
            conn.execute(
                """
                insert into chunk (document_id, ordinal, text_original, text_en, heading_path, anchor,
                                   embedding, chunk_hash, extent_id, authority, categories)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (document_id, ordinal, chunk.text_original, chunk.text_en, chunk.heading_path,
                 chunk.anchor, vector, _hash(chunk.text_en), doc.extent_id, doc.authority.value,
                 doc.categories),
            )
            chunks_written += 1
    return LoadReport(documents=docs_written, chunks=chunks_written)
```

Write an empty `src/swiss_grounding/ingest/__init__.py`.

- [ ] **Step 5: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_fixture_loader.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/ingest tests/fixtures/zurich_hiking.json tests/integration/test_fixture_loader.py
git commit -m "feat: add fixture loader and Zurich hiking fixture"
```

---

### Task 12: Hybrid search with reciprocal rank fusion

**Files:**
- Create: `src/swiss_grounding/retrieval/search.py`, `tests/unit/test_rrf.py`, `tests/integration/test_search.py`

- [ ] **Step 1: Write the failing unit test for fusion**

```python
# tests/unit/test_rrf.py
from swiss_grounding.retrieval.search import reciprocal_rank_fusion


def test_rrf_combines_ranks():
    fused = reciprocal_rank_fusion(dense=[10, 20, 30], lexical=[20, 40], k=60)
    ids = [chunk_id for chunk_id, _ in fused]
    assert ids[0] == 20                     # appears in both lists
    assert set(ids) == {10, 20, 30, 40}
    scores = dict(fused)
    assert scores[20] == 1 / (60 + 2) + 1 / (60 + 1)


def test_rrf_reports_ranks():
    fused = reciprocal_rank_fusion(dense=[1], lexical=[2], k=60, with_ranks=True)
    assert fused == [(1, 1 / 61, 1, None), (2, 1 / 61, None, 1)]
```

- [ ] **Step 2: Write the failing integration test for search**

```python
# tests/integration/test_search.py
import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.search import hybrid_search

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return u


def test_search_filters_by_extent_path(url):
    embedder = FakeEmbedder(dim=8)
    with connect(url) as conn:
        hits = hybrid_search(
            conn, embedder, question="Do I need to leash my dog?",
            extent_path=("CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"), as_of=None, top_n=50,
        )
    extents = {h.chunk.extent_id for h in hits}
    assert "CH-BS" not in extents
    assert {"CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3"} >= extents
    assert len(hits) >= 5


def test_search_country_only_returns_only_ch(url):
    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="leash dog hiking",
            extent_path=("CH",), as_of=None, top_n=50,
        )
    assert {h.chunk.extent_id for h in hits} == {"CH"}


def test_search_as_of_excludes_future_valid_from(url):
    from datetime import date

    with connect(url) as conn:
        hits = hybrid_search(
            conn, FakeEmbedder(dim=8), question="animal welfare",
            extent_path=("CH",), as_of=date(2000, 1, 1), top_n=50,
        )
    identifiers = {h.chunk.identifier for h in hits}
    assert "SR 455 Art. 6" not in identifiers       # valid_from 2008
    assert "SR 704 Art. 1" in identifiers           # valid_from 1987


def test_hit_carries_document_fields(url):
    with connect(url) as conn:
        hits = hybrid_search(conn, FakeEmbedder(dim=8), question="dog", extent_path=("CH",), as_of=None, top_n=5)
    h = hits[0]
    assert h.chunk.url.startswith("https://")
    assert h.chunk.title_en
    assert h.chunk.retrieved_at is not None
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/unit/test_rrf.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement**

```python
# src/swiss_grounding/retrieval/search.py
from datetime import date
from typing import Sequence

import psycopg

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import ChunkRecord, Hit

CHUNK_COLUMNS = """
    c.id as chunk_id, c.document_id, c.ordinal, c.text_original, c.text_en, c.heading_path,
    c.anchor, c.extent_id, c.authority, c.categories,
    d.url, d.identifier, d.title_original, d.title_en, d.language, d.valid_from, d.retrieved_at,
    d.source_id, s.license
"""

FILTER = """
    c.extent_id = any(%(path)s)
    and (
        (%(as_of)s::date is null and c.document_status = 'current')
        or (%(as_of)s::date is not null
            and d.status in ('current', 'superseded')
            and (d.valid_from is null or d.valid_from <= %(as_of)s::date)
            and (d.valid_to is null or d.valid_to > %(as_of)s::date))
    )
"""

DENSE_SQL = f"""
select {CHUNK_COLUMNS}, c.embedding <=> %(vector)s as distance
from chunk c join document d on d.id = c.document_id join source s on s.id = d.source_id
where {FILTER}
order by distance asc
limit %(top_n)s
"""

LEXICAL_SQL = f"""
select {CHUNK_COLUMNS}, ts_rank_cd(c.tsv, q) as rank
from chunk c join document d on d.id = c.document_id join source s on s.id = d.source_id,
     websearch_to_tsquery('english', %(question)s) q
where {FILTER} and c.tsv @@ q
order by rank desc
limit %(top_n)s
"""


def reciprocal_rank_fusion(
    dense: Sequence[int], lexical: Sequence[int], k: int = 60, with_ranks: bool = False,
) -> list:
    """Fuse two ranked id lists. Returns (id, score) or (id, score, dense_rank, lexical_rank)."""
    dense_rank = {cid: i + 1 for i, cid in enumerate(dense)}
    lexical_rank = {cid: i + 1 for i, cid in enumerate(lexical)}
    ids = list(dict.fromkeys([*dense, *lexical]))
    scored = []
    for cid in ids:
        score = 0.0
        if cid in dense_rank:
            score += 1.0 / (k + dense_rank[cid])
        if cid in lexical_rank:
            score += 1.0 / (k + lexical_rank[cid])
        scored.append((cid, score, dense_rank.get(cid), lexical_rank.get(cid)))
    scored.sort(key=lambda t: -t[1])
    if with_ranks:
        return scored
    return [(cid, score) for cid, score, _, _ in scored]


def _record(row: dict) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=row["chunk_id"], document_id=row["document_id"], ordinal=row["ordinal"],
        text_original=row["text_original"], text_en=row["text_en"],
        heading_path=row["heading_path"], anchor=row["anchor"], extent_id=row["extent_id"],
        authority=Authority(row["authority"]), categories=tuple(row["categories"]),
        url=row["url"], identifier=row["identifier"], title_original=row["title_original"],
        title_en=row["title_en"], language=row["language"], valid_from=row["valid_from"],
        retrieved_at=row["retrieved_at"], license=row["license"], source_id=row["source_id"],
    )


def hybrid_search(
    conn: psycopg.Connection,
    embedder: Embedder,
    question: str,
    extent_path: tuple[str, ...],
    as_of: date | None,
    top_n: int = 50,
) -> tuple[Hit, ...]:
    """Dense and lexical retrieval restricted to the extent path, fused with RRF."""
    vector = embedder.embed([question])[0]
    params = {"path": list(extent_path), "as_of": as_of, "top_n": top_n}
    dense_rows = conn.execute(DENSE_SQL, {**params, "vector": vector}).fetchall()
    lexical_rows = conn.execute(LEXICAL_SQL, {**params, "question": question}).fetchall()
    records = {r["chunk_id"]: _record(r) for r in [*dense_rows, *lexical_rows]}
    fused = reciprocal_rank_fusion(
        dense=[r["chunk_id"] for r in dense_rows],
        lexical=[r["chunk_id"] for r in lexical_rows],
        with_ranks=True,
    )
    return tuple(
        Hit(chunk=records[cid], rrf_score=score, dense_rank=dr, lexical_rank=lr)
        for cid, score, dr, lr in fused
    )
```

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/unit/test_rrf.py -v && DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_search.py -v`
Expected: `2 passed` then `4 passed`

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/retrieval/search.py tests/unit/test_rrf.py tests/integration/test_search.py
git commit -m "feat: hybrid search with extent filter and reciprocal rank fusion"
```

---

### Task 13: Reranker

**Files:**
- Create: `src/swiss_grounding/retrieval/rerank.py`, `tests/unit/test_rerank.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_rerank.py
from datetime import datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.models import ChunkRecord, Hit
from swiss_grounding.retrieval.rerank import RerankWeights, rerank


def make_hit(chunk_id, extent_id, authority, categories, rrf=0.01):
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=chunk_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id, authority=authority,
        categories=tuple(categories), url="https://x", identifier=None, title_original="t",
        title_en="t", language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1),
        license=None, source_id="s",
    )
    return Hit(chunk=chunk, rrf_score=rrf, dense_rank=1, lexical_rank=1)


TREE = LocationTree.from_locations(seed_locations())
QUERY_NODE = "CH-ZH-261-K3"


def test_more_specific_extent_ranks_higher_all_else_equal():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, ["dogs"]),
        make_hit(2, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, ["dogs"]),
        make_hit(3, "CH-ZH", Authority.OFFICIAL_INFO, ["dogs"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=("dogs",), weights=RerankWeights())
    assert [s.hit.chunk.chunk_id for s in ranked] == [2, 3, 1]


def test_category_overlap_boosts():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, ["waste"]),
        make_hit(2, "CH", Authority.OFFICIAL_INFO, ["dogs", "hiking"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=("dogs",), weights=RerankWeights())
    assert ranked[0].hit.chunk.chunk_id == 2
    assert ranked[0].category_overlap == 1.0
    assert ranked[1].category_overlap == 0.0


def test_authority_breaks_ties():
    hits = (
        make_hit(1, "CH", Authority.INSTITUTIONAL, ["dogs"]),
        make_hit(2, "CH", Authority.FEDERAL_LAW, ["dogs"]),
    )
    ranked = rerank(hits, TREE, QUERY_NODE, query_categories=(), weights=RerankWeights())
    assert ranked[0].hit.chunk.chunk_id == 2


def test_specificity_values():
    hits = (make_hit(1, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, []),
            make_hit(2, "CH", Authority.OFFICIAL_INFO, []))
    ranked = {s.hit.chunk.chunk_id: s for s in rerank(hits, TREE, QUERY_NODE, (), RerankWeights())}
    assert ranked[1].specificity == 1.0
    assert ranked[2].specificity == 0.25


def test_weights_zero_specificity_leaves_rrf_order():
    hits = (
        make_hit(1, "CH", Authority.OFFICIAL_INFO, [], rrf=0.05),
        make_hit(2, "CH-ZH-261-K3", Authority.OFFICIAL_INFO, [], rrf=0.01),
    )
    w = RerankWeights(specificity=0.0, category=0.0, authority=0.0, rrf=1.0)
    ranked = rerank(hits, TREE, QUERY_NODE, (), w)
    assert ranked[0].hit.chunk.chunk_id == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_rerank.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/retrieval/rerank.py
from dataclasses import dataclass
from typing import Sequence

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import AUTHORITY_RANK
from swiss_grounding.retrieval.models import Hit, ScoredHit


@dataclass(frozen=True)
class RerankWeights:
    """Additive weights. rrf is multiplied by rrf_scale so it lives on a similar scale."""
    specificity: float = 0.5
    category: float = 0.3
    authority: float = 0.2
    rrf: float = 1.0
    rrf_scale: float = 30.0


def specificity_score(tree: LocationTree, query_node_id: str, chunk_extent_id: str) -> float:
    """1.0 for an exact extent match, decaying with each level of generality."""
    distance = tree.distance(query_node_id, chunk_extent_id)
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + distance)


def category_overlap(query_categories: Sequence[str], chunk_categories: Sequence[str]) -> float:
    if not query_categories:
        return 0.0
    matched = sum(1 for c in query_categories if c in chunk_categories)
    return matched / len(query_categories)


def rerank(
    hits: Sequence[Hit],
    tree: LocationTree,
    query_node_id: str,
    query_categories: Sequence[str],
    weights: RerankWeights,
) -> tuple[ScoredHit, ...]:
    scored = []
    for hit in hits:
        spec = specificity_score(tree, query_node_id, hit.chunk.extent_id)
        cat = category_overlap(query_categories, hit.chunk.categories)
        auth = AUTHORITY_RANK[hit.chunk.authority]
        score = (
            weights.specificity * spec
            + weights.category * cat
            + weights.authority * auth
            + weights.rrf * weights.rrf_scale * hit.rrf_score
        )
        scored.append(ScoredHit(hit=hit, score=score, specificity=spec,
                                category_overlap=cat, authority_score=auth))
    return tuple(sorted(scored, key=lambda s: (-s.score, s.hit.chunk.chunk_id)))
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_rerank.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/retrieval/rerank.py tests/unit/test_rerank.py
git commit -m "feat: deterministic reranker over specificity, category and authority"
```

---

### Task 14: Diversifier and citation builder

**Files:**
- Create: `src/swiss_grounding/retrieval/diversify.py`, `src/swiss_grounding/retrieval/cite.py`, `tests/unit/test_diversify.py`, `tests/unit/test_cite.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_diversify.py
from datetime import datetime

from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def scored(chunk_id, document_id, extent_id, score, specificity):
    chunk = ChunkRecord(
        chunk_id=chunk_id, document_id=document_id, ordinal=0, text_original="o", text_en="e",
        heading_path="", anchor=None, extent_id=extent_id, authority=Authority.OFFICIAL_INFO,
        categories=(), url="u", identifier=None, title_original="t", title_en="t",
        language="de", valid_from=None, retrieved_at=datetime(2026, 1, 1), license=None,
        source_id="s",
    )
    hit = Hit(chunk=chunk, rrf_score=0.0, dense_rank=None, lexical_rank=None)
    return ScoredHit(hit=hit, score=score, specificity=specificity, category_overlap=0, authority_score=0)


def test_caps_chunks_per_document():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 100, "CH", 0.8, 0.25),
        scored(3, 100, "CH", 0.7, 0.25), scored(4, 200, "CH", 0.6, 0.25),
    )
    out = diversify(items, limit=3, per_document_cap=2)
    assert [s.hit.chunk.chunk_id for s in out] == [1, 2, 4]


def test_guarantees_most_specific_extent_present():
    items = (
        scored(1, 100, "CH", 0.9, 0.25), scored(2, 200, "CH", 0.8, 0.25),
        scored(3, 300, "CH-ZH-261-K3", 0.1, 1.0),
    )
    out = diversify(items, limit=2, per_document_cap=2)
    ids = [s.hit.chunk.chunk_id for s in out]
    assert 3 in ids and len(ids) == 2


def test_empty_input():
    assert diversify((), limit=5, per_document_cap=2) == ()
```

```python
# tests/unit/test_cite.py
from datetime import date, datetime

from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.models import Authority
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.models import ChunkRecord, Hit, ScoredHit


def test_citation_copies_fields_and_labels_extent():
    chunk = ChunkRecord(
        chunk_id=7, document_id=3, ordinal=0, text_original="Im Kanton Zürich gilt Leinenpflicht.",
        text_en="In the Canton of Zurich dogs must be leashed.", heading_path="Leinenpflicht",
        anchor="leinenpflicht", extent_id="CH-ZH", authority=Authority.OFFICIAL_INFO,
        categories=("dogs",), url="https://www.zh.ch/x", identifier=None,
        title_original="Hunde", title_en="Dogs", language="de", valid_from=date(2020, 1, 1),
        retrieved_at=datetime(2026, 9, 1), license="zh terms", source_id="zh_ch",
    )
    sh = ScoredHit(hit=Hit(chunk=chunk, rrf_score=0.0, dense_rank=1, lexical_rank=None),
                   score=0.7, specificity=0.5, category_overlap=1.0, authority_score=0.6)
    tree = LocationTree.from_locations(seed_locations())
    c = build_citation(sh, tree)
    assert c.url == "https://www.zh.ch/x" and c.anchor == "leinenpflicht"
    assert c.extent_label == "Zurich" and c.extent_id == "CH-ZH"
    assert c.authority == "official_info"
    assert c.snippet_original.startswith("Im Kanton")
    assert c.score == 0.7
    assert c.license == "zh terms"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_diversify.py tests/unit/test_cite.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `diversify.py`**

```python
# src/swiss_grounding/retrieval/diversify.py
from typing import Sequence

from swiss_grounding.retrieval.models import ScoredHit


def diversify(
    ranked: Sequence[ScoredHit], limit: int, per_document_cap: int = 2,
) -> tuple[ScoredHit, ...]:
    """Cap chunks per document and guarantee the most specific extent is represented."""
    if not ranked:
        return ()
    chosen: list[ScoredHit] = []
    per_doc: dict[int, int] = {}
    for item in ranked:
        if len(chosen) >= limit:
            break
        doc = item.hit.chunk.document_id
        if per_doc.get(doc, 0) >= per_document_cap:
            continue
        chosen.append(item)
        per_doc[doc] = per_doc.get(doc, 0) + 1
    most_specific = max(ranked, key=lambda s: s.specificity)
    chosen_ids = {s.hit.chunk.chunk_id for s in chosen}
    if most_specific.hit.chunk.chunk_id not in chosen_ids:
        chosen = [*chosen[: max(limit - 1, 0)], most_specific]
    return tuple(chosen)
```

- [ ] **Step 4: Write `cite.py`**

```python
# src/swiss_grounding/retrieval/cite.py
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, ScoredHit

SNIPPET_CHARS = 600


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1] + "…"


def build_citation(scored: ScoredHit, tree: LocationTree) -> Citation:
    c = scored.hit.chunk
    return Citation(
        chunk_id=c.chunk_id, document_id=c.document_id, source_id=c.source_id,
        title_en=c.title_en, title_original=c.title_original, url=c.url, anchor=c.anchor,
        identifier=c.identifier, snippet_en=_snippet(c.text_en),
        snippet_original=_snippet(c.text_original), language=c.language,
        heading_path=c.heading_path, extent_id=c.extent_id,
        extent_label=tree.get(c.extent_id).label("en"), authority=c.authority.value,
        categories=c.categories, valid_from=c.valid_from, retrieved_at=c.retrieved_at,
        license=c.license, score=round(scored.score, 4),
    )
```

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/unit/test_diversify.py tests/unit/test_cite.py -v`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/retrieval/diversify.py src/swiss_grounding/retrieval/cite.py tests/unit/test_diversify.py tests/unit/test_cite.py
git commit -m "feat: result diversification and structured citations"
```

---

### Task 15: Query core

**Files:**
- Create: `src/swiss_grounding/retrieval/query_core.py`, `tests/integration/test_query_core.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_query_core.py
import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.models import QueryRequest
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


class NoGeo:
    def search_communes(self, text):
        return ()


@pytest.fixture
def core():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        tree = load_tree(conn)
    return QueryCore(
        database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
        embedder=FakeEmbedder(dim=8), weights=RerankWeights(),
    )


def test_neighborhood_question_prefers_specific_and_excludes_siblings(core):
    resp = core.query(QueryRequest(question="Where can my dog run off leash?", location="Wiedikon", categories=("dogs",)))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-ZH-261-K3-ALT-WIEDIKON"
    extents = [c.extent_id for c in resp.citations]
    assert extents[0] == "CH-ZH-261-K3"
    assert "CH-BS" not in extents
    assert any(e == "CH-ZH-261" for e in extents)


def test_missing_location_returns_needs_location(core):
    resp = core.query(QueryRequest(question="Do I need to leash my dog in the forest?"))
    assert resp.status == "needs_location"
    assert resp.citations == ()
    assert "city, canton, or postal code" in resp.message


def test_unresolvable_location_returns_needs_location_with_reason(core):
    resp = core.query(QueryRequest(question="dog rules", location="Atlantis"))
    assert resp.status == "needs_location"
    assert "Atlantis" in resp.message


def test_country_question_returns_only_country_scoped(core):
    resp = core.query(QueryRequest(question="Who is responsible for hiking trails?", location="Switzerland"))
    assert resp.status == "results"
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_unindexed_canton_falls_back_to_federal_only(core):
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-GE"
    assert {c.extent_id for c in resp.citations} == {"CH"}


def test_no_evidence_when_nothing_indexed_for_path(core):
    with connect(core.database_url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
    resp = core.query(QueryRequest(question="dog leash", location="Genève"))
    assert resp.status == "no_evidence"
    assert resp.resolved_location_id == "CH-GE"
    assert "Geneva" in resp.message


def test_location_in_question_is_detected(core):
    resp = core.query(QueryRequest(question="What are the dog rules in Basel?"))
    assert resp.status == "results"
    assert resp.resolved_location_id == "CH-BS"
    assert all(c.extent_id in {"CH", "CH-BS"} for c in resp.citations)
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_query_core.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/retrieval/query_core.py
import re
from dataclasses import dataclass, replace

from swiss_grounding.db.connection import connect
from swiss_grounding.locations.models import ResolvedLocation
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.categories import CATEGORY_IDS
from swiss_grounding.retrieval.cite import build_citation
from swiss_grounding.retrieval.diversify import diversify
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import QueryRequest, QueryResponse
from swiss_grounding.retrieval.rerank import RerankWeights, rerank
from swiss_grounding.retrieval.search import hybrid_search

CANDIDATE_TOP_N = 50
PER_DOCUMENT_CAP = 2
MAX_LIMIT = 25
NEEDS_LOCATION_MESSAGE = (
    "No location was given and none was recognised in the question. "
    "Ask the user which city, canton, or postal code they are interested in, then search again."
)
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9.\-]*")


@dataclass(frozen=True)
class QueryCore:
    database_url: str
    tree: LocationTree
    resolver: LocationResolver
    embedder: Embedder
    weights: RerankWeights

    def query(self, request: QueryRequest) -> QueryResponse:
        if not request.question.strip():
            return QueryResponse(status="needs_location", message="The question is empty.")
        unknown = [c for c in request.categories if c not in CATEGORY_IDS]
        if unknown:
            return QueryResponse(status="needs_location", message=f"Unknown categories: {unknown}")
        resolved = self._resolve(request)
        if resolved is None:
            text = request.location or ""
            message = (
                f"Could not resolve location {text!r}. Ask the user for a city, canton, or postal code."
                if text.strip() else NEEDS_LOCATION_MESSAGE
            )
            return QueryResponse(status="needs_location", message=message)
        limit = max(1, min(request.limit, MAX_LIMIT))
        with connect(self.database_url) as conn:
            hits = hybrid_search(
                conn, self.embedder, question=request.question, extent_path=resolved.path,
                as_of=request.as_of, top_n=CANDIDATE_TOP_N,
            )
        base = QueryResponse(
            status="no_evidence", resolved_location_id=resolved.location.id,
            resolved_location_label=resolved.location.label("en"),
            resolution_method=resolved.method,
            alternatives=tuple(a.id for a in resolved.alternatives),
            categories_used=request.categories,
        )
        if not hits:
            label = resolved.location.label("en")
            return replace(base, message=f"No indexed evidence for {label} or its parent jurisdictions.")
        ranked = rerank(hits, self.tree, resolved.location.id, request.categories, self.weights)
        chosen = diversify(ranked, limit=limit, per_document_cap=PER_DOCUMENT_CAP)
        citations = tuple(build_citation(s, self.tree) for s in chosen)
        return replace(base, status="results", citations=citations)

    def _resolve(self, request: QueryRequest) -> ResolvedLocation | None:
        if request.location and request.location.strip():
            return self.resolver.resolve(request.location)
        return self._resolve_from_question(request.question)

    def _resolve_from_question(self, question: str) -> ResolvedLocation | None:
        """Alias-only scan of the question text, longest n-gram first. Never calls GeoAdmin."""
        words = WORD_RE.findall(question)
        for size in (3, 2, 1):
            for start in range(0, max(0, len(words) - size + 1)):
                candidate = " ".join(words[start:start + size]).rstrip("?.,!")
                matches = self.tree.find(candidate)
                if matches:
                    best = matches[0]
                    return ResolvedLocation(
                        location=best, path=self.tree.path(best.id), method="alias_in_question",
                        input_text=candidate, alternatives=tuple(matches[1:]),
                    )
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_query_core.py -v`
Expected: `7 passed`

If `test_neighborhood_question_prefers_specific_and_excludes_siblings` fails on the first extent, the FakeEmbedder ranking is noisy; the reranker weights are the fix, not the test. Raise `RerankWeights.specificity` to `0.8` and rerun.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/retrieval/query_core.py tests/integration/test_query_core.py
git commit -m "feat: query core orchestrating resolve, filter, search, rerank, cite"
```

---

### Task 16: Application wiring

**Files:**
- Create: `src/swiss_grounding/app.py`, `tests/integration/test_app.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_app.py
import os

import pytest

from swiss_grounding.app import build_query_core
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


def test_build_query_core_loads_tree_from_db():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        upsert_locations(conn, seed_locations())
    settings = Settings(database_url=url, embedding_backend="fake", embedding_dim=8)
    core = build_query_core(settings)
    assert core.tree.by_bfs_id(261).id == "CH-ZH-261"
    assert core.embedder.dim == 8
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/app.py
"""Composition root: builds fully wired objects from settings."""
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.locations.geoadmin import GeoAdminClient
from swiss_grounding.locations.repository import load_tree
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights


def build_query_core(settings: Settings) -> QueryCore:
    with connect(settings.database_url) as conn:
        tree = load_tree(conn)
    if not tree.by_id:
        raise RuntimeError("location table is empty; run `swiss-grounding db seed` first")
    geo = GeoAdminClient.from_settings(settings.geoadmin_base_url, settings.geoadmin_timeout_seconds)
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    return QueryCore(
        database_url=settings.database_url, tree=tree,
        resolver=LocationResolver(tree, geo), embedder=embedder, weights=RerankWeights(),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_app.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/app.py tests/integration/test_app.py
git commit -m "feat: composition root for the query core"
```

---

### Task 17: MCP server

**Files:**
- Create: `src/swiss_grounding/mcp_server/__init__.py`, `src/swiss_grounding/mcp_server/server.py`, `tests/integration/test_mcp_server.py`

- [ ] **Step 1: Write the failing integration test**

Uses the MCP in-memory client so no transport is needed.

```python
# tests/integration/test_mcp_server.py
import json
import os
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.mcp_server.server import build_server
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"


@pytest.fixture
def server():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
    return build_server(Settings(database_url=url, embedding_backend="fake", embedding_dim=8))


async def call(server, name, args):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args)
        return json.loads(result.content[0].text)


async def test_lists_expected_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools.tools}
    assert names == {"swiss_resolve_location", "swiss_search", "swiss_get_document",
                     "swiss_list_categories", "swiss_coverage"}


async def test_search_returns_results_with_notice(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?", "location": "Wiedikon"})
    assert data["status"] == "results"
    assert data["notice"].startswith("Retrieved public information")
    assert data["citations"][0]["url"].startswith("https://")
    assert "snippet_original" not in data["citations"][0]      # concise by default


async def test_search_detailed_includes_original_snippet(server):
    data = await call(server, "swiss_search", {"question": "leash", "location": "Wiedikon", "response_format": "detailed"})
    assert "snippet_original" in data["citations"][0]


async def test_search_without_location_asks(server):
    data = await call(server, "swiss_search", {"question": "Can my dog run off leash?"})
    assert data["status"] == "needs_location"


async def test_resolve_location(server):
    data = await call(server, "swiss_resolve_location", {"query": "8003"})
    assert data["location_id"] == "CH-ZH-261-K3"
    assert data["path"][0] == "CH"


async def test_get_document(server):
    search = await call(server, "swiss_search", {"question": "leash", "location": "Zurich"})
    doc_id = search["citations"][0]["document_id"]
    data = await call(server, "swiss_get_document", {"document_id": doc_id})
    assert data["document"]["id"] == doc_id
    assert len(data["chunks"]) >= 1


async def test_list_categories(server):
    data = await call(server, "swiss_list_categories", {})
    assert any(c["id"] == "hiking" for c in data["categories"])


async def test_coverage(server):
    data = await call(server, "swiss_coverage", {"location": "Zurich"})
    extents = {row["extent_id"] for row in data["coverage"]}
    assert "CH-ZH-261" in extents and "CH-BS" not in extents
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_mcp_server.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/mcp_server/server.py
import json
from dataclasses import asdict
from datetime import date
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from swiss_grounding.app import build_query_core
from swiss_grounding.config import Settings
from swiss_grounding.db.connection import connect
from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.retrieval.models import NOTICE, QueryRequest, QueryResponse
from swiss_grounding.retrieval.query_core import QueryCore

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
CONCISE_DROP = {"snippet_original", "title_original", "heading_path", "license", "retrieved_at"}


def _json(obj: Any) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)


def _response_to_dict(resp: QueryResponse, response_format: str) -> dict:
    data = asdict(resp)
    if response_format == "concise":
        data["citations"] = [
            {k: v for k, v in c.items() if k not in CONCISE_DROP} for c in data["citations"]
        ]
    return data


def build_server(settings: Settings) -> FastMCP:
    core: QueryCore = build_query_core(settings)
    mcp = FastMCP("swiss-grounding")

    @mcp.tool(annotations=READ_ONLY)
    def swiss_resolve_location(query: str) -> str:
        """Resolve a Swiss place name, canton, city district, or postal code to a jurisdiction node.
        Use this to confirm the location with the user before calling swiss_search when the
        user's wording is ambiguous."""
        resolved = core.resolver.resolve(query)
        if resolved is None:
            return _json({"found": False, "query": query,
                          "message": "No Swiss location matched. Ask for a city, canton, or postal code."})
        return _json({
            "found": True, "location_id": resolved.location.id,
            "label": resolved.location.label("en"), "level": resolved.location.level.value,
            "path": list(resolved.path), "method": resolved.method,
            "alternatives": [a.id for a in resolved.alternatives],
        })

    @mcp.tool(annotations=READ_ONLY)
    def swiss_search(
        question: str,
        location: str | None = None,
        categories: list[str] | None = None,
        as_of: str | None = None,
        limit: int = 8,
        response_format: Literal["concise", "detailed"] = "concise",
    ) -> str:
        """Search Swiss public sources (federal law, cantonal and municipal information,
        institutional guidance) for evidence answering a question, restricted to the
        jurisdictions that apply to a location.

        The location is a hard filter: only documents scoped to the location or one of its
        parent jurisdictions (city, canton, Switzerland) are returned, most specific first.
        If the question concerns a specific place and no location is given, the response
        status is 'needs_location': ask the user for a city, canton, or postal code, then
        call again. Do not guess a location.

        categories: optional hints from swiss_list_categories; they rerank, never exclude.
        as_of: ISO date to retrieve law as it stood on that date.
        Results are evidence with citations; write the answer from them and cite the URLs.
        Never invent URLs."""
        parsed_as_of = date.fromisoformat(as_of) if as_of else None
        resp = core.query(QueryRequest(
            question=question, location=location, categories=tuple(categories or ()),
            as_of=parsed_as_of, limit=limit,
        ))
        return _json(_response_to_dict(resp, response_format))

    @mcp.tool(annotations=READ_ONLY)
    def swiss_get_document(document_id: int, chunk_id: int | None = None) -> str:
        """Fetch a full document, or one chunk of it, by id from a previous swiss_search result."""
        with connect(settings.database_url) as conn:
            doc = conn.execute(
                "select id, source_id, url, identifier, title_original, title_en, language, "
                "extent_id, authority, categories, valid_from, valid_to, retrieved_at, status "
                "from document where id = %s", (document_id,),
            ).fetchone()
            if doc is None:
                return _json({"error": f"document {document_id} not found"})
            if chunk_id is None:
                chunks = conn.execute(
                    "select id, ordinal, heading_path, anchor, text_en, text_original "
                    "from chunk where document_id = %s order by ordinal", (document_id,),
                ).fetchall()
            else:
                chunks = conn.execute(
                    "select id, ordinal, heading_path, anchor, text_en, text_original "
                    "from chunk where document_id = %s and id = %s", (document_id, chunk_id),
                ).fetchall()
        return _json({"document": doc, "chunks": chunks, "notice": NOTICE})

    @mcp.tool(annotations=READ_ONLY)
    def swiss_list_categories() -> str:
        """List the topic categories that swiss_search accepts as hints."""
        return _json({"categories": [asdict(c) for c in CATEGORIES]})

    @mcp.tool(annotations=READ_ONLY)
    def swiss_coverage(location: str | None = None) -> str:
        """Report which sources and jurisdictions are indexed, with document counts and the
        latest retrieval date. Use it to tell the user when a place has no coverage instead
        of guessing."""
        path: list[str] | None = None
        resolved_id = None
        if location:
            resolved = core.resolver.resolve(location)
            if resolved is None:
                return _json({"coverage": [], "message": f"Could not resolve {location!r}"})
            path = list(resolved.path)
            resolved_id = resolved.location.id
        with connect(settings.database_url) as conn:
            rows = conn.execute(
                "select d.extent_id, d.source_id, count(*) as documents, max(d.retrieved_at) as last_retrieved "
                "from document d where d.status = 'current' "
                "and (%(path)s::text[] is null or d.extent_id = any(%(path)s)) "
                "group by d.extent_id, d.source_id order by d.extent_id, d.source_id",
                {"path": path},
            ).fetchall()
        return _json({"resolved_location_id": resolved_id, "coverage": rows, "notice": NOTICE})

    return mcp
```

Write an empty `src/swiss_grounding/mcp_server/__init__.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_mcp_server.py -v`
Expected: `8 passed`

If `create_connected_server_and_client_session` needs the low-level server object under a different attribute in the installed `mcp` version, check `FastMCP` for `_mcp_server` and adjust the test helper, not the server.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/mcp_server tests/integration/test_mcp_server.py
git commit -m "feat: MCP server with five read-only grounding tools"
```

---

### Task 18: CLI

**Files:**
- Create: `src/swiss_grounding/cli/__init__.py`, `src/swiss_grounding/cli/main.py`, `tests/integration/test_cli.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_cli.py
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from swiss_grounding.cli.main import app

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
runner = CliRunner()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    assert os.environ.get("DATABASE_URL")


def test_full_cli_flow():
    assert runner.invoke(app, ["db", "init"]).exit_code == 0
    assert runner.invoke(app, ["db", "seed"]).exit_code == 0
    r = runner.invoke(app, ["load-fixture", str(FIXTURE)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["query", "Can my dog run off leash?", "--location", "Wiedikon", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["status"] == "results"
    r = runner.invoke(app, ["query", "Can my dog run off leash?"])
    assert r.exit_code == 2
    assert "needs_location" in r.output
```

- [ ] **Step 2: Run to verify it fails**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/swiss_grounding/cli/main.py
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Optional

import typer

from swiss_grounding.app import build_query_core
from swiss_grounding.config import load_settings
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import build_embedder
from swiss_grounding.retrieval.models import QueryRequest

app = typer.Typer(help="Swiss Grounding MCP command line.", no_args_is_help=True)
db_app = typer.Typer(help="Database commands.")
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init() -> None:
    """Create tables and the pgvector extension."""
    settings = load_settings()
    apply_schema(settings.database_url, settings.embedding_dim)
    typer.echo("schema applied")


@db_app.command("seed")
def db_seed() -> None:
    """Insert the location tree and seed source definitions."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
    typer.echo("locations and sources seeded")


@app.command("load-fixture")
def load_fixture_cmd(path: Path) -> None:
    """Load a JSON fixture of documents and chunks (development and demo only)."""
    settings = load_settings()
    if not path.exists():
        typer.echo(f"fixture not found: {path}", err=True)
        raise typer.Exit(code=1)
    embedder = build_embedder(settings.embedding_backend, settings.embedding_model, settings.embedding_dim)
    with connect(settings.database_url) as conn:
        report = load_fixture(conn, path, embedder)
    typer.echo(f"loaded {report.documents} documents, {report.chunks} chunks")


@app.command("query")
def query_cmd(
    question: str,
    location: Optional[str] = typer.Option(None, "--location", "-l"),
    categories: Optional[str] = typer.Option(None, "--categories", "-c", help="comma-separated"),
    as_of: Optional[str] = typer.Option(None, "--as-of", help="ISO date"),
    limit: int = typer.Option(8, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run the query core and print evidence. Exit code 2 when a location is needed."""
    core = build_query_core(load_settings())
    request = QueryRequest(
        question=question, location=location,
        categories=tuple(c.strip() for c in categories.split(",")) if categories else (),
        as_of=date.fromisoformat(as_of) if as_of else None, limit=limit,
    )
    resp = core.query(request)
    if as_json:
        typer.echo(json.dumps(asdict(resp), default=str, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"status: {resp.status}")
        if resp.resolved_location_id:
            typer.echo(f"location: {resp.resolved_location_label} ({resp.resolved_location_id}, {resp.resolution_method})")
        if resp.message:
            typer.echo(resp.message)
        for i, c in enumerate(resp.citations, 1):
            typer.echo(f"\n[{i}] {c.title_en} — {c.extent_label} / {c.authority} (score {c.score})")
            typer.echo(f"    {c.url}{'#' + c.anchor if c.anchor else ''}")
            typer.echo(f"    {c.snippet_en}")
        typer.echo(f"\n{resp.notice}")
    if resp.status == "needs_location":
        raise typer.Exit(code=2)


@app.command("serve")
def serve_cmd(transport: str = typer.Option("stdio", "--transport", help="stdio or http")) -> None:
    """Start the MCP server."""
    from swiss_grounding.mcp_server.server import build_server

    server = build_server(load_settings())
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "http":
        server.run(transport="streamable-http")
    else:
        typer.echo("transport must be stdio or http", err=True)
        raise typer.Exit(code=1)
```

Write an empty `src/swiss_grounding/cli/__init__.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest tests/integration/test_cli.py -v`
Expected: `1 passed`

- [ ] **Step 5: Smoke-test the real commands**

```bash
cp .env.example .env
uv run swiss-grounding db init
uv run swiss-grounding db seed
uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json
uv run swiss-grounding query "Where can my dog run off leash?" --location Wiedikon --categories dogs
```
Expected: `status: results`, first citation labelled `District 3 / official_info`, Basel absent.

- [ ] **Step 6: Commit**

```bash
git add src/swiss_grounding/cli tests/integration/test_cli.py
git commit -m "feat: CLI with db, load-fixture, query and serve commands"
```

---

### Task 19: Full test run, lint, README check

**Files:**
- Modify: `README.md` (only if commands changed)

- [ ] **Step 1: Run everything**

Run: `uv run ruff check src tests && uv run pytest tests/unit -v && DATABASE_URL=postgresql://swiss:swiss@localhost:5433/swiss_grounding uv run pytest -m integration -v`
Expected: ruff clean, all unit tests pass, all integration tests pass.

- [ ] **Step 2: Fix any ruff findings**

Apply `uv run ruff check --fix src tests` for import ordering; fix anything else by hand.

- [ ] **Step 3: Verify the README quick start works from a clean database**

```bash
docker compose down -v && docker compose up -d db && sleep 5
uv run swiss-grounding db init && uv run swiss-grounding db seed
uv run swiss-grounding load-fixture tests/fixtures/zurich_hiking.json
uv run swiss-grounding query "Do I need to leash my dog on hiking trails?" --location Wiedikon
```
Expected: results printed, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: lint fixes and verified quick start"
```

---

## Self-review against the spec

**Coverage of spec sections in this plan:**
- §3 architecture, package layout: Tasks 1, 16
- §4 data model (all six Plan 1 tables): Task 3
- §4 location tree, seed, aliases, PLZ: Tasks 4, 5, 6
- §6 query pipeline steps 1–6, `needs_location`, `no_evidence`, as-of filter, never relax to sibling: Tasks 7, 12, 13, 14, 15
- §7 tools 1–5 with annotations, `notice`, `response_format`, routing instruction in description: Task 17
- §8 CLI `db`, `load-fixture`, `query`, `serve`: Task 18
- §10 error handling: GeoAdmin failures return `needs_location` (Task 7, 15), tool inputs validated (Tasks 8, 11, 15), unknown ids return structured errors (Task 17), settings from environment (Task 2)

**Deferred to Plan 2 (ingestion):** fetchers, change detection, versioning and `document_change` writes, translation, extent narrowing, category tagging, chunking, `ingest` and `sources` commands, `swiss_suggest_source` tool and `source_suggestion` writes.

**Deferred to Plan 3 (evals):** `eval_case` and `eval_run` tables, three suites, `eval generate`, `eval run`, `ask` command.

**Type consistency checked:** `ChunkRecord`, `Hit`, `ScoredHit`, `Citation`, `QueryRequest`, `QueryResponse` defined in Task 10 and used unchanged in Tasks 12–18. `LocationTree.find/path/distance/by_bfs_id/get/all` defined in Task 4 and used in Tasks 5–17. `RerankWeights` defined in Task 13, used in 15 and 16. `load_fixture` returns `LoadReport` (Task 11), used in Task 18.
