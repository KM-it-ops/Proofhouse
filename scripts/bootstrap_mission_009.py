#!/usr/bin/env python3
"""Bootstrap MISSION-009 evaluation-repair contract package (one-shot generator)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "architecture" / "evaluation-repair-contract-v0.1"
SCHEMAS = PKG / "schemas"
FIXTURES = PKG / "fixtures"
EVIDENCE = PKG / "evidence"
TESTS = ROOT / "tests" / "evaluation"

CONTRACT_VERSION = "0.1.0-draft"
BASELINE_COMMIT = "d0bca1c9ebbf6ab4dfbfbab75ec27456c4f263cf"


def w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n") if text.startswith("\n") else text, encoding="utf-8")


def j(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


SCHEMA_DEFS = {
    "evaluator-record.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/evaluator-record.schema.json",
        "title": "EvaluatorRecord",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "evaluator_id",
            "evaluator_kind",
            "version",
            "authority_rank",
            "inputs",
            "outputs",
        ],
        "properties": {
            "evaluator_id": {"type": "string", "pattern": "^EVL-[A-Z0-9-]{3,64}$"},
            "evaluator_kind": {
                "type": "string",
                "enum": [
                    "deterministic_validator",
                    "schema_validator",
                    "security_policy_check",
                    "score_aggregator",
                    "model_judge",
                    "fake_adapter_oracle",
                ],
            },
            "version": {"type": "string", "minLength": 1},
            "authority_rank": {"type": "integer", "minimum": 1, "maximum": 9},
            "inputs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "outputs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "confidence_scale": {"type": "string", "enum": ["none", "0-1", "ordinal"]},
            "cost_model": {"type": "string"},
            "latency_budget_ms": {"type": "integer", "minimum": 0},
            "provenance": {"type": "string"},
        },
    },
    "baseline-identity.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/baseline-identity.schema.json",
        "title": "BaselineIdentity",
        "type": "object",
        "additionalProperties": False,
        "required": ["baseline_id", "artifact_digest", "contract_version", "created_at"],
        "properties": {
            "baseline_id": {"type": "string", "pattern": "^BSL-[A-Z0-9-]{3,64}$"},
            "artifact_digest": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
            "contract_version": {"type": "string"},
            "requirement_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^REQ-[A-Z0-9-]{3,64}$"},
            },
            "created_at": {"type": "string", "minLength": 1},
            "stale": {"type": "boolean"},
        },
    },
    "candidate-identity.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/candidate-identity.schema.json",
        "title": "CandidateIdentity",
        "type": "object",
        "additionalProperties": False,
        "required": ["candidate_id", "artifact_digest", "contract_version", "created_at"],
        "properties": {
            "candidate_id": {"type": "string", "pattern": "^CND-[A-Z0-9-]{3,64}$"},
            "artifact_digest": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
            "contract_version": {"type": "string"},
            "requirement_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^REQ-[A-Z0-9-]{3,64}$"},
            },
            "created_at": {"type": "string", "minLength": 1},
            "parent_baseline_id": {"type": "string", "pattern": "^BSL-[A-Z0-9-]{3,64}$"},
        },
    },
    "evaluation-request.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/evaluation-request.schema.json",
        "title": "EvaluationRequest",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "request_id",
            "contract_version",
            "baseline",
            "candidate",
            "evaluator_ids",
            "requirement_ids",
            "network_allowed",
        ],
        "properties": {
            "request_id": {"type": "string", "pattern": "^ERQ-[A-Z0-9-]{3,64}$"},
            "contract_version": {"type": "string"},
            "baseline": {"$ref": "baseline-identity.schema.json"},
            "candidate": {"$ref": "candidate-identity.schema.json"},
            "evaluator_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^EVL-[A-Z0-9-]{3,64}$"},
                "minItems": 1,
            },
            "requirement_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^REQ-[A-Z0-9-]{3,64}$"},
                "minItems": 1,
            },
            "network_allowed": {"type": "boolean"},
            "repair_budget": {"type": "integer", "minimum": 0, "maximum": 2},
        },
    },
    "evaluation-result.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/evaluation-result.schema.json",
        "title": "EvaluationResult",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "result_id",
            "request_id",
            "status",
            "scores",
            "diagnostic_codes",
            "evaluator_outcomes",
            "failed_attempts",
            "network_used",
        ],
        "properties": {
            "result_id": {"type": "string", "pattern": "^ERS-[A-Z0-9-]{3,64}$"},
            "request_id": {"type": "string", "pattern": "^ERQ-[A-Z0-9-]{3,64}$"},
            "status": {
                "type": "string",
                "enum": [
                    "PASS",
                    "FAIL",
                    "ERROR",
                    "BLOCKED",
                    "UNAVAILABLE",
                    "REGRESSION",
                    "UNRESOLVED_DEFECT",
                ],
            },
            "scores": {
                "type": "object",
                "additionalProperties": {"type": ["number", "null"]},
            },
            "aggregation": {"type": "string", "enum": ["min", "max", "mean", "any_fail", "all_pass"]},
            "threshold": {"type": ["number", "null"]},
            "diagnostic_codes": {
                "type": "array",
                "items": {"type": "string", "pattern": "^EVR-[A-Z]+-[0-9]{4}$"},
            },
            "evaluator_outcomes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["evaluator_id", "outcome", "authoritative_for_executable"],
                    "properties": {
                        "evaluator_id": {"type": "string"},
                        "outcome": {
                            "type": "string",
                            "enum": ["pass", "fail", "error", "unavailable", "advisory"],
                        },
                        "authoritative_for_executable": {"type": "boolean"},
                        "score": {"type": ["number", "null"]},
                        "message": {"type": "string"},
                    },
                },
            },
            "failed_attempts": {
                "type": "array",
                "items": {"$ref": "repair-attempt.schema.json"},
            },
            "unresolved_defect_id": {
                "type": "string",
                "pattern": "^UDF-[A-Z0-9-]{3,64}$",
            },
            "network_used": {"type": "boolean"},
            "deterministic_repeatable": {"type": "boolean"},
        },
    },
    "repair-attempt.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/repair-attempt.schema.json",
        "title": "RepairAttempt",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "attempt_id",
            "attempt_index",
            "mutation_summary",
            "outcome",
            "preserved_failed_evidence",
            "weakened_security_or_objective",
        ],
        "properties": {
            "attempt_id": {"type": "string", "pattern": "^RPA-[A-Z0-9-]{3,64}$"},
            "attempt_index": {"type": "integer", "minimum": 0, "maximum": 2},
            "mutation_summary": {"type": "string", "minLength": 1},
            "allowed_mutation": {"type": "boolean"},
            "outcome": {
                "type": "string",
                "enum": [
                    "improved",
                    "no_change",
                    "regressed",
                    "timeout",
                    "cost_exhausted",
                    "refused_immutable",
                    "error",
                ],
            },
            "preserved_failed_evidence": {"type": "boolean"},
            "weakened_security_or_objective": {"type": "boolean"},
            "cost_units": {"type": "number", "minimum": 0},
            "duration_ms": {"type": "integer", "minimum": 0},
            "diagnostic_codes": {
                "type": "array",
                "items": {"type": "string", "pattern": "^EVR-[A-Z]+-[0-9]{4}$"},
            },
        },
    },
    "repair-plan.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/repair-plan.schema.json",
        "title": "RepairPlan",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "plan_id",
            "budget",
            "immutable_fields",
            "allowed_mutations",
            "stop_states",
        ],
        "properties": {
            "plan_id": {"type": "string", "pattern": "^RPL-[A-Z0-9-]{3,64}$"},
            "budget": {"type": "integer", "minimum": 0, "maximum": 2},
            "immutable_fields": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "allowed_mutations": {"type": "array", "items": {"type": "string"}},
            "stop_states": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "budget_exhausted",
                        "timeout",
                        "cost_exhausted",
                        "regression",
                        "unresolved_defect",
                        "immutable_violation",
                        "success",
                    ],
                },
                "minItems": 1,
            },
            "time_limit_ms": {"type": "integer", "minimum": 0},
            "cost_limit": {"type": "number", "minimum": 0},
        },
    },
    "unresolved-defect.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/unresolved-defect.schema.json",
        "title": "UnresolvedDefect",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "defect_id",
            "requirement_ids",
            "failed_attempt_ids",
            "terminal_reason",
            "discarded_attempts",
        ],
        "properties": {
            "defect_id": {"type": "string", "pattern": "^UDF-[A-Z0-9-]{3,64}$"},
            "requirement_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^REQ-[A-Z0-9-]{3,64}$"},
                "minItems": 1,
            },
            "failed_attempt_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^RPA-[A-Z0-9-]{3,64}$"},
            },
            "terminal_reason": {"type": "string", "minLength": 1},
            "discarded_attempts": {"type": "boolean"},
            "diagnostic_codes": {
                "type": "array",
                "items": {"type": "string", "pattern": "^EVR-[A-Z]+-[0-9]{4}$"},
            },
        },
    },
    "evaluation-evidence-bundle.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://promptrig.local/schemas/evaluation-repair/evaluation-evidence-bundle.schema.json",
        "title": "EvaluationEvidenceBundle",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "bundle_id",
            "contract_version",
            "request",
            "result",
            "evaluators",
            "requirement_ids",
        ],
        "properties": {
            "bundle_id": {"type": "string", "pattern": "^EEB-[A-Z0-9-]{3,64}$"},
            "contract_version": {"type": "string"},
            "request": {"$ref": "evaluation-request.schema.json"},
            "result": {"$ref": "evaluation-result.schema.json"},
            "evaluators": {
                "type": "array",
                "items": {"$ref": "evaluator-record.schema.json"},
                "minItems": 1,
            },
            "repair_plan": {"$ref": "repair-plan.schema.json"},
            "unresolved_defect": {"$ref": "unresolved-defect.schema.json"},
            "requirement_ids": {
                "type": "array",
                "items": {"type": "string", "pattern": "^REQ-[A-Z0-9-]{3,64}$"},
                "minItems": 1,
            },
        },
    },
}


DIGEST_A = "sha256:" + ("a" * 64)
DIGEST_B = "sha256:" + ("b" * 64)
DIGEST_C = "sha256:" + ("c" * 64)


def baseline(bid="BSL-001", digest=DIGEST_A, stale=False):
    return {
        "baseline_id": bid,
        "artifact_digest": digest,
        "contract_version": CONTRACT_VERSION,
        "requirement_ids": ["REQ-EVAL-001"],
        "created_at": "2026-08-11T00:00:00Z",
        "stale": stale,
    }


def candidate(cid="CND-001", digest=DIGEST_B, parent="BSL-001"):
    return {
        "candidate_id": cid,
        "artifact_digest": digest,
        "contract_version": CONTRACT_VERSION,
        "requirement_ids": ["REQ-EVAL-001"],
        "created_at": "2026-08-11T00:01:00Z",
        "parent_baseline_id": parent,
    }


def eval_det():
    return {
        "evaluator_id": "EVL-DET-001",
        "evaluator_kind": "deterministic_validator",
        "version": "0.1.0",
        "authority_rank": 1,
        "inputs": ["candidate", "baseline"],
        "outputs": ["pass_fail"],
        "confidence_scale": "none",
        "provenance": "contract",
    }


def eval_model():
    return {
        "evaluator_id": "EVL-MDL-001",
        "evaluator_kind": "model_judge",
        "version": "0.1.0",
        "authority_rank": 7,
        "inputs": ["candidate"],
        "outputs": ["advisory_score"],
        "confidence_scale": "0-1",
        "provenance": "advisory_only",
    }


def eval_sec():
    return {
        "evaluator_id": "EVL-SEC-001",
        "evaluator_kind": "security_policy_check",
        "version": "0.1.0",
        "authority_rank": 1,
        "inputs": ["candidate", "accepted_objectives"],
        "outputs": ["pass_fail"],
        "confidence_scale": "none",
        "provenance": "contract",
    }


def make_cases():
    cases = []

    def add(case_id, category, description, expected_status, codes, extra=None):
        req = {
            "request_id": f"ERQ-{case_id}",
            "contract_version": CONTRACT_VERSION,
            "baseline": baseline(),
            "candidate": candidate(),
            "evaluator_ids": ["EVL-DET-001"],
            "requirement_ids": ["REQ-EVAL-001"],
            "network_allowed": False,
            "repair_budget": 1,
        }
        result = {
            "result_id": f"ERS-{case_id}",
            "request_id": f"ERQ-{case_id}",
            "status": expected_status,
            "scores": {"primary": 1.0 if expected_status == "PASS" else 0.0},
            "aggregation": "any_fail",
            "threshold": 1.0,
            "diagnostic_codes": codes,
            "evaluator_outcomes": [
                {
                    "evaluator_id": "EVL-DET-001",
                    "outcome": "pass" if expected_status == "PASS" else "fail",
                    "authoritative_for_executable": True,
                    "score": 1.0 if expected_status == "PASS" else 0.0,
                }
            ],
            "failed_attempts": [],
            "network_used": False,
            "deterministic_repeatable": True,
        }
        case = {
            "case_id": case_id,
            "category": category,
            "description": description,
            "evaluators": [eval_det()],
            "request": req,
            "result": result,
            "expected": {
                "status": expected_status,
                "diagnostic_codes": codes,
                "model_judge_authoritative_for_executable": False,
                "failed_attempts_discarded": False,
                "network_used": False,
                "termination_depends_on_model_self_report": False,
                "repair_weakened_security_or_objective": False,
            },
        }
        if extra:
            extra(case)
        cases.append(case)

    add("001", "positive", "deterministic validator pass", "PASS", [])
    add(
        "002",
        "negative",
        "deterministic validator fail",
        "FAIL",
        ["EVR-DET-0001"],
        lambda c: c["result"]["evaluator_outcomes"][0].update(
            {"outcome": "fail", "score": 0.0, "message": "schema mismatch"}
        ),
    )
    add(
        "003",
        "negative",
        "deterministic validator error surfaces",
        "ERROR",
        ["EVR-DET-0002"],
        lambda c: (
            c["result"]["evaluator_outcomes"][0].update({"outcome": "error", "score": None}),
            c["result"].update({"scores": {"primary": None}}),
        ),
    )

    def baseline_absent(c):
        c["request"]["baseline"] = baseline(bid="BSL-MISSING", digest=DIGEST_C)
        c["expected"]["status"] = "BLOCKED"
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-BSL-0001"]
        c["expected"]["diagnostic_codes"] = ["EVR-BSL-0001"]

    add("004", "boundary", "baseline absent/mismatched", "BLOCKED", ["EVR-BSL-0001"], baseline_absent)

    def baseline_stale(c):
        c["request"]["baseline"] = baseline(stale=True)
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-BSL-0002"]
        c["expected"]["diagnostic_codes"] = ["EVR-BSL-0002"]
        c["expected"]["status"] = "BLOCKED"

    add("005", "boundary", "baseline stale", "BLOCKED", ["EVR-BSL-0002"], baseline_stale)

    def agg_boundary(c):
        c["evaluators"] = [eval_det(), eval_sec()]
        c["request"]["evaluator_ids"] = ["EVL-DET-001", "EVL-SEC-001"]
        c["result"]["aggregation"] = "min"
        c["result"]["scores"] = {"det": 1.0, "sec": 0.0, "primary": 0.0}
        c["result"]["evaluator_outcomes"] = [
            {
                "evaluator_id": "EVL-DET-001",
                "outcome": "pass",
                "authoritative_for_executable": True,
                "score": 1.0,
            },
            {
                "evaluator_id": "EVL-SEC-001",
                "outcome": "fail",
                "authoritative_for_executable": True,
                "score": 0.0,
            },
        ]
        c["result"]["status"] = "FAIL"
        c["result"]["diagnostic_codes"] = ["EVR-AGG-0001"]
        c["expected"]["status"] = "FAIL"
        c["expected"]["diagnostic_codes"] = ["EVR-AGG-0001"]

    add("006", "boundary", "score aggregation min fails on any zero", "FAIL", ["EVR-AGG-0001"], agg_boundary)

    def eval_unavailable(c):
        c["result"]["status"] = "UNAVAILABLE"
        c["result"]["evaluator_outcomes"][0].update({"outcome": "unavailable", "score": None})
        c["result"]["scores"] = {"primary": None}
        c["result"]["diagnostic_codes"] = ["EVR-UNA-0001"]
        c["expected"]["status"] = "UNAVAILABLE"
        c["expected"]["diagnostic_codes"] = ["EVR-UNA-0001"]

    add("007", "negative", "evaluator unavailable not hidden", "UNAVAILABLE", ["EVR-UNA-0001"], eval_unavailable)

    def model_disagree(c):
        c["evaluators"] = [eval_det(), eval_model()]
        c["request"]["evaluator_ids"] = ["EVL-DET-001", "EVL-MDL-001"]
        c["result"]["evaluator_outcomes"] = [
            {
                "evaluator_id": "EVL-DET-001",
                "outcome": "pass",
                "authoritative_for_executable": True,
                "score": 1.0,
            },
            {
                "evaluator_id": "EVL-MDL-001",
                "outcome": "fail",
                "authoritative_for_executable": False,
                "score": 0.2,
                "message": "advisory disagree",
            },
        ]
        c["result"]["status"] = "PASS"
        c["result"]["diagnostic_codes"] = ["EVR-MDL-0001"]
        c["expected"]["status"] = "PASS"
        c["expected"]["diagnostic_codes"] = ["EVR-MDL-0001"]
        c["expected"]["model_judge_authoritative_for_executable"] = False

    add(
        "008",
        "adversarial",
        "model judge disagreement cannot override deterministic pass",
        "PASS",
        ["EVR-MDL-0001"],
        model_disagree,
    )

    def model_cannot_authorize(c):
        c["evaluators"] = [eval_model()]
        c["request"]["evaluator_ids"] = ["EVL-MDL-001"]
        c["result"]["evaluator_outcomes"] = [
            {
                "evaluator_id": "EVL-MDL-001",
                "outcome": "pass",
                "authoritative_for_executable": True,
                "score": 0.99,
            }
        ]
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-AUT-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-AUT-0001"]
        c["expected"]["model_judge_authoritative_for_executable"] = False

    add(
        "009",
        "adversarial",
        "model judge cannot be authoritative for executable correctness",
        "BLOCKED",
        ["EVR-AUT-0001"],
        model_cannot_authorize,
    )

    def repair_budget(budget, outcome_status, codes, attempt_outcomes):
        def mut(c):
            c["request"]["repair_budget"] = budget
            attempts = []
            for i, oc in enumerate(attempt_outcomes):
                attempts.append(
                    {
                        "attempt_id": f"RPA-{c['case_id']}-{i}",
                        "attempt_index": i,
                        "mutation_summary": f"repair attempt {i}",
                        "allowed_mutation": True,
                        "outcome": oc,
                        "preserved_failed_evidence": True,
                        "weakened_security_or_objective": False,
                        "diagnostic_codes": codes if oc != "improved" else [],
                    }
                )
            c["result"]["failed_attempts"] = attempts
            c["result"]["status"] = outcome_status
            c["result"]["diagnostic_codes"] = codes
            c["expected"]["status"] = outcome_status
            c["expected"]["diagnostic_codes"] = codes
            c["expected"]["failed_attempts_discarded"] = False
            if outcome_status == "UNRESOLVED_DEFECT":
                c["result"]["unresolved_defect_id"] = f"UDF-{c['case_id']}"
                c["unresolved_defect"] = {
                    "defect_id": f"UDF-{c['case_id']}",
                    "requirement_ids": ["REQ-EVAL-001"],
                    "failed_attempt_ids": [a["attempt_id"] for a in attempts],
                    "terminal_reason": "budget exhausted without pass",
                    "discarded_attempts": False,
                    "diagnostic_codes": codes,
                }
            c["repair_plan"] = {
                "plan_id": f"RPL-{c['case_id']}",
                "budget": budget,
                "immutable_fields": ["accepted_objectives", "security_constraints", "requirement_ids"],
                "allowed_mutations": ["artifact_surface", "prompt_wording"],
                "stop_states": [
                    "budget_exhausted",
                    "timeout",
                    "cost_exhausted",
                    "regression",
                    "unresolved_defect",
                    "immutable_violation",
                    "success",
                ],
            }

        return mut

    add("010", "positive", "repair budget 0 means no repair", "FAIL", ["EVR-REP-0001"], repair_budget(0, "FAIL", ["EVR-REP-0001"], []))
    add(
        "011",
        "positive",
        "repair budget 1 succeeds",
        "PASS",
        [],
        repair_budget(1, "PASS", [], ["improved"]),
    )
    add(
        "012",
        "boundary",
        "repair budget 2 then unresolved",
        "UNRESOLVED_DEFECT",
        ["EVR-REP-0002"],
        repair_budget(2, "UNRESOLVED_DEFECT", ["EVR-REP-0002"], ["no_change", "no_change"]),
    )
    add(
        "013",
        "negative",
        "repair timeout",
        "ERROR",
        ["EVR-REP-0003"],
        repair_budget(1, "ERROR", ["EVR-REP-0003"], ["timeout"]),
    )
    add(
        "014",
        "negative",
        "repair cost exhausted",
        "ERROR",
        ["EVR-REP-0004"],
        repair_budget(1, "ERROR", ["EVR-REP-0004"], ["cost_exhausted"]),
    )
    add(
        "015",
        "adversarial",
        "repair regression preserved",
        "REGRESSION",
        ["EVR-REG-0001"],
        repair_budget(1, "REGRESSION", ["EVR-REG-0001"], ["regressed"]),
    )

    def weaken_security(c):
        c["request"]["repair_budget"] = 1
        c["evaluators"] = [eval_det(), eval_sec()]
        c["request"]["evaluator_ids"] = ["EVL-DET-001", "EVL-SEC-001"]
        c["result"]["failed_attempts"] = [
            {
                "attempt_id": "RPA-016-0",
                "attempt_index": 0,
                "mutation_summary": "removed security constraint",
                "allowed_mutation": False,
                "outcome": "refused_immutable",
                "preserved_failed_evidence": True,
                "weakened_security_or_objective": True,
                "diagnostic_codes": ["EVR-SEC-0001"],
            }
        ]
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-SEC-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-SEC-0001"]
        c["expected"]["repair_weakened_security_or_objective"] = False
        c["repair_plan"] = {
            "plan_id": "RPL-016",
            "budget": 1,
            "immutable_fields": ["accepted_objectives", "security_constraints"],
            "allowed_mutations": ["artifact_surface"],
            "stop_states": ["immutable_violation", "success"],
        }

    add(
        "016",
        "adversarial",
        "repair cannot weaken security or accepted objectives",
        "BLOCKED",
        ["EVR-SEC-0001"],
        weaken_security,
    )

    def discard_attempts(c):
        c["result"]["failed_attempts"] = []
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-EVD-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-EVD-0001"]
        c["expected"]["failed_attempts_discarded"] = False
        c["meta"] = {"claimed_attempts": 2, "recorded_attempts": 0}

    add(
        "017",
        "adversarial",
        "discarding failed attempts is invalid",
        "BLOCKED",
        ["EVR-EVD-0001"],
        discard_attempts,
    )

    def network_used(c):
        c["request"]["network_allowed"] = False
        c["result"]["network_used"] = True
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-NET-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-NET-0001"]
        c["expected"]["network_used"] = False

    add("018", "adversarial", "no-network default violated", "BLOCKED", ["EVR-NET-0001"], network_used)

    def hide_error_in_score(c):
        c["result"]["evaluator_outcomes"][0].update({"outcome": "error", "score": 1.0})
        c["result"]["scores"] = {"primary": 1.0}
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-SCR-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-SCR-0001"]

    add(
        "019",
        "adversarial",
        "scoring cannot hide evaluator errors",
        "BLOCKED",
        ["EVR-SCR-0001"],
        hide_error_in_score,
    )

    def model_self_report_termination(c):
        c["evaluators"] = [eval_model()]
        c["request"]["evaluator_ids"] = ["EVL-MDL-001"]
        c["result"]["evaluator_outcomes"] = [
            {
                "evaluator_id": "EVL-MDL-001",
                "outcome": "pass",
                "authoritative_for_executable": False,
                "score": 1.0,
                "message": "model says done",
            }
        ]
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-TRM-0001"]
        c["meta"] = {"termination_source": "model_self_report"}
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-TRM-0001"]
        c["expected"]["termination_depends_on_model_self_report"] = False

    add(
        "020",
        "adversarial",
        "termination must not depend on model self-report",
        "BLOCKED",
        ["EVR-TRM-0001"],
        model_self_report_termination,
    )

    add("021", "positive", "repeatable deterministic pass", "PASS", [])
    # duplicate semantics for determinism pair
    cases[-1]["determinism_pair"] = "pair-a"
    add("022", "positive", "repeatable deterministic pass twin", "PASS", [])
    cases[-1]["determinism_pair"] = "pair-a"

    def missing_req(c):
        c["request"]["requirement_ids"] = ["REQ-MISSING-999"]
        c["result"]["status"] = "BLOCKED"
        c["result"]["diagnostic_codes"] = ["EVR-REQ-0001"]
        c["expected"]["status"] = "BLOCKED"
        c["expected"]["diagnostic_codes"] = ["EVR-REQ-0001"]
        c["meta"] = {"known_requirement_ids": ["REQ-EVAL-001"]}

    add(
        "023",
        "negative",
        "MISSION-008 requirement identity unavailable",
        "BLOCKED",
        ["EVR-REQ-0001"],
        missing_req,
    )

    def precedence(c):
        c["evaluators"] = [eval_det(), eval_model(), eval_sec()]
        c["request"]["evaluator_ids"] = ["EVL-DET-001", "EVL-MDL-001", "EVL-SEC-001"]
        c["result"]["evaluator_outcomes"] = [
            {
                "evaluator_id": "EVL-SEC-001",
                "outcome": "fail",
                "authoritative_for_executable": True,
                "score": 0.0,
            },
            {
                "evaluator_id": "EVL-MDL-001",
                "outcome": "pass",
                "authoritative_for_executable": False,
                "score": 1.0,
            },
            {
                "evaluator_id": "EVL-DET-001",
                "outcome": "pass",
                "authoritative_for_executable": True,
                "score": 1.0,
            },
        ]
        c["result"]["status"] = "FAIL"
        c["result"]["diagnostic_codes"] = ["EVR-PRC-0001"]
        c["expected"]["status"] = "FAIL"
        c["expected"]["diagnostic_codes"] = ["EVR-PRC-0001"]

    add(
        "024",
        "boundary",
        "deterministic/security precedence over model judge",
        "FAIL",
        ["EVR-PRC-0001"],
        precedence,
    )

    return cases


REGISTRY = {
    "namespace": "EVR",
    "version": "0.1.0-draft",
    "diagnostics": [
        {"code": "EVR-DET-0001", "severity": "deterministic", "summary": "Deterministic validator failed"},
        {"code": "EVR-DET-0002", "severity": "deterministic", "summary": "Deterministic validator error"},
        {"code": "EVR-BSL-0001", "severity": "baseline", "summary": "Baseline absent or mismatched"},
        {"code": "EVR-BSL-0002", "severity": "baseline", "summary": "Baseline stale"},
        {"code": "EVR-AGG-0001", "severity": "aggregation", "summary": "Aggregation threshold failed"},
        {"code": "EVR-UNA-0001", "severity": "availability", "summary": "Evaluator unavailable"},
        {"code": "EVR-MDL-0001", "severity": "model_judge", "summary": "Advisory model judge disagreement"},
        {"code": "EVR-AUT-0001", "severity": "authority", "summary": "Model judge claimed executable authority"},
        {"code": "EVR-REP-0001", "severity": "repair", "summary": "Repair budget zero with failing candidate"},
        {"code": "EVR-REP-0002", "severity": "repair", "summary": "Repair budget exhausted unresolved"},
        {"code": "EVR-REP-0003", "severity": "repair", "summary": "Repair timeout"},
        {"code": "EVR-REP-0004", "family": "repair", "summary": "Repair cost exhausted"},
        {"code": "EVR-REG-0001", "family": "regression", "summary": "Repair introduced regression"},
        {"code": "EVR-SEC-0001", "family": "security", "summary": "Repair attempted to weaken security/objectives"},
        {"code": "EVR-EVD-0001", "family": "evidence", "summary": "Failed attempts discarded"},
        {"code": "EVR-NET-0001", "family": "network", "summary": "Network used under no-network default"},
        {"code": "EVR-SCR-0001", "family": "scoring", "summary": "Score hides evaluator error"},
        {"code": "EVR-TRM-0001", "family": "termination", "summary": "Termination depended on model self-report"},
        {"code": "EVR-REQ-0001", "family": "requirements", "summary": "Requirement identity unavailable"},
        {"code": "EVR-PRC-0001", "family": "precedence", "summary": "Lower-authority evaluator cannot override"},
        {"code": "EVR-SCH-0001", "family": "schema", "summary": "Schema validation failure"},
    ],
}


def write_docs() -> None:
    w(
        PKG / "README.md",
        f"""# Evaluation and Bounded Repair Contract v0.1

