from __future__ import annotations

import copy
import json
import socket

import pytest

from promptrig.compiler.adapters.openai import ADAPTER_ID, ADAPTER_VERSION, OpenAIAdapter
from promptrig.compiler.canonical import canonical_sha256
from promptrig.compiler.contracts import CapabilityDecision

from .fixtures.ir_fixtures import (
    ir_with_openai_structured_output,
    ir_with_openai_tool,
    minimal_valid_ir,
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    """Every test in this file runs with socket construction/connection
    patched to raise -- the OpenAI adapter must never touch the network,
    including implicitly, anywhere in describe/check_capabilities/lower."""

    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted by the OpenAI adapter (must be zero-network)")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


def test_describe_is_deterministic_and_identifies_as_openai(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    d1 = adapter.describe().to_dict()
    d2 = adapter.describe().to_dict()
    assert d1 == d2
    assert d1["adapter_id"] == "openai"
    assert d1["provider_id"] == "openai"
    assert d1["adapter_id"] not in {"fake", "anthropic", "gemini"}


def test_adapter_identity_stable(diagnostic_factory):
    a1 = OpenAIAdapter(diagnostic_factory)
    a2 = OpenAIAdapter(diagnostic_factory)
    assert a1.adapter_id == a2.adapter_id == ADAPTER_ID
    assert a1.adapter_version == a2.adapter_version == ADAPTER_VERSION


def test_capability_manifest_supports_structured_json_and_function_calling(diagnostic_factory):
    manifest = OpenAIAdapter(diagnostic_factory).capability_manifest()
    assert manifest.resolve("output.structured_json@1") == "supported"
    assert manifest.resolve("tools.function_calling@1") == "supported"


def test_capability_manifest_reasoning_effort_is_conditional_not_supported(diagnostic_factory):
    manifest = OpenAIAdapter(diagnostic_factory).capability_manifest()
    assert manifest.resolve("reasoning.effort_control@1") == "conditional"


def test_capability_manifest_carries_machine_readable_limits(diagnostic_factory):
    manifest = OpenAIAdapter(diagnostic_factory).capability_manifest()
    limits = manifest.limits_for("output.structured_json@1")
    assert limits["additional_properties_must_be_false"] is True
    assert limits["all_properties_must_be_required"] is True
    assert "source" in limits


def test_check_capabilities_required_gap(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    ir["provider_requirements"] = {"required_capabilities": ["nonexistent@1"], "optional_capabilities": []}
    decisions = adapter.check_capabilities(ir)
    assert decisions[0].resolution == "unsupported"


def test_lower_fails_explicitly_on_missing_required_capability(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = (CapabilityDecision(capability="nonexistent@1", requirement="required", resolution="unsupported"),)
    result = adapter.lower(ir, resolution)
    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-CAPABILITY-0001" for d in result.diagnostics)


def test_lower_compliant_structured_output_succeeds(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    assert len(result.artifacts) == 1
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True


def test_lower_noncompliant_structured_output_fails_explicitly(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_structured_output(compliant=False)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-ADAPTER-0001" for d in result.diagnostics)


def test_lower_compliant_tool_succeeds(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_tool(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "success"
    payload = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "lookup_answer"
    assert payload["tools"][0]["function"]["strict"] is True


def test_lower_noncompliant_tool_fails_explicitly(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_tool(compliant=False)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-ADAPTER-0001" for d in result.diagnostics)


def test_lower_is_deterministic_across_runs(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    r1 = adapter.lower(ir, resolution)
    r2 = adapter.lower(ir, resolution)
    assert r1.artifacts[0].sha256 == r2.artifacts[0].sha256
    assert r1.artifacts[0].data == r2.artifacts[0].data


def test_lower_never_mutates_input_ir(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_structured_output(compliant=True)
    snapshot = copy.deepcopy(ir)
    resolution = adapter.check_capabilities(ir)
    adapter.lower(ir, resolution)
    assert ir == snapshot


def test_lower_matches_committed_golden_fixture(diagnostic_factory, repo_root):
    adapter = OpenAIAdapter(diagnostic_factory)
    ir = ir_with_openai_structured_output(compliant=True)
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    golden_path = repo_root / "tests" / "compiler" / "fixtures" / "golden" / "openai_adapter_structured_output.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    produced = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert produced == golden
    assert canonical_sha256(produced) == result.artifacts[0].sha256


def test_openai_never_claims_to_be_another_adapter(diagnostic_factory):
    adapter = OpenAIAdapter(diagnostic_factory)
    assert adapter.describe().to_dict()["adapter_id"] == "openai"
    assert adapter.describe().to_dict()["provider_id"] == "openai"
