from __future__ import annotations

import copy

import pytest

from promptrig.compiler.adapters import get_adapter
from promptrig.compiler.capability import CapabilityManifest
from promptrig.compiler.passes import (
    AdapterLoweringPass,
    CapabilityResolutionPass,
    CompilationState,
    NormalizationPass,
    OptimizationPass,
    SafetyPass,
    ValidationPass,
)
from promptrig.compiler.pipeline import PASS_ORDER, run_pipeline

from .fixtures.ir_fixtures import (
    ir_with_capabilities,
    ir_with_duplicate_requirement_ids,
    ir_with_unknown_field,
    minimal_valid_ir,
    strict_compliant_schema,
)


def _build_passes(diagnostic_factory, ir_schema_path, adapter):
    manifest = adapter.capability_manifest()
    return (
        NormalizationPass(diagnostic_factory, "test.json"),
        ValidationPass(diagnostic_factory, ir_schema_path, "test.json"),
        OptimizationPass(),
        CapabilityResolutionPass(diagnostic_factory, manifest, "test.json"),
        SafetyPass(diagnostic_factory, "test.json"),
        AdapterLoweringPass(diagnostic_factory, adapter, "test.json"),
    )


def _initial_state(document: dict) -> CompilationState:
    return CompilationState(ir_document=document, canonical_sha256="", source_document="test.json")


def test_pass_names_match_fixed_pipeline_order(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    assert tuple(p.name for p in passes) == PASS_ORDER


def test_out_of_order_passes_rejected(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    manifest = adapter.capability_manifest()
    out_of_order = (
        ValidationPass(diagnostic_factory, ir_schema_path, "test.json"),
        NormalizationPass(diagnostic_factory, "test.json"),
    )
    with pytest.raises(ValueError):
        run_pipeline(_initial_state(minimal_valid_ir()), out_of_order)


def test_successful_pipeline_produces_no_error_diagnostics_and_one_artifact(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    result = run_pipeline(_initial_state(minimal_valid_ir()), passes)

    assert not any(d.severity == "error" for d in result.diagnostics)
    assert len(result.state.artifacts) == 1
    assert [t.pass_name for t in result.trace] == list(PASS_ORDER)


def test_invalid_ir_stops_before_lowering(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    result = run_pipeline(_initial_state(ir_with_unknown_field()), passes)

    ran_passes = [t.pass_name for t in result.trace]
    assert "adapter_lowering" not in ran_passes
    assert any(d.code == "PRG-VALIDATION-0001" for d in result.diagnostics)
    assert result.state.artifacts == ()


def test_duplicate_ids_stop_before_lowering(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    result = run_pipeline(_initial_state(ir_with_duplicate_requirement_ids()), passes)

    assert any(d.code == "PRG-VALIDATION-0004" for d in result.diagnostics)
    assert "adapter_lowering" not in [t.pass_name for t in result.trace]


def test_missing_required_capability_stops_before_lowering(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    ir = ir_with_capabilities(required=["nonexistent.capability@1"])
    result = run_pipeline(_initial_state(ir), passes)

    assert any(d.code == "PRG-CAPABILITY-0001" for d in result.diagnostics)
    assert "adapter_lowering" not in [t.pass_name for t in result.trace]
    assert result.state.artifacts == ()


def test_missing_optional_capability_only_warns_and_still_lowers(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    ir = ir_with_capabilities(optional=["nonexistent.optional@1"])
    result = run_pipeline(_initial_state(ir), passes)

    assert any(d.code == "PRG-CAPABILITY-0002" and d.severity == "warning" for d in result.diagnostics)
    assert not any(d.severity == "error" for d in result.diagnostics)
    assert len(result.state.artifacts) == 1


def test_supported_required_capability_lowers_successfully(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    ir = ir_with_capabilities(required=["output.structured_json@1"])
    ir["output_contracts"] = [
        {"id": "answer", "name": "Answer", "required": True, "schema": strict_compliant_schema()}
    ]
    result = run_pipeline(_initial_state(ir), passes)

    assert not any(d.severity == "error" for d in result.diagnostics)
    assert len(result.state.artifacts) == 1


def test_pipeline_never_mutates_input_ir_document(diagnostic_factory, ir_schema_path):
    adapter = get_adapter("fake", diagnostic_factory, "test.json")
    passes = _build_passes(diagnostic_factory, ir_schema_path, adapter)
    original = minimal_valid_ir()
    snapshot = copy.deepcopy(original)

    run_pipeline(_initial_state(original), passes)

    assert original == snapshot


def test_each_pass_returns_new_state_object(diagnostic_factory, ir_schema_path):
    document = minimal_valid_ir()
    state = _initial_state(document)
    pass_ = NormalizationPass(diagnostic_factory, "test.json")
    new_state, _ = pass_.run(state)
    assert new_state is not state
    assert new_state.ir_document is state.ir_document  # unchanged reference, not a mutated copy


def test_capability_manifest_never_mutated_by_resolution(diagnostic_factory):
    manifest = CapabilityManifest(
        adapter_id="fake", adapter_version="0.1.0", manifest_version="0.1.0",
        supported=frozenset({"output.structured_json@1"}),
    )
    snapshot = frozenset(manifest.supported)
    pass_ = CapabilityResolutionPass(diagnostic_factory, manifest, "test.json")
    state = _initial_state(ir_with_capabilities(required=["output.structured_json@1"]))
    pass_.run(state)
    assert manifest.supported == snapshot
