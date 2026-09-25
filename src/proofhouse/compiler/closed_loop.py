"""Headless closed-loop (fake adapter only) — OAR-005 narrow certification.

Structured profiles → IR → fake compile → evaluate → bounded repair → evidence.
No network. No live providers. MISSION-012 graduates evaluation/repair/evidence
from MISSION-010 prototype semantics toward production-grade offline headless.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Any

from . import api
from .canonical import canonical_sha256, canonicalize
from .contracts import CompileOptions, ResultEnvelope
from .eval_product import (
    BINDING_BOUND,
    PRODUCT_EVALUATOR_ID,
    PRODUCT_EVALUATOR_VERSION,
    ProductEvalRequest,
    ProductEvaluationResult,
    evaluate_product,
)
from .intake import INP_TYPE, IntakeError, parse_json_object, structured_shape_errors
from .evaluation import EvaluationRequest, EvaluationResult, evaluate_deterministic
from .evidence import (
    DEFAULT_EVALUATOR_ID,
    DEFAULT_EVALUATOR_VERSION,
    build_evidence_bundle,
)
from .model_suggest import (
    SUGGESTION_PROFILE,
    build_fake_model_proposal,
    validate_model_boundary,
)
from .plain_language import PlainLanguageParseError, parse_plain_language_v0
from .repair import ClosedLoopTestHooks, apply_instruction_repair, plan_repair
from .resource_bounds import MAX_INPUT_BYTES

ACCEPTED_INPUT_CONTRACT_VERSIONS = frozenset({"0.1.0-draft", "0.1.0"})
FAKE_ADAPTER_ID = "fake"
FAKE_ADAPTER_VERSION = "0.1.0"
IMMUTABLE_FIELDS = ("accepted_objectives", "security_constraints", "requirement_ids")
REQ_ID_RE = re.compile(r"^REQ-[A-Z0-9-]{3,40}$")
_EVAL_RANK = {"FAIL": 0, "BLOCKED": 0, "UNRESOLVED_DEFECT": 0, "PASS": 1}
# Repair cannot change imported observations, so re-evaluating after a repair
# would re-score the same static data. The loop stops and says so instead.
REPAIR_UNSUPPORTED = "EVR-REP-0005"
# Imported observations that do not all declare this candidate's digest can score
# a rubric, but cannot vouch for this candidate: the closed loop withholds PASS.
CANDIDATE_UNBOUND = "EVR-BND-0002"


@dataclass
class ClosedLoopOptions:
    repair_budget: int = 1
    network_allowed: bool = False
    enable_model_suggestions: bool = False
    product_eval: ProductEvalRequest | None = None


@dataclass
class ClosedLoopResult:
    status: str
    evidence_bundle: dict[str, Any]
    envelope: ResultEnvelope | None = None
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    model_proposal: dict[str, Any] | None = None


def _digest(payload: Any) -> str:
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    else:
        raw = canonicalize(payload)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


APPROVED_PROFILES = frozenset({"structured_minimal_v0", "structured_developer_v0"})
PLAIN_LANGUAGE_INTAKE_PROFILE = "plain_language_v0"
SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC = (
    "Simple Mode UI-only semantics are forbidden before plain-language headless milestone"
)
REQUIREMENTS_CONTRACT_USE_COMPILE_COMMAND = "EVR-RQC-0001"


def validate_structured_requirements(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    profile = doc.get("profile")
    if profile not in APPROVED_PROFILES:
        errors.append(
            "unsupported profile; approved headless profiles are structured_minimal_v0 and structured_developer_v0"
        )
    contract_version = doc.get("contract_version")
    if contract_version not in ACCEPTED_INPUT_CONTRACT_VERSIONS:
        errors.append(
            "requirements contract_version must be one of: 0.1.0-draft, 0.1.0"
        )
    reqs = doc.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        errors.append("requirements must be a non-empty list")
    else:
        for req in reqs:
            rid = req.get("id", "")
            if not isinstance(rid, str) or not REQ_ID_RE.fullmatch(rid):
                errors.append(f"invalid requirement id: {rid!r}")
            if not req.get("statement"):
                errors.append(f"requirement {rid} missing statement")
    if not doc.get("objective", {}).get("goal"):
        errors.append("objective.goal is required")
    if doc.get("network_allowed") is True:
        errors.append("network_allowed must be false for prototype")
    if profile == "structured_developer_v0":
        tools = doc.get("tool_permissions")
        if not isinstance(tools, dict) or not tools.get("allowed_tools"):
            errors.append("structured_developer_v0 requires tool_permissions.allowed_tools")
        if not doc.get("stop_conditions"):
            errors.append("structured_developer_v0 requires stop_conditions")
    if profile == "simple_mode_ui" or doc.get("authoring_mode") == "simple_ui_only":
        errors.append(SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC)
    return errors


def _repair_outcome(prior_status: str, next_status: str) -> str:
    if _EVAL_RANK.get(next_status, 0) > _EVAL_RANK.get(prior_status, 0):
        return "improved"
    return "no_change"


def requirements_to_ir(doc: dict[str, Any]) -> dict[str, Any]:
    """Deterministic mapping for approved structured profiles (MISSION-011)."""
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
    instructions = list(doc.get("behavior", {}).get("instructions", ["Follow requirements exactly."]))
    constraints = list(doc.get("behavior", {}).get("constraints", ["Do not invent facts."]))
    if doc.get("profile") == "structured_developer_v0":
        allowed = ",".join(doc["tool_permissions"]["allowed_tools"])
        instructions.append(f"Tool permission map: allow only [{allowed}].")
        instructions.append("Stop conditions: " + "; ".join(doc["stop_conditions"]))
        constraints.append("Do not invoke disallowed tools.")

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
            "instructions": instructions,
            "constraints": constraints,
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
            "source_id": f"mission-011-{doc['profile']}",
            "source_sha256": hashlib.sha256(source).hexdigest(),
        },
    }


def _evaluation_result_to_evidence(result: EvaluationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "diagnostic_codes": list(result.diagnostic_codes),
        "scores": dict(result.scores),
    }


def _run_product_stage(
    request: ProductEvalRequest,
    candidate_digest: str,
    mandatory_requirement_ids: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate imported observations against this exact candidate; never raise on bad data."""
    try:
        result = evaluate_product(
            replace(request, candidate_digest=candidate_digest, required_req_ids=mandatory_requirement_ids)
        )
    except (OSError, ValueError) as exc:
        code = "EVR-DUP-0001" if "duplicate" in str(exc) else INP_TYPE
        result = ProductEvaluationResult(
            status="BLOCKED",
            diagnostic_codes=(f"{code}: product-eval input rejected: {exc}",),
            scores={"primary": None},
            evaluator_id=PRODUCT_EVALUATOR_ID,
            evaluator_version=PRODUCT_EVALUATOR_VERSION,
            authoritative=True,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=(),
            candidate_digest=candidate_digest,
        )
    evaluation = {
        "status": result.status,
        "diagnostic_codes": list(result.diagnostic_codes),
        "scores": dict(result.scores),
    }
    stage = {
        **evaluation,
        "evaluator": {"id": result.evaluator_id, "version": result.evaluator_version},
        "observation_source": result.observation_source,
        "candidate_digest": result.candidate_digest,
        "candidate_binding": result.candidate_binding,
        "dataset_sha256": result.dataset_sha256,
        "rubric_sha256": result.rubric_sha256,
        "rubric": {"id": result.rubric_id, "version": result.rubric_version},
        "aggregation": result.aggregation,
        "case_results": [dict(row) for row in result.case_results],
        "requirement_coverage": result.requirement_coverage,
    }
    return stage, evaluation


