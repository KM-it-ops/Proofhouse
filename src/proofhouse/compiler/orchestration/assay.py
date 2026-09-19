"""Assay: research with a claim ledger. Offline default. No memory citations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .claim_ledger import Claim


@dataclass(frozen=True)
class AssayResult:
    status: str
    claims: tuple[Claim, ...]


def reverify(claim: Claim, fetched_text: str) -> bool:
    """Caller supplies fetched text. No network."""
    needle = claim.text.strip().lower()
    return bool(needle) and needle in fetched_text.lower()


def assay(claims: Sequence[Claim], *, rotten_fields: bool = False) -> AssayResult:
    frozen = tuple(claims)
    for claim in frozen:
        if claim.tier == "T3" and claim.drives_architecture:
            return AssayResult("BLOCKED", frozen)
        if rotten_fields and claim.freshness is None:
            return AssayResult("BLOCKED", frozen)
    return AssayResult("PASS", frozen)
