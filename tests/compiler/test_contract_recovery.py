"""Frozen-contract recovery cases added before implementation changes.

Each case exercises a confirmed MISSION-006 defect through the public
boundary or an independently invocable compiler pass.
"""
from __future__ import annotations

import copy
import inspect
import json

import pytest

from promptrig.compiler import api
from promptrig.compiler.adapters.openai import OpenAIAdapter
from promptrig.compiler.capability import CapabilityManifest
from promptrig.compiler.canonical import CanonicalizationError, canonicalize
from promptrig.compiler.contracts import Artifact
from promptrig.compiler.passes.adapter_lowering import AdapterLoweringPass
from promptrig.compiler.passes.base import CompilationState

from .fixtures.ir_fixtures import (
    ir_with_capabilities,
    minimal_valid_ir,
    strict_compliant_schema,
)


def _raw(document: dict) -> bytes:
    return json.dumps(document).encode("utf-8")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1e-7, b"1e-7"),
        (1e-6, b"0.000001"),
        (1e20, b"100000000000000000000"),
        (1e21, b"1e+21"),
    ],
)
def test_rfc8785_number_boundaries_use_ecmascript_serialization(value: float, expected: bytes):
    assert canonicalize(value) == expected


def test_jcs_rejects_integer_outside_the_binary64_safe_domain():
    with pytest.raises(CanonicalizationError):
        canonicalize(9_007_199_254_740_993)


def test_all_populated_ir_sections_are_retained_in_artifact_provenance():
    document = minimal_valid_ir()
    document.update(
        {
            "input_contracts": [{"id": "request", "name": "Request", "required": True, "schema": strict_compliant_schema()}],
            "output_contracts": [{"id": "response", "name": "Response", "required": True, "schema": strict_compliant_schema()}],
            "knowledge": {"sources": [{"id": "guide", "kind": "inline", "required": True}]},
            "memory": {"mode": "session", "retention": "one_day", "sensitive_data_allowed": False},
            "tools": [{"id": "lookup", "description": "Lookup", "input_schema": strict_compliant_schema(), "output_schema": strict_compliant_schema(), "side_effecting": False, "approval": "always"}],
            "workflow": {"steps": [{"id": "answer", "action": "answer", "on_failure": "stop"}]},
            "autonomy": {"approval_policy": "human_approval", "max_tool_calls": 1, "stop_conditions": ["uncertain"]},
            "security": {"rules": ["no credentials"]},
            "privacy": {"rules": ["minimize data"]},
            "provider_requirements": {"required_capabilities": [], "optional_capabilities": []},
            "deployment": {"targets": ["offline"]},
            "assumptions": ["input is English"],
            "open_questions": ["none"],
        }
    )

    envelope = api.compile(_raw(document), adapter_id="fake")
    assert envelope.status == "success"
    coverage = envelope.data["artifacts"][0]["provenance"]["semantic_coverage"]
    assert {"/requirements", "/tools", "/privacy", "/provenance"}.issubset(coverage)


def test_multiple_required_output_contracts_fail_closed_not_index_truncated():
    document = ir_with_capabilities(required=["output.structured_json@1"])
    document["output_contracts"] = [
        {"id": "first", "name": "First", "required": True, "schema": strict_compliant_schema()},
        {"id": "second", "name": "Second", "required": True, "schema": strict_compliant_schema()},
    ]
    envelope = api.compile(_raw(document), adapter_id="openai")
    assert envelope.status == "error"
    assert envelope.data["artifacts"] == []


def test_declared_tools_without_capability_declaration_fail_closed():
    document = minimal_valid_ir()
    document["tools"] = [
        {"id": "lookup", "description": "Lookup", "input_schema": strict_compliant_schema(), "side_effecting": False, "approval": "always"}
    ]
    envelope = api.compile(_raw(document), adapter_id="openai")
    assert envelope.status == "error"


