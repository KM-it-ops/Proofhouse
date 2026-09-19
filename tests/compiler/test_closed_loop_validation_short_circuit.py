"""Closed-loop validation short-circuit and honest repair outcomes (T-P3-02)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from proofhouse.compiler.closed_loop import ClosedLoopOptions, run_closed_loop, validate_structured_requirements
from proofhouse.compiler.contracts import CONTRACT_VERSION, ResultEnvelope
from proofhouse.compiler.evaluation import EvaluationResult
from proofhouse.compiler.repair import ClosedLoopTestHooks

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_req_1_id_is_invalid_and_does_not_repair() -> None:
    doc = _doc()
    doc["requirements"][0]["id"] = "REQ-1"
    errors = validate_structured_requirements(doc)
    assert any("invalid requirement id" in err for err in errors)
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    assert result.status == "BLOCKED"
    assert result.failed_attempts == []
    assert result.evidence_bundle == {}


def test_compile_validation_errors_skip_repair(monkeypatch) -> None:
    envelope = ResultEnvelope(
        contract_version=CONTRACT_VERSION,
        command="compile",
        status="error",
        data={},
        diagnostics=(SimpleNamespace(code="PRG-VALIDATION-0001", severity="error"),),  # type: ignore[arg-type]
    )
    monkeypatch.setattr("proofhouse.compiler.closed_loop.api.compile", lambda *args, **kwargs: envelope)
    result = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    assert result.status == "BLOCKED"
    assert result.diagnostics == ["PRG-VALIDATION-0001"]
    assert result.failed_attempts == []
    assert result.evidence_bundle == {}
    assert result.envelope is envelope


def test_repair_outcome_improved_when_next_eval_passes() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1),
        hooks=ClosedLoopTestHooks(force_fail_first_compile=True),
    )
    assert result.status == "PASS"
    assert result.failed_attempts[0]["outcome"] == "improved"


def test_repair_outcome_no_change_when_next_eval_still_fails(monkeypatch) -> None:
    def always_fail(request):
        return EvaluationResult(
            status="FAIL",
            diagnostic_codes=("EVR-DET-0001",),
            scores={"primary": 0.0},
            evaluator_id=request.evaluator_id,
            evaluator_version=request.evaluator_version,
            authoritative=True,
        )

    monkeypatch.setattr("proofhouse.compiler.closed_loop.evaluate_deterministic", always_fail)
    result = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    assert result.failed_attempts
    assert result.failed_attempts[0]["outcome"] == "no_change"
    assert result.status == "UNRESOLVED_DEFECT"
