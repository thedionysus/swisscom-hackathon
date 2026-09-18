# Zurich Fix Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the red probes in `evals/probes/` green, in the order that flips the most probes per change, without spending API credits.

**Architecture:** Five behaviour changes, each gated by the probe suite: (1) seed every Swiss commune into the location tree from a committed register snapshot; (2) make the resolver honest, with level markers, ambiguity returned as a question, strict GeoAdmin acceptance, and typo tolerance; (3) add a coverage signal to search results; (4) re-narrow stored documents under ADR 0002; (5) rank calendar evidence nearest-future first and let `as_of` drive the clock. Each task ends by running the structural harness; a probe that starts passing reports `XPASS(strict)` and its `status` is flipped to green in the same commit. The last task re-records the live run and reverts the two fixture mirrors.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 16, PyYAML, typer, pytest. Register data from the Federal Statistical Office commune API (AGVCH) and the LINDAS SPARQL endpoint, both public and unauthenticated.

**Red set baseline (main after PR #16):** 47 probes, 31 red. Structural harness: 15 passed, 28 xfailed. Live: 16/47.

**Commands used throughout:**
```
export DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)"   # integration tests only; unset before CLI runs
uv run pytest tests/unit -q
uv run pytest tests/integration/test_probes_structural.py -q -rxX
uv run ruff check src tests
```
Commit messages: `<type>: <description>` ending with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

## File Structure

```
src/swiss_grounding/locations/
  data/communes.csv           committed register snapshot: bfs_id,name,canton,district,postal_codes
  register.py                 parse the snapshot into Location nodes (pure)
  register_fetch.py           fetch AGVCH + LINDAS and write the snapshot (network, CLI only)
  markers.py                  level-marker parsing ("Gemeinde X", "Kreis 3") (pure)
  fuzzy.py                    per-token edit distance and coverage check (pure)
  resolver.py                 modified: markers, ambiguity, strict GeoAdmin, fuzzy alias
  question_scan.py            modified: prose flag for the sentence-initial guard
  models.py                   modified: AmbiguousLocation
  seed.py                     modified: seed_locations() includes communes
src/swiss_grounding/retrieval/
  coverage.py                 per-extent document counts on a path (shared by search and swiss_coverage)
  models.py                   modified: CoverageRow, QueryResponse.coverage + resolution_note
  query_core.py               modified: coverage rows, ambiguity → needs_location, as_of clock
  rerank.py                   modified: nearest-future factor
src/swiss_grounding/ingest/
  narrowing.py                rewritten under ADR 0002
  enrich.py                   modified: passes title and headings
  renarrow.py                 re-narrow stored documents from stored text
src/swiss_grounding/cli/
  main.py                     + `locations fetch-register`, `ingest renarrow`
src/swiss_grounding/mcp_server/server.py   uses retrieval.coverage; resolve tool returns candidates
tests/unit/locations/  test_register.py, test_markers.py, test_fuzzy.py, test_resolver_*.py
tests/unit/ingest/     test_narrowing.py (rewritten), test_renarrow.py
tests/unit/            test_rerank.py (+ nearest-future), test_coverage_models.py
tests/integration/     test_register_seed.py, test_renarrow.py, test_coverage.py
tests/fixtures/        register_sample.csv, agvch_sample.csv, lindas_plz_sample.csv
```

---

## Task 1: Register snapshot and parser

The BFS AGVCH snapshot lists cantons (Level 1), districts (Level 2) and communes (Level 3) with `Parent` pointing at the parent's `HistoricalCode`. LINDAS gives postal codes per BFS number. The committed CSV is the single input for seeding; the fetcher only regenerates it.

**Files:**
- Create: `src/swiss_grounding/locations/register.py`
- Create: `src/swiss_grounding/locations/register_fetch.py`
- Create: `tests/fixtures/agvch_sample.csv`, `tests/fixtures/lindas_plz_sample.csv`
- Create: `tests/unit/locations/__init__.py` (empty), `tests/unit/locations/test_register.py`
- Generate: `src/swiss_grounding/locations/data/communes.csv` (via the CLI in Task 2)

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/agvch_sample.csv` (AGVCH format, semicolon-free, comma separated as the API returns):
```csv
HistoricalCode,BfsCode,ValidFrom,ValidTo,Level,Parent,Name,ShortName,Inscription,Radiation,Rec_Type_fr,Rec_Type_de
1,1,12.09.1848,,1,,Zürich,ZH,,,,
17,17,12.09.1848,,1,,St. Gallen,SG,,,,
10053,101,12.09.1848,,2,1,Bezirk Affoltern,Affoltern,100,,,
10054,102,12.09.1848,,2,1,Bezirk Winterthur,Winterthur,100,,,
10080,1721,12.09.1848,,2,17,Wahlkreis Wil,Wil,100,,,
11001,230,12.09.1848,,3,10054,Winterthur,Winterthur,1000,,,
11002,2,12.09.1848,,3,10053,Affoltern am Albis,Affoltern am Albis,1000,,,
11003,3427,12.09.1848,,3,10080,Wil (SG),Wil (SG),1000,,,
11004,34,12.09.1848,,3,10054,Wil (ZH),Wil (ZH),1000,,,
11005,261,12.09.1848,,3,10054,Zürich,Zürich,1000,,,
```
`tests/fixtures/lindas_plz_sample.csv`:
```csv
id,postalCode
230,8400
230,8404
2,8910
3427,9500
34,8196
261,8001
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/unit/locations/test_register.py
from pathlib import Path

from swiss_grounding.locations.models import Level
from swiss_grounding.locations.register import (
    Commune, commune_locations, parse_register_csv, write_register_csv,
)
from swiss_grounding.locations.register_fetch import merge_snapshot, parse_agvch, parse_lindas_plz

FIX = Path(__file__).parent.parent.parent / "fixtures"


def test_parse_agvch_yields_communes_with_canton_abbreviation():
    communes = parse_agvch((FIX / "agvch_sample.csv").read_text())
    by_id = {c.bfs_id: c for c in communes}
    assert by_id[230] == Commune(bfs_id=230, name="Winterthur", canton="ZH", district="Bezirk Winterthur", postal_codes=())
    assert by_id[3427].canton == "SG"
    assert len(communes) == 5


def test_parse_lindas_plz_groups_codes_by_bfs_id():
    plz = parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text())
    assert plz[230] == ("8400", "8404")
    assert plz[261] == ("8001",)


def test_merge_snapshot_attaches_postal_codes():
    communes = parse_agvch((FIX / "agvch_sample.csv").read_text())
    plz = parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text())
    merged = merge_snapshot(communes, plz)
    assert next(c for c in merged if c.bfs_id == 230).postal_codes == ("8400", "8404")