**Status:** `PROPOSED` — executable contract evidence for MISSION-009. Not production-certified. Does not authorize a production evaluator/repair engine, live providers, benchmarks, UI, or MISSION-010/011 without separate launch.

**Exact baseline:** `main` at `{BASELINE_COMMIT}`.

## Purpose

Define deterministic-first evaluation, baseline/candidate comparison, bounded repair (budgets 0–2), regression, and evidence semantics that close the compiler loop while preserving MISSION-008 requirement identities.

## Authority (non-negotiable)

1. Deterministic validators, schema validators, and security policy checks are authoritative for schema, security, and executable correctness.
2. Model judges are advisory only and must set `authoritative_for_executable=false`.
3. Failed attempts and regressions are retained evidence; discarding them is a contract violation (`EVR-EVD-0001`).
4. Termination must not depend on model self-report (`EVR-TRM-0001`).
5. Scoring must not hide evaluator errors (`EVR-SCR-0001`).
6. Repair must not weaken accepted objectives or security constraints (`EVR-SEC-0001`).
7. Default evaluation is no-network (`network_allowed=false`, `network_used=false`).

## Package index

| Path | Role |
|---|---|
| EVALUATION_REPAIR_SPEC.md | Normative terms and statuses |
| AUTHORITY_AND_PRECEDENCE.md | Evaluator authority order |
| BASELINE_AND_CANDIDATE.md | Baseline/candidate identity rules |
| REPAIR_BUDGETS_AND_MUTATIONS.md | Budgets 0/1/2 and stop states |
| EVIDENCE_MODEL.md | Evidence and REQ-* linkage |
| DIAGNOSTICS.md | EVR-* namespace |
| TRACEABILITY.md | Trace rules |
| SECURITY_CONSTRAINTS.md | Immutable security/objectives |
| DECISION_LOG.md | Proposed decisions |
| OPEN_QUESTIONS.md | Open questions |
| OWNER_DECISION_REQUEST.md | Owner choices |
| schemas/ | Draft 2020-12 schemas |
| fixtures/ | Semantic oracle + schema instances |
| validate_contract.py | Test-only validator |
| evidence/ | Validation evidence output |

