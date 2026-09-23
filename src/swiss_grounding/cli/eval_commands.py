"""`swiss-grounding eval` commands: run probes against the live database, drive judge cases."""
import subprocess
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import typer

from swiss_grounding.app import build_query_core
from swiss_grounding.config import load_settings
from swiss_grounding.db.connection import connect
from swiss_grounding.evals.eval_run_repository import insert_results
from swiss_grounding.evals.probe_loader import PROBE_DIR, load_all_probes
from swiss_grounding.evals.probe_models import Probe, Tier
from swiss_grounding.evals.recorder import record_observed
from swiss_grounding.evals.runner import ProbeResult, run_probe

eval_app = typer.Typer(help="Evaluation: probes and judge cases.")

DEFAULT_MODELS = "claude-fable-5-1,claude-opus-5,claude-sonnet-5,claude-haiku-4-5-20251001"
DEFAULT_JUDGE_OUT = Path("evals/judge/results.json")
GOLDEN_RUNS = Path("evals/golden/runs")
LABELS_PATH = Path("evals/golden/labels.jsonl")
LABEL_BUDGET_USD = 2.0
LOW_RANK_SAMPLE = 5
REVIEW_PATH = Path("evals/golden/label_review.csv")
EXIT_STATUS_MISMATCH = 3
RUN_ID_LENGTH = 12
SWISS_TZ = ZoneInfo("Europe/Zurich")

TierResults = Sequence[tuple[str, ProbeResult]]


class TierOption(str, Enum):
    city = "city"
    communes = "communes"
    lookalikes = "lookalikes"


class KindOption(str, Enum):
    structural = "structural"
    ranking = "ranking"


def _today() -> date:
    """Civil date in Switzerland; calendar evidence is dated in local time."""
    return datetime.now(SWISS_TZ).date()


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _load_probes_or_exit(probe_dir: Path) -> tuple[tuple[Tier, Probe], ...]:
    try:
        return load_all_probes(probe_dir)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _print_table(results: TierResults) -> None:
    typer.echo(f"{'probe':<12} {'kind':<11} {'class':<26} {'status':<6} result")
    for _tier, r in results:
        mark = "PASS" if r.passed else "FAIL"
        typer.echo(f"{r.probe.id:<12} {r.probe.kind:<11} {r.probe.failure_class:<26} "
                   f"{r.probe.status:<6} {mark}")
        for f in r.failures:
            typer.echo(f"    - {f}")


def _status_mismatches(results: TierResults) -> list[str]:
    """Probe ids whose recorded status disagrees with the live outcome."""
    return [r.probe.id for _, r in results if r.passed == (r.probe.status == "red")]


def _by_tier(results: TierResults) -> dict[str, list[ProbeResult]]:
    grouped: dict[str, list[ProbeResult]] = defaultdict(list)
    for tier, r in results:
        grouped[tier].append(r)
    return dict(grouped)


@eval_app.command("probes")
def probes_cmd(
    tier: Annotated[
        TierOption | None, typer.Option("--tier", help="city, communes, or lookalikes")
    ] = None,
    kind: Annotated[
        KindOption | None, typer.Option("--kind", help="structural or ranking")
    ] = None,
    record: bool = typer.Option(
        False, "--record", help="write observed blocks into the YAML files"
    ),
    probe_dir: Annotated[Path, typer.Option("--probe-dir")] = PROBE_DIR,
) -> None:
    """Run probes against the live database; with --record, store results in eval_run and write observed blocks.

    Exit code 3 when a probe's red/green status disagrees with the live result.
    """
    all_probes = _load_probes_or_exit(probe_dir)
    selected = [
        (t, p) for t, p in all_probes
        if (tier is None or t == tier.value) and (kind is None or p.kind == kind.value)
    ]
    if (tier is not None or kind is not None) and not selected:
        typer.echo("no probes match --tier/--kind", err=True)
        raise typer.Exit(code=1)
    settings = load_settings()
    # The reranker must judge "past" with the same civil date the checker uses.
    core = build_query_core(settings, today=_today)
    commit = _git_commit()
    run_id = uuid.uuid4().hex[:RUN_ID_LENGTH]
    today = _today()
    results = [(t, run_probe(p, core, today, git_commit=commit)) for t, p in selected]
    _print_table(results)
    grouped = _by_tier(results)
    if record:
        with connect(settings.database_url) as conn:
            for t, rs in grouped.items():
                insert_results(conn, run_id=run_id, git_commit=commit, tier=t, results=rs)
        for t, rs in grouped.items():
            # Probe files are named after their tier (city.yaml, communes.yaml, lookalikes.yaml); see README.
            record_observed(probe_dir / f"{t}.yaml", {r.probe.id: r.observed for r in rs})
        typer.echo(f"observed blocks written to {probe_dir}")
    passed = sum(1 for _, r in results if r.passed)
    typer.echo(f"\nrun {run_id} ({commit}): {passed}/{len(results)} passed")
    mismatches = _status_mismatches(results)
    if mismatches:
        typer.echo(f"status mismatch (red passing or green failing): {mismatches}")
        raise typer.Exit(code=EXIT_STATUS_MISMATCH)


