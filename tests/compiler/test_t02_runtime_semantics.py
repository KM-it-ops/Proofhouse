"""T02 (review F01): mandatory semantics reach the live request or block it.

On 78e512c the OpenAI execution path built its only system message from the
goal, instructions and constraints; requirement statements, the uncertainty
and evidence policies, success/failure criteria and policy blocks were kept in
the artifact's semantic sidecar but never sent. These tests inspect the final
``PreparedLiveRequest`` a recording transport receives, not intermediate flags.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai
from proofhouse.compiler.runtime_context import RUNTIME_FIELD_MAP, render_runtime_context

from .fixtures.ir_fixtures import ir_with_openai_structured_output, minimal_valid_ir

SCHEMA = Path(__file__).resolve().parents[2] / "src" / "proofhouse" / "compiler" / "schemas" / "promptrig_ir_v0_1.schema.json"


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": 200, "payload": {"choices": []}})()


def _execute(ir: dict, transport: RecordingTransport):
    return execute_openai(
        json.dumps(ir),
        LiveOpenAIRequest(
            opt_in=True,
            model="synthetic-model",
            credential_value="dummy-not-a-secret",
            max_output_tokens=16,
            max_cost_usd="1",
            transport=transport,
        ),
    )


def _sentinel_ir() -> dict:
    ir = minimal_valid_ir()
    ir["requirements"][0]["statement"] = "REQUIREMENT_SENTINEL_X41 never omit this mandatory instruction"
    ir["requirements"][0]["acceptance"] = ["ACCEPTANCE_SENTINEL_X44"]
    ir["behavior"]["uncertainty_policy"] = "UNCERTAINTY_SENTINEL_X42"
    ir["behavior"]["evidence_policy"] = "EVIDENCE_SENTINEL_X43"
    ir["objective"]["success_criteria"] = ["SUCCESS_SENTINEL_X45"]
    ir["objective"]["failure_conditions"] = ["FAILURE_SENTINEL_X46"]
    ir["behavior"]["instructions"] = ["INSTRUCTION_SENTINEL_X47"]
    ir["behavior"]["constraints"] = ["CONSTRAINT_SENTINEL_X48"]
    ir["assumptions"] = ["ASSUMPTION_SENTINEL_X49"]
    ir["open_questions"] = ["QUESTION_SENTINEL_X50"]
    return ir


def _system_text(prepared: Any) -> str:
    return "\n".join(m["content"] for m in prepared.body["messages"] if m["role"] == "system")


def test_probe_sentinels_reach_the_transport_body() -> None:
    transport = RecordingTransport()
    result = _execute(_sentinel_ir(), transport)
    assert result.status == "success", result.diagnostics
    assert len(transport.calls) == 1
    system = _system_text(transport.calls[0])
    for sentinel in (
        "REQUIREMENT_SENTINEL_X41",
        "ACCEPTANCE_SENTINEL_X44",
        "UNCERTAINTY_SENTINEL_X42",
        "EVIDENCE_SENTINEL_X43",
        "SUCCESS_SENTINEL_X45",
        "FAILURE_SENTINEL_X46",
        "INSTRUCTION_SENTINEL_X47",
        "CONSTRAINT_SENTINEL_X48",
        "ASSUMPTION_SENTINEL_X49",
        "QUESTION_SENTINEL_X50",
    ):
        assert sentinel in system, sentinel


def test_requirement_id_and_mandatory_flag_are_rendered() -> None:
    transport = RecordingTransport()
    _execute(_sentinel_ir(), transport)
    system = _system_text(transport.calls[0])
    assert "REQ-001" in system
    assert "MANDATORY" in system


def test_output_contract_is_enforced_by_response_format() -> None:
    transport = RecordingTransport()
    result = _execute(ir_with_openai_structured_output(compliant=True), transport)
    assert result.status == "success"
    body = transport.calls[0].body
    assert body["response_format"]["type"] == "json_schema"
    mapping = {row["source_path"]: row for row in result.envelope["runtime_context"]["fields"]}
    assert mapping["/output_contracts"]["disposition"] == "enforced_by_request_parameter"


def test_envelope_records_mapping_and_system_digest() -> None:
    transport = RecordingTransport()
    result = _execute(_sentinel_ir(), transport)
    context = result.envelope["runtime_context"]
    rendered = {row["source_path"] for row in context["fields"] if row["disposition"] == "rendered"}
    assert {"/requirements", "/behavior/uncertainty_policy", "/behavior/evidence_policy", "/assumptions"} <= rendered
    import hashlib

    digest = hashlib.sha256(_system_text(transport.calls[0]).encode("utf-8")).hexdigest()
    assert context["system_message_sha256"] == digest


@pytest.mark.parametrize("key", ["security", "privacy"])
def test_free_text_policy_blocks_are_refused_before_send(key: str) -> None:
    """The compiler refuses free-text policy blocks it cannot enforce; nothing is sent."""
    ir = minimal_valid_ir()
    ir[key] = {"rules": ["POLICY_SENTINEL"]}
    transport = RecordingTransport()
    result = _execute(ir, transport)
    assert result.status == "error"
    assert transport.calls == []


def test_required_knowledge_source_without_content_blocks_before_send() -> None:
    ir = minimal_valid_ir()
    ir["knowledge"] = {"sources": [{"id": "kb.main", "kind": "file", "required": True, "sha256": "b" * 64}]}
    transport = RecordingTransport()
    result = _execute(ir, transport)
    assert result.status == "error"
    assert "EXE-SEM-0001" in result.diagnostics
    assert transport.calls == []
    unsupported = result.envelope["unsupported_semantics"]
    assert unsupported[0]["source_path"] == "/knowledge/sources/0"


def test_persistent_memory_blocks_before_send() -> None:
    ir = minimal_valid_ir()
    ir["memory"] = {"mode": "persistent", "retention": "30 days"}
    transport = RecordingTransport()
    result = _execute(ir, transport)
    assert result.status == "error"
    assert "EXE-SEM-0001" in result.diagnostics
    assert transport.calls == []


def test_every_ir_top_level_field_has_an_explicit_runtime_disposition() -> None:
    """A new IR field must be mapped deliberately; silence is not a disposition."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    mapped_roots = {path.split("/")[1] for path in RUNTIME_FIELD_MAP}
    assert set(schema["properties"]) <= mapped_roots, set(schema["properties"]) - mapped_roots


def test_render_is_deterministic() -> None:
    ir = _sentinel_ir()
    assert render_runtime_context(ir).system_text == render_runtime_context(json.loads(json.dumps(ir))).system_text


@pytest.mark.parametrize("field", ["uncertainty_policy", "evidence_policy"])
def test_render_contains_each_behavior_policy(field: str) -> None:
    ir = minimal_valid_ir()
    ir["behavior"][field] = f"POLICY_{field.upper()}"
    assert f"POLICY_{field.upper()}" in render_runtime_context(ir).system_text
