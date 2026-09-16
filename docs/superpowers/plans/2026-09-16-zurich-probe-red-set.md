# Zurich Probe Red Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hand-written, adversarial probe suite for canton Zurich that records, per probe, what the MCP server should return and what it returns today, so the later fix pass has a red baseline to turn green.

**Architecture:** Probes are YAML files under `evals/probes/`, one per location tier. A pure checker compares a `QueryResponse` against a probe's expectation and returns named failures. Structural probes run under pytest on a fixture corpus with a frozen clock; ranking probes run through a CLI command against the live database and write results to an `eval_run` table. A judge harness drives Claude Code headless per answering model and grades with a fixed Fable judge. This plan is collect-only: no retrieval, resolver, or narrowing behaviour is changed. Probes that fail today are marked `status: red` and run as strict expected failures so CI stays green until the fix pass flips them.

**Tech Stack:** Python 3.12, pydantic 2, PyYAML, pytest, typer, psycopg 3, PostgreSQL 16 with pgvector, Claude Code CLI (`claude -p`) for judge cases.

**Decisions this plan implements** (see `CONTEXT.md`, `docs/adr/0001`, `docs/adr/0002`):

- Five failure classes: jurisdiction confusion, authority-hierarchy violation, temporal misapplication, entity substitution, silent under-coverage.
- Expected coverage signal on `results`: a `coverage` field listing, per extent on the resolved path, the number of documents indexed there. This field does not exist yet; probes that need it are red.
- Full commune register expected in the tree; commune probes expect resolution to a municipality node whose parent is `CH-ZH`. Not seeded yet; those probes are red.
- Calendar evidence: nearest future event first, past events sink. Probes use the relative rule `first_event: nearest_future` so they hold on any date.
- Evidence is named by source id, URL fragment, or extent, never by database id.
- Probe counts: 20 in-city, 15 canton communes, 12 lookalikes. 15 marked `judge: true`.

**Frozen clock for structural runs:** `2026-09-16`.

---

## File Structure

```
evals/
  probes/
    city.yaml                 tier 1: Kreise, Quartiere, postal codes
    communes.yaml             tier 2: canton communes outside the city
    lookalikes.yaml           tier 3: bordering and lookalike names
  judge/
    mcp.json                  MCP config handing claude -p the server
    rubric.md                 judge prompt template
src/swiss_grounding/evals/
  __init__.py
  probe_models.py             pydantic models for a probe file
  probe_loader.py             read and validate YAML probe files
  checker.py                  pure: (Probe, QueryResponse, today) -> failures
  runner.py                   run probes through a QueryCore, build ProbeResult
  recorder.py                 write observed blocks back into YAML
  eval_run_repository.py      insert ProbeResult rows into eval_run
  judge_harness.py            drive claude -p per model, grade with Fable
src/swiss_grounding/cli/eval_commands.py   `swiss-grounding eval probes`, `eval judge`
src/swiss_grounding/db/schema.sql          + eval_run table
src/swiss_grounding/retrieval/query_core.py  + injectable today
tests/fixtures/probe_corpus.json           structural corpus
tests/unit/evals/
  test_probe_models.py
  test_probe_loader.py
  test_checker.py
  test_recorder.py
  test_judge_harness.py
tests/integration/
  test_probes_structural.py   parametrised over structural probes
  test_eval_run_repository.py
```

---

## Task 1: Probe models

**Files:**
- Create: `src/swiss_grounding/evals/__init__.py` (empty)
- Create: `src/swiss_grounding/evals/probe_models.py`
- Test: `tests/unit/evals/__init__.py` (empty), `tests/unit/evals/test_probe_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_probe_models.py
import pytest
from pydantic import ValidationError

from swiss_grounding.evals.probe_models import (
    EvidenceRule, Expectation, Probe, ProbeFile, ResolvedExpectation,
)


def _probe(**overrides) -> dict:
    base = {
        "id": "city-001",
        "question": "When is the next cardboard collection?",
        "location": "8004",
        "categories": ["waste"],
        "kind": "structural",
        "failure_class": "silent_under_coverage",
        "status": "red",
        "expect": {
            "status": "results",
            "resolved": {"id": "CH-ZH-261-K4"},
            "must_exclude": [{"source": "open_erz"}],
            "coverage_empty": ["CH-ZH-261-K4"],
        },
    }
    return {**base, **overrides}


def test_probe_file_parses_minimal_probe():
    pf = ProbeFile.model_validate({"tier": "city", "probes": [_probe()]})
    probe = pf.probes[0]
    assert probe.id == "city-001"
    assert probe.limit == 8
    assert probe.judge is False
    assert probe.expect.resolved == ResolvedExpectation(id="CH-ZH-261-K4")
    assert probe.expect.must_exclude == (EvidenceRule(source="open_erz"),)


def test_evidence_rule_needs_at_least_one_selector():
    with pytest.raises(ValidationError):
        EvidenceRule()


def test_resolved_expectation_by_label_and_level():
    r = ResolvedExpectation(label="Winterthur", level="municipality", parent="CH-ZH")
    assert r.id is None


def test_unknown_failure_class_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(failure_class="vibes")]})


def test_duplicate_probe_ids_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(), _probe()]})


def test_extra_keys_rejected():
    with pytest.raises(ValidationError):
        ProbeFile.model_validate({"tier": "city", "probes": [_probe(surprise=1)]})


def test_expectation_defaults_are_empty():
    e = Expectation(status="results")
    assert e.must_include == ()
    assert e.coverage_empty == ()
    assert e.first_event is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_probe_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swiss_grounding.evals'`

- [ ] **Step 3: Write the models**

```python
# src/swiss_grounding/evals/probe_models.py
"""Shape of a probe file. A probe states what the server should return and, once recorded,
what it returned. Evidence is named by source, URL fragment, or extent, never by database id."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

FailureClass = Literal[
    "jurisdiction_confusion",
    "authority_hierarchy",
    "temporal_misapplication",
    "entity_substitution",
    "silent_under_coverage",
    "none",
]
ProbeKind = Literal["structural", "ranking"]
ProbeStatus = Literal["red", "green"]
Tier = Literal["city", "communes", "lookalikes"]
ResponseStatus = Literal["results", "needs_location", "no_evidence", "invalid_request"]
FirstEventRule = Literal["nearest_future"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRule(_Strict):
    """Selects citations. All given selectors must match one citation for the rule to hit."""
    source: str | None = None
    url_contains: str | None = None
    extent: str | None = None          # an extent id, or "off_path" for any extent not on the resolved path
    authority: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "EvidenceRule":
        if not any((self.source, self.url_contains, self.extent, self.authority)):
            raise ValueError("an evidence rule needs at least one selector")
        return self


class ResolvedExpectation(_Strict):
    """Either an exact node id, or a label plus level plus parent for nodes that do not exist yet."""
    id: str | None = None
    label: str | None = None
    level: str | None = None
    parent: str | None = None

    @model_validator(mode="after")
    def _id_or_label(self) -> "ResolvedExpectation":
        if self.id is None and self.label is None:
            raise ValueError("resolved expectation needs id or label")
        return self


class Expectation(_Strict):
    status: ResponseStatus
    resolved: ResolvedExpectation | None = None
    method: str | None = None
    alternatives_include: tuple[str, ...] = ()
    must_include: tuple[EvidenceRule, ...] = ()
    must_exclude: tuple[EvidenceRule, ...] = ()
    first_extent: str | None = None
    first_authority: str | None = None
    first_url_contains: str | None = None
    first_event: FirstEventRule | None = None
    coverage_empty: tuple[str, ...] = ()
    coverage_present: tuple[str, ...] = ()
    message_contains: str | None = None


class ObservedCitation(_Strict):
    source: str
    extent: str
    url: str
    authority: str
    event_date: date | None = None


class Observed(_Strict):
    recorded_at: datetime
    git_commit: str | None = None
    status: str
    resolved_id: str | None = None
    method: str | None = None
    alternatives: tuple[str, ...] = ()
    message: str = ""
    citations: tuple[ObservedCitation, ...] = ()
    failures: tuple[str, ...] = ()


class Probe(_Strict):
    id: str
    question: str
    location: str | None = None
    categories: tuple[str, ...] = ()
    as_of: date | None = None
    limit: int = 8
    kind: ProbeKind
    failure_class: FailureClass
    status: ProbeStatus
    judge: bool = False
    note: str = ""
    expect: Expectation
    observed: Observed | None = None


class ProbeFile(_Strict):
    tier: Tier
    probes: tuple[Probe, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> "ProbeFile":
        ids = [p.id for p in self.probes]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate probe ids: {dupes}")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_probe_models.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/__init__.py src/swiss_grounding/evals/probe_models.py tests/unit/evals/
git commit -m "feat: probe file models for the eval red set"
```

---

## Task 2: Probe loader

**Files:**
- Create: `src/swiss_grounding/evals/probe_loader.py`
- Test: `tests/unit/evals/test_probe_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_probe_loader.py
from pathlib import Path

import pytest

from swiss_grounding.evals.probe_loader import PROBE_DIR, load_probe_file, load_all_probes

MINIMAL = """
tier: city
probes:
  - id: city-001
    question: When is the next cardboard collection?
    location: "8004"
    categories: [waste]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    expect:
      status: results
      resolved: {id: CH-ZH-261-K4}
      must_exclude:
        - {source: open_erz}
      coverage_empty: [CH-ZH-261-K4]
"""


def test_load_probe_file(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(MINIMAL)
    pf = load_probe_file(path)
    assert pf.tier == "city"
    assert pf.probes[0].location == "8004"


def test_load_all_probes_reads_every_yaml_in_dir(tmp_path: Path):
    (tmp_path / "city.yaml").write_text(MINIMAL)
    (tmp_path / "communes.yaml").write_text(MINIMAL.replace("tier: city", "tier: communes").replace("city-001", "com-001"))
    probes = load_all_probes(tmp_path)
    assert sorted(p.id for _, p in probes) == ["city-001", "com-001"]
    assert {t for t, _ in probes} == {"city", "communes"}


def test_load_all_probes_rejects_ids_duplicated_across_files(tmp_path: Path):
    (tmp_path / "a.yaml").write_text(MINIMAL)
    (tmp_path / "b.yaml").write_text(MINIMAL.replace("tier: city", "tier: communes"))
    with pytest.raises(ValueError, match="city-001"):
        load_all_probes(tmp_path)


def test_default_probe_dir_is_repo_evals_probes():
    assert PROBE_DIR.name == "probes"
    assert PROBE_DIR.parent.name == "evals"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_probe_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the loader**

```python
# src/swiss_grounding/evals/probe_loader.py
from pathlib import Path

import yaml

from swiss_grounding.evals.probe_models import Probe, ProbeFile, Tier

PROBE_DIR = Path(__file__).resolve().parents[3] / "evals" / "probes"


def load_probe_file(path: Path) -> ProbeFile:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return ProbeFile.model_validate(raw)


