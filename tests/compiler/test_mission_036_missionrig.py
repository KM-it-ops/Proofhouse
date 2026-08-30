from __future__ import annotations

import json
from pathlib import Path

import pytest

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop
from promptrig.compiler.missionrig import (
    EVR_WS_0001,
    WorkspaceWritebackError,
    generate_mission,
    generate_mission_from_paths,
    render_mission,
    workspace_consume,
    workspace_writeback_ir,
)

ROOT = Path(__file__).resolve().parents[2]
INTAKE = json.loads(
    (ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json").read_text(
        encoding="utf-8"
    )
)


def test_missionrig_preserves_stop_conditions_and_req_ids() -> None:
    result = run_closed_loop(INTAKE, ClosedLoopOptions())
    mission = generate_mission(result.evidence_bundle, INTAKE)
    assert mission["status"] == "READY"
    assert mission["compiler_status"] == "PASS"
    assert "REQ-EVAL-001" in mission["requirement_ids"]
    assert "hallucinated_iocs" in mission["stop_conditions"]
    assert mission["ir_sha256"] == result.evidence_bundle["ir_sha256"]
    rendered = render_mission(mission)
    assert "REQ-EVAL-001" in rendered
    assert "hallucinated_iocs" in rendered
    consumed = workspace_consume(mission)
    assert consumed["may_mutate_ir"] is False
    assert consumed["requirement_ids"] == mission["requirement_ids"]
    assert consumed["stop_conditions"] == mission["stop_conditions"]


def test_missionrig_partial_does_not_invent_success() -> None:
    evidence = {
        "requirement_ids": ["REQ-EVAL-001"],
        "ir_sha256": "deadbeef",
        "evaluation": {"status": "UNRESOLVED_DEFECT"},
        "unresolved_defect": {"defect_id": "UDF-CLOSED-LOOP", "requirement_ids": ["REQ-EVAL-001"]},
        "compile_status": "UNRESOLVED_DEFECT",
    }
    mission = generate_mission(evidence, INTAKE)
    assert mission["status"] == "PARTIAL"
    assert mission["status"] != "SUCCESS"
    assert mission["status"] != "READY"
    assert mission["unresolved_defect"]["defect_id"] == "UDF-CLOSED-LOOP"
    assert "SUCCESS" not in render_mission(mission).split("status: ", maxsplit=1)[1].split("\n", maxsplit=1)[0]


def test_workspace_writeback_rejected() -> None:
    with pytest.raises(WorkspaceWritebackError) as exc:
        workspace_writeback_ir({"spec_version": "0.1.0"}, {"objective": {"goal": "mutated"}})
    assert exc.value.code == EVR_WS_0001


def test_missionrig_crash_leaves_source_unchanged(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    intake_path = tmp_path / "intake.json"
    output_path = tmp_path / "mission.json"
    evidence_path.write_text(json.dumps({"evaluation": {"status": "PASS"}, "requirement_ids": ["REQ-1"]}), encoding="utf-8")
    intake_path.write_text(json.dumps(INTAKE), encoding="utf-8")
    before_e = evidence_path.read_bytes()
    before_i = intake_path.read_bytes()
    with pytest.raises(RuntimeError, match="missionrig crash"):
        generate_mission_from_paths(evidence_path, intake_path, output_path, crash_after_read=True)
    assert evidence_path.read_bytes() == before_e
    assert intake_path.read_bytes() == before_i
    assert not output_path.exists()
