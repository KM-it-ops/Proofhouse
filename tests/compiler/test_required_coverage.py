"""`evaluate-product` and the sealed benchmark can require requirement coverage (evidence-integrity
review, still open on 0.7.0).

`closed-loop` already blocks a result whose dataset misses a mandatory requirement (EVR-COV-0001),
but the standalone `evaluate-product` command and the benchmark scorer had no way to say which
requirements must be covered, so a dataset about something else could still PASS.

- `evaluate-product --require-req REQ-ID` (repeatable) names requirements the dataset must cover.
- A benchmark manifest may carry `required_req_ids` (a list of requirement ids); the hidden dataset
  must cover every one of them or the published status is BLOCKED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.compiler.benchmark import ScoredConfiguration, run_sealed_benchmark, validate_benchmark_manifest

sys.path.insert(0, str(Path(__file__).parent))
from test_benchmark_manifest_validation import _passing_hidden, _valid_manifest  # noqa: E402


def _dataset_and_rubric(tmp_path: Path) -> tuple[Path, Path]:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps({"case_id": "c1", "req_ids": ["REQ-EVAL-001"], "observations": {"ok": True}}) + "\n",
        encoding="utf-8",
    )
    rubric = tmp_path / "rubric.json"
    rubric.write_text(
        json.dumps({"rubric_id": "r", "version": "1", "criteria": [{"criterion_id": "ok", "field": "ok", "expected": True}]}),
        encoding="utf-8",
    )
    return dataset, rubric


def _evaluate(tmp_path: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> dict:
    dataset, rubric = _dataset_and_rubric(tmp_path)
    cli_compiler.main(
        ["evaluate-product", "--dataset", str(dataset), "--rubric", str(rubric),
         "--candidate-digest", "sha256:candidate", "--aggregation", "all_pass", "--json", *extra]
    )
    return json.loads(capsys.readouterr().out)["data"]


def test_evaluate_product_blocks_when_a_required_requirement_is_not_covered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _evaluate(tmp_path, capsys, "--require-req", "REQ-EVAL-001", "--require-req", "REQ-OTHER-002")
    assert data["status"] == "BLOCKED"
    assert "EVR-COV-0001" in data["diagnostic_codes"]
    assert data["requirement_coverage"]["missing"] == ["REQ-OTHER-002"]


def test_evaluate_product_passes_when_every_required_requirement_is_covered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _evaluate(tmp_path, capsys, "--require-req", "REQ-EVAL-001")
    assert data["status"] == "PASS"
    assert data["requirement_coverage"]["missing"] == []


def test_evaluate_product_without_require_req_behaves_as_before(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _evaluate(tmp_path, capsys)["status"] == "PASS"


def _run_benchmark(tmp_path: Path, required: list[str]) -> object:
    blob = b'{"config":"alpha"}'
    sources = {"alpha": blob}
    manifest = _valid_manifest(sources, required_req_ids=required)
    hidden, rubric = _passing_hidden(tmp_path)  # covers REQ-BMK-001 only
    configs = (ScoredConfiguration(config_id="alpha", source=blob, compile_ok=True, security_ok=True, network_used=False),)
    return run_sealed_benchmark(
        manifest, sources=sources, configs=configs, hidden_dataset_path=hidden, hidden_rubric_path=rubric
    )


def test_benchmark_manifest_accepts_required_req_ids() -> None:
    sources = {"alpha": b'{"config":"alpha"}'}
    validate_benchmark_manifest(_valid_manifest(sources, required_req_ids=["REQ-BMK-001"]), sources=sources)


def test_benchmark_blocks_when_the_hidden_dataset_misses_a_required_requirement(tmp_path: Path) -> None:
    result = _run_benchmark(tmp_path, ["REQ-BMK-001", "REQ-BMK-002"])
    assert result.published_status == "BLOCKED"  # type: ignore[attr-defined]
    assert result.product_eval_status == "BLOCKED"  # type: ignore[attr-defined]


def test_benchmark_passes_when_the_hidden_dataset_covers_every_required_requirement(tmp_path: Path) -> None:
    result = _run_benchmark(tmp_path, ["REQ-BMK-001"])
    assert result.published_status == "PASS"  # type: ignore[attr-defined]


def test_the_sealed_record_names_the_required_requirements(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    one = _run_benchmark(tmp_path / "a", ["REQ-BMK-001"])
    none = _run_benchmark(tmp_path / "b", [])
    assert one.sealed.required_req_ids == ("REQ-BMK-001",)  # type: ignore[attr-defined]
    assert none.sealed.required_req_ids == ()  # type: ignore[attr-defined]
    assert one.score_checksum != none.score_checksum  # type: ignore[attr-defined]


def _find_property(node: object, name: str) -> dict | None:
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict) and name in props:
            return props[name]
        for value in node.values():
            found = _find_property(value, name)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_property(value, name)
            if found is not None:
                return found
    return None


def test_the_hosted_contract_lists_repeatable_flags_as_arrays(monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse.compiler.hosted_openapi import build_openapi

    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")
    schema = _find_property(build_openapi(), "require-req")
    assert schema is not None
    assert schema["type"] == "array"
    assert schema["items"] == {"type": "string"}
