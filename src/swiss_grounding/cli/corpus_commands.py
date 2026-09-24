"""`swiss-grounding corpus ...`: the encoding-track stages as commands (Task 19).

Every paid command first ingests its own unfinished Batch API jobs (amendment A3), then builds new tasks,
checks the budget at the price it will actually pay (A9) and only then submits; the Batch path re-checks
the cap before each further file. With CORPUS_LLM_PROVIDER=fake no OpenAI client is built (A8), nothing
is billed, and nothing is written unless `--allow-fake` is passed or the database is a test database.
The unpaid commands (init, check-manifest, fetch, status, batches) live in `corpus_source_commands`.
"""
from collections.abc import Callable, Sequence
from pathlib import Path

import psycopg
import typer

from swiss_grounding.cli.corpus_source_commands import (
    REFUSED_EXIT_CODE,
    friendly_errors,
    register,
    usd,
)
from swiss_grounding.config import Settings, load_settings
from swiss_grounding.corpus.budget import (
    OCR_IMAGE_TOKENS,
    PRICES,
    SYNC_MULTIPLIER,
    TERMINAL_NON_COUNTING_STATUSES,
    BudgetExceeded,
    cost_usd,
    ensure_within,
    remaining_budget,
    spent,
    tasks_that_fit,
)
from swiss_grounding.corpus.describe import (
    build_chunk_tasks,
    build_doc_tasks,
    estimate_describe,
    mark_repeated_furniture,
    project_chunk_tasks,
    run_chunk_descriptions,
    run_doc_descriptions,
)
from swiss_grounding.corpus.embed import (
    build_vector_indexes,
    embed_local,
    embed_openai_batch,
    estimate_embeddings,
    pending_for_index,
    resume_embed_batches,
    reuse_embeddings,
)
from swiss_grounding.corpus.hybrid_runner import HybridRunner
from swiss_grounding.corpus.ocr import (
    OCR_OUTPUT_TOKENS,
    OCR_PROMPT_TOKENS,
    PENDING_WHERE,
    build_ocr_tasks,
    estimate_ocr,
    run_ocr,
)
from swiss_grounding.corpus.providers import (
    INDEXES,
    AnthropicLLM,
    FakeEmbeddings,
    IndexSpec,
    LocalBgeM3,
    OpenAIEmbeddings,
    OpenAILLM,
    Usage,
)
from swiss_grounding.corpus.runner import BatchRunner, LlmTask, SyncRunner
from swiss_grounding.db.connection import connect

corpus_app = typer.Typer(help="Encoding track: fetch, describe, OCR and embed the declared-scope corpus.")
register(corpus_app)

DIRECT_MAX_RETRIES = 8                   # direct calls beside batches run at the per-minute limit; 429s are retried
LOCAL_EMBED_BATCH = 64
OPENAI_EMBED_MAX_ITEMS = 2048            # inputs per embeddings request (OpenAI limit)
# Estimated tokens per sync embeddings request; OpenAI rejects a request over 300k real tokens. The estimate
# (budget.CHARS_PER_TOKEN = 3) runs low on OCR'd pages full of digits and table pipes: at 250k estimated, a
# request passed 300k real. 100k leaves a threefold margin; throughput is set by the tokens-per-minute limit.
OPENAI_EMBED_MAX_TOKENS = 100_000
PROJECTED_DESCRIPTION_TOKENS = 40        # a chunk description's share of the embedded text
OCR_SLICE = 1000                         # pages built (images read) and run per round without --limit
DESCRIBE_KINDS = {"docs": "describe-doc", "chunks": "describe-chunk"}
TEST_DB_PREFIX = "swiss_grounding_test_"
ALLOW_FAKE_HELP = "Write fake-provider output into a non-test database."


# --- providers, prices and guards -------------------------------------------------------------------

def _openai_client(settings: Settings):
    """The only place an OpenAI client is built for the Batch path (tests replace it)."""
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _uses_batch(settings: Settings, sync: bool) -> bool:
    return settings.corpus_llm_provider == "openai" and not sync


def _price_label(model: str, batch: bool) -> str:
    return f"{model} {'batch' if batch else 'sync'} price"


def _priced_model(settings: Settings, openai_model: str) -> str:
    """The model whose price is paid: the Anthropic fallback bills at its own rates. Refuses an unpriced model."""
    model = settings.corpus_anthropic_model if settings.corpus_llm_provider == "anthropic" else openai_model
    if model not in PRICES:
        typer.echo(f"refused: no price for {model} in budget.PRICES; add it before running")
        raise typer.Exit(REFUSED_EXIT_CODE)
    return model


def _fake_write_allowed(database_url: str, allow_fake: bool) -> bool:
    name = psycopg.conninfo.conninfo_to_dict(database_url).get("dbname") or ""
    return allow_fake or str(name).startswith(TEST_DB_PREFIX)


def _guard_fake(settings: Settings, uses_fake: bool, allow_fake: bool, what: str) -> None:
    """Placeholder output from fake providers must not land in the real corpus by accident."""
    if uses_fake and not _fake_write_allowed(settings.database_url, allow_fake):
        typer.echo(f"refused: {what} would write fake-provider placeholders into the corpus database. Set "
                   "CORPUS_LLM_PROVIDER (and EMBEDDING_BACKEND for bge-m3), or pass --allow-fake if that is intended.")
        raise typer.Exit(REFUSED_EXIT_CODE)


class _FakeCorpusLLM:
    """Fake mode: valid replies for every custom id shape, zero usage, so the ledger stays at $0."""

    def complete(self, task: LlmTask) -> tuple[dict, Usage]:
        return _fake_reply(task), Usage(0, 0)


def _fake_reply(task: LlmTask) -> dict:
    parts = task.custom_id.split("|", 4)
    if parts[0] == "ocr":
        return {"text": "[fake transcription]"}
    # doc|gid|de,fr   or   chunk|gid|status|de=12,fr=34|align_key
    languages = parts[2].split(",") if parts[0] == "doc" else [p.split("=")[0] for p in parts[3].split(",")]
    return {"descriptions": {lang: f"[fake description {lang}]" for lang in languages}, "topics": [],
            "boilerplate": False}


def _llm(settings: Settings):
    if settings.corpus_llm_provider == "openai":
        # A plain --sync run is direct calls too: without these retries, 846 of 1,648 OCR requests on a
        # 200k-tokens-per-minute account ended in quarantine after the SDK default of 2.
        return OpenAILLM(settings.openai_api_key, max_retries=DIRECT_MAX_RETRIES)
    if settings.corpus_llm_provider == "anthropic":
        return AnthropicLLM(settings.anthropic_api_key, settings.corpus_anthropic_model)
    return _FakeCorpusLLM()


# --- configured indexes -----------------------------------------------------------------------------

def _configured_indexes(settings: Settings) -> list[IndexSpec]:
    """CORPUS_INDEXES as specs, local indexes first (free work before paid work)."""
    specs = [INDEXES[name] for name in settings.corpus_indexes]
    return sorted(specs, key=lambda spec: spec.provider != "local")


def _require_configured(settings: Settings, name: str) -> None:
    """Which indexes get built is configuration: an explicit --index outside CORPUS_INDEXES is refused."""
    if name not in settings.corpus_indexes:
        typer.echo(f"{name} is not in CORPUS_INDEXES (currently: {','.join(settings.corpus_indexes)}); "
                   "add it there to build it")
        raise typer.Exit(REFUSED_EXIT_CODE)


def _selected_indexes(settings: Settings, index: str | None) -> list[IndexSpec]:
    if index is None:
        return _configured_indexes(settings)
    if index not in INDEXES:
        raise typer.BadParameter(f"--index must be one of {sorted(INDEXES)}")
    _require_configured(settings, index)
    return [INDEXES[index]]


# --- batch runners ----------------------------------------------------------------------------------

def _record_batch(database_url: str) -> Callable[..., None]:
    def record(batch_id: str, kind: str, endpoint: str, count: int, path: str, estimated_usd: float) -> None:
        with connect(database_url) as conn:
            conn.execute("insert into corpus.batch_job (id, kind, endpoint, status, request_count, input_path, "
                         "estimated_usd) values (%s,%s,%s,'submitted',%s,%s,%s) on conflict (id) do nothing",
                         (batch_id, kind, endpoint, count, path, estimated_usd))
    return record


