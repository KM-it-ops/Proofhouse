"""008 SUCCESS/PARTIAL → structured_minimal_v0 → existing closed-loop.

Does not teach ``closed_loop_from_json`` to parse 008 envelopes. Unbridged
canonical 008 JSON on ``closed-loop`` stays ``BLOCKED`` + ``EVR-RQC-0001``.
Does not fork IR compilation: projection builds a structured_minimal_v0
document, then ``requirements_to_ir`` / ``run_closed_loop`` own lowering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .closed_loop import (
    ACCEPTED_INPUT_CONTRACT_VERSIONS,
    ClosedLoopOptions,
    ClosedLoopResult,
    ClosedLoopTestHooks,
    run_closed_loop,
)
from .requirements_contract import compile_requirements

GOAL_POINTER = "/objective/goal"
NON_REPRESENTABLE_DIAGNOSTIC = "EVR-BRG-0001"
_EMITTING_MAPPING_OUTCOMES = frozenset(
    {"direct", "deterministic_derivation", "authorized_default"}
)
_LOWERABLE_STATUSES = frozenset({"SUCCESS", "PARTIAL"})
_INTAKE_PROFILE = "bridged_008"


@dataclass(frozen=True, slots=True)
class Bridge008Result:
    status: str
    reason_codes: tuple[str, ...]
    structured_document: dict[str, Any] | None
    diagnostics: tuple[str, ...] = ()


@dataclass
class BridgedClosedLoopResult:
    status: str
    requirements_compile_status: str
    evidence_bundle: dict[str, Any]
    diagnostics: list[str] = field(default_factory=list)
    envelope: Any = None
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    structured_document: dict[str, Any] | None = None
    closed_loop: ClosedLoopResult | None = None
    reason_codes: tuple[str, ...] = ()


def _requirement_statement(requirements: list[Any], requirement_id: str) -> str | None:
    for req in requirements:
        if not isinstance(req, dict):
            continue
        if req.get("id") == requirement_id:
            statement = req.get("statement")
            if isinstance(statement, str) and statement:
                return statement
            return None
    return None


def _project_structured_minimal(artifacts: Mapping[str, Any]) -> dict[str, Any] | None:
    document = artifacts.get("requirements_document")
    if not isinstance(document, Mapping):
        return None
    raw_requirements = document.get("requirements")
    if not isinstance(raw_requirements, list) or not raw_requirements:
        return None
    mappings = artifacts.get("mappings")
    if not isinstance(mappings, list):
        mappings = []

    goal_mapping = next(
        (
            mapping
            for mapping in mappings
            if isinstance(mapping, dict)
            and mapping.get("target_pointer") == GOAL_POINTER
            and mapping.get("outcome") in _EMITTING_MAPPING_OUTCOMES
        ),
        None,
    )
    if goal_mapping is None:
        return None
    goal = _requirement_statement(raw_requirements, str(goal_mapping.get("requirement_id", "")))
    if goal is None:
        return None

    requirements: list[dict[str, Any]] = []
    for req in raw_requirements:
        if not isinstance(req, dict):
            continue
        rid = req.get("id")
        statement = req.get("statement")
        if not isinstance(rid, str) or not rid.startswith("REQ-"):
            continue
        if not isinstance(statement, str) or not statement:
            continue
        item: dict[str, Any] = {"id": rid, "statement": statement}
        priority = req.get("priority")
        if isinstance(priority, str) and priority:
            item["priority"] = priority
        requirements.append(item)
    if not requirements:
        return None

    contract_version = document.get("contract_version")
    if contract_version not in ACCEPTED_INPUT_CONTRACT_VERSIONS:
        contract_version = "0.1.0-draft"

    return {
        "profile": "structured_minimal_v0",
        "contract_version": contract_version,
        "objective": {"goal": goal},
        "requirements": requirements,
        "network_allowed": False,
    }


def bridge_008_to_structured(artifacts: Mapping[str, Any] | object) -> Bridge008Result:
    if not isinstance(artifacts, Mapping):
        return Bridge008Result(
            status="INVALID_OUTPUT",
            reason_codes=("RQC-SCH-0001",),
            structured_document=None,
            diagnostics=("RQC-SCH-0001",),
        )
    compiled = compile_requirements(artifacts)
    if compiled.status not in _LOWERABLE_STATUSES:
        return Bridge008Result(
            status=compiled.status,
            reason_codes=compiled.reason_codes,
            structured_document=None,
            diagnostics=compiled.reason_codes,
        )
    structured = _project_structured_minimal(artifacts)
    if structured is None:
        diagnostics = tuple(compiled.reason_codes) + (NON_REPRESENTABLE_DIAGNOSTIC,)
        return Bridge008Result(
            status=compiled.status,
            reason_codes=compiled.reason_codes,
            structured_document=None,
            diagnostics=diagnostics,
        )
    return Bridge008Result(
        status=compiled.status,
        reason_codes=compiled.reason_codes,
        structured_document=structured,
        diagnostics=compiled.reason_codes,
    )


def _blocked_bridge(
    *,
    status: str,
    requirements_compile_status: str,
    diagnostics: list[str],
    reason_codes: tuple[str, ...] = (),
    structured_document: dict[str, Any] | None = None,
) -> BridgedClosedLoopResult:
    return BridgedClosedLoopResult(
        status=status,
        requirements_compile_status=requirements_compile_status,
        evidence_bundle={},
        diagnostics=diagnostics,
        envelope=None,
        structured_document=structured_document,
        reason_codes=reason_codes,
    )


def closed_loop_from_bridged_008(
    artifacts: Mapping[str, Any] | object,
    options: ClosedLoopOptions | None = None,
    hooks: ClosedLoopTestHooks | None = None,
) -> BridgedClosedLoopResult:
    options = options or ClosedLoopOptions()
    if options.network_allowed:
        return _blocked_bridge(
            status="BLOCKED",
            requirements_compile_status="",
            diagnostics=["EVR-NET-0001"],
        )

    bridged = bridge_008_to_structured(artifacts)
    if bridged.status not in _LOWERABLE_STATUSES:
        return _blocked_bridge(
            status=bridged.status,
            requirements_compile_status=bridged.status,
            diagnostics=list(bridged.diagnostics),
            reason_codes=bridged.reason_codes,
        )
    if bridged.structured_document is None:
        return _blocked_bridge(
            status="BLOCKED",
            requirements_compile_status=bridged.status,
            diagnostics=list(bridged.diagnostics),
            reason_codes=bridged.reason_codes,
        )

    loop = run_closed_loop(
        bridged.structured_document,
        options,
        hooks,
        intake_profile=_INTAKE_PROFILE,
    )
    evidence = dict(loop.evidence_bundle) if loop.evidence_bundle else {}
    if evidence:
        evidence["requirements_compile_status"] = bridged.status
    return BridgedClosedLoopResult(
        status=loop.status,
        requirements_compile_status=bridged.status,
        evidence_bundle=evidence,
        diagnostics=list(loop.diagnostics),
        envelope=loop.envelope,
        failed_attempts=list(loop.failed_attempts),
        structured_document=bridged.structured_document,
        closed_loop=loop,
        reason_codes=bridged.reason_codes,
    )