def load_all_probes(directory: Path = PROBE_DIR) -> tuple[tuple[Tier, Probe], ...]:
    """Every probe in every YAML file, paired with its tier. Ids must be unique across files."""
    pairs: list[tuple[Tier, Probe]] = []
    for path in sorted(directory.glob("*.yaml")):
        pf = load_probe_file(path)
        pairs.extend((pf.tier, p) for p in pf.probes)
    ids = [p.id for _, p in pairs]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"probe ids duplicated across files: {dupes}")
    return tuple(pairs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_probe_loader.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/probe_loader.py tests/unit/evals/test_probe_loader.py
git commit -m "feat: load probe YAML files"
```

---

## Task 3: Checker

The checker is pure. It never touches the database. It reads an optional `coverage` attribute off the response with `getattr`, because that field is a fix-pass addition; its absence is itself a failure when a probe expects it.

**Files:**
- Create: `src/swiss_grounding/evals/checker.py`
- Test: `tests/unit/evals/test_checker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_checker.py
from datetime import date, datetime, timezone

from swiss_grounding.evals.checker import check
from swiss_grounding.evals.probe_models import EvidenceRule, Expectation, Probe, ResolvedExpectation
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryResponse

TODAY = date(2026, 9, 16)


def _tree() -> LocationTree:
    return LocationTree.from_locations([
        Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None, lindas_uri=None, names={"en": "Switzerland"}, aliases=()),
        Location(id="CH-ZH", parent_id="CH", level=Level.CANTON, bfs_id=1, lindas_uri=None, names={"en": "Zurich"}, aliases=()),
        Location(id="CH-ZH-261", parent_id="CH-ZH", level=Level.MUNICIPALITY, bfs_id=261, lindas_uri=None, names={"en": "Zurich"}, aliases=()),
        Location(id="CH-ZH-261-K3", parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None, lindas_uri=None, names={"en": "District 3"}, aliases=()),
        Location(id="CH-ZH-261-K4", parent_id="CH-ZH-261", level=Level.NEIGHBORHOOD, bfs_id=None, lindas_uri=None, names={"en": "District 4"}, aliases=()),
    ])


def _cit(source="fedlex", extent="CH", url="https://www.fedlex.admin.ch/eli/cc/2008/414/de",
         authority="federal_law", event_date=None) -> Citation:
    return Citation(
        chunk_id=1, document_id=1, source_id=source, title_en="t", title_original="t", url=url,
        anchor=None, identifier=None, snippet_en="s", snippet_original="s", language="de",
        heading_path="", extent_id=extent, extent_label=extent, authority=authority,
        categories=("dogs",), valid_from=None, retrieved_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
        license=None, score=1.0, event_date=event_date,
    )


def _probe(**expect) -> Probe:
    return Probe(
        id="x", question="q", location="8004", kind="structural", failure_class="none",
        status="green", expect=Expectation(**expect),
    )


def _resp(**overrides) -> QueryResponse:
    base = dict(status="results", resolved_location_id="CH-ZH-261-K4",
                resolution_method="alias", citations=(_cit(),))
    return QueryResponse(**{**base, **overrides})


def test_passes_when_everything_matches():
    probe = _probe(status="results", resolved=ResolvedExpectation(id="CH-ZH-261-K4"),
                   must_include=(EvidenceRule(source="fedlex"),))
    assert check(probe, _resp(), _tree(), TODAY) == ()


def test_status_mismatch():
    probe = _probe(status="needs_location")
    assert check(probe, _resp(), _tree(), TODAY) == ("status: expected needs_location, got results",)


def test_resolved_id_mismatch():
    probe = _probe(status="results", resolved=ResolvedExpectation(id="CH-ZH-261-K3"))
    assert "resolved: expected CH-ZH-261-K3, got CH-ZH-261-K4" in check(probe, _resp(), _tree(), TODAY)


def test_resolved_by_label_level_parent_uses_tree():
    probe = _probe(status="results", resolved=ResolvedExpectation(label="District 4", level="neighborhood", parent="CH-ZH-261"))
    assert check(probe, _resp(), _tree(), TODAY) == ()
    wrong = _probe(status="results", resolved=ResolvedExpectation(label="Winterthur", level="municipality", parent="CH-ZH"))
    failures = check(wrong, _resp(), _tree(), TODAY)
    assert any(f.startswith("resolved: expected Winterthur (municipality under CH-ZH)") for f in failures)


def test_method_and_alternatives():
    probe = _probe(status="results", method="geoadmin", alternatives_include=("CH-ZH",))
    failures = check(probe, _resp(), _tree(), TODAY)
    assert "method: expected geoadmin, got alias" in failures
    assert "alternatives: CH-ZH missing from ()" in failures


def test_must_include_reports_missing_rule():
    probe = _probe(status="results", must_include=(EvidenceRule(source="zh_ch", url_contains="hunde"),))
    assert check(probe, _resp(), _tree(), TODAY) == ("must_include: no citation matched source=zh_ch url_contains=hunde",)


def test_must_exclude_reports_matching_citation():
    probe = _probe(status="results", must_exclude=(EvidenceRule(source="fedlex"),))
    assert check(probe, _resp(), _tree(), TODAY) == ("must_exclude: citation matched source=fedlex (https://www.fedlex.admin.ch/eli/cc/2008/414/de)",)


def test_off_path_extent_rule():
    probe = _probe(status="results", must_exclude=(EvidenceRule(extent="off_path"),))
    leak = _resp(citations=(_cit(source="open_erz", extent="CH-ZH-261-K3", url="https://openerz.metaodi.ch/x"),))
    assert check(probe, leak, _tree(), TODAY) == ("must_exclude: citation matched extent=off_path (https://openerz.metaodi.ch/x)",)
    assert check(probe, _resp(), _tree(), TODAY) == ()


def test_first_extent_authority_url():
    probe = _probe(status="results", first_extent="CH-ZH", first_authority="official_info", first_url_contains="zh.ch")
    failures = check(probe, _resp(), _tree(), TODAY)
    assert "first_extent: expected CH-ZH, got CH" in failures
    assert "first_authority: expected official_info, got federal_law" in failures
    assert "first_url_contains: 'zh.ch' not in https://www.fedlex.admin.ch/eli/cc/2008/414/de" in failures


def test_first_event_nearest_future():
    probe = _probe(status="results", first_event="nearest_future")
    good = _resp(citations=(
        _cit(source="open_erz", event_date=date(2026, 9, 17)),
        _cit(source="open_erz", event_date=date(2026, 12, 31)),
    ))
    assert check(probe, good, _tree(), TODAY) == ()
    bad = _resp(citations=(
        _cit(source="open_erz", event_date=date(2026, 12, 31)),
        _cit(source="open_erz", event_date=date(2026, 9, 17)),
    ))
    assert check(probe, bad, _tree(), TODAY) == ("first_event: expected nearest future 2026-09-17, first citation has 2026-12-31",)
    past = _resp(citations=(_cit(source="open_erz", event_date=date(2026, 9, 10)),))
    assert check(probe, past, _tree(), TODAY) == ("first_event: first citation 2026-09-10 is before today 2026-09-16",)


def test_coverage_signal_missing_is_a_failure():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",), coverage_present=("CH",))
    assert check(probe, _resp(), _tree(), TODAY) == ("coverage: response carries no coverage signal",)


def test_coverage_signal_checked_when_present():
    probe = _probe(status="results", coverage_empty=("CH-ZH-261-K4",), coverage_present=("CH",))

    class WithCoverage(QueryResponse):
        pass

    resp = WithCoverage(status="results", resolved_location_id="CH-ZH-261-K4", citations=(_cit(),))
    object.__setattr__(resp, "coverage", ({"extent_id": "CH", "documents": 3}, {"extent_id": "CH-ZH-261-K4", "documents": 2}))
    assert check(probe, resp, _tree(), TODAY) == ("coverage: expected CH-ZH-261-K4 empty, has 2 documents",)


