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
