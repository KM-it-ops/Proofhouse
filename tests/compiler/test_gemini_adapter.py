from __future__ import annotations

import copy
import json
import socket

import pytest

from promptrig.compiler.adapters.gemini import ADAPTER_ID, ADAPTER_VERSION, GeminiAdapter
from promptrig.compiler.canonical import canonical_sha256
from promptrig.compiler.contracts import CapabilityDecision

from .fixtures.ir_fixtures import (
    ir_with_gemini_built_in_tool,
    ir_with_gemini_function_tool,
    ir_with_gemini_structured_output,
    ir_with_gemini_thinking,
    minimal_valid_ir,
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    """Every test in this file runs with socket construction/connection
    patched to raise -- the Gemini adapter must never touch the network,
    including implicitly, anywhere in describe/check_capabilities/lower."""

    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted by the Gemini adapter (must be zero-network)")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


def test_describe_is_deterministic_and_identifies_as_gemini(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    d1 = adapter.describe().to_dict()
    d2 = adapter.describe().to_dict()
    assert d1 == d2
    assert d1["adapter_id"] == "gemini"
    assert d1["provider_id"] == "gemini"
    assert d1["adapter_id"] not in {"fake", "openai", "anthropic"}


def test_adapter_identity_stable(diagnostic_factory):
    a1 = GeminiAdapter(diagnostic_factory)
    a2 = GeminiAdapter(diagnostic_factory)
    assert a1.adapter_id == a2.adapter_id == ADAPTER_ID
    assert a1.adapter_version == a2.adapter_version == ADAPTER_VERSION


def test_capability_manifest_supports_structured_json_and_function_calling(diagnostic_factory):
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    assert manifest.resolve("output.structured_json@1") == "supported"
    assert manifest.resolve("tools.function_calling@1") == "supported"


def test_capability_manifest_thinking_is_conditional_not_supported(diagnostic_factory):
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    assert manifest.resolve("reasoning.thinking_level@1") == "conditional"


def test_capability_manifest_built_in_tools_is_unsupported(diagnostic_factory):
    """Built-in/grounding tools and caller-defined function tools are
    contractually distinct for Gemini (PROVIDER_SELECTION_MATRIX.md) and
    must not be collapsed into one capability id or resolution."""
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    assert manifest.resolve("tools.server_executed@1") == "unsupported"
    assert manifest.resolve("tools.server_executed@1") != manifest.resolve("tools.function_calling@1")


def test_capability_manifest_carries_machine_readable_limits(diagnostic_factory):
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    limits = manifest.limits_for("output.structured_json@1")
    assert limits["additional_properties_required_false"] is False
    assert limits["all_properties_must_be_required"] is False
    assert "source" in limits


def test_capability_manifest_built_in_tools_limits_explain_ir_gap(diagnostic_factory):
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    limits = manifest.limits_for("tools.server_executed@1")
    assert "note" in limits
    assert "IR" in limits["note"] or "frozen" in limits["note"]
    assert "source" in limits


def test_capability_manifest_thinking_limits_document_signature_requirements(diagnostic_factory):
    manifest = GeminiAdapter(diagnostic_factory).capability_manifest()
    limits = manifest.limits_for("reasoning.thinking_level@1")
    assert limits["thought_signature_required_with_function_calling"] is True
    assert limits["thought_signature_must_be_echoed_back_on_continuation"] is True
    assert "source" in limits


def test_check_capabilities_required_gap(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    ir["provider_requirements"] = {"required_capabilities": ["nonexistent@1"], "optional_capabilities": []}
    decisions = adapter.check_capabilities(ir)
    assert decisions[0].resolution == "unsupported"


def test_lower_fails_explicitly_on_missing_required_capability(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = (CapabilityDecision(capability="nonexistent@1", requirement="required", resolution="unsupported"),)
    result = adapter.lower(ir, resolution)
    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-CAPABILITY-0001" for d in result.diagnostics)


def test_lower_compliant_structured_output_succeeds(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    assert len(result.artifacts) == 1
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["output_config"]["response_mime_type"] == "application/json"
    assert "response_schema" in payload["output_config"]


def test_lower_compliant_structured_output_accepts_loosely_typed_schema(diagnostic_factory):
    """The fixture schema omits additionalProperties: false and leaves a
    property out of required -- non-compliant for OpenAI/Anthropic, but
    fully compliant for Gemini's documented subset (genuine divergence)."""
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)
    assert result.status == "success"


def test_lower_structured_output_emits_property_ordering(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["output_config"]["response_schema"]["propertyOrdering"] == ["answer", "confidence"]


def test_lower_noncompliant_structured_output_fails_explicitly(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=False)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-ADAPTER-0001" for d in result.diagnostics)


def test_lower_compliant_function_tool_succeeds(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_function_tool(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["function_tools"][0]["name"] == "lookup_answer"
    assert "parameters" in payload["function_tools"][0]
    assert "strict" not in payload["function_tools"][0]


def test_lower_noncompliant_function_tool_fails_explicitly(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_function_tool(compliant=False)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-ADAPTER-0001" for d in result.diagnostics)


def test_lower_function_and_built_in_tools_are_never_flattened_into_one_field(diagnostic_factory):
    """Scope item 4: the built-in-vs-function tool distinction must be
    explicit in the artifact, not collapsed into a single generic 'tools'
    field."""
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_function_tool(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert "tools" not in payload
    assert "function_tools" in payload and "built_in_tools" in payload
    assert len(payload["function_tools"]) == 1
    assert payload["built_in_tools"] == []


def test_lower_required_built_in_tool_capability_fails_explicitly(diagnostic_factory):
    """tools.server_executed@1 is a genuine required-capability gap (the
    frozen IR cannot express a Gemini built-in/grounding tool), not a
    synthetic nonexistent-capability test."""
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_built_in_tool(required=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-CAPABILITY-0001" for d in result.diagnostics)


def test_lower_optional_built_in_tool_capability_does_not_block_lowering(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_built_in_tool(required=False)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["built_in_tools"] == []
    decisions = payload["capability_decisions"]
    built_in_decision = next(d for d in decisions if d["capability"] == "tools.server_executed@1")
    assert built_in_decision["requirement"] == "optional"
    assert built_in_decision["resolution"] == "unsupported"


def test_lower_thinking_not_requested_is_explicitly_absent_not_omitted(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert "thinking" in payload
    assert payload["thinking"] == {"requested": False}


def test_lower_thinking_requested_represents_signature_state_explicitly(diagnostic_factory):
    """Scope item 3/4 and the ADR-006 third-confirmation check: thinking-
    level/thought-signature state must be explicitly represented in the
    artifact, not silently dropped, even though the frozen IR has no field
    to source a concrete thinking_level value from and no multi-turn state
    field to carry a continuation signature."""
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_thinking(optional=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    thinking = payload["thinking"]
    assert thinking["requested"] is True
    assert thinking["capability_resolution"] == "conditional"
    assert thinking["thinking_level"] is None
    assert thinking["thought_signature"]["required_when_function_calling"] is True
    assert thinking["thought_signature"]["must_be_echoed_back_on_continuation"] is True


def test_lower_required_thinking_conditional_does_not_fail(diagnostic_factory):
    """conditional != unsupported, so a required-but-conditional capability
    must not trip the required-capability-gap failure path."""
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_thinking(required=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["thinking"]["requested"] is True


def test_lower_is_deterministic_across_runs(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    r1 = adapter.lower(ir, resolution)
    r2 = adapter.lower(ir, resolution)
    assert r1.artifacts[0].sha256 == r2.artifacts[0].sha256
    assert r1.artifacts[0].data == r2.artifacts[0].data


def test_lower_never_mutates_input_ir(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    snapshot = copy.deepcopy(ir)
    resolution = adapter.check_capabilities(ir)
    adapter.lower(ir, resolution)
    assert ir == snapshot


def test_lower_matches_committed_golden_fixture(diagnostic_factory, repo_root):
    adapter = GeminiAdapter(diagnostic_factory)
    ir = ir_with_gemini_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    golden_path = repo_root / "tests" / "compiler" / "fixtures" / "golden" / "gemini_adapter_structured_output.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    produced = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert produced == golden
    assert canonical_sha256(produced) == result.artifacts[0].sha256


def test_gemini_never_claims_to_be_another_adapter(diagnostic_factory):
    adapter = GeminiAdapter(diagnostic_factory)
    assert adapter.describe().to_dict()["adapter_id"] == "gemini"
    assert adapter.describe().to_dict()["provider_id"] == "gemini"