def test_message_contains():
    probe = _probe(status="needs_location", message_contains="Atlantis")
    resp = QueryResponse(status="needs_location", message="Could not resolve location 'Nowhere'.")
    assert check(probe, resp, _tree(), TODAY) == ("message: 'Atlantis' not in \"Could not resolve location 'Nowhere'.\"",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_checker.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the checker**

```python
# src/swiss_grounding/evals/checker.py
"""Compare a QueryResponse against a probe's expectation. Pure; returns failure strings."""
from collections.abc import Iterable, Sequence
from datetime import date

from swiss_grounding.evals.probe_models import EvidenceRule, Expectation, Probe, ResolvedExpectation
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryResponse

OFF_PATH = "off_path"


def _rule_label(rule: EvidenceRule) -> str:
    parts = [f"{k}={v}" for k, v in (
        ("source", rule.source), ("url_contains", rule.url_contains),
        ("extent", rule.extent), ("authority", rule.authority),
    ) if v]
    return " ".join(parts)


def _matches(rule: EvidenceRule, c: Citation, path: Sequence[str]) -> bool:
    if rule.source and c.source_id != rule.source:
        return False
    if rule.url_contains and rule.url_contains not in c.url:
        return False
    if rule.authority and c.authority != rule.authority:
        return False
    if rule.extent == OFF_PATH:
        return c.extent_id not in path
    if rule.extent and c.extent_id != rule.extent:
        return False
    return True


def _check_resolved(exp: ResolvedExpectation, resp: QueryResponse, tree: LocationTree) -> Iterable[str]:
    got = resp.resolved_location_id
    if exp.id is not None:
        if got != exp.id:
            yield f"resolved: expected {exp.id}, got {got}"
        return
    wanted = f"{exp.label} ({exp.level} under {exp.parent})"
    node = tree.by_id.get(got) if got else None
    if node is None:
        yield f"resolved: expected {wanted}, got {got}"
        return
    ok = (
        node.label("en") == exp.label
        and (exp.level is None or node.level.value == exp.level)
        and (exp.parent is None or node.parent_id == exp.parent)
    )
    if not ok:
        yield f"resolved: expected {wanted}, got {got} ({node.label('en')}, {node.level.value} under {node.parent_id})"


def _check_first(exp: Expectation, first: Citation | None, today: date, citations: Sequence[Citation]) -> Iterable[str]:
    if first is None:
        if any((exp.first_extent, exp.first_authority, exp.first_url_contains, exp.first_event)):
            yield "first: no citations returned"
        return
    if exp.first_extent and first.extent_id != exp.first_extent:
        yield f"first_extent: expected {exp.first_extent}, got {first.extent_id}"
    if exp.first_authority and first.authority != exp.first_authority:
        yield f"first_authority: expected {exp.first_authority}, got {first.authority}"
    if exp.first_url_contains and exp.first_url_contains not in first.url:
        yield f"first_url_contains: '{exp.first_url_contains}' not in {first.url}"
    if exp.first_event == "nearest_future":
        future = sorted(c.event_date for c in citations if c.event_date and c.event_date >= today)
        if first.event_date is None:
            yield "first_event: first citation carries no event_date"
        elif first.event_date < today:
            yield f"first_event: first citation {first.event_date} is before today {today}"
        elif future and first.event_date != future[0]:
            yield f"first_event: expected nearest future {future[0]}, first citation has {first.event_date}"


def _check_coverage(exp: Expectation, resp: QueryResponse) -> Iterable[str]:
    if not (exp.coverage_empty or exp.coverage_present):
        return
    signal = getattr(resp, "coverage", None)
    if signal is None:
        yield "coverage: response carries no coverage signal"
        return
    counts = {row["extent_id"]: row["documents"] for row in signal}
    for extent in exp.coverage_empty:
        if extent not in counts:
            yield f"coverage: {extent} not listed in signal"
        elif counts[extent] != 0:
            yield f"coverage: expected {extent} empty, has {counts[extent]} documents"
    for extent in exp.coverage_present:
        if counts.get(extent, 0) == 0:
            yield f"coverage: expected {extent} present, has {counts.get(extent, 0)} documents"


def check(probe: Probe, resp: QueryResponse, tree: LocationTree, today: date) -> tuple[str, ...]:
    exp = probe.expect
    failures: list[str] = []
    if resp.status != exp.status:
        failures.append(f"status: expected {exp.status}, got {resp.status}")
    if exp.resolved is not None:
        failures.extend(_check_resolved(exp.resolved, resp, tree))
    if exp.method and resp.resolution_method != exp.method:
        failures.append(f"method: expected {exp.method}, got {resp.resolution_method}")
    for alt in exp.alternatives_include:
        if alt not in resp.alternatives:
            failures.append(f"alternatives: {alt} missing from {resp.alternatives}")
    path = tree.path(resp.resolved_location_id) if resp.resolved_location_id in tree.by_id else ()
    for rule in exp.must_include:
        if not any(_matches(rule, c, path) for c in resp.citations):
            failures.append(f"must_include: no citation matched {_rule_label(rule)}")
    for rule in exp.must_exclude:
        for c in resp.citations:
            if _matches(rule, c, path):
                failures.append(f"must_exclude: citation matched {_rule_label(rule)} ({c.url})")
    first = resp.citations[0] if resp.citations else None
    failures.extend(_check_first(exp, first, today, resp.citations))
    failures.extend(_check_coverage(exp, resp))
    if exp.message_contains and exp.message_contains not in resp.message:
        failures.append(f"message: '{exp.message_contains}' not in \"{resp.message}\"")
    return tuple(failures)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_checker.py -v`
Expected: 13 passed. If `Level` is not a `str` enum and `.value` differs, check `src/swiss_grounding/locations/models.py` and match its representation in `_check_resolved`.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/checker.py tests/unit/evals/test_checker.py
git commit -m "feat: pure probe checker over QueryResponse"
```

---

## Task 4: Injectable clock in QueryCore

Structural temporal probes need a frozen "today". The reranker already takes a clock; the core does not pass one.

**Files:**
- Modify: `src/swiss_grounding/retrieval/query_core.py`
- Test: `tests/unit/test_query_core_clock.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_query_core_clock.py
from dataclasses import fields
from datetime import date

from swiss_grounding.retrieval.query_core import QueryCore


def test_query_core_has_today_field_defaulting_to_date_today():
    names = {f.name: f for f in fields(QueryCore)}
    assert "today" in names
    assert names["today"].default is date.today
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_query_core_clock.py -v`
Expected: FAIL with `AssertionError` on `"today" in names`

- [ ] **Step 3: Add the field and pass it to rerank**

In `src/swiss_grounding/retrieval/query_core.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
```

and in the dataclass:

```python
@dataclass(frozen=True)
class QueryCore:
    database_url: str
    tree: LocationTree
    resolver: LocationResolver
    embedder: Embedder
    weights: RerankWeights
    today: Callable[[], date] = date.today
```

and change the rerank call:

```python
        ranked = rerank(hits, self.tree, resolved.location.id, request.categories, self.weights,
                        today=self.today)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/retrieval/query_core.py tests/unit/test_query_core_clock.py
git commit -m "feat: injectable clock on QueryCore for deterministic evals"
```

---

## Task 5: Structural fixture corpus

A corpus small enough to reason about, shaped to make every structural probe's expected and observed behaviour unambiguous. Dates are relative to the frozen clock `2026-09-16`.

**Files:**
- Create: `tests/fixtures/probe_corpus.json`
- Test: `tests/integration/test_probe_corpus.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_probe_corpus.py
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
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"


def test_probe_corpus_loads_and_covers_every_level():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        report = load_fixture(conn, CORPUS, FakeEmbedder(dim=8))
        extents = {r["extent_id"] for r in conn.execute("select distinct extent_id from document").fetchall()}
    assert report.documents >= 12
    assert {"CH", "CH-ZH", "CH-ZH-261", "CH-ZH-261-K3", "CH-BS"} <= extents
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_probe_corpus.py -v`
Expected: FAIL with `FileNotFoundError` on the corpus path

- [ ] **Step 3: Write the corpus**

```json
{
  "documents": [
    {
      "source_id": "fedlex",
      "url": "https://www.fedlex.admin.ch/eli/cc/2008/414/de",
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
         "text_original": "Wer ein Tier hält, muss es angemessen nähren und pflegen.",
         "text_en": "Anyone who keeps an animal must feed and care for it appropriately. Dog owners must ensure the dog does not endanger people or other animals."}
      ]
    },
    {
      "source_id": "fedlex",
      "url": "https://www.fedlex.admin.ch/eli/cc/1991/1052_1052_1052/de",
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
         "text_original": "Dieses Gesetz regelt die Planung von Fuss- und Wanderwegnetzen.",
         "text_en": "This Act governs the planning, construction and maintenance of hiking trail networks. Cantons are responsible for hiking trails and their signposting."}
      ]
    },
    {
      "source_id": "fedlex",
      "url": "https://www.fedlex.admin.ch/eli/cc/1983/1205_1205_1205/de",
      "identifier": "SR 814.01 Art. 30",
      "title_original": "Umweltschutzgesetz",
      "title_en": "Environmental Protection Act",
      "language": "de",
      "extent_id": "CH",
      "authority": "federal_law",
      "categories": ["waste"],
      "valid_from": "1985-01-01",
      "chunks": [
        {"heading_path": "Art. 30", "anchor": "art_30",
         "text_original": "Abfälle sind soweit möglich zu vermeiden und zu verwerten.",
         "text_en": "Waste must be avoided where possible and recycled. Cantons and communes organise the collection of household waste, paper and cardboard."}
      ]
    },
    {
      "source_id": "ch_ch",
      "url": "https://www.ch.ch/en/animals/dogs/",
      "identifier": null,
      "title_original": "Dogs",
      "title_en": "Dogs",
      "language": "en",
      "extent_id": "CH",
      "authority": "official_info",
      "categories": ["dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Dog tax", "anchor": "tax",
         "text_original": "Every dog must be registered with the commune. Communes levy a dog tax.",
         "text_en": "Every dog must be registered with the commune. Communes levy a dog tax; the amount is set by each canton or commune."}
      ]
    },
    {
      "source_id": "schweizer_wanderwege",
      "url": "https://www.schweizer-wanderwege.ch/de/wissen/sicherheit",
      "identifier": null,
      "title_original": "Sicher unterwegs",
      "title_en": "Safe on the trail",
      "language": "de",
      "extent_id": "CH",
      "authority": "institutional",
      "categories": ["hiking", "safety"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Hunde", "anchor": "hunde",
         "text_original": "Wir empfehlen, Hunde auf Wanderwegen an der Leine zu führen.",
         "text_en": "We recommend keeping dogs on a leash on hiking trails, especially near grazing cattle."}
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
         "text_original": "Im Kanton Zürich gilt vom 1. April bis 31. Juli im Wald Leinenpflicht.",
         "text_en": "In the Canton of Zurich, dogs must be kept on a leash in forests and at forest edges from 1 April to 31 July. This applies on hiking trails through forest."}
      ]
    },
    {
      "source_id": "zh_ch",
      "url": "https://www.zh.ch/de/umwelt-tiere/abfall-rohstoffe.html",
      "identifier": null,
      "title_original": "Abfall und Rohstoffe",
      "title_en": "Waste and raw materials",
      "language": "de",
      "extent_id": "CH-ZH",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Sammlung", "anchor": "sammlung",
         "text_original": "Die Gemeinden organisieren die Sammlung von Papier und Karton.",
         "text_en": "Communes in the Canton of Zurich organise the collection of paper and cardboard. Check your commune's calendar."}
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
        {"heading_path": "Leinenpflicht", "anchor": "leinenpflicht",
         "text_original": "In städtischen Parks gilt Leinenpflicht für Hunde.",
         "text_en": "Dogs must be kept on a leash in city parks of Zurich. Off-leash areas are marked."}
      ]
    },
    {
      "source_id": "stadt_zuerich",
      "url": "https://www.stadt-zuerich.ch/de/umwelt-und-energie/abfall/karton.html",
      "identifier": null,
      "title_original": "Karton",
      "title_en": "Cardboard",
      "language": "de",
      "extent_id": "CH-ZH-261",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Karton bereitstellen", "anchor": "bereitstellen",
         "text_original": "Karton gebündelt bis 7 Uhr am Sammeltag bereitstellen.",
         "text_en": "Bundle cardboard and put it out by 7:00 on collection day. Collection days depend on your district; see the collection calendar."}
      ]
    },
    {
      "source_id": "stadt_zuerich",
      "url": "https://www.stadt-zuerich.ch/de/stadtleben/hundezone-wiedikon.html",
      "identifier": null,
      "title_original": "Hundezone Wiedikon",
      "title_en": "Dog zone Wiedikon",
      "language": "de",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Freilauf", "anchor": "freilauf",
         "text_original": "In der Hundezone Wiedikon dürfen Hunde frei laufen.",
         "text_en": "In the Wiedikon dog zone in District 3, dogs may run off leash."}
      ]
    },
    {
      "source_id": "open_erz",
      "url": "https://openerz.metaodi.ch/api/calendar?region=zurich&zip=8003&sort=date&limit=100#cardboard-2026-09-10",
      "identifier": "cardboard-2026-09-10",
      "title_original": "Waste collection cardboard in 8003 on 2026-09-10",
      "title_en": "Waste collection cardboard in 8003 on 2026-09-10",
      "language": "en",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "event_date": "2026-09-10",
      "chunks": [
        {"heading_path": "Waste collection cardboard in 8003", "anchor": null,
         "text_original": "Collection of cardboard in Zurich postal code 8003 on 2026-09-10.",
         "text_en": "Collection of cardboard in Zurich postal code 8003 on 2026-09-10. Put it out before 7:00 on collection day."}
      ]
    },
    {
      "source_id": "open_erz",
      "url": "https://openerz.metaodi.ch/api/calendar?region=zurich&zip=8003&sort=date&limit=100#cardboard-2026-09-17",
      "identifier": "cardboard-2026-09-17",
      "title_original": "Waste collection cardboard in 8003 on 2026-09-17",
      "title_en": "Waste collection cardboard in 8003 on 2026-09-17",
      "language": "en",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "event_date": "2026-09-17",
      "chunks": [
        {"heading_path": "Waste collection cardboard in 8003", "anchor": null,
         "text_original": "Collection of cardboard in Zurich postal code 8003 on 2026-09-17.",
         "text_en": "Collection of cardboard in Zurich postal code 8003 on 2026-09-17. Put it out before 7:00 on collection day."}
      ]
    },
    {
      "source_id": "open_erz",
      "url": "https://openerz.metaodi.ch/api/calendar?region=zurich&zip=8003&sort=date&limit=100#cardboard-2026-12-31",
      "identifier": "cardboard-2026-12-31",
      "title_original": "Waste collection cardboard in 8003 on 2026-12-31",
      "title_en": "Waste collection cardboard in 8003 on 2026-12-31",
      "language": "en",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "event_date": "2026-12-31",
      "chunks": [
        {"heading_path": "Waste collection cardboard in 8003", "anchor": null,
         "text_original": "Collection of cardboard in Zurich postal code 8003 on 2026-12-31.",
         "text_en": "Collection of cardboard in Zurich postal code 8003 on 2026-12-31. Put it out before 7:00 on collection day."}
      ]
    },
    {
      "source_id": "open_erz",
      "url": "https://openerz.metaodi.ch/api/calendar?region=zurich&zip=8003&sort=date&limit=100#paper-2026-09-29",
      "identifier": "paper-2026-09-29",
      "title_original": "Waste collection paper in 8003 on 2026-09-29",
      "title_en": "Waste collection paper in 8003 on 2026-09-29",
      "language": "en",
      "extent_id": "CH-ZH-261-K3",
      "authority": "official_info",
      "categories": ["waste"],
      "valid_from": null,
      "event_date": "2026-09-29",
      "chunks": [
        {"heading_path": "Waste collection paper in 8003", "anchor": null,
         "text_original": "Collection of paper in Zurich postal code 8003 on 2026-09-29.",
         "text_en": "Collection of paper in Zurich postal code 8003 on 2026-09-29. Put it out before 7:00 on collection day."}
      ]
    },
    {
      "source_id": "ch_ch",
      "url": "https://www.bs.ch/hunde",
      "identifier": null,
      "title_original": "Hunde in Basel-Stadt",
      "title_en": "Dogs in Basel-Stadt",
      "language": "de",
      "extent_id": "CH-BS",
      "authority": "official_info",
      "categories": ["dogs"],
      "valid_from": null,
      "chunks": [
        {"heading_path": "Leinenpflicht", "anchor": null,
         "text_original": "In Basel-Stadt gilt ganzjährig Leinenpflicht im Wald.",
         "text_en": "In Basel-Stadt, dogs must be leashed in forests all year round."}
      ]
    }
  ]
}
```

Note: the Basel document uses `source_id: ch_ch` only because the seed registry has no Basel source; its extent is what matters. The sibling-leak probes reference it by `extent`, never by source.

- [ ] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_probe_corpus.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/probe_corpus.json tests/integration/test_probe_corpus.py
git commit -m "test: structural probe corpus for canton Zurich"
```

