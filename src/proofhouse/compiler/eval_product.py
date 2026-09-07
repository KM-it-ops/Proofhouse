from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .eval_aggregate import Aggregation, aggregate_scores
from .eval_dataset import load_dataset
from .eval_rubric import load_rubric, score_case
from .evaluation import EvaluationRequest, evaluate_deterministic

PRODUCT_EVALUATOR_ID = "evr-product-v1"
PRODUCT_EVALUATOR_VERSION = "0.1.0"


@dataclass(frozen=True)
class ProductEvalRequest:
    baseline_digest: str | None
    candidate_digest: str
    dataset_path: Path
    rubric_path: Path
    aggregation: Aggregation
    baseline_required: bool
    baseline_primary: float | None
    network_used: bool
    compile_ok: bool
    security_ok: bool
    baseline_stale: bool = False


@dataclass(frozen=True)
class ProductEvaluationResult:
    status: str
    diagnostic_codes: tuple[str, ...]
    scores: dict[str, float | None]
    evaluator_id: str
    evaluator_version: str
    authoritative: bool
    aggregation: str
    failed_attempts: tuple[dict[str, object], ...]
    req_ids: tuple[str, ...]


def evaluate_product(request: ProductEvalRequest) -> ProductEvaluationResult:
    oracle = evaluate_deterministic(
        EvaluationRequest(
            baseline_digest=request.baseline_digest,
            candidate_digest=request.candidate_digest,
            compile_ok=request.compile_ok,
            security_ok=request.security_ok,
            network_used=request.network_used,
            baseline_required=request.baseline_required,
        )
    )
    if oracle.status != "PASS":
        return ProductEvaluationResult(
            status=oracle.status,
            diagnostic_codes=oracle.diagnostic_codes,
            scores=dict(oracle.scores),
            evaluator_id=oracle.evaluator_id,
            evaluator_version=oracle.evaluator_version,
            authoritative=oracle.authoritative,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=(),
        )
    if request.baseline_stale:
        return ProductEvaluationResult(
            status="BLOCKED",
            diagnostic_codes=("EVR-BSL-0002",),
            scores={"primary": None},
            evaluator_id=PRODUCT_EVALUATOR_ID,
            evaluator_version=PRODUCT_EVALUATOR_VERSION,
            authoritative=True,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=(),
        )

    cases = load_dataset(request.dataset_path)
    rubric = load_rubric(request.rubric_path)
    merged: dict[str, float | None] = {}
    req_ids: list[str] = []
    for case in cases:
        req_ids.extend(case.req_ids)
        for key, value in score_case(rubric, case).items():
            slot = f"{case.case_id}:{key}"
            merged[slot] = value

    primary, codes = aggregate_scores(merged, request.aggregation)
    if "EVR-SCR-0001" in codes:
        return ProductEvaluationResult(
            status="ERROR",
            diagnostic_codes=codes,
            scores={"primary": None},
            evaluator_id=PRODUCT_EVALUATOR_ID,
            evaluator_version=PRODUCT_EVALUATOR_VERSION,
            authoritative=True,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=tuple(dict.fromkeys(req_ids)),
        )

    status = "PASS" if primary == 1.0 else "FAIL"
    if (
        request.baseline_required
        and request.baseline_primary is not None
        and primary is not None
        and primary < request.baseline_primary
    ):
        status = "REGRESSION"

    return ProductEvaluationResult(
        status=status,
        diagnostic_codes=codes,
        scores={"primary": primary},
        evaluator_id=PRODUCT_EVALUATOR_ID,
        evaluator_version=PRODUCT_EVALUATOR_VERSION,
        authoritative=True,
        aggregation=request.aggregation,
        failed_attempts=(),
        req_ids=tuple(dict.fromkeys(req_ids)),
    )