def test_required_unresolved_conditional_capability_is_an_error():
    document = ir_with_capabilities(required=["reasoning.effort_control@1"])
    envelope = api.compile(_raw(document), adapter_id="openai")
    assert envelope.status == "error"


def test_partial_lowering_stops_the_pipeline_and_cannot_be_deployable():
    class PartialAdapter:
        adapter_id = "partial"

        def lower(self, validated_ir, resolution):
            from promptrig.compiler.adapters.base import LoweringResult

            artifact = Artifact(name="partial", media_type="application/json", sha256="a" * 64, data=b"{}")
            return LoweringResult(artifacts=(artifact,), diagnostics=(), status="partial")

    state = CompilationState(ir_document=minimal_valid_ir(), canonical_sha256="a" * 64, source_document="test")
    next_state, diagnostics = AdapterLoweringPass(api._diagnostic_factory(), PartialAdapter(), "test").run(state)
    assert diagnostics == ()
    assert next_state.stopped is True
    assert next_state.artifacts == ()


def test_public_compile_boundary_requires_an_exact_adapter_version():
    assert "adapter_version" in inspect.signature(api.compile).parameters


def test_each_artifact_has_complete_machine_readable_provenance():
    envelope = api.compile(_raw(minimal_valid_ir()), adapter_id="fake")
    artifact = envelope.data["artifacts"][0]
    provenance = artifact["provenance"]
    assert set(provenance) >= {
        "source_ir_paths",
        "ir_sha256",
        "compiler_id",
        "compiler_version",
        "adapter_id",
        "adapter_version",
        "capability_manifest_version",
        "capability_manifest_digest",
        "capability_decisions",
        "deployable",
    }


def test_manifest_digest_changes_when_machine_readable_limits_change(monkeypatch):
    baseline = OpenAIAdapter(api._diagnostic_factory()).describe().capability_manifest_digest
    original = OpenAIAdapter.capability_manifest

    def altered_manifest(self):
        manifest = original(self)
        limits = copy.deepcopy(manifest.limits)
        limits["output.structured_json@1"]["all_properties_must_be_required"] = False
        return CapabilityManifest(
            adapter_id=manifest.adapter_id,
            adapter_version=manifest.adapter_version,
            manifest_version=manifest.manifest_version,
            supported=manifest.supported,
            conditional=manifest.conditional,
            limits=limits,
        )

    monkeypatch.setattr(OpenAIAdapter, "capability_manifest", altered_manifest)
    changed = OpenAIAdapter(api._diagnostic_factory()).describe().capability_manifest_digest
    assert changed != baseline


def test_capability_manifest_nested_limits_are_immutable():
    manifest = CapabilityManifest(
        adapter_id="test",
        adapter_version="0.1.0",
        manifest_version="0.1.0",
        limits={"output.structured_json@1": {"max_depth": 5}},
    )
    with pytest.raises((TypeError, AttributeError)):
        manifest.limits["output.structured_json@1"]["max_depth"] = 6


def test_json_pointer_escapes_slash_and_tilde_in_schema_property_names():
    from promptrig.compiler.adapters.openai_schema_subset import check_strict_subset

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"a/b~c": {"type": "object", "properties": {"nested": {"type": "string"}}}},
        "required": ["a/b~c"],
    }
    pointers = [violation.json_pointer for violation in check_strict_subset(schema, base_pointer="/output_contracts/0/schema")]
    assert any("a~1b~0c" in pointer for pointer in pointers)


def test_read_only_autonomy_cannot_authorize_a_side_effecting_tool():
    document = minimal_valid_ir()
    document["autonomy"] = {"approval_policy": "read_only", "max_tool_calls": 1}
    document["tools"] = [
        {"id": "write", "description": "Write", "input_schema": strict_compliant_schema(), "side_effecting": True, "approval": "policy"}
    ]
    envelope = api.compile(_raw(document), adapter_id="fake")
    assert envelope.status == "error"
