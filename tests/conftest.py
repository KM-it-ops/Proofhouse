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


_NO_LINKS = ("not permitted in this environment", "cannot make symbolic links", "cannot create symlinks",
             "symlinks needs privileges", "cannot create a file symlink")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # noqa: ANN001, ANN201 - pytest hook
    """The link tests prove a model cannot write outside its folder. On a locked-down machine they may skip when
    it refuses to make a folder link; on CI that skip would hide a real hole, so there it is a failure."""
    import os

    outcome = yield
    report = outcome.get_result()
    if report.skipped and os.environ.get("CI") and any(mark in str(report.longrepr) for mark in _NO_LINKS):
        report.outcome = "failed"
        report.longrepr = f"a link test may not skip on CI: {report.longrepr}"
