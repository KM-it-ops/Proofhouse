from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop, closed_loop_from_json
from promptrig.compiler.repair import ClosedLoopTestHooks

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_default_off_has_no_model_proposal_key() -> None:
    off = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    assert off.status == "PASS"
    assert "model_proposal" not in off.evidence_bundle
    assert "suggestion_profile" not in off.evidence_bundle
    assert off.model_proposal is None


def test_suggestions_on_sidecar_does_not_change_ir_ids() -> None:
    off = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    on = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
    )
    assert on.status == "PASS"
    assert on.evidence_bundle["requirement_ids"] == off.evidence_bundle["requirement_ids"]
    assert on.evidence_bundle["ir_sha256"] == off.evidence_bundle["ir_sha256"]
    assert on.evidence_bundle["suggestion_profile"] == "fake_suggester_v0"
    assert on.evidence_bundle["model_proposal"]["proposed_records"] == ["REQ-MS-001"]
    assert "REQ-MS-001" not in on.evidence_bundle["requirement_ids"]


def test_self_accept_in_requirements_is_invalid_output_when_off() -> None:
    doc = _doc()
    doc["requirements"][0]["acceptance_state"] = "accepted"
    doc["requirements"][0]["authority_basis"] = "model_suggested"
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0001" in result.diagnostics


def test_hook_self_accept_proposal() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_self_accept_proposal=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0001" in result.diagnostics


def test_json_enable_flag_turns_sidecar_on() -> None:
    off = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    via_opt = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
    )
    raw = json.dumps({**_doc(), "enable_model_suggestions": True}).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["suggestion_profile"] == "fake_suggester_v0"
    assert result.evidence_bundle["ir_sha256"] == via_opt.evidence_bundle["ir_sha256"]
    assert result.evidence_bundle["ir_sha256"] == off.evidence_bundle["ir_sha256"]
