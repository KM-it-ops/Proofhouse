"""Host mode launch: one folder, many parts, shared names and facts."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from proofhouse import cli

SITE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Brew Brand</title></head>'
    '<body><h1>Brew Brand</h1><a href="menu.html">Menu</a></body></html>'
)
MENU = SITE.replace("Brew Brand</title>", "Menu</title>").replace('<a href="menu.html">Menu</a>', "<p>Opens at 5 AM</p>")
SKILL = (
    "---\nname: brew-helper\ndescription: Use when a customer asks about Brew Brand.\n---\n"
    "# Brew helper\nBrew Brand serves fresh coffee. Opens at 5 AM.\n"
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("host mode tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(Path("no-such-browser")))
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def write_launch(
    folder: Path,
    *,
    shared: list[str] | None = None,
    facts: list[str] | None = None,
    avoid: list[str] | None = None,
    parts: list[dict[str, str]] | None = None,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    shared = shared if shared is not None else ["Brew Brand"]
    facts = facts if facts is not None else ["Opens at 5 AM"]
    avoid = avoid if avoid is not None else []
    if parts is None:
        parts = [
            {"id": "site", "kind": "site", "path": "site"},
            {"id": "announce", "kind": "copy", "path": "announcement/copy.md"},
            {"id": "helper", "kind": "skill", "path": "brew-helper"},
        ]
    manifest = {
        "name": "Brew Brand",
        "goal": "Launch Brew Brand coffee to commuters",
        "tone": "warm and quick",
        "shared_names": shared,
        "facts": facts,
        "avoid": avoid,
        "parts": parts,
    }
    (folder / "launch.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for part in parts:
        kind, rel = part["kind"], part["path"]
        target = folder / rel
        if kind == "site":
            target.mkdir(parents=True, exist_ok=True)
            (target / "index.html").write_text(SITE, encoding="utf-8")
            (target / "menu.html").write_text(MENU, encoding="utf-8")
        elif kind == "copy":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Brew Brand is here\nOpens at 5 AM. Order in one tap.\n", encoding="utf-8")
        elif kind == "skill":
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text(SKILL, encoding="utf-8")
        elif kind == "video":
            target.mkdir(parents=True, exist_ok=True)
            (target / "shot-01.png").write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            script = {
                "title": "Brew Brand",
                "voiceover": "Brew Brand opens at 5 AM.",
                "music": "lofi beats",
                "shots": [{"seconds": 2, "visual": "cup", "caption": "Brew Brand", "file": "shot-01.png"}],
            }
            (target / "script.json").write_text(json.dumps(script), encoding="utf-8")
    return folder


def test_check_launch_passes_three_parts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH")
    assert cli.main(["check", "launch", str(launch), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows and all(row.get("ok") is not False for row in rows)


def test_check_launch_fails_when_shared_name_missing_in_one_part(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH")
    copy_path = launch / "announcement" / "copy.md"
    copy_path.write_text("Generic coffee shop opens early.\n", encoding="utf-8")
    assert cli.main(["check", "launch", str(launch)]) != 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "Brew Brand" in out and "announce" in out.lower()


def test_check_launch_fails_when_avoid_word_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH", avoid=["competitor"])
    (launch / "announcement" / "copy.md").write_text(
        "# Brew Brand\nAvoid the competitor. Opens at 5 AM.\n", encoding="utf-8")
    assert cli.main(["check", "launch", str(launch)]) != 0
    assert "competitor" in capsys.readouterr().out.lower()


def test_check_launch_fails_when_fact_missing_everywhere(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH", facts=["Opens at 5 AM", "Free refills"])
    assert cli.main(["check", "launch", str(launch)]) != 0
    assert "Free refills" in capsys.readouterr().out


def test_check_launch_fails_on_bad_part_kind(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH", parts=[
        {"id": "site", "kind": "site", "path": "site"},
        {"id": "bad", "kind": "poster", "path": "poster"},
    ])
    assert cli.main(["check", "launch", str(launch)]) != 0
    assert "poster" in capsys.readouterr().out.lower()


def test_check_launch_fails_on_path_traversal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH", parts=[
        {"id": "site", "kind": "site", "path": "site"},
        {"id": "evil", "kind": "copy", "path": "../secret.md"},
    ])
    assert cli.main(["check", "launch", str(launch)]) != 0
    captured = capsys.readouterr()
    assert "inside" in (captured.out + captured.err).lower()


def test_check_launch_fails_on_symlink(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH")
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    try:
        (launch / "site" / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("this machine does not allow symbolic links")
    assert cli.main(["check", "launch", str(launch)]) != 0
    assert "link" in capsys.readouterr().err.lower()


def test_check_launch_fails_on_duplicate_part_ids(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH", parts=[
        {"id": "site", "kind": "site", "path": "site"},
        {"id": "site", "kind": "copy", "path": "announcement/copy.md"},
    ])
    assert cli.main(["check", "launch", str(launch)]) != 0
    assert "duplicate" in capsys.readouterr().out.lower()


def test_check_launch_video_structural_pass_and_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "good", parts=[
        {"id": "site", "kind": "site", "path": "site"},
        {"id": "clip", "kind": "video", "path": "promo"},
    ])
    assert cli.main(["check", "launch", str(launch)]) == 0
    bad = write_launch(tmp_path / "bad", parts=[
        {"id": "site", "kind": "site", "path": "site"},
        {"id": "clip", "kind": "video", "path": "promo"},
    ])
    (bad / "promo" / "shot-01.png").unlink()
    assert cli.main(["check", "launch", str(bad)]) != 0
    assert "shot-01.png" in capsys.readouterr().out


def test_record_launch_delivers_parts_readme_and_best_score(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    launch = write_launch(tmp_path / "LAUNCH")
    out = tmp_path / "deliver"
    assert cli.main([
        "record", "launch", str(launch), "--out", str(out), "--request", "launch brew",
        "--agent", "cursor", "--score", "6",
    ]) == 0
    assert (out / "site" / "index.html").is_file()
    assert (out / "announce" / "final.md").is_file()
    assert (out / "helper" / "brew-helper" / "SKILL.md").is_file()
    assert (out / "launch.json").is_file()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "Brew Brand" in readme and "cursor" in readme and "6" in readme
    assert "| site |" in readme or "site" in readme

    launch2 = write_launch(tmp_path / "LAUNCH2")
    assert cli.main([
        "record", "launch", str(launch2), "--out", str(out), "--request", "launch brew",
        "--agent", "cursor", "--score", "9",
    ]) == 0
    record = json.loads((out / "record.json").read_text(encoding="utf-8"))
    assert record["best_version"] == 2
    assert (out / "v1").is_dir() and (out / "v2").is_dir()


def test_record_launch_refuses_out_inside_launch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    launch = write_launch(tmp_path / "LAUNCH")
    assert cli.main([
        "record", "launch", str(launch), "--out", str(launch / "nested"),
        "--request", "x", "--agent", "cursor",
    ]) != 0
    assert "separate" in capsys.readouterr().err.lower()
