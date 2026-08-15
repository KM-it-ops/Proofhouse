from __future__ import annotations

import sys
from pathlib import Path

import pytest

_COMPILER_TEST_DIR = Path(__file__).resolve().parent
if str(_COMPILER_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_COMPILER_TEST_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO_ROOT / "architecture" / "compiler-contract-freeze-v0.5"
DIAGNOSTICS_DIR = REPO_ROOT / "architecture" / "diagnostics"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def ir_schema_path() -> Path:
    return CONTRACT_DIR / "PROMPTRIG_IR_V0_1.schema.json"


@pytest.fixture(scope="session")
def diagnostic_contract_schema_path() -> Path:
    return CONTRACT_DIR / "DIAGNOSTIC_CONTRACT.schema.json"


@pytest.fixture(scope="session")
def diagnostic_registry_path() -> Path:
    return DIAGNOSTICS_DIR / "DIAGNOSTIC_CODE_REGISTRY.json"


@pytest.fixture()
def diagnostic_registry(diagnostic_registry_path):
    from promptrig.compiler.diagnostics import DiagnosticRegistry

    return DiagnosticRegistry(diagnostic_registry_path)


@pytest.fixture()
def diagnostic_factory(diagnostic_registry, diagnostic_contract_schema_path):
    from promptrig.compiler.diagnostics import DiagnosticFactory

    return DiagnosticFactory(diagnostic_registry, diagnostic_contract_schema_path)
