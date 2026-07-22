"""Programmatic IR fixture builders shared across compiler tests and CLI parity fixtures.

Kept as Python (not static JSON) so every fixture is guaranteed to start
from a schema-valid baseline and mutations are explicit and reviewable.
"""
from __future__ import annotations

import copy
from typing import Any

_PLACEHOLDER_SHA256 = "a" * 64


def minimal_valid_ir() -> dict[str, Any]:
    return {
        "spec_version": "0.1.0",
        "project": {"name": "demo", "mode": "balanced", "compilation_level": "prompt"},
        "objective": {
            "goal": "Answer user questions accurately and concisely.",
            "target_users": ["general_users"],
            "success_criteria": ["accurate_answer"],
            "failure_conditions": ["hallucination"],
        },
        "requirements": [
            {
                "id": "REQ-001",
                "statement": "Responses must be in English.",
                "priority": "p0",
                "mandatory": True,
                "acceptance": ["response_language_is_english"],
            }
        ],
        "behavior": {
            "instructions": ["Be concise."],
            "constraints": ["No profanity."],
            "uncertainty_policy": "State uncertainty explicitly rather than guessing.",
            "evidence_policy": "Cite sources when available.",
        },
        "evaluation": {
            "dimensions": ["accuracy"],
            "repair_limit": 1,
            "baseline_required": False,
            "test_categories": ["smoke"],
        },
        "provenance": {"source_id": "demo-source", "source_sha256": _PLACEHOLDER_SHA256},
    }


def ir_with_unknown_field() -> dict[str, Any]:
    doc = minimal_valid_ir()
    doc["not_a_real_field"] = True
    return doc


def ir_with_repair_limit_above_two() -> dict[str, Any]:
    doc = minimal_valid_ir()
    doc["evaluation"] = copy.deepcopy(doc["evaluation"])
    doc["evaluation"]["repair_limit"] = 3
    return doc


def ir_with_duplicate_requirement_ids() -> dict[str, Any]:
    doc = minimal_valid_ir()
    doc["requirements"] = doc["requirements"] + [
        {
            "id": "REQ-001",
            "statement": "Duplicate of REQ-001.",
            "priority": "p1",
            "mandatory": False,
            "acceptance": ["placeholder"],
        }
    ]
    return doc


def ir_with_wrong_spec_version() -> dict[str, Any]:
    doc = minimal_valid_ir()
    doc["spec_version"] = "0.2.0"
    return doc


def ir_with_capabilities(*, required: list[str] | None = None, optional: list[str] | None = None) -> dict[str, Any]:
    doc = minimal_valid_ir()
    doc["provider_requirements"] = {
        "required_capabilities": required or [],
        "optional_capabilities": optional or [],
    }
    return doc