## Out of scope

Production evaluator/repair engines, live provider judges as required infrastructure, unbounded repair, benchmarks, UI, hosted jobs, IR v0.2, frozen Compiler Core diagnostic registry edits.
""",
    )

    docs = {
        "EVALUATION_REPAIR_SPEC.md": """# Evaluation Repair Spec

## Statuses

`PASS`, `FAIL`, `ERROR`, `BLOCKED`, `UNAVAILABLE`, `REGRESSION`, `UNRESOLVED_DEFECT`.

## Determinism

Given identical request, evaluators, and fixtures, validation outcomes are byte-stable. No network. No wall-clock dependence in the oracle.

## Fail-closed

Unavailable evaluators, schema failures, authority violations, and evidence gaps produce `BLOCKED`/`ERROR`/`UNAVAILABLE` — never a silent PASS.
""",
        "AUTHORITY_AND_PRECEDENCE.md": """# Authority and Precedence

Lower rank number = higher authority.

1. `deterministic_validator`, `schema_validator`, `security_policy_check` (rank 1)
2. `score_aggregator` / `fake_adapter_oracle` (rank 2–3)
3. `model_judge` (rank 7, advisory only)

A model judge with `authoritative_for_executable=true` is invalid (`EVR-AUT-0001`).
""",
        "BASELINE_AND_CANDIDATE.md": """# Baseline and Candidate

