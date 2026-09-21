"""`proofhouse-compiler optimize criteria|verdict|check`: user-declared acceptance criteria per revision."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import checks

OBJECTIVE = "Summarise a security advisory for a SOC audience"
SCORE_WORD = re.compile(r"\bscor(e|es|ed|ing)\b", re.IGNORECASE)
PROMPT_SHORT = "Summarise the advisory for SOC analysts in under 200 words. Lead with severity."
PROMPT_LONG = "Write a long report for the whole company. " * 60  # 480 words, no "SOC"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _json(out: str) -> dict:
    assert out.endswith("\n")
    payload = json.loads(out)
    assert set(payload) == {"command", "status", "data"}
    assert json.dumps(payload, sort_keys=True) + "\n" == out
    return payload


def _case(tmp_path: Path, capsys, name: str = "case") -> Path:
    case_dir = tmp_path / name
    code, _, err = _run(
        ["optimize", "new", "--case", str(case_dir), "--objective", OBJECTIVE, "--model", "Sonnet 5"], capsys
    )
    assert code == 0 and err == ""
    return case_dir


def _record(case_dir: Path, tmp_path: Path, name: str, prompt: str, capsys) -> None:
    prompt_file = tmp_path / name
    prompt_file.write_text(prompt, encoding="utf-8")
    code, _, err = _run(["optimize", "record", "--case", str(case_dir), "--prompt-file", str(prompt_file)], capsys)
    assert code == 0 and err == ""


def _add(case_dir: Path, capsys, *flags: str) -> tuple[int, str, str]:
    return _run(["optimize", "criteria", "add", "--case", str(case_dir), *flags], capsys)


def _case_json(case_dir: Path) -> dict:
    return json.loads((case_dir / "case.json").read_text(encoding="utf-8"))


def _criterion(kind: str, value: str, cid: str = "C1") -> dict:
    return {"id": cid, "kind": kind, "value": value, "note": ""}


def test_evaluate_each_kind_pass_and_fail() -> None:
    prompt = "Summarise the advisory for SOC analysts.\nLead with severity."
    assert checks.evaluate(_criterion("must_contain", "soc analysts"), prompt) == "PASS"
    assert checks.evaluate(_criterion("must_contain", "leaderboard"), prompt) == "FAIL"
    assert checks.evaluate(_criterion("must_not_contain", "LEADERBOARD"), prompt) == "PASS"
    assert checks.evaluate(_criterion("must_not_contain", "severity"), prompt) == "FAIL"
    assert checks.evaluate(_criterion("max_words", "9"), prompt) == "PASS"
    assert checks.evaluate(_criterion("max_words", "8"), prompt) == "FAIL"
    assert checks.evaluate(_criterion("regex", r"^Lead with \w+\.$"), prompt) == "PASS"
    assert checks.evaluate(_criterion("regex", r"^severity"), prompt) == "FAIL"
    assert checks.evaluate(_criterion("manual", "Reads naturally"), prompt) == "UNJUDGED"
    assert checks.evaluate(_criterion("manual", "Reads naturally"), prompt, verdict="pass") == "PASS"
    assert checks.evaluate(_criterion("manual", "Reads naturally"), prompt, verdict="fail") == "FAIL"
    assert checks.KINDS == ("must_contain", "must_not_contain", "max_words", "regex", "manual")
    with pytest.raises(ValueError):
        checks.evaluate(_criterion("quality", "x"), prompt)


def test_criteria_add_and_list_persist_in_case_json(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    code, out, err = _add(case_dir, capsys, "--must-contain", "SOC")
    assert code == 0 and err == ""
    assert out == "criteria: added C1  must_contain     SOC\n"
    code, out, err = _add(case_dir, capsys, "--max-words", "200", "--note", "brief for the SOC")
    assert code == 0 and err == ""
    assert out == "criteria: added C2  max_words        200\n"
    code, out, err = _add(case_dir, capsys, "--manual", "Reads naturally to an analyst", "--json")
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "optimize criteria add"
    assert payload["status"] == "success"
    assert payload["data"]["criterion"] == {
        "id": "C3", "kind": "manual", "value": "Reads naturally to an analyst", "note": ""
    }
    code, out, err = _add(case_dir, capsys, "--regex", r"^Summarise", "--id", "TONE")
    assert code == 0 and err == ""
    assert out == "criteria: added TONE  regex            ^Summarise\n"
    code, out, err = _add(case_dir, capsys, "--must-not-contain", "leaderboard")
    assert code == 0 and out == "criteria: added C4  must_not_contain leaderboard\n"

    criteria = _case_json(case_dir)["criteria"]
    assert [c["id"] for c in criteria] == ["C1", "C2", "C3", "TONE", "C4"]
    assert criteria[0] == {"id": "C1", "kind": "must_contain", "value": "SOC", "note": ""}
    assert criteria[1] == {"id": "C2", "kind": "max_words", "value": "200", "note": "brief for the SOC"}
    assert criteria[3] == {"id": "TONE", "kind": "regex", "value": "^Summarise", "note": ""}

    code, out, err = _run(["optimize", "criteria", "list", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    assert out.splitlines() == [
        "criteria: 5",
        "  C1  must_contain     SOC",
        "  C2  max_words        200",
        "  C3  manual           Reads naturally to an analyst",
        "  TONE  regex            ^Summarise",
        "  C4  must_not_contain leaderboard",
    ]
    code, out, err = _run(["optimize", "criteria", "list", "--case", str(case_dir), "--json"], capsys)
    assert code == 0
    payload = _json(out)
    assert payload["command"] == "optimize criteria list"
    assert payload["data"]["criteria"] == criteria

    code, out, err = _run(["optimize", "status", "--case", str(case_dir)], capsys)
    assert code == 0 and out.splitlines()[-1] == "  criteria: 5"


def test_criteria_add_rejects_bad_input_with_exit_2(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    code, out, err = _add(case_dir, capsys, "--regex", "(")
    assert code == 2 and out == ""
    assert err.startswith("error: invalid regex: ")
    code, out, err = _add(case_dir, capsys, "--max-words", "0")
    assert code == 2 and out == ""
    assert err == "error: --max-words must be a positive integer\n"
    code, out, err = _add(case_dir, capsys, "--must-contain", "SOC", "--max-words", "5")
    assert code == 2 and out == ""
    code, out, err = _add(case_dir, capsys)
    assert code == 2 and out == ""
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    code, out, err = _add(case_dir, capsys, "--must-contain", "SOC", "--id", "C1")
    assert code == 2 and out == ""
    assert err == "error: criterion C1 already exists\n"
    code, out, err = _add(tmp_path / "missing", capsys, "--must-contain", "SOC")
    assert code == 2 and err.startswith("error: case not found: ")
    assert [c["id"] for c in _case_json(case_dir)["criteria"]] == ["C1"]


def test_manual_is_unjudged_until_verdict(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    _record(case_dir, tmp_path, "p1.txt", PROMPT_SHORT, capsys)
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    assert _add(case_dir, capsys, "--manual", "Reads naturally to an analyst")[0] == 0

    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 3 and err == ""
    assert out.splitlines() == [f"check: {case_dir.resolve()}", "  v1: FAIL  C1=PASS C2=UNJUDGED"]

    code, out, err = _run(
        ["optimize", "verdict", "--case", str(case_dir), "--revision", "1", "--criterion", "C2",
         "--result", "pass", "--note", "read by the on-call lead"],
        capsys,
    )
    assert code == 0 and err == ""
    assert out == "verdict: v1 C2 = PASS -> checks/verdicts.json\n"
    verdicts = json.loads((case_dir / "checks" / "verdicts.json").read_text(encoding="utf-8"))
    assert verdicts["schema"] == "proofhouse.optimize.verdicts/v0"
    assert len(verdicts["verdicts"]) == 1
    entry = verdicts["verdicts"][0]
    assert entry["revision"] == 1 and entry["criterion"] == "C2" and entry["result"] == "pass"
    assert entry["note"] == "read by the on-call lead"
    assert "recorded_at" in entry

    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    assert out.splitlines() == [f"check: {case_dir.resolve()}", "  v1: PASS  C1=PASS C2=PASS"]

    code, out, err = _run(
        ["optimize", "verdict", "--case", str(case_dir), "--revision", "1", "--criterion", "C2", "--result", "fail", "--json"],
        capsys,
    )
    assert code == 0
    payload = _json(out)
    assert payload["command"] == "optimize verdict"
    assert payload["data"]["verdict"]["result"] == "fail"
    verdicts = json.loads((case_dir / "checks" / "verdicts.json").read_text(encoding="utf-8"))
    assert len(verdicts["verdicts"]) == 1  # same (revision, criterion) overwrites
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 3
    assert out.splitlines()[1] == "  v1: FAIL  C1=PASS C2=FAIL"


def test_verdict_usage_errors(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    _record(case_dir, tmp_path, "p1.txt", PROMPT_SHORT, capsys)
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    assert _add(case_dir, capsys, "--manual", "Reads naturally")[0] == 0
    base = ["optimize", "verdict", "--case", str(case_dir)]

    code, out, err = _run([*base, "--revision", "1", "--criterion", "C1", "--result", "pass"], capsys)
    assert code == 2 and out == ""
    assert err == "error: criterion C1 is must_contain; verdicts apply only to manual criteria\n"
    code, out, err = _run([*base, "--revision", "1", "--criterion", "C9", "--result", "pass"], capsys)
    assert code == 2 and err == "error: criterion C9 does not exist\n"
    code, out, err = _run([*base, "--revision", "4", "--criterion", "C2", "--result", "pass"], capsys)
    assert code == 2 and err == "error: revision v4 does not exist (latest is v1)\n"
    code, out, err = _run([*base, "--revision", "1", "--criterion", "C2", "--result", "maybe"], capsys)
    assert code == 2 and out == ""
    assert not (case_dir / "checks").exists()


def test_check_all_prints_both_revisions_and_exit_reflects_both(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    _record(case_dir, tmp_path, "p1.txt", PROMPT_LONG, capsys)
    _record(case_dir, tmp_path, "p2.txt", PROMPT_SHORT, capsys)
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    assert _add(case_dir, capsys, "--max-words", "200")[0] == 0

    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--all"], capsys)
    assert code == 3 and err == ""
    assert out.splitlines() == [
        f"check: {case_dir.resolve()}",
        "  v1: FAIL  C1=FAIL C2=FAIL",
        "  v2: PASS  C1=PASS C2=PASS",
    ]
    assert (case_dir / "checks" / "v1.json").is_file()
    assert (case_dir / "checks" / "v2.json").is_file()

    # Default is the latest revision only.
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    assert out.splitlines() == [f"check: {case_dir.resolve()}", "  v2: PASS  C1=PASS C2=PASS"]

    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--revision", "1"], capsys)
    assert code == 3
    assert out.splitlines() == [f"check: {case_dir.resolve()}", "  v1: FAIL  C1=FAIL C2=FAIL"]

    _record(case_dir, tmp_path, "p3.txt", PROMPT_SHORT + " Cite the CVE id.", capsys)
    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--all", "--json"], capsys)
    assert code == 3
    payload = _json(out)
    assert payload["command"] == "optimize check"
    assert payload["status"] == "error"
    assert payload["data"]["overall"] == "FAIL"
    assert [r["revision"] for r in payload["data"]["revisions"]] == [1, 2, 3]
    assert [r["overall"] for r in payload["data"]["revisions"]] == ["FAIL", "PASS", "PASS"]


def test_check_exit_3_on_any_fail_0_when_all_pass(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    _record(case_dir, tmp_path, "p1.txt", PROMPT_SHORT, capsys)
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    assert _add(case_dir, capsys, "--max-words", "200")[0] == 0
    assert _add(case_dir, capsys, "--regex", r"severity\.$")[0] == 0
    assert _add(case_dir, capsys, "--must-not-contain", "company")[0] == 0
    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--json"], capsys)
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["status"] == "success"
    assert payload["data"]["overall"] == "PASS"
    assert [r["result"] for r in payload["data"]["revisions"][0]["results"]] == ["PASS"] * 4

    assert _add(case_dir, capsys, "--must-contain", "CVE")[0] == 0
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 3 and err == ""
    assert out.splitlines()[1] == "  v1: FAIL  C1=PASS C2=PASS C3=PASS C4=PASS C5=FAIL"


def test_check_writes_checks_v1_json_with_overall(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    _record(case_dir, tmp_path, "p1.txt", PROMPT_SHORT, capsys)
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    assert _add(case_dir, capsys, "--max-words", "5")[0] == 0
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 3
    path = case_dir / "checks" / "v1.json"
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n") and "\r" not in text
    written = json.loads(text)
    # T04: the latest view also names exactly what was checked.
    assert set(written) == {
        "revision", "results", "overall", "run_id", "checked_at", "checks_version",
        "revision_sha256", "criteria_sha256", "target",
    }
    assert written["target"] == "prompt_text"
    assert set(written["criteria_sha256"]) == {"C1", "C2"}
    assert written["revision"] == 1
    assert written["overall"] == "FAIL"
    assert written["results"] == [
        {"id": "C1", "kind": "must_contain", "value": "SOC", "result": "PASS"},
        {"id": "C2", "kind": "max_words", "value": "5", "result": "FAIL"},
    ]
    assert not SCORE_WORD.search(text)


def test_check_usage_errors(tmp_path: Path, capsys) -> None:
    case_dir = _case(tmp_path, capsys)
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 2 and out == ""
    assert err == "error: no criteria declared; run criteria add first\n"
    assert _add(case_dir, capsys, "--must-contain", "SOC")[0] == 0
    code, out, err = _run(["optimize", "check", "--case", str(case_dir)], capsys)
    assert code == 2 and out == ""
    assert err == "error: no revisions recorded; run record first\n"
    _record(case_dir, tmp_path, "p1.txt", PROMPT_SHORT, capsys)
    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--revision", "7"], capsys)
    assert code == 2 and out == ""
    assert err == "error: revision v7 does not exist (latest is v1)\n"
    code, out, err = _run(["optimize", "check", "--case", str(case_dir), "--revision", "1", "--all"], capsys)
    assert code == 2 and out == ""
    assert not (case_dir / "checks").exists()


def test_help_is_ascii_and_never_says_score(tmp_path: Path, capsys) -> None:
    for argv in (
        ["optimize", "--help"],
        ["optimize", "criteria", "--help"],
        ["optimize", "criteria", "add", "--help"],
        ["optimize", "criteria", "list", "--help"],
        ["optimize", "verdict", "--help"],
        ["optimize", "check", "--help"],
    ):
        code, out, err = _run(argv, capsys)
        assert code == 0, argv
        (out + err).encode("ascii")
        assert not SCORE_WORD.search(out + err), argv
    code, out, err = _run(["optimize", "--help"], capsys)
    for name in ("criteria", "verdict", "check"):
        assert name in out
    code, out, err = _run(["optimize", "criteria"], capsys)
    assert code == 2
    for path in Path(checks.__file__).parent.glob("*.py"):
        assert not SCORE_WORD.search(path.read_text(encoding="utf-8")), path
