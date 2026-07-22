from __future__ import annotations

import json

from promptrig.compiler import api
from promptrig.compiler.contracts import CompileOptions
from promptrig.compiler.sink import InMemorySink

from .fixtures.ir_fixtures import (
    ir_with_anthropic_structured_output,
    ir_with_capabilities,
    ir_with_gemini_structured_output,
    ir_with_openai_structured_output,
    ir_with_repair_limit_above_two,
    ir_with_unknown_field,
    minimal_valid_ir,
)


def _raw(doc: dict) -> bytes:
    return json.dumps(doc).encode("utf-8")


def test_validate_success():
    env = api.validate(_raw(minimal_valid_ir()))
    assert env.status == "success"
    assert env.data["valid"] is True
    assert env.diagnostics == ()


def test_validate_unknown_field_fails_with_exit_relevant_diagnostic():
    env = api.validate(_raw(ir_with_unknown_field()))
    assert env.status == "error"
    assert env.data["valid"] is False
    assert any(d.code == "PRG-VALIDATION-0001" for d in env.diagnostics)


def test_validate_repair_limit_above_two_fails():
    env = api.validate(_raw(ir_with_repair_limit_above_two()))
    assert env.status == "error"


def test_validate_malformed_json_fails_with_normalization_diagnostic():
    env = api.validate(b"{not json")
    assert env.status == "error"
    assert env.diagnostics[0].code == "PRG-NORMALIZATION-0001"


def test_inspect_success_reports_manifest():
    env = api.inspect(_raw(minimal_valid_ir()))
    assert env.status == "success"
    assert env.data["manifest"]["project_name"] == "demo"
    assert env.data["manifest"]["requirement_count"] == 1


def test_inspect_invalid_ir_reports_diagnostics_no_manifest():
    env = api.inspect(_raw(ir_with_unknown_field()))
    assert env.status == "error"
    assert "manifest" not in env.data


def test_compile_success_with_fake_adapter():
    env = api.compile(_raw(minimal_valid_ir()), adapter_id="fake")
    assert env.status == "success"
    assert env.data["adapter_id"] == "fake"
    assert len(env.data["artifacts"]) == 1
    assert env.data["artifacts"][0]["sha256"]


def test_compile_missing_required_capability_fails_explicitly():
    ir = ir_with_capabilities(required=["nonexistent.capability@1"])
    env = api.compile(_raw(ir), adapter_id="fake")
    assert env.status == "error"
    assert any(d.code == "PRG-CAPABILITY-0001" for d in env.diagnostics)
    assert env.data["artifacts"] == []


def test_compile_optional_capability_gap_only_warns():
    ir = ir_with_capabilities(optional=["nonexistent.optional@1"])
    env = api.compile(_raw(ir), adapter_id="fake")
    assert env.status == "warning"
    assert len(env.data["artifacts"]) == 1


def test_compile_success_with_openai_adapter():
    env = api.compile(_raw(ir_with_openai_structured_output(compliant=True)), adapter_id="openai")
    assert env.status == "success"
    assert env.data["adapter_id"] == "openai"
    assert len(env.data["artifacts"]) == 1


def test_compile_success_with_anthropic_adapter():
    env = api.compile(_raw(ir_with_anthropic_structured_output(compliant=True)), adapter_id="anthropic")
    assert env.status == "success"
    assert env.data["adapter_id"] == "anthropic"
    assert len(env.data["artifacts"]) == 1


def test_compile_success_with_gemini_adapter():
    env = api.compile(_raw(ir_with_gemini_structured_output(compliant=True)), adapter_id="gemini")
    assert env.status == "success"
    assert env.data["adapter_id"] == "gemini"
    assert len(env.data["artifacts"]) == 1


def test_compile_unknown_adapter_fails_explicitly_never_substitutes():
    # All four planned adapter ids (fake -> openai -> anthropic -> gemini)
    # are now registered per OAR-001-02's completed order; a genuinely
    # unknown id (never a recognized provider name) must still fail loudly
    # rather than silently substituting another adapter.
    env = api.compile(_raw(minimal_valid_ir()), adapter_id="not-a-real-provider")
    assert env.status == "error"
    assert any(d.code == "PRG-ADAPTER-0002" for d in env.diagnostics)
    assert env.data == {}


def test_compile_is_deterministic_across_repeated_runs():
    raw = _raw(minimal_valid_ir())
    env1 = api.compile(raw, adapter_id="fake")
    env2 = api.compile(raw, adapter_id="fake")
    d1 = dict(env1.data)
    d2 = dict(env2.data)
    for d in (d1, d2):
        for entry in d["pass_trace"]:
            entry.pop("duration_seconds", None)
    assert d1 == d2


def test_compile_uses_caller_supplied_sink(tmp_path):
    from promptrig.compiler.sink import DirectorySink

    sink = DirectorySink(tmp_path)
    env = api.compile(_raw(minimal_valid_ir()), adapter_id="fake", sink=sink)
    assert env.status == "success"
    artifact = env.data["artifacts"][0]
    assert artifact["path"] is not None
    assert (tmp_path / "compiled_prompt").exists()


def test_list_adapters_reports_all_four_as_registered():
    env = api.list_adapters()
    assert env.status == "success"
    ids = [a["adapter_id"] for a in env.data["adapters"]]
    assert ids == ["fake", "openai", "anthropic", "gemini"]
    assert env.data["reserved_not_implemented"] == []


def test_doctor_healthy_environment():
    env = api.doctor()
    assert env.status == "success"
    assert all(c["ok"] for c in env.data["checks"])


def test_compile_offline_option_defaults_true():
    options = CompileOptions()
    assert options.offline is True


def test_envelope_round_trips_through_json():
    env = api.validate(_raw(minimal_valid_ir()))
    encoded = json.dumps(env.to_dict())
    decoded = json.loads(encoded)
    assert decoded["contract_version"] == "0.1.0"
    assert decoded["command"] == "validate"
    assert decoded["status"] == "success"
