"""Real-network live OpenAI tests. Ordinary CI does not collect this module.

Q1 is unpicked. These tests must fail-closed unless the owner supplies call-time
model, ceilings, and credential env. Do not treat collection as authorization
to call the network.
"""

from __future__ import annotations

import os

import pytest

from promptrig.compiler.execution import LiveOpenAIRequest, execute_openai

pytestmark = pytest.mark.live


def test_real_network_fail_closed_until_q1_picked() -> None:
    raw = b'{"spec_version":"0.1.0"}'
    result = execute_openai(
        raw,
        LiveOpenAIRequest(
            opt_in=os.environ.get("PROMPTRIG_LIVE") == "1",
            model=os.environ.get("PROMPTRIG_LIVE_MODEL") or None,
            credential_env_name=os.environ.get("PROMPTRIG_LIVE_CREDENTIAL_ENV") or None,
            max_output_tokens=int(os.environ["PROMPTRIG_LIVE_MAX_OUTPUT_TOKENS"])
            if os.environ.get("PROMPTRIG_LIVE_MAX_OUTPUT_TOKENS")
            else None,
            max_cost_usd=os.environ.get("PROMPTRIG_LIVE_MAX_COST_USD") or None,
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
    }
    assert "q1_unpicked" in result.envelope
