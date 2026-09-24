import subprocess

import pytest
import typer

from swiss_grounding.cli import serving_commands


def test_repo_root_has_docker_compose_file():
    assert (serving_commands.REPO_ROOT / "docker-compose.yml").exists()


def test_dump_dir_is_under_repo_root():
    assert serving_commands.DUMP_DIR.is_relative_to(serving_commands.REPO_ROOT)


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
