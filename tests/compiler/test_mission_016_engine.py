from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "architecture" / "requirements-compiler-contract-v0.1"
LAS = PACKAGE / "fixtures" / "linked_artifact_sets.json"


def _load_harness() -> ModuleType:
    path = PACKAGE / "validate_contract.py"
    spec = importlib.util.spec_from_file_location("mission008_contract_validator", path)
    assert spec and spec.loader
    module = ModuleType("mission008_contract_validator")
    spec.loader.exec_module(module)
    return module


def _set(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item
    raise KeyError(set_id)


def test_compile_requirements_not_importable_yet() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements  # noqa: F401


def test_positive_linked_sets_match_declared_status() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements

    expected = {
        "LAS-POS-SUCCESS-001": "SUCCESS",
        "LAS-POS-PARTIAL-001": "PARTIAL",
        "LAS-POS-BLOCKED-001": "BLOCKED",
        "LAS-POS-REFUSED-001": "REFUSED",
    }
    for set_id, status in expected.items():
        result = compile_requirements(_set(set_id)["artifacts"])
        assert result.status == status, set_id
        assert result.contract_version == "0.1.0-draft"
        assert result.command == "compile-requirements"


def test_missing_requirements_document_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements

    result = compile_requirements({"intent_input": {"contract_version": "0.1.0-draft"}})
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_harness_reexports_the_same_evaluate_contract_rules() -> None:
    from promptrig.compiler import requirements_contract as rc

    harness = _load_harness()
    assert harness.evaluate_contract_rules is rc.evaluate_contract_rules
    assert harness.context_from_artifacts is rc.context_from_artifacts
    assert harness.derive_canonical_outcome is rc.derive_canonical_outcome
