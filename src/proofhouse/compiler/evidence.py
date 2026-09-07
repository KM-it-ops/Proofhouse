"""Headless closed-loop evidence bundle (MISSION-012 graduation).

Graduates MISSION-010 prototype evidence identity to headless v0.1. The
``prototype_id`` key remains as a deprecated alias equal to ``loop_id`` for one
release so older readers do not break silently; new consumers should use
``loop_id`` and ``evidence_schema``.
"""
from __future__ import annotations

from typing import Any

HEADLESS_LOOP_ID = "mission-012-headless-closed-loop-v0.1"
CONTRACT_008_ACCEPTED = "0.1.0"
CONTRACT_009_ACCEPTED = "0.1.0"
EVIDENCE_BUNDLE_SCHEMA = "eeb-headless-v0.1"
DEFAULT_EVALUATOR_ID = "evr-det-compile-security-v1"
DEFAULT_EVALUATOR_VERSION = "0.1.0"
BUNDLE_ID = "EEB-CLOSED-LOOP"


def build_evidence_bundle(
    *,
    requirement_ids: list[str],
    immutable_fields: tuple[str, ...],
    adapter: dict[str, str],
    ir_sha256: str,
    baseline_digest: str,
    evaluation: dict[str, Any],
    failed_attempts: list[dict[str, Any]],
    unresolved_defect: dict[str, Any] | None,
    network_allowed: bool,
    network_used: bool,
    repair_budget: int,
    compile_status: str | None,
    evaluator_id: str = DEFAULT_EVALUATOR_ID,
    evaluator_version: str = DEFAULT_EVALUATOR_VERSION,
    intake_profile: str | None = None,
    model_proposal: dict[str, Any] | None = None,
    suggestion_profile: str | None = None,
) -> dict[str, Any]:
    """Build a graduated headless evidence bundle with stable keys."""
    bundle: dict[str, Any] = {
        "bundle_id": BUNDLE_ID,
        "loop_id": HEADLESS_LOOP_ID,
        "prototype_id": HEADLESS_LOOP_ID,
        "evidence_schema": EVIDENCE_BUNDLE_SCHEMA,
        "contract_versions": {
            "requirements": CONTRACT_008_ACCEPTED,
            "evaluation_repair": CONTRACT_009_ACCEPTED,
        },
        "requirement_ids": requirement_ids,
        "immutable_fields": list(immutable_fields),
        "adapter": adapter,
        "ir_sha256": ir_sha256,
        "baseline_digest": baseline_digest,
        "evaluation": evaluation,
        "failed_attempts": failed_attempts,
        "unresolved_defect": unresolved_defect,
        "network_allowed": network_allowed,
        "network_used": network_used,
        "repair_budget": repair_budget,
        "compile_status": compile_status,
        "evaluator": {
            "id": evaluator_id,
            "version": evaluator_version,
        },
    }
    if intake_profile is not None:
        bundle["intake_profile"] = intake_profile
    if model_proposal is not None:
        bundle["model_proposal"] = model_proposal
        bundle["suggestion_profile"] = suggestion_profile or "fake_suggester_v0"
    return bundle
