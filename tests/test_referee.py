"""Host referee: the agent runs the loop; Proofhouse runs the check and keeps the record."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from proofhouse import cli
from proofhouse import referee

CHECK = (
    'python -c "import os, sys; ok = os.path.isfile(\'done.txt\') and open(\'done.txt\').read() == \'yes\'; '
    "sys.exit(0 if ok else 1)\""
)


def _start(work: Path, out: Path, *, rounds: int = 20, allow: bool = True, extra: list[str] | None = None) -> int:
    args = [
        "referee",
        "start",
        "make tests pass",
        "--check",
        CHECK,
        "--folder",
        str(work),
        "--out",
        str(out),
        "--rounds",
        str(rounds),
        "--agent",
        "cursor",
    ]
    if allow:
        args.append("--allow-commands")
    if extra:
        args.extend(extra)
    return cli.main(args)


def _round(out: Path, summary: str, *, allow: bool = True, json_out: bool = False) -> int:
    args = ["referee", "round", str(out), "--summary", summary, "--agent", "cursor"]
    if allow:
        args.append("--allow-commands")
    if json_out:
        args.append("--json")
    return cli.main(args)


def _status(out: Path, *, json_out: bool = False) -> int:
    args = ["referee", "status", str(out)]
    if json_out:
        args.append("--json")
    return cli.main(args)


def test_start_refuses_without_allow_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out, allow=False) == 2
    assert "allow-commands" in capsys.readouterr().err.lower()


def test_round_refuses_without_allow_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out) == 0
    assert _round(out, "first", allow=False) == 2
    assert "allow-commands" in capsys.readouterr().err.lower()


def test_passes_on_round_two_after_writing_done_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out) == 0
    assert _round(out, "still working") == 10
    assert "continue" in capsys.readouterr().out.lower()
    (work / "done.txt").write_text("yes", encoding="utf-8")
    capsys.readouterr()
    assert _round(out, "wrote done.txt") == 0
    out_text = capsys.readouterr().out.lower()
    assert "passed" in out_text
    data = json.loads((out / "loop.json").read_text(encoding="utf-8"))
    assert data["status"] == "done"
    lines = (out / "rounds.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    last = json.loads(lines[-1])
    assert last["check_passed"] is True and last["round"] == 2


def test_stops_at_rounds_limit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out, rounds=2) == 0
    assert _round(out, "one") == 10
    capsys.readouterr()
    assert _round(out, "two") == 11
    assert "rounds" in capsys.readouterr().out.lower()
    assert json.loads((out / "loop.json").read_text(encoding="utf-8"))["status"] == "stopped"


def test_stops_on_time_limit_but_still_runs_last_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out, extra=["--for", "1s"]) == 0
    time.sleep(1.1)
    (work / "done.txt").write_text("yes", encoding="utf-8")
    assert _round(out, "late pass") == 0
    assert "passed" in capsys.readouterr().out.lower()
    assert json.loads((out / "loop.json").read_text(encoding="utf-8"))["status"] == "done"


def test_refuses_round_after_done(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    (work / "done.txt").write_text("yes", encoding="utf-8")
    assert _start(work, out) == 0
    assert _round(out, "done") == 0
    capsys.readouterr()
    assert _round(out, "again") == 2
    err = capsys.readouterr().err.lower()
    assert "running" in err or "status" in err


def test_dir_inside_work_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work = tmp_path / "work"
    work.mkdir()
    out = work / "record"
    assert _start(work, out) == 2
    err = capsys.readouterr().err.lower()
    assert "out" in err or "folder" in err


def test_secret_env_does_not_leak_into_check_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "fake-value-for-redaction-test-123456"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    leak_check = (
        'python -c "import os, sys; print(os.environ.get(\'OPENAI_API_KEY\',\'\')); sys.exit(1)"'
    )
    args = [
        "referee",
        "start",
        "x",
        "--check",
        leak_check,
        "--folder",
        str(work),
        "--out",
        str(out),
        "--allow-commands",
    ]
    assert cli.main(args) == 0
    assert cli.main(["referee", "round", str(out), "--summary", "leak test", "--allow-commands"]) == 10
    row = json.loads((out / "rounds.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert secret not in row["check_output"]
    assert "[redacted]" in row["check_output"] or row["check_output"].strip() == ""


def test_secret_looking_env_is_not_passed_to_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_SERVICE_TOKEN", "tok-abcdef123456")
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    check = "python -c \"import os, sys; print(os.environ.get('MY_SERVICE_TOKEN', 'absent')); sys.exit(1)\""
    assert cli.main(["referee", "start", "x", "--check", check, "--folder", str(work), "--out", str(out), "--allow-commands"]) == 0
    cli.main(["referee", "round", str(out), "--summary", "env", "--allow-commands"])
    row = json.loads((out / "rounds.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert "absent" in row["check_output"]
    assert "tok-abcdef123456" not in row["check_output"]


def test_tampered_check_is_refused(tmp_path: Path) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert cli.main(["referee", "start", "x", "--check", "python -c \"import sys; sys.exit(1)\"", "--folder", str(work), "--out", str(out), "--allow-commands"]) == 0
    record = json.loads((out / "loop.json").read_text(encoding="utf-8"))
    record["check"] = "python -c \"print('evil')\""
    (out / "loop.json").write_text(json.dumps(record), encoding="utf-8")
    assert cli.main(["referee", "round", str(out), "--summary", "t", "--allow-commands"]) == 2
    assert (out / "rounds.jsonl").read_text(encoding="utf-8") == ""


def test_damaged_record_is_a_clean_error(tmp_path: Path) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert cli.main(["referee", "start", "x", "--check", "python -c \"import sys; sys.exit(1)\"", "--folder", str(work), "--out", str(out), "--allow-commands"]) == 0
    record = json.loads((out / "loop.json").read_text(encoding="utf-8"))
    del record["rounds_limit"]
    (out / "loop.json").write_text(json.dumps(record), encoding="utf-8")
    assert cli.main(["referee", "round", str(out), "--summary", "t", "--allow-commands"]) == 2


def test_long_check_output_is_trimmed(tmp_path: Path) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    loud = 'python -c "print(\'x\' * 5000); import sys; sys.exit(1)"'
    args = [
        "referee",
        "start",
        "x",
        "--check",
        loud,
        "--folder",
        str(work),
        "--out",
        str(out),
        "--allow-commands",
    ]
    assert cli.main(args) == 0
    cli.main(["referee", "round", str(out), "--summary", "long", "--allow-commands"])
    row = json.loads((out / "rounds.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert len(row["check_output"]) <= 4000
    assert row["check_output"].startswith("…")


def test_status_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out, rounds=5) == 0
    assert _round(out, "first") == 10
    capsys.readouterr()
    assert _status(out, json_out=True) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["goal"] == "make tests pass"
    assert data["rounds_used"] == 1
    assert data["rounds_limit"] == 5
    assert data["status"] == "running"
    assert data["last_check_passed"] is False


def test_start_writes_loop_json(tmp_path: Path) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    assert _start(work, out) == 0
    data = json.loads((out / "loop.json").read_text(encoding="utf-8"))
    assert data["mode"] == "host"
    assert data["status"] == "running"
    assert data["check"] == CHECK
    assert (out / "rounds.jsonl").read_text(encoding="utf-8") == ""


def test_time_stop_without_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work, out = tmp_path / "work", tmp_path / "out"
    work.mkdir()
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tick = started + timedelta(seconds=10)

    def fake_now() -> datetime:
        return tick

    monkeypatch.setattr(referee, "_utc_now", fake_now)
    referee.start_referee(
        "g",
        check=CHECK,
        workdir=work,
        out_dir=out,
        max_rounds=20,
        max_seconds=5.0,
        agent="cursor",
        command_timeout=300,
        allow_commands=True,
    )
    loop = json.loads((out / "loop.json").read_text(encoding="utf-8"))
    loop["started_at"] = started.isoformat(timespec="seconds")
    (out / "loop.json").write_text(json.dumps(loop, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    code = referee.run_round(out, "late", agent="cursor", allow_commands=True, now=fake_now)
    assert code == 11
    assert "time" in capsys.readouterr().out.lower()
