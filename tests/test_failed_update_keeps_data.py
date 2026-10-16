"""A failed install or update leaves your existing settings and files as they were, with nothing left behind."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from proofhouse import addons, cli, media, providers, train

AGENT = "---\nname: review-bot\ndescription: Reviews pull requests.\n---\nCheck every diff for secrets.\n"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: folder))
    return folder


def _fail_replace(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)


def _leftovers(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*") if p.name.endswith(".proofhouse-tmp")]


def _run_failing(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()
    assert cli.main(argv, prog="proofhouse") != 0
    err = capsys.readouterr().err
    assert "disk full" in err and "Traceback" not in err


def test_write_atomic_keeps_the_old_file_when_the_swap_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "settings.json"
    target.write_text("old\n", encoding="utf-8")
    _fail_replace(monkeypatch)
    with pytest.raises(OSError):
        providers.write_atomic(target, "new\n")
    assert target.read_text(encoding="utf-8") == "old\n"
    assert _leftovers(tmp_path) == []


def test_a_failed_media_add_keeps_your_services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    first = {"id": "my-gpu", "kinds": ["image"], "base_url": "http://localhost:7860", "key_env": None, "auth": "none",
             "unit": "image", "submit": {"path": "/generate", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"]}}
    (tmp_path / "a.json").write_text(json.dumps(first), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "a.json")]) == 0
    before = media.user_path().read_bytes()

    (tmp_path / "b.json").write_text(json.dumps({**first, "id": "other-gpu"}), encoding="utf-8")
    _fail_replace(monkeypatch)
    _run_failing(["media", "add", "--from", str(tmp_path / "b.json")], capsys)
    assert media.user_path().read_bytes() == before
    assert _leftovers(media.user_path().parent) == []


def test_a_failed_train_add_keeps_your_services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    first = {"id": "my-lora", "command": [sys.executable, "tune.py", "--data", "{train}", "--out", "{out}"]}
    (tmp_path / "a.json").write_text(json.dumps(first), encoding="utf-8")
    assert cli.main(["train", "add", "--from", str(tmp_path / "a.json")]) == 0
    before = train.user_path().read_bytes()

    (tmp_path / "b.json").write_text(json.dumps({**first, "id": "other-lora"}), encoding="utf-8")
    _fail_replace(monkeypatch)
    _run_failing(["train", "add", "--from", str(tmp_path / "b.json")], capsys)
    assert train.user_path().read_bytes() == before
    assert _leftovers(train.user_path().parent) == []


def test_a_failed_add_on_update_keeps_the_installed_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = {"schema": "proofhouse.addon/v1", "name": "acme-pack", "version": "1.0",
            "providers": [{"id": "acme", "base_url": "https://api.acme.example/v1", "key_env": "ACME_API_KEY"}]}
    folder = tmp_path / "pack"
    folder.mkdir()
    (folder / "addon.json").write_text(json.dumps(pack), encoding="utf-8")
    addons.install(folder)
    installed = addons.packs_dir() / "acme-pack" / "addon.json"
    before = installed.read_bytes()

    (folder / "addon.json").write_text(json.dumps({**pack, "version": "2.0"}), encoding="utf-8")
    _fail_replace(monkeypatch)
    with pytest.raises(OSError):
        addons.install(folder)
    assert installed.read_bytes() == before
    assert _leftovers(installed.parent) == []


def test_a_failed_reinstall_into_a_tool_keeps_the_installed_agent_and_its_record(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    assert cli.main(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], prog="proofhouse") == 0
    placed = home / ".claude" / "agents" / "review-bot.md"
    records = providers.proofhouse_home() / "installs"
    before = placed.read_bytes(), {p.name: p.read_bytes() for p in records.iterdir()}

    (tmp_path / "agent.md").write_text(AGENT.replace("secrets", "secrets and keys"), encoding="utf-8")
    real_replace = os.replace
    _fail_replace(monkeypatch)
    _run_failing(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], capsys)
    assert (placed.read_bytes(), {p.name: p.read_bytes() for p in records.iterdir()}) == before
    assert _leftovers(home) == [] and _leftovers(records) == []
    # once the disk is fine again, uninstall still removes it cleanly
    monkeypatch.setattr(os, "replace", real_replace)
    assert cli.main(["uninstall", "agent", "review-bot", "--from", "claude"], prog="proofhouse") == 0
    assert not placed.exists()


def _fail_second_replace(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool's file is swapped in, then saving the install record fails."""
    real_replace = os.replace
    calls: list[object] = []

    def second_fails(src: object, dst: object) -> None:
        calls.append(dst)
        if len(calls) == 2:
            raise OSError("disk full")
        real_replace(src, dst)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "replace", second_fails)


