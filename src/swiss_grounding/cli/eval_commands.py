"""`swiss-grounding eval` commands: run probes against the live database, drive judge cases."""
import subprocess
import uuid
from collections import defaultdict
from collections.abc import Sequence
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
    """Run probes against the live database and store results in eval_run.

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
    with connect(settings.database_url) as conn:
        for t, rs in grouped.items():
            insert_results(conn, run_id=run_id, git_commit=commit, tier=t, results=rs)
    if record:
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
