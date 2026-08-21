"""The package vendors copies of the frozen contract schemas so an installed
wheel is self-contained. This test fails the build the moment a vendored
copy diverges from its frozen architecture/ source -- vendoring must never
become a silent fork of the frozen contract."""
from __future__ import annotations

from promptrig.compiler import paths


def test_vendored_ir_schema_matches_frozen_source(repo_root):
    frozen = repo_root / "architecture" / "compiler-contract-freeze-v0.5" / "PROMPTRIG_IR_V0_1.schema.json"
    assert paths.IR_SCHEMA_PATH.read_bytes() == frozen.read_bytes()


def test_vendored_diagnostic_contract_schema_matches_frozen_source(repo_root):
    frozen = repo_root / "architecture" / "compiler-contract-freeze-v0.5" / "DIAGNOSTIC_CONTRACT.schema.json"
    assert paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH.read_bytes() == frozen.read_bytes()


def test_vendored_diagnostic_registry_matches_frozen_source(repo_root):
    frozen = repo_root / "architecture" / "diagnostics" / "DIAGNOSTIC_CODE_REGISTRY.json"
    assert paths.DIAGNOSTIC_REGISTRY_PATH.read_bytes() == frozen.read_bytes()


def test_vendored_requirements_diagnostic_registry_matches_source(repo_root):
    frozen = (
        repo_root
        / "architecture"
        / "requirements-compiler-contract-v0.1"
        / "requirements-diagnostic-registry.json"
    )
    assert paths.REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH.read_bytes() == frozen.read_bytes()
