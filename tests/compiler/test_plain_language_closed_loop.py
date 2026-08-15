from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json

PLAIN_FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"
STRUCTURED_FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def test_plain_language_closed_loop_pass() -> None:
    text = PLAIN_FIXTURE.read_text(encoding="utf-8")
    raw = json.dumps(
        {
            "profile": "plain_language_v0",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "repair_budget": 1,
            "text": text,
        }
    ).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["intake_profile"] == "plain_language_v0"
    assert "REQ-PL-001" in result.evidence_bundle["requirement_ids"]


def test_structured_fixture_still_passes_via_closed_loop_from_json() -> None:
    raw = STRUCTURED_FIXTURE.read_bytes()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert "intake_profile" not in result.evidence_bundle
    assert result.evidence_bundle["requirement_ids"] == ["REQ-EVAL-001"]
