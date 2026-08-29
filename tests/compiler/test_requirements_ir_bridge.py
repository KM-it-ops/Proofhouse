from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from promptrig.compiler.closed_loop import (
    ClosedLoopOptions,
    closed_loop_from_json,
    run_closed_loop,
)
from promptrig.compiler.cli_compiler import main as compiler_main
from promptrig.compiler.requirements_ir_bridge import (
    bridge_008_to_structured,
    closed_loop_from_bridged_008,
)

ROOT = Path(__file__).resolve().parents[2]
MINIMAL = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def _las(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item["artifacts"]
    raise KeyError(set_id)


def test_ae1_success_fixture_bridges_then_closed_loop_fake() -> None:
    artifacts = _las("LAS-POS-SUCCESS-001")
    result = closed_loop_from_bridged_008(artifacts)
    assert "REQ-LAS-001" in result.evidence_bundle["requirement_ids"]
    assert "EVR-RQC-0001" not in result.diagnostics
    assert result.status != "BLOCKED"
    assert result.envelope is not None
    assert result.envelope.status != "error"
    assert result.requirements_compile_status == "SUCCESS"
    assert result.evidence_bundle.get("compile_status") is not None


def test_bridge_008_to_structured_success_shape_keeps_goal_requirement() -> None:
    bridged = bridge_008_to_structured(_las("LAS-POS-SUCCESS-001"))
    assert bridged.status == "SUCCESS"
    doc = bridged.structured_document
    assert doc is not None
    assert doc["profile"] == "structured_minimal_v0"
    assert doc["contract_version"] in {"0.1.0-draft", "0.1.0"}
    assert doc["objective"]["goal"] == "Produce a cited offline incident report."
    assert doc["network_allowed"] is False
    ids = [req["id"] for req in doc["requirements"]]
    assert "REQ-LAS-001" in ids
    statements = {req["id"]: req["statement"] for req in doc["requirements"]}
    assert statements["REQ-LAS-001"] == "Produce a cited offline incident report."


def test_ae2_unbridged_008_on_closed_loop_from_json_is_blocked() -> None:
    raw = json.dumps(_las("LAS-POS-SUCCESS-001")).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert "EVR-RQC-0001" in result.diagnostics
    assert result.evidence_bundle == {}


def test_partial_with_representable_ir_emits_evidence_not_008_success() -> None:
    artifacts = _las("LAS-POS-PARTIAL-001")
    bridged = bridge_008_to_structured(artifacts)
    assert bridged.status == "PARTIAL"
    assert bridged.structured_document is not None
    ids = [req["id"] for req in bridged.structured_document["requirements"]]
    assert "REQ-LAS-001" in ids
    assert "REQ-LAS-002" in ids

    result = closed_loop_from_bridged_008(artifacts)
    assert result.evidence_bundle.get("requirement_ids")
    assert "REQ-LAS-001" in result.evidence_bundle["requirement_ids"]
    assert result.requirements_compile_status == "PARTIAL"
    assert result.requirements_compile_status != "SUCCESS"
    assert result.evidence_bundle.get("requirements_compile_status") == "PARTIAL"


def test_blocked_008_does_not_lower() -> None:
    result = closed_loop_from_bridged_008(_las("LAS-POS-BLOCKED-001"))
    assert result.status == "BLOCKED"
    assert result.requirements_compile_status == "BLOCKED"
    assert result.envelope is None
    assert result.evidence_bundle == {}
    assert result.structured_document is None


def test_refused_008_does_not_lower() -> None:
    result = closed_loop_from_bridged_008(_las("LAS-POS-REFUSED-001"))
    assert result.status == "REFUSED"
    assert result.requirements_compile_status == "REFUSED"
    assert result.envelope is None
    assert result.evidence_bundle == {}
    assert result.structured_document is None


def test_invalid_output_008_does_not_lower() -> None:
    result = closed_loop_from_bridged_008({"intent_input": {"contract_version": "0.1.0-draft"}})
    assert result.status == "INVALID_OUTPUT"
    assert result.requirements_compile_status == "INVALID_OUTPUT"
    assert result.envelope is None
    assert result.evidence_bundle == {}


def test_partial_missing_goal_fails_closed_without_invented_meaning() -> None:
    artifacts = deepcopy(_las("LAS-POS-PARTIAL-001"))
    for mapping in artifacts["mappings"]:
        if mapping.get("target_pointer") == "/objective/goal":
            mapping["target_pointer"] = "/project/name"
    bridged = bridge_008_to_structured(artifacts)
    assert bridged.status == "PARTIAL"
    assert bridged.structured_document is None
    assert "EVR-BRG-0001" in bridged.diagnostics

    result = closed_loop_from_bridged_008(artifacts)
    assert result.status == "BLOCKED"
    assert result.requirements_compile_status == "PARTIAL"
    assert "EVR-BRG-0001" in result.diagnostics
    assert result.envelope is None
    assert result.evidence_bundle == {}
    assert result.structured_document is None


def test_ae5_simple_mode_ui_still_forbidden_on_closed_loop() -> None:
    raw = json.dumps({"profile": "simple_mode_ui", "objective": {"goal": "x"}}).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in code for code in result.diagnostics)


def test_ae5_network_allowed_true_still_evr_net_on_closed_loop_and_bridge() -> None:
    structured = json.loads(MINIMAL.read_text(encoding="utf-8"))
    loop = run_closed_loop(structured, ClosedLoopOptions(network_allowed=True))
    assert loop.status == "BLOCKED"
    assert loop.diagnostics == ["EVR-NET-0001"]

    bridged = closed_loop_from_bridged_008(
        _las("LAS-POS-SUCCESS-001"),
        ClosedLoopOptions(network_allowed=True),
    )
    assert bridged.status == "BLOCKED"
    assert "EVR-NET-0001" in bridged.diagnostics
    assert bridged.envelope is None


def test_repair_budgets_0_1_2_accepted_on_bridged_success() -> None:
    artifacts = _las("LAS-POS-SUCCESS-001")
    for budget in (0, 1, 2):
        result = closed_loop_from_bridged_008(artifacts, ClosedLoopOptions(repair_budget=budget))
        assert "EVR-RQC-0001" not in result.diagnostics
        assert result.evidence_bundle.get("repair_budget") == budget
        assert "REQ-LAS-001" in result.evidence_bundle["requirement_ids"]


def test_repair_budget_outside_0_1_2_blocked() -> None:
    result = closed_loop_from_bridged_008(
        _las("LAS-POS-SUCCESS-001"),
        ClosedLoopOptions(repair_budget=3),
    )
    assert result.status == "BLOCKED"
    assert "EVR-REP-0001" in result.diagnostics


def test_cli_closed_loop_bridged_008_matches_library(tmp_path, capsys) -> None:
    artifacts = _las("LAS-POS-SUCCESS-001")
    lib = closed_loop_from_bridged_008(artifacts)
    path = tmp_path / "las-success.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    code = compiler_main(["closed-loop-bridged-008", str(path), "--json", "--repair-budget", "1"])
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["status"] == lib.status
    assert cli["requirements_compile_status"] == "SUCCESS"
    assert "REQ-LAS-001" in cli["evidence_bundle"]["requirement_ids"]
    assert "EVR-RQC-0001" not in cli["diagnostics"]
