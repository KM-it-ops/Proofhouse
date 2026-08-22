from __future__ import annotations

from promptrig.compiler.requirements_contract import compile_requirements_input
from promptrig.compiler.requirements_produce import produce_requirements


def _intent(*, mode: str, input_id: str = "INP-018-001") -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str = "SRC-018-001", **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://018", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str = "REQ-018-001", source_id: str = "SRC-018-001", **extra: object) -> dict:
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


def _simple_envelope(**extra: object) -> dict:
    envelope = {
        "intent_input": _intent(mode="simple", input_id="INP-018-SMP"),
        "sources": [_source(kind="ordinary_language", source_id="SRC-018-SMP")],
        "claims": [_claim(req_id="REQ-018-SMP", source_id="SRC-018-SMP")],
    }
    envelope.update(extra)
    return envelope


def _developer_envelope(**extra: object) -> dict:
    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-018-DEV"),
        "sources": [_source(kind="developer_config", source_id="SRC-018-DEV")],
        "claims": [_claim(req_id="REQ-018-DEV", source_id="SRC-018-DEV")],
    }
    envelope.update(extra)
    return envelope


def test_simple_envelope_produces_ordinary_language_sources() -> None:
    envelope = _simple_envelope()
    artifacts = produce_requirements(envelope)
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "ordinary_language"
    result = compile_requirements_input(envelope)
    assert result.status != "INVALID_OUTPUT"


def test_developer_envelope_produces_developer_config_sources() -> None:
    envelope = _developer_envelope()
    artifacts = produce_requirements(envelope)
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "developer_config"
    result = compile_requirements_input(envelope)
    assert result.status != "INVALID_OUTPUT"


def test_wrong_kind_for_simple_is_schema_invalid() -> None:
    envelope = _simple_envelope()
    envelope["sources"] = [_source(kind="file", source_id="SRC-018-SMP")]
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_imports_rejected_on_simple() -> None:
    envelope = _simple_envelope(imports=["some/path.txt"])
    assert produce_requirements(envelope) == {}


def test_compile_requirements_input_help_names_simple_developer() -> None:
    from promptrig.compiler.cli_compiler import build_parser

    parser = build_parser()
    req = None
    for action in parser._subparsers._group_actions:
        req = action.choices.get("compile-requirements")
        if req is not None:
            break
    assert req is not None
    help_text = req.format_help()
    lower = help_text.lower()
    assert "simple" in lower and "developer" in lower
    input_action = next(a for a in req._actions if getattr(a, "dest", None) == "input")
    assert "simple" in (input_action.help or "").lower()
    assert "developer" in (input_action.help or "").lower()