def run_closed_loop(
    requirements_doc: dict[str, Any],
    options: ClosedLoopOptions | None = None,
    hooks: ClosedLoopTestHooks | None = None,
    *,
    intake_profile: str | None = None,
) -> ClosedLoopResult:
    options = options or ClosedLoopOptions()
    if options.network_allowed:
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=["EVR-NET-0001"],
        )
    if options.repair_budget not in (0, 1, 2):
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=["EVR-REP-0001"])

    if hooks is not None:
        if hooks.force_self_accept_proposal:
            return ClosedLoopResult(
                status="INVALID_OUTPUT",
                evidence_bundle={},
                diagnostics=["MAS-GATE-0001"],
            )
        if hooks.force_invent_owner_decision:
            return ClosedLoopResult(
                status="INVALID_OUTPUT",
                evidence_bundle={},
                diagnostics=["MAS-GATE-0002"],
            )
        if hooks.force_weaken_security_via_suggestion:
            return ClosedLoopResult(
                status="INVALID_OUTPUT",
                evidence_bundle={},
                diagnostics=["MAS-GATE-0003"],
            )

    shape_errors = structured_shape_errors(requirements_doc)
    if shape_errors:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=shape_errors)

    boundary_errors = validate_model_boundary(requirements_doc)
    if boundary_errors:
        return ClosedLoopResult(
            status="INVALID_OUTPUT",
            evidence_bundle={},
            diagnostics=boundary_errors,
        )

    model_proposal: dict[str, Any] | None = None
    if options.enable_model_suggestions:
        proposal = build_fake_model_proposal(requirements_doc)
        proposal_errors = validate_model_boundary(requirements_doc, proposal)
        if proposal_errors:
            return ClosedLoopResult(
                status="INVALID_OUTPUT",
                evidence_bundle={},
                diagnostics=proposal_errors,
            )
        model_proposal = proposal

    try:
        ir_doc = requirements_to_ir(requirements_doc)
    except ValueError as exc:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=[str(exc)])

    # freeze repair_limit to options
    ir_doc = json.loads(json.dumps(ir_doc))
    ir_doc["evaluation"]["repair_limit"] = options.repair_budget

    requirement_ids = [r["id"] for r in ir_doc["requirements"]]
    mandatory_requirement_ids = tuple(r["id"] for r in ir_doc["requirements"] if r["mandatory"])
    accepted_objectives = list(ir_doc["objective"]["success_criteria"])
    security_constraints = list(ir_doc["behavior"]["constraints"])

    ir_raw = canonicalize(ir_doc)
    baseline_digest = _digest({"phase": "requirements", "ir": ir_doc})

    failed_attempts: list[dict[str, Any]] = []
    pending_repair: dict[str, Any] | None = None
    pending_prior_status: str | None = None
    current_ir = ir_doc
    current_raw = ir_raw
    compile_env: ResultEnvelope | None = None
    final_eval: dict[str, Any] | None = None
    final_evaluator_id = DEFAULT_EVALUATOR_ID
    final_evaluator_version = DEFAULT_EVALUATOR_VERSION
    deterministic_stage: dict[str, Any] | None = None
    product_stage: dict[str, Any] | None = None
    candidate_digest = ""
    terminal_reason = "not_needed"
    extra_diagnostics: list[str] = []

    attempts_allowed = options.repair_budget
    # initial compile + eval counts as attempt 0 only when repair runs after failure
    for attempt_index in range(0, attempts_allowed + 1):
        force_fail = hooks is not None and hooks.force_fail_first_compile and attempt_index == 0
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
            if compile_env.status == "error":
                error_codes = [d.code for d in compile_env.diagnostics if d.severity == "error"]
                if error_codes and all(
                    code.startswith("PRG-VALIDATION-") or code.startswith("PRG-NORMALIZATION-")
                    for code in error_codes
                ):
                    return ClosedLoopResult(
                        status="BLOCKED",
                        evidence_bundle={},
                        envelope=compile_env,
                        diagnostics=error_codes,
                    )
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
        if hooks is not None and hooks.force_security_weaken_repair and attempt_index > 0:
            security_ok = False

        eval_result = evaluate_deterministic(
            EvaluationRequest(
                baseline_digest=baseline_digest,
                candidate_digest=candidate_digest,
                compile_ok=compile_ok,
                security_ok=security_ok,
                network_used=False,
                baseline_required=bool(current_ir["evaluation"].get("baseline_required", False)),
            )
        )
        evaluation = _evaluation_result_to_evidence(eval_result)
        final_eval = evaluation
        final_evaluator_id = eval_result.evaluator_id
        final_evaluator_version = eval_result.evaluator_version
        deterministic_stage = {
            **evaluation,
            "evaluator": {"id": eval_result.evaluator_id, "version": eval_result.evaluator_version},
            "attempt_index": attempt_index,
        }
        if pending_repair is not None:
            pending_repair["outcome"] = _repair_outcome(pending_prior_status or "", evaluation["status"])
            failed_attempts.append(pending_repair)
            pending_repair = None
            pending_prior_status = None

        if evaluation["status"] == "PASS":
            if attempt_index > 0:
                terminal_reason = "passed_after_repair"
            if options.product_eval is not None:
                product_stage, product_eval = _run_product_stage(
                    options.product_eval, candidate_digest, mandatory_requirement_ids
                )
                final_eval = product_eval
                final_evaluator_id = product_stage["evaluator"]["id"]
                final_evaluator_version = product_stage["evaluator"]["version"]
                binding = product_stage["candidate_binding"]
                if product_eval["status"] == "PASS" and binding != BINDING_BOUND:
                    final_eval = {
                        **product_eval,
                        "status": "BLOCKED",
                        "diagnostic_codes": [
                            *product_eval["diagnostic_codes"],
                            f"{CANDIDATE_UNBOUND}: product observations are {binding}; candidate PASS withheld "
                            f"until every dataset row declares candidate_digest {candidate_digest}",
                        ],
                        "scores": {"primary": None},
                    }
                    terminal_reason = "blocked_unbound_observations"
                elif product_eval["status"] != "PASS":
                    if product_eval["status"] in {"FAIL", "REGRESSION"}:
                        if options.repair_budget - attempt_index > 0:
                            terminal_reason = "repair_unsupported_imported_observations"
                            extra_diagnostics.append(REPAIR_UNSUPPORTED)
                        else:
                            terminal_reason = "repair_budget_exhausted"
                    else:
                        terminal_reason = "blocked_before_repair"
            break

        if attempt_index >= attempts_allowed:
            terminal_reason = "repair_budget_exhausted" if attempts_allowed > 0 else "repair_budget_zero"
            break

        weaken_security = hooks is not None and hooks.force_security_weaken_repair
        repair_plan = plan_repair(attempt_index=attempt_index, weaken_security=weaken_security)
        if not repair_plan.allowed:
            failed_attempts.append(
                {
                    "attempt_id": f"RPA-{attempt_index}",
                    "attempt_index": attempt_index,
                    "mutation_summary": repair_plan.mutation_summary,
                    "allowed_mutation": False,
                    "outcome": "refused_immutable",
                    "preserved_failed_evidence": True,
                    "weakened_security_or_objective": True,
                    "diagnostic_codes": list(repair_plan.diagnostic_codes),
                }
            )
            final_eval = {
                "status": "BLOCKED",
                "diagnostic_codes": list(repair_plan.diagnostic_codes),
                "scores": {"primary": 0.0},
            }
            terminal_reason = "refused_immutable"
            break

        current_ir = apply_instruction_repair(current_ir, attempt_index)
        assert current_ir["objective"]["success_criteria"] == accepted_objectives
        assert current_ir["behavior"]["constraints"] == security_constraints
        assert [r["id"] for r in current_ir["requirements"]] == requirement_ids
        current_raw = canonicalize(current_ir)
        pending_prior_status = evaluation["status"]
        pending_repair = {
            "attempt_id": f"RPA-{attempt_index}",
            "attempt_index": attempt_index,
            "mutation_summary": repair_plan.mutation_summary,
            "allowed_mutation": True,
            "outcome": "no_change",
            "preserved_failed_evidence": True,
            "weakened_security_or_objective": False,
            "diagnostic_codes": [],
        }

    assert final_eval is not None
    if extra_diagnostics:
        final_eval = {
            **final_eval,
            "diagnostic_codes": list(dict.fromkeys([*final_eval.get("diagnostic_codes", []), *extra_diagnostics])),
        }
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

    evidence = build_evidence_bundle(
        requirement_ids=requirement_ids,
        immutable_fields=IMMUTABLE_FIELDS,
        adapter={"id": FAKE_ADAPTER_ID, "version": FAKE_ADAPTER_VERSION},
        ir_sha256=canonical_sha256(current_ir),
        baseline_digest=baseline_digest,
        evaluation=final_eval,
        failed_attempts=failed_attempts,
        unresolved_defect=unresolved,
        network_allowed=False,
        network_used=False,
        repair_budget=options.repair_budget,
        compile_status=None if compile_env is None else compile_env.status,
        evaluator_id=final_evaluator_id,
        evaluator_version=final_evaluator_version,
        intake_profile=intake_profile,
        model_proposal=model_proposal,
        suggestion_profile=SUGGESTION_PROFILE if model_proposal is not None else None,
        candidate_digest=candidate_digest,
        requirement_coverage=None if product_stage is None else product_stage["requirement_coverage"],
        stages={
            "compile": {
                "status": None if compile_env is None else compile_env.status,
                "adapter": {"id": FAKE_ADAPTER_ID, "version": FAKE_ADAPTER_VERSION},
            },
            "deterministic_evaluation": deterministic_stage,
            "product_evaluation": product_stage,
            "repair": {
                "budget": options.repair_budget,
                "attempted": sum(1 for a in failed_attempts if a.get("allowed_mutation")),
                "terminal_reason": terminal_reason,
            },
        },
        evidence_classes=["structural_compile_check"]
        + ([] if product_stage is None else ["imported_observation_check"]),
        not_measured=["live_model_output"]
        + ([] if product_stage is not None and product_stage["candidate_binding"] == BINDING_BOUND else ["semantic_quality"]),
    )

    return ClosedLoopResult(
        status=status,
        evidence_bundle=evidence,
        envelope=compile_env,
        failed_attempts=failed_attempts,
        diagnostics=list(final_eval.get("diagnostic_codes", [])),
        model_proposal=model_proposal,
    )


