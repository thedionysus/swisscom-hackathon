"""`swiss-grounding corpus ...`: the encoding-track stages as commands (Task 19).

Every paid command first ingests its own unfinished Batch API jobs (amendment A3), then builds new tasks,
checks the budget at the price it will actually pay (A9) and only then submits. With
CORPUS_LLM_PROVIDER=fake no OpenAI client is ever built (A8) and nothing is billed.
"""
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated
from urllib import robotparser
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
import typer

from swiss_grounding.config import Settings, load_settings
from swiss_grounding.corpus.budget import (
    OCR_IMAGE_TOKENS,
    SYNC_MULTIPLIER,
    TERMINAL_NON_COUNTING_STATUSES,
    BudgetExceeded,
    cost_usd,
    ensure_within,
    spent,
)
from swiss_grounding.corpus.connectors.fedlex import FedlexConnector
from swiss_grounding.corpus.connectors.html import CrawlPolicy, HtmlConnector
from swiss_grounding.corpus.connectors.html_meta import page_meta
from swiss_grounding.corpus.connectors.pdf import PdfConnector
from swiss_grounding.corpus.db import apply_corpus_schema
from swiss_grounding.corpus.describe import (
    build_chunk_tasks,
    build_doc_tasks,
    estimate_describe,
    mark_repeated_furniture,
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
from swiss_grounding.corpus.fetch_stage import run_fetch
from swiss_grounding.corpus.manifest import load_manifest, select_sources
from swiss_grounding.corpus.ocr import (
    OCR_OUTPUT_TOKENS,
    OCR_PROMPT_TOKENS,
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
from swiss_grounding.db.migrate import apply_schema

corpus_app = typer.Typer(help="Encoding track: fetch, describe, OCR and embed the declared-scope corpus.")

SYNC_WORKERS = 8
BUDGET_EXIT_CODE = 2
LOCAL_EMBED_BATCH = 64
OPENAI_SYNC_EMBED_BATCH = 128
DESCRIBE_KINDS = {"docs": "describe-doc", "chunks": "describe-chunk"}
SWISS_TZ = ZoneInfo("Europe/Zurich")


# --- clients and runners --------------------------------------------------------------------------

def _openai_client(settings: Settings):
    """The only place an OpenAI client is built for the Batch path (tests replace it)."""
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _http(settings: Settings) -> httpx.Client:
    return httpx.Client(headers={"user-agent": settings.corpus_user_agent}, timeout=settings.fetch_timeout_seconds)


def _swiss_today() -> date:
    return datetime.now(tz=SWISS_TZ).date()


def _uses_batch(settings: Settings, sync: bool) -> bool:
    return settings.corpus_llm_provider == "openai" and not sync


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
        return OpenAILLM(settings.openai_api_key)
    if settings.corpus_llm_provider == "anthropic":
        return AnthropicLLM(settings.anthropic_api_key, settings.corpus_anthropic_model)
    return _FakeCorpusLLM()


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


def _batch_runner(settings: Settings, tokens_per_file: int) -> BatchRunner:
    return BatchRunner(_openai_client(settings), Path(settings.data_dir) / "batches",
                       max_tokens_per_file=tokens_per_file, record=_record_batch(settings.database_url),
                       mark_done=_mark_done(settings.database_url))


def _chat_runner(settings: Settings, sync: bool):
    if _uses_batch(settings, sync):
        return _batch_runner(settings, settings.corpus_chat_tokens_per_file)
    return SyncRunner(_llm(settings), workers=SYNC_WORKERS)


class _ResumeRunner:
    """Feeds already-submitted batches through a run_* function in place of new tasks (A3)."""

    def __init__(self, batch_runner: BatchRunner, batch_ids: Sequence[str]):
        self._runner = batch_runner
        self._ids = list(batch_ids)

    def run(self, tasks, kind: str = "", estimated_usd: float = 0.0):
        return self._runner.resume(self._ids)


# --- shared steps ---------------------------------------------------------------------------------

def _unfinished_batches(database_url: str, kind: str) -> list[str]:
    placeholders = ",".join(["%s"] * len(TERMINAL_NON_COUNTING_STATUSES))
    with connect(database_url) as conn:
        rows = conn.execute(f"select id from corpus.batch_job where kind = %s and ingested_at is null "
                            f"and status not in ({placeholders}) order by created_at, id",
                            (kind, *TERMINAL_NON_COUNTING_STATUSES)).fetchall()
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
    report = run_fn(settings.database_url, runner, [], model=model, batch=True)
    typer.echo(f"resumed {kind}: {report}")


def _check_budget(conn, settings: Settings, estimate: float, kind: str | None = None,
                  kind_cap: float | None = None) -> None:
    try:
        ensure_within(conn, estimate=estimate, total_cap=settings.corpus_budget_usd, kind=kind, kind_cap=kind_cap)
    except BudgetExceeded as exc:
        typer.echo(f"refused: {exc}")
        raise typer.Exit(BUDGET_EXIT_CODE) from exc


def _usd(amount: float) -> str:
    """Cents matter for pilots and small runs; whole runs read better rounded."""
    return f"${amount:.2f}" if amount >= 1 else f"${amount:.4f}"


def _price_label(batch: bool) -> str:
    return "batch price" if batch else "sync price"


# --- setup and fetch ------------------------------------------------------------------------------

@corpus_app.command("init")
def init_cmd() -> None:
    """Apply the public schema and the corpus schema."""
    settings = load_settings()
    apply_schema(settings.database_url, settings.embedding_dim)
    apply_corpus_schema(settings.database_url)
    typer.echo("corpus schema ready")


def _robots_verdict(http: httpx.Client, url: str, user_agent: str) -> str:
    parts = urlparse(url)
    parser = robotparser.RobotFileParser()
    try:
        response = http.get(f"{parts.scheme}://{parts.netloc}/robots.txt", follow_redirects=True)
    except httpx.HTTPError:
        return "robots=unreachable"
    if response.status_code != 200:
        return f"robots=none({response.status_code})"
    parser.parse(response.text.splitlines())
    return "robots=allowed" if parser.can_fetch(user_agent, url) else "robots=DISALLOWED"


def _check_html(http: httpx.Client, entry, user_agent: str) -> int:
    problems = 0
    selector = entry.config.get("language_links_selector")
    for url in entry.config["start_urls"]:
        try:
            response = http.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            typer.echo(f"{entry.id}: FAILED {url} ({exc})")
            problems += 1
            continue
        alternates = len(page_meta(response.text, str(response.url), language_links_selector=selector).alternates)
        verdict = _robots_verdict(http, url, user_agent)
        typer.echo(f"{entry.id}: {response.status_code} {url} -> {response.url} {verdict} alternates={alternates}")
        problems += int(response.status_code >= 400 or verdict == "robots=DISALLOWED")
    return problems


def _check_fedlex(connector: FedlexConnector, entry) -> int:
    problems = 0
    for sr in entry.config["sr_numbers"]:
        try:
            found = connector._rows_for_language(str(sr), "de", _swiss_today())  # one SPARQL probe per SR
        except httpx.HTTPError as exc:
            typer.echo(f"{entry.id}: SR {sr} FAILED ({exc})")
            problems += 1
            continue
        typer.echo(f"{entry.id}: SR {sr} de {sorted(found) or 'NOT FOUND'}")
        problems += int(not found)
    return problems


@corpus_app.command("check-manifest")
def check_manifest_cmd(path: Path) -> None:
    """Validate a manifest and probe every start URL and SR number. Exit 1 on any problem."""
    settings = load_settings()
    manifest = load_manifest(path)
    with connect(settings.database_url) as conn:
        extents = {r["id"] for r in conn.execute("select id from location").fetchall()}
    problems = 0
    with _http(settings) as http:
        fedlex = FedlexConnector(http, _swiss_today, settings.data_dir)
        for entry in manifest.sources:
            if entry.extent_id not in extents:
                typer.echo(f"{entry.id}: unknown extent {entry.extent_id}")
                problems += 1
            if entry.connector == "html":
                problems += _check_html(http, entry, settings.corpus_user_agent)
            else:
                problems += _check_fedlex(fedlex, entry)
    typer.echo(f"{problems} problem(s)")
    raise typer.Exit(1 if problems else 0)


@corpus_app.command("fetch")
def fetch_cmd(manifest: Annotated[Path, typer.Option("--manifest")],
              tier: Annotated[int, typer.Option("--tier")] = 1,
              source: Annotated[list[str] | None, typer.Option("--source", help="Repeatable; narrows the tier.")] = None,
              workers: Annotated[int, typer.Option("--workers")] = 4) -> None:
    """Fetch the manifest's sources, persist documents and chunks, promote scheduled versions that are due."""
    settings = load_settings()
    try:
        specs = select_sources(load_manifest(manifest), tier=tier, source_ids=tuple(source or ()))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    with _http(settings) as http:
        policy = CrawlPolicy(respect_robots=settings.respect_robots, delay_seconds=settings.crawl_delay_seconds)
        connectors = {"fedlex": FedlexConnector(http, _swiss_today, settings.data_dir),
                      "html": HtmlConnector(http, policy)}
        pdf = PdfConnector(http, settings.data_dir, delay_seconds=settings.crawl_delay_seconds)
        report = run_fetch(settings.database_url, specs, connectors, pdf, now=lambda: datetime.now(tz=UTC),
                           workers=workers)
    promote = report.pop("_promote", {})
    for sid, tally in report.items():
        typer.echo(f"{sid}: " + " ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    typer.echo("promote: " + (" ".join(f"{k}={v}" for k, v in sorted(promote.items())) or "nothing due"))


# --- estimate --------------------------------------------------------------------------------------

@corpus_app.command("estimate")
def estimate_cmd() -> None:
    """Pending work per stage with its cost at Batch price, and the ledger."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        ocr = estimate_ocr(conn, settings.corpus_ocr_model)
        docs = build_doc_tasks(conn, settings.corpus_doc_model, None)
        chunks = build_chunk_tasks(conn, settings.corpus_chunk_model, None)
        pending = {name: pending_for_index(conn, spec, require_description=False, limit=None)
                   for name, spec in INDEXES.items()}
        in_flight = conn.execute("select count(*) as n, coalesce(sum(estimated_usd), 0) as usd "
                                 "from corpus.batch_job where ingested_at is null and status <> all(%s)",
                                 (list(TERMINAL_NON_COUNTING_STATUSES),)).fetchone()
        total = spent(conn)
    typer.echo(f"ocr: estimate {_usd(ocr)}")
    typer.echo(f"describe docs: {len(docs)} tasks, estimate {_usd(estimate_describe(docs, settings.corpus_doc_model))}")
    typer.echo(f"describe chunks: {len(chunks)} tasks (lower bound: groups without a document description come "
               f"later), estimate {_usd(estimate_describe(chunks, settings.corpus_chunk_model))}")
    openai_spec = INDEXES["openai-3l"]
    typer.echo(f"embed openai-3l: {len(pending['openai-3l'])} chunks (before reuse), estimate "
               f"{_usd(estimate_embeddings(pending['openai-3l'], openai_spec.model))}")
    typer.echo(f"embed bge-m3: {len(pending['bge-m3'])} chunks, local (free)")
    typer.echo(f"estimates at batch price; sync costs x{SYNC_MULTIPLIER:g}")
    typer.echo(f"batches in flight: {in_flight['n']} ({_usd(float(in_flight['usd']))})")
    typer.echo(f"spent so far: {_usd(total)} of {_usd(settings.corpus_budget_usd)}")


# --- ocr -------------------------------------------------------------------------------------------

def _ocr_page_usd(model: str, batch: bool) -> float:
    return cost_usd(model, OCR_IMAGE_TOKENS + OCR_PROMPT_TOKENS, OCR_OUTPUT_TOKENS, batch=batch)


def _ocr_pilot(settings: Settings, pages: int) -> None:
    model = settings.corpus_ocr_model
    with connect(settings.database_url) as conn:
        tasks = build_ocr_tasks(conn, model, pages)
        if not tasks:
            typer.echo("no pages need OCR")
            return
        estimate = len(tasks) * _ocr_page_usd(model, batch=False)
        typer.echo(f"pilot: {len(tasks)} page(s), estimate {_usd(estimate)} ({_price_label(False)})")
        _check_budget(conn, settings, estimate, kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
        last_id = conn.execute("select coalesce(max(id), 0) as id from corpus.llm_spend").fetchone()["id"]
    report = run_ocr(settings.database_url, SyncRunner(_llm(settings), workers=SYNC_WORKERS), tasks, model=model,
                     batch=False)
    with connect(settings.database_url) as conn:
        used = conn.execute("select coalesce(sum(usd), 0) as usd, coalesce(sum(input_tokens), 0) as tokens "
                            "from corpus.llm_spend where kind = 'ocr' and id > %s", (last_id,)).fetchone()
        remaining = conn.execute("select count(*) as n from corpus.chunk where needs_ocr and text = '' "
                                 "and status in ('current','scheduled')").fetchone()["n"]
    done = max(1, report["done"] + report["failed"])
    per_page = float(used["usd"]) / done
    typer.echo(f"pilot: {report} - {_usd(per_page)} per page ({_price_label(False)}), "
               f"{int(used['tokens']) // done} input tokens per page")
    typer.echo(f"projection for {remaining} remaining page(s) at batch price: "
               f"{_usd(per_page / SYNC_MULTIPLIER * remaining)}")


@corpus_app.command("ocr")
def ocr_cmd(pilot: int = typer.Option(0, "--pilot", help="Sync OCR of N pages, then a projection."),
            sync: bool = typer.Option(False, "--sync"), limit: int | None = typer.Option(None, "--limit"),
            dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """OCR scanned PDF pages, under the OCR sub-cap."""
    settings = load_settings()
    model = settings.corpus_ocr_model
    batch = _uses_batch(settings, sync or bool(pilot))
    if not dry_run:
        _resume_chat(settings, "ocr", run_ocr, model)
    if pilot and not dry_run:
        _ocr_pilot(settings, pilot)
        return
    with connect(settings.database_url) as conn:
        typer.echo(f"ocr estimate for all pending pages: {_usd(estimate_ocr(conn, model, batch=batch))} "
                   f"({_price_label(batch)})")
        if dry_run:
            return
        tasks = build_ocr_tasks(conn, model, limit)
        if not tasks:
            typer.echo("no pages need OCR")
            return
        estimate = len(tasks) * _ocr_page_usd(model, batch)
        typer.echo(f"this run: {len(tasks)} page(s), estimate {_usd(estimate)}")
        _check_budget(conn, settings, estimate, kind="ocr", kind_cap=settings.corpus_ocr_budget_usd)
    report = run_ocr(settings.database_url, _chat_runner(settings, sync), tasks, model=model, batch=batch,
                     estimated_usd=estimate)
    typer.echo(f"ocr: {report}")


# --- describe --------------------------------------------------------------------------------------

def _describe_one(settings: Settings, what: str, sync: bool, limit: int | None, dry_run: bool) -> None:
    kind = DESCRIBE_KINDS[what]
    model = settings.corpus_doc_model if what == "docs" else settings.corpus_chunk_model
    run_fn = run_doc_descriptions if what == "docs" else run_chunk_descriptions
    batch = _uses_batch(settings, sync)
    if not dry_run:
        _resume_chat(settings, kind, run_fn, model)
    with connect(settings.database_url) as conn:
        if what == "chunks" and not dry_run:
            typer.echo(f"marked {mark_repeated_furniture(conn)} repeated furniture chunk(s) as boilerplate")
            conn.commit()
        tasks = (build_doc_tasks if what == "docs" else build_chunk_tasks)(conn, model, limit)
        estimate = estimate_describe(tasks, model, batch=batch)
        typer.echo(f"{what}: {len(tasks)} tasks, estimate {_usd(estimate)} ({_price_label(batch)})")
        if dry_run or not tasks:
            return
        _check_budget(conn, settings, estimate)
    report = run_fn(settings.database_url, _chat_runner(settings, sync), tasks, model=model, batch=batch,
                    estimated_usd=estimate)
    typer.echo(f"{what}: {report}")


@corpus_app.command("describe")
def describe_cmd(what: str = typer.Option(..., "--what", help="docs, chunks, or all (docs then chunks)"),
                 sync: bool = typer.Option(False, "--sync"), limit: int | None = typer.Option(None, "--limit"),
                 dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Document descriptions (per translation group), then chunk descriptions, with topics."""
    if what not in ("docs", "chunks", "all"):
        raise typer.BadParameter("--what must be docs, chunks or all")
    settings = load_settings()
    for step in (("docs", "chunks") if what == "all" else (what,)):
        _describe_one(settings, step, sync, limit, dry_run)
    if what == "all" and dry_run:
        typer.echo("note: chunk tasks exist only for groups that already have a document description")


# --- embed and index -------------------------------------------------------------------------------

def _embed_in_process(settings: Settings, spec: IndexSpec, require_description: bool) -> None:
    if spec.provider == "local":
        provider = FakeEmbeddings(spec.dim) if settings.embedding_backend == "fake" else LocalBgeM3(spec.model)
        batch_size = LOCAL_EMBED_BATCH
    elif settings.corpus_llm_provider == "openai":
        provider, batch_size = OpenAIEmbeddings(settings.openai_api_key, spec.model), OPENAI_SYNC_EMBED_BATCH
    elif settings.corpus_llm_provider == "fake":
        provider, batch_size = FakeEmbeddings(spec.dim), OPENAI_SYNC_EMBED_BATCH
    else:
        raise typer.BadParameter(f"{spec.name} needs CORPUS_LLM_PROVIDER=openai (or fake)")
    written = embed_local(settings.database_url, spec, provider, batch_size=batch_size,
                          require_description=require_description)
    typer.echo(f"{spec.name}: written {written}")


def _resume_embed(settings: Settings, spec: IndexSpec) -> None:
    ids = _resume_ids(settings, "embed")
    if not ids:
        return
    typer.echo(f"collecting {len(ids)} unfinished embed batch(es) first")
    runner = _batch_runner(settings, settings.corpus_embed_tokens_per_file)
    typer.echo(f"resumed embed: {resume_embed_batches(settings.database_url, spec, runner, ids)}")


@corpus_app.command("embed")
def embed_cmd(index: str = typer.Option(..., "--index", help="openai-3l or bge-m3"),
              sync: bool = typer.Option(False, "--sync"),
              limit: int | None = typer.Option(None, "--limit", help="Batch path only."),
              dry_run: bool = typer.Option(False, "--dry-run"),
              allow_undescribed: bool = typer.Option(False, "--allow-undescribed")) -> None:
    """Embed described chunks: openai-3l through the Batch API (or sync), bge-m3 locally."""
    if index not in INDEXES:
        raise typer.BadParameter(f"--index must be one of {sorted(INDEXES)}")
    settings = load_settings()
    spec = INDEXES[index]
    require = not allow_undescribed
    paid = spec.provider == "openai"
    batch = paid and _uses_batch(settings, sync)
    if paid and not dry_run:
        _resume_embed(settings, spec)
    with connect(settings.database_url) as conn:
        if paid and not dry_run:
            typer.echo(f"{index}: reused {reuse_embeddings(conn, spec, require)} vector(s) from earlier versions")
            conn.commit()
        pending = pending_for_index(conn, spec, require_description=require, limit=limit if batch else None)
        estimate = estimate_embeddings(pending, spec.model, batch=batch) if paid else 0.0
        typer.echo(f"{index}: {len(pending)} chunks pending, estimate {_usd(estimate)}"
                   + (f" ({_price_label(batch)})" if paid else " (local)"))
        if dry_run or not pending:
            return
        if paid:
            _check_budget(conn, settings, estimate, kind="embed")
    if limit is not None and not batch:
        typer.echo("note: --limit applies to the Batch path only; embedding every pending chunk")
    if not batch:
        _embed_in_process(settings, spec, require)
        return
    runner = _batch_runner(settings, settings.corpus_embed_tokens_per_file)
    typer.echo(f"{index}: {embed_openai_batch(settings.database_url, spec, runner, pending, estimated_usd=estimate)}")


@corpus_app.command("index")
def index_cmd(index: str = typer.Option(..., "--index")) -> None:
    """Build the HNSW indexes of one embedding table (after bulk loading)."""
    if index not in INDEXES:
        raise typer.BadParameter(f"--index must be one of {sorted(INDEXES)}")
    settings = load_settings()
    build_vector_indexes(settings.database_url, INDEXES[index],
                         parallel_workers=settings.corpus_index_parallel_workers)
    typer.echo(f"{index}: HNSW indexes built")


# --- reporting -------------------------------------------------------------------------------------

@corpus_app.command("status")
def status_cmd() -> None:
    """Documents, chunks, embeddings, spend and quarantine at a glance."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        for r in conn.execute("select source_id, language, status, count(*) as n from corpus.document "
                              "group by 1,2,3 order by 1,2,3").fetchall():
            typer.echo(f"documents {r['source_id']:<28} {r['language']} {r['status']:<11} {r['n']}")
        c = conn.execute("select count(*) filter (where status in ('current','scheduled')) as live, "
                         "count(*) filter (where status in ('current','scheduled') and description <> '') "
                         "as described, count(*) filter (where needs_ocr) as ocr from corpus.chunk").fetchone()
        typer.echo(f"chunks live={c['live']} described={c['described']} awaiting_ocr={c['ocr']}")
        for name, spec in INDEXES.items():
            n = conn.execute(f"select count(*) as n from {spec.table}").fetchone()["n"]
            typer.echo(f"embeddings {name}: {n}")
        for r in conn.execute("select kind, sum(usd) as usd from corpus.llm_spend group by kind order by kind"):
            typer.echo(f"spend {r['kind']}: {_usd(float(r['usd']))}")
        typer.echo(f"spend total: {_usd(spent(conn))} of {_usd(settings.corpus_budget_usd)}")
        pending = conn.execute("select count(*) as n from corpus.batch_job where ingested_at is null").fetchone()
        typer.echo(f"batches not ingested: {pending['n']}")
        q = conn.execute("select count(*) as n from corpus.quarantine").fetchone()["n"]
        typer.echo(f"quarantine: {q}")


@corpus_app.command("batches")
def batches_cmd() -> None:
    """List Batch API jobs: id, kind, status, requests, estimate, submitted and ingested times."""
    settings = load_settings()
    with connect(settings.database_url) as conn:
        rows = conn.execute("select id, kind, status, request_count, estimated_usd, created_at, ingested_at "
                            "from corpus.batch_job order by created_at, id").fetchall()
    if not rows:
        typer.echo("no batch jobs")
        return
    for r in rows:
        ingested = r["ingested_at"].isoformat(timespec="seconds") if r["ingested_at"] else "not ingested"
        typer.echo(f"{r['id']}  {r['kind']:<14} {r['status']:<11} {r['request_count']:>6} requests  "
                   f"{_usd(float(r['estimated_usd']))}  submitted {r['created_at'].isoformat(timespec='seconds')}  "
                   f"{ingested}")
