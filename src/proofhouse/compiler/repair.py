from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClosedLoopTestHooks:
    """Test-only. Production CLI must never instantiate this."""

    force_fail_first_compile: bool = False
    force_security_weaken_repair: bool = False
    force_self_accept_proposal: bool = False
    force_invent_owner_decision: bool = False
    force_weaken_security_via_suggestion: bool = False


@dataclass(frozen=True)
class RepairPlan:
    mutation_summary: str
    allowed: bool
    diagnostic_codes: tuple[str, ...]


def plan_repair(*, attempt_index: int, weaken_security: bool) -> RepairPlan:
    del attempt_index  # reserved for future attempt-scoped repair policies
    if weaken_security:
        return RepairPlan(
            mutation_summary="remove_security_constraint",
            allowed=False,
            diagnostic_codes=("EVR-SEC-0001",),
        )
    return RepairPlan(
        mutation_summary="tighten_instruction_wording",
        allowed=True,
        diagnostic_codes=(),
    )


def apply_instruction_repair(ir_doc: dict[str, Any], attempt_index: int) -> dict[str, Any]:
    """Return deep-copied IR with one appended repair instruction; immutables unchanged."""
    out: dict[str, Any] = json.loads(json.dumps(ir_doc))
    instructions = list(out["behavior"]["instructions"])
    instructions.append(f"Repair pass {attempt_index}: restate requirements without changing meaning.")
    out["behavior"]["instructions"] = instructions
    return out