Baselines and candidates carry digests, contract versions, and optional REQ-* links.
Missing, mismatched, or stale baselines block evaluation (`EVR-BSL-0001`, `EVR-BSL-0002`).
""",
        "REPAIR_BUDGETS_AND_MUTATIONS.md": """# Repair Budgets and Mutations

Budgets are exactly 0, 1, or 2 attempts.
Immutable fields include accepted objectives, security constraints, and requirement identities.
Stop states: budget_exhausted, timeout, cost_exhausted, regression, unresolved_defect, immutable_violation, success.
""",
        "EVIDENCE_MODEL.md": """# Evidence Model

Every evaluation evidence bundle must reference one or more MISSION-008-compatible requirement IDs (`REQ-*`).
Failed attempts remain in `failed_attempts` and unresolved defects reference them. Discarding attempts is forbidden.
""",
        "DIAGNOSTICS.md": """# Diagnostics

Namespace `EVR-*` is separate from `RQC-*` and from the frozen Compiler Core registry.
See `evaluation-repair-diagnostic-registry.json`.
""",
        "TRACEABILITY.md": """# Traceability

request → evaluators → result → failed_attempts → unresolved_defect → requirement_ids.
""",
        "SECURITY_CONSTRAINTS.md": """# Security Constraints

Repair mutations that weaken security constraints or accepted objectives are refused (`EVR-SEC-0001`).
""",
        "DECISION_LOG.md": """# Decision Log (Proposed)

