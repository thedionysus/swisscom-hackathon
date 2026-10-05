"""`serving`, `lookups`, `dump` and `setup` commands."""
import json as _json_module
import shutil
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
from swiss_grounding.lookups.premium_data import load_premiums, unnamed_insurers
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
from swiss_grounding.serving.secrets import (
    SECRETS_ASSET,
    SHARED_KEYS,
    merge_env,
    parse_env,
    shared_env_text,
)

serving_app = typer.Typer(help="Serving: schema, calendars, latency stats.")


@serving_app.command("init")
def init_cmd() -> None:
    """Create or update the serving schema (idempotent)."""
    apply_serving_schema(load_settings().database_url)
    typer.echo("serving schema ready")


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
    missing = unnamed_insurers(premiums, names)
    if missing:
        typer.echo(f"warning: {len(missing)} insurer numbers have no name and will be shown as numbers: "
                   f"{', '.join(missing)}. Pass the BAG insurer register with --insurers (see the runbook).",
                   err=True)


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
    cwd. `serving_commands.py` lives at <root>/src/swiss_grounding/cli/, three parents up.

    Resolved lazily (called only from inside `dump export`/`setup`, never at import time): every
    `swiss-grounding` command imports this module through `main.py`, so an import-time call would
    break the whole CLI outside a checkout, even for commands that never touch the dump.
    """
    root = Path(__file__).resolve().parents[3]
    if not (root / "docker-compose.yml").exists():
        raise RuntimeError(f"repo root {root} has no docker-compose.yml; move or reinstall the package")
    return root


def dump_dir() -> Path:
    return repo_root() / "data" / "dump"


DUMP_OUT_OPTION = typer.Option(None, "--out", help="default: <repo root>/dist")


def _compose(*args: str, stdout=None) -> None:
    compose_file = repo_root() / "docker-compose.yml"
    cmd = ["docker", "compose", "-f", str(compose_file), *args]
    try:
        subprocess.run(cmd, check=True, stdout=stdout)
    except FileNotFoundError as exc:
        raise typer.BadParameter("docker is not installed; see the README's setup section") from exc
    except subprocess.CalledProcessError as exc:
        raise typer.BadParameter(
            f"docker compose failed: is Docker running? (command: {' '.join(cmd)})") from exc


@dump_app.command("export")
def dump_export_cmd(out: Path | None = DUMP_OUT_OPTION) -> None:
    """Write the database dump, OpenAI vectors included, split into release-sized parts, plus a manifest."""
    out = out or repo_root() / "dist"
    out.mkdir(parents=True, exist_ok=True)
    excludes = [f"--exclude-table-data={t}" for t in EXCLUDE_DATA]
    with (out / "corpus.dump").open("wb") as f:
        _compose("exec", "-T", "db", "pg_dump", *DB_ARGS, "-Fc", "-Z", "6", *excludes, stdout=f)
    parts = split_file(out / "corpus.dump", out)
    (out / "corpus.dump").unlink()
    manifest = build_manifest(parts, meta={"created_at": datetime.now(UTC).isoformat(), "kind": "default"})
    (out / MANIFEST_NAME).write_text(_json_module.dumps(manifest, indent=2))
    typer.echo(f"{len(parts)} parts and {MANIFEST_NAME} in {out}. Publish them as a new release of the private "
               f"repository, for example:\n"
               f"  gh release create corpus-<what>-<YYYY-MM-DD> {out}/* --repo thedionysus/swisscom-hackathon "
               f"--title '<title>' --notes 'Restore with: uv run swiss-grounding setup'\n"
               f"then set the default of DUMP_RELEASE_TAG in config.py to that tag, so `setup` installs it.")


def _gh_download(settings, directory: Path, *patterns: str, clobber: bool = False) -> None:
    """Download release assets of our private repository into `directory`. `gh` uses the caller's GitHub
    login, so only people with access to the repository (the team and the evaluators we invite) can
    download. Existing files are kept unless `clobber`."""
    selected = [arg for pattern in patterns for arg in ("--pattern", pattern)]
    _run(["gh", "release", "download", settings.dump_release_tag, "--repo", settings.dump_release_repo,
          *selected, "--dir", str(directory), "--clobber" if clobber else "--skip-existing"])


def _run(cmd: list[str], what: str = "download the prebuilt database") -> None:
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"{cmd[0]} is not installed; see the README's setup section") from exc
    except subprocess.CalledProcessError as exc:
        raise typer.BadParameter(
            f"could not {what}: run `gh auth login` with an account that has "
            "access to thedionysus/swisscom-hackathon") from exc


def install_shared_key(settings, env_path: Path) -> bool:
    """Download the shared keys (translation, zbern token) from the release and write them into `.env`.

    The asset is optional: a release without it leaves `.env` alone, translation and zbern off. The
    download always replaces an earlier copy, so a rotated key reaches every machine on the next
    `setup`. Returns whether a key was installed."""
    asset = dump_dir() / SECRETS_ASSET
    asset.unlink(missing_ok=True)
    result = subprocess.run(["gh", "release", "download", settings.shared_key_release_tag, "--repo",
                             settings.dump_release_repo, "--pattern", SECRETS_ASSET, "--dir", str(dump_dir())],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0 or not asset.exists():
        typer.echo("no shared keys on the release; translation and the zbern tools stay off "
                   "(set SUPERTEXT_API_KEY / ZBERN_MCP_TOKEN in .env yourself, or ask the team to run "
                   "`dump publish-key`)")
        return False
    shared = parse_env(asset.read_text(encoding="utf-8"))
    asset.unlink()                                 # the key lives in .env only
    if not shared:
        typer.echo(f"{SECRETS_ASSET} on the release holds none of {', '.join(SHARED_KEYS)}")
        return False
    current = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    env_path.write_text(merge_env(current, shared), encoding="utf-8")
    typer.echo(f"shared keys written to {env_path.name}: {', '.join(sorted(shared))}")
    return True


def ensure_env_file(root: Path) -> bool:
    """Copy `.env.example` to `.env` when there is no `.env` yet, so `setup` needs no manual step.
    An existing `.env` is never touched. Returns whether it was created."""
    env, example = root / ".env", root / ".env.example"
    if env.exists() or not example.exists():
        return False
    shutil.copyfile(example, env)
    typer.echo(".env created from .env.example")
    return True


@dump_app.command("publish-key")
def publish_key_cmd() -> None:
    """Upload SUPERTEXT_API_KEY and ZBERN_MCP_TOKEN from your .env to the private release, for everyone's `setup`."""
    settings = load_settings()
    values = {"SUPERTEXT_API_KEY": settings.supertext_api_key or "",
              "ZBERN_MCP_TOKEN": settings.zbern_mcp_token.get_secret_value() if settings.zbern_mcp_token else ""}
    if not any(values.values()):
        raise typer.BadParameter("neither SUPERTEXT_API_KEY nor ZBERN_MCP_TOKEN is set in .env; nothing to publish")
    dump_dir().mkdir(parents=True, exist_ok=True)
    asset = dump_dir() / SECRETS_ASSET
    asset.write_text(shared_env_text(values), encoding="utf-8")
    try:
        _run(["gh", "release", "upload", settings.shared_key_release_tag, str(asset), "--repo",
              settings.dump_release_repo, "--clobber"], what="upload the shared keys")
    finally:
        asset.unlink(missing_ok=True)
    published = ", ".join(k for k, v in values.items() if v)
    typer.echo(f"{SECRETS_ASSET} ({published}) published to release {settings.shared_key_release_tag} of "
               f"{settings.dump_release_repo}; collaborators get it on their next `swiss-grounding setup`")