@eval_app.command("judge")
def judge_cmd(
    models: str = typer.Option(DEFAULT_MODELS, "--models", help="comma-separated model ids"),
    out: Annotated[Path, typer.Option("--out")] = DEFAULT_JUDGE_OUT,
    probe_dir: Annotated[Path, typer.Option("--probe-dir")] = PROBE_DIR,
    resume: Annotated[bool, typer.Option("--resume", help="keep clean records in --out, rerun the rest")] = False,
) -> None:
    """Answer every judge case with each model via claude -p and grade with a fixed Fable judge."""
    from swiss_grounding.evals.judge_harness import run_judge_suite

    all_probes = _load_probes_or_exit(probe_dir)
    cases = [p for _, p in all_probes if p.judge]
    table = run_judge_suite(cases, tuple(m.strip() for m in models.split(",")), out, resume=resume)
    typer.echo(table)


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


@eval_app.command("label")
def label_cmd(confirm_spend: bool = typer.Option(False, "--confirm-spend", help="required: calls gpt-5-mini"),
              top: int = typer.Option(10, "--top")) -> None:
    """Judge the top citations of every results probe with gpt-5-mini; write evals/golden/labels.jsonl."""
    import csv
    import json
    import random

    from swiss_grounding.app import build_search_service
    from swiss_grounding.corpus.budget import ensure_within, record_spend
    from swiss_grounding.corpus.providers import OpenAILLM
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.golden_runner import citation_key
    from swiss_grounding.evals.labels import LABEL_KIND, judge_pairs, sample_for_review
    from swiss_grounding.serving.models import MAX_LIMIT, SearchRequest
    from swiss_grounding.serving.relevance import ProvisionalRelevance

    if not confirm_spend:
        typer.echo("This calls gpt-5-mini (about $0.30 for 1,500 pairs). Re-run with --confirm-spend.", err=True)
        raise typer.Exit(code=1)
    settings = load_settings()
    # Threshold 0 so pairs below the provisional threshold are judged too: the fitted model must learn
    # where abstention is decided. Top `top` per place, plus a random sample of the ranks below.
    service = replace(build_search_service(settings, today=_today), relevance=ProvisionalRelevance(0.0))
    rng = random.Random(20260924)
    pairs = []
    for probe in load_golden().probes:
        if probe.expect.status != "results" or probe.tool != "swiss_search":
            continue
        resp = service.search(SearchRequest(probe.question, probe.locations, {}, None, MAX_LIMIT))
        for place in resp.places:
            ranked = list(place.citations)
            chosen = ranked[:top] + rng.sample(ranked[top:], min(LOW_RANK_SAMPLE, len(ranked[top:])))
            pairs.extend({"probe_id": probe.id, "key": citation_key(c), "question": probe.question,
                          "passage": f"{' › '.join(c.breadcrumb)}\n{c.passage}"} for c in chosen)
    done = _load_labels(LABELS_PATH)
    todo = [p for p in pairs if (p["probe_id"], p["key"]) not in done]
    with connect(settings.database_url) as conn:
        ensure_within(conn, estimate=0.0005 * len(todo), total_cap=settings.corpus_budget_usd,
                      kind=LABEL_KIND, kind_cap=LABEL_BUDGET_USD)

    def spend(usd: float) -> None:        # its own short transaction: a later failure cannot roll it back
        with connect(settings.database_url) as c:
            record_spend(c, kind=LABEL_KIND, model=settings.corpus_doc_model, usd=usd, input_tokens=0,
                         output_tokens=0, estimated=False)

    with LABELS_PATH.open("a", encoding="utf-8") as f:
        def append(row: dict) -> None:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
        rows = judge_pairs(todo, OpenAILLM(settings.openai_api_key), model=settings.corpus_doc_model,
                           on_usage=spend, on_row=append)
    review = sample_for_review(rows, 100, seed=20260924)
    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["probe_id", "key", "question", "passage", "model_says", "human_says"])
        writer.writerows([r["probe_id"], r["key"], r["question"], r["passage"][:300], r["relevant"], ""]
                         for r in review)
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