def test_register_csv_roundtrip(tmp_path: Path):
    communes = merge_snapshot(parse_agvch((FIX / "agvch_sample.csv").read_text()),
                              parse_lindas_plz((FIX / "lindas_plz_sample.csv").read_text()))
    path = tmp_path / "communes.csv"
    write_register_csv(path, communes)
    assert parse_register_csv(path.read_text()) == tuple(sorted(communes, key=lambda c: c.bfs_id))


def test_commune_locations_builds_nodes_under_canton_with_aliases():
    communes = (
        Commune(bfs_id=230, name="Winterthur", canton="ZH", district="Bezirk Winterthur", postal_codes=("8400", "8404")),
        Commune(bfs_id=3427, name="Wil (SG)", canton="SG", district="Wahlkreis Wil", postal_codes=("9500",)),
        Commune(bfs_id=34, name="Wil (ZH)", canton="ZH", district="Bezirk Winterthur", postal_codes=("8196",)),
        Commune(bfs_id=261, name="Zürich", canton="ZH", district="Bezirk Zürich", postal_codes=("8001",)),
    )
    nodes = commune_locations(communes, skip_bfs_ids={261})
    by_id = {n.id: n for n in nodes}
    w = by_id["CH-ZH-230"]
    assert w.parent_id == "CH-ZH" and w.level is Level.MUNICIPALITY and w.bfs_id == 230
    assert w.names == {"de": "Winterthur"}
    assert w.lindas_uri == "https://ld.admin.ch/municipality/230"
    assert set(w.aliases) == {"Gemeinde Winterthur", "Stadt Winterthur", "Winterthur ZH", "Winterthur (ZH)", "8400", "8404"}
    wil = by_id["CH-SG-3427"]
    assert wil.names == {"de": "Wil"}
    assert "Wil" in wil.all_names() and "Wil SG" in wil.aliases and "Wil (SG)" in wil.aliases
    assert "CH-ZH-261" not in by_id


def test_shared_postal_codes_are_not_aliases():
    communes = (
        Commune(bfs_id=1, name="A", canton="ZH", district="d", postal_codes=("8000",)),
        Commune(bfs_id=2, name="B", canton="ZH", district="d", postal_codes=("8000", "8001")),
    )
    nodes = {n.id: n for n in commune_locations(communes, skip_bfs_ids=set())}
    assert "8000" not in nodes["CH-ZH-1"].aliases and "8000" not in nodes["CH-ZH-2"].aliases
    assert "8001" in nodes["CH-ZH-2"].aliases
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/unit/locations/test_register.py -q` → ModuleNotFoundError.

- [ ] **Step 4: Write register.py**

```python
# src/swiss_grounding/locations/register.py
"""The commune register: every Swiss commune as a Location under its canton.

Read from the committed snapshot `data/communes.csv`; regenerate it with
`swiss-grounding locations fetch-register`. Pure: no network, no database."""
import csv
import io
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from swiss_grounding.locations.models import Level, Location

SNAPSHOT = Path(__file__).resolve().parent / "data" / "communes.csv"
COLUMNS = ("bfs_id", "name", "canton", "district", "postal_codes")
PLZ_SEPARATOR = "|"
CANTON_SUFFIX = re.compile(r"\s*\(([A-Z]{2})\)\s*$")
LINDAS_MUNICIPALITY = "https://ld.admin.ch/municipality/{bfs_id}"


@dataclass(frozen=True)
class Commune:
    bfs_id: int
    name: str            # as in the register, e.g. "Wil (SG)"
    canton: str          # two-letter abbreviation
    district: str
    postal_codes: tuple[str, ...]


def parse_register_csv(text: str) -> tuple[Commune, ...]:
    reader = csv.DictReader(io.StringIO(text))
    missing = set(COLUMNS) - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"register snapshot lacks columns {sorted(missing)}")
    communes = tuple(
        Commune(bfs_id=int(r["bfs_id"]), name=r["name"], canton=r["canton"], district=r["district"],
                postal_codes=tuple(p for p in r["postal_codes"].split(PLZ_SEPARATOR) if p))
        for r in reader
    )
    return tuple(sorted(communes, key=lambda c: c.bfs_id))


