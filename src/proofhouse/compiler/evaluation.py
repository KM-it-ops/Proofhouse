from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationRequest:
    baseline_digest: str | None
    candidate_digest: str
    compile_ok: bool
    security_ok: bool
    network_used: bool
    baseline_required: bool = False
    evaluator_id: str = "evr-det-compile-security-v1"
    evaluator_version: str = "0.1.0"


@dataclass(frozen=True)
class EvaluationResult:
    status: str
    diagnostic_codes: tuple[str, ...]
    scores: dict[str, float | None]
    evaluator_id: str
    evaluator_version: str
    authoritative: bool


def evaluate_deterministic(request: EvaluationRequest) -> EvaluationResult:
    evaluator_id = request.evaluator_id
    evaluator_version = request.evaluator_version

    if request.network_used:
        return EvaluationResult(
            status="BLOCKED",
            diagnostic_codes=("EVR-NET-0001",),
            scores={"primary": None},
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
            authoritative=True,
        )

    if not request.compile_ok:
        return EvaluationResult(
            status="FAIL",
            diagnostic_codes=("EVR-DET-0001",),
            scores={"primary": 0.0},
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
            authoritative=True,
        )

    if not request.security_ok:
        return EvaluationResult(
            status="BLOCKED",
            diagnostic_codes=("EVR-SEC-0001",),
            scores={"primary": 0.0},
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
            authoritative=True,
        )

    if request.baseline_required and not request.baseline_digest:
        return EvaluationResult(
            status="BLOCKED",
            diagnostic_codes=("EVR-BSL-0001",),
            scores={"primary": None},
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
            authoritative=True,
        )

    return EvaluationResult(
        status="PASS",
        diagnostic_codes=(),
        scores={"primary": 1.0},
        evaluator_id=evaluator_id,
        evaluator_version=evaluator_version,
        authoritative=True,
    )
