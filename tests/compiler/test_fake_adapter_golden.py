from __future__ import annotations

import json

from promptrig.compiler.adapters.fake import ADAPTER_ID, ADAPTER_VERSION, FakeAdapter
from promptrig.compiler.canonical import canonical_sha256

from .fixtures.ir_fixtures import minimal_valid_ir

GOLDEN_PATH = None  # set in fixture


def test_describe_is_deterministic_and_never_claims_a_live_provider(diagnostic_factory):
    adapter = FakeAdapter(diagnostic_factory)
    d1 = adapter.describe().to_dict()
    d2 = adapter.describe().to_dict()
    assert d1 == d2
    assert d1["adapter_id"] == "fake"
    assert d1["provider_id"] == "fake"
    assert d1["adapter_id"] not in {"openai", "anthropic", "gemini"}


def test_check_capabilities_deterministic(diagnostic_factory):
    adapter = FakeAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    ir["provider_requirements"] = {
        "required_capabilities": ["output.structured_json@1"],
        "optional_capabilities": ["tools.function_calling@1", "unsupported.thing@1"],
    }
    d1 = tuple(c.to_dict() for c in adapter.check_capabilities(ir))
    d2 = tuple(c.to_dict() for c in adapter.check_capabilities(ir))
    assert d1 == d2
    resolutions = {c["capability"]: c["resolution"] for c in d1}
    assert resolutions["output.structured_json@1"] == "supported"
    assert resolutions["tools.function_calling@1"] == "supported"
    assert resolutions["unsupported.thing@1"] == "unsupported"


def test_lower_produces_deterministic_artifact_digest(diagnostic_factory):
    adapter = FakeAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = adapter.check_capabilities(ir)
    result_a = adapter.lower(ir, resolution)
    result_b = adapter.lower(ir, resolution)

    assert result_a.status == result_b.status == "success"
    assert result_a.artifacts[0].sha256 == result_b.artifacts[0].sha256
    assert result_a.artifacts[0].data == result_b.artifacts[0].data


def test_lower_matches_committed_golden_fixture(diagnostic_factory, repo_root):
    adapter = FakeAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = adapter.check_capabilities(ir)
    result = adapter.lower(ir, resolution)

    golden_path = repo_root / "tests" / "compiler" / "fixtures" / "golden" / "fake_adapter_minimal_ir.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    produced = json.loads(result.artifacts[0].data.decode("utf-8"))
    assert produced == golden
    assert canonical_sha256(produced) == result.artifacts[0].sha256


def test_lower_fails_explicitly_on_missing_required_capability(diagnostic_factory):
    from promptrig.compiler.contracts import CapabilityDecision

    adapter = FakeAdapter(diagnostic_factory)
    ir = minimal_valid_ir()
    resolution = (
        CapabilityDecision(capability="nonexistent@1", requirement="required", resolution="unsupported"),
    )
    result = adapter.lower(ir, resolution)
    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d.code == "PRG-CAPABILITY-0001" for d in result.diagnostics)


def test_adapter_identity_is_stable_across_instances(diagnostic_factory):
    a1 = FakeAdapter(diagnostic_factory)
    a2 = FakeAdapter(diagnostic_factory)
    assert a1.adapter_id == a2.adapter_id == ADAPTER_ID
    assert a1.adapter_version == a2.adapter_version == ADAPTER_VERSION