def _mark_done(database_url: str) -> Callable[[str, str], None]:
    """Committed on its own connection: the run_* functions commit each outcome before pulling the next,
    so by the time a batch's last line has been consumed its results are already stored."""
    def mark_done(batch_id: str, status: str) -> None:
        with connect(database_url) as conn:
            conn.execute("update corpus.batch_job set status = %s, ingested_at = now() where id = %s",
                         (status, batch_id))
    return mark_done


def _before_submit(settings: Settings, kind: str | None, kind_cap: float | None) -> Callable[[float], None]:
    """Before each Batch file: the cap against what earlier files actually cost (raises BudgetExceeded)."""
    def check(file_usd: float) -> None:
        with connect(settings.database_url) as conn:
            ensure_within(conn, estimate=file_usd, total_cap=settings.corpus_budget_usd, kind=kind, kind_cap=kind_cap)
    return check


def _batch_runner(settings: Settings, tokens_per_file: int, kind: str | None = None,
                  kind_cap: float | None = None) -> BatchRunner:
    return BatchRunner(_openai_client(settings), Path(settings.data_dir) / "batches",
                       max_tokens_per_file=tokens_per_file, record=_record_batch(settings.database_url),
                       mark_done=_mark_done(settings.database_url),
                       before_submit=_before_submit(settings, kind, kind_cap))


def _chat_runner(settings: Settings, sync: bool, kind: str | None = None, kind_cap: float | None = None):
    if _uses_batch(settings, sync):
        return _batch_runner(settings, settings.corpus_chat_tokens_per_file, kind, kind_cap)
    return SyncRunner(_llm(settings), workers=settings.corpus_sync_workers)


def _side_by_side(settings: Settings, sync: bool) -> bool:
    return _uses_batch(settings, sync) and settings.corpus_direct_workers > 0


def _describe_runner(settings: Settings, sync: bool):
    """Batches, direct calls, or both side by side (CORPUS_DIRECT_WORKERS > 0 in a batch run)."""
    if not _side_by_side(settings, sync):
        return _chat_runner(settings, sync)
    llm = OpenAILLM(settings.openai_api_key, max_retries=DIRECT_MAX_RETRIES)
    return HybridRunner(_batch_runner(settings, settings.corpus_chat_tokens_per_file), llm,
                        workers=settings.corpus_direct_workers)


def _estimate_at_batch_price(settings: Settings, sync: bool) -> bool:
    """Side by side, any task may take the direct path, so the cap is checked at the direct price."""
    return _uses_batch(settings, sync) and not _side_by_side(settings, sync)


class _ResumeRunner:
    """Feeds already-submitted batches through a run_* function in place of new tasks (A3)."""

    def __init__(self, batch_runner: BatchRunner, batch_ids: Sequence[str]):
        self._runner = batch_runner
        self._ids = list(batch_ids)

    def run(self, tasks, kind: str = "", estimated_usd: float = 0.0):
        return self._runner.resume(self._ids)


def _unfinished_batches(database_url: str, kind: str) -> list[str]:
    with connect(database_url) as conn:
        rows = conn.execute("select id from corpus.batch_job where kind = %s and ingested_at is null "
                            "and status <> all(%s) order by created_at, id",
                            (kind, list(TERMINAL_NON_COUNTING_STATUSES))).fetchall()
    return [r["id"] for r in rows]


def _resume_ids(settings: Settings, kind: str) -> list[str]:
    """Unfinished batches of `kind` that can be collected now; warns when the provider cannot collect them."""
    ids = _unfinished_batches(settings.database_url, kind)
    if ids and settings.corpus_llm_provider != "openai":
        typer.echo(f"{len(ids)} unfinished {kind} batch(es) need CORPUS_LLM_PROVIDER=openai to be collected; "
                   "they still count against the budget")
        return []
    return ids


def _resume_chat(settings: Settings, kind: str, run_fn, model: str) -> None:
    ids = _resume_ids(settings, kind)
    if not ids:
        return
    typer.echo(f"collecting {len(ids)} unfinished {kind} batch(es) first")
    runner = _ResumeRunner(_batch_runner(settings, settings.corpus_chat_tokens_per_file), ids)
    typer.echo(f"resumed {kind}: {run_fn(settings.database_url, runner, [], model=model, batch=True)}")


