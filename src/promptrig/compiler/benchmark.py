"""Sealed offline whole-configuration benchmark (MISSION-033).

Offline-only. Oracle ``evaluate_deterministic`` is the rank-1
compile/security/network gate. Product eval is the published scorer.
Hidden tests stay on the runner, not on the scored configuration.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import jsonschema

from .canonical import canonical_sha256
from .eval_product import ProductEvalRequest, evaluate_product
from .evaluation import EvaluationRequest, evaluate_deterministic

MANIFEST_VERSION = "0.1.0"
BENCHMARK_ID_DEFAULT = "promptrig-sealed-offline-v0.1"
REPAIR_BUDGETS = (0, 1, 2)
DEFAULT_AUTONOMOUS_ATTEMPTS = 3
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "architecture"
    / "sealed-benchmark-v0.1"
    / "benchmark-manifest.schema.json"
)
_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "sk-live",
    "sk-proj-",
    "begin private key",
    "authorization: bearer",
    "aws_secret_access_key",
)


class ManifestValidationError(ValueError):
    def __init__(self, codes: tuple[str, ...], message: str = "") -> None:
        self.codes = codes
        super().__init__(message or ",".join(codes))


@dataclass(frozen=True)
class ValidatedManifest:
    payload: dict[str, Any]
    network_allowed: bool
    network_mode: str
    autonomous_attempts: int
    environment_digest: str
    source_hashes: dict[str, str]


@dataclass(frozen=True)
class ScoredConfiguration:
    config_id: str
    source: bytes
    compile_ok: bool
    security_ok: bool
    network_used: bool


@dataclass(frozen=True)
class SealedEvidence:
    environment_digest: str
    source_hashes: dict[str, str]
    oracle_status: str
    oracle_codes: tuple[str, ...]
    product_eval_status: str | None
    classification: str
    published_status: str
    scores_by_config: dict[str, float | None]
    score_checksum: str


@dataclass(frozen=True)
class BenchmarkRunResult:
    classification: str
    published_status: str
    diagnostic_codes: tuple[str, ...]
    oracle_codes: tuple[str, ...]
    product_eval_status: str | None
    scores_by_config: dict[str, float | None]
    score_checksum: str
    autonomous_attempts: int
    attempts: dict[str, tuple[dict[str, object], ...]]
    config_accessible_paths: frozenset[Path]
    sealed: SealedEvidence


def source_sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_PATH.is_file():
        raise ManifestValidationError(
            ("BMK-MAN-0001",),
            f"benchmark manifest schema missing: {_SCHEMA_PATH}",
        )
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _looks_like_secret(source: bytes) -> bool:
    text = source.decode("utf-8", errors="replace").lower()
    return any(marker in text for marker in _SECRET_MARKERS)


def _oracle_security_failed(oracle_codes: tuple[str, ...]) -> bool:
    return "EVR-SEC-0001" in oracle_codes


def validate_benchmark_manifest(
    manifest: dict[str, Any],
    *,
    sources: Mapping[str, bytes],
) -> ValidatedManifest:
    if not isinstance(manifest, dict):
        raise ManifestValidationError(("BMK-MAN-0001",), "manifest must be an object")

    codes: list[str] = []
    network_mode = manifest.get("network_mode")
    network_allowed = manifest.get("network_allowed")
    if network_mode != "offline" or network_allowed is not False:
        codes.append("BMK-NET-0001")
    budgets = manifest.get("budgets")
    if isinstance(budgets, dict) and tuple(budgets.get("repair") or ()) != REPAIR_BUDGETS:
        codes.append("BMK-BUD-0001")

    try:
        jsonschema.Draft202012Validator(_load_schema()).validate(manifest)
    except jsonschema.ValidationError as exc:
        codes.append("BMK-MAN-0001")
        raise ManifestValidationError(tuple(dict.fromkeys(codes)), str(exc)) from exc

    if codes:
        raise ManifestValidationError(tuple(dict.fromkeys(codes)))

    repair = tuple(manifest["budgets"]["repair"])
    attempts = int(manifest["repetition"]["autonomous_attempts"])
    budget_attempts = int(manifest["budgets"]["autonomous_attempts"])
    ratified = bool(manifest["repetition"]["owner_ratified_smaller_budget"])
    note = str(manifest["repetition"]["owner_ratification_note"]).strip()
    if repair != REPAIR_BUDGETS or attempts != budget_attempts:
        raise ManifestValidationError(("BMK-BUD-0001",), "illegal repair or repetition budget")
    if attempts < DEFAULT_AUTONOMOUS_ATTEMPTS and not (ratified and note):
        raise ManifestValidationError(
            ("BMK-BUD-0001",),
            "autonomous attempts default to 3 unless owner-ratified with a note",
        )

    declared = dict(manifest["source_hashes"])
    if set(declared) != set(sources):
        raise ManifestValidationError(("BMK-HASH-0001",), "source id set mismatch")
    for config_id, blob in sources.items():
        if declared[config_id] != source_sha256(blob):
            raise ManifestValidationError(("BMK-HASH-0001",), f"source hash mismatch: {config_id}")
        if _looks_like_secret(blob):
            raise ManifestValidationError(("BMK-SEC-0001",), f"secrets policy violated: {config_id}")

    return ValidatedManifest(
        payload=dict(manifest),
        network_allowed=False,
        network_mode="offline",
        autonomous_attempts=attempts,
        environment_digest=str(manifest["environment_digest"]),
        source_hashes=declared,
    )


def seal_evidence(
    *,
    environment_digest: str,
    source_hashes: Mapping[str, str],
    oracle_status: str,
    oracle_codes: tuple[str, ...],
    product_eval_status: str | None,
    classification: str,
    published_status: str,
    scores_by_config: Mapping[str, float | None],
) -> SealedEvidence:
    if _oracle_security_failed(oracle_codes) and (
        product_eval_status == "PASS" or published_status == "PASS"
    ):
        raise ManifestValidationError(
            ("BMK-ORC-0001",),
            "oracle security failure cannot be published as a product-eval PASS",
        )
    checksum = canonical_sha256(
        {
            "environment_digest": environment_digest,
            "source_hashes": dict(sorted(source_hashes.items())),
            "scores_by_config": {
                key: scores_by_config[key] for key in sorted(scores_by_config)
            },
            "published_status": published_status,
            "classification": classification,
        }
    )
    return SealedEvidence(
        environment_digest=environment_digest,
        source_hashes=dict(source_hashes),
        oracle_status=oracle_status,
        oracle_codes=oracle_codes,
        product_eval_status=product_eval_status,
        classification=classification,
        published_status=published_status,
        scores_by_config=dict(scores_by_config),
        score_checksum=checksum,
    )


def run_sealed_benchmark(
    manifest: dict[str, Any],
    *,
    sources: Mapping[str, bytes],
    configs: tuple[ScoredConfiguration, ...],
    hidden_dataset_path: Path,
    hidden_rubric_path: Path,
) -> BenchmarkRunResult:
    validated = validate_benchmark_manifest(manifest, sources=sources)
    if {config.config_id for config in configs} != set(sources):
        raise ManifestValidationError(("BMK-HASH-0001",), "config ids must match sources")
    for config in configs:
        if sources[config.config_id] != config.source:
            raise ManifestValidationError(("BMK-HASH-0001",), "config source bytes mismatch")

    if not hidden_dataset_path.is_file() or not hidden_rubric_path.is_file():
        sealed = seal_evidence(
            environment_digest=validated.environment_digest,
            source_hashes=validated.source_hashes,
            oracle_status="ERROR",
            oracle_codes=(),
            product_eval_status=None,
            classification="infrastructure",
            published_status="INFRA",
            scores_by_config={config.config_id: None for config in configs},
        )
        return BenchmarkRunResult(
            classification="infrastructure",
            published_status="INFRA",
            diagnostic_codes=("BMK-INF-0001",),
            oracle_codes=(),
            product_eval_status=None,
            scores_by_config=sealed.scores_by_config,
            score_checksum=sealed.score_checksum,
            autonomous_attempts=validated.autonomous_attempts,
            attempts={config.config_id: () for config in configs},
            config_accessible_paths=frozenset(),
            sealed=sealed,
        )

    oracle_codes: list[str] = []
    oracle_status = "PASS"
    product_eval_status: str | None = None
    scores: dict[str, float | None] = {}
    attempts: dict[str, tuple[dict[str, object], ...]] = {}
    classification = "product"
    published_status = "PASS"

    try:
        for config in configs:
            oracle = evaluate_deterministic(
                EvaluationRequest(
                    baseline_digest=None,
                    candidate_digest=source_sha256(config.source),
                    compile_ok=config.compile_ok,
                    security_ok=config.security_ok,
                    network_used=config.network_used,
                    baseline_required=False,
                )
            )
            oracle_codes.extend(oracle.diagnostic_codes)
            attempt_rows: list[dict[str, object]] = []
            last_product = None
            for attempt_index in range(validated.autonomous_attempts):
                product = evaluate_product(
                    ProductEvalRequest(
                        baseline_digest=None,
                        candidate_digest=source_sha256(config.source),
                        dataset_path=hidden_dataset_path,
                        rubric_path=hidden_rubric_path,
                        aggregation="any_fail",
                        baseline_required=False,
                        baseline_primary=None,
                        network_used=config.network_used,
                        compile_ok=config.compile_ok,
                        security_ok=config.security_ok,
                    )
                )
                last_product = product
                attempt_rows.append(
                    {
                        "attempt": attempt_index + 1,
                        "oracle_status": oracle.status,
                        "product_status": product.status,
                        "primary": product.scores.get("primary"),
                    }
                )
            assert last_product is not None
            product_eval_status = last_product.status
            scores[config.config_id] = last_product.scores.get("primary")
            attempts[config.config_id] = tuple(attempt_rows)
            if _oracle_security_failed(oracle.diagnostic_codes) or oracle.status != "PASS":
                oracle_status = oracle.status
                classification = "oracle_gate"
                published_status = oracle.status
                product_eval_status = last_product.status
                if product_eval_status == "PASS":
                    raise ManifestValidationError(
                        ("BMK-ORC-0001",),
                        "oracle security failure cannot be published as a product-eval PASS",
                    )
            elif last_product.status != "PASS":
                published_status = last_product.status
                classification = "product"
    except (OSError, ValueError, json.JSONDecodeError):
        sealed = seal_evidence(
            environment_digest=validated.environment_digest,
            source_hashes=validated.source_hashes,
            oracle_status="ERROR",
            oracle_codes=tuple(dict.fromkeys(oracle_codes)),
            product_eval_status=None,
            classification="infrastructure",
            published_status="INFRA",
            scores_by_config={config.config_id: None for config in configs},
        )
        return BenchmarkRunResult(
            classification="infrastructure",
            published_status="INFRA",
            diagnostic_codes=("BMK-INF-0001",),
            oracle_codes=tuple(dict.fromkeys(oracle_codes)),
            product_eval_status=None,
            scores_by_config=sealed.scores_by_config,
            score_checksum=sealed.score_checksum,
            autonomous_attempts=validated.autonomous_attempts,
            attempts={config.config_id: () for config in configs},
            config_accessible_paths=frozenset(),
            sealed=sealed,
        )

    unique_oracle = tuple(dict.fromkeys(oracle_codes))
    if published_status == "PASS" and classification == "oracle_gate":
        published_status = "BLOCKED"
    sealed = seal_evidence(
        environment_digest=validated.environment_digest,
        source_hashes=validated.source_hashes,
        oracle_status=oracle_status,
        oracle_codes=unique_oracle,
        product_eval_status=product_eval_status,
        classification=classification,
        published_status=published_status,
        scores_by_config=scores,
    )
    return BenchmarkRunResult(
        classification=classification,
        published_status=published_status,
        diagnostic_codes=unique_oracle,
        oracle_codes=unique_oracle,
        product_eval_status=product_eval_status,
        scores_by_config=scores,
        score_checksum=sealed.score_checksum,
        autonomous_attempts=validated.autonomous_attempts,
        attempts=attempts,
        config_accessible_paths=frozenset(),
        sealed=sealed,
    )
