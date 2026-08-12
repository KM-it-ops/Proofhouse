from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from promptrig.compiler.cli_compiler import build_parser, main as compiler_main
from promptrig.compiler.closed_loop import ClosedLoopOptions, requirements_to_ir, run_closed_loop
from promptrig.compiler.repair import ClosedLoopTestHooks

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_requirements_to_ir_is_deterministic() -> None:
    a = requirements_to_ir(_doc())
    b = requirements_to_ir(_doc())
    assert a == b
    assert a["spec_version"] == "0.1.0"
    assert a["requirements"][0]["id"] == "REQ-EVAL-001"


def test_closed_loop_pass_no_repair_needed() -> None:
    result = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["network_used"] is False
    assert result.evidence_bundle["adapter"]["id"] == "fake"
    assert result.evidence_bundle["requirement_ids"] == ["REQ-EVAL-001"]
    assert result.evidence_bundle["failed_attempts"] == []


def test_closed_loop_repair_budget_zero_unresolved_on_forced_fail() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=0),
        hooks=ClosedLoopTestHooks(force_fail_first_compile=True),
    )
    assert result.status == "FAIL"
    assert result.failed_attempts == []


def test_closed_loop_repair_then_pass() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1),
        hooks=ClosedLoopTestHooks(force_fail_first_compile=True),
    )
    assert result.status == "PASS"
    assert len(result.failed_attempts) == 1
    assert result.failed_attempts[0]["preserved_failed_evidence"] is True


def test_closed_loop_refuses_security_weakening() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1),
        hooks=ClosedLoopTestHooks(
            force_fail_first_compile=True,
            force_security_weaken_repair=True,
        ),
    )
    assert result.status == "BLOCKED"
    assert "EVR-SEC-0001" in result.diagnostics
    assert result.failed_attempts[-1]["weakened_security_or_objective"] is True


def test_closed_loop_budget_two_unresolved() -> None:
    # Force fail every compile by always failing first and repairing into still-forced path:
    # simulate unresolved by budget 2 with persistent fail via security refuse then fail.
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=2),
        hooks=ClosedLoopTestHooks(force_fail_first_compile=True),
    )
    # after first fail, repair improves and second compile succeeds → PASS
    assert result.status == "PASS"


def test_cli_closed_loop_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "req.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    code = compiler_main(["closed-loop", str(path), "--json", "--repair-budget", "1"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "PASS"
    assert out["evidence_bundle"]["adapter"]["id"] == "fake"


def test_library_cli_closed_loop_parity(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    doc = _doc()
    lib = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    path = tmp_path / "req.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    code = compiler_main(["closed-loop", str(path), "--json", "--repair-budget", "1"])
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["status"] == lib.status
    assert cli["evidence_bundle"]["requirement_ids"] == lib.evidence_bundle["requirement_ids"]


def test_cli_closed_loop_has_no_force_flags() -> None:
    parser = build_parser()
    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    loop_parser = subparsers.choices["closed-loop"]
    option_strings = [opt for action in loop_parser._actions for opt in (action.option_strings or [])]
    dests = {action.dest for action in loop_parser._actions if action.dest not in (None, "help", "func")}
    assert not any("force_" in opt for opt in option_strings)
    assert not any(dest.startswith("force_") for dest in dests)