def _check_budget(conn, settings: Settings, estimate: float, num_tasks: int, kind: str | None = None,
                  kind_cap: float | None = None) -> None:
    """Raises BudgetExceeded, which `friendly_errors` turns into one line and exit 2. On refusal, the
    message also says how many of `num_tasks` fit in what is left, so the operator does not have to
    guess `--limit`."""
    try:
        ensure_within(conn, estimate=estimate, total_cap=settings.corpus_budget_usd, kind=kind, kind_cap=kind_cap)
    except BudgetExceeded as exc:
        remaining = remaining_budget(conn, total_cap=settings.corpus_budget_usd, kind=kind, kind_cap=kind_cap)
        fit = tasks_that_fit(remaining, estimate, num_tasks)
        if fit:
            raise BudgetExceeded(f"{exc} — about {fit:,} of {num_tasks:,} tasks fit; "
                                 f"re-run with --limit {fit}") from exc
        raise BudgetExceeded(f"{exc} — no tasks fit in what is left") from exc


def empty_report() -> dict[str, int]:
    return {"done": 0, "failed": 0, "skipped": 0, "refused": 0}


def add_reports(total: dict[str, int], report: dict[str, int]) -> dict[str, int]:
    return {key: total.get(key, 0) + report.get(key, 0) for key in empty_report()}


def _fit_to_budget(conn, settings: Settings, tasks: Sequence, estimate_fn: Callable[[Sequence], float],
                   kind: str | None, kind_cap: float | None) -> tuple[list, float]:
    """The longest prefix of `tasks` whose estimate fits what is left of the cap, and its estimate. Shrinks
    until the prefix's own estimate fits, since the first tasks may cost more than the average."""
    remaining = remaining_budget(conn, total_cap=settings.corpus_budget_usd, kind=kind, kind_cap=kind_cap)
    count, estimate = len(tasks), estimate_fn(tasks)
    while count and estimate > remaining:
        count = tasks_that_fit(remaining, estimate, count)
        estimate = estimate_fn(tasks[:count]) if count else 0.0
    return list(tasks[:count]), estimate


def _admit(conn, settings: Settings, tasks: Sequence, estimate_fn: Callable[[Sequence], float], fit_budget: bool,
           kind: str | None = None, kind_cap: float | None = None) -> tuple[list, float]:
    """The tasks to run and their estimate. Standalone commands refuse when the stage does not fit
    (BudgetExceeded); `corpus run` (fit_budget) runs the part that fits instead."""
    if fit_budget:
        return _fit_to_budget(conn, settings, tasks, estimate_fn, kind, kind_cap)
    estimate = estimate_fn(tasks)
    _check_budget(conn, settings, estimate, len(tasks), kind=kind, kind_cap=kind_cap)
    return list(tasks), estimate


# --- estimate ---------------------------------------------------------------------------------------

def _echo_describe_estimates(conn, settings: Settings, batch: bool) -> float:
    """Prints the describe lines; returns docs + projected chunks, the describe share of the run's total."""
    doc_model = _priced_model(settings, settings.corpus_doc_model)
    chunk_model = _priced_model(settings, settings.corpus_chunk_model)
    docs = build_doc_tasks(conn, settings.corpus_doc_model, None)
    chunks = build_chunk_tasks(conn, settings.corpus_chunk_model, None)
    projected, projected_usd = project_chunk_tasks(conn, chunk_model, batch=batch)
    docs_usd = estimate_describe(docs, doc_model, batch=batch)
    typer.echo(f"describe docs: {len(docs)} tasks, estimate {usd(docs_usd)}")
    typer.echo(f"describe chunks: {len(chunks)} tasks in described groups, estimate "
               f"{usd(estimate_describe(chunks, chunk_model, batch=batch))}")
    typer.echo(f"describe chunks projected: {projected} tasks, estimate {usd(projected_usd)} "
               "(every group, once documents are described)")
    return docs_usd + projected_usd


