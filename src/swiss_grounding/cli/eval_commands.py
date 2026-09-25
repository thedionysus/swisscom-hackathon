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
LABEL_SEED = 20260924
REVIEW_PATH = Path("evals/golden/label_review.csv")
GENERATE_BUDGET_USD = 2.0
GENERATE_SEED = 20260924
GENERATED_PATH = Path("evals/generated/questions.jsonl")
FAITHFULNESS_OUT = Path("evals/judge/faithfulness.jsonl")
FAITHFULNESS_RUBRIC = Path("evals/judge/faithfulness.md")
FAITHFULNESS_MCP_CONFIG = Path("evals/judge/mcp-http.json")
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


def _eval_llm_or_exit(settings):
    from swiss_grounding.corpus.llm_factory import eval_llm
    try:
        return eval_llm(settings)
    except ValueError as exc:
        typer.echo(f"refused: {exc}", err=True)
        raise typer.Exit(code=1) from exc


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
    """Run the golden set; print per-probe results and the summary against the pass thresholds."""
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
def label_cmd(confirm_spend: bool = typer.Option(
                  False, "--confirm-spend", help="required: calls the EVAL_LLM_PROVIDER model"),
              top: int = typer.Option(10, "--top")) -> None:
    """Judge the top citations of every results probe with the eval model; write evals/golden/labels.jsonl."""
    import csv
    import json
    import random

    from swiss_grounding.app import build_search_service
    from swiss_grounding.corpus.budget import ensure_within, record_spend
    from swiss_grounding.corpus.llm_factory import eval_model
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.golden_runner import citation_key
    from swiss_grounding.evals.labels import LABEL_KIND, judge_pairs, sample_for_review
    from swiss_grounding.serving.models import MAX_LIMIT, SearchRequest
    from swiss_grounding.serving.relevance import ProvisionalRelevance

    settings = load_settings()
    model = eval_model(settings)
    if not confirm_spend:
        typer.echo(f"This calls {model} (about 1,500 pairs). Re-run with --confirm-spend.", err=True)
        raise typer.Exit(code=1)
    llm, model = _eval_llm_or_exit(settings)
    # Threshold 0 so pairs below the provisional threshold are judged too: the fitted model must learn
    # where abstention is decided. Top `top` per place, plus a random sample of the ranks below.
    service = replace(build_search_service(settings, today=_today), relevance=ProvisionalRelevance(0.0))
    rng = random.Random(LABEL_SEED)
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
            record_spend(c, kind=LABEL_KIND, model=model, usd=usd, input_tokens=0,
                         output_tokens=0, estimated=False)

    with LABELS_PATH.open("a", encoding="utf-8") as f:
        def append(row: dict) -> None:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
        rows = judge_pairs(todo, llm, model=model, on_usage=spend, on_row=append)
    review = sample_for_review(rows, 100, seed=LABEL_SEED)
    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["probe_id", "key", "question", "passage", "model_says", "human_says"])
        writer.writerows([r["probe_id"], r["key"], r["question"], r["passage"][:300], r["relevant"], ""]
                         for r in review)
    typer.echo(f"{len(rows)} pairs judged; fill the human_says column of {REVIEW_PATH} (true/false), "
               "then run `eval label-check`.")


@eval_app.command("label-check")
def label_check_cmd() -> None:
    """Agreement between the model judge and the human-checked sample; must be ≥ 0.85."""
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


@eval_app.command("generate")
def generate_cmd(confirm_spend: bool = typer.Option(
                     False, "--confirm-spend", help="required: calls the EVAL_LLM_PROVIDER model"),
                 per_stratum: int = typer.Option(35, "--per-stratum")) -> None:
    """The eval model writes one question per sampled chunk; used for recall@5 only."""
    import json

    from swiss_grounding.corpus.budget import ensure_within, record_spend
    from swiss_grounding.corpus.llm_factory import eval_model
    from swiss_grounding.evals.generate import GENERATE_KIND, SAMPLE_SQL, generate_questions

    settings = load_settings()
    model = eval_model(settings)
    if not confirm_spend:
        typer.echo(f"This calls {model}. Re-run with --confirm-spend.", err=True)
        raise typer.Exit(code=1)
    llm, model = _eval_llm_or_exit(settings)
    with connect(settings.database_url) as conn:
        chunks = conn.execute(SAMPLE_SQL, {"seed": GENERATE_SEED, "per_stratum": per_stratum}).fetchall()
        ensure_within(conn, estimate=0.0005 * len(chunks), total_cap=settings.corpus_budget_usd,
                      kind=GENERATE_KIND, kind_cap=GENERATE_BUDGET_USD)

    def spend(usd: float) -> None:        # its own short transaction: a later failure cannot roll it back
        with connect(settings.database_url) as c:
            record_spend(c, kind=GENERATE_KIND, model=model, usd=usd, input_tokens=0,
                         output_tokens=0, estimated=False)

    GENERATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GENERATED_PATH.open("w", encoding="utf-8") as f:
        rows = generate_questions(chunks, llm, model=model, on_usage=spend)
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
    typer.echo(f"{len(rows)} questions written to {GENERATED_PATH}")


