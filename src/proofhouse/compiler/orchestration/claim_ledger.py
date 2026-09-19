"""Assay claim record. In-run ledger only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Tier = Literal["T0", "T1", "T2", "T3"]
ClaimStatus = Literal["verified", "assumption", "rejected"]


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    evidence_url: str | None
    tier: Tier
    status: ClaimStatus
    freshness: str | None
    drives_architecture: bool