def _echo_embed_estimates(conn, settings: Settings, batch: bool) -> float:
    """Prints the embed lines, marking indexes outside CORPUS_INDEXES; returns the openai-3l estimate projected
    with descriptions when it is configured, else 0."""
    configured = settings.corpus_indexes
    mark = {name: "" if name in configured else " (not configured, excluded)" for name in INDEXES}
    spec = INDEXES["openai-3l"]
    pending = pending_for_index(conn, spec, require_description=False, limit=None)
    before = estimate_embeddings(pending, spec.model, batch=batch)
    extra = cost_usd(spec.model, PROJECTED_DESCRIPTION_TOKENS * len(pending), 0, batch=batch)
    typer.echo(f"embed openai-3l before descriptions: {len(pending)} chunks, estimate {usd(before)}"
               f"{mark['openai-3l']}")
    typer.echo(f"embed openai-3l projected with descriptions: {len(pending)} chunks, estimate {usd(before + extra)}"
               f"{mark['openai-3l']}")
    local = pending_for_index(conn, INDEXES["bge-m3"], require_description=False, limit=None)
    typer.echo(f"embed bge-m3: {len(local)} chunks, local (free){mark['bge-m3']}")
    return before + extra if "openai-3l" in configured else 0.0


@corpus_app.command("estimate")
@friendly_errors
def estimate_cmd() -> None:
    """Pending work per stage with its cost, and the ledger."""
    settings = load_settings()
    batch = settings.corpus_llm_provider != "anthropic"     # the Anthropic fallback is sync-only
    ocr_model = _priced_model(settings, settings.corpus_ocr_model)
    with connect(settings.database_url) as conn:
        ocr_usd = estimate_ocr(conn, ocr_model, batch=batch)
        typer.echo(f"ocr: estimate {usd(ocr_usd)}")
        describe_usd = _echo_describe_estimates(conn, settings, batch)
        embed_usd = _echo_embed_estimates(conn, settings, batch=True)
        in_flight = conn.execute("select count(*) as n, coalesce(sum(estimated_usd), 0) as usd "
                                 "from corpus.batch_job where ingested_at is null and status <> all(%s)",
                                 (list(TERMINAL_NON_COUNTING_STATUSES),)).fetchone()
        total = spent(conn)
    typer.echo(f"estimates at {'batch' if batch else 'sync'} price; sync costs x{SYNC_MULTIPLIER:g}")
    typer.echo(f"batches in flight: {in_flight['n']} ({usd(float(in_flight['usd']))})")
    typer.echo(f"spent so far: {usd(total)} of {usd(settings.corpus_budget_usd)}")
    # The go/no-go number: ocr + docs + projected chunk pass + configured paid indexes projected with descriptions.
    label = "batch price" if batch else "ocr/describe at sync price, embed at batch price"
    typer.echo(f"total estimate ({label}): {usd(ocr_usd + describe_usd + embed_usd)}")


# --- ocr --------------------------------------------------------------------------------------------

def _ocr_page_usd(model: str, batch: bool) -> float:
    return cost_usd(model, OCR_IMAGE_TOKENS + OCR_PROMPT_TOKENS, OCR_OUTPUT_TOKENS, batch=batch)


