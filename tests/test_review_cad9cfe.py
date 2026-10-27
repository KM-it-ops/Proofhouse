"""Failing tests for review-cad9cfe. Run from the repo root:
uv run --extra test pytest tests/test_review_cad9cfe.py -q
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from proofhouse import host
from scripts.stage3_hard_cases import ROOT, _scrub

BS = chr(92)


# cad9cfe-F1: the scrubber that keeps the user's profile out of the committed report only knows forward slashes.
def test_f1_scrub_removes_a_windows_profile_path_written_with_backslashes(tmp_path: Path) -> None:
    text = f'File "C:{BS}Users{BS}someone{BS}AppData{BS}Roaming{BS}uv{BS}python{BS}x.py", line 1'
    assert "someone" not in _scrub(text, tmp_path)


def test_f1_scrub_removes_the_same_path_as_json_writes_it(tmp_path: Path) -> None:
    text = f'"C:{BS*2}Users{BS*2}someone{BS*2}AppData{BS*2}x.json"'
    assert "someone" not in _scrub(text, tmp_path)


# cad9cfe-F2: rounds saved before this PR (no "status") are read as passed even when their checks did not run.
def _site(folder: Path) -> Path:
    shutil.copytree(ROOT / "examples" / "host-mode" / "site", folder)
    return folder


def _record(site: Path, out: Path) -> int:
    return host.run_record("site", site, out=out, request="a site", agent="cursor", score=9, judge=None,
                           judge_score=None, judge_note=None, allow_commands=False, as_json=True)


def test_f2_an_older_round_whose_browser_check_never_ran_is_not_delivered_as_passed(tmp_path: Path) -> None:
    site, out = _site(tmp_path / "site"), tmp_path / "out"
    assert _record(site, out) == host.NOT_MEASURED_EXIT
    # Rewrite v1's round the way 0.9 saved it: passed true, no status. v1/checks.json still shows the unrun check.
    record = json.loads((out / "record.json").read_text(encoding="utf-8"))
    record["rounds"] = [{"version": 1, "score": 9, "passed": True, "agent": "cursor"}]
    (out / "record.json").write_text(json.dumps(record), encoding="utf-8")
    assert any(row.get("ok") is None for row in json.loads((out / "v1" / "checks.json").read_text(encoding="utf-8")))
    _record(site, out)
    record = json.loads((out / "record.json").read_text(encoding="utf-8"))
    assert record["best_status"] != "passed", record["rounds"]


def test_f2_shipped_example_records_do_not_call_an_unrun_check_passed() -> None:
    wrong = []
    for path in sorted((ROOT / "examples" / "host-mode").glob("*/record.json")):
        for row in json.loads(path.read_text(encoding="utf-8")).get("rounds", []):
            checks = path.parent / f"v{row['version']}" / "checks.json"
            if not checks.is_file():
                continue
            unrun = [c["check"] for c in json.loads(checks.read_text(encoding="utf-8")) if c.get("ok") is None]
            if unrun and host._round_status(row) == "passed":
                wrong.append(f"{path.parent.name} v{row['version']}: {unrun}")
    assert not wrong, wrong


# cad9cfe-F3: the MCP example delivers a server that is not the version its record scored and judged.
def test_f3_delivered_mcp_server_is_the_version_the_record_scored() -> None:
    record = ROOT / "examples" / "host-mode" / "mcp-record"
    best = json.loads((record / "record.json").read_text(encoding="utf-8"))["best_version"]
    delivered = (record / "mcp" / "server.py").read_bytes()
    scored = (record / f"v{best}" / "mcp" / "server.py").read_bytes()
    assert delivered == scored, "delivered server.py differs from the scored version the record names"
