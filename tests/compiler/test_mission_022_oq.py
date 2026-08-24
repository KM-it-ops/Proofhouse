from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from promptrig.compiler.requirements_contract import (
    REQUIREMENTS_CONTRACT_VERSION,
    compile_requirements,
)

ROOT = Path(__file__).resolve().parents[2]
LAS = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "fixtures" / "linked_artifact_sets.json"


def _set(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item
    raise KeyError(set_id)


def test_oq_008_005_exact_draft_version_still_required() -> None:
    assert REQUIREMENTS_CONTRACT_VERSION == "0.1.0-draft"
    result = compile_requirements(_set("LAS-POS-SUCCESS-001")["artifacts"])
    assert result.status == "SUCCESS"
    assert result.contract_version == "0.1.0-draft"


def test_oq_008_005_rejects_non_exact_versions() -> None:
    for version in ("0.1.0", "0.1.0-draft.1", ">=0.1.0", "", "1.0.0"):
        artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
        artifacts["intent_input"]["contract_version"] = version
        result = compile_requirements(artifacts)
        assert result.status == "INVALID_OUTPUT", version
        assert "RQC-VER-0001" in result.reason_codes, version


def test_oq_008_005_rejects_missing_contract_version() -> None:
    artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
    del artifacts["intent_input"]["contract_version"]
    result = compile_requirements(artifacts)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-VER-0001" in result.reason_codes


def _consequential_success_overlay() -> dict:
    """Deepcopy SUCCESS and mark the existing requirement consequential for Class 6a."""

    artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
    requirement = artifacts["requirements_document"]["requirements"][0]
    requirement["consequential"] = True
    return artifacts


def _approval(*, approval_id: str, requirement_id: str, policy_ref: str, authority: str) -> dict:
    return {
        "id": approval_id,
        "subject_refs": [requirement_id],
        "authority": authority,
        "decision": "approved",
        "scope": {"kind": "requirement", "value": requirement_id},
        "evidence_refs": ["SRC-LAS-001"],
        "policy_ref": policy_ref,
    }


def _policy(*, policy_id: str, requirement_id: str, required_authority: str, source_ref: str) -> dict:
    return {
        "id": policy_id,
        "kind": "approval_threshold",
        "status": "accepted",
        "statement": "Consequential meaning requires the named authority.",
        "scope": {"kind": "requirement", "value": requirement_id},
        "required_authority": required_authority,
        "source_ref": source_ref,
    }


def _contract_source() -> dict:
    return {
        "id": "SRC-LAS-POLICY",
        "kind": "contract",
        "lifecycle": "current",
        "authority_claim": "Accepted governing contract for approvals.",
        "location": {
            "uri": "contract://promptrig/governance",
            "json_pointer": "/policies/approval",
        },
        "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "contract_identity": "promptrig.governance",
        "contract_version": "1.4.0",
    }


def test_oq_008_003_unresolvable_policy_ref_is_blocked() -> None:
    artifacts = _consequential_success_overlay()
    document = artifacts["requirements_document"]
    requirement = document["requirements"][0]
    requirement_id = requirement["id"]
    requirement["approval_refs"] = ["APR-LAS-MISSING-POLICY"]
    document["approvals"] = [
        _approval(
            approval_id="APR-LAS-MISSING-POLICY",
            requirement_id=requirement_id,
            policy_ref="POL-DOES-NOT-EXIST",
            authority="owner",
        )
    ]
    result = compile_requirements(artifacts)
    assert result.status == "BLOCKED"
    assert "RQC-APR-0001" in result.reason_codes


def test_oq_008_003_conflicting_required_authority_is_undeterminable() -> None:
    artifacts = _consequential_success_overlay()
    document = artifacts["requirements_document"]
    requirement = document["requirements"][0]
    requirement_id = requirement["id"]
    requirement["approval_refs"] = ["APR-LAS-OWNER", "APR-LAS-USER"]
    document["sources"].append(_contract_source())
    document["policies"] = [
        _policy(
            policy_id="POL-LAS-OWNER",
            requirement_id=requirement_id,
            required_authority="owner",
            source_ref="SRC-LAS-POLICY",
        ),
        _policy(
            policy_id="POL-LAS-USER",
            requirement_id=requirement_id,
            required_authority="user",
            source_ref="SRC-LAS-POLICY",
        ),
    ]
    document["approvals"] = [
        _approval(
            approval_id="APR-LAS-OWNER",
            requirement_id=requirement_id,
            policy_ref="POL-LAS-OWNER",
            authority="owner",
        ),
        _approval(
            approval_id="APR-LAS-USER",
            requirement_id=requirement_id,
            policy_ref="POL-LAS-USER",
            authority="user",
        ),
    ]
    result = compile_requirements(artifacts)
    assert result.status == "BLOCKED"
    assert "RQC-APR-0001" in result.reason_codes


def test_oq_008_003_does_not_freeze_owner_only_categories() -> None:
    source = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    assert "OWNER_ONLY" not in source
    assert "owner_only_categories" not in source

