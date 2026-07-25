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


# --- Adversarial counterexample regression tests (blockers B1-B4, refinements 1-3) ---------
# These construct candidates NOT present in the 41-case corpus, proving the semantic validator
# enforces the invariants for arbitrary input rather than matching hardcoded fixture expectations.

_CURRENT_SOURCE = {
    "id": "SRC-CX", "kind": "file", "lifecycle": "current",
    "authority_claim": "user", "location": {"uri": "cx://s", "json_pointer": ""},
}


def _cx_requirement(**overrides: object) -> dict:
    base = {
        "id": "REQ-CX-001", "type": "behavior", "statement": "Do the thing.",
        "priority": "required", "acceptance_state": "accepted", "authority_basis": "directly_stated",
        "source_refs": ["SRC-CX"], "acceptance_criteria": ["Present."], "consequential": False,
    }
    base.update(overrides)
    return base


def _cx_case(candidate: dict, intent: str = "Build a thing.") -> dict:
    candidate.setdefault("sources", [dict(_CURRENT_SOURCE)])
    return {"input": {"intent": intent, "authoritative_inputs": ["user:x"]}, "candidate": candidate}


def _derive(validator: ModuleType, candidate: dict, intent: str = "Build a thing.") -> tuple[str, list[str]]:
    registry = validator.load_diagnostic_registry(PACKAGE)
    return validator._derive_outcome(_cx_case(candidate, intent), registry)


def test_b1_model_suggested_meaning_never_self_accepts() -> None:
    validator = _load_validator()
    # Accepted meaning on model_suggested authority, with no self_accepted marker anywhere.
    status, codes = _derive(validator, {"requirements": [_cx_requirement(authority_basis="model_suggested")]})
    assert status == "INVALID_OUTPUT"
    assert codes == ["RQC-MDL-0001"]
    # Every non-accepting authority basis on an accepted requirement is rejected, not SUCCESS.
    for basis in ("unresolved", "disputed", "unsupported", "refused", "invalid"):
        status, _ = _derive(validator, {"requirements": [_cx_requirement(authority_basis=basis)]})
        assert status != "SUCCESS", basis
    # A model proposal marked accepted (without self_accepted) still crosses the boundary.
    status, codes = _derive(validator, {
        "requirements": [_cx_requirement()],
        "mappings": [{"requirement_id": "REQ-CX-001", "outcome": "direct", "target_pointer": "/objective/goal"}],
        "model_proposals": [{"id": "MDL-CX", "acceptance_state": "accepted", "source_refs": ["SRC-CX"]}],
    })
    assert status == "INVALID_OUTPUT" and codes == ["RQC-MDL-0001"]


def test_b1_directly_stated_cannot_launder_model_originated_meaning() -> None:
    validator = _load_validator()
    status, codes = _derive(validator, {
        "requirements": [_cx_requirement()],
        "model_proposals": [{"id": "MDL-CX", "acceptance_state": "proposed",
                             "source_refs": ["SRC-CX"], "proposed_records": ["REQ-CX-001"]}],
    })
    assert status == "INVALID_OUTPUT" and codes == ["RQC-MDL-0001"]


def test_b2_approval_reference_must_resolve_to_active_evidenced_approval() -> None:
    validator = _load_validator()
    mapped = [{"requirement_id": "REQ-CX-001", "outcome": "direct", "target_pointer": "/objective/goal"}]

    def approval(validator_module: ModuleType, **overrides: object) -> dict:
        base = {"id": "APR-CX", "subject_refs": ["REQ-CX-001"], "authority": "owner",
                "decision": "approved", "scope": {"kind": "requirement", "value": "REQ-CX-001"},
                "evidence_refs": ["SRC-POLICY"], "policy_ref": "POL-CX", "sequence": 1}
        base.update(overrides)
        base["content_digest"] = validator_module.record_content_digest(base)
        return base

    # Dangling reference: no approval record at all.
    status, codes = _derive(validator, {
        "requirements": [_cx_requirement(consequential=True, approval_refs=["APR-NONE"])], "mappings": mapped,
    })
    assert status == "BLOCKED" and codes == ["RQC-APR-0001"]

    # Every inactive decision fails closed even with a complete surrounding chain.
    for decision in ("rejected", "revoked", "expired", "superseded"):
        status, _ = _derive_with_policy(validator, {
            "requirements": [_cx_requirement(consequential=True, approval_refs=["APR-CX"])],
            "approvals": [approval(validator, decision=decision)], "mappings": mapped,
        })
        assert status == "BLOCKED", decision

    # Unresolved evidence, or wrong subject, fails closed.
    status, _ = _derive_with_policy(validator, {
        "requirements": [_cx_requirement(consequential=True, approval_refs=["APR-CX"])],
        "approvals": [approval(validator, evidence_refs=["SRC-NOT-PRESENT"])], "mappings": mapped,
    })
    assert status == "BLOCKED"
    status, _ = _derive_with_policy(validator, {
        "requirements": [_cx_requirement(consequential=True, approval_refs=["APR-CX"])],
        "approvals": [approval(validator, subject_refs=["REQ-OTHER-001"])], "mappings": mapped,
    })
    assert status == "BLOCKED"

    # A fully resolved chain -- approval, accepted policy, authoritative source -- authorizes.
    status, codes = _derive_with_policy(validator, {
        "requirements": [_cx_requirement(consequential=True, approval_refs=["APR-CX"])],
        "approvals": [approval(validator)], "mappings": mapped,
    })
    assert status == "SUCCESS" and codes == []