---

## Task 6: Tier 1 probes, in-city

Every probe below was chosen so that its expected behaviour follows from the decisions in `CONTEXT.md` and the two ADRs. `status: red` means the server fails it today; the runner turns red probes into strict expected failures.

**Files:**
- Create: `evals/probes/city.yaml`
- Test: `tests/unit/evals/test_probe_files.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_probe_files.py
from collections import Counter

from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes


def test_probe_dir_loads():
    probes = load_all_probes(PROBE_DIR)
    assert len(probes) >= 20


def test_city_tier_has_twenty_probes():
    tiers = Counter(t for t, _ in load_all_probes(PROBE_DIR))
    assert tiers["city"] == 20


def test_every_failure_class_is_probed():
    classes = {p.failure_class for _, p in load_all_probes(PROBE_DIR)}
    assert {"jurisdiction_confusion", "authority_hierarchy", "temporal_misapplication",
            "entity_substitution", "silent_under_coverage"} <= classes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_probe_files.py -v`
Expected: FAIL, `len(probes) >= 20` is false because the directory is empty

- [ ] **Step 3: Write the tier 1 probe file**

```yaml
# evals/probes/city.yaml
tier: city
probes:
  - id: city-001
    question: When is the next cardboard collection?
    location: "8003"
    categories: [waste]
    kind: structural
    failure_class: temporal_misapplication
    status: red
    judge: true
    note: With a frozen clock of 2026-09-16 the nearest future event is 2026-09-17. Today the reranker only penalises past events, so ordering among future events is arbitrary.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      must_include:
        - {source: open_erz, url_contains: "#cardboard-2026-09-17"}
      first_event: nearest_future

  - id: city-002
    question: When is the next cardboard collection?
    location: "8004"
    categories: [waste]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    judge: true
    note: Only 8003 has calendar data. Kreis 4 must get city and canton guidance, no Kreis 3 dates, and a signal that Kreis 4 itself is empty.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K4}
      must_exclude:
        - {source: open_erz}
        - {extent: off_path}
      must_include:
        - {source: stadt_zuerich, url_contains: karton}
      coverage_empty: [CH-ZH-261-K4]
      coverage_present: [CH-ZH-261]

  - id: city-003
    question: Did I miss last week's cardboard collection?
    location: "8003"
    categories: [waste]
    kind: structural
    failure_class: temporal_misapplication
    status: green
    note: Past events must stay reachable, just not first.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      must_include:
        - {source: open_erz, url_contains: "#cardboard-2026-09-10"}

  - id: city-004
    question: When is paper collected?
    location: "8003"
    categories: [waste]
    kind: ranking
    failure_class: entity_substitution
    status: red
    judge: true
    note: Paper and cardboard are different collections. The first citation must be a paper event, not cardboard.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      first_url_contains: "#paper-"
      first_event: nearest_future

  - id: city-005
    question: Where can my dog run off leash?
    location: Wiedikon
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: green
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3-ALT-WIEDIKON}
      first_extent: CH-ZH-261-K3
      must_exclude:
        - {extent: off_path}
        - {extent: CH-BS}

  - id: city-006
    question: Where can my dog run off leash?
    location: Seefeld
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: Seefeld is Kreis 8. The Wiedikon dog zone is a sibling and must not appear. Coverage must say Kreis 8 is empty.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K8-SEEFELD}
      must_exclude:
        - {extent: CH-ZH-261-K3}
        - {extent: off_path}
      must_include:
        - {source: stadt_zuerich, url_contains: parks/hunde}
      coverage_empty: [CH-ZH-261-K8-SEEFELD, CH-ZH-261-K8]

  - id: city-007
    question: Do I need to leash my dog in the forest in July?
    location: Zürich
    categories: [dogs]
    kind: structural
    failure_class: authority_hierarchy
    status: green
    note: The canton rule is the operative one. Institutional advice from Schweizer Wanderwege must not be first.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      alternatives_include: [CH-ZH]
      must_include:
        - {source: zh_ch, url_contains: hunde}
      must_exclude:
        - {authority: institutional, extent: CH}

  - id: city-008
    question: How much is the dog tax?
    location: Stadt Zürich
    categories: [dogs]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    note: No indexed page states the city dog tax. The result may carry ch.ch and canton evidence but must say the city level has no dog tax document. Today the city level does have dog documents, so coverage_present holds; the failure is the missing signal.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      must_include:
        - {source: ch_ch, url_contains: dogs}
      coverage_present: [CH-ZH-261, CH]

  - id: city-009
    question: When is cardboard collected?
    location: Kreis 3
    categories: [waste]
    kind: structural
    failure_class: none
    status: green
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      method: alias
      must_include:
        - {source: open_erz}

  - id: city-010
    question: When is cardboard collected in Kreis 3?
    categories: [waste]
    kind: structural
    failure_class: none
    status: green
    note: Location given only inside the question; the scanner must find it.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      method: alias_scan
      must_include:
        - {source: open_erz}

  - id: city-011
    question: When is cardboard collected?
    location: "8045"
    categories: [waste]
    kind: structural
    failure_class: none
    status: green
    note: 8045 is a second postal code inside Kreis 3; the 8003 calendar applies because the calendar is filed at Kreis level.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      must_include:
        - {source: open_erz}

  - id: city-012
    question: Where can my dog run off leash?
    location: City
    categories: [dogs]
    kind: structural
    failure_class: entity_substitution
    status: red
    note: "City" is a Quartier name in Kreis 1. A bare "City" as a location must not resolve to that Quartier; it is ambiguous and should need a location.
    expect:
      status: needs_location

  - id: city-013
    question: Where can my dog run off leash?
    location: Zurich City
    categories: [dogs]
    kind: structural
    failure_class: entity_substitution
    status: green
    expect:
      status: results
      resolved: {id: CH-ZH-261}

  - id: city-014
    question: Where can my dog run off leash in Hard?
    categories: [dogs]
    kind: structural
    failure_class: entity_substitution
    status: red
    note: Hard is a Quartier in Kreis 4 and also a common English word. Without a marker the scanner must not resolve it; with no other location the response is needs_location.
    expect:
      status: needs_location

  - id: city-015
    question: Where can my dog run off leash?
    location: Quartier Hard
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    expect:
      status: results
      resolved: {id: CH-ZH-261-K4-HARD}

  - id: city-016
    question: What are the rules for dogs?
    location: Zürich West
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    note: Alias of the Escher Wyss Quartier.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K5-ESCHER-WYSS}
      must_exclude:
        - {extent: off_path}

  - id: city-017
    question: Which cantonal rules apply to dogs on hiking trails?
    location: Kanton Zürich
    categories: [dogs, hiking]
    kind: structural
    failure_class: jurisdiction_confusion
    status: green
    note: Marked canton input must resolve to the canton, not the city, and must not return city documents.
    expect:
      status: results
      resolved: {id: CH-ZH}
      must_include:
        - {source: zh_ch, extent: CH-ZH}
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: off_path}

  - id: city-018
    question: When is cardboard collected?
    location: "8003"
    categories: [waste]
    as_of: "2026-09-12"
    kind: structural
    failure_class: temporal_misapplication
    status: red
    note: With as_of before the 2026-09-17 event, the 2026-09-10 event is the nearest one at or after that date is 09-17; the nearest_future rule is evaluated against as_of when given. Today as_of only filters law validity, not calendar ordering.
    expect:
      status: results
      resolved: {id: CH-ZH-261-K3}
      first_url_contains: "#cardboard-2026-09-17"

  - id: city-019
    question: Was ist die Leinenpflicht im Wald?
    location: Zürich
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    note: German question over English-indexed text. Lexical leg will miss; dense leg must carry it on the live corpus. On fixtures with the fake embedder this checks only routing.
    expect:
      status: results
      resolved: {id: CH-ZH-261}

  - id: city-020
    question: Who maintains hiking trail signposts?
    location: Zürich
    categories: [hiking]
    kind: ranking
    failure_class: authority_hierarchy
    status: red
    judge: true
    note: Federal law assigns trails to cantons. On the live corpus the institutional Schweizer Wanderwege pages dominate hiking; the federal act must still be in the results.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      must_include:
        - {source: fedlex, url_contains: "1991/1052"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_probe_files.py::test_city_tier_has_twenty_probes -v`
Expected: PASS. The other two tests still fail until Tasks 7 and 8 add the remaining tiers.

- [ ] **Step 5: Commit**

```bash
git add evals/probes/city.yaml tests/unit/evals/test_probe_files.py
git commit -m "feat: tier 1 in-city probes"
```

---

## Task 7: Tier 2 probes, canton communes

Commune probes expect a municipality node under `CH-ZH` by label, because the commune register is not seeded yet and the exact ids are assigned by the register's BFS numbers.

**Files:**
- Create: `evals/probes/communes.yaml`

