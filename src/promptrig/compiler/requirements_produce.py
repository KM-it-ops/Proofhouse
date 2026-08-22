"""MISSION-017: file/api envelope → canonical MISSION-008 artifact mapping.

Does not evaluate RC-065. `compile_requirements` remains the sole rule engine.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from .requirements_contract import REQUIREMENTS_CONTRACT_VERSION

ALLOWED_ENVELOPE_KEYS = frozenset(
    {"intent_input", "sources", "claims", "mappings", "imports", "diagnostics"}
)
ALLOWED_INTENT_KEYS = frozenset(
    {
        "contract_version",
        "input_id",
        "authoring_mode",
        "intent",
        "authoritative_inputs",
        "non_authoritative_inputs",
        "source_ids",
    }
)
REQUIRED_INTENT_KEYS = frozenset(
    {
        "contract_version",
        "input_id",
        "authoring_mode",
        "intent",
        "authoritative_inputs",
        "non_authoritative_inputs",
    }
)
MODE_SOURCE_KINDS = {
    "file": frozenset({"file", "decision", "contract"}),
    "api": frozenset({"api_request", "decision", "contract"}),
    "simple": frozenset({"ordinary_language", "decision", "contract"}),
    "developer": frozenset({"developer_config", "decision", "contract"}),
}
PRODUCER_VAL_DIGEST = hashlib.sha256(b"promptrig-mission-017-producer").hexdigest()
INPUT_ID_PATTERN = re.compile(r"^INP-[A-Z0-9-]+$")


def produce_requirements(envelope: Mapping[str, Any] | object) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        return {}
    if set(envelope) - ALLOWED_ENVELOPE_KEYS:
        return {}
    intent = envelope.get("intent_input")
    if not isinstance(intent, Mapping):
        return {}
    if set(intent) - ALLOWED_INTENT_KEYS or not REQUIRED_INTENT_KEYS <= set(intent):
        return {}
    mode = intent.get("authoring_mode")
    if mode not in MODE_SOURCE_KINDS:
        return {}
    if intent.get("contract_version") != REQUIREMENTS_CONTRACT_VERSION:
        return {}
    input_id = intent.get("input_id")
    if not isinstance(input_id, str) or not INPUT_ID_PATTERN.fullmatch(input_id):
        return {}
    sources = envelope.get("sources")
    claims = envelope.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list) or not sources or not claims:
        return {}
    if any(not isinstance(item, Mapping) for item in sources + claims):
        return {}
    if any(
        isinstance(source, Mapping) and source.get("fragment") and not source.get("fragment_digest")
        for source in sources
    ):
        return {}
    allowed_kinds = MODE_SOURCE_KINDS[mode]
    if any(source.get("kind") not in allowed_kinds for source in sources):
        return {}
    imports = envelope.get("imports")
    if imports is not None:
        if mode != "file" or not isinstance(imports, list) or not all(isinstance(item, str) for item in imports):
            return {}

    source_by_id = {source.get("id"): source for source in sources}
    produced_claims: list[dict[str, Any]] = []
    open_questions: list[dict[str, Any]] = []
    for claim in claims:
        produced = dict(claim)
        if (
            produced.get("acceptance_state") == "accepted"
            and produced.get("authority_basis") == "directly_stated"
        ):
            ambiguous = False
            for ref in produced.get("source_refs") or []:
                source = source_by_id.get(ref)
                if not isinstance(source, Mapping) or source.get("kind") != "file":
                    continue
                if not source.get("sha256") and not source.get("fragment_digest"):
                    ambiguous = True
                    break
            if ambiguous:
                produced["acceptance_state"] = "unresolved"
                rid = str(produced.get("id") or "REQ-UNKNOWN")
                open_questions.append(
                    {
                        "id": f"OQN-{rid}",
                        "text": "OQ-008-001 unanswered: file fragment without digest; fail closed.",
                        "affected_requirement_refs": [rid],
                        "impact": "required",
                        "resolution_state": "unresolved",
                    }
                )
        produced_claims.append(produced)

    first_source_id = str(sources[0].get("id") or "")
    if imports:
        for index, path in enumerate(imports, start=1):
            produced_claims.append(
                {
                    "id": f"REQ-IMP-{index:03d}",
                    "type": "behavior",
                    "statement": path,
                    "priority": "required",
                    "acceptance_state": "unsupported",
                    "authority_basis": "unsupported",
                    "source_refs": [first_source_id],
                    "acceptance_criteria": ["Import is unsupported."],
                    "consequential": False,
                }
            )

    produced_claims.sort(key=lambda item: str(item.get("id") or ""))
    sorted_sources = sorted(sources, key=lambda item: str(item.get("id") or ""))
    document_id = "RQD-" + input_id.removeprefix("INP-")

    document: dict[str, Any] = {
        "contract_version": REQUIREMENTS_CONTRACT_VERSION,
        "document_id": document_id,
        "input_ref": input_id,
        "requirements": produced_claims,
        "sources": sorted_sources,
        "assumptions": [],
        "open_questions": open_questions,
        "conflicts": [],
        "validations": [
            {
                "id": "VAL-PROD-001",
                "validator_version": "0.1.0",
                "result": "PASS",
                "content_digest": PRODUCER_VAL_DIGEST,
            }
        ],
    }

    mappings = envelope.get("mappings")
    if not isinstance(mappings, list):
        mappings = []
        for claim in produced_claims:
            refs = claim.get("source_refs") or [first_source_id]
            rid = str(claim.get("id") or "")
            mappings.append(
                {
                    "id": f"MAP-{rid.removeprefix('REQ-')}",
                    "requirement_id": rid,
                    "outcome": "unresolved",
                    "authority_ref": {"kind": "source", "ref": str(refs[0])},
                    "validation_ref": "VAL-PROD-001",
                }
            )

    artifacts: dict[str, Any] = {
        "intent_input": dict(intent),
        "requirements_document": document,
        "mappings": mappings,
    }
    if "diagnostics" in envelope:
        artifacts["diagnostics"] = envelope["diagnostics"]
    return artifacts
