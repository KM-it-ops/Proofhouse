"""evaluate_contract_rules build-plan unit (T-P4-06)."""

from __future__ import annotations

from proofhouse.compiler.requirements_contract import (
    REQUIREMENTS_CONTRACT_VERSION,
    evaluate_contract_rules,
)

REGISTRY = {"RQC-SEM-0001": {}, "RQC-BLD-0001": {}}

PROMPT_CTX = {
    "requirements": [],
    "sources": [],
    "mappings": [],
    "conflicts": [],
    "defaults": [],
    "model_proposals": [],
    "emitted_diagnostic_codes": [],
    "unknown_fields": False,
    "version": REQUIREMENTS_CONTRACT_VERSION,
    "semantically_empty": True,
    "assumptions": [],
}


def test_prompt_program_default_is_bit_identical() -> None:
    left = evaluate_contract_rules(PROMPT_CTX, REGISTRY)
    right = evaluate_contract_rules({**PROMPT_CTX, "evaluation_unit": "prompt_program"}, REGISTRY)
    assert left == right
    assert left == ("INVALID_OUTPUT", ["RQC-SEM-0001"])


def test_mixed_prompt_and_site_is_partial_with_named_code() -> None:
    context = {
        "evaluation_unit": "build_plan",
        "artifacts": [
            {"class": "prompt", "profile": "SP-static"},
            {"class": "site", "profile": "SP-react-motion"},
        ],
    }
    status, codes = evaluate_contract_rules(context, REGISTRY)
    assert status == "PARTIAL"
    assert "RQC-BLD-0001" in codes
    assert any(code.startswith("decertification_scope:") for code in codes)
    assert "prompt" in ",".join(codes)
    assert "site" in ",".join(codes)
