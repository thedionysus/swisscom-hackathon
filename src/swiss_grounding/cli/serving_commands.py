"""`serving`, `lookups`, `dump` and `setup` commands."""
import json as _json_module
import subprocess
import time
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

import httpx
import typer

from swiss_grounding.app import build_search_service
from swiss_grounding.config import load_settings
from swiss_grounding.corpus.calendar import (
    OPENERZ_SOURCE,
    ZURICH_ZIPS,
    calendar_document,
    fetch_events,
    now,
    swiss_today,
)
from swiss_grounding.corpus.persist import persist_document, upsert_source
from swiss_grounding.db.connection import connect
from swiss_grounding.lookups.premium_data import load_premiums
from swiss_grounding.serving.call_log import latency_summary
from swiss_grounding.serving.db import apply_serving_schema
from swiss_grounding.serving.dump import (
    EXCLUDE_DATA,
    MANIFEST_NAME,
    build_manifest,
    join_parts,
    split_file,
    verify_parts,
)
from swiss_grounding.serving.models import SearchRequest

serving_app = typer.Typer(help="Serving: schema, calendars, latency stats.")


@serving_app.command("calendar")
def calendar_cmd() -> None:
    """Import the Zürich waste calendar (OpenERZ) as corpus documents. Run `corpus embed` afterwards."""
    settings = load_settings()
    today = swiss_today()
    with httpx.Client(timeout=settings.fetch_timeout_seconds,
                       headers={"user-agent": settings.corpus_user_agent}) as client, \
            connect(settings.database_url) as conn:
        upsert_source(conn, OPENERZ_SOURCE)
        for zip_code in ZURICH_ZIPS:
            doc = calendar_document(zip_code, fetch_events(client, zip_code, today), today)
            if doc is not None:
                typer.echo(f"{zip_code}: {persist_document(conn, doc, OPENERZ_SOURCE, now())}")


lookups_app = typer.Typer(help="Lookup data: premiums.")
INSURERS_OPTION = typer.Option(None, help="CSV 'id;name' of insurers")


@lookups_app.command("load-premiums")
def load_premiums_cmd(premiums: Path, regions: Path, year: int,
                      insurers: Path | None = INSURERS_OPTION) -> None:
    """Load the BAG premium table and premium-region list for one business year."""
    names = {}
    if insurers:
        names = dict(line.strip().split(";", 1) for line in insurers.read_text(encoding="utf-8-sig").splitlines()
                     if ";" in line)
    with connect(load_settings().database_url) as conn:
        n_prem, n_reg = load_premiums(conn, premiums, regions, year, names)
    typer.echo(f"loaded {n_prem} premiums and {n_reg} municipalities for {year}")


@serving_app.command("ask")
def ask_cmd(question: str,
            location: Annotated[list[str] | None, typer.Option("--location", "-l")] = None,
            as_of: str | None = typer.Option(None, "--as-of")) -> None:
    """Run swiss_search from the command line and print the JSON response."""
    service = build_search_service(load_settings())
    request = SearchRequest(question, tuple(location or ()), {}, date.fromisoformat(as_of) if as_of else None)
    typer.echo(_json_module.dumps(asdict(service.search(request)), default=str, ensure_ascii=False, indent=2))


@serving_app.command("stats")
def stats_cmd() -> None:
    """p50/p95 latency, abstention and empty-result rate per tool."""
    with connect(load_settings().database_url) as conn:
        for row in latency_summary(conn):
            typer.echo(f"{row['tool']:<22} calls={row['calls']:<5} p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
                       f"abstain={row['abstain_rate']:.0%} empty={row['empty_rate']:.0%}")


dump_app = typer.Typer(help="Prebuilt database dump.")
DB_ARGS = ["-U", "swiss", "-d", "swiss_grounding"]
RESTORE_PGOPTIONS = "-c maintenance_work_mem=1GB -c max_parallel_maintenance_workers=0"


def repo_root() -> Path:
    """The checkout root, found from this file's location so `dump export`/`setup` work from any
    cwd. `serving_commands.py` lives at <root>/src/swiss_grounding/cli/, three parents up."""
    root = Path(__file__).resolve().parents[3]
    if not (root / "docker-compose.yml").exists():
        raise RuntimeError(f"repo root {root} has no docker-compose.yml; move or reinstall the package")
    return root


REPO_ROOT = repo_root()
DUMP_DIR = REPO_ROOT / "data" / "dump"
DUMP_OUT_OPTION = typer.Option(REPO_ROOT / "dist", "--out")


def _compose(*args: str, stdout=None) -> None:
    compose_file = REPO_ROOT / "docker-compose.yml"
    cmd = ["docker", "compose", "-f", str(compose_file), *args]
    try:
        subprocess.run(cmd, check=True, stdout=stdout)
    except FileNotFoundError as exc:
        raise typer.BadParameter("docker is not installed; see the README's setup section") from exc
    except subprocess.CalledProcessError as exc:
        raise typer.BadParameter(
            f"docker compose failed: is Docker running? (command: {' '.join(cmd)})") from exc


@dump_app.command("export")
def dump_export_cmd(out: Path = DUMP_OUT_OPTION,
                    openai: bool = typer.Option(False, "--openai", help="also export the OpenAI vectors")) -> None:
    """Write the default dump (no OpenAI vectors) split into release-sized parts, plus a manifest."""
    out.mkdir(parents=True, exist_ok=True)
    excludes = [f"--exclude-table-data={t}" for t in EXCLUDE_DATA]
    with (out / "corpus.dump").open("wb") as f:
        _compose("exec", "-T", "db", "pg_dump", *DB_ARGS, "-Fc", "-Z", "6", *excludes, stdout=f)
    parts = split_file(out / "corpus.dump", out)
    (out / "corpus.dump").unlink()
    manifest = build_manifest(parts, meta={"created_at": datetime.now(UTC).isoformat(), "kind": "default"})
    (out / MANIFEST_NAME).write_text(_json_module.dumps(manifest, indent=2))
    if openai:
        with (out / "openai.dump").open("wb") as f:
            _compose("exec", "-T", "db", "pg_dump", *DB_ARGS, "-Fc", "--data-only", "-t", "corpus.emb_openai_3l*",
                     stdout=f)
    typer.echo(f"{len(parts)} parts and {MANIFEST_NAME} in {out}. Publish them to the private repository:\n"
               f"  gh release create corpus-latest {out}/* --repo thedionysus/swisscom-hackathon "
               f"--title 'Prebuilt corpus' --notes 'Restore with: uv run swiss-grounding setup'\n"
               f"  (or `gh release upload corpus-latest {out}/* --clobber` to replace an existing one)")


def _gh_download(settings, pattern: str) -> None:
    """Download release assets of our private repository. `gh` uses the caller's GitHub login, so only
    people with access to the repository (the team and the evaluators we invite) can download."""
    _run(["gh", "release", "download", settings.dump_release_tag, "--repo", settings.dump_release_repo,
          "--pattern", pattern, "--dir", str(DUMP_DIR), "--skip-existing"])


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"{cmd[0]} is not installed; see the README's setup section") from exc
    except subprocess.CalledProcessError as exc:
        raise typer.BadParameter(
            "could not download the prebuilt database: run `gh auth login` with an account that has "
            "access to thedionysus/swisscom-hackathon") from exc


def setup_cmd(skip_models: bool = typer.Option(False, "--skip-models", help="do not pre-download models")) -> None:
    """Download the prebuilt database, verify it, restore it, and pre-download the local models."""
    settings = load_settings()
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    # Parts already in data/dump (e.g. copied from a USB stick) are kept; a wrong one fails the checksum.
    _gh_download(settings, MANIFEST_NAME)
    _gh_download(settings, "corpus.dump.part*")
    manifest = _json_module.loads((DUMP_DIR / MANIFEST_NAME).read_text())
    verify_parts(DUMP_DIR, manifest)
    dump = join_parts(DUMP_DIR, manifest, DUMP_DIR / "corpus.dump")
    _compose("up", "-d", "--wait", "db")
    _compose("cp", str(dump), "db:/tmp/corpus.dump")
    dump.unlink()                                  # the parts stay; the joined copy is not needed twice
    # The dump carries the HNSW index definitions; pg_restore builds them. Postgres' default 64 MB of
    # maintenance memory makes that build crawl, and parallel jobs multiply memory use.
    _compose("exec", "-T", "-e", f"PGOPTIONS={RESTORE_PGOPTIONS}", "db", "pg_restore", *DB_ARGS, "--clean",
             "--if-exists", "--no-owner", "-j", "2", "/tmp/corpus.dump")
    _compose("exec", "-T", "db", "rm", "-f", "/tmp/corpus.dump")
    apply_serving_schema(settings.database_url)
    typer.echo(f"database restored and indexes rebuilt in {time.perf_counter() - started:.0f}s")
    if not skip_models:
        from swiss_grounding.app import build_query_provider, build_reranker
        from swiss_grounding.serving.reranker import detect_device
        build_query_provider(settings).embed(["warm up"])
        build_reranker(settings, detect_device()).score("warm up", ["warm up"])
        typer.echo("bge-m3 and the reranker are downloaded")
