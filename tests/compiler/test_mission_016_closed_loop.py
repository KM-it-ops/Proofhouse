from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import (
    ClosedLoopOptions,
    closed_loop_from_json,
    run_closed_loop,
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


def test_canonical_008_on_closed_loop_is_blocked_not_compiled() -> None:
    raw = json.dumps(_las("LAS-POS-SUCCESS-001")).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert "EVR-RQC-0001" in result.diagnostics
    assert result.evidence_bundle == {}


def test_structured_minimal_closed_loop_still_passes() -> None:
    result = closed_loop_from_json(MINIMAL.read_bytes(), ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"


def test_simple_mode_still_blocked() -> None:
    raw = json.dumps({"profile": "simple_mode_ui", "objective": {"goal": "x"}}).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in code for code in result.diagnostics)


def test_network_allowed_still_evr_net() -> None:
    result = run_closed_loop(
        json.loads(MINIMAL.read_text(encoding="utf-8")),
        ClosedLoopOptions(network_allowed=True),
    )
    assert result.status == "BLOCKED"
    assert result.diagnostics == ["EVR-NET-0001"]