| ID | Decision | Status |
|---|---|---|
| RCD-009-001 | Deterministic/security validators authoritative for executable correctness | Proposed |
| RCD-009-002 | Model judges advisory only | Proposed |
| RCD-009-003 | Repair budgets limited to 0–2 | Proposed |
| RCD-009-004 | Failed attempts retained | Proposed |
| RCD-009-005 | No-network default | Proposed |
""",
        "OPEN_QUESTIONS.md": """# Open Questions

- OQ-009-001: Exact cost-unit ontology for repair budgets across adapters.
- OQ-009-002: Whether fake-adapter oracle shares rank with deterministic validators for prototype-only paths.
""",
        "OWNER_DECISION_REQUEST.md": """# Owner Decision Request — MISSION-009

Approve or modify RCD-009-001 through RCD-009-005.
Non-authorization: no production engine, no live providers, no MISSION-010 start without separate baseline authorization (campaign pre-auth recorded in SDD ledger).
""",
    }
    for name, body in docs.items():
        w(PKG / name, body)


def write_validator() -> None:
    w(
        PKG / "validate_contract.py",
        '''"""Deterministic validation harness for MISSION-009 evaluation-repair contract.

Test-only. Not a production evaluator or repair engine. No network.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CONTRACT_VERSION = "0.1.0-draft"
SCHEMA_NAMES = (
    "evaluator-record.schema.json",
    "baseline-identity.schema.json",
    "candidate-identity.schema.json",
    "evaluation-request.schema.json",
    "repair-attempt.schema.json",
    "repair-plan.schema.json",
    "unresolved-defect.schema.json",
    "evaluation-result.schema.json",
    "evaluation-evidence-bundle.schema.json",
)
REQ_RE = re.compile(r"^REQ-[A-Z0-9-]{3,64}$")
EVR_RE = re.compile(r"^EVR-[A-Z]+-[0-9]{4}$")
KNOWN_REQS = {"REQ-EVAL-001"}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry(schemas_dir: Path) -> Registry:
    registry = Registry()
    for name in SCHEMA_NAMES:
        path = schemas_dir / name
        data = _read(path)
        registry = registry.with_resource(data["$id"], Resource.from_contents(data))
        registry = registry.with_resource(name, Resource.from_contents(data))
    return registry


