"""Two-pass proof audit. Offline. max_passes=2. No critique-gate copy.

A verdict needs real passes. With no pass functions supplied, no pass ran and
the result is ``UNJUDGED`` with ``passes == 0``: an audit nobody performed is
never a ``SHIP``. With real passes the rules are unchanged: a new critical
finding on pass B escalates; otherwise only minor or important findings ship.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

Severity = Literal["critical", "important", "minor"]
PassId = Literal["A", "B"]
ProofStatus = Literal["SHIP", "ESCALATE_TO_BOSS", "UNJUDGED"]

MAX_PASSES = 2


@dataclass(frozen=True)
class ProofFinding:
    severity: Severity
    failure_scenario: str
    pass_id: PassId


@dataclass(frozen=True)
class ProofResult:
    status: ProofStatus
    findings: tuple[ProofFinding, ...]
    passes: int


PassA = Callable[[str, str], tuple[ProofFinding, ...]]
PassB = Callable[[str, str, tuple[ProofFinding, ...]], tuple[ProofFinding, ...]]


def _kept(findings: tuple[ProofFinding, ...]) -> tuple[ProofFinding, ...]:
    return tuple(item for item in findings if item.failure_scenario.strip())


def run_proof(
    artifact: str,
    spec: str,
    *,
    drafting_rationale: str,
    pass_a: PassA | None,
    pass_b: PassB | None,
) -> ProofResult:
    del drafting_rationale
    if pass_a is None or pass_b is None:
        return ProofResult("UNJUDGED", (), 0)
    findings_a = _kept(pass_a(artifact, spec))
    findings_b = _kept(pass_b(artifact, spec, findings_a))
    if any(item.severity == "critical" and item.pass_id == "B" for item in findings_b):
        return ProofResult("ESCALATE_TO_BOSS", findings_a + findings_b, MAX_PASSES)
    return ProofResult("SHIP", findings_a + findings_b, MAX_PASSES)
