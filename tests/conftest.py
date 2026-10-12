"""Suite-wide guard: no test may write into the real Proofhouse home folder.

Each test gets its own temporary ``PROOFHOUSE_HOME`` (install records, backups,
model-notes cache, overseer demand records). A test that needs another value
sets or removes the variable itself.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_proofhouse_home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path_factory.mktemp("proofhouse-home")))


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