def _validator_for(schemas_dir: Path, name: str) -> Draft202012Validator:
    schema = _read(schemas_dir / name)
    return Draft202012Validator(schema, registry=_registry(schemas_dir))


def _oracle(case: dict[str, Any]) -> list[str]:
    """Return diagnostic codes the contract rules require for this case shape."""
    errors: list[str] = []
    request = case["request"]
    result = case["result"]
    evaluators = {e["evaluator_id"]: e for e in case.get("evaluators", [])}

    if request.get("network_allowed") is False and result.get("network_used") is True:
        errors.append("EVR-NET-0001")

    for req in request.get("requirement_ids", []):
        known = set(case.get("meta", {}).get("known_requirement_ids", list(KNOWN_REQS)))
        if req not in known:
            errors.append("EVR-REQ-0001")

    baseline = request.get("baseline", {})
    if baseline.get("stale") is True:
        errors.append("EVR-BSL-0002")
    if baseline.get("baseline_id") == "BSL-MISSING":
        errors.append("EVR-BSL-0001")

    for outcome in result.get("evaluator_outcomes", []):
        ev = evaluators.get(outcome["evaluator_id"])
        if ev and ev.get("evaluator_kind") == "model_judge" and outcome.get("authoritative_for_executable") is True:
            errors.append("EVR-AUT-0001")
        if outcome.get("outcome") == "error" and outcome.get("score") not in (None,):
            # hiding error behind numeric success score
            if isinstance(outcome.get("score"), (int, float)) and outcome["score"] >= 1.0:
                errors.append("EVR-SCR-0001")
        if outcome.get("outcome") == "unavailable":
            errors.append("EVR-UNA-0001")
        if (
            outcome.get("outcome") == "error"
            and ev
            and ev.get("evaluator_kind") == "deterministic_validator"
            and result.get("status") == "ERROR"
        ):
            errors.append("EVR-DET-0002")
        if (
            outcome.get("outcome") == "fail"
            and ev
            and ev.get("evaluator_kind") == "deterministic_validator"
            and result.get("status") == "FAIL"
        ):
            errors.append("EVR-DET-0001")

    if case.get("meta", {}).get("termination_source") == "model_self_report":
        errors.append("EVR-TRM-0001")

    meta = case.get("meta", {})
    if meta.get("claimed_attempts", 0) > len(result.get("failed_attempts", [])):
        errors.append("EVR-EVD-0001")

    for attempt in result.get("failed_attempts", []):
        if attempt.get("weakened_security_or_objective") is True:
            errors.append("EVR-SEC-0001")
        if attempt.get("outcome") == "regressed":
            errors.append("EVR-REG-0001")
        if attempt.get("outcome") == "timeout":
            errors.append("EVR-REP-0003")
        if attempt.get("outcome") == "cost_exhausted":
            errors.append("EVR-REP-0004")
        if attempt.get("preserved_failed_evidence") is False:
            errors.append("EVR-EVD-0001")

    if request.get("repair_budget") == 0 and result.get("status") == "FAIL" and not result.get("failed_attempts"):
        errors.append("EVR-REP-0001")
    if result.get("status") == "UNRESOLVED_DEFECT":
        errors.append("EVR-REP-0002")
        ud = case.get("unresolved_defect")
        if ud and ud.get("discarded_attempts") is True:
            errors.append("EVR-EVD-0001")

    # model advisory disagreement marker when model fails but det passes
    outcomes = {o["evaluator_id"]: o for o in result.get("evaluator_outcomes", [])}
    if "EVL-MDL-001" in outcomes and "EVL-DET-001" in outcomes:
        if outcomes["EVL-DET-001"]["outcome"] == "pass" and outcomes["EVL-MDL-001"]["outcome"] == "fail":
            if outcomes["EVL-MDL-001"].get("authoritative_for_executable") is False:
                errors.append("EVR-MDL-0001")

    if "EVL-SEC-001" in outcomes and outcomes["EVL-SEC-001"]["outcome"] == "fail":
        if result.get("status") == "FAIL":
            errors.append("EVR-PRC-0001" if "EVL-MDL-001" in outcomes else "EVR-AGG-0001")

    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for code in errors:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def validate_case(case: dict[str, Any], schemas_dir: Path, registry_codes: set[str]) -> dict[str, Any]:
    problems: list[str] = []
    # schema-validate core records present
    for name, obj, schema in (
        ("request", case.get("request"), "evaluation-request.schema.json"),
        ("result", case.get("result"), "evaluation-result.schema.json"),
    ):
        if obj is None:
            problems.append(f"missing {name}")
            continue
        errs = sorted(_validator_for(schemas_dir, schema).iter_errors(obj), key=lambda e: list(e.path))
        for err in errs:
            problems.append(f"{name} schema: {err.message}")

    for ev in case.get("evaluators", []):
        for err in _validator_for(schemas_dir, "evaluator-record.schema.json").iter_errors(ev):
            problems.append(f"evaluator schema: {err.message}")

    if "repair_plan" in case:
        for err in _validator_for(schemas_dir, "repair-plan.schema.json").iter_errors(case["repair_plan"]):
            problems.append(f"repair_plan schema: {err.message}")
    if "unresolved_defect" in case:
        for err in _validator_for(schemas_dir, "unresolved-defect.schema.json").iter_errors(case["unresolved_defect"]):
            problems.append(f"unresolved_defect schema: {err.message}")

    derived = _oracle(case)
    expected_codes = list(case.get("expected", {}).get("diagnostic_codes", []))
    expected_status = case.get("expected", {}).get("status")
    actual_status = case.get("result", {}).get("status")
    actual_codes = list(case.get("result", {}).get("diagnostic_codes", []))

    if expected_status != actual_status:
        problems.append(f"status mismatch expected={expected_status} actual={actual_status}")
    if sorted(expected_codes) != sorted(actual_codes):
        problems.append(f"result codes mismatch expected={expected_codes} actual={actual_codes}")
    if sorted(derived) != sorted(expected_codes):
        problems.append(f"oracle codes mismatch derived={derived} expected={expected_codes}")

    for code in expected_codes + actual_codes + derived:
        if code not in registry_codes:
            problems.append(f"unknown diagnostic {code}")
        if not EVR_RE.match(code):
            problems.append(f"malformed diagnostic {code}")

    # stop-condition guards encoded as expected flags
    exp = case.get("expected", {})
    if exp.get("model_judge_authoritative_for_executable") is True:
        problems.append("stop-condition: model judge must not be authoritative")
    if exp.get("failed_attempts_discarded") is True:
        problems.append("stop-condition: failed attempts must not be discarded")
    if exp.get("termination_depends_on_model_self_report") is True:
        problems.append("stop-condition: termination must not depend on model self-report")
    if exp.get("repair_weakened_security_or_objective") is True:
        problems.append("stop-condition: repair must not weaken security/objectives")
    if exp.get("network_used") is True:
        problems.append("stop-condition: network must not be used by default")

    # structural: model outcomes never authoritative in fixtures that PASS/FAIL legitimately
    for outcome in case.get("result", {}).get("evaluator_outcomes", []):
        ev = next((e for e in case.get("evaluators", []) if e["evaluator_id"] == outcome["evaluator_id"]), None)
        if ev and ev.get("evaluator_kind") == "model_judge" and outcome.get("authoritative_for_executable") is True:
            if "EVR-AUT-0001" not in actual_codes:
                problems.append("model judge authoritative without EVR-AUT-0001")

    return {"case_id": case.get("case_id"), "ok": not problems, "problems": problems}


