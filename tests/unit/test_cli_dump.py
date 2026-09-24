import importlib
import pathlib
import subprocess

import pytest
import typer
from typer.testing import CliRunner

from swiss_grounding.cli import main, serving_commands


def test_serving_init_is_registered():
    result = CliRunner().invoke(main.app, ["serving", "--help"])
    assert result.exit_code == 0
    assert "init" in result.output


def test_repo_root_has_docker_compose_file():
    root = serving_commands.repo_root()
    assert (root / "docker-compose.yml").exists()


def test_dump_dir_is_under_repo_root():
    assert serving_commands.dump_dir().is_relative_to(serving_commands.repo_root())


def test_repo_root_raises_when_docker_compose_is_missing(tmp_path, monkeypatch):
    fake_file = tmp_path / "src" / "swiss_grounding" / "cli" / "serving_commands.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("")
    monkeypatch.setattr(serving_commands, "__file__", str(fake_file))
    with pytest.raises(RuntimeError, match="docker-compose.yml"):
        serving_commands.repo_root()


def test_compose_wraps_called_process_error_in_bad_parameter(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    with pytest.raises(typer.BadParameter, match="docker compose failed: is Docker running"):
        serving_commands._compose("up", "-d")


def test_compose_wraps_file_not_found_in_bad_parameter(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    with pytest.raises(typer.BadParameter, match="docker is not installed"):
        serving_commands._compose("up", "-d")


def test_run_wraps_gh_failure_with_actionable_message(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    with pytest.raises(typer.BadParameter, match="gh auth login"):
        serving_commands._run(["gh", "release", "download"])


def test_run_wraps_missing_executable(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    with pytest.raises(typer.BadParameter, match="gh is not installed"):
        serving_commands._run(["gh", "release", "download"])


def test_cli_help_works_even_when_repo_root_would_fail(monkeypatch):
    """`main.py` imports `serving_commands` for every command; `repo_root()` must never run at
    import time, or a broken repo root would break the whole CLI, not just `dump`/`setup`."""
    def broken_repo_root():
        raise RuntimeError("repo root has no docker-compose.yml")

    monkeypatch.setattr(serving_commands, "repo_root", broken_repo_root)
    reloaded_main = importlib.reload(main)
    try:
        result = CliRunner().invoke(reloaded_main.app, ["--help"])
        assert result.exit_code == 0
    finally:
        importlib.reload(main)


class _Settings:
    dump_release_tag = "corpus-latest"
    dump_release_repo = "thedionysus/swisscom-hackathon"
    supertext_api_key = "k-123"
    zbern_mcp_token = None


def test_publish_key_uploads_the_key_from_env_and_removes_the_temp_file(tmp_path, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["content"] = pathlib.Path(cmd[4]).read_text(encoding="utf-8")

    monkeypatch.setattr(serving_commands, "load_settings", lambda: _Settings())
    monkeypatch.setattr(serving_commands, "dump_dir", lambda: tmp_path)
    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    serving_commands.publish_key_cmd()
    assert seen["cmd"][:3] == ["gh", "release", "upload"] and "--clobber" in seen["cmd"]
    assert seen["content"] == "SUPERTEXT_API_KEY=k-123\n"
    assert not (tmp_path / "supertext.env").exists()


def test_publish_key_uploads_the_zbern_token_beside_the_translation_key(tmp_path, monkeypatch):
    from pydantic import SecretStr

    class Both(_Settings):
        zbern_mcp_token = SecretStr("z-456")
    seen = {}
    monkeypatch.setattr(serving_commands, "load_settings", lambda: Both())
    monkeypatch.setattr(serving_commands, "dump_dir", lambda: tmp_path)
    monkeypatch.setattr(serving_commands.subprocess, "run",
                        lambda cmd, **kw: seen.setdefault("content", pathlib.Path(cmd[4]).read_text(encoding="utf-8")))
    serving_commands.publish_key_cmd()
    assert seen["content"] == "SUPERTEXT_API_KEY=k-123\nZBERN_MCP_TOKEN=z-456\n"


def test_publish_key_refuses_without_a_key(monkeypatch):
    class NoKey(_Settings):
        supertext_api_key = None
    monkeypatch.setattr(serving_commands, "load_settings", lambda: NoKey())
    with pytest.raises(typer.BadParameter, match="SUPERTEXT_API_KEY"):
        serving_commands.publish_key_cmd()


def test_install_shared_key_writes_the_downloaded_key_into_env(tmp_path, monkeypatch):
    class Done:
        returncode = 0

    def fake_run(cmd, **kwargs):
        (tmp_path / "supertext.env").write_text("SUPERTEXT_API_KEY=k-123\n")
        return Done()

    monkeypatch.setattr(serving_commands, "dump_dir", lambda: tmp_path)
    monkeypatch.setattr(serving_commands.subprocess, "run", fake_run)
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=x\n# SUPERTEXT_API_KEY=\n")
    assert serving_commands.install_shared_key(_Settings(), env) is True
    assert env.read_text() == "DATABASE_URL=x\nSUPERTEXT_API_KEY=k-123\n"
    assert not (tmp_path / "supertext.env").exists()


def test_install_shared_key_is_optional(tmp_path, monkeypatch):
    class Failed:
        returncode = 1

    monkeypatch.setattr(serving_commands, "dump_dir", lambda: tmp_path)
    monkeypatch.setattr(serving_commands.subprocess, "run", lambda cmd, **kw: Failed())
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=x\n")
    assert serving_commands.install_shared_key(_Settings(), env) is False
    assert env.read_text() == "DATABASE_URL=x\n"
