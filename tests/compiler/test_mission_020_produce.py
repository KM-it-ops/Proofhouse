from __future__ import annotations

from pathlib import Path

from promptrig.compiler.requirements_contract import compile_requirements_input

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"


def _plain_payload(text: str | None = None) -> dict:
    return {
        "profile": "plain_language_v0",
        "text": FIXTURE.read_text(encoding="utf-8") if text is None else text,
    }


def test_valid_grammar_is_blocked_not_invalid_or_success() -> None:
    from promptrig.compiler.requirements_plain_produce import produce_plain_language_requirements

    artifacts = produce_plain_language_requirements(FIXTURE.read_text(encoding="utf-8"))
    document = artifacts["requirements_document"]
    ids = {item["id"] for item in document["requirements"]}
    assert "REQ-PL-GOAL" in ids
    assert "REQ-PL-001" in ids
    assert "REQ-PL-C001" in ids
    goal_map = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-GOAL")
    assert goal_map["outcome"] == "direct"
    assert goal_map["target_pointer"] == "/objective/goal"
    numbered = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    assert numbered["outcome"] == "unresolved"
    assert "target_pointer" not in numbered
    result = compile_requirements_input(_plain_payload())
    assert result.status == "BLOCKED"
    assert "RQC-BLK-0001" in result.reason_codes


def test_freeform_text_is_parse_blocked() -> None:
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": "Please build a helpful assistant that does stuff."}
    )
    assert result.status == "BLOCKED"
    assert "PL-PARSE-0001" in result.reason_codes


def test_goal_only_plain_language_is_parse_blocked() -> None:
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": "Goal: Only a goal.\n"}
    )
    assert result.status == "BLOCKED"
    assert "PL-PARSE-0002" in result.reason_codes


def test_extra_keys_are_schema_invalid() -> None:
    payload = _plain_payload()
    payload["repair_budget"] = 1
    result = compile_requirements_input(payload)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_prs_envelope_still_compiles() -> None:
    envelope = {
        "intent_input": {
            "contract_version": "0.1.0-draft",
            "input_id": "INP-020-PRS",
            "authoring_mode": "prs",
            "intent": "Compile from an envelope.",
            "authoritative_inputs": ["prs:envelope"],
            "non_authoritative_inputs": [],
        },
        "sources": [
            {
                "id": "SRC-020-PRS",
                "kind": "prs",
                "lifecycle": "current",
                "authority_claim": "Envelope supplied the objective.",
                "location": {"uri": "prs://020", "json_pointer": "/claims/0"},
            }
        ],
        "claims": [
            {
                "id": "REQ-020-PRS",
                "type": "objective",
                "statement": "Compile from an envelope.",
                "priority": "required",
                "acceptance_state": "accepted",
                "authority_basis": "directly_stated",
                "source_refs": ["SRC-020-PRS"],
                "acceptance_criteria": ["Engine owns status."],
                "consequential": False,
            }
        ],
    }
    result = compile_requirements_input(envelope)
    assert result.status != "INVALID_OUTPUT"


def test_compile_requirements_input_help_names_plain_language() -> None:
    from promptrig.compiler.cli_compiler import build_parser

    parser = build_parser()
    req = None
    for action in parser._subparsers._group_actions:
        req = action.choices.get("compile-requirements")
        if req is not None:
            break
    assert req is not None
    help_text = req.format_help()
    assert "plain_language_v0" in help_text
    input_action = next(a for a in req._actions if getattr(a, "dest", None) == "input")
    assert input_action.help == (
        "Path to canonical artifact JSON, file/api/simple/developer/prs envelope, "
        "or plain_language_v0 text envelope, or '-' for stdin."
    )