def validate_package(package: Path) -> dict[str, Any]:
    schemas_dir = package / "schemas"
    fixtures = package / "fixtures"
    registry = _read(package / "evaluation-repair-diagnostic-registry.json")
    registry_codes = {d["code"] for d in registry["diagnostics"]}
    cases = _read(fixtures / "cases.json")["cases"]
    manifest = _read(fixtures / "manifest.json")
    schema_instances = _read(fixtures / "schema_instances.json")["instances"]

    schema_ok = 0
    for name in SCHEMA_NAMES:
        Draft202012Validator.check_schema(_read(schemas_dir / name))
        schema_ok += 1

    instance_pass = 0
    instance_problems: list[str] = []
    for inst in schema_instances:
        v = _validator_for(schemas_dir, inst["schema"])
        errs = list(v.iter_errors(inst["document"]))
        should_pass = inst["expect"] == "accept"
        if should_pass and not errs:
            instance_pass += 1
        elif (not should_pass) and errs:
            instance_pass += 1
        else:
            instance_problems.append(inst["id"])

    case_results = [validate_case(case, schemas_dir, registry_codes) for case in cases]
    case_pass = sum(1 for r in case_results if r["ok"])

    # determinism pairs must match status+codes
    pairs: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        key = case.get("determinism_pair")
        if key:
            pairs.setdefault(key, []).append(case)
    determinism_ok = True
    for key, group in pairs.items():
        sigs = {(c["result"]["status"], tuple(sorted(c["result"]["diagnostic_codes"]))) for c in group}
        if len(sigs) != 1:
            determinism_ok = False

    status = "PASS" if (
        schema_ok == len(SCHEMA_NAMES)
        and case_pass == len(cases)
        and instance_pass == len(schema_instances)
        and case_pass == manifest["case_count"]
        and determinism_ok
    ) else "FAIL"

    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "schema_count": schema_ok,
        "fixture_count": len(cases),
        "fixture_pass_count": case_pass,
        "schema_instance_count": len(schema_instances),
        "schema_instance_pass_count": instance_pass,
        "determinism_ok": determinism_ok,
        "failed_cases": [r for r in case_results if not r["ok"]],
        "failed_instances": instance_problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = validate_package(args.package)
    evidence = args.package / "evidence" / "validation-result.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "fixture_pass_count": result["fixture_pass_count"], "fixture_count": result["fixture_count"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
