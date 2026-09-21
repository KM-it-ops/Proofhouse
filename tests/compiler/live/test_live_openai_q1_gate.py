"""Real-network live OpenAI tests. Ordinary CI does not collect this module.

Q1 is gpt-5.6-luna (OAR-032). These tests still fail-closed unless the owner
supplies call-time model, ceilings, and credential env. The stub IR in this
module must not call the network. Do not treat collection as a CI live job.
"""

from __future__ import annotations

import os
import pytest

from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai

pytestmark = pytest.mark.live

_PREFIX = "PROOFHOUSE_LIVE"


def _live_env(suffix: str = "") -> str | None:
    """Read the Proofhouse live-test environment namespace."""
    return os.environ.get(_PREFIX + suffix)


def test_real_network_fail_closed_until_q1_picked() -> None:
    raw = b'{"spec_version":"0.1.0"}'
    result = execute_openai(
        raw,
        LiveOpenAIRequest(
            opt_in=_live_env() == "1",
            model=_live_env("_MODEL") or None,
            credential_env_name=_live_env("_CREDENTIAL_ENV") or None,
            max_output_tokens=int(_live_env("_MAX_OUTPUT_TOKENS"))
            if _live_env("_MAX_OUTPUT_TOKENS")
            else None,
            max_cost_usd=_live_env("_MAX_COST_USD") or None,
        ),
    )
    assert result.status == "error"
    assert result.diagnostics[0] in {
        "EXE-OPT-0001",
        "EXE-CRED-0001",
        "EXE-MODEL-0001",
        "EXE-CEIL-0001",
        "EXE-COMPILE-0001",
        "EXE-DEP-0001",
        "EXE-HTTP-0001",
    }
    assert "q1_unpicked" in result.envelope
    assert result.envelope.get("q1_unpicked") is False
    assert result.envelope.get("q1_model") == "gpt-5.6-luna"