- [ ] **Step 1: Extend the probe-file test**

Add to `tests/unit/evals/test_probe_files.py`:

```python
def test_communes_tier_has_fifteen_probes():
    tiers = Counter(t for t, _ in load_all_probes(PROBE_DIR))
    assert tiers["communes"] == 15


def test_commune_probes_never_expect_an_exact_id():
    for tier, p in load_all_probes(PROBE_DIR):
        if tier == "communes" and p.expect.resolved is not None:
            assert p.expect.resolved.id is None or p.expect.resolved.id in {"CH-ZH", "CH-ZH-261"}, p.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_probe_files.py::test_communes_tier_has_fifteen_probes -v`
Expected: FAIL, count is 0

- [ ] **Step 3: Write the tier 2 probe file**

```yaml
# evals/probes/communes.yaml
tier: communes
probes:
  - id: com-001
    question: Do I need to leash my dog in the forest?
    location: Winterthur
    categories: [dogs]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    judge: true
    note: Today resolves to the canton via geoadmin_approximate. Expected is the Winterthur node itself with canton and federal evidence and a signal that Winterthur is empty.
    expect:
      status: results
      resolved: {label: Winterthur, level: municipality, parent: CH-ZH}
      must_include:
        - {source: zh_ch, extent: CH-ZH}
        - {source: fedlex}
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: off_path}
      coverage_empty: [Winterthur]
      coverage_present: [CH-ZH]

  - id: com-002
    question: When is cardboard collected?
    location: Uster
    categories: [waste]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    judge: true
    note: No calendar for Uster. Must not return the 8003 calendar. Canton guidance applies.
    expect:
      status: results
      resolved: {label: Uster, level: municipality, parent: CH-ZH}
      must_exclude:
        - {source: open_erz}
        - {extent: CH-ZH-261}
      must_include:
        - {source: zh_ch, url_contains: abfall}
      coverage_empty: [Uster]

  - id: com-003
    question: When is cardboard collected in Dübendorf?
    categories: [waste]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    note: Location only in the question, with an umlaut.
    expect:
      status: results
      resolved: {label: Dübendorf, level: municipality, parent: CH-ZH}
      must_exclude:
        - {source: open_erz}
      coverage_empty: [Dübendorf]

  - id: com-004
    question: Do I need to leash my dog in the forest?
    location: Kloten
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: Kloten must not receive city of Zurich park rules.
    expect:
      status: results
      resolved: {label: Kloten, level: municipality, parent: CH-ZH}
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: CH-ZH-261-K3}

  - id: com-005
    question: Do I need to leash my dog in the forest?
    location: Wetzikon
    categories: [dogs]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    expect:
      status: results
      resolved: {label: Wetzikon, level: municipality, parent: CH-ZH}
      must_include:
        - {source: zh_ch, extent: CH-ZH}
      coverage_empty: [Wetzikon]

  - id: com-006
    question: Do I need to leash my dog in the forest?
    location: Wil ZH
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: Wil exists in both ZH and SG. The canton suffix must pin it to Zurich.
    expect:
      status: results
      resolved: {label: Wil, level: municipality, parent: CH-ZH}
      must_include:
        - {source: zh_ch, extent: CH-ZH}

  - id: com-007
    question: Do I need to leash my dog in the forest?
    location: Wil
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: Bare "Wil" is ambiguous between cantons. Must ask, not guess.
    expect:
      status: needs_location
      message_contains: Wil

  - id: com-008
    question: Do I need to leash my dog in the forest?
    location: Affoltern am Albis
    categories: [dogs]
    kind: structural
    failure_class: entity_substitution
    status: red
    note: A commune, not the Affoltern Quartier in Kreis 11. Today the alias index maps "Affoltern" to the Quartier and the full name goes to GeoAdmin.
    expect:
      status: results
      resolved: {label: Affoltern am Albis, level: municipality, parent: CH-ZH}
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: CH-ZH-261-K11}

  - id: com-009
    question: Do I need to leash my dog in the forest?
    location: Affoltern
    categories: [dogs]
    kind: structural
    failure_class: entity_substitution
    status: red
    note: Bare "Affoltern" matches a Quartier and a commune. Must ask.
    expect:
      status: needs_location

  - id: com-010
    question: Do I need to leash my dog in the forest?
    location: Gemeinde Winterthur
    categories: [dogs]
    kind: structural
    failure_class: none
    status: red
    note: Marked commune input. Same expectation as com-001; checks that the marker is accepted.
    expect:
      status: results
      resolved: {label: Winterthur, level: municipality, parent: CH-ZH}
      method: alias

  - id: com-011
    question: Do I need to leash my dog in the forest?
    location: "8400"
    categories: [dogs]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    note: Postal code of Winterthur. The register carries postal codes for communes; today 8400 is unknown.
    expect:
      status: results
      resolved: {label: Winterthur, level: municipality, parent: CH-ZH}
      coverage_empty: [Winterthur]

  - id: com-012
    question: Do I need to leash my dog in the forest?
    location: Winterthurr
    categories: [dogs]
    kind: structural
    failure_class: none
    status: red
    note: One-character typo. Accepted under the edit-distance rule, resolved to Winterthur, method geoadmin.
    expect:
      status: results
      resolved: {label: Winterthur, level: municipality, parent: CH-ZH}
      method: geoadmin

  - id: com-013
    question: Do I need to leash my dog in the forest?
    location: Bülach
    categories: [dogs]
    kind: structural
    failure_class: silent_under_coverage
    status: red
    expect:
      status: results
      resolved: {label: Bülach, level: municipality, parent: CH-ZH}
      coverage_empty: [Bülach]
      coverage_present: [CH]

  - id: com-014
    question: What applies to dogs everywhere in the canton?
    location: Kanton Zürich
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: green
    note: Control probe. Canton-level answer must carry canton documents and no commune or city ones.
    expect:
      status: results
      resolved: {id: CH-ZH}
      must_include:
        - {source: zh_ch, extent: CH-ZH}
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: off_path}

  - id: com-015
    question: Do I need to leash my dog in the forest?
    location: Dietikon
    categories: [dogs]
    kind: ranking
    failure_class: authority_hierarchy
    status: red
    judge: true
    note: With no local data, the canton leash rule must outrank institutional trail advice. Live corpus only.
    expect:
      status: results
      resolved: {label: Dietikon, level: municipality, parent: CH-ZH}
      first_extent: CH-ZH
      first_authority: official_info
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/evals/test_probe_files.py -v`
Expected: `test_communes_tier_has_fifteen_probes` and `test_commune_probes_never_expect_an_exact_id` pass; `test_every_failure_class_is_probed` passes.

- [ ] **Step 5: Commit**

```bash
git add evals/probes/communes.yaml tests/unit/evals/test_probe_files.py
git commit -m "feat: tier 2 canton commune probes"
```

---

## Task 8: Tier 3 probes, lookalikes

**Files:**
- Create: `evals/probes/lookalikes.yaml`

- [ ] **Step 1: Extend the probe-file test**

Add to `tests/unit/evals/test_probe_files.py`:

```python
def test_lookalikes_tier_has_twelve_probes():
    tiers = Counter(t for t, _ in load_all_probes(PROBE_DIR))
    assert tiers["lookalikes"] == 12


def test_fifteen_judge_cases():
    assert sum(1 for _, p in load_all_probes(PROBE_DIR) if p.judge) == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_probe_files.py::test_lookalikes_tier_has_twelve_probes -v`
Expected: FAIL, count is 0

- [ ] **Step 3: Write the tier 3 probe file**

```yaml
# evals/probes/lookalikes.yaml
tier: lookalikes
probes:
  - id: look-001
    question: Do I need to leash my dog in the forest?
    location: Zürich Oberland
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    judge: true
    note: Today resolves to the city via a one-token GeoAdmin overlap. Expected is canton, approximate, with a signal that the region is not recognised.
    expect:
      status: results
      resolved: {id: CH-ZH}
      method: geoadmin_approximate
      must_exclude:
        - {extent: CH-ZH-261}
        - {extent: off_path}

  - id: look-002
    question: Do I need to leash my dog in the forest?
    location: Zug
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: green
    note: Neighbouring canton. No Zurich documents at any level.
    expect:
      status: results
      resolved: {id: CH-ZG}
      must_exclude:
        - {extent: CH-ZH}
        - {extent: CH-ZH-261}
        - {extent: off_path}

  - id: look-003
    question: Do I need to leash my dog in the forest?
    location: ZH
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    expect:
      status: results
      resolved: {id: CH-ZH}
      method: alias

  - id: look-004
    question: Do I need to leash my dog in the forest?
    location: Zurigo
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    note: Italian name; shared by canton and city, most specific wins with the canton as alternative.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      alternatives_include: [CH-ZH]

  - id: look-005
    question: Do I need to leash my dog in the forest?
    location: Zurich Airport
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    judge: true
    note: The airport lies in Kloten, not in the city. Today GeoAdmin overlap on "zurich" gives the city. Expected is Kloten once the register exists, or at minimum not the city.
    expect:
      status: results
      resolved: {label: Kloten, level: municipality, parent: CH-ZH}
      must_exclude:
        - {extent: CH-ZH-261}

  - id: look-006
    question: Do I need to leash my dog in the forest?
    location: Zürichsee
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: A lake, not a jurisdiction. Must not resolve to the city.
    expect:
      status: needs_location

  - id: look-007
    question: Do I need to leash my dog in the forest?
    location: Zurzach
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: red
    note: Canton Aargau commune whose name starts like Zurich. Expected is a municipality under CH-AG once the register exists.
    expect:
      status: results
      resolved: {label: Zurzach, level: municipality, parent: CH-AG}
      must_exclude:
        - {extent: CH-ZH}
        - {extent: CH-ZH-261}

  - id: look-008
    question: Do I need to leash my dog in the forest?
    location: Basel
    categories: [dogs]
    kind: structural
    failure_class: jurisdiction_confusion
    status: green
    note: Control. Basel alias resolves to Basel-Stadt; the CH-BS fixture document must appear, nothing from Zurich.
    expect:
      status: results
      resolved: {id: CH-BS}
      must_include:
        - {extent: CH-BS}
      must_exclude:
        - {extent: CH-ZH}
        - {extent: CH-ZH-261}

  - id: look-009
    question: Muss ich meinen Hund im Wald anleinen?
    location: Kanton Zürich
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    note: German question with a marked canton. Routing only on fixtures.
    expect:
      status: results
      resolved: {id: CH-ZH}

  - id: look-010
    question: Do I need to leash my dog in the forest?
    location: Zürich, Switzerland
    categories: [dogs]
    kind: structural
    failure_class: none
    status: red
    note: Trailing country name. Today the exact alias lookup fails on the whole string and falls to GeoAdmin. Expected is the city with the canton alternative, as for bare Zürich.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      alternatives_include: [CH-ZH]

  - id: look-011
    question: Do I need to leash my dog in the forest?
    location: Nowhere
    categories: [dogs]
    kind: structural
    failure_class: none
    status: green
    note: Control. GeoAdmin fuzzy-matches "Nowhere" to Nidwalden; the overlap check must reject it.
    expect:
      status: needs_location
      message_contains: Nowhere

  - id: look-012
    question: Where can I dispose of cardboard?
    location: Zürich
    categories: [waste]
    kind: ranking
    failure_class: entity_substitution
    status: red
    judge: true
    note: Bare Zürich resolves to the city. On the live corpus the Kreis 3 calendar is not on the city path and must not appear; the city cardboard page must be first.
    expect:
      status: results
      resolved: {id: CH-ZH-261}
      must_exclude:
        - {source: open_erz}
      first_url_contains: stadt-zuerich.ch
```