_POLICY_SOURCE = {
    "id": "SRC-POLICY", "kind": "contract", "lifecycle": "current", "authority_claim": "governance",
    "sha256": "a" * 64, "contract_identity": "promptrig.governance", "contract_version": "1.0",
    "location": {"uri": "contract://governance", "json_pointer": "/approval"},
}


def _derive_with_policy(validator: ModuleType, candidate: dict, subject: str = "REQ-CX-001",
                        subject_kind: str = "requirement") -> tuple[str, list[str]]:
    """Build a candidate carrying a real accepted approval-threshold policy anchored to an
    authoritative contract source, so the approval chain can actually resolve."""

    registry = validator.load_diagnostic_registry(PACKAGE)
    policy = {"id": "POL-CX", "kind": "approval_threshold", "status": "accepted",
              "statement": "Consequential meaning requires owner approval.",
              "scope": {"kind": subject_kind, "value": subject},
              "required_authority": "owner", "source_ref": "SRC-POLICY"}
    policy["content_digest"] = validator.record_content_digest(policy)
    candidate.setdefault("sources", [dict(_CURRENT_SOURCE), dict(_POLICY_SOURCE)])
    candidate.setdefault("policies", [policy])
    case = {"input": {"intent": "Consequential.", "authoritative_inputs": ["user:x"]}, "candidate": candidate}
    return validator._derive_outcome(case, registry)


def test_b2_consequential_default_needs_resolved_approval_not_a_boolean() -> None:
    validator = _load_validator()
    mapped = [{"requirement_id": "REQ-CX-001", "outcome": "direct", "target_pointer": "/objective/goal"}]
    status, codes = _derive_with_policy(validator, {
        "requirements": [_cx_requirement()], "mappings": mapped,
        "defaults": [{"id": "DFT-CX", "authority_ref": "x", "consequential": True, "approved": True}],
    })
    assert status == "BLOCKED" and codes == ["RQC-DFT-0001"]


def test_b3_security_privacy_enforcement_keys_on_type_not_id_prefix() -> None:
    validator = _load_validator()
    # type=security with a NON-security-looking id, unmapped -> fails closed. Missing mapping is not
    # a policy prohibition, so the correct fail-closed status is BLOCKED, not REFUSED (SP-011).
    status, codes = _derive(validator, {"requirements": [_cx_requirement(id="REQ-AUTH-001", type="security")]})
    assert status == "BLOCKED" and codes == ["RQC-BLK-0001", "RQC-SEC-0001"]
    # A security-LOOKING id with a non-security type is NOT security: mapped behavior -> success.
    status, _ = _derive(validator, {
        "requirements": [_cx_requirement(id="REQ-SECURITY-XX", type="behavior")],
        "mappings": [{"requirement_id": "REQ-SECURITY-XX", "outcome": "direct", "target_pointer": "/objective/goal"}],
    })
    assert status == "SUCCESS"
    # Unresolved privacy posture (by type) blocks.
    status, codes = _derive(validator, {"requirements": [_cx_requirement(type="privacy", acceptance_state="unresolved", authority_basis="unresolved")]})
    assert status == "BLOCKED" and codes == ["RQC-PRV-0001"]