def setup_cmd(skip_models: bool = typer.Option(False, "--skip-models", help="do not pre-download models")) -> None:
    """Download the prebuilt database, verify it, restore it, and pre-download the local models."""
    ensure_env_file(repo_root())
    settings = load_settings()
    # One folder per release, so parts of an earlier release never mix in. The manifest is always fetched
    # anew and names the parts; parts already in the folder (e.g. copied from a USB stick) are kept, and a
    # wrong one fails the checksum.
    directory = dump_dir() / settings.dump_release_tag
    directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    _gh_download(settings, directory, MANIFEST_NAME, clobber=True)
    manifest = _json_module.loads((directory / MANIFEST_NAME).read_text())
    _gh_download(settings, directory, *(part["name"] for part in manifest["parts"]))
    verify_parts(directory, manifest)
    dump = join_parts(directory, manifest, directory / "corpus.dump")
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
    install_shared_key(settings, repo_root() / ".env")
    if not skip_models:
        from swiss_grounding.app import build_query_provider, build_reranker
        from swiss_grounding.serving.reranker import detect_device
        if settings.serving_index == "openai-3l" and not settings.openai_api_key:
            typer.echo("OPENAI_API_KEY is not set: add it to .env before serving; every question is embedded with "
                       "OpenAI's text-embedding-3-large")
        else:
            build_query_provider(settings).embed(["warm up"])
        build_reranker(settings, detect_device()).score("warm up", ["warm up"])
        typer.echo("the reranker is downloaded and the query embedder is ready")
