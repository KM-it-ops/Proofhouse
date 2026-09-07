"""Deterministic fake model-assisted suggester (MISSION-014 M2).

Offline sidecar only: emits proposed / model_suggested records as evidence.
No provider SDK, HTTP client, credentials, or network on the certified path.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonicalize

FAKE_SUGGESTER_ID = "fake-suggester-v0"
FAKE_SUGGESTER_VERSION = "0.1.0"
SUGGESTION_PROFILE = "fake_suggester_v0"
PROPOSED_REQUIREMENT_ID = "REQ-MS-001"

_GATE_SELF_ACCEPT = "MAS-GATE-0001"
_GATE_INVENTED_OWNER = "MAS-GATE-0002"


def _digest(payload: Any) -> str:
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    else:
        raw = canonicalize(payload)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_fake_model_proposal(doc: dict[str, Any]) -> dict[str, Any]:
    goal = doc["objective"]["goal"]
    proposal: dict[str, Any] = {
        "id": "MAS-PROP-001",
        "producer_id": FAKE_SUGGESTER_ID,
        "producer_version": FAKE_SUGGESTER_VERSION,
        "acceptance_state": "proposed",
        "authority_basis": "model_suggested",
        "input_digest": _digest(doc),
        "proposed_records": [PROPOSED_REQUIREMENT_ID],
        "proposed_requirements": [
            {
                "id": PROPOSED_REQUIREMENT_ID,
                "statement": f"Consider documenting assumption: {goal}",
                "acceptance_state": "proposed",
                "authority_basis": "model_suggested",
            }
        ],
    }
    proposal["output_digest"] = _digest(proposal)
    return proposal


def validate_model_boundary(
    doc: dict[str, Any],
    proposal: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []

    for requirement in doc.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        if (
            requirement.get("acceptance_state") == "accepted"
            and requirement.get("authority_basis") == "model_suggested"
        ):
            errors.append(_GATE_SELF_ACCEPT)
            break

    if proposal is not None:
        if proposal.get("acceptance_state") == "accepted":
            if _GATE_SELF_ACCEPT not in errors:
                errors.append(_GATE_SELF_ACCEPT)

        if proposal.get("authority_basis") == "owner_decision":
            errors.append(_GATE_INVENTED_OWNER)

        for proposed_requirement in proposal.get("proposed_requirements", []):
            if not isinstance(proposed_requirement, dict):
                continue
            if proposed_requirement.get("authority_basis") == "owner_decision":
                if _GATE_INVENTED_OWNER not in errors:
                    errors.append(_GATE_INVENTED_OWNER)
                break
            if proposed_requirement.get("acceptance_state") == "accepted":
                if _GATE_SELF_ACCEPT not in errors:
                    errors.append(_GATE_SELF_ACCEPT)
                break

    return errors
