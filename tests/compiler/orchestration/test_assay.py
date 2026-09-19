"""Assay claim ledger (T-P4-04)."""

from __future__ import annotations

from proofhouse.compiler.orchestration.assay import assay, reverify
from proofhouse.compiler.orchestration.claim_ledger import Claim


def test_t3_may_not_drive_architecture() -> None:
    claim = Claim(
        id="c1",
        text="use library X because a blog said so",
        evidence_url=None,
        tier="T3",
        status="assumption",
        freshness=None,
        drives_architecture=True,
    )
    result = assay((claim,))
    assert result.status == "BLOCKED"


def test_reverify_is_offline_and_requires_caller_text() -> None:
    claim = Claim(
        id="c2",
        text="Next.js App Router is stable",
        evidence_url="https://example.invalid/docs",
        tier="T0",
        status="verified",
        freshness="2026-09-19",
        drives_architecture=True,
    )
    assert reverify(claim, "Next.js App Router is stable in this release.") is True
    assert reverify(claim, "unrelated paragraph") is False


def test_freshness_required_on_rotten_fields() -> None:
    claim = Claim(
        id="c3",
        text="model gpt-x max_tokens=99",
        evidence_url="https://example.invalid",
        tier="T0",
        status="verified",
        freshness=None,
        drives_architecture=False,
    )
    result = assay((claim,), rotten_fields=True)
    assert result.status == "BLOCKED"
