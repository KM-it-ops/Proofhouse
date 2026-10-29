"""Deploying a finished site when you say so, with the hosting service's own tool."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from proofhouse import addons, cli, deploy, providers


@pytest.fixture
def made(tmp_path: Path) -> Path:
    site = tmp_path / "make-brew" / "site"
    site.mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html><title>Brew</title>", encoding="utf-8")
    return tmp_path / "make-brew"


def _fake_tool(tmp_path: Path, exit_code: int = 0) -> list[str]:
    script = tmp_path / "fake_host.py"
    script.write_text("import sys, pathlib\nassert (pathlib.Path(sys.argv[1]) / 'index.html').is_file()\n"
                      "print('Uploading... done')\nprint(f'Website URL: https://{sys.argv[2]}.example.app.')\n"
                      f"sys.exit({exit_code})\n", encoding="utf-8")
    return [sys.executable, str(script), "{folder}", "{name}"]


def _add_target(command: list[str]) -> None:
    path = providers.proofhouse_home() / "deploy_targets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": deploy.DEPLOY_SCHEMA, "targets": [{"id": "myhost", "command": command}]}), encoding="utf-8")


def test_a_dry_run_shows_the_exact_command_for_the_finished_site(made: Path, capsys) -> None:
    assert cli.main(["deploy", str(made), "--to", "netlify", "--dry-run"]) == 0
    assert capsys.readouterr().out.strip() == f"netlify deploy --dir {made.resolve() / 'site'} --prod"
    done = deploy.deploy(made, "cloudflare", dry_run=True)
    assert done.command[-2:] == ["--project-name", "make-brew"]


def test_any_tool_you_add_deploys_and_the_address_is_kept(tmp_path: Path, made: Path, capsys) -> None:
    _add_target(_fake_tool(tmp_path))
    assert cli.main(["deploy", str(made), "--to", "myhost", "--name", "brew"]) == 0
    assert capsys.readouterr().out.strip() == "https://brew.example.app"
    (record,) = [json.loads(line) for line in (providers.proofhouse_home() / "deploys.jsonl").read_text(encoding="utf-8").splitlines()]
    assert record["status"] == "deployed" and record["url"] == "https://brew.example.app" and record["exit"] == 0


def test_a_failed_deploy_is_reported_and_not_retried(tmp_path: Path, made: Path) -> None:
    _add_target(_fake_tool(tmp_path, exit_code=3))
    assert cli.main(["deploy", str(made), "--to", "myhost"]) == 7
    assert deploy.deploy(made, "myhost").url is None


def test_nothing_runs_without_a_site_a_known_target_or_the_tool(tmp_path: Path, made: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(deploy.DeployError, match="index.html"):
        deploy.deploy(tmp_path / "empty", "netlify")
    with pytest.raises(deploy.DeployError, match="known"):
        deploy.deploy(made, "nowhere")
    if shutil.which("surge") is None:
        with pytest.raises(deploy.DeployError, match="npm install -g surge"):
            deploy.deploy(made, "surge")
    with pytest.raises(deploy.DeployError):
        deploy._check({"id": "x", "command": ["tool", "--no-folder"]}, "test")


def test_an_add_on_can_bring_a_deploy_target(tmp_path: Path, made: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "addon.json").write_text(json.dumps({"name": "edge-host", "deploy_targets": [{"id": "edge", "command": ["edge", "push", "{folder}"]}]}),
                                     encoding="utf-8")
    addons.install(pack)
    assert deploy.deploy(made, "edge", dry_run=True).command == ["edge", "push", str(made.resolve() / "site")]


def test_a_tool_found_on_the_path_is_started_by_the_path_it_was_found_at(made: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # on Windows an npm tool is vercel.cmd; starting the bare name fails with "file not found"
    found = str(made / "vercel.cmd")
    monkeypatch.setattr(deploy.shutil, "which", lambda name: found if name == "vercel" else None)
    started: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> object:
        started.append(command)
        return type("Run", (), {"returncode": 0, "stdout": "Production: https://brew.vercel.app", "stderr": ""})()

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)
    assert deploy.deploy(made, "vercel").url == "https://brew.vercel.app"
    assert started[0][0] == found
    assert deploy.deploy(made, "vercel", dry_run=True).command[0] == "vercel"


def test_a_name_the_target_cannot_use_is_said_not_dropped(made: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from proofhouse import cli

    assert cli.main(["deploy", str(made), "--to", "vercel", "--name", "harbor-demo", "--dry-run"]) == 0
    err = capsys.readouterr().err
    assert "vercel" in err and "folder" in err and "harbor-demo" in err
    assert cli.main(["deploy", str(made), "--to", "cloudflare", "--name", "harbor-demo", "--dry-run"]) == 0
    assert capsys.readouterr().err == ""
