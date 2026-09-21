"""Product evaluation over imported observations (datasets + rubric).

The observations are caller-supplied: they were not produced by the
candidate during this evaluation. Results therefore carry the exact dataset
and rubric digests, a per-case result table, requirement coverage, and how
(or whether) the observations are bound to the candidate digest (T03,
review F02/F03).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .eval_aggregate import Aggregation, aggregate_scores
from .eval_dataset import DatasetCase, load_dataset
from .eval_rubric import load_rubric, score_case
from .evaluation import EvaluationRequest, evaluate_deterministic

PRODUCT_EVALUATOR_ID = "evr-product-v1"
PRODUCT_EVALUATOR_VERSION = "0.2.0"
OBSERVATION_SOURCE_IMPORTED = "imported"

COVERAGE_MISSING = "EVR-COV-0001"
BINDING_MISMATCH = "EVR-BND-0001"

BINDING_UNBOUND = "unbound"
BINDING_BOUND = "bound"
BINDING_PARTIAL = "partially_bound"
BINDING_MISMATCH_STATE = "mismatch"


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
    # Requirement ids the dataset must cover; missing coverage blocks the result.
    required_req_ids: tuple[str, ...] = ()


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
    case_results: tuple[dict[str, Any], ...] = ()
    candidate_digest: str | None = None
    candidate_binding: str | None = None
    observation_source: str = OBSERVATION_SOURCE_IMPORTED
    dataset_sha256: str | None = None
    rubric_sha256: str | None = None
    rubric_id: str | None = None
    rubric_version: str | None = None
    requirement_coverage: dict[str, list[str]] | None = field(default=None)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(cases: tuple[DatasetCase, ...], candidate_digest: str) -> str:
    declared = [case.candidate_digest for case in cases if case.candidate_digest is not None]
    if any(digest != candidate_digest for digest in declared):
        return BINDING_MISMATCH_STATE
    if not declared:
        return BINDING_UNBOUND
    return BINDING_BOUND if len(declared) == len(cases) else BINDING_PARTIAL


def requirement_coverage(required: tuple[str, ...], observed: tuple[str, ...]) -> dict[str, list[str]]:
    observed_set = set(observed)
    required_set = set(required)
    return {
        "required": sorted(required_set),
        "covered": sorted(required_set & observed_set),
        "missing": sorted(required_set - observed_set),
        "not_declared": sorted(observed_set - required_set) if required_set else [],
    }


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
    req_ids = tuple(dict.fromkeys(req_id for case in cases for req_id in case.req_ids))
    common: dict[str, Any] = dict(
        evaluator_id=PRODUCT_EVALUATOR_ID,
        evaluator_version=PRODUCT_EVALUATOR_VERSION,
        authoritative=True,
        aggregation=request.aggregation,
        failed_attempts=(),
        req_ids=req_ids,
        candidate_digest=request.candidate_digest,
        candidate_binding=_binding(cases, request.candidate_digest),
        dataset_sha256=_sha256(request.dataset_path),
        rubric_sha256=_sha256(request.rubric_path),
        rubric_id=rubric.rubric_id,
        rubric_version=rubric.version,
        requirement_coverage=requirement_coverage(tuple(request.required_req_ids), req_ids),
    )

    # Structured (case_id, criterion_id) keys: no string concatenation, no collisions.
    rows: list[dict[str, Any]] = []
    merged: dict[tuple[str, str], float | None] = {}
    for case in cases:
        for criterion_id, value in score_case(rubric, case).items():
            merged[(case.case_id, criterion_id)] = value
            rows.append({"case_id": case.case_id, "criterion_id": criterion_id, "score": value, "req_ids": list(case.req_ids)})
    rows.sort(key=lambda row: (row["case_id"], row["criterion_id"]))
    common["case_results"] = tuple(rows)

    if common["candidate_binding"] == BINDING_MISMATCH_STATE:
        return ProductEvaluationResult(
            status="BLOCKED", diagnostic_codes=(BINDING_MISMATCH,), scores={"primary": None}, **common
        )
    if common["requirement_coverage"]["missing"]:
        return ProductEvaluationResult(
            status="BLOCKED", diagnostic_codes=(COVERAGE_MISSING,), scores={"primary": None}, **common
        )

    primary, codes = aggregate_scores(merged, request.aggregation)
    if "EVR-SCR-0001" in codes:
        return ProductEvaluationResult(status="ERROR", diagnostic_codes=codes, scores={"primary": None}, **common)

    status = "PASS" if primary == 1.0 else "FAIL"
    if (
        request.baseline_required
        and request.baseline_primary is not None
        and primary is not None
        and primary < request.baseline_primary
    ):
        status = "REGRESSION"

    return ProductEvaluationResult(status=status, diagnostic_codes=codes, scores={"primary": primary}, **common)