def _ocr_pilot(settings: Settings, pages: int) -> None:
    priced = _priced_model(settings, settings.corpus_ocr_model)
    with connect(settings.database_url) as conn:
        tasks = build_ocr_tasks(conn, settings.corpus_ocr_model, pages)
        if not tasks:
            typer.echo("no pages need OCR")
            return
        estimate = len(tasks) * _ocr_page_usd(priced, batch=False)
        typer.echo(f"pilot: {len(tasks)} page(s), estimate {usd(estimate)} ({_price_label(priced, False)})")
        _check_budget(conn, settings, estimate, len(tasks), kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
        last_id = conn.execute("select coalesce(max(id), 0) as id from corpus.llm_spend").fetchone()["id"]
    report = run_ocr(settings.database_url, SyncRunner(_llm(settings), workers=settings.corpus_sync_workers), tasks, model=priced,
                     batch=False)
    with connect(settings.database_url) as conn:
        used = conn.execute("select coalesce(sum(usd), 0) as usd, coalesce(sum(input_tokens), 0) as tokens "
                            "from corpus.llm_spend where kind = 'ocr' and id > %s", (last_id,)).fetchone()
        remaining = conn.execute("select count(*) as n from corpus.chunk where needs_ocr and text = '' "
                                 "and status in ('current','scheduled')").fetchone()["n"]
    billed = max(1, report["done"] + report["failed"])
    per_page = float(used["usd"]) / billed
    typer.echo(f"pilot: {report} - {usd(per_page)} per page ({_price_label(priced, False)}), "
               f"{int(used['tokens']) // billed} input tokens per page")
    typer.echo(f"projection for {remaining} remaining page(s) at batch price: "
               f"{usd(per_page / SYNC_MULTIPLIER * remaining)}")


def _pending_ocr_pages(conn) -> int:
    return conn.execute(f"select count(*) as n from corpus.chunk where {PENDING_WHERE}").fetchone()["n"]


def _ocr_round(settings: Settings, priced: str, batch: bool, tasks: list, fit_budget: bool) -> tuple[list, float, int]:
    """(pages admitted, their estimate, pages left pending because the budget ran out)."""
    page_usd = _ocr_page_usd(priced, batch)
    typer.echo(f"ocr round: {len(tasks)} page(s), estimate {usd(len(tasks) * page_usd)} "
               f"({_price_label(priced, batch)})")
    with connect(settings.database_url) as conn:
        admitted, estimate = _admit(conn, settings, tasks, lambda ts: len(ts) * page_usd, fit_budget,
                                    kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
        refused = _pending_ocr_pages(conn) - len(admitted) if len(admitted) < len(tasks) else 0
    if refused:
        typer.echo(f"ocr: budget allows {len(admitted)} of {len(tasks)} page(s) in this round; "
                   f"{refused} page(s) left pending")
    return admitted, estimate, refused


def _ocr_slices(settings: Settings, sync: bool, limit: int | None, fit_budget: bool = False) -> dict[str, int]:
    """OCR in rounds of at most OCR_SLICE pages (bounded memory for page images) until nothing is pending,
    `limit` pages are done, or the cap refuses (with fit_budget: until the cap is reached). Pages that failed
    in this run are not retried in it. Returns the totals."""
    priced = _priced_model(settings, settings.corpus_ocr_model)
    batch = _uses_batch(settings, sync)
    attempted: set[str] = set()
    totals = empty_report()
    left = limit
    while left is None or left > 0:
        size = OCR_SLICE if left is None else min(OCR_SLICE, left)
        with connect(settings.database_url) as conn:
            built = build_ocr_tasks(conn, settings.corpus_ocr_model, size + totals["failed"])
        tasks = [t for t in built if t.custom_id not in attempted][:size]
        if not tasks:
            typer.echo("no pages need OCR" if not attempted else "ocr: nothing left to do")
            return totals
        tasks, estimate, refused = _ocr_round(settings, priced, batch, tasks, fit_budget)
        totals = add_reports(totals, {"refused": refused})
        if tasks:
            runner = _chat_runner(settings, sync, kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
            report = run_ocr(settings.database_url, runner, tasks, model=priced, batch=batch, estimated_usd=estimate)
            typer.echo(f"ocr: {report}")
            totals = add_reports(totals, report)
        if refused:
            return totals
        attempted.update(t.custom_id for t in tasks)
        left = None if left is None else left - len(tasks)
    return totals


@corpus_app.command("ocr")
@friendly_errors
def ocr_cmd(pilot: int = typer.Option(0, "--pilot", help="Sync OCR of N pages, then a projection."),
            sync: bool = typer.Option(False, "--sync"), limit: int | None = typer.Option(None, "--limit"),
            dry_run: bool = typer.Option(False, "--dry-run"),
            allow_fake: bool = typer.Option(False, "--allow-fake", help=ALLOW_FAKE_HELP)) -> None:
    """OCR scanned PDF pages, under the OCR sub-cap."""
    settings = load_settings()
    if dry_run:
        priced = _priced_model(settings, settings.corpus_ocr_model)
        batch = _uses_batch(settings, sync or bool(pilot))
        with connect(settings.database_url) as conn:
            typer.echo(f"ocr estimate for all pending pages: {usd(estimate_ocr(conn, priced, batch=batch))} "
                       f"({_price_label(priced, batch)})")
        return
    _guard_fake(settings, settings.corpus_llm_provider == "fake", allow_fake, "ocr")
    _resume_chat(settings, "ocr", run_ocr, _priced_model(settings, settings.corpus_ocr_model))
    if pilot:
        _ocr_pilot(settings, pilot)
    else:
        _ocr_slices(settings, sync, limit)


# --- describe ---------------------------------------------------------------------------------------

def _describe_one(settings: Settings, what: str, sync: bool, limit: int | None, dry_run: bool,
                  fit_budget: bool = False) -> dict[str, int]:
    """One describe pass (`docs` or `chunks`). Returns done/failed/skipped/refused, refused being the tasks
    left for lack of budget (only with fit_budget; otherwise a stage over the cap raises BudgetExceeded)."""
    task_model = settings.corpus_doc_model if what == "docs" else settings.corpus_chunk_model
    priced = _priced_model(settings, task_model)
    run_fn = run_doc_descriptions if what == "docs" else run_chunk_descriptions
    batch = _uses_batch(settings, sync)
    batch_price = _estimate_at_batch_price(settings, sync)
    if not dry_run:
        _resume_chat(settings, DESCRIBE_KINDS[what], run_fn, priced)
    with connect(settings.database_url) as conn:
        if not dry_run:     # before either pass: doc excerpts and chunk tasks both leave furniture out
            typer.echo(f"marked {mark_repeated_furniture(conn)} repeated furniture chunk(s) as boilerplate")
            conn.commit()
        tasks = (build_doc_tasks if what == "docs" else build_chunk_tasks)(conn, task_model, limit)
        typer.echo(f"{what}: {len(tasks)} tasks, estimate {usd(estimate_describe(tasks, priced, batch=batch_price))} "
                   f"({_price_label(priced, batch_price)})")
        if dry_run or not tasks:
            return empty_report()
        admitted, estimate = _admit(conn, settings, tasks,
                                    lambda ts: estimate_describe(ts, priced, batch=batch_price), fit_budget)
    refused = len(tasks) - len(admitted)
    if refused:
        typer.echo(f"{what}: budget allows {len(admitted)} of {len(tasks)} task(s); {refused} left for later")
    if not admitted:
        return add_reports(empty_report(), {"refused": refused})
    if _side_by_side(settings, sync):
        typer.echo(f"{what}: batches and {settings.corpus_direct_workers} direct-call workers side by side")
    report = run_fn(settings.database_url, _describe_runner(settings, sync), admitted, model=priced, batch=batch,
                    estimated_usd=estimate)
    typer.echo(f"{what}: {report}")
    return add_reports(report, {"refused": refused})


@corpus_app.command("describe")
@friendly_errors
def describe_cmd(what: str = typer.Option(..., "--what", help="docs, chunks, or all (docs then chunks)"),
                 sync: bool = typer.Option(False, "--sync"), limit: int | None = typer.Option(None, "--limit"),
                 dry_run: bool = typer.Option(False, "--dry-run"),
                 allow_fake: bool = typer.Option(False, "--allow-fake", help=ALLOW_FAKE_HELP)) -> None:
    """Document descriptions (per translation group), then chunk descriptions, with topics."""
    if what not in ("docs", "chunks", "all"):
        raise typer.BadParameter("--what must be docs, chunks or all")
    settings = load_settings()
    if not dry_run:
        _guard_fake(settings, settings.corpus_llm_provider == "fake", allow_fake, "describe")
    for step in (("docs", "chunks") if what == "all" else (what,)):
        _describe_one(settings, step, sync, limit, dry_run)
    if what == "all" and dry_run:
        typer.echo("note: chunk tasks exist only for groups that already have a document description")


# --- embed and index --------------------------------------------------------------------------------

def _embed_in_process(settings: Settings, spec: IndexSpec, require_description: bool) -> int:
    """Embeds in this process (local model, or sync OpenAI embeddings with the key CORPUS_INDEXES requires)."""
    max_tokens = None
    if spec.provider == "local":
        provider = FakeEmbeddings(spec.dim) if settings.embedding_backend == "fake" else LocalBgeM3(spec.model)
        batch_size = LOCAL_EMBED_BATCH
    else:
        provider = (FakeEmbeddings(spec.dim) if settings.corpus_llm_provider == "fake"
                    else OpenAIEmbeddings(settings.openai_api_key, spec.model, max_retries=DIRECT_MAX_RETRIES))
        batch_size, max_tokens = OPENAI_EMBED_MAX_ITEMS, OPENAI_EMBED_MAX_TOKENS
    written = embed_local(settings.database_url, spec, provider, batch_size=batch_size,
                          require_description=require_description, max_tokens_per_request=max_tokens)
    typer.echo(f"{spec.name}: written {written}")
    return written


def _resume_embed(settings: Settings, spec: IndexSpec) -> None:
    ids = _resume_ids(settings, "embed")
    if not ids:
        return
    typer.echo(f"collecting {len(ids)} unfinished embed batch(es) first")
    runner = _batch_runner(settings, settings.corpus_embed_tokens_per_file)
    typer.echo(f"resumed embed: {resume_embed_batches(settings.database_url, spec, runner, ids)}")


def _embeds_fake(settings: Settings, spec: IndexSpec) -> bool:
    if spec.provider == "local":
        return settings.embedding_backend == "fake"
    return settings.corpus_llm_provider == "fake"


def _embed_one(settings: Settings, spec: IndexSpec, sync: bool, limit: int | None, dry_run: bool,
               require: bool) -> int:
    """Embeds one index's pending chunks; returns the vectors written. A paid index over the cap raises
    BudgetExceeded before anything new is submitted."""
    paid = spec.provider == "openai"
    batch = paid and _uses_batch(settings, sync)
    if paid and not dry_run:
        _resume_embed(settings, spec)
    with connect(settings.database_url) as conn:
        if paid and not dry_run:
            typer.echo(f"{spec.name}: reused {reuse_embeddings(conn, spec, require)} vector(s) from earlier versions")
            conn.commit()
        pending = pending_for_index(conn, spec, require_description=require, limit=limit if batch else None)
        estimate = estimate_embeddings(pending, spec.model, batch=batch) if paid else 0.0
        typer.echo(f"{spec.name}: {len(pending)} chunks pending, estimate {usd(estimate)}"
                   + (f" ({_price_label(spec.model, batch)})" if paid else " (local)"))
        if dry_run or not pending:
            return 0
        if paid:
            _check_budget(conn, settings, estimate, len(pending), kind="embed")
    if limit is not None and not batch:
        typer.echo("note: --limit applies to the Batch path only; embedding every pending chunk")
    if not batch:
        return _embed_in_process(settings, spec, require)
    runner = _batch_runner(settings, settings.corpus_embed_tokens_per_file, kind="embed")
    report = embed_openai_batch(settings.database_url, spec, runner, pending, estimated_usd=estimate)
    typer.echo(f"{spec.name}: {report}")
    return report["written"]


INDEX_HELP = "One index from CORPUS_INDEXES; default: every configured index, local first."


@corpus_app.command("embed")
@friendly_errors
def embed_cmd(index: str | None = typer.Option(None, "--index", help=INDEX_HELP),
              sync: bool = typer.Option(False, "--sync"),
              limit: int | None = typer.Option(None, "--limit", help="Batch path only."),
              dry_run: bool = typer.Option(False, "--dry-run"),
              allow_undescribed: bool = typer.Option(False, "--allow-undescribed"),
              allow_fake: bool = typer.Option(False, "--allow-fake", help=ALLOW_FAKE_HELP)) -> None:
    """Embed described chunks for the indexes in CORPUS_INDEXES: bge-m3 locally, openai-3l via the Batch API."""
    settings = load_settings()
    specs = _selected_indexes(settings, index)
    if not dry_run:
        for spec in specs:
            _guard_fake(settings, _embeds_fake(settings, spec), allow_fake, f"embed {spec.name}")
    for spec in specs:
        _embed_one(settings, spec, sync, limit, dry_run, require=not allow_undescribed)


def build_indexes(settings: Settings, specs: Sequence[IndexSpec]) -> None:
    for spec in specs:
        build_vector_indexes(settings.database_url, spec, parallel_workers=settings.corpus_index_parallel_workers)
        typer.echo(f"{spec.name}: HNSW indexes built")


@corpus_app.command("index")
@friendly_errors
def index_cmd(index: str | None = typer.Option(None, "--index", help=INDEX_HELP)) -> None:
    """Build the HNSW indexes of the configured embedding tables (after bulk loading)."""
    settings = load_settings()
    build_indexes(settings, _selected_indexes(settings, index))
