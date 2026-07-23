from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "architecture" / "requirements-compiler-contract-v0.1"
FIXTURES = PACKAGE / "fixtures"
VALIDATOR_PATH = PACKAGE / "validate_contract.py"
SCHEMAS = {
    "intent-input.schema.json",
    "source-evidence.schema.json",
    "requirement.schema.json",
    "requirements-document.schema.json",
    "requirements-diagnostic.schema.json",
    "requirement-ir-mapping.schema.json",
    "requirements-compile-result.schema.json",
    "requirements-evidence-bundle.schema.json",
}
REQUIRED_DIAGNOSTIC_FAMILIES = {
    "RQC-AMB-0001", "RQC-APR-0001", "RQC-AUT-0001", "RQC-BLK-0001",
    "RQC-CFL-0001", "RQC-CTX-0001", "RQC-DFT-0001", "RQC-EVD-0001",
    "RQC-IDN-0001", "RQC-IRG-0001", "RQC-MDL-0001", "RQC-PRI-0001",
    "RQC-PRV-0001", "RQC-REF-0001", "RQC-SCH-0001", "RQC-SEC-0001",
    "RQC-SEM-0001", "RQC-SRC-0002", "RQC-SRC-0003", "RQC-SRC-0004",
    "RQC-UNS-0001", "RQC-VER-0001",
}
FROZEN_HASHES = {
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json": "a274953882b5b46166d87eece761dd1b637ddc7c8061b1c2ba4b2f0cb9303ad3",
    "architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json": "ad42ca198f089a0f578bf99daa797f86e58d146f398bd2b93aae6a4c945e6987",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_validator() -> ModuleType:
    assert VALIDATOR_PATH.is_file(), "MISSION-008 contract validator is not implemented"
    spec = importlib.util.spec_from_file_location("mission008_contract_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evidence_first_case_set_precedes_contract_fields() -> None:
    manifest = _json(FIXTURES / "manifest.json")
    cases = _json(FIXTURES / "cases.json")["cases"]
    assert len(cases) == manifest["case_count"] == 41
    assert {case["authoring_mode"] for case in cases} == {"simple", "developer", "api", "file"}
    assert {case["expected"]["status"] for case in cases} == {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}
    assert sum(case["category"] in {"positive", "boundary"} for case in cases) >= 12
    assert sum(case["category"] in {"negative", "adversarial"} for case in cases) >= 18
    assert sum(bool(case["candidate"].get("semantically_empty")) for case in cases) >= 2
    assert sum(any(mapping.get("outcome") == "no_ir_representation" and mapping.get("gap_id") for mapping in case["candidate"].get("mappings", [])) for case in cases) >= 2
    assert sum("RQC-MDL-0001" in case["expected"]["diagnostic_codes"] for case in cases) >= 2
    assert sum(bool({"RQC-SEC-0001", "RQC-PRV-0001"} & set(case["expected"]["diagnostic_codes"])) for case in cases) >= 2
    for case in cases:
        assert case["input"]["intent"].strip()
        assert case["input"]["authoritative_inputs"]
        assert set(case["expected"]) == {"status", "diagnostic_codes", "requirement_ids", "assumptions", "open_questions", "conflicts", "ir_mapping_outcomes", "evidence", "approval_required"}


def test_contract_validator_meta_validates_schemas_and_all_fixture_outcomes() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS"
    assert result["schema_count"] == 8
    assert result["fixture_count"] == 41
    assert result["fixture_pass_count"] == 41
    assert result["errors"] == []
    assert {path.name for path in (PACKAGE / "schemas").glob("*.schema.json")} == SCHEMAS


def test_validation_evidence_is_byte_deterministic_and_ordered() -> None:
    validator = _load_validator()
    first = validator.canonical_validation_json(validator.validate_package(PACKAGE))
    second = validator.canonical_validation_json(validator.validate_package(PACKAGE))
    assert first == second
    parsed = json.loads(first)
    assert parsed["diagnostic_codes"] == sorted(parsed["diagnostic_codes"])
    assert [item["id"] for item in parsed["fixtures"]] == sorted(item["id"] for item in parsed["fixtures"])


def test_diagnostic_namespace_covers_required_families_and_rejects_unknown_codes() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    cases = _json(FIXTURES / "cases.json")["cases"]
    fixture_codes = {code for case in cases for code in case["expected"]["diagnostic_codes"]}
    assert REQUIRED_DIAGNOSTIC_FAMILIES <= set(registry)
    assert fixture_codes <= set(registry)
    unknown_case = next(case for case in cases if case["id"] == "api-unknown-diagnostic-code")
    result = validator.validate_case(unknown_case, registry)
    assert result["actual_diagnostic_codes"] == ["RQC-DIA-0001"]
    assert result["passed"] is True


def test_semantic_validator_rejects_duplicates_vacuity_broken_references_and_hidden_defaults() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    cases = {case["id"]: case for case in _json(FIXTURES / "cases.json")["cases"]}
    expected = {
        "developer-duplicate-requirement-id": "RQC-IDN-0001",
        "simple-semantic-empty": "RQC-SEM-0001",
        "developer-semantic-empty-structured": "RQC-SEM-0001",
        "api-incomplete-evidence-link": "RQC-EVD-0001",
        "api-broken-ir-mapping-reference": "RQC-EVD-0001",
        "developer-hidden-consequential-default": "RQC-DFT-0001",
    }
    for case_id, code in expected.items():
        result = validator.validate_case(cases[case_id], registry)
        assert code in result["actual_diagnostic_codes"]
        assert result["passed"] is True


def test_security_privacy_and_model_assisted_paths_fail_closed() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    cases = {case["id"]: case for case in _json(FIXTURES / "cases.json")["cases"]}
    for case_id in {"simple-hostile-rule-override", "simple-privacy-posture-unknown", "developer-security-fail-closed", "developer-model-security-weakening", "api-model-self-accept", "file-adversarial-embedded-content"}:
        result = validator.validate_case(cases[case_id], registry)
        assert result["actual_status"] in {"BLOCKED", "REFUSED", "INVALID_OUTPUT"}
        assert result["passed"] is True


def test_required_meaning_has_mapping_or_stable_gap_evidence() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    cases = _json(FIXTURES / "cases.json")["cases"]
    for case in cases:
        result = validator.validate_case(case, registry)
        assert result["passed"] is True
        if result["actual_status"] == "SUCCESS":
            assert set(case["expected"]["requirement_ids"]) <= set(result["mapped_requirement_ids"])
        for mapping in case["candidate"].get("mappings", []):
            if mapping["outcome"] == "no_ir_representation" and mapping.get("gap_id"):
                assert mapping["diagnostic_code"] == "RQC-IRG-0001"


def test_source_locations_are_stable_across_repeated_validation() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    case = next(case for case in _json(FIXTURES / "cases.json")["cases"] if case["id"] == "file-source-location-stability")
    first = validator.validate_case(case, registry)
    second = validator.validate_case(case, registry)
    assert first["source_locations"] == second["source_locations"] == [{"column": 3, "json_pointer": "/requirements/0", "line": 12, "uri": "file://stable.json"}]


def test_validator_uses_no_network_or_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = _load_validator()
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("contract validation must not access network or credentials")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS"
    assert result["network_access"] is False
    assert result["credentials_accessed"] is False


def test_frozen_ir_and_diagnostic_registry_hashes_are_unchanged() -> None:
    for relative, expected in FROZEN_HASHES.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected
