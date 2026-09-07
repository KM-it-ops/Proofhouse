"""Real-network live OpenAI tests. Ordinary CI does not collect this module.

Q1 is unpicked. These tests must fail-closed unless the owner supplies call-time
model, ceilings, and credential env. Do not treat collection as authorization
to call the network.
"""

from __future__ import annotations

import os
import warnings

import pytest

from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai

pytestmark = pytest.mark.live

_PREFIX = "PROOFHOUSE_LIVE"
_LEGACY_PREFIX = "PROMPTRIG_LIVE"
_legacy_warned = False


def _live_env(suffix: str = "") -> str | None:
    """Read PROOFHOUSE_LIVE*, falling back to the pre-rename PROMPTRIG_LIVE* name.

    The fallback is kept for one minor version and is removable at 0.3.0. It
    warns once per process however many legacy names are set, so a run with
    several of them does not bury the notice in repeats.
    """
    global _legacy_warned
    value = os.environ.get(_PREFIX + suffix)
    if value is not None:
        return value
    legacy = os.environ.get(_LEGACY_PREFIX + suffix)
    if legacy is not None and not _legacy_warned:
        _legacy_warned = True
        warnings.warn(
            f"{_LEGACY_PREFIX}* environment variables are deprecated; "
            f"use {_PREFIX}* instead. The fallback is removable at 0.3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
    return legacy


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
    }
    assert "q1_unpicked" in result.envelope
