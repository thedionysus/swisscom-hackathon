"""`swiss-grounding corpus run`: the whole paid + local run in one resumable command.

Order: OCR -> describe docs -> describe chunks (repeated while a pass describes something and tasks remain:
duplicate align_keys need a second pass) -> embed every index in CORPUS_INDEXES (local first) -> build their
HNSW indexes. It reuses the stage internals of `corpus_commands`, so each stage first collects its own
unfinished batches and skips finished work: re-running `corpus run` continues where the last one stopped.

Budget: a paid stage that does not fit what is left of the cap runs only the tasks that fit (none: it is
skipped with a note). If descriptions stop for lack of budget, the indexes are built over every chunk anyway
(`require_description=False`); those chunks are re-embedded automatically once described. A paid index that
does not fit is skipped with a note.
"""
from dataclasses import dataclass

import typer

from swiss_grounding.cli import corpus_commands as cc
from swiss_grounding.cli.corpus_commands import (
    ALLOW_FAKE_HELP,
    add_reports,
    corpus_app,
    empty_report,
)
from swiss_grounding.cli.corpus_source_commands import friendly_errors, usd
from swiss_grounding.config import Settings, load_settings
from swiss_grounding.corpus.budget import SYNC_MULTIPLIER, BudgetExceeded, remaining_budget, spent
from swiss_grounding.corpus.ocr import estimate_ocr, run_ocr
from swiss_grounding.corpus.providers import INDEXES, IndexSpec
from swiss_grounding.db.connection import connect

MAX_DESCRIBE_PASSES = 5
DESCRIBE_STEPS = ("docs", "chunks")
LIVE_CHUNKS = "status in ('current','scheduled')"


@dataclass(frozen=True)
class StageResult:
    name: str
    report: dict[str, int] | None = None     # done / failed / skipped / refused (tasks left for lack of budget)
    written: int | None = None                # embed stages
    note: str = ""

    @property
    def skipped(self) -> bool:
        return self.note.startswith("skipped")

    def line(self) -> str:
        if self.report is not None:
            text = " ".join(f"{key}={self.report[key]}" for key in empty_report())
        elif self.written is not None:
            text = f"written={self.written}"
        else:
            text = ""
        note = f" ({self.note})" if text and self.note else self.note
        return f"{self.name}: {text}{note}"


# --- stages -----------------------------------------------------------------------------------------

def _ocr_stage(settings: Settings, sync: bool) -> StageResult:
    typer.echo("== ocr")
    cc._resume_chat(settings, "ocr", run_ocr, cc._priced_model(settings, settings.corpus_ocr_model))
    report = cc._ocr_slices(settings, sync, None, fit_budget=True)
    return StageResult("ocr", report=report, note="budget reached" if report["refused"] else "")


def _describe_tasks_left(settings: Settings) -> bool:
    with connect(settings.database_url) as conn:
        return bool(cc.build_doc_tasks(conn, settings.corpus_doc_model, 1)
                    or cc.build_chunk_tasks(conn, settings.corpus_chunk_model, 1))


def _describe_pass(settings: Settings, sync: bool, number: int) -> dict[str, dict[str, int]]:
    reports = {}
    for what in DESCRIBE_STEPS:
        typer.echo(f"== describe {what} (pass {number})")
        reports[what] = cc._describe_one(settings, what, sync, None, dry_run=False, fit_budget=True)
    return reports


def _describe_stages(settings: Settings, sync: bool) -> list[StageResult]:
    """Passes of docs then chunks until a pass describes nothing or nothing is left. `refused` is the
    backlog of the last pass (not a sum: the same tasks are refused again on every pass)."""
    totals = {what: empty_report() for what in DESCRIBE_STEPS}
    for number in range(1, MAX_DESCRIBE_PASSES + 1):
        reports = _describe_pass(settings, sync, number)
        totals = {what: {**add_reports(totals[what], reports[what]), "refused": reports[what]["refused"]}
                  for what in DESCRIBE_STEPS}
        if not any(r["done"] for r in reports.values()) or not _describe_tasks_left(settings):
            break
    return [StageResult(f"describe {what}", report=totals[what],
                        note="budget reached" if totals[what]["refused"] else "") for what in DESCRIBE_STEPS]


def _embed_stage(settings: Settings, spec: IndexSpec, sync: bool, require_description: bool) -> StageResult:
    typer.echo(f"== embed {spec.name}" + ("" if require_description else " (including undescribed chunks)"))
    try:
        written = cc._embed_one(settings, spec, sync, None, dry_run=False, require=require_description)
    except BudgetExceeded as exc:
        typer.echo(f"embed {spec.name}: skipped, it does not fit the budget ({exc})")
        return StageResult(f"embed {spec.name}", note="skipped: does not fit the budget")
    return StageResult(f"embed {spec.name}", written=written)


def _index_stage(settings: Settings, spec: IndexSpec) -> StageResult:
    typer.echo(f"== index {spec.name}")
    cc.build_indexes(settings, [spec])
    return StageResult(f"index {spec.name}", note="built")


