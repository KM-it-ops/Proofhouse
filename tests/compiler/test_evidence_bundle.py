from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import (
    ClosedLoopOptions,
    run_closed_loop,
    validate_structured_requirements,
)

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_evidence_bundle_has_graduated_ids() -> None:
    result = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    b = result.evidence_bundle
    assert b["loop_id"] == "mission-012-headless-closed-loop-v0.1"
    assert b["evidence_schema"] == "eeb-headless-v0.1"
    assert b["contract_versions"]["requirements"] == "0.1.0"
    assert b["contract_versions"]["evaluation_repair"] == "0.1.0"
    assert "evaluator" in b
    assert b["evaluator"]["id"] == "evr-det-compile-security-v1"
    assert b["evaluator"]["version"] == "0.1.0"


def test_prototype_id_deprecated_alias_matches_loop_id() -> None:
    result = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    b = result.evidence_bundle
    assert b["prototype_id"] == b["loop_id"]
    assert b["prototype_id"] == "mission-012-headless-closed-loop-v0.1"


def test_validate_accepts_draft_and_accepted_contract_versions() -> None:
    base = _doc()
    for version in ("0.1.0-draft", "0.1.0"):
        doc = {**base, "contract_version": version}
        errors = validate_structured_requirements(doc)
        assert errors == [], f"expected no errors for contract_version={version!r}"


def test_validate_rejects_unknown_contract_version() -> None:
    doc = {**_doc(), "contract_version": "0.2.0"}
    errors = validate_structured_requirements(doc)
    assert any("contract_version" in e for e in errors)