def write_register_csv(path: Path, communes: Iterable[Commune]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for c in sorted(communes, key=lambda c: c.bfs_id):
        writer.writerow({"bfs_id": c.bfs_id, "name": c.name, "canton": c.canton,
                         "district": c.district, "postal_codes": PLZ_SEPARATOR.join(c.postal_codes)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue())


def load_register(path: Path = SNAPSHOT) -> tuple[Commune, ...]:
    return parse_register_csv(path.read_text())


def _bare_name(name: str) -> str:
    return CANTON_SUFFIX.sub("", name).strip()


def _aliases(c: Commune, bare: str, unique_plz: frozenset[str]) -> tuple[str, ...]:
    marked = (f"Gemeinde {bare}", f"Stadt {bare}", f"{bare} {c.canton}", f"{bare} ({c.canton})")
    plz = tuple(p for p in c.postal_codes if p in unique_plz)
    return tuple(dict.fromkeys(marked + plz))


def commune_locations(communes: Sequence[Commune], skip_bfs_ids: set[int]) -> tuple[Location, ...]:
    """One Location per commune, id CH-<canton>-<bfs>, name without the canton suffix.

    A postal code becomes an alias only when exactly one commune carries it."""
    plz_counts = Counter(p for c in communes for p in c.postal_codes)
    unique_plz = frozenset(p for p, n in plz_counts.items() if n == 1)
    nodes = []
    for c in communes:
        if c.bfs_id in skip_bfs_ids:
            continue
        bare = _bare_name(c.name)
        nodes.append(Location(
            id=f"CH-{c.canton}-{c.bfs_id}", parent_id=f"CH-{c.canton}", level=Level.MUNICIPALITY,
            bfs_id=c.bfs_id, lindas_uri=LINDAS_MUNICIPALITY.format(bfs_id=c.bfs_id),
            names={"de": bare}, aliases=_aliases(c, bare, unique_plz),
        ))
    return tuple(nodes)
```

- [ ] **Step 5: Write register_fetch.py**

```python
# src/swiss_grounding/locations/register_fetch.py
"""Fetch the commune register from the BFS AGVCH API and postal codes from LINDAS.

Network only; the result is written to the committed snapshot by the CLI."""
import csv
import io
from collections.abc import Mapping, Sequence
from datetime import date

import httpx

from swiss_grounding.locations.register import Commune

AGVCH_URL = "https://www.agvchapp.bfs.admin.ch/api/communes/snapshot"
LINDAS_URL = "https://ld.admin.ch/query"
LINDAS_PLZ_QUERY = """
PREFIX schema: <http://schema.org/>
SELECT ?id ?postalCode WHERE {
  ?m a <https://schema.ld.admin.ch/PoliticalMunicipality> ; schema:identifier ?id ; schema:postalCode ?postalCode .
}
"""
LEVEL_CANTON, LEVEL_DISTRICT, LEVEL_COMMUNE = "1", "2", "3"
TIMEOUT = 60.0


def parse_agvch(text: str) -> tuple[Commune, ...]:
    """Communes from an AGVCH snapshot; canton found by walking Parent to the Level 1 row."""
    rows = list(csv.DictReader(io.StringIO(text)))
    by_hist = {r["HistoricalCode"]: r for r in rows}

    def canton_of(row: Mapping[str, str]) -> str:
        current = row
        while current["Level"] != LEVEL_CANTON:
            current = by_hist[current["Parent"]]
        return current["ShortName"]

    communes = []
    for r in rows:
        if r["Level"] != LEVEL_COMMUNE:
            continue
        district = by_hist[r["Parent"]]["Name"]
        communes.append(Commune(bfs_id=int(r["BfsCode"]), name=r["Name"], canton=canton_of(r),
                                district=district, postal_codes=()))
    return tuple(sorted(communes, key=lambda c: c.bfs_id))


def parse_lindas_plz(text: str) -> dict[int, tuple[str, ...]]:
    grouped: dict[int, list[str]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        grouped.setdefault(int(r["id"]), []).append(r["postalCode"])
    return {k: tuple(sorted(set(v))) for k, v in grouped.items()}


def merge_snapshot(communes: Sequence[Commune], plz: Mapping[int, tuple[str, ...]]) -> tuple[Commune, ...]:
    return tuple(Commune(c.bfs_id, c.name, c.canton, c.district, plz.get(c.bfs_id, ())) for c in communes)


def fetch_register(snapshot_date: date) -> tuple[Commune, ...]:
    with httpx.Client(timeout=TIMEOUT) as http:
        agvch = http.get(AGVCH_URL, params={"date": snapshot_date.strftime("%d-%m-%Y")})
        agvch.raise_for_status()
        lindas = http.post(LINDAS_URL, data={"query": LINDAS_PLZ_QUERY}, headers={"Accept": "text/csv"})
        lindas.raise_for_status()
    return merge_snapshot(parse_agvch(agvch.text), parse_lindas_plz(lindas.text))
```

- [ ] **Step 6: Run tests** → 6 passed. `uv run ruff check src tests`.

- [ ] **Step 7: Commit** `feat: commune register parser and fetcher`

---

## Task 2: Seed communes and the fetch-register CLI

**Files:**
- Modify: `src/swiss_grounding/locations/seed.py`
- Modify: `src/swiss_grounding/cli/main.py` (new `locations` sub-app)
- Create: `src/swiss_grounding/locations/data/communes.csv` (generated)
- Test: `tests/unit/test_location_seed.py` (extend), `tests/integration/test_register_seed.py`

- [ ] **Step 1: Failing tests**

Append to `tests/unit/test_location_seed.py`:
```python
def test_seed_includes_every_commune_under_its_canton():
    from swiss_grounding.locations.register import load_register
    from swiss_grounding.locations.seed import seed_locations
    locs = {l.id: l for l in seed_locations()}
    register = load_register()
    assert len(register) > 2000
    for c in register:
        if c.bfs_id == 261:
            assert locs["CH-ZH-261"].level.value == "municipality"
            continue
        node = locs[f"CH-{c.canton}-{c.bfs_id}"]
        assert node.parent_id == f"CH-{c.canton}"
    assert locs["CH-ZH-230"].names["de"] == "Winterthur"
    assert "8400" in locs["CH-ZH-230"].aliases


def test_seed_ids_are_unique_and_parents_exist():
    from swiss_grounding.locations.seed import seed_locations
    locs = seed_locations()
    ids = [l.id for l in locs]
    assert len(ids) == len(set(ids))
    known = set(ids)
    assert all(l.parent_id in known for l in locs if l.parent_id)
```
`tests/integration/test_register_seed.py`:
```python
import os
import pytest
from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.seed import seed_locations

pytestmark = pytest.mark.integration


def test_seeded_tree_resolves_winterthur_by_alias_and_postal_code():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        upsert_locations(conn, seed_locations())
        tree = load_tree(conn)
    assert tree.find("Winterthur")[0].id == "CH-ZH-230"
    assert tree.find("8400")[0].id == "CH-ZH-230"
    assert {n.id for n in tree.find("Wil")} == {"CH-ZH-34", "CH-SG-3427"} or len(tree.find("Wil")) >= 2
```
Note: verify Wil ZH's BFS number in the generated snapshot and fix the assertion to the real ids.

- [ ] **Step 2: Modify seed.py**

At the end of `seed_locations()`:
```python
from swiss_grounding.locations.register import commune_locations, load_register
...
    communes = commune_locations(load_register(), skip_bfs_ids={city.bfs_id})
    return (country,) + cantons + (city,) + tuple(kreise) + tuple(quartiere) + communes
```
Canton ids in `CANTONS` are abbreviations matching the register's `ShortName`; confirm all 26 line up (AGVCH uses "ZH", "BE", ... ; check "GE"/"VD"/"TI"/"VS"/"NE"/"JU"/"FR"/"GR"/"SG").

- [ ] **Step 3: Add the CLI**

In `main.py`:
```python
locations_app = typer.Typer(help="Location tree data.")
app.add_typer(locations_app, name="locations")


@locations_app.command("fetch-register")
def fetch_register_cmd(
    snapshot_date: str = typer.Option(None, "--date", help="ISO date, default today"),
    out: Path = typer.Option(SNAPSHOT, "--out"),
) -> None:
    """Regenerate the committed commune register snapshot from BFS and LINDAS."""
    from swiss_grounding.locations.register import write_register_csv
    from swiss_grounding.locations.register_fetch import fetch_register

    when = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    communes = fetch_register(when)
    write_register_csv(out, communes)
    typer.echo(f"wrote {len(communes)} communes to {out}")
```
Import `SNAPSHOT` from `swiss_grounding.locations.register`. Then run `uv run swiss-grounding locations fetch-register` and commit the generated `data/communes.csv` (expect ~2,100 rows). Ensure the `data/` directory is included in the wheel (hatch includes package data under `src/swiss_grounding` by default; verify with `uv build --wheel` or skip if not packaging).

- [ ] **Step 4: Seed the live database** with `uv run swiss-grounding db seed` (upsert; existing nodes unchanged).

- [ ] **Step 5: Run unit + integration + harness.** Expected: unit green; harness may now show XPASS(strict) for com-004, com-011 (postal code), com-013 and others whose only failure was resolution. For each XPASS, flip `status: green` in the YAML and check its `note` still describes the situation; if the note says "today resolves to the canton", rewrite it to state what now happens. Coverage probes (com-001/002/005/013) still fail on the missing signal; leave red.

- [ ] **Step 6: Commit** `feat: seed every Swiss commune from the register snapshot` (include the CSV and flipped probes).

---

## Task 3: Level markers, ambiguity, and common-word Quartiere in the resolver

**Files:**
- Create: `src/swiss_grounding/locations/markers.py`
- Modify: `src/swiss_grounding/locations/models.py` (AmbiguousLocation)
- Modify: `src/swiss_grounding/locations/resolver.py`
- Modify: `src/swiss_grounding/retrieval/query_core.py` (ambiguity → needs_location message)
- Modify: `src/swiss_grounding/mcp_server/server.py` (resolve tool returns candidates)
- Test: `tests/unit/locations/test_markers.py`, `tests/unit/test_resolver.py` (extend)

- [ ] **Step 1: Failing tests**

```python
# tests/unit/locations/test_markers.py
from swiss_grounding.locations.markers import strip_marker
from swiss_grounding.locations.models import Level


def test_strip_marker_recognises_german_and_english_markers():
    assert strip_marker("Gemeinde Winterthur") == (Level.MUNICIPALITY, "Winterthur")
    assert strip_marker("Stadt Zürich") == (Level.MUNICIPALITY, "Zürich")
    assert strip_marker("Kanton Zürich") == (Level.CANTON, "Zürich")
    assert strip_marker("Canton of Zurich") == (Level.CANTON, "Zurich")
    assert strip_marker("Quartier Hard") == (Level.NEIGHBORHOOD, "Hard")
    assert strip_marker("Kreis 3") == (Level.NEIGHBORHOOD, "Kreis 3")


def test_strip_marker_leaves_bare_names_alone():
    assert strip_marker("Winterthur") == (None, "Winterthur")
    assert strip_marker("Zürich, Switzerland") == (None, "Zürich, Switzerland")
```
Extend `tests/unit/test_resolver.py` (read the file first for its fixtures; add a tree containing CH, CH-ZH, CH-SG, CH-ZH-261, CH-ZH-34 "Wil", CH-SG-3427 "Wil", CH-ZH-261-K1, CH-ZH-261-K1-CITY "City", CH-ZH-261-K11, CH-ZH-261-K11-AFFOLTERN "Affoltern", CH-ZH-2 "Affoltern am Albis"):
```python
def test_bare_wil_is_ambiguous_across_cantons(resolver):
    result = resolver.resolve("Wil")
    assert isinstance(result, AmbiguousLocation)
    assert {c.id for c in result.candidates} == {"CH-ZH-34", "CH-SG-3427"}


def test_wil_with_canton_suffix_resolves(resolver):
    assert resolver.resolve("Wil ZH").location.id == "CH-ZH-34"


def test_bare_affoltern_is_ambiguous_between_quartier_and_commune(resolver):
    assert isinstance(resolver.resolve("Affoltern"), AmbiguousLocation)


def test_common_word_quartier_needs_a_marker(resolver):
    assert isinstance(resolver.resolve("City"), AmbiguousLocation)
    assert resolver.resolve("Quartier City").location.id == "CH-ZH-261-K1-CITY"


def test_marker_restricts_level(resolver):
    assert resolver.resolve("Kanton Zürich").location.id == "CH-ZH"
    assert resolver.resolve("Stadt Zürich").location.id == "CH-ZH-261"
    assert resolver.resolve("Gemeinde Zürich").location.id == "CH-ZH-261"


def test_city_and_canton_same_name_stays_most_specific(resolver):
    r = resolver.resolve("Zürich")
    assert r.location.id == "CH-ZH-261" and [a.id for a in r.alternatives] == ["CH-ZH"]
```

- [ ] **Step 2: markers.py**

```python
# src/swiss_grounding/locations/markers.py
"""Level markers fix which level a place name means: "Stadt Zürich" is marked, "Zürich" is bare."""
import re

from swiss_grounding.locations.models import Level

MARKERS: dict[str, Level] = {
    "kanton": Level.CANTON, "canton": Level.CANTON, "canton of": Level.CANTON, "cantone": Level.CANTON,
    "stadt": Level.MUNICIPALITY, "gemeinde": Level.MUNICIPALITY, "commune": Level.MUNICIPALITY,
    "comune": Level.MUNICIPALITY, "city of": Level.MUNICIPALITY, "municipality of": Level.MUNICIPALITY,
    "quartier": Level.NEIGHBORHOOD, "quartiere": Level.NEIGHBORHOOD,
}
KREIS = re.compile(r"^\s*kreis\s+\d{1,2}\s*$", re.IGNORECASE)
_PATTERN = re.compile(
    r"^\s*(" + "|".join(sorted(map(re.escape, MARKERS), key=len, reverse=True)) + r")\s+(.+?)\s*$",
    re.IGNORECASE,
)


def strip_marker(text: str) -> tuple[Level | None, str]:
    """(level named by a leading marker, remaining name). Kreis N keeps its marker: it is the name."""
    if KREIS.match(text):
        return Level.NEIGHBORHOOD, text.strip()
    m = _PATTERN.match(text)
    if not m:
        return None, text.strip()
    return MARKERS[m.group(1).lower()], m.group(2)
```

- [ ] **Step 3: models.py**

```python
@dataclass(frozen=True)
class AmbiguousLocation:
    """The input names more than one place that is not on a single path; ask, do not guess."""
    input_text: str
    candidates: tuple[Location, ...]
    reason: str
```

- [ ] **Step 4: resolver.py**

Replace `resolve` and add helpers (keep `overlaps`, `_tokens`, GeoAdmin fallback for now; Task 4 rewrites the GeoAdmin part):
```python
COMMON_WORD_NEIGHBORHOODS = frozenset({"city", "hard", "werd", "enge"})
Resolution = ResolvedLocation | AmbiguousLocation | None


def _on_one_path(tree: LocationTree, nodes: Sequence[Location]) -> bool:
    deepest = max(nodes, key=lambda n: len(tree.path(n.id)))
    path = tree.path(deepest.id)
    return all(n.id in path for n in nodes)


class LocationResolver:
    ...
    def resolve(self, text: str) -> Resolution:
        cleaned = text.strip()
        if not cleaned:
            return None
        level, name = strip_marker(cleaned)
        matches = self._tree.find(name)
        if level is not None:
            matches = tuple(m for m in matches if m.level is level)
        if matches:
            return self._from_alias_matches(cleaned, name, level, matches)
        scanned = resolve_from_question(self._tree, cleaned, prose=False)
        if scanned is not None:
            return replace(scanned, method=SCAN_METHOD, input_text=cleaned)
        return self._resolve_via_geoadmin(cleaned)

    def _from_alias_matches(self, cleaned: str, name: str, level: Level | None,
                            matches: tuple[Location, ...]) -> Resolution:
        if level is None and normalize(name) in COMMON_WORD_NEIGHBORHOODS \
                and all(m.level is Level.NEIGHBORHOOD for m in matches):
            return AmbiguousLocation(cleaned, matches, "a common word; say Quartier <name> to mean the district")
        if len(matches) > 1 and not _on_one_path(self._tree, matches):
            return AmbiguousLocation(cleaned, matches, "several places share this name")
        best = matches[0]
        return ResolvedLocation(location=best, path=self._tree.path(best.id), method="alias",
                                input_text=cleaned, alternatives=tuple(matches[1:]))
```
`tree.find` sorts most specific first, so a city/canton pair on one path keeps the city with the canton as alternative.

- [ ] **Step 5: query_core.py and server.py**

In `QueryCore.query`, after `resolved = self._resolve(request)`:
```python
        if isinstance(resolved, AmbiguousLocation):
            labels = ", ".join(f"{c.label('en')} ({c.id})" for c in resolved.candidates)
            return QueryResponse(status="needs_location",
                                 message=f"{resolved.input_text!r} is ambiguous ({resolved.reason}): {labels}. "
                                         "Ask the user which one they mean, then search again.")
```
In `swiss_resolve_location`, when `isinstance(resolved, AmbiguousLocation)` return `{"found": False, "ambiguous": True, "query": query, "candidates": [{"location_id", "label", "level", "path"}...], "message": ...}`. `swiss_coverage` treats ambiguous like unresolved.

- [ ] **Step 6: Run unit tests, ruff, harness.** Expected XPASS: city-012 (City), com-007 (Wil; check `message_contains: Wil` holds), com-009 (Affoltern), com-010 (Gemeinde Winterthur, method alias), city-015 (Quartier Hard), com-006 (Wil ZH: verify the alias "Wil ZH" exists from Task 1). Flip each to green with an updated note. Update `CANNED_GEOADMIN` in the harness only if a probe now reaches GeoAdmin with a new input (it will raise KeyError and tell you).

- [ ] **Step 7: Commit** `feat: level markers and ambiguity in the location resolver`

---

## Task 4: Strict GeoAdmin acceptance and typo tolerance

**Files:**
- Create: `src/swiss_grounding/locations/fuzzy.py`
- Modify: `src/swiss_grounding/locations/resolver.py`, `src/swiss_grounding/locations/question_scan.py` (prose flag)
- Test: `tests/unit/locations/test_fuzzy.py`, `tests/unit/test_resolver.py`, `tests/unit/test_resolve_from_question.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/locations/test_fuzzy.py
from swiss_grounding.locations.fuzzy import edit_distance, tokens_covered


def test_edit_distance():
    assert edit_distance("winterthur", "winterthurr") == 1
    assert edit_distance("zurich", "zurichsee") == 3


def test_tokens_covered_requires_every_input_token():
    assert tokens_covered("Winterthur", "Winterthur (ZH)")
    assert tokens_covered("Winterthurr", "Winterthur (ZH)")          # one edit on a long token
    assert not tokens_covered("Zürich Oberland", "Zürich (ZH)")      # oberland unaccounted for
    assert not tokens_covered("Zurich Airport", "Zürich (ZH)")
    assert not tokens_covered("Nowhere", "Nidwalden (NW)")
    assert not tokens_covered("Wil", "Wila (ZH)")                    # short tokens must match exactly
```
Resolver tests to add:
```python
def test_geoadmin_hit_needs_every_token_covered(resolver_with_geo):
    # geo stub: "Zürich Oberland" -> Zürich (ZH) 261 ; "Winterthurr" -> () ; "Zürichsee" -> Zürichsee (ZH) 0
    assert resolver_with_geo.resolve("Zürich Oberland").location.id == "CH-ZH"
    assert resolver_with_geo.resolve("Zürich Oberland").method == "geoadmin_approximate"
    assert resolver_with_geo.resolve("Zürichsee") is None


def test_single_token_typo_resolves_against_the_tree(resolver_with_geo):
    r = resolver_with_geo.resolve("Winterthurr")
    assert r.location.id == "CH-ZH-230" and r.method == "alias_fuzzy"


def test_trailing_country_name_keeps_the_most_specific(resolver_with_geo):
    r = resolver_with_geo.resolve("Zürich, Switzerland")
    assert r.location.id == "CH-ZH-261" and [a.id for a in r.alternatives] == ["CH-ZH"]
```

- [ ] **Step 2: fuzzy.py**

```python
# src/swiss_grounding/locations/fuzzy.py
"""Token-level tolerance for place names: a hit counts only when every input token is accounted for."""
from swiss_grounding.locations.tree import normalize

MIN_FUZZY_LENGTH = 6      # tokens shorter than this must match exactly
MAX_EDITS = 1
LABEL_PUNCTUATION = "()[],."


def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(t.strip(LABEL_PUNCTUATION) for t in normalize(text).split() if t.strip(LABEL_PUNCTUATION))


def token_matches(token: str, candidate: str) -> bool:
    if token == candidate:
        return True
    if len(token) < MIN_FUZZY_LENGTH:
        return False
    return edit_distance(token, candidate) <= MAX_EDITS


def tokens_covered(text: str, label: str) -> bool:
    """True when every token of text matches some token of label (exactly, or within one edit for long tokens)."""
    label_tokens = _tokens(label)
    return all(any(token_matches(t, c) for c in label_tokens) for t in _tokens(text))
```

- [ ] **Step 3: resolver.py GeoAdmin and fuzzy alias**

Replace `overlaps` usage:
```python
FUZZY_METHOD = "alias_fuzzy"

    def _resolve_via_geoadmin(self, text: str) -> Resolution:
        try:
            hits = self._geo.search_communes(text)
        except RuntimeError:
            return None
        if not hits:
            return self._resolve_fuzzy_alias(text)
        hit = hits[0]
        exact = self._tree.by_bfs_id(hit.bfs_id)
        if exact is not None and tokens_covered(text, hit.label):
            return ResolvedLocation(location=exact, path=self._tree.path(exact.id), method="geoadmin",
                                    input_text=text)
        canton_match = CANTON_IN_LABEL.search(hit.label)
        if canton_match and _shares_a_token(text, hit.label):
            canton = self._tree.find(canton_match.group(1))
            if canton:
                return ResolvedLocation(location=canton[0], path=self._tree.path(canton[0].id),
                                        method="geoadmin_approximate", input_text=text)
        return self._resolve_fuzzy_alias(text)

    def _resolve_fuzzy_alias(self, text: str) -> Resolution:
        """Single-token inputs within one edit of exactly one alias resolve to it."""
        key = normalize(text)
        if " " in key or len(key) < MIN_FUZZY_LENGTH:
            return None
        candidates = {node_id for alias, ids in self._tree.alias_index.items()
                      if " " not in alias and token_matches(key, alias) for node_id in ids}
        if len(candidates) != 1:
            return None
        node = self._tree.get(candidates.pop())
        return ResolvedLocation(location=node, path=self._tree.path(node.id), method=FUZZY_METHOD,
                                input_text=text)
```
`_shares_a_token(text, label)`: True when at least one input token of length ≥ 4 matches a label token exactly (keeps "Zürich Oberland" → canton approximate; rejects "Nowhere" vs "Nidwalden"). Remove `overlaps` and its tests if no longer used, or keep it as `_shares_a_token`.

- [ ] **Step 4: question_scan.py prose flag**

`resolve_from_question(tree, question, prose: bool = True)`; pass `prose` into `_keep` → `_accept_unigram`, and skip the `_is_sentence_initial` guard when `prose` is False. The resolver calls it with `prose=False`; QueryCore's question path keeps `prose=True`.

- [ ] **Step 5: Run tests, ruff, harness.** Expected XPASS: look-001, look-006 (now None → needs_location), look-010, com-012 (fuzzy), look-005 (Zurich Airport: tokens not covered → `_shares_a_token` true → canton approximate; the probe expects Kloten. Decide: keep the probe red with a note that the airport is a landmark, not a commune, and canton-approximate is the honest answer? No: the agreed rule says approximate to canton. Update look-005's expectation to `resolved: {id: CH-ZH}`, `method: geoadmin_approximate`, must_exclude CH-ZH-261, and flip green. Record the reasoning in its note.) look-007 Zurzach: GeoAdmin gives bfs 4324 which now exists in the tree → exact under CH-AG → XPASS, flip.

- [ ] **Step 6: Commit** `feat: strict GeoAdmin acceptance and single-edit typo tolerance`

---

## Task 5: Coverage signal on search results

**Files:**
- Create: `src/swiss_grounding/retrieval/coverage.py`
- Modify: `src/swiss_grounding/retrieval/models.py`, `query_core.py`, `mcp_server/server.py`
- Test: `tests/unit/test_coverage_models.py`, `tests/integration/test_coverage.py`

- [ ] **Step 1: Failing tests**

```python
# tests/integration/test_coverage.py  (setup as in test_probes_structural: corpus + FakeEmbedder)
def test_results_carry_one_coverage_row_per_extent_on_the_path(core):
    resp = core.query(QueryRequest(question="dog leash", location="Wiedikon", categories=("dogs",)))
    assert [r.extent_id for r in resp.coverage] == ["CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3", "CH-ZH-261-K3-ALT-WIEDIKON"]
    counts = {r.extent_id: r.documents for r in resp.coverage}
    assert counts["CH"] > 0 and counts["CH-ZH-261-K3-ALT-WIEDIKON"] == 0
    assert "no documents" in resp.resolution_note.lower()


def test_coverage_rows_survive_the_mcp_dict(core):
    from swiss_grounding.mcp_server.server import _response_to_dict
    resp = core.query(QueryRequest(question="dog leash", location="Zug"))
    data = _response_to_dict(resp, "concise")
    assert data["coverage"][0]["extent_id"] == "CH"
```

- [ ] **Step 2: models.py**

```python
@dataclass(frozen=True)
class CoverageRow:
    extent_id: str
    label: str
    documents: int


# on QueryResponse:
    coverage: tuple[CoverageRow, ...] = ()
    resolution_note: str = ""
```

- [ ] **Step 3: coverage.py**

```python
# src/swiss_grounding/retrieval/coverage.py
"""Document counts per extent on a path. Shared by swiss_search and swiss_coverage."""
from collections.abc import Sequence

import psycopg

from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import CoverageRow

COUNTS_SQL = """
select extent_id, count(*) as documents from document
where status = 'current' and extent_id = any(%(path)s) group by extent_id
"""


def coverage_rows(conn: psycopg.Connection, tree: LocationTree, path: Sequence[str]) -> tuple[CoverageRow, ...]:
    counts = {r["extent_id"]: r["documents"] for r in conn.execute(COUNTS_SQL, {"path": list(path)}).fetchall()}
    return tuple(CoverageRow(extent_id=e, label=tree.get(e).label("en"), documents=counts.get(e, 0)) for e in path)


def resolution_note(rows: Sequence[CoverageRow], method: str, alternatives: Sequence[str]) -> str:
    empty = [r.label for r in rows if r.documents == 0]
    parts = []
    if empty:
        parts.append("No documents indexed for " + ", ".join(empty) + "; evidence comes from parent jurisdictions.")
    if method == "geoadmin_approximate":
        parts.append("The place was not recognised below canton level; answered at canton level.")
    if alternatives:
        parts.append("Alternative reading: " + ", ".join(alternatives) + ".")
    return " ".join(parts)
```

- [ ] **Step 4: query_core.py** — inside the `with connect(...)` block also compute `rows = coverage_rows(conn, self.tree, resolved.path)`; set `coverage=rows` and `resolution_note=resolution_note(rows, resolved.method, [a.label("en") for a in resolved.alternatives])` on `base` (both `no_evidence` and `results`). `server.py`: `_response_to_dict` already uses `asdict`, so rows serialise; make `swiss_coverage` reuse `coverage_rows` for its per-extent counts where it fits, or leave the per-source breakdown and just share the SQL constant. Update the `swiss_search` docstring: "`coverage` lists, per jurisdiction on the path, how many documents are indexed; when the asked place has 0, say so in the answer."

- [ ] **Step 5: Run tests, harness.** Expected XPASS: city-002, city-006, city-008, com-001, com-002, com-005, com-013 and any other probe whose only remaining failure was the signal. Flip and update notes. `must_include: {source: stadt_zuerich, url_contains: karton}` on city-002 and `parks/hunde` on city-006 may still fail on ranking with the fake embedder; if so, those probes remain red until Task 7 and their notes say so.

- [ ] **Step 6: Commit** `feat: coverage signal and resolution note on search results (ADR 0001)`

---

## Task 6: Narrowing under ADR 0002 and re-narrowing stored documents

**Files:**
- Rewrite: `src/swiss_grounding/ingest/narrowing.py`
- Modify: `src/swiss_grounding/ingest/enrich.py` (pass title and headings)
- Create: `src/swiss_grounding/ingest/renarrow.py`
- Modify: `src/swiss_grounding/cli/main.py` (`ingest renarrow`)
- Test: `tests/unit/ingest/test_narrowing.py` (rewrite), `tests/integration/test_renarrow.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/ingest/test_narrowing.py (replace existing cases with these; keep the tree fixture style used there)
def test_bare_ancestor_name_in_body_never_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Hunde", headings=(), text="Im Kanton Zürich gilt ... Zürich ...")
    assert extent == "CH-ZH" and reason == "source_default"


def test_marker_in_body_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH", title="Hunde", headings=(), text="In der Stadt Zürich gilt Leinenpflicht.")
    assert extent == "CH-ZH-261" and reason.startswith("narrowed:marker:")


def test_bare_name_in_title_narrows(tree):
    extent, reason = narrow_extent(tree, "CH-ZH-261", title="Hundezone Wiedikon", headings=(), text="...")
    assert extent == "CH-ZH-261-K3-ALT-WIEDIKON" and reason.startswith("narrowed:title:")


def test_bare_name_in_heading_narrows(tree):
    extent, _ = narrow_extent(tree, "CH-ZH-261", title="Parks", headings=("Seefeld",), text="...")
    assert extent == "CH-ZH-261-K8-SEEFELD"


def test_common_word_quartier_needs_marker_even_in_title(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="City Guide", headings=(), text="")[0] == "CH-ZH-261"
    assert narrow_extent(tree, "CH-ZH-261", title="Quartier City", headings=(), text="")[0] == "CH-ZH-261-K1-CITY"


def test_postal_code_anywhere_narrows(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="Sammlung", headings=(), text="Für 8003 gilt ...")[0] == "CH-ZH-261-K3"


def test_two_mentions_narrow_to_common_ancestor(tree):
    extent, _ = narrow_extent(tree, "CH-ZH-261", title="Wiedikon und Seefeld", headings=(), text="")
    assert extent == "CH-ZH-261"


def test_never_widens_or_moves_sideways(tree):
    assert narrow_extent(tree, "CH-ZH-261", title="Kanton Zürich", headings=(), text="")[0] == "CH-ZH-261"
    assert narrow_extent(tree, "CH-ZH", title="Stadt Bern", headings=(), text="")[0] == "CH-ZH"
```
Integration:
```python
# tests/integration/test_renarrow.py: load zurich_hiking.json fixture, set the zh_ch document's extent to CH-ZH-261 by SQL to simulate the defect, run renarrow_all(conn, tree), assert the document and its chunks are back at CH-ZH with reason 'source_default', and that the report counts moved=1.
```

- [ ] **Step 2: narrowing.py**

```python
"""Extent narrowing under ADR 0002: only a level marker, a postal code, or a bare name in the
title or a heading may narrow; a name shared with an ancestor of the default extent never
narrows on its own; common-word Quartier names always need a marker."""
import re
from collections.abc import Sequence

from swiss_grounding.locations.markers import MARKERS
from swiss_grounding.locations.models import LEVEL_DEPTH, Level
from swiss_grounding.locations.tree import LocationTree, normalize

SOURCE_DEFAULT = "source_default"
COMMON_WORD_NEIGHBORHOODS = frozenset({"city", "hard", "werd", "enge"})
PLZ = re.compile(r"(?<!\d)(\d{4})(?!\d)")
WORD = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]*"
MARKED = re.compile(r"\b(" + "|".join(map(re.escape, MARKERS)) + r")\s+(" + WORD + r"(?:\s+" + WORD + r"){0,2})",
                    re.IGNORECASE)
KREIS = re.compile(r"\bKreis\s+(\d{1,2})\b", re.IGNORECASE)
MAX_NGRAM = 3


def _names(tree: LocationTree) -> dict[str, str]:
    names: dict[str, str] = {}
    for loc in sorted(tree.all(), key=lambda l: LEVEL_DEPTH[l.level]):
        for name in loc.all_names():
            names[normalize(name)] = loc.id
    return names


def _ngrams(text: str) -> list[str]:
    words = re.findall(WORD, text)
    return [" ".join(words[i:i + n]) for n in range(MAX_NGRAM, 0, -1) for i in range(len(words) - n + 1)]


def _marker_mentions(tree, names, text) -> list[tuple[str, str]]:
    found = []
    for m in MARKED.finditer(text):
        level = MARKERS[m.group(1).lower()]
        for gram in _ngrams(m.group(2)):
            node_id = names.get(normalize(gram))
            if node_id and tree.get(node_id).level is level:
                found.append((node_id, f"marker:{m.group(1)} {gram}"))
                break
    for m in KREIS.finditer(text):
        node_id = names.get(normalize(f"Kreis {m.group(1)}"))
        if node_id:
            found.append((node_id, f"marker:Kreis {m.group(1)}"))
    for m in PLZ.finditer(text):
        node_id = names.get(m.group(1))
        if node_id:
            found.append((node_id, f"plz:{m.group(1)}"))
    return found


def _bare_mentions(tree, names, text, where, ancestors) -> list[tuple[str, str]]:
    found = []
    for gram in _ngrams(text):
        key = normalize(gram)
        node_id = names.get(key)
        if not node_id or node_id in ancestors:
            continue
        node = tree.get(node_id)
        if node.level is Level.NEIGHBORHOOD and key in COMMON_WORD_NEIGHBORHOODS:
            continue
        if any(normalize(n) == key for a in ancestors for n in tree.get(a).all_names()):
            continue
        found.append((node_id, f"{where}:{gram}"))
    return found


def _deepest_common_ancestor(tree, ids):
    paths = [tree.path(i) for i in ids]
    common = paths[0]
    for p in paths[1:]:
        common = tuple(a for a, b in zip(common, p) if a == b)
    return common[-1]


def narrow_extent(tree: LocationTree, default_extent_id: str, title: str, headings: Sequence[str],
                  text: str) -> tuple[str, str]:
    """Narrow to a descendant of the default extent; never widen, never move sideways."""
    names = _names(tree)
    ancestors = set(tree.path(default_extent_id))
    mentions = _marker_mentions(tree, names, " ".join((title, *headings, text)))
    mentions += _bare_mentions(tree, names, title, "title", ancestors)
    for h in headings:
        mentions += _bare_mentions(tree, names, h, "heading", ancestors)
    below = [(n, why) for n, why in mentions if default_extent_id in tree.path(n) and n != default_extent_id]
    if not below:
        return default_extent_id, SOURCE_DEFAULT
    target = _deepest_common_ancestor(tree, tuple(dict.fromkeys(n for n, _ in below)))
    if target == default_extent_id:
        return default_extent_id, SOURCE_DEFAULT
    return target, "narrowed:" + ",".join(dict.fromkeys(why for _, why in below))
```
`enrich.py`: call `narrow_extent(tree, source.default_extent_id, title=title_en, headings=tuple(s.heading_path for s in sections_en), text=text_en)`. Fix any existing tests that call the old signature.

- [ ] **Step 3: renarrow.py and CLI**

```python
# src/swiss_grounding/ingest/renarrow.py
"""Re-run narrowing over stored documents using their stored English text. No API calls."""
from dataclasses import dataclass

import psycopg

from swiss_grounding.ingest.narrowing import narrow_extent
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.registry.repository import load_sources

SELECT = """
select d.id, d.source_id, d.title_en, d.extent_id,
       array_agg(c.heading_path order by c.ordinal) as headings,
       string_agg(c.text_en, ' ' order by c.ordinal) as text_en
from document d join chunk c on c.document_id = d.id
where d.status = 'current' group by d.id
"""
UPDATE_DOC = "update document set extent_id = %s, extent_reason = %s where id = %s"
UPDATE_CHUNKS = "update chunk set extent_id = %s where document_id = %s"


@dataclass(frozen=True)
class RenarrowReport:
    examined: int
    moved: int


def renarrow_all(conn: psycopg.Connection, tree: LocationTree) -> RenarrowReport:
    sources = {s.id: s for s in load_sources(conn)}
    examined = moved = 0
    for row in conn.execute(SELECT).fetchall():
        examined += 1
        source = sources[row["source_id"]]
        if not source.allow_narrowing:
            target, reason = source.default_extent_id, "source_default"
        else:
            target, reason = narrow_extent(tree, source.default_extent_id, row["title_en"],
                                           tuple(h for h in row["headings"] if h), row["text_en"] or "")
        if target != row["extent_id"]:
            conn.execute(UPDATE_DOC, (target, reason, row["id"]))
            conn.execute(UPDATE_CHUNKS, (target, row["id"]))
            moved += 1
    return RenarrowReport(examined=examined, moved=moved)
```
CLI: `ingest_app`? There is a top-level `ingest` command; add a `renarrow` command under a new `ingest_app` only if `ingest` is not already a sub-app. Otherwise add top-level `renarrow`. It loads the tree, runs `renarrow_all`, prints the report. Check `load_sources` exists in `registry/repository.py` with that name and return shape (Source has `allow_narrowing`, `default_extent_id`).

- [ ] **Step 4: Run tests, run `uv run swiss-grounding renarrow` on the live database**, check `swiss_coverage` for `Kanton Zürich` now lists zh_ch at `CH-ZH` and the "City" Quartier is empty. Then move the two zh_ch fixture documents back to `CH-ZH` in `tests/fixtures/probe_corpus.json`, update `test_probe_corpus.py` (extents include CH-ZH, docstring first bullet removed), run harness; expected XPASS: city-017, com-014, com-006, com-001 etc. Flip and update notes.

- [ ] **Step 5: Commit** `feat: narrowing under ADR 0002 and a renarrow command; canton pages back at canton level`

---

## Task 7: Calendar ordering and as_of as the clock

**Files:**
- Modify: `src/swiss_grounding/retrieval/rerank.py`, `query_core.py`
- Test: `tests/unit/test_rerank.py`, `tests/unit/test_query_core_clock.py`

- [ ] **Step 1: Failing tests**

```python
def test_nearest_future_event_outranks_later_ones():
    # three identical hits differing only in event_date: 09-17, 09-29, 12-31, today 09-16 → order 17, 29, 31
def test_past_event_sinks_below_all_future_events():
    # 09-10 must come after every future event, but still be present
def test_as_of_replaces_today_in_query_core(monkeypatch):
    # as_of 2026-09-08 → 09-10 is future and nearest → ranks first (monkeypatch rerank to capture today)
```

- [ ] **Step 2: rerank.py**

```python
PAST_EVENT_PENALTY = 0.5
NEARNESS_BONUS = 0.5      # added to the factor for an event today, decaying with days ahead
NEARNESS_HALF_LIFE_DAYS = 14.0


def event_recency_factor(event_date: date | None, today: date) -> float:
    """1.0 for non-events; past events halved; future events boosted the nearer they are."""
    if event_date is None:
        return 1.0
    days = (event_date - today).days
    if days < 0:
        return PAST_EVENT_PENALTY
    return 1.0 + NEARNESS_BONUS / (1.0 + days / NEARNESS_HALF_LIFE_DAYS)
```
Verify on the live corpus that 17 Sep now outranks 3 Dec for "next cardboard collection" in 8003 with limit 8 (all cardboard events share the same base score, so the factor decides; if the lexical leg separates them, tune `NEARNESS_BONUS` upward, and note the value in the commit).

- [ ] **Step 3: query_core.py** — `today = request.as_of or self.today()`; pass `today=lambda: today` to rerank.

- [ ] **Step 4: Run tests, harness (city-001, city-018 should XPASS; city-004 stays green), flip, commit** `feat: rank calendar evidence nearest-future first; as_of drives the clock`

---

## Task 8: Re-record, reconcile, and document

**Files:** `evals/probes/*.yaml`, `tests/fixtures/probe_corpus.json`, `tests/integration/test_probe_corpus.py`, `tests/integration/test_probes_structural.py` (canned hits for new inputs), `CONTEXT.md`, `docs/adr/0002...` (consequences: done), README.

- [ ] **Step 1:** `uv run swiss-grounding db seed && uv run swiss-grounding renarrow` (idempotent), then `uv run swiss-grounding eval probes --record`. Reconcile status mismatches exactly as in the red-set plan: red passing → green with an updated note; green failing → investigate; never edit code in this step except to fix a real regression found this way (then loop back to the owning task).
- [ ] **Step 2:** Harness: `uv run pytest tests/integration -q -rxX` must show 0 failed and 0 XPASS; unit and ruff green.
- [ ] **Step 3:** `CONTEXT.md`: commune register entry drops "Not yet seeded"; add **Ambiguous location** term. README: mention `locations fetch-register` and `renarrow`. Memory note update is the controller's job.
- [ ] **Step 4:** Expected end state: only city-003 (no past events ingested) and city-020 (SR 704 not in registry) remain red, both marked as blocked on credits in their notes. Any other remaining red gets a note naming the task that should have fixed it and why it did not.
- [ ] **Step 5:** Optional if usage allows: `uv run swiss-grounding eval judge` for a post-fix baseline; commit results.
- [ ] **Step 6:** Commit `docs: record the live run after the fix pass; probes flipped green`

---

## Self-review notes

- **Spec coverage.** Every fix-order item from the report has a task: register (1, 2), ambiguity + markers (3), GeoAdmin + typo (4), coverage signal (5), re-narrow (6), calendar + as_of (7). The fixture reverts and the flip protocol are in 6 and 8.
- **Placeholder scan.** Task 7's tests and Task 6's integration test are described rather than written verbatim; the implementer writes them following the patterns in `tests/unit/test_rerank.py` and `tests/integration/test_pipeline.py`. Everything else is complete code.
- **Type consistency.** `narrow_extent(tree, default, title, headings, text)` is the one signature change; `enrich.py` and `renarrow.py` both use it. `Resolution` is the union returned by `LocationResolver.resolve`; `QueryCore._resolve` and `swiss_resolve_location` handle `AmbiguousLocation`. `CoverageRow(extent_id, label, documents)` matches the checker's `{extent_id, documents}` reader.
- **Unknowns to verify early.** Wil ZH's BFS number (test in Task 2); whether the canton `ShortName` in AGVCH equals the seed abbreviations for all 26; that `load_sources` exists with that name; whether `ingest` is a sub-app or a command in `cli/main.py`.