def closed_loop_from_json(
    raw: bytes | str,
    options: ClosedLoopOptions | None = None,
    hooks: ClosedLoopTestHooks | None = None,
) -> ClosedLoopResult:
    size = len(raw) if isinstance(raw, (bytes, bytearray)) else len(raw.encode("utf-8"))
    if size > MAX_INPUT_BYTES:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=["EVR-RES-0001"])
    try:
        doc = parse_json_object(raw)
    except IntakeError as exc:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=[exc.diagnostic])
    top_level_errors = [
        f"{INP_TYPE}: {key} must be true or false"
        for key in ("network_allowed", "enable_model_suggestions")
        if key in doc and not isinstance(doc[key], bool)
    ]
    if top_level_errors:
        return ClosedLoopResult(status="BLOCKED", evidence_bundle={}, diagnostics=top_level_errors)
    options = options or ClosedLoopOptions()
    enable_from_doc = doc.pop("enable_model_suggestions", None) is True
    if enable_from_doc:
        options = ClosedLoopOptions(
            repair_budget=options.repair_budget,
            network_allowed=options.network_allowed,
            enable_model_suggestions=True,
            product_eval=options.product_eval,
        )

    if options.network_allowed or doc.get("network_allowed") is True:
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=["EVR-NET-0001"],
        )

    if doc.get("authoring_mode") == "simple_ui_only" or doc.get("profile") == "simple_mode_ui":
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=[SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC],
        )

    if "requirements_document" in doc and "profile" not in doc:
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=[REQUIREMENTS_CONTRACT_USE_COMPILE_COMMAND],
        )

    profile = doc.get("profile")
    if profile == PLAIN_LANGUAGE_INTAKE_PROFILE:
        prose = doc.get("text")
        if not isinstance(prose, str):
            return ClosedLoopResult(
                status="BLOCKED",
                evidence_bundle={},
                diagnostics=["PL-PARSE-0002"],
            )
        try:
            structured = parse_plain_language_v0(prose)
        except PlainLanguageParseError as exc:
            return ClosedLoopResult(
                status="BLOCKED",
                evidence_bundle={},
                diagnostics=[exc.code],
            )
        if "repair_budget" in doc:
            structured["repair_budget"] = doc["repair_budget"]
        return run_closed_loop(
            structured,
            options,
            hooks,
            intake_profile=PLAIN_LANGUAGE_INTAKE_PROFILE,
        )

    return run_closed_loop(doc, options, hooks)