@eval_app.command("recall")
def recall_cmd(path: Annotated[Path, typer.Option("--path")] = GENERATED_PATH) -> None:
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


@eval_app.command("faithfulness")
def faithfulness_cmd(model: str = typer.Option("claude-sonnet-5", "--model"),
                     split: str = typer.Option("holdout", "--split"),
                     parallel: int = typer.Option(4, "--parallel"),
                     out: Annotated[Path, typer.Option("--out")] = FAITHFULNESS_OUT) -> None:
    """Answer golden probes through the MCP with `claude -p` and grade faithfulness (target 0.9).

    Start the server once first: `uv run swiss-grounding serve --transport http` (one model load for the
    whole run); evals/judge/mcp-http.json points claude at it. Resumable: finished ids in --out are skipped.
    Errors and unparsed verdicts count as failures."""
    import json
    from concurrent.futures import ThreadPoolExecutor

    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.evals.judge_harness import run_question

    rubric = FAITHFULNESS_RUBRIC.read_text(encoding="utf-8")
    done = {json.loads(x)["id"] for x in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    probes = [p for p in load_golden().probes if split in ("all", p.split) and p.id not in done]

    def one(p) -> dict:
        question = p.question if not p.locations else f"{p.question} ({', '.join(p.locations)})"
        return run_question(question, p.id, model, rubric, mcp_config=FAITHFULNESS_MCP_CONFIG)

    out.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=parallel) as pool, out.open("a", encoding="utf-8") as f:
        for record in pool.map(one, probes):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
    records = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    passed = sum(1 for r in records if r["verdict_parsed"] and r["verdict"].get("faithful"))
    failed_to_run = sum(1 for r in records if r["error"] or not r["verdict_parsed"])
    typer.echo(f"faithfulness {passed / len(records):.3f} over {len(records)} answers "
               f"({failed_to_run} errors or unparsed, counted as failures)")


@eval_app.command("fit")
def fit_cmd() -> None:
    """Fit the relevance probability on dev labels; threshold from out-of-fold dev; report on holdout."""
    import numpy as np

    from swiss_grounding.app import build_search_service, relevance_path
    from swiss_grounding.evals.fit import (
        TARGET_PRECISION,
        check_training_labels,
        choose_threshold,
        fit_model,
        out_of_fold_probabilities,
        write_model,
    )
    from swiss_grounding.evals.golden_models import load_golden
    from swiss_grounding.serving.models import SearchRequest
    from swiss_grounding.serving.relevance import ProvisionalRelevance

    settings = load_settings()
    base = build_search_service(settings, today=_today)
    service = replace(base, relevance=ProvisionalRelevance(threshold=0.0))  # keep every candidate
    labels = _load_labels(LABELS_PATH)
    rows: dict[str, list[tuple[tuple[float, ...], bool]]] = {"dev": [], "holdout": []}
    for probe in load_golden().probes:
        if probe.expect.status != "results" or probe.tool != "swiss_search":
            continue
        for features, key in service.scored_for_eval(SearchRequest(probe.question, probe.locations, {}, None, 10)):
            if (probe.id, key) in labels:
                rows[probe.split].append((features, labels[(probe.id, key)]))
    y_dev_list = [r[1] for r in rows["dev"]]
    try:
        check_training_labels(y_dev_list)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    x_dev = np.array([r[0] for r in rows["dev"]])
    y_dev = np.array(y_dev_list)
    weights, bias = fit_model(x_dev, y_dev)
    threshold = choose_threshold(list(out_of_fold_probabilities(x_dev, y_dev)), list(y_dev), TARGET_PRECISION)
    z = np.array([bias + float(np.dot(weights, r[0])) for r in rows["holdout"]])
    kept = [label for p, (_, label) in zip(1 / (1 + np.exp(-z)), rows["holdout"], strict=True) if p >= threshold]
    positives = sum(label for _, label in rows["holdout"])
    precision = sum(kept) / len(kept) if kept else float("nan")
    recall = sum(kept) / positives if positives else float("nan")
    out = relevance_path(settings, base.reranker.name)
    write_model(out, weights=weights, bias=bias, threshold=float(threshold), reranker=base.reranker.name,
                meta={"dev_pairs": len(rows["dev"]), "holdout_pairs": len(rows["holdout"]),
                      "holdout_precision": precision, "holdout_recall": recall,
                      "dataset_version": load_golden().version, "git_commit": _git_commit()})
    typer.echo(f"{base.reranker.name}: fitted on {len(rows['dev'])} dev pairs, threshold {threshold:.3f}; "
               f"holdout precision {precision:.3f}, recall {recall:.3f}; wrote {out}")
