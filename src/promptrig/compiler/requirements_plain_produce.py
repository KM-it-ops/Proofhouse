"""MISSION-020: plain_language_v0 text → canonical MISSION-008 artifact mapping.

Does not evaluate RC-065. `compile_requirements` remains the sole rule engine.
Does not interpret freeform NLP. Parser failures stay PL-PARSE-*.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .plain_language import parse_plain_language_v0
from .requirements_contract import REQUIREMENTS_CONTRACT_VERSION

PLAIN_LANGUAGE_PROFILE = "plain_language_v0"
PLAIN_LANGUAGE_COMPILE_KEYS = frozenset({"profile", "text"})
PLAIN_PRODUCER_VAL_DIGEST = hashlib.sha256(b"promptrig-mission-020-plain-producer").hexdigest()


def is_plain_language_compile_payload(payload: object) -> bool:
    return (
        isinstance(payload, Mapping)
        and set(payload) == PLAIN_LANGUAGE_COMPILE_KEYS
        and payload.get("profile") == PLAIN_LANGUAGE_PROFILE
        and isinstance(payload.get("text"), str)
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source(*, source_id: str, fragment: str, pointer: str) -> dict[str, Any]:
    digest = _digest(fragment)
    return {
        "id": source_id,
        "kind": "ordinary_language",
        "lifecycle": "current",
        "authority_claim": "plain_language_v0 source fragment.",
        "location": {"uri": "plain-language://v0", "json_pointer": pointer},
        "fragment": fragment,
        "fragment_digest": digest,
    }


def _requirement(
    *,
    req_id: str,
    req_type: str,
    statement: str,
    source_id: str,
) -> dict[str, Any]:
    digest = _digest(statement)
    return {
        "id": req_id,
        "type": req_type,
        "statement": statement,
        "priority": "required",
        "acceptance_state": "accepted",
        "authority_basis": "directly_stated",
        "source_refs": [source_id],
        "acceptance_criteria": ["Statement matches preserved source fragment."],
        "consequential": False,
        "statement_digest": digest,
    }


def _mapping(
    *,
    map_id: str,
    requirement_id: str,
    source_id: str,
    outcome: str,
    target_pointer: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": map_id,
        "requirement_id": requirement_id,
        "outcome": outcome,
        "authority_ref": {"kind": "source", "ref": source_id},
        "validation_ref": "VAL-PL-001",
    }
    if target_pointer is not None:
        record["target_pointer"] = target_pointer
    return record


def produce_plain_language_requirements(text: str) -> dict[str, Any]:
    """Parse constrained prose and lower to canonical 008 artifacts.

    Raises PlainLanguageParseError on grammar failure.
    """
    parsed = parse_plain_language_v0(text)
    suffix = _digest(text)[:12].upper()
    input_id = f"INP-PL-{suffix}"
    document_id = f"RQD-PL-{suffix}"
    goal = str(parsed["objective"]["goal"])

    sources: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []

    sources.append(_source(source_id="SRC-PL-GOAL", fragment=goal, pointer="/text"))
    requirements.append(
        _requirement(
            req_id="REQ-PL-GOAL",
            req_type="objective",
            statement=goal,
            source_id="SRC-PL-GOAL",
        )
    )
    mappings.append(
        _mapping(
            map_id="MAP-PL-GOAL",
            requirement_id="REQ-PL-GOAL",
            source_id="SRC-PL-GOAL",
            outcome="direct",
            target_pointer="/objective/goal",
        )
    )

    for item in parsed["requirements"]:
        rid = str(item["id"])
        statement = str(item["statement"])
        token = rid.removeprefix("REQ-")
        src_id = f"SRC-{token}"
        sources.append(_source(source_id=src_id, fragment=statement, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="behavior", statement=statement, source_id=src_id)
        )
        mappings.append(
            _mapping(map_id=f"MAP-{token}", requirement_id=rid, source_id=src_id, outcome="unresolved")
        )

    constraints = list(parsed.get("behavior", {}).get("constraints") or [])
    for index, constraint in enumerate(constraints, start=1):
        rid = f"REQ-PL-C{index:03d}"
        src_id = f"SRC-PL-C{index:03d}"
        sources.append(_source(source_id=src_id, fragment=constraint, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="constraint", statement=constraint, source_id=src_id)
        )
        mappings.append(
            _mapping(
                map_id=f"MAP-PL-C{index:03d}",
                requirement_id=rid,
                source_id=src_id,
                outcome="unresolved",
            )
        )

    requirements.sort(key=lambda item: str(item.get("id") or ""))
    sources.sort(key=lambda item: str(item.get("id") or ""))
    mappings.sort(key=lambda item: str(item.get("id") or ""))

    document = {
        "contract_version": REQUIREMENTS_CONTRACT_VERSION,
        "document_id": document_id,
        "input_ref": input_id,
        "requirements": requirements,
        "sources": sources,
        "assumptions": [],
        "open_questions": [],
        "conflicts": [],
        "validations": [
            {
                "id": "VAL-PL-001",
                "validator_version": "0.1.0",
                "result": "PASS",
                "content_digest": PLAIN_PRODUCER_VAL_DIGEST,
            }
        ],
    }
    return {
        "intent_input": {
            "contract_version": REQUIREMENTS_CONTRACT_VERSION,
            "input_id": input_id,
            "authoring_mode": "simple",
            "intent": goal,
            "authoritative_inputs": ["user:intent"],
            "non_authoritative_inputs": [],
        },
        "requirements_document": document,
        "mappings": mappings,
    }
