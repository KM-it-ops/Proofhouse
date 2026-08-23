from __future__ import annotations

from promptrig.compiler.requirements_contract import compile_requirements_input
from promptrig.compiler.requirements_produce import produce_requirements


def _intent(*, mode: str, input_id: str) -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str, **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://021", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str, source_id: str, **extra: object) -> dict:
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


def test_oq_008_001_file_without_digest_is_blocked_not_unanswered() -> None:
    envelope = {
        "intent_input": _intent(mode="file", input_id="INP-021-001"),
        "sources": [_source(kind="file", source_id="SRC-021-001")],
        "claims": [_claim(req_id="REQ-021-001", source_id="SRC-021-001")],
    }
    artifacts = produce_requirements(envelope)
    questions = artifacts["requirements_document"]["open_questions"]
    assert questions
    text = questions[0]["text"]
    assert "OQ-008-001" in text
    assert "unanswered" not in text.lower()
    claim = next(
        item
        for item in artifacts["requirements_document"]["requirements"]
        if item["id"] == "REQ-021-001"
    )
    assert claim["acceptance_state"] == "unresolved"
    result = compile_requirements_input(envelope)
    assert result.status == "BLOCKED"
    assert result.reason_codes == ("RQC-AMB-0001",)


def test_oq_008_001_fragment_without_digest_stays_invalid() -> None:
    envelope = {
        "intent_input": _intent(mode="file", input_id="INP-021-002"),
        "sources": [
            _source(kind="file", source_id="SRC-021-002", fragment="Compile from an envelope.")
        ],
        "claims": [_claim(req_id="REQ-021-002", source_id="SRC-021-002")],
    }
    assert produce_requirements(envelope) == {}
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes
