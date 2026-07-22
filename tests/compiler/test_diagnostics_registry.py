from __future__ import annotations

import pytest

from promptrig.compiler.diagnostics import DiagnosticRegistryError


def test_known_active_code_resolves(diagnostic_registry):
    entry = diagnostic_registry.resolve("PRG-VALIDATION-0001")
    assert entry.phase == "validation"
    assert entry.severity == "error"


def test_unregistered_code_rejected(diagnostic_registry):
    with pytest.raises(DiagnosticRegistryError):
        diagnostic_registry.resolve("PRG-NOT-REAL-9999")


def test_registry_is_immutable_status(diagnostic_registry_path):
    from promptrig.compiler.diagnostics import DiagnosticRegistry

    registry = DiagnosticRegistry(diagnostic_registry_path)
    assert registry.registry_version == "1.0.0"


def test_emit_produces_conformant_diagnostic(diagnostic_factory):
    diag = diagnostic_factory.emit(
        code="PRG-VALIDATION-0001",
        phase="validation",
        message="IR schema validation failed: missing required field",
        document="input.json",
        json_pointer="/project/name",
    )
    d = diag.to_dict()
    assert d["code"] == "PRG-VALIDATION-0001"
    assert d["severity"] == "error"
    assert d["phase"] == "validation"
    assert d["contract_version"] == "0.1.0"
    assert d["source"] == {"document": "input.json", "json_pointer": "/project/name"}


def test_emit_validates_against_diagnostic_contract_schema(diagnostic_factory, diagnostic_contract_schema_path):
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(diagnostic_contract_schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    diag = diagnostic_factory.emit(
        code="PRG-CAPABILITY-0002",
        phase="capability_resolution",
        message="optional capability unavailable",
        document="input.json",
        json_pointer="/provider_requirements/optional_capabilities/0",
    )
    validator.validate(diag.to_dict())


def test_emit_rejects_wrong_phase_for_code(diagnostic_factory):
    with pytest.raises(DiagnosticRegistryError):
        diagnostic_factory.emit(
            code="PRG-VALIDATION-0001",
            phase="safety",
            message="mismatched phase",
            document="input.json",
            json_pointer="/",
        )


def test_emit_rejects_overridden_severity(diagnostic_factory):
    with pytest.raises(DiagnosticRegistryError):
        diagnostic_factory.emit(
            code="PRG-VALIDATION-0001",
            phase="validation",
            message="attempting to downgrade severity",
            document="input.json",
            json_pointer="/",
            severity="warning",
        )


def test_emit_unregistered_code_rejected(diagnostic_factory):
    with pytest.raises(DiagnosticRegistryError):
        diagnostic_factory.emit(
            code="PRG-NOT-REAL-9999",
            phase="validation",
            message="unregistered",
            document="input.json",
            json_pointer="/",
        )


def test_retired_code_cannot_be_emitted(tmp_path, diagnostic_contract_schema_path):
    import json

    from promptrig.compiler.diagnostics import DiagnosticFactory, DiagnosticRegistry

    registry_data = {
        "registry_version": "1.0.0",
        "contract_version": "0.1.0",
        "status": "immutable",
        "codes": [],
        "retired_codes": ["PRG-VALIDATION-0099"],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_data), encoding="utf-8")
    registry = DiagnosticRegistry(path)
    factory = DiagnosticFactory(registry, diagnostic_contract_schema_path)

    with pytest.raises(DiagnosticRegistryError):
        factory.emit(
            code="PRG-VALIDATION-0099",
            phase="validation",
            message="retired code reuse attempt",
            document="input.json",
            json_pointer="/",
        )


def test_code_cannot_be_both_active_and_retired(tmp_path):
    import json

    from promptrig.compiler.diagnostics import DiagnosticRegistry

    registry_data = {
        "registry_version": "1.0.0",
        "contract_version": "0.1.0",
        "status": "immutable",
        "codes": [
            {
                "code": "PRG-VALIDATION-0001",
                "phase": "validation",
                "severity": "error",
                "summary": "x",
                "status": "active",
                "introduced": "0.1.0",
            }
        ],
        "retired_codes": ["PRG-VALIDATION-0001"],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry_data), encoding="utf-8")

    with pytest.raises(DiagnosticRegistryError):
        DiagnosticRegistry(path)


def test_fingerprint_deterministic_across_instances(diagnostic_factory):
    d1 = diagnostic_factory.emit(
        code="PRG-VALIDATION-0001", phase="validation", message="m1",
        document="input.json", json_pointer="/a",
    )
    d2 = diagnostic_factory.emit(
        code="PRG-VALIDATION-0001", phase="validation", message="different message text",
        document="input.json", json_pointer="/a",
    )
    assert d1.fingerprint == d2.fingerprint
    assert d1.id == d2.id


def test_fingerprint_differs_by_location(diagnostic_factory):
    d1 = diagnostic_factory.emit(
        code="PRG-VALIDATION-0001", phase="validation", message="m",
        document="input.json", json_pointer="/a",
    )
    d2 = diagnostic_factory.emit(
        code="PRG-VALIDATION-0001", phase="validation", message="m",
        document="input.json", json_pointer="/b",
    )
    assert d1.fingerprint != d2.fingerprint
