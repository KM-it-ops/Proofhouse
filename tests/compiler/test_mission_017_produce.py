from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.cli_compiler import main as compiler_main

ROOT = Path(__file__).resolve().parents[2]
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def _artifacts(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item["artifacts"]
    raise KeyError(set_id)


def _intent(*, mode: str, input_id: str = "INP-017-001") -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str = "SRC-017-001", **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://017", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str = "REQ-017-001", source_id: str = "SRC-017-001", **extra: object) -> dict:
    record = {
        "id": req_id,
        "type": "objective",
        "statement": "Compile from an envelope.",
        "priority": "required",
        "acceptance_state": "accepted",
        "authority_basis": "directly_stated",
        "source_refs": [source_id],
        "acceptance_criteria": ["Engine owns status."],
        "consequential": False,
    }
    record.update(extra)
    return record


def _file_envelope(**extra: object) -> dict:
    envelope = {
        "intent_input": _intent(mode="file"),
        "sources": [_source(kind="file")],
        "claims": [_claim()],
    }
    envelope.update(extra)
    return envelope


def _api_envelope() -> dict:
    return {
        "intent_input": _intent(mode="api", input_id="INP-017-API"),
        "sources": [_source(kind="api_request", source_id="SRC-017-API")],
        "claims": [_claim(req_id="REQ-017-API", source_id="SRC-017-API")],
    }


def test_canonical_payload_matches_direct_compile() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements, compile_requirements_input

    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    assert compile_requirements_input(artifacts).to_dict() == compile_requirements(artifacts).to_dict()


def test_file_envelope_sources_are_file_kind() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input
    from promptrig.compiler.requirements_produce import produce_requirements

    artifacts = produce_requirements(_file_envelope())
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "file"
    result = compile_requirements_input(_file_envelope())
    assert result.command == "compile-requirements"
    assert result.status in {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}


def test_api_envelope_sources_are_api_request_kind() -> None:
    from promptrig.compiler.requirements_produce import produce_requirements

    artifacts = produce_requirements(_api_envelope())
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "api_request"


def test_simple_developer_prs_are_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    for mode in ("simple", "developer", "prs"):
        envelope = _file_envelope()
        envelope["intent_input"]["authoring_mode"] = mode
        result = compile_requirements_input(envelope)
        assert result.status == "INVALID_OUTPUT"
        assert "RQC-SCH-0001" in result.reason_codes


def test_unknown_top_level_field_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope(prose="not allowed")
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_unknown_contract_version_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["intent_input"]["contract_version"] = "9.9.9"
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_file_imports_unsupported_and_path_not_opened(tmp_path: Path) -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input
    from promptrig.compiler.requirements_produce import produce_requirements

    missing = tmp_path / "does-not-exist-017.txt"
    envelope = _file_envelope(imports=[str(missing)])
    artifacts = produce_requirements(envelope)
    statements = [r["statement"] for r in artifacts["requirements_document"]["requirements"]]
    assert str(missing) in statements
    assert any(r["acceptance_state"] == "unsupported" for r in artifacts["requirements_document"]["requirements"])
    result = compile_requirements_input(envelope)
    assert result.status == "BLOCKED"
    assert "RQC-UNS-0001" in result.reason_codes
    assert not missing.exists()


def test_duplicate_source_ids_are_engine_rqc_src_0001() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["sources"] = [_source(kind="file"), _source(kind="file")]
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SRC-0001" in result.reason_codes


def test_model_self_accept_is_not_success() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["claims"] = [_claim(authority_basis="model_suggested")]
    result = compile_requirements_input(envelope)
    assert result.status != "SUCCESS"
    assert "RQC-MDL-0001" in result.reason_codes


def test_digest_ambiguity_records_oq_008_001() -> None:
    from promptrig.compiler.requirements_produce import produce_requirements
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["sources"] = [_source(kind="file", fragment="Compile from an envelope.")]
    artifacts = produce_requirements(envelope)
    questions = artifacts["requirements_document"]["open_questions"]
    assert any("OQ-008-001" in q.get("text", "") for q in questions)
    claim = next(r for r in artifacts["requirements_document"]["requirements"] if r["id"] == "REQ-017-001")
    assert claim["acceptance_state"] == "unresolved"
    result = compile_requirements_input(envelope)
    assert result.status != "SUCCESS"


def test_harness_still_shares_evaluate_contract_rules() -> None:
    import importlib.util
    from types import ModuleType

    from promptrig.compiler import requirements_contract as rc

    path = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "validate_contract.py"
    spec = importlib.util.spec_from_file_location("mission008_contract_validator", path)
    assert spec and spec.loader
    module = ModuleType("mission008_contract_validator")
    spec.loader.exec_module(module)
    assert module.evaluate_contract_rules is rc.evaluate_contract_rules