Judge count check: city-001, city-002, city-004, city-020, com-001, com-002, com-015, look-001, look-005, look-012 is ten. Mark five more as `judge: true` to reach fifteen: city-006, city-007, city-008, com-007, com-008. Edit those five probes in their files to add `judge: true`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/evals/test_probe_files.py -v`
Expected: all pass, including `test_fifteen_judge_cases`

- [ ] **Step 5: Commit**

```bash
git add evals/probes/lookalikes.yaml evals/probes/city.yaml evals/probes/communes.yaml tests/unit/evals/test_probe_files.py
git commit -m "feat: tier 3 lookalike probes and judge markers"
```

---

## Task 9: Runner

Runs one probe through a `QueryCore` and returns a `ProbeResult` with the checker's failures and an `Observed` block. Shared by the pytest harness and the CLI.

**Files:**
- Create: `src/swiss_grounding/evals/runner.py`
- Test: `tests/unit/evals/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_runner.py
from datetime import date, datetime, timezone

from swiss_grounding.evals.probe_models import Expectation, Probe, ResolvedExpectation
from swiss_grounding.evals.runner import ProbeResult, run_probe, to_request
from swiss_grounding.locations.models import Level, Location
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import Citation, QueryRequest, QueryResponse

TODAY = date(2026, 9, 16)


class FakeCore:
    def __init__(self, resp: QueryResponse):
        self.resp = resp
        self.tree = LocationTree.from_locations([
            Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None, lindas_uri=None, names={"en": "Switzerland"}, aliases=()),
        ])
        self.seen: list[QueryRequest] = []

    def query(self, request: QueryRequest) -> QueryResponse:
        self.seen.append(request)
        return self.resp


def _probe() -> Probe:
    return Probe(id="p", question="q", location="Switzerland", categories=("dogs",), limit=5,
                 kind="structural", failure_class="none", status="green",
                 expect=Expectation(status="results", resolved=ResolvedExpectation(id="CH")))


def test_to_request_maps_probe_fields():
    req = to_request(_probe())
    assert req == QueryRequest(question="q", location="Switzerland", categories=("dogs",), as_of=None, limit=5)


def test_run_probe_builds_result_with_observed():
    cit = Citation(chunk_id=1, document_id=1, source_id="fedlex", title_en="t", title_original="t",
                   url="https://x", anchor=None, identifier=None, snippet_en="s", snippet_original="s",
                   language="de", heading_path="", extent_id="CH", extent_label="CH", authority="federal_law",
                   categories=("dogs",), valid_from=None, retrieved_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
                   license=None, score=1.0)
    core = FakeCore(QueryResponse(status="results", resolved_location_id="CH", resolution_method="alias", citations=(cit,)))
    result = run_probe(_probe(), core, TODAY, git_commit="abc123")
    assert isinstance(result, ProbeResult)
    assert result.passed is True
    assert result.failures == ()
    assert result.observed.resolved_id == "CH"
    assert result.observed.git_commit == "abc123"
    assert result.observed.citations[0].source == "fedlex"
    assert core.seen[0].limit == 5


def test_run_probe_records_failures():
    core = FakeCore(QueryResponse(status="needs_location", message="no"))
    result = run_probe(_probe(), core, TODAY, git_commit=None)
    assert result.passed is False
    assert "status: expected results, got needs_location" in result.failures
    assert result.observed.failures == result.failures
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the runner**

```python
# src/swiss_grounding/evals/runner.py
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from swiss_grounding.evals.checker import check
from swiss_grounding.evals.probe_models import Observed, ObservedCitation, Probe
from swiss_grounding.locations.tree import LocationTree
from swiss_grounding.retrieval.models import QueryRequest, QueryResponse


class QueryCoreLike(Protocol):
    tree: LocationTree

    def query(self, request: QueryRequest) -> QueryResponse: ...


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    response: QueryResponse
    failures: tuple[str, ...]
    observed: Observed

    @property
    def passed(self) -> bool:
        return not self.failures


def to_request(probe: Probe) -> QueryRequest:
    return QueryRequest(
        question=probe.question, location=probe.location, categories=probe.categories,
        as_of=probe.as_of, limit=probe.limit,
    )


def _observed(resp: QueryResponse, failures: tuple[str, ...], git_commit: str | None) -> Observed:
    return Observed(
        recorded_at=datetime.now(UTC), git_commit=git_commit, status=resp.status,
        resolved_id=resp.resolved_location_id, method=resp.resolution_method,
        alternatives=resp.alternatives, message=resp.message,
        citations=tuple(
            ObservedCitation(source=c.source_id, extent=c.extent_id, url=c.url,
                             authority=c.authority, event_date=c.event_date)
            for c in resp.citations
        ),
        failures=failures,
    )


def run_probe(probe: Probe, core: QueryCoreLike, today: date, git_commit: str | None) -> ProbeResult:
    resp = core.query(to_request(probe))
    failures = check(probe, resp, core.tree, today)
    return ProbeResult(probe=probe, response=resp, failures=failures,
                       observed=_observed(resp, failures, git_commit))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_runner.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/runner.py tests/unit/evals/test_runner.py
git commit -m "feat: probe runner producing observed blocks"
```

---

## Task 10: Structural pytest harness

Parametrises every structural probe over the fixture corpus with the frozen clock. Red probes become strict expected failures, so a fix that makes one pass forces its `status` to be flipped to green.

**Files:**
- Create: `tests/integration/test_probes_structural.py`

- [ ] **Step 1: Write the harness**

```python
# tests/integration/test_probes_structural.py
"""Every structural probe, run on the fixture corpus with a frozen clock.

Red probes are strict xfails: when the fix pass makes one pass, pytest reports XPASS(strict)
as a failure, which is the signal to flip the probe's status to green in its YAML file."""
import os
from datetime import date
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes
from swiss_grounding.evals.runner import run_probe
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.locations.repository import load_tree, upsert_locations
from swiss_grounding.locations.resolver import LocationResolver
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder
from swiss_grounding.retrieval.query_core import QueryCore
from swiss_grounding.retrieval.rerank import RerankWeights

pytestmark = pytest.mark.integration
CORPUS = Path(__file__).parent.parent / "fixtures" / "probe_corpus.json"
FROZEN_TODAY = date(2026, 9, 16)


class NoGeo:
    """Structural probes never call GeoAdmin; anything not in the tree must be unresolvable."""

    def search_communes(self, text):
        return ()


@pytest.fixture(scope="module")
def core():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, CORPUS, FakeEmbedder(dim=8))
        tree = load_tree(conn)
    return QueryCore(
        database_url=url, tree=tree, resolver=LocationResolver(tree, NoGeo()),
        embedder=FakeEmbedder(dim=8), weights=RerankWeights(), today=lambda: FROZEN_TODAY,
    )


def _params():
    for tier, probe in load_all_probes(PROBE_DIR):
        if probe.kind != "structural":
            continue
        marks = [pytest.mark.xfail(strict=True, reason=f"red: {probe.failure_class}")] if probe.status == "red" else []
        yield pytest.param(probe, id=f"{tier}/{probe.id}", marks=marks)


@pytest.mark.parametrize("probe", list(_params()))
def test_structural_probe(core, probe):
    result = run_probe(probe, core, FROZEN_TODAY, git_commit=None)
    assert result.passed, "\n".join(result.failures)
```

- [ ] **Step 2: Run the harness**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_probes_structural.py -v`
Expected: every green probe passes and every red probe reports `XFAIL`. If a red probe reports `XPASS(strict)`, the probe is not actually red on fixtures: read its failure note, decide whether the expectation is wrong or the fixture makes it trivially pass, and fix the probe, not the code. If a green probe fails, the observed failure string tells you which expectation is wrong; adjust the probe's expectation or status only after confirming the behaviour against `CONTEXT.md`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_probes_structural.py
git commit -m "test: structural probe harness with strict xfail for red probes"
```

---

## Task 11: eval_run table and repository

**Files:**
- Modify: `src/swiss_grounding/db/schema.sql` (append)
- Create: `src/swiss_grounding/evals/eval_run_repository.py`
- Test: `tests/integration/test_eval_run_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_eval_run_repository.py
import os
from datetime import UTC, datetime

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.evals.eval_run_repository import insert_results, latest_run_summary
from swiss_grounding.evals.probe_models import Expectation, Observed, Probe
from swiss_grounding.evals.runner import ProbeResult
from swiss_grounding.retrieval.models import QueryResponse

pytestmark = pytest.mark.integration


def _result(pid: str, failures: tuple[str, ...]) -> ProbeResult:
    probe = Probe(id=pid, question="q", kind="structural", failure_class="none", status="green",
                  expect=Expectation(status="results"))
    obs = Observed(recorded_at=datetime.now(UTC), status="results", failures=failures)
    return ProbeResult(probe=probe, response=QueryResponse(status="results"), failures=failures, observed=obs)


def test_insert_and_summarise():
    url = os.environ["DATABASE_URL"]
    apply_schema(url, embedding_dim=8)
    with connect(url) as conn:
        conn.execute("truncate eval_run")
        insert_results(conn, run_id="r1", git_commit="abc", tier="city",
                       results=(_result("a", ()), _result("b", ("status: x",))))
        summary = latest_run_summary(conn)
    assert summary == {"run_id": "r1", "total": 2, "passed": 1, "failed": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_eval_run_repository.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Add the table and repository**

Append to `src/swiss_grounding/db/schema.sql`:

```sql
-- One row per probe per run. observed is the probe's Observed block as JSON.
create table if not exists eval_run (
    id             bigserial primary key,
    run_id         text not null,
    ran_at         timestamptz not null default now(),
    git_commit     text,
    tier           text not null,
    probe_id       text not null,
    kind           text not null,
    failure_class  text not null,
    passed         boolean not null,
    failures       jsonb not null default '[]',
    observed       jsonb not null default '{}'
);
create index if not exists eval_run_run_idx on eval_run(run_id, tier, probe_id);
```

```python
# src/swiss_grounding/evals/eval_run_repository.py
import json
from collections.abc import Sequence

import psycopg

from swiss_grounding.evals.runner import ProbeResult

INSERT = """
insert into eval_run (run_id, git_commit, tier, probe_id, kind, failure_class, passed, failures, observed)
values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
"""

SUMMARY = """
select run_id, count(*) as total, count(*) filter (where passed) as passed,
       count(*) filter (where not passed) as failed
from eval_run
where run_id = (select run_id from eval_run order by ran_at desc limit 1)
group by run_id
"""


def insert_results(conn: psycopg.Connection, run_id: str, git_commit: str | None, tier: str,
                   results: Sequence[ProbeResult]) -> None:
    for r in results:
        conn.execute(INSERT, (
            run_id, git_commit, tier, r.probe.id, r.probe.kind, r.probe.failure_class, r.passed,
            json.dumps(list(r.failures)), r.observed.model_dump_json(),
        ))


