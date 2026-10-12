from __future__ import annotations

import sys
from pathlib import Path

import pytest

from proofhouse.compiler import paths as compiler_paths

_COMPILER_TEST_DIR = Path(__file__).resolve().parent
if str(_COMPILER_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_COMPILER_TEST_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_CONTRACT_DIR = REPO_ROOT / "tests" / "fixtures" / "requirements-compiler-contract-v0.1"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def ir_schema_path() -> Path:
    return compiler_paths.IR_SCHEMA_PATH


@pytest.fixture(scope="session")
def diagnostic_contract_schema_path() -> Path:
    return compiler_paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH


@pytest.fixture(scope="session")
def diagnostic_registry_path() -> Path:
    return compiler_paths.DIAGNOSTIC_REGISTRY_PATH


@pytest.fixture()
def diagnostic_registry(diagnostic_registry_path):
    from proofhouse.compiler.diagnostics import DiagnosticRegistry

    return DiagnosticRegistry(diagnostic_registry_path)


@pytest.fixture()
def diagnostic_factory(diagnostic_registry, diagnostic_contract_schema_path):
    from proofhouse.compiler.diagnostics import DiagnosticFactory

    return DiagnosticFactory(diagnostic_registry, diagnostic_contract_schema_path)


# Made-up model ids the existing live-path tests send to through fake transports.
TEST_PRICED_MODELS = ("caller-supplied-unratified-model", "synthetic-model", "synthetic")


@pytest.fixture()
def priced(monkeypatch: pytest.MonkeyPatch):
    """A test price list for the made-up models the send tests use; never the shipped table.

    The spend gate refuses any model with no price, so tests that exercise what
    happens after the gate admit a request use this. Gate tests do not.
    """
    from decimal import Decimal

    from proofhouse import spend

    table = spend.PriceTable(
        version="2026-10-12.9",
        entries=tuple(
            spend.PriceEntry(
                provider="openai",
                model=model,
                input_usd_per_million_tokens=Decimal("0.01"),
                output_usd_per_million_tokens=Decimal("0.01"),
                applies_up_to_input_tokens=None,
                service_tier="default",
                source_url="https://example.com/test-prices",
                read_on="2026-10-12",
            )
            for model in TEST_PRICED_MODELS
        ),
    )
    monkeypatch.setattr(spend, "load_price_table", lambda: table)
    return table