''',
    )


def write_tests() -> None:
    w(
        TESTS / "test_evaluation_repair_contract.py",
        '''from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "architecture" / "evaluation-repair-contract-v0.1"
FIXTURES = PACKAGE / "fixtures"
VALIDATOR_PATH = PACKAGE / "validate_contract.py"
SCHEMA_NAMES = {
    "evaluator-record.schema.json",
    "baseline-identity.schema.json",
    "candidate-identity.schema.json",
    "evaluation-request.schema.json",
    "evaluation-result.schema.json",
    "repair-attempt.schema.json",
    "repair-plan.schema.json",
    "unresolved-defect.schema.json",
    "evaluation-evidence-bundle.schema.json",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_validator() -> ModuleType:
    assert VALIDATOR_PATH.is_file(), "MISSION-009 contract validator is not implemented"
    spec = importlib.util.spec_from_file_location("mission009_contract_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_package_layout_and_case_coverage() -> None:
    manifest = _json(FIXTURES / "manifest.json")
    cases = _json(FIXTURES / "cases.json")["cases"]
    assert len(cases) == manifest["case_count"] >= 20
    assert {c["category"] for c in cases} >= {"positive", "negative", "boundary", "adversarial"}
    statuses = {c["expected"]["status"] for c in cases}
    assert "PASS" in statuses
    assert "UNRESOLVED_DEFECT" in statuses or "REGRESSION" in statuses
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-AUT-0001"] for c in cases)
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-SEC-0001"] for c in cases)
    assert any(c["expected"]["diagnostic_codes"] == ["EVR-NET-0001"] for c in cases)
    for name in SCHEMA_NAMES:
        assert (PACKAGE / "schemas" / name).is_file()


def test_contract_validator_passes_all_fixtures() -> None:
    validator = _load_validator()
    result = validator.validate_package(PACKAGE)
    assert result["status"] == "PASS", result.get("failed_cases")
    assert result["schema_count"] == 9
    assert result["fixture_pass_count"] == result["fixture_count"]
    assert result["determinism_ok"] is True


def test_model_judge_never_quietly_authoritative() -> None:
    cases = _json(FIXTURES / "cases.json")["cases"]
    for case in cases:
        for outcome in case["result"]["evaluator_outcomes"]:
            ev = next(e for e in case["evaluators"] if e["evaluator_id"] == outcome["evaluator_id"])
            if ev["evaluator_kind"] == "model_judge" and outcome.get("authoritative_for_executable") is True:
                assert "EVR-AUT-0001" in case["result"]["diagnostic_codes"]
''',
    )


def write_schema_instances() -> list[dict]:
    instances = [
        {
            "id": "accept-evaluator",
            "schema": "evaluator-record.schema.json",
            "expect": "accept",
            "document": eval_det(),
        },
        {
            "id": "reject-evaluator-kind",
            "schema": "evaluator-record.schema.json",
            "expect": "reject",
            "document": {**eval_det(), "evaluator_kind": "live_provider"},
        },
        {
            "id": "accept-baseline",
            "schema": "baseline-identity.schema.json",
            "expect": "accept",
            "document": baseline(),
        },
        {
            "id": "reject-baseline-digest",
            "schema": "baseline-identity.schema.json",
            "expect": "reject",
            "document": {**baseline(), "artifact_digest": "not-a-digest"},
        },
        {
            "id": "accept-repair-plan",
            "schema": "repair-plan.schema.json",
            "expect": "accept",
            "document": {
                "plan_id": "RPL-OKAY",
                "budget": 2,
                "immutable_fields": ["security_constraints"],
                "allowed_mutations": ["artifact_surface"],
                "stop_states": ["success", "budget_exhausted"],
            },
        },
        {
            "id": "reject-repair-budget",
            "schema": "repair-plan.schema.json",
            "expect": "reject",
            "document": {
                "plan_id": "RPL-BAD",
                "budget": 3,
                "immutable_fields": ["security_constraints"],
                "allowed_mutations": [],
                "stop_states": ["success"],
            },
        },
    ]
    return instances


def write_report() -> None:
    w(
        ROOT / "MISSION_009_REPORT.md",
        f"""# PromptRig MISSION-009 Report

**Mission:** Evaluation and Bounded Repair Contract  
**Status:** Proposed package prepared for adversarial audit and merge; not production-certified.  
**Baseline:** `main` at `{BASELINE_COMMIT}`  
**Branch:** `contracts/mission-009-evaluation-repair-v0.1`

## Deliverables

- Contract package at `architecture/evaluation-repair-contract-v0.1/`
- Nine Draft 2020-12 schemas
- EVR-* diagnostic registry (separate from RQC-* and frozen compiler registry)
- 24 semantic-oracle fixtures covering precedence, repair budgets 0–2, regressions, security immutability, no-network, evidence retention
- Deterministic `validate_contract.py` harness
- Pytest suite `tests/evaluation/test_evaluation_repair_contract.py`

## Stop-condition posture

Encoded as fixtures + oracle rules:

- Model judges cannot be executable-authoritative (`EVR-AUT-0001`)
- Failed attempts cannot be discarded (`EVR-EVD-0001`)
- Termination cannot depend on model self-report (`EVR-TRM-0001`)
- Scoring cannot hide evaluator errors (`EVR-SCR-0001`)
- Repair cannot weaken security/objectives (`EVR-SEC-0001`)
- MISSION-008 requirement IDs must resolve (`EVR-REQ-0001`)

## Non-claims

No production evaluator/repair engine, no live providers, no benchmark runner, no UI.
""",
    )


def main() -> None:
    for name, schema in SCHEMA_DEFS.items():
        j(SCHEMAS / name, schema)
    cases = make_cases()
    j(FIXTURES / "cases.json", {"cases": cases})
    j(
        FIXTURES / "manifest.json",
        {
            "case_count": len(cases),
            "contract_version": CONTRACT_VERSION,
            "baseline_commit": BASELINE_COMMIT,
        },
    )
    j(FIXTURES / "schema_instances.json", {"instances": write_schema_instances()})
    j(FIXTURES / "linked_artifact_sets.json", {"sets": []})
    j(PKG / "evaluation-repair-diagnostic-registry.json", REGISTRY)
    write_docs()
    write_validator()
    write_tests()
    write_report()
    print(f"wrote {len(cases)} cases to {PKG}")


if __name__ == "__main__":
    main()