def latest_run_summary(conn: psycopg.Connection) -> dict | None:
    row = conn.execute(SUMMARY).fetchone()
    return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_eval_run_repository.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/db/schema.sql src/swiss_grounding/evals/eval_run_repository.py tests/integration/test_eval_run_repository.py
git commit -m "feat: eval_run table and repository"
```

---

## Task 12: Recorder

Writes an `observed` block back into the YAML file for each probe, preserving everything else. Uses a load-modify-dump on the parsed mapping, so comments are lost; probe notes live in the `note` field for that reason.

**Files:**
- Create: `src/swiss_grounding/evals/recorder.py`
- Test: `tests/unit/evals/test_recorder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_recorder.py
from datetime import UTC, datetime
from pathlib import Path

import yaml

from swiss_grounding.evals.probe_loader import load_probe_file
from swiss_grounding.evals.probe_models import Observed, ObservedCitation
from swiss_grounding.evals.recorder import record_observed

SRC = """
tier: city
probes:
  - id: city-001
    question: q
    location: "8003"
    kind: structural
    failure_class: none
    status: green
    expect:
      status: results
  - id: city-002
    question: q2
    kind: structural
    failure_class: none
    status: green
    expect:
      status: needs_location
"""


def test_record_observed_writes_block_for_matching_probe_only(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    obs = Observed(recorded_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC), git_commit="abc",
                   status="results", resolved_id="CH-ZH-261-K3", method="alias",
                   citations=(ObservedCitation(source="open_erz", extent="CH-ZH-261-K3",
                                               url="https://x", authority="official_info"),),
                   failures=())
    record_observed(path, {"city-001": obs})
    pf = load_probe_file(path)
    assert pf.probes[0].observed == obs
    assert pf.probes[1].observed is None
    raw = yaml.safe_load(path.read_text())
    assert raw["probes"][0]["observed"]["resolved_id"] == "CH-ZH-261-K3"
    assert raw["probes"][0]["expect"] == {"status": "results"}


def test_record_observed_replaces_previous_block(tmp_path: Path):
    path = tmp_path / "city.yaml"
    path.write_text(SRC)
    first = Observed(recorded_at=datetime(2026, 9, 16, tzinfo=UTC), status="results", failures=("a",))
    second = Observed(recorded_at=datetime(2026, 9, 17, tzinfo=UTC), status="results", failures=())
    record_observed(path, {"city-001": first})
    record_observed(path, {"city-001": second})
    assert load_probe_file(path).probes[0].observed == second
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_recorder.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the recorder**

```python
# src/swiss_grounding/evals/recorder.py
from collections.abc import Mapping
from pathlib import Path

import yaml

from swiss_grounding.evals.probe_models import Observed, ProbeFile


def _with_observed(probe_raw: dict, observed: Observed | None) -> dict:
    if observed is None:
        return probe_raw
    without = {k: v for k, v in probe_raw.items() if k != "observed"}
    return {**without, "observed": observed.model_dump(mode="json")}


def record_observed(path: Path, observed_by_id: Mapping[str, Observed]) -> None:
    """Rewrite the probe file with an observed block on each probe named in observed_by_id."""
    raw = yaml.safe_load(path.read_text())
    ProbeFile.model_validate(raw)
    updated = {
        **raw,
        "probes": [_with_observed(p, observed_by_id.get(p["id"])) for p in raw["probes"]],
    }
    ProbeFile.model_validate(updated)
    path.write_text(yaml.safe_dump(updated, sort_keys=False, allow_unicode=True, width=120))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_recorder.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/evals/recorder.py tests/unit/evals/test_recorder.py
git commit -m "feat: record observed probe results into YAML"
```

---

## Task 13: CLI `eval probes`

Runs probes against the live database with the configured embedder. Prints a table, writes `eval_run` rows, and with `--record` writes observed blocks into the YAML files.

**Files:**
- Create: `src/swiss_grounding/cli/eval_commands.py`
- Modify: `src/swiss_grounding/cli/main.py` (register the sub-app)
- Test: `tests/unit/test_cli_eval.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_cli_eval.py
from typer.testing import CliRunner

from swiss_grounding.cli.main import app


def test_eval_probes_command_is_registered():
    result = CliRunner().invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "probes" in result.output
    assert "judge" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli_eval.py -v`
Expected: FAIL, exit code 2 because `eval` is not a command

- [ ] **Step 3: Write the command module and register it**

```python
# src/swiss_grounding/cli/eval_commands.py
"""`swiss-grounding eval` commands: run probes against the live database, drive judge cases."""
import subprocess
import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path

import typer

from swiss_grounding.app import build_query_core
from swiss_grounding.config import load_settings
from swiss_grounding.db.connection import connect
from swiss_grounding.evals.eval_run_repository import insert_results
from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes, load_probe_file
from swiss_grounding.evals.recorder import record_observed
from swiss_grounding.evals.runner import ProbeResult, run_probe

eval_app = typer.Typer(help="Evaluation: probes and judge cases.")


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _print_table(results: list[tuple[str, ProbeResult]]) -> None:
    typer.echo(f"{'probe':<12} {'kind':<11} {'class':<26} {'status':<6} result")
    for tier, r in results:
        mark = "PASS" if r.passed else "FAIL"
        typer.echo(f"{r.probe.id:<12} {r.probe.kind:<11} {r.probe.failure_class:<26} {r.probe.status:<6} {mark}")
        for f in r.failures:
            typer.echo(f"    - {f}")


@eval_app.command("probes")
def probes_cmd(
    tier: str | None = typer.Option(None, "--tier", help="city, communes, or lookalikes"),
    kind: str | None = typer.Option(None, "--kind", help="structural or ranking"),
    record: bool = typer.Option(False, "--record", help="write observed blocks into the YAML files"),
    probe_dir: Path = typer.Option(PROBE_DIR, "--probe-dir"),
) -> None:
    """Run probes against the live database and store results in eval_run."""
    settings = load_settings()
    core = build_query_core(settings)
    commit = _git_commit()
    run_id = uuid.uuid4().hex[:12]
    selected = [
        (t, p) for t, p in load_all_probes(probe_dir)
        if (tier is None or t == tier) and (kind is None or p.kind == kind)
    ]
    results = [(t, run_probe(p, core, date.today(), git_commit=commit)) for t, p in selected]
    _print_table(results)
    by_tier: dict[str, list[ProbeResult]] = defaultdict(list)
    for t, r in results:
        by_tier[t].append(r)
    with connect(settings.database_url) as conn:
        for t, rs in by_tier.items():
            insert_results(conn, run_id=run_id, git_commit=commit, tier=t, results=rs)
    if record:
        for t, rs in by_tier.items():
            path = probe_dir / f"{t}.yaml"
            record_observed(path, {r.probe.id: r.observed for r in rs})
        typer.echo(f"observed blocks written to {probe_dir}")
    passed = sum(1 for _, r in results if r.passed)
    typer.echo(f"\nrun {run_id} ({commit}): {passed}/{len(results)} passed")
    unexpected = [r.probe.id for _, r in results if r.passed == (r.probe.status == "red")]
    if unexpected:
        typer.echo(f"status mismatch (red passing or green failing): {unexpected}")
        raise typer.Exit(code=3)


@eval_app.command("judge")
def judge_cmd(
    models: str = typer.Option("claude-fable-5-1,claude-opus-5,claude-sonnet-5,claude-haiku-4-5-20251001", "--models"),
    out: Path = typer.Option(Path("evals/judge/results.json"), "--out"),
    probe_dir: Path = typer.Option(PROBE_DIR, "--probe-dir"),
) -> None:
    """Answer every judge case with each model via claude -p and grade with a fixed Fable judge."""
    from swiss_grounding.evals.judge_harness import run_judge_suite

    cases = [p for _, p in load_all_probes(probe_dir) if p.judge]
    table = run_judge_suite(cases, tuple(models.split(",")), out)
    typer.echo(table)
```

In `src/swiss_grounding/cli/main.py`, after `sources_app` is registered:

```python
from swiss_grounding.cli.eval_commands import eval_app

app.add_typer(eval_app, name="eval")
```

`load_probe_file` is imported for the recorder's benefit; remove the import if ruff flags it unused.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli_eval.py -v && uv run ruff check src`
Expected: 1 passed, ruff clean. `judge_harness` does not exist yet; the import is inside the command body so `--help` works.

- [ ] **Step 5: Commit**

```bash
git add src/swiss_grounding/cli/eval_commands.py src/swiss_grounding/cli/main.py tests/unit/test_cli_eval.py
git commit -m "feat: eval probes CLI writing eval_run and observed blocks"
```

---

## Task 14: Record the red set against the live database

This is the deliverable of the collect phase: every probe's observed block, taken from the real server state on the day.

**Files:**
- Modify: `evals/probes/city.yaml`, `evals/probes/communes.yaml`, `evals/probes/lookalikes.yaml`

- [ ] **Step 1: Confirm the live database and embedder are configured**

Run: `uv run swiss-grounding query "When is cardboard collected?" --location 8003 --categories waste | head -5`
Expected: `status: results` and a location line naming District 3. If it prints `needs_location` or fails to connect, fix `.env` before continuing; the recorded set must come from the real corpus with bge-m3.

- [ ] **Step 2: Run all probes with recording**

Run: `uv run swiss-grounding eval probes --record`
Expected: a table of all 47 probes. Exit code 3 is expected if any probe's red or green status disagrees with the live result. The output lists them under "status mismatch".

- [ ] **Step 3: Reconcile status mismatches**

For each probe in the mismatch list:

- A red probe that passes live: check its `note`. If the expectation is genuinely met today, set `status: green`. If it passes for an accidental reason (for example, no citations at all so `must_exclude` is vacuously true), tighten the expectation with a `must_include` so it fails honestly.
- A green probe that fails live: read the observed failures. If the failure reflects a real defect, set `status: red` and change `failure_class` from `none` to the matching class. If the expectation was wrong, fix the expectation.

Never change code in this step.

- [ ] **Step 4: Re-run until the exit code is 0**

Run: `uv run swiss-grounding eval probes --record; echo exit=$?`
Expected: `exit=0`, and every probe now has an `observed` block.

- [ ] **Step 5: Run the structural harness on fixtures too**

Run: `DATABASE_URL=postgresql://localhost/swiss_grounding uv run pytest tests/integration/test_probes_structural.py -q`
Expected: no failures, no XPASS(strict). A probe can be red live and green on fixtures only if the fixture corpus is shaped differently from the live corpus; when that happens, prefer changing the fixture to match the live defect so the probe is red in both places.

- [ ] **Step 6: Commit the recorded red set**

```bash
git add evals/probes/
git commit -m "docs: record observed behaviour for the Zurich probe red set"
```

---

## Task 15: Judge harness

Drives Claude Code headless for each judge case and answering model, captures the tool results from the stream, and asks a fixed Fable judge for seven pass or fail verdicts.

