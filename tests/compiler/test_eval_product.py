from pathlib import Path

from promptrig.compiler.eval_product import ProductEvalRequest, evaluate_product


CASES = Path("tests/compiler/fixtures/mission_027/cases.jsonl")
RUBRIC = Path("tests/compiler/fixtures/mission_027/rubric.json")


def _req(**overrides: object) -> ProductEvalRequest:
    base = dict(
        baseline_digest="sha256:base",
        candidate_digest="sha256:cand",
        dataset_path=CASES,
        rubric_path=RUBRIC,
        aggregation="any_fail",
        baseline_required=True,
        baseline_primary=1.0,
        network_used=False,
        compile_ok=True,
        security_ok=True,
        baseline_stale=False,
    )
    base.update(overrides)
    return ProductEvalRequest(**base)  # type: ignore[arg-type]


def test_network_still_blocks() -> None:
    result = evaluate_product(_req(network_used=True))
    assert result.status == "BLOCKED"
    assert "EVR-NET-0001" in result.diagnostic_codes


def test_missing_baseline_blocks() -> None:
    result = evaluate_product(_req(baseline_digest=None))
    assert result.status == "BLOCKED"
    assert "EVR-BSL-0001" in result.diagnostic_codes


def test_stale_baseline_blocks() -> None:
    result = evaluate_product(_req(baseline_stale=True))
    assert result.status == "BLOCKED"
    assert "EVR-BSL-0002" in result.diagnostic_codes


def test_regression_when_worse_than_baseline() -> None:
    result = evaluate_product(_req(baseline_primary=1.0))
    # fixture case EVC-002 fails compile_ok; any_fail primary is 0.0
    assert result.status == "REGRESSION"
    assert result.scores["primary"] == 0.0
    assert "REQ-EVAL-001" in result.req_ids
    assert result.failed_attempts == ()


def test_error_score_does_not_pass(tmp_path: Path) -> None:
    cases = tmp_path / "one.jsonl"
    cases.write_text(
        '{"case_id": "EVC-Z", "req_ids": ["REQ-EVAL-001"], "observations": {}}\n',
        encoding="utf-8",
    )
    result = evaluate_product(_req(dataset_path=cases, baseline_required=False))
    assert result.status == "ERROR"
    assert "EVR-SCR-0001" in result.diagnostic_codes
    assert result.scores["primary"] is None
