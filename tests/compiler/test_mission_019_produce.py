from __future__ import annotations

from promptrig.compiler.requirements_contract import compile_requirements_input
from promptrig.compiler.requirements_produce import produce_requirements


def _intent(*, mode: str, input_id: str = "INP-019-001") -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str = "SRC-019-001", **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://019", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str = "REQ-019-001", source_id: str = "SRC-019-001", **extra: object) -> dict:
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


def _prs_envelope(**extra: object) -> dict:
    envelope = {
        "intent_input": _intent(mode="prs", input_id="INP-019-PRS"),
        "sources": [_source(kind="prs", source_id="SRC-019-PRS")],
        "claims": [_claim(req_id="REQ-019-PRS", source_id="SRC-019-PRS")],
    }
    envelope.update(extra)
    return envelope


def test_prs_envelope_produces_prs_sources() -> None:
    envelope = _prs_envelope()
    artifacts = produce_requirements(envelope)
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "prs"
    result = compile_requirements_input(envelope)
    assert result.status != "INVALID_OUTPUT"


def test_wrong_kind_for_prs_is_schema_invalid() -> None:
    envelope = _prs_envelope()
    envelope["sources"] = [_source(kind="file", source_id="SRC-019-PRS")]
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_imports_rejected_on_prs() -> None:
    envelope = _prs_envelope(imports=["some/path.txt"])
    assert produce_requirements(envelope) == {}