**Files:**
- Create: `evals/judge/mcp.json`
- Create: `evals/judge/rubric.md`
- Create: `src/swiss_grounding/evals/judge_harness.py`
- Test: `tests/unit/evals/test_judge_harness.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/evals/test_judge_harness.py
import json

from swiss_grounding.evals.judge_harness import (
    VERDICT_KEYS, build_judge_prompt, extract_tool_results, parse_verdict, summary_table,
)


def test_extract_tool_results_from_stream_json():
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "{\"status\": \"results\"}"}]}
        ]}}),
        json.dumps({"type": "result", "result": "final answer"}),
    ]
    tool_results, final = extract_tool_results("\n".join(lines))
    assert tool_results == ['{"status": "results"}']
    assert final == "final answer"


def test_parse_verdict_reads_json_object_anywhere_in_text():
    text = "Here is my grading:\n```json\n" + json.dumps({k: True for k in VERDICT_KEYS}) + "\n```"
    verdict = parse_verdict(text)
    assert all(verdict[k] is True for k in VERDICT_KEYS)


def test_parse_verdict_missing_key_is_false():
    verdict = parse_verdict(json.dumps({"jurisdiction_confusion": True}))
    assert verdict["jurisdiction_confusion"] is True
    assert verdict["coverage_signal_repeated"] is False


def test_build_judge_prompt_includes_question_evidence_and_answer():
    prompt = build_judge_prompt("rubric {question} {evidence} {answer}", "Q?", ["E1", "E2"], "A.")
    assert "Q?" in prompt and "E1" in prompt and "E2" in prompt and "A." in prompt


def test_summary_table_one_row_per_model():
    verdicts = {
        "claude-sonnet-5": [{k: True for k in VERDICT_KEYS}, {**{k: True for k in VERDICT_KEYS}, "url_grounded": False}],
    }
    table = summary_table(verdicts)
    assert "claude-sonnet-5" in table
    assert "url_grounded" in table
    assert "1/2" in table
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/evals/test_judge_harness.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the config, rubric, and harness**

```json
// evals/judge/mcp.json
{
  "mcpServers": {
    "swiss-grounding": {
      "command": "uv",
      "args": ["run", "swiss-grounding", "serve"]
    }
  }
}
```

```markdown
<!-- evals/judge/rubric.md -->
You are grading an answer produced by a language model that had access to a Swiss public-information search tool.
Grade only against the evidence the tool returned. Do not use your own knowledge of Swiss law.

Question asked by the user:
{question}

Evidence the tool returned (raw JSON, one block per call):
{evidence}

Final answer given by the model:
{answer}

For each key below, output true when the answer PASSES the check and false when it FAILS.

- jurisdiction_confusion: the answer does not present evidence from another jurisdiction as applying to the asked place.
- authority_hierarchy: the answer does not present lower-authority guidance as overriding law, or the reverse.
- temporal_misapplication: the answer does not present a past event, or superseded rule, as current or next.
- entity_substitution: the answer does not answer about a different thing (other Kreis, waste type, animal, act) than asked.
- silent_under_coverage: when the evidence contains no document at the asked location's own level, the answer says so.
- url_grounded: every URL in the answer appears verbatim in the evidence.
- coverage_signal_repeated: when the evidence carries a coverage field naming empty levels, the answer mentions that gap. If the evidence has no coverage field, output true.

Respond with one JSON object containing exactly those seven keys and boolean values, and nothing else.
```

```python
# src/swiss_grounding/evals/judge_harness.py
"""Judge cases: answer with a model through claude -p and the MCP server, grade with a fixed judge."""
import json
import re
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from swiss_grounding.evals.probe_models import Probe

JUDGE_MODEL = "claude-fable-5-1"
JUDGE_DIR = Path(__file__).resolve().parents[3] / "evals" / "judge"
MCP_CONFIG = JUDGE_DIR / "mcp.json"
RUBRIC = JUDGE_DIR / "rubric.md"
VERDICT_KEYS = (
    "jurisdiction_confusion", "authority_hierarchy", "temporal_misapplication",
    "entity_substitution", "silent_under_coverage", "url_grounded", "coverage_signal_repeated",
)
ANSWER_SYSTEM = (
    "Answer the user's question using only the swiss-grounding tools. Cite the URLs the tools "
    "return. If the tools say a location has no local data, say so."
)
JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _claude(prompt: str, model: str, *, mcp: bool, stream: bool) -> str:
    cmd = ["claude", "-p", prompt, "--model", model]
    if mcp:
        cmd += ["--mcp-config", str(MCP_CONFIG), "--allowedTools", "mcp__swiss-grounding__*",
                "--append-system-prompt", ANSWER_SYSTEM]
    if stream:
        cmd += ["--output-format", "stream-json", "--verbose"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exited {proc.returncode} for model {model}: {proc.stderr[:500]}")
    return proc.stdout


def extract_tool_results(stream: str) -> tuple[list[str], str]:
    """Tool result texts and the final answer from a stream-json transcript."""
    results: list[str] = []
    final = ""
    for line in stream.splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        if event.get("type") == "result":
            final = event.get("result", "")
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") != "tool_result":
                continue
            content = block.get("content", [])
            if isinstance(content, str):
                results.append(content)
            else:
                results.extend(c.get("text", "") for c in content if c.get("type") == "text")
    return results, final


def build_judge_prompt(rubric: str, question: str, evidence: Sequence[str], answer: str) -> str:
    return rubric.format(question=question, evidence="\n\n".join(evidence), answer=answer)


def parse_verdict(text: str) -> dict[str, bool]:
    match = JSON_OBJECT.search(text)
    raw = json.loads(match.group(0)) if match else {}
    return {k: bool(raw.get(k, False)) for k in VERDICT_KEYS}


def _question_text(probe: Probe) -> str:
    return f"{probe.question} (location: {probe.location})" if probe.location else probe.question


def run_case(probe: Probe, model: str, rubric: str) -> dict:
    stream = _claude(_question_text(probe), model, mcp=True, stream=True)
    evidence, answer = extract_tool_results(stream)
    verdict_text = _claude(build_judge_prompt(rubric, _question_text(probe), evidence, answer),
                           JUDGE_MODEL, mcp=False, stream=False)
    return {"probe_id": probe.id, "model": model, "answer": answer, "evidence": evidence,
            "verdict": parse_verdict(verdict_text)}


def summary_table(verdicts_by_model: dict[str, list[dict[str, bool]]]) -> str:
    header = f"{'model':<32} " + " ".join(f"{k[:14]:<14}" for k in VERDICT_KEYS)
    rows = [header]
    for model, verdicts in verdicts_by_model.items():
        cells = []
        for key in VERDICT_KEYS:
            passed = sum(1 for v in verdicts if v.get(key))
            cells.append(f"{passed}/{len(verdicts)}".ljust(14))
        rows.append(f"{model:<32} " + " ".join(cells))
    return "\n".join(rows)


def run_judge_suite(cases: Sequence[Probe], models: Sequence[str], out: Path) -> str:
    rubric = RUBRIC.read_text()
    records = [run_case(p, m, rubric) for m in models for p in cases]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ran_at": datetime.now(UTC).isoformat(), "judge": JUDGE_MODEL,
                               "records": records}, indent=2, ensure_ascii=False))
    by_model: dict[str, list[dict[str, bool]]] = {m: [] for m in models}
    for r in records:
        by_model[r["model"]].append(r["verdict"])
    return summary_table(by_model)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/evals/test_judge_harness.py -v`
Expected: 5 passed

- [ ] **Step 5: Smoke-run one case manually**

Run: `claude -p "When is the next cardboard collection? (location: 8003)" --model claude-sonnet-5 --mcp-config evals/judge/mcp.json --allowedTools "mcp__swiss-grounding__*" --output-format stream-json --verbose | tail -1`
Expected: a JSON line with `"type": "result"`. If the MCP server fails to start, check that `uv run swiss-grounding serve` works from the repo root, because `claude -p` inherits the current directory.

- [ ] **Step 6: Commit**

```bash
git add evals/judge/ src/swiss_grounding/evals/judge_harness.py tests/unit/evals/test_judge_harness.py
git commit -m "feat: judge harness driving claude -p per model with a fixed Fable judge"
```

---

## Task 16: Baseline judge run

**Files:**
- Create: `evals/judge/results.json` (generated)

- [ ] **Step 1: Run the suite**

Run: `uv run swiss-grounding eval judge`
Expected: a table with four model rows and seven columns, each cell `passed/15`. This runs 60 answering calls and 60 judge calls; expect several minutes.

- [ ] **Step 2: Sanity-check three records by hand**

Open `evals/judge/results.json`, pick city-002, com-001, and look-001 for one model, and confirm the verdicts match what you would say reading the answer against the evidence. If the judge is wrong in a consistent way, sharpen the wording in `evals/judge/rubric.md` and re-run.

- [ ] **Step 3: Commit**

```bash
git add evals/judge/results.json
git commit -m "docs: baseline judge results across four models on the red set"
```

---

## Task 17: README section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the section**

Append to `README.md`:

```markdown
## Evals

Probes are hand-written adversarial questions under `evals/probes/`, one YAML file per location tier. Each probe states the expected tool response and, once recorded, the observed one. `status: red` marks a probe the server fails today. See `CONTEXT.md` for the failure classes and `docs/adr/` for the decisions behind the expectations.

    uv run pytest tests/integration/test_probes_structural.py   # structural probes on fixtures, frozen clock
    uv run swiss-grounding eval probes --record                  # all probes on the live database, writes observed blocks
    uv run swiss-grounding eval judge                            # judge cases across models, needs the claude CLI

Red probes run as strict expected failures. When a fix makes one pass, pytest reports it and the probe's `status` must be flipped to green.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: eval probes and judge cases"
```

---

## Self-review notes

- **Spec coverage.** Five failure classes: each appears in at least one probe (`test_every_failure_class_is_probed`). Coverage signal: checker reads `coverage`, probes assert it. Commune register: tier 2 expects municipality under `CH-ZH` by label. Calendar ordering: `first_event: nearest_future`. Evidence by source, URL, extent: `EvidenceRule` has no id field. Structural versus ranking split: pytest harness filters `kind == structural`; CLI runs both. Judge: harness with seven pass or fail keys and a fixed judge. Collect-first: no task modifies resolver, narrowing, or ranking; Task 4 only adds an injectable clock.
- **city-018 note wording** is muddled. The intended rule: when `as_of` is set, `nearest_future` is evaluated against `as_of` rather than today. The checker as written uses `today` only. Decide during Task 14 whether to pass `probe.as_of or today` into the checker's date; if so, change `run_probe` to `check(probe, resp, core.tree, probe.as_of or today)` and add a unit test for it in `test_runner.py`.
- **Verified before execution.** `Level` is a `StrEnum` whose values are `country`, `canton`, `municipality`, `neighborhood`, so `node.level.value` in `_check_resolved` is correct. The seed generates exactly the Quartier ids the probes use: `CH-ZH-261-K1-CITY`, `CH-ZH-261-K3-ALT-WIEDIKON`, `CH-ZH-261-K4-HARD`, `CH-ZH-261-K5-ESCHER-WYSS`, `CH-ZH-261-K8-SEEFELD`, `CH-ZH-261-K11-AFFOLTERN`. `Location.label("en")` falls back to the German name, so label matching works for Quartiere and for register communes that carry only a German name.
```
