from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import socket
import subprocess
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
    "architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json": "082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6",
    "architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json": "d900aa57468be4cadb145d4a6458ef0308ad4d686ea86aab3407c782dfd4dc8f",
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


def _canonical_git_blob_sha256(relative: str) -> str:
    """Hash the exact committed git blob bytes for `relative` at HEAD.

    Reading via `git show HEAD:<path>` bypasses the working-tree checkout entirely
    (no smudge/clean filters, no core.autocrlf conversion), so this is sensitive to
    ANY committed byte change, including a line-ending-only change -- unlike reading
    the checked-out file directly, whose bytes depend on the tester's local git
    config and would silently mask a real CRLF/LF change to frozen content.
    """

    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.fail(f"could not retrieve canonical git blob for {relative!r}: {exc}")
    return hashlib.sha256(result.stdout).hexdigest()


def test_frozen_ir_and_diagnostic_registry_hashes_are_unchanged() -> None:
    for relative, expected in FROZEN_HASHES.items():
        actual = _canonical_git_blob_sha256(relative)
        assert actual == expected


def test_authority_basis_vocabulary_is_normalized() -> None:
    schema = _json(PACKAGE / "schemas" / "requirement.schema.json")
    enum_values = set(schema["properties"]["authority_basis"]["enum"])
    assert {"owner_decision", "user_decision", "accepted_contract"} <= enum_values
    assert not {"owner_approved", "user_approved"} & enum_values

    banned = ("owner_approved", "user_approved", "owner approved", "user approved")
    for name in ("REQUIREMENTS_COMPILER_SPEC.md", "REQUIREMENTS_EVIDENCE_MODEL.md", "AUTHORITY_AND_DEFAULTS.md"):
        text = (PACKAGE / name).read_text(encoding="utf-8")
        for term in banned:
            assert term not in text, f"{term!r} still present in {name}"


def test_schema_instance_corpus_proves_specific_rejection_reasons() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["schema_instance_count"] >= 19
    assert result["schema_instance_pass_count"] == result["schema_instance_count"]

    by_id = {item["id"]: item for item in result["schema_instance_results"]}
    for instance_id in ("SCHI-REQUIREMENT-NEG-OWNER-APPROVED", "SCHI-REQUIREMENT-NEG-USER-APPROVED"):
        record = by_id[instance_id]
        assert record["passed"] is True
        assert len(record["errors"]) == 1
        assert record["errors"][0]["keyword"] == "enum"
        assert record["errors"][0]["instance_path"] == "/authority_basis"

    for instance_id in (
        "SCHI-REQUIREMENT-POS-OWNER-DECISION",
        "SCHI-REQUIREMENT-POS-USER-DECISION",
        "SCHI-REQUIREMENT-POS-ACCEPTED-CONTRACT",
    ):
        record = by_id[instance_id]
        assert record["passed"] is True
        assert record["errors"] == []

    schemas_covered = {record["schema"] for record in result["schema_instance_results"]}
    assert schemas_covered == SCHEMAS


def test_schema_instance_validation_is_byte_deterministic() -> None:
    validator = _load_validator()
    first = validator.canonical_validation_json(validator.validate_package(PACKAGE))
    second = validator.canonical_validation_json(validator.validate_package(PACKAGE))
    assert first == second
    parsed = json.loads(first)
    assert [item["id"] for item in parsed["schema_instance_results"]] == sorted(
        item["id"] for item in parsed["schema_instance_results"]
    )


def test_requirement_vocabulary_has_no_drift_from_normative_contract() -> None:
    validator = _load_validator()
    schema_docs = {
        path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")
    }
    assert validator.find_vocabulary_drift(schema_docs) == []

    requirement_schema = schema_docs["requirement.schema.json"]
    props = requirement_schema["properties"]
    assert set(props["type"]["enum"]) == validator.CONTRACT_REQUIREMENT_TYPES
    assert set(props["priority"]["enum"]) == validator.CONTRACT_REQUIREMENT_PRIORITIES
    assert props["id"]["pattern"] == validator.CONTRACT_REQUIREMENT_ID_PATTERN
    assert "capability" not in props["type"]["enum"]
    assert "policy" not in props["type"]["enum"]
    assert "recommended" not in props["priority"]["enum"]


def test_requirement_id_pattern_is_bounded_and_rejects_pathological_inputs() -> None:
    validator = _load_validator()
    pattern = re.compile(validator.CONTRACT_REQUIREMENT_ID_PATTERN)
    assert pattern.match("REQ-ABC")
    assert not pattern.match("REQ-AB")
    assert not pattern.match("REQ-" + "A" * 65)
    assert not pattern.match("req-abc")
    assert not pattern.match("REQ-ABC ")


def test_traceability_evidence_has_no_unknown_clause_references() -> None:
    validator = _load_validator()
    assert validator.find_unknown_clause_references(PACKAGE) == []


def test_traceability_evidence_covers_every_required_field() -> None:
    validator = _load_validator()
    schema_docs = {
        path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")
    }
    assert validator.find_uncovered_required_fields(PACKAGE, schema_docs) == []


def test_traceability_checks_actually_detect_injected_drift() -> None:
    """Prove the checks are not vacuously passing: a deliberately broken input must fail."""

    validator = _load_validator()
    schema_docs = {
        path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")
    }

    broken_schema_docs = dict(schema_docs)
    broken_requirement_schema = json.loads(json.dumps(schema_docs["requirement.schema.json"]))
    broken_requirement_schema["properties"]["priority"]["enum"] = ["required", "optional", "recommended"]
    broken_schema_docs["requirement.schema.json"] = broken_requirement_schema
    assert validator.find_vocabulary_drift(broken_schema_docs) != []

    missing_fields = validator.find_uncovered_required_fields(
        PACKAGE, {"requirement.schema.json": {"required": ["a_field_with_no_justification_entry"]}}
    )
    assert "requirement.a_field_with_no_justification_entry" in missing_fields


def test_ir_pointer_case_corpus_proves_valid_leaves_and_specific_rejection_reasons() -> None:
    validator = _load_validator()
    ir_leaves, ir_subtrees = validator.build_ir_pointer_index(validator.load_frozen_ir_schema())
    cases = validator.load_ir_pointer_cases(PACKAGE)
    assert len(cases) >= 11

    results = {
        case["id"]: validator.validate_ir_pointer_case(case, ir_leaves, ir_subtrees) for case in cases
    }
    assert all(result["passed"] for result in results.values())
    assert sum(case["kind"] == "positive" for case in cases) >= 6
    assert sum(case["kind"] == "negative" for case in cases) >= 5

    assert results["IRP-NEG-IMPOSSIBLE-PROJECT-OBJECTIVE"]["actual_classification"] == "not_a_permitted_leaf"
    assert results["IRP-NEG-SUBTREE-PROJECT"]["actual_classification"] == "subtree_shortcut"
    assert results["IRP-NEG-SUBTREE-REQUIREMENTS-ITEM"]["actual_classification"] == "subtree_shortcut"
    assert results["IRP-NEG-MALFORMED-POINTER"]["actual_classification"] == "invalid_pointer_syntax"
    assert results["IRP-POS-OBJECTIVE-GOAL"]["actual_classification"] == "valid"

    assert validator.classify_ir_pointer("/project/objective", ir_leaves, ir_subtrees) == "not_a_permitted_leaf"


def test_validate_package_reports_ir_pointer_traceability_and_vocabulary_checks() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["ir_pointer_case_count"] >= 11
    assert result["ir_pointer_case_pass_count"] == result["ir_pointer_case_count"]
    assert result["unknown_clause_references"] == []
    assert result["uncovered_required_fields"] == []
    assert result["vocabulary_drift"] == []


def test_ir_mapping_emitting_outcome_with_impossible_pointer_is_invalid_output() -> None:
    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    case = {
        "id": "synthetic-impossible-pointer-check",
        "authoring_mode": "developer",
        "input": {"intent": "Synthetic check.", "authoritative_inputs": ["synthetic"]},
        "candidate": {
            "requirements": [{
                "id": "REQ-SYN-001", "type": "objective", "statement": "Synthetic requirement.",
                "priority": "required", "acceptance_state": "accepted", "authority_basis": "directly_stated",
                "source_refs": ["SRC-SYN-001"], "acceptance_criteria": ["Present."], "consequential": False,
            }],
            "sources": [{
                "id": "SRC-SYN-001", "kind": "developer_prompt", "lifecycle": "current",
                "authority_claim": "Synthetic.", "location": {"uri": "synthetic://check", "json_pointer": "/x"},
            }],
            "mappings": [{
                "id": "MAP-SYN-001", "requirement_id": "REQ-SYN-001", "outcome": "direct",
                "target_pointer": "/project/objective", "authority_ref": "directly_stated",
                "validation_ref": "VAL-SYN-001",
            }],
        },
        "expected": {
            "status": "INVALID_OUTPUT", "diagnostic_codes": ["RQC-EVD-0001"],
            "requirement_ids": ["REQ-SYN-001"], "assumptions": [], "open_questions": [], "conflicts": [],
            "ir_mapping_outcomes": ["direct"], "evidence": ["SRC-SYN-001"], "approval_required": False,
        },
    }
    result = validator.validate_case(case, registry)
    assert result["actual_status"] == "INVALID_OUTPUT"
    assert "RQC-EVD-0001" in result["actual_diagnostic_codes"]
    assert result["passed"] is True