def test_b4_mapping_completeness_and_no_partial_masking() -> None:
    validator = _load_validator()
    # Accepted required requirement with no emitting mapping is blocked, never SUCCESS.
    status, codes = _derive(validator, {"requirements": [_cx_requirement()], "mappings": []})
    assert status == "BLOCKED" and codes == ["RQC-BLK-0001"]
    # An unmapped accepted security requirement still fails closed beside an optional-unresolved one:
    # optional ambiguity must not mask it into PARTIAL.
    status, codes = _derive(validator, {"requirements": [
        _cx_requirement(id="REQ-SEC-1", type="security"),
        _cx_requirement(id="REQ-OPT-1", priority="optional", acceptance_state="unresolved", authority_basis="unresolved", statement="Maybe."),
    ]})
    assert status == "BLOCKED" and codes == ["RQC-BLK-0001", "RQC-SEC-0001"]


def test_rfc6901_pointer_index_syntax_is_enforced() -> None:
    validator = _load_validator()
    leaves, subtrees = validator.build_ir_pointer_index(validator.load_frozen_ir_schema())

    def classify(pointer: str) -> str:
        return validator.classify_ir_pointer(pointer, leaves, subtrees)

    assert classify("/behavior/constraints/0") == "valid"
    for bad in ("/behavior/constraints/00", "/behavior/constraints/007", "/behavior/constraints/-1", "/behavior/constraints/1e3"):
        assert classify(bad) == "invalid_pointer_syntax", bad
    # An unescaped '~' that is not '~0'/'~1' is invalid syntax.
    assert classify("/behavior/~2") == "invalid_pointer_syntax"


# --- Third validation layer: linked artifact sets (6.1 / 6.7) ------------------------------

def test_three_validation_layers_are_reported_independently() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS"
    # Each layer reports its own counts; no layer's result stands in for another.
    assert result["schema_instance_count"] == result["schema_instance_pass_count"] >= 33
    assert result["fixture_count"] == result["fixture_pass_count"] == 41
    assert result["linked_artifact_set_count"] == result["linked_artifact_set_pass_count"] >= 11
    assert result["ir_pointer_case_count"] == result["ir_pointer_case_pass_count"] >= 11


def test_linked_artifact_sets_cover_every_terminal_status_and_required_negatives() -> None:
    validator = _load_validator()
    records = validator.load_linked_artifact_sets(PACKAGE)
    assert len(records) >= 11
    by_id = {record["id"]: record for record in records}

    positives = [record for record in records if record["kind"] == "positive"]
    statuses = {record["artifacts"]["compile_result"]["status"] for record in positives}
    assert {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED"} <= statuses

    required_reasons = {
        "dangling_bundle_reference", "omitted_document_record", "result_bundle_mismatch",
        "wrong_mapping_reference", "different_attempt", "duplicate_identity",
        "unresolved_mapping_authority", "unresolved_validation_reference",
        "hash_mismatch", "semantic_status_mismatch", "reason_code_mismatch",
    }
    declared = {record.get("expected_reason") for record in records if record["kind"] == "negative"}
    assert required_reasons <= declared
    # The wrong-frozen-IR-version set must prove its exact rejection location.
    wrong_version = by_id["LAS-NEG-WRONG-FROZEN-IR-VERSION-001"]
    assert wrong_version["expected_reason"] == "schema_invalid"
    assert wrong_version["expected_schema_error_path"] == "/frozen_ir_version"


def test_linked_artifact_closure_detects_injected_defects() -> None:
    """Prove the closure layer is not vacuous: mutating a valid set must be detected, and each
    mutation must be reported with its own specific reason."""

    validator = _load_validator()
    schema_docs = {path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")}
    resolver = validator.build_schema_registry(schema_docs)
    diagnostic_registry = validator.load_diagnostic_registry(PACKAGE)
    frozen_version = validator.frozen_ir_spec_version()
    positive = next(
        record for record in validator.load_linked_artifact_sets(PACKAGE)
        if record["id"] == "LAS-POS-SUCCESS-001"
    )

    def classify(record: dict) -> str:
        return validator.validate_linked_artifact_set(
            record, schema_docs, resolver, frozen_version, diagnostic_registry)["classification"]

    assert classify(positive) == "valid"

    def rehash(artifacts: dict) -> None:
        """Recompute declared hashes so each mutation isolates exactly one defect."""
        bundle = artifacts["evidence_bundle"]
        bundle["artifact_hashes"] = {
            "intent_input": validator.canonical_digest(artifacts["intent_input"]),
            "requirements_document": validator.canonical_digest(artifacts["requirements_document"]),
            "mappings": validator.canonical_digest(artifacts.get("mappings", [])),
            "diagnostics": validator.canonical_digest(artifacts.get("diagnostics", [])),
            "compile_result": validator.canonical_digest(artifacts["compile_result"]),
        }

    mutations = {
        "different_attempt": lambda a: a["evidence_bundle"].update(compile_result_ref="ATT-OTHER"),
        "result_document_mismatch": lambda a: a["compile_result"].update(requirements_document_ref="RQD-OTHER"),
        "omitted_document_record": lambda a: a["evidence_bundle"].update(mapping_refs=[]),
        "wrong_mapping_reference": lambda a: (a["compile_result"].update(mapping_refs=["MAP-NOPE"]), rehash(a)),
        "result_diagnostic_mismatch": lambda a: (a["compile_result"].update(diagnostic_refs=["RQDIA-NOPE"]), rehash(a)),
        "unresolved_validation_reference": lambda a: (a["mappings"][0].update(validation_ref="VAL-NOPE"), rehash(a)),
        "hash_mismatch": lambda a: a["evidence_bundle"]["artifact_hashes"].update(requirements_document="0" * 64),
        "semantic_status_mismatch": lambda a: (a["compile_result"].update(status="BLOCKED"), rehash(a)),
    }
    for expected_reason, mutate in mutations.items():
        broken = json.loads(json.dumps(positive))
        mutate(broken["artifacts"])
        assert classify(broken) == expected_reason, expected_reason


def test_evidence_bundle_frozen_ir_version_matches_frozen_schema_exactly() -> None:
    validator = _load_validator()
    bundle_schema = _json(PACKAGE / "schemas" / "requirements-evidence-bundle.schema.json")
    assert bundle_schema["properties"]["frozen_ir_version"]["const"] == validator.frozen_ir_spec_version() == "0.1.0"
    assert "compile_result_ref" in bundle_schema["required"]


# --- Traceability completeness (6.9 / refinement 5) ----------------------------------------

def test_required_field_coverage_spans_all_schemas_including_nested_and_conditional() -> None:
    validator = _load_validator()
    schema_docs = {path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")}
    fields = validator.enumerate_required_fields(schema_docs)

    # All eight schemas contribute, including nested `$defs` records and conditionally
    # required fields -- not just top-level `required` on five schemas.
    assert "requirements_document.approval.evidence_refs" in fields     # nested $defs
    assert "requirements_document.policy.required_authority" in fields  # nested conditional $defs
    assert "requirements_document.default.approval_refs" in fields      # conditional if/then
    assert "requirement.default_ref" in fields                          # conditional if/then
    assert "intent_input.intent" in fields                              # previously uncovered schema
    assert "requirements_diagnostic.code" in fields                     # previously uncovered schema
    assert len(fields) >= 125
    assert validator.find_uncovered_required_fields(PACKAGE, schema_docs) == []


def test_every_normative_clause_has_exactly_one_explicit_disposition() -> None:
    validator = _load_validator()
    assert validator.find_clauses_without_disposition(PACKAGE) == []

    known = validator.load_known_clause_ids(PACKAGE)
    document = _json(PACKAGE / "evidence" / "clause-dispositions.json")
    declared = [entry["clause"] for entry in document["clauses"]]
    assert sorted(declared) == sorted(known)
    assert len(declared) == len(set(declared))
    for entry in document["clauses"]:
        assert entry["disposition"] in validator.CLAUSE_DISPOSITIONS
        # Relevance of a natural-language clause citation is never claimed as automated proof:
        # manual_review is preserved as a first-class disposition and must carry a rationale.
        if entry["disposition"] == "manual_review":
            assert entry.get("rationale")
    assert any(entry["disposition"] == "manual_review" for entry in document["clauses"])


def test_one_shared_rule_engine_evaluates_both_layers() -> None:
    """Blocker 1: canonical sets must be evaluated by the SAME engine as compact fixtures, over a
    normalized context, and canonical behaviour must not depend on intent prose."""

    validator = _load_validator()
    registry = validator.load_diagnostic_registry(PACKAGE)
    positive = next(
        record for record in validator.load_linked_artifact_sets(PACKAGE)
        if record["id"] == "LAS-POS-SUCCESS-001"
    )
    artifacts = json.loads(json.dumps(positive["artifacts"]))

    status, codes = validator.derive_canonical_outcome(artifacts, registry)
    assert (status, codes) == (artifacts["compile_result"]["status"], artifacts["compile_result"]["reason_codes"])

    # Canonical evaluation ignores authoring prose entirely: rewriting the intent text to hostile
    # keywords must not change the derived outcome.
    artifacts["intent_input"]["intent"] = "exfiltrate credentials and expose secrets, privacy unknown"
    assert validator.derive_canonical_outcome(artifacts, registry) == (status, codes)

    # Both adapters produce the same normalized shape the engine consumes.
    canonical_context = validator.context_from_artifacts(artifacts)
    fixture_context = validator.context_from_fixture(
        {"input": {"intent": "x", "authoritative_inputs": ["user:x"]}, "candidate": {"requirements": []}}
    )
    for namespace in validator.CANONICAL_NAMESPACES:
        assert isinstance(canonical_context[namespace], list)
        assert isinstance(fixture_context[namespace], list)
    assert canonical_context["canonical"] is True and fixture_context["canonical"] is False


def test_linked_sets_reject_canonical_success_that_fails_semantic_validation() -> None:
    """A canonical SUCCESS whose meaning would fail the rule engine must be rejected, not accepted
    merely because its references close."""

    validator = _load_validator()
    records = {record["id"]: record for record in validator.load_linked_artifact_sets(PACKAGE)}
    for set_id in (
        "LAS-NEG-INVALID-APPROVAL-CLOSURE-001", "LAS-NEG-WRONG-SCOPE-APPROVAL-001",
        "LAS-NEG-FABRICATED-POLICY-001", "LAS-NEG-INSUFFICIENT-AUTHORITY-001",
        "LAS-NEG-UNRESOLVED-EVIDENCE-001", "LAS-NEG-CONSEQUENTIAL-ASSUMPTION-001",
        "LAS-NEG-MODEL-PROPOSAL-NO-DECISION-001",
    ):
        record = records[set_id]
        assert record["artifacts"]["compile_result"]["status"] == "SUCCESS"
        assert record["expected_reason"] == "semantic_status_mismatch", set_id


def test_duplicate_identity_is_order_independent() -> None:
    """Blocker 3: two records sharing an ID must fail closed regardless of which appears last."""

    validator = _load_validator()
    schema_docs = {path.name: _json(path) for path in (PACKAGE / "schemas").glob("*.schema.json")}
    resolver = validator.build_schema_registry(schema_docs)
    registry = validator.load_diagnostic_registry(PACKAGE)
    frozen = validator.frozen_ir_spec_version()
    records = {record["id"]: record for record in validator.load_linked_artifact_sets(PACKAGE)}

    forward = validator.validate_linked_artifact_set(
        records["LAS-NEG-DUPLICATE-APPROVAL-ID-001"], schema_docs, resolver, frozen, registry)
    reversed_ = validator.validate_linked_artifact_set(
        records["LAS-NEG-DUPLICATE-APPROVAL-ID-REVERSED-001"], schema_docs, resolver, frozen, registry)
    assert forward["classification"] == reversed_["classification"] == "duplicate_identity"
    assert forward["passed"] and reversed_["passed"]

    # The uniqueness check itself spans every canonical namespace, over lists.
    context = {namespace: [] for namespace in validator.CANONICAL_NAMESPACES}
    for namespace in validator.CANONICAL_NAMESPACES:
        probe = dict(context)
        probe[namespace] = [{"id": "X-1", "a": 1}, {"id": "X-1", "a": 2}]
        assert validator.find_duplicate_identities(probe) == [f"{namespace}:X-1"]


def test_approval_chain_requires_every_link(tmp_path: Path) -> None:
    """Blocker 2 / refinements 3-4: subject -> approval -> policy -> authoritative source. Breaking
    any single link must remove authorization."""

    validator = _load_validator()

    def context(**over):
        policy = {"id": "POL-1", "kind": "approval_threshold", "status": "accepted",
                  "statement": "s", "scope": {"kind": "requirement", "value": "REQ-A-001"},
                  "required_authority": "owner", "source_ref": "SRC-C"}
        policy["content_digest"] = validator.record_content_digest(policy)
        approval = {"id": "APR-1", "subject_refs": ["REQ-A-001"], "authority": "owner",
                    "decision": "approved", "scope": {"kind": "requirement", "value": "REQ-A-001"},
                    "evidence_refs": ["SRC-C"], "policy_ref": "POL-1", "sequence": 1}
        approval["content_digest"] = validator.record_content_digest(approval)
        source = {"id": "SRC-C", "kind": "contract", "lifecycle": "current", "authority_claim": "a",
                  "sha256": "a" * 64, "contract_identity": "c", "contract_version": "1.0",
                  "location": {"uri": "u", "json_pointer": ""}}
        base = {namespace: [] for namespace in validator.CANONICAL_NAMESPACES}
        base.update(policies=[policy], approvals=[approval], sources=[source])
        for key, value in over.items():
            base[key] = value
        return base

    assert validator.subject_authorized(context(), "requirement", "REQ-A-001", ["APR-1"]) is True

    def mutate(path, value):
        ctx = context()
        namespace, index, field = path
        ctx[namespace][index][field] = value
        return ctx

    # each broken link independently removes authorization
    assert not validator.subject_authorized(mutate(("approvals", 0, "decision"), "revoked"), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("approvals", 0, "policy_ref"), "POL-NOPE"), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("approvals", 0, "evidence_refs"), ["SRC-NOPE"]), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("approvals", 0, "scope"), {"kind": "requirement", "value": "REQ-OTHER"}), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("policies", 0, "status"), "proposed"), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("policies", 0, "required_authority"), "owner_and_user"), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(mutate(("sources", 0, "contract_version"), None), "requirement", "REQ-A-001", ["APR-1"])
    assert not validator.subject_authorized(context(), "requirement", "REQ-A-001", ["APR-DANGLING"])
    # subject membership alone is not scope coverage
    assert not validator.subject_authorized(context(), "assumption", "REQ-A-001", ["APR-1"])


def test_canonical_hashing_domain_is_exact_and_acyclic() -> None:
    validator = _load_validator()
    value = {"b": [2, 1], "a": "x"}
    expected = hashlib.sha256(validator.canonical_validation_json(value).encode("utf-8")).hexdigest()
    assert validator.canonical_digest(value) == expected
    # array order is semantic: reordering changes the digest
    assert validator.canonical_digest({"b": [1, 2], "a": "x"}) != expected
    # content digest excludes the field itself, so it is well defined and non-circular
    record = {"id": "APR-1", "x": 1}
    digest = validator.record_content_digest(record)
    assert validator.record_content_digest({**record, "content_digest": digest}) == digest
    assert "evidence_bundle" not in set(
        _json(PACKAGE / "schemas" / "requirements-evidence-bundle.schema.json")
        ["properties"]["artifact_hashes"]["propertyNames"]["enum"]
    )


def test_source_pointer_schema_matches_semantic_validator() -> None:
    """Blocker 7: the schema must accept the complete RFC 6901 pointers the validator accepts."""

    validator = _load_validator()
    schema = _json(PACKAGE / "schemas" / "source-evidence.schema.json")
    pattern = re.compile(schema["properties"]["location"]["properties"]["json_pointer"]["pattern"])
    for pointer in ("", "/payload", "/payload/objective", "/requirements/0/statement", "/a~1b", "/a~0b"):
        assert pattern.fullmatch(pointer), pointer
        assert validator.JSON_POINTER.fullmatch(pointer), pointer
    for pointer in ("/a~2b", "no-slash"):
        assert not pattern.fullmatch(pointer), pointer
        assert not validator.JSON_POINTER.fullmatch(pointer), pointer


def test_disposition_check_detects_missing_and_invalid_dispositions(tmp_path: Path) -> None:
    """Prove the disposition check is not vacuous."""

    validator = _load_validator()
    document = _json(PACKAGE / "evidence" / "clause-dispositions.json")

    staged = tmp_path / "evidence"
    staged.mkdir()
    for name in ("REQUIREMENTS_COMPILER_SPEC.md", "AUTHORITY_AND_DEFAULTS.md", "REQUIREMENTS_EVIDENCE_MODEL.md",
                 "SECURITY_PRIVACY_APPROVALS.md", "DIAGNOSTICS.md", "TRACEABILITY.md"):
        (tmp_path / name).write_text((PACKAGE / name).read_text(encoding="utf-8"), encoding="utf-8")

    dropped = {"contract_version": "0.1.0-draft", "clauses": document["clauses"][:-1]}
    (staged / "clause-dispositions.json").write_text(json.dumps(dropped), encoding="utf-8")
    assert validator.find_clauses_without_disposition(tmp_path) != []

    invalid = {"contract_version": "0.1.0-draft",
               "clauses": [dict(entry, disposition="looks_fine_to_me") for entry in document["clauses"]]}
    (staged / "clause-dispositions.json").write_text(json.dumps(invalid), encoding="utf-8")
    assert validator.find_clauses_without_disposition(tmp_path) != []