def test_a_reinstall_whose_record_cannot_be_saved_puts_the_old_agent_back(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    assert cli.main(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], prog="proofhouse") == 0
    placed = home / ".claude" / "agents" / "review-bot.md"
    records = providers.proofhouse_home() / "installs"
    before = placed.read_bytes(), {p.name: p.read_bytes() for p in records.iterdir()}

    (tmp_path / "agent.md").write_text(AGENT.replace("secrets", "secrets and keys"), encoding="utf-8")
    real_replace = os.replace
    _fail_second_replace(monkeypatch)
    _run_failing(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], capsys)
    assert (placed.read_bytes(), {p.name: p.read_bytes() for p in records.iterdir()}) == before
    assert _leftovers(home) == [] and _leftovers(records) == []
    monkeypatch.setattr(os, "replace", real_replace)
    assert cli.main(["uninstall", "agent", "review-bot", "--from", "claude"], prog="proofhouse") == 0


def test_a_first_install_whose_record_cannot_be_saved_leaves_nothing_behind(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    real_replace = os.replace
    _fail_second_replace(monkeypatch)
    _run_failing(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], capsys)
    placed = home / ".claude" / "agents" / "review-bot.md"
    records = providers.proofhouse_home() / "installs"
    assert not placed.exists() and not any(records.glob("*.json"))
    assert _leftovers(home) == []
    # trying again once the disk is fine works, with no --force needed
    monkeypatch.setattr(os, "replace", real_replace)
    assert cli.main(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude"], prog="proofhouse") == 0
    assert placed.read_text(encoding="utf-8") == AGENT


def test_a_forced_replace_whose_record_cannot_be_saved_keeps_your_file_and_no_stray_copy(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    placed = home / ".claude" / "agents" / "review-bot.md"
    placed.parent.mkdir(parents=True)
    placed.write_text("my own agent\n", encoding="utf-8")
    before = placed.read_bytes()
    (tmp_path / "agent.md").write_text(AGENT, encoding="utf-8")
    _fail_second_replace(monkeypatch)
    _run_failing(["install", "agent", str(tmp_path / "agent.md"), "--into", "claude", "--force"], capsys)
    assert placed.read_bytes() == before
    assert not any((providers.proofhouse_home() / "install-backups").glob("*"))
    assert _leftovers(home) == []


@pytest.mark.parametrize("argv", [
    ["providers", "add", "other-api", "--base-url", "https://api.other.example/v1", "--key-env", "OTHER_API_KEY"],
    ["providers", "remove", "my-api"],
    ["providers", "price", "my-api", "some-model", "--input", "1", "--output", "2"],
    ["media", "price", "openai-images", "some-model", "--usd", "0.04"],
    ["train", "price", "openai", "some-model", "--usd-per-million", "25"],
])
def test_a_failed_save_of_your_providers_file_keeps_it_and_says_so(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["providers", "add", "my-api", "--base-url", "https://api.mine.example/v1", "--key-env", "MY_API_KEY"]) == 0
    before = providers.user_path().read_bytes()
    _fail_replace(monkeypatch)
    _run_failing(argv, capsys)
    assert providers.user_path().read_bytes() == before
    assert _leftovers(providers.user_path().parent) == []


def test_a_failed_first_add_on_install_leaves_no_empty_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "pack"
    folder.mkdir()
    (folder / "addon.json").write_text(json.dumps({"schema": "proofhouse.addon/v1", "name": "acme-pack", "version": "1.0"}), encoding="utf-8")
    _fail_replace(monkeypatch)
    with pytest.raises(OSError):
        addons.install(folder)
    assert not (addons.packs_dir() / "acme-pack").exists()


@pytest.mark.skipif(os.name == "nt", reason="permission bits are a POSIX idea; Windows has only read-only")
def test_a_rewritten_file_keeps_its_permissions(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    target.write_text("{}\n", encoding="utf-8")
    target.chmod(0o600)
    providers.write_atomic(target, '{"a": 1}\n')
    assert target.stat().st_mode & 0o777 == 0o600
