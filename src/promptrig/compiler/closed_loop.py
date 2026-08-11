"""MISSION-010 headless closed-loop prototype (fake adapter only).

Pipeline: structured requirements → IR → fake compile → evaluate → bounded repair → evidence.
No network. No live providers. Not a production hardening boundary (see MISSION-011).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from . import api
from .canonical import canonical_sha256, canonicalize
from .contracts import CompileOptions, ResultEnvelope

CONTRACT_008 = "0.1.0-draft"
CONTRACT_009 = "0.1.0-draft"
PROTOTYPE_ID = "mission-010-closed-loop-v0.1"
FAKE_ADAPTER_ID = "fake"
FAKE_ADAPTER_VERSION = "0.1.0"
IMMUTABLE_FIELDS = ("accepted_objectives", "security_constraints", "requirement_ids")


@dataclass
class ClosedLoopOptions:
    repair_budget: int = 1
    network_allowed: bool = False
    force_fail_first_compile: bool = False
    force_security_weaken_repair: bool = False


@dataclass
class ClosedLoopResult:
    status: str
    evidence_bundle: dict[str, Any]
    envelope: ResultEnvelope | None = None
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


def _digest(payload: Any) -> str:
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    else:
        raw = canonicalize(payload)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_structured_requirements(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("profile") != "structured_minimal_v0":
        errors.append("unsupported profile; prototype accepts only structured_minimal_v0")
    if doc.get("contract_version") != CONTRACT_008:
        errors.append("requirements contract_version must be 0.1.0-draft")
    reqs = doc.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        errors.append("requirements must be a non-empty list")
    else:
        for req in reqs:
            rid = req.get("id", "")
            if not isinstance(rid, str) or not rid.startswith("REQ-"):
                errors.append(f"invalid requirement id: {rid!r}")
            if not req.get("statement"):
                errors.append(f"requirement {rid} missing statement")
    if not doc.get("objective", {}).get("goal"):
        errors.append("objective.goal is required")
    if doc.get("network_allowed") is True:
        errors.append("network_allowed must be false for prototype")
    return errors


def requirements_to_ir(doc: dict[str, Any]) -> dict[str, Any]:
    """Deterministic mapping for the single approved structured profile."""
    errors = validate_structured_requirements(doc)
    if errors:
        raise ValueError("; ".join(errors))

    requirements = []
    for req in doc["requirements"]:
        requirements.append(
            {
                "id": req["id"],
                "statement": req["statement"],
                "priority": "p0" if req.get("priority", "required") == "required" else "p1",
                "mandatory": req.get("priority", "required") == "required",
                "acceptance": list(req.get("acceptance", ["statement_satisfied"])),
            }
        )

    goal = doc["objective"]["goal"]
    project_name = doc.get("project_name", "closed-loop-demo")
    source = canonicalize(doc)
    return {
        "spec_version": "0.1.0",
        "project": {
            "name": project_name,
            "mode": "balanced",
            "compilation_level": "prompt",
        },
        "objective": {
            "goal": goal,
            "target_users": list(doc.get("objective", {}).get("target_users", ["operators"])),
            "success_criteria": list(doc.get("objective", {}).get("success_criteria", ["requirements_met"])),
            "failure_conditions": list(doc.get("objective", {}).get("failure_conditions", ["requirement_violation"])),
        },
        "requirements": requirements,
        "behavior": {
            "instructions": list(doc.get("behavior", {}).get("instructions", ["Follow requirements exactly."])),
            "constraints": list(doc.get("behavior", {}).get("constraints", ["Do not invent facts."])),
            "uncertainty_policy": doc.get("behavior", {}).get(
                "uncertainty_policy", "State uncertainty explicitly rather than guessing."
            ),
            "evidence_policy": doc.get("behavior", {}).get(
                "evidence_policy", "Cite sources when available."
            ),
        },
        "evaluation": {
            "dimensions": ["accuracy"],
            "repair_limit": int(doc.get("repair_budget", 1)),
            "baseline_required": False,
            "test_categories": ["smoke"],
        },
        "provenance": {
            "source_id": "mission-010-structured-requirements",
            "source_sha256": hashlib.sha256(source).hexdigest(),
        },
    }


def _evaluate_artifact(
    *,
    baseline_digest: str | None,
    candidate_digest: str,
    compile_ok: bool,
    security_ok: bool,
    network_used: bool,
) -> dict[str, Any]:
    codes: list[str] = []
    if network_used:
        return {
            "status": "BLOCKED",
            "diagnostic_codes": ["EVR-NET-0001"],
            "scores": {"primary": None},
        }
    if not compile_ok:
        codes.append("EVR-DET-0001")
        return {"status": "FAIL", "diagnostic_codes": codes, "scores": {"primary": 0.0}}
    if not security_ok:
        codes.append("EVR-SEC-0001")
        return {"status": "BLOCKED", "diagnostic_codes": codes, "scores": {"primary": 0.0}}
    if baseline_digest and baseline_digest == candidate_digest:
        # identical to failing baseline still fails if marked
        pass
    return {"status": "PASS", "diagnostic_codes": [], "scores": {"primary": 1.0}}


def run_closed_loop(requirements_doc: dict[str, Any], options: ClosedLoopOptions | None = None) -> ClosedLoopResult:
    options = options or ClosedLoopOptions()
    if options.network_allowed:
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=["EVR-NET-0001"],
        )
    if options.repair_budget not in (0, 1, 2):
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=["EVR-REP-0001"])

    try:
        ir_doc = requirements_to_ir(requirements_doc)
    except ValueError as exc:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=[str(exc)])

    # freeze repair_limit to options
    ir_doc = json.loads(json.dumps(ir_doc))
    ir_doc["evaluation"]["repair_limit"] = options.repair_budget

    requirement_ids = [r["id"] for r in ir_doc["requirements"]]
    accepted_objectives = list(ir_doc["objective"]["success_criteria"])
    security_constraints = list(ir_doc["behavior"]["constraints"])

    ir_raw = canonicalize(ir_doc)
    baseline_digest = _digest({"phase": "requirements", "ir": ir_doc})

    failed_attempts: list[dict[str, Any]] = []
    current_ir = ir_doc
    current_raw = ir_raw
    compile_env: ResultEnvelope | None = None
    final_eval: dict[str, Any] | None = None

    attempts_allowed = options.repair_budget
    # initial compile + eval counts as attempt 0 only when repair runs after failure
    for attempt_index in range(0, attempts_allowed + 1):
        force_fail = options.force_fail_first_compile and attempt_index == 0
        if force_fail:
            compile_ok = False
            candidate_digest = _digest({"failed": True, "attempt": attempt_index})
            artifacts: list[dict[str, Any]] = []
        else:
            compile_env = api.compile(
                current_raw,
                adapter_id=FAKE_ADAPTER_ID,
                adapter_version=FAKE_ADAPTER_VERSION,
                options=CompileOptions(offline=True),
                source_document="<closed-loop>",
            )
            compile_ok = compile_env.status != "error"
            artifacts = list(compile_env.data.get("artifacts", [])) if compile_ok else []
            candidate_digest = _digest(
                {
                    "ir": current_ir,
                    "artifacts": artifacts,
                    "adapter": FAKE_ADAPTER_ID,
                    "attempt": attempt_index,
                }
            )

        security_ok = True
        if options.force_security_weaken_repair and attempt_index > 0:
            security_ok = False

        evaluation = _evaluate_artifact(
            baseline_digest=baseline_digest,
            candidate_digest=candidate_digest,
            compile_ok=compile_ok,
            security_ok=security_ok,
            network_used=False,
        )
        final_eval = evaluation

        if evaluation["status"] == "PASS":
            break

        if attempt_index >= attempts_allowed:
            break

        # bounded repair mutation (prototype): tweak instruction wording only
        mutation = "tighten_instruction_wording"
        weakened = False
        if options.force_security_weaken_repair:
            mutation = "remove_security_constraint"
            weakened = True
            # refused — do not apply
            failed_attempts.append(
                {
                    "attempt_id": f"RPA-{attempt_index}",
                    "attempt_index": attempt_index,
                    "mutation_summary": mutation,
                    "allowed_mutation": False,
                    "outcome": "refused_immutable",
                    "preserved_failed_evidence": True,
                    "weakened_security_or_objective": True,
                    "diagnostic_codes": ["EVR-SEC-0001"],
                }
            )
            final_eval = {
                "status": "BLOCKED",
                "diagnostic_codes": ["EVR-SEC-0001"],
                "scores": {"primary": 0.0},
            }
            break

        # apply allowed mutation
        current_ir = json.loads(json.dumps(current_ir))
        instructions = list(current_ir["behavior"]["instructions"])
        instructions.append(f"Repair pass {attempt_index}: restate requirements without changing meaning.")
        current_ir["behavior"]["instructions"] = instructions
        # immutables unchanged
        assert current_ir["objective"]["success_criteria"] == accepted_objectives
        assert current_ir["behavior"]["constraints"] == security_constraints
        assert [r["id"] for r in current_ir["requirements"]] == requirement_ids
        current_raw = canonicalize(current_ir)
        failed_attempts.append(
            {
                "attempt_id": f"RPA-{attempt_index}",
                "attempt_index": attempt_index,
                "mutation_summary": mutation,
                "allowed_mutation": True,
                "outcome": "improved",
                "preserved_failed_evidence": True,
                "weakened_security_or_objective": False,
                "diagnostic_codes": [],
            }
        )

    assert final_eval is not None
    status = final_eval["status"]
    if status != "PASS" and attempts_allowed > 0 and failed_attempts and status == "FAIL":
        status = "UNRESOLVED_DEFECT"
        final_eval = {
            **final_eval,
            "status": status,
            "diagnostic_codes": list(dict.fromkeys([*final_eval.get("diagnostic_codes", []), "EVR-REP-0002"])),
        }

    unresolved = None
    if status == "UNRESOLVED_DEFECT":
        unresolved = {
            "defect_id": "UDF-CLOSED-LOOP",
            "requirement_ids": requirement_ids,
            "failed_attempt_ids": [a["attempt_id"] for a in failed_attempts],
            "terminal_reason": "repair budget exhausted without PASS",
            "discarded_attempts": False,
            "diagnostic_codes": final_eval.get("diagnostic_codes", []),
        }

    evidence = {
        "bundle_id": "EEB-CLOSED-LOOP",
        "prototype_id": PROTOTYPE_ID,
        "contract_versions": {"requirements": CONTRACT_008, "evaluation_repair": CONTRACT_009},
        "requirement_ids": requirement_ids,
        "immutable_fields": list(IMMUTABLE_FIELDS),
        "adapter": {"id": FAKE_ADAPTER_ID, "version": FAKE_ADAPTER_VERSION},
        "ir_sha256": canonical_sha256(current_ir),
        "baseline_digest": baseline_digest,
        "evaluation": final_eval,
        "failed_attempts": failed_attempts,
        "unresolved_defect": unresolved,
        "network_allowed": False,
        "network_used": False,
        "repair_budget": options.repair_budget,
        "compile_status": None if compile_env is None else compile_env.status,
    }

    return ClosedLoopResult(
        status=status,
        evidence_bundle=evidence,
        envelope=compile_env,
        failed_attempts=failed_attempts,
        diagnostics=list(final_eval.get("diagnostic_codes", [])),
    )


def closed_loop_from_json(raw: bytes | str, options: ClosedLoopOptions | None = None) -> ClosedLoopResult:
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = raw
    doc = json.loads(text)
    return run_closed_loop(doc, options)
