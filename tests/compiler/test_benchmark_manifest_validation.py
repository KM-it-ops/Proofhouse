"""MISSION-033 sealed offline benchmark: manifest validation, then runner/sealer.

Offline-only track. Hidden tests stay off the scored configuration. Oracle
``evaluate_deterministic`` is the rank-1 compile/security/network gate.
Product eval (U2 / ``evaluate-product`` CLI) is the published scorer.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from proofhouse.compiler.benchmark import (
    ManifestValidationError,
    ScoredConfiguration,
    seal_evidence,
    source_sha256,
    validate_benchmark_manifest,
    run_sealed_benchmark,
)


def _hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _write_jsonl(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_rubric(path: Path) -> Path:
    path.write_text(
        '{"rubric_id": "evr-product-v1", "version": "0.1.0", '
        '"criteria": [{"criterion_id": "compile", "field": "compile_ok", "expected": true},'
        '{"criterion_id": "security", "field": "security_ok", "expected": true}]}\n',
        encoding="utf-8",
    )
    return path


def _valid_manifest(
    sources: dict[str, bytes],
    *,
    environment_digest: str = "sha256:" + ("ab" * 32),
    **overrides: Any,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "manifest_version": "0.1.0",
        "benchmark_id": "promptrig-sealed-offline-v0.1",
        "network_mode": "offline",
        "network_allowed": False,
        "environment_digest": environment_digest,
        "source_hashes": {
            config_id: source_sha256(blob) for config_id, blob in sources.items()
        },
        "secrets_policy": {
            "credentials": "forbidden",
            "in_artifacts": False,
            "in_repository": False,
        },
        "budgets": {"repair": [0, 1, 2], "autonomous_attempts": 3},
        "repetition": {
            "autonomous_attempts": 3,
            "owner_ratified_smaller_budget": False,
            "owner_ratification_note": "",
        },
        "starter_commit": "bfb091b4d8e24a106c9f28e50ff8f0da983a0b9d",
        "permissions": {"network": "deny", "credentials": "deny"},
        "intervention_policy": "autonomous",
        "contamination_controls": {
            "hidden_tests_inaccessible": True,
            "public_tests_only_for_config": True,
        },
        "scoring": {
            "oracle": "evaluate_deterministic",
            "published_scorer": "evaluate_product",
        },
        "marketing_claims_policy": "forbidden_until_owner_authorized_dry_run",
    }
    manifest.update(overrides)
    return manifest


def _passing_hidden(tmp_path: Path) -> tuple[Path, Path]:
    dataset = _write_jsonl(
        tmp_path / "hidden.jsonl",
        [
            '{"case_id": "HID-001", "req_ids": ["REQ-BMK-001"], '
            '"observations": {"compile_ok": true, "security_ok": true}}'
        ],
    )
    rubric = _write_rubric(tmp_path / "hidden_rubric.json")
    return dataset, rubric


def test_valid_manifest_accepts() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    validated = validate_benchmark_manifest(_valid_manifest(sources), sources=sources)
    assert validated.network_allowed is False
    assert validated.network_mode == "offline"
    assert validated.autonomous_attempts == 3


def test_mutated_source_hash_fails_validation() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(sources)
    manifest["source_hashes"] = {"alpha": "sha256:" + ("00" * 32)}
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-HASH-0001" in exc.value.codes


def test_network_allowed_true_rejected() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(sources, network_allowed=True)
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-NET-0001" in exc.value.codes


def test_non_offline_network_mode_rejected() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(sources, network_mode="live")
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-NET-0001" in exc.value.codes


def test_missing_environment_digest_fails() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(sources)
    del manifest["environment_digest"]
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-MAN-0001" in exc.value.codes


def test_secret_material_in_source_fails_policy() -> None:
    sources = {"alpha": b'{"api_key":"sk-live-not-a-real-secret"}'}
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(_valid_manifest(sources), sources=sources)
    assert "BMK-SEC-0001" in exc.value.codes


def test_repetition_below_three_without_ratification_fails() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(
        sources,
        repetition={
            "autonomous_attempts": 1,
            "owner_ratified_smaller_budget": False,
            "owner_ratification_note": "",
        },
        budgets={"repair": [0, 1, 2], "autonomous_attempts": 1},
    )
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-BUD-0001" in exc.value.codes


def test_owner_ratified_smaller_budget_documented() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(
        sources,
        repetition={
            "autonomous_attempts": 1,
            "owner_ratified_smaller_budget": True,
            "owner_ratification_note": "owner-ratifiable smaller budget for fixture cost",
        },
        budgets={"repair": [0, 1, 2], "autonomous_attempts": 1},
    )
    validated = validate_benchmark_manifest(manifest, sources=sources)
    assert validated.autonomous_attempts == 1


def test_repair_budgets_must_remain_0_1_2() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    manifest = _valid_manifest(
        sources, budgets={"repair": [0, 1, 2, 3], "autonomous_attempts": 3}
    )
    with pytest.raises(ManifestValidationError) as exc:
        validate_benchmark_manifest(manifest, sources=sources)
    assert "BMK-BUD-0001" in exc.value.codes


def test_two_identical_configs_same_sealed_env_scores_match(tmp_path: Path) -> None:
    blob = b'{"config":"same"}'
    sources = {"alpha": blob, "beta": blob}
    hidden, rubric = _passing_hidden(tmp_path)
    manifest = _valid_manifest(sources)
    configs = (
        ScoredConfiguration(
            config_id="alpha",
            source=blob,
            compile_ok=True,
            security_ok=True,
            network_used=False,
        ),
        ScoredConfiguration(
            config_id="beta",
            source=blob,
            compile_ok=True,
            security_ok=True,
            network_used=False,
        ),
    )
    first = run_sealed_benchmark(
        manifest,
        sources=sources,
        configs=configs,
        hidden_dataset_path=hidden,
        hidden_rubric_path=rubric,
    )
    second = run_sealed_benchmark(
        manifest,
        sources=sources,
        configs=configs,
        hidden_dataset_path=hidden,
        hidden_rubric_path=rubric,
    )
    assert first.classification == "product"
    assert first.scores_by_config == second.scores_by_config
    assert first.scores_by_config["alpha"] == first.scores_by_config["beta"]
    assert first.score_checksum == second.score_checksum


def test_infrastructure_failure_classified_separately_from_product_fail(
    tmp_path: Path,
) -> None:
    blob = b'{"config":"alpha"}'
    sources = {"alpha": blob}
    hidden, rubric = _passing_hidden(tmp_path)
    failing = _write_jsonl(
        tmp_path / "failing.jsonl",
        [
            '{"case_id": "HID-FAIL", "req_ids": ["REQ-BMK-001"], '
            '"observations": {"compile_ok": false, "security_ok": true}}'
        ],
    )
    config = ScoredConfiguration(
        config_id="alpha",
        source=blob,
        compile_ok=True,
        security_ok=True,
        network_used=False,
    )
    product = run_sealed_benchmark(
        _valid_manifest(sources),
        sources=sources,
        configs=(config,),
        hidden_dataset_path=failing,
        hidden_rubric_path=rubric,
    )
    assert product.classification == "product"
    assert product.published_status == "FAIL"

    missing = tmp_path / "missing-hidden.jsonl"
    infra = run_sealed_benchmark(
        _valid_manifest(sources),
        sources=sources,
        configs=(config,),
        hidden_dataset_path=missing,
        hidden_rubric_path=rubric,
    )
    assert infra.classification == "infrastructure"
    assert infra.published_status == "INFRA"
    assert "BMK-INF-0001" in infra.diagnostic_codes
    assert infra.published_status != product.published_status


def test_oracle_security_failure_cannot_publish_product_eval_pass(
    tmp_path: Path,
) -> None:
    blob = b'{"config":"insecure"}'
    sources = {"alpha": blob}
    hidden, rubric = _passing_hidden(tmp_path)
    result = run_sealed_benchmark(
        _valid_manifest(sources),
        sources=sources,
        configs=(
            ScoredConfiguration(
                config_id="alpha",
                source=blob,
                compile_ok=True,
                security_ok=False,
                network_used=False,
            ),
        ),
        hidden_dataset_path=hidden,
        hidden_rubric_path=rubric,
    )
    assert "EVR-SEC-0001" in result.oracle_codes
    assert result.published_status != "PASS"
    assert result.product_eval_status != "PASS"
    assert result.classification == "oracle_gate"


def test_sealer_rejects_forged_product_pass_on_oracle_security() -> None:
    with pytest.raises(ManifestValidationError) as exc:
        seal_evidence(
            environment_digest="sha256:" + ("ab" * 32),
            source_hashes={"alpha": _hash_bytes(b'{"config":"alpha"}')},
            oracle_status="BLOCKED",
            oracle_codes=("EVR-SEC-0001",),
            product_eval_status="PASS",
            classification="product",
            published_status="PASS",
            scores_by_config={"alpha": 1.0},
        )
    assert "BMK-ORC-0001" in exc.value.codes


def test_hidden_tests_inaccessible_to_scored_configuration(tmp_path: Path) -> None:
    blob = b'{"config":"alpha","public_only":true}'
    sources = {"alpha": blob}
    hidden, rubric = _passing_hidden(tmp_path)
    config = ScoredConfiguration(
        config_id="alpha",
        source=blob,
        compile_ok=True,
        security_ok=True,
        network_used=False,
    )
    assert not hasattr(config, "hidden_dataset_path")
    assert str(hidden) not in blob.decode("utf-8")
    result = run_sealed_benchmark(
        _valid_manifest(sources),
        sources=sources,
        configs=(config,),
        hidden_dataset_path=hidden,
        hidden_rubric_path=rubric,
    )
    assert hidden.resolve() not in result.config_accessible_paths
    assert rubric.resolve() not in result.config_accessible_paths
    leaked = json_leaked_hidden(result, hidden)
    assert leaked is False


def json_leaked_hidden(result: object, hidden: Path) -> bool:
    blob = str(result).lower()
    return hidden.name.lower() in blob and "hidden" in hidden.name.lower()


def test_default_autonomous_attempts_is_three(tmp_path: Path) -> None:
    blob = b'{"config":"alpha"}'
    sources = {"alpha": blob}
    hidden, rubric = _passing_hidden(tmp_path)
    result = run_sealed_benchmark(
        _valid_manifest(sources),
        sources=sources,
        configs=(
            ScoredConfiguration(
                config_id="alpha",
                source=blob,
                compile_ok=True,
                security_ok=True,
                network_used=False,
            ),
        ),
        hidden_dataset_path=hidden,
        hidden_rubric_path=rubric,
    )
    assert result.autonomous_attempts == 3
    assert len(result.attempts["alpha"]) == 3