# --- summary and plan -------------------------------------------------------------------------------

def _echo_totals(settings: Settings) -> None:
    with connect(settings.database_url) as conn:
        kinds = conn.execute("select kind, sum(usd) as usd from corpus.llm_spend group by kind order by kind").fetchall()
        total = spent(conn)
        c = conn.execute(f"select count(*) filter (where {LIVE_CHUNKS} and text <> '' and description <> '') as d, "
                         f"count(*) filter (where {LIVE_CHUNKS} and text <> '' and description = '') as u, "
                         f"count(*) filter (where {LIVE_CHUNKS} and needs_ocr and text = '') as o "
                         "from corpus.chunk").fetchone()
        counts = {spec.name: conn.execute(f"select count(*) as n from {spec.table}").fetchone()["n"]
                  for spec in sorted(INDEXES.values(), key=lambda spec: spec.provider != "local")}
    per_kind = ", ".join(f"{r['kind']} {usd(float(r['usd']))}" for r in kinds) or "nothing"
    typer.echo(f"spend: {per_kind}; total {usd(total)} of {usd(settings.corpus_budget_usd)}")
    typer.echo(f"chunks: described={c['d']} undescribed={c['u']} awaiting_ocr={c['o']}")
    typer.echo("embeddings: " + " ".join(f"{name}={n}" for name, n in counts.items()))


def _summary(settings: Settings, results: list[StageResult]) -> None:
    typer.echo("run summary")
    for result in results:
        typer.echo(f"  {result.line()}")
    _echo_totals(settings)


def _plan(settings: Settings, specs: list[IndexSpec], skip_ocr: bool, sync: bool) -> None:
    """--dry-run: the stages and their estimates, read-only (the same numbers as `corpus estimate`)."""
    names = ", ".join(spec.name for spec in specs)
    steps = ([] if skip_ocr else ["ocr"]) + ["describe docs", "describe chunks (repeated while it progresses)",
                                             f"embed {names}", f"index {names}"]
    typer.echo("plan: " + " -> ".join(steps))
    batch = cc._uses_batch(settings, sync)
    with connect(settings.database_url) as conn:
        ocr_usd = 0.0 if skip_ocr else estimate_ocr(conn, cc._priced_model(settings, settings.corpus_ocr_model),
                                                    batch=batch)
        if not skip_ocr:
            typer.echo(f"ocr: estimate {usd(ocr_usd)}")
        describe_usd = cc._echo_describe_estimates(conn, settings, batch)
        embed_usd = cc._echo_embed_estimates(conn, settings, batch=True)
        left = remaining_budget(conn, total_cap=settings.corpus_budget_usd)
    typer.echo(f"estimates at {'batch' if batch else 'sync'} price; sync costs x{SYNC_MULTIPLIER:g}")
    typer.echo(f"total estimate: {usd(ocr_usd + describe_usd + embed_usd)}; budget left {usd(left)} of "
               f"{usd(settings.corpus_budget_usd)} (a stage that does not fit runs only the part that fits)")


# --- command ----------------------------------------------------------------------------------------

def _guard(settings: Settings, specs: list[IndexSpec], allow_fake: bool) -> None:
    uses_fake = settings.corpus_llm_provider == "fake" or any(cc._embeds_fake(settings, spec) for spec in specs)
    cc._guard_fake(settings, uses_fake, allow_fake, "run")


def _run(settings: Settings, specs: list[IndexSpec], skip_ocr: bool, sync: bool) -> list[StageResult]:
    results = [] if skip_ocr else [_ocr_stage(settings, sync)]
    described = _describe_stages(settings, sync)
    budget_short = any(r.report["refused"] for r in described)
    embedded = [_embed_stage(settings, spec, sync, require_description=not budget_short) for spec in specs]
    indexed = [_index_stage(settings, spec) for spec, e in zip(specs, embedded, strict=True) if not e.skipped]
    return results + described + embedded + indexed


@corpus_app.command("run")
@friendly_errors
def run_cmd(skip_ocr: bool = typer.Option(False, "--skip-ocr", help="Leave scanned pages for later."),
            dry_run: bool = typer.Option(False, "--dry-run", help="Print the plan and estimates; write nothing."),
            sync: bool = typer.Option(False, "--sync", help="Synchronous calls instead of the OpenAI Batch API."),
            allow_fake: bool = typer.Option(False, "--allow-fake", help=ALLOW_FAKE_HELP)) -> None:
    """The whole run: OCR, descriptions, then embeddings and indexes for CORPUS_INDEXES. Resumable.

    Paid stages that do not fit the budget run only what fits; re-run to continue.
    """
    settings = load_settings()
    specs = cc._configured_indexes(settings)
    if dry_run:
        _plan(settings, specs, skip_ocr, sync)
        return
    _guard(settings, specs, allow_fake)
    _summary(settings, _run(settings, specs, skip_ocr, sync))
