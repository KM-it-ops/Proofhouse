from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "architecture" / "evaluation-repair-contract-v0.1"
FIXTURES = PACKAGE / "fixtures"
VALIDATOR_PATH = PACKAGE / "validate_contract.py"
SCHEMA_NAMES = {
    "evaluator-record.schema.json",
    "baseline-identity.schema.json",
    "candidate-identity.schema.json",
    "evaluation-request.schema.json",
    "evaluation-result.schema.json",
    "repair-attempt.schema.json",
    "repair-plan.schema.json",
    "unresolved-defect.schema.json",
    "evaluation-evidence-bundle.schema.json",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_validator() -> ModuleType:
    assert VALIDATOR_PATH.is_file(), "MISSION-009 contract validator is not implemented"
    spec = importlib.util.spec_from_file_location("mission009_contract_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_layout_and_case_coverage() -> None:
    manifest = _json(FIXTURES / "manifest.json")
    cases = _json(FIXTURES / "cases.json")["cases"]
    assert len(cases) == manifest["case_count"] >= 20
    assert {c["category"] for c in cases} >= {"positive", "negative", "boundary", "adversarial"}
    statuses = {c["expected"]["status"] for c in cases}
    assert "PASS" in statuses
    assert "UNRESOLVED_DEFECT" in statuses or "REGRESSION" in statuses
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-AUT-0001"] for c in cases)
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-SEC-0001"] for c in cases)
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-NET-0001"] for c in cases)
    for name in SCHEMA_NAMES:
        assert (PACKAGE / "schemas" / name).is_file()


def test_contract_validator_passes_all_fixtures() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS", result.get("failed_cases")
    assert result["schema_count"] == 9
    assert result["fixture_pass_count"] == result["fixture_count"]
    assert result["determinism_ok"] is True


def test_model_judge_never_quietly_authoritative() -> None:
    cases = _json(FIXTURES / "cases.json")["cases"]
    for case in cases:
        for outcome in case["result"]["evaluator_outcomes"]:
            ev = next(e for e in case["evaluators"] if e["evaluator_id"] == outcome["evaluator_id"])
            if ev["evaluator_kind"] == "model_judge" and outcome.get("authoritative_for_executable") is True:
                assert "EVR-AUT-0001" in case["result"]["diagnostic_codes"]
