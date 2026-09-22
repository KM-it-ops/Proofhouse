"""T03 (review F02, F03) and T05 (review F06): evaluation integrity.

On 78e512c: a passing duplicate ``case_id`` erased a failing one; a dataset
covering only an unrelated requirement produced a closed-loop PASS that still
claimed the declared requirement; a failing product evaluation reported the
deterministic evaluator's identity and zero repair attempts with no reason.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

import pytest

from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json, run_closed_loop
from proofhouse.compiler.eval_dataset import load_dataset
from proofhouse.compiler.eval_product import PRODUCT_EVALUATOR_ID, ProductEvalRequest, evaluate_product
from proofhouse.compiler.eval_rubric import load_rubric

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def _rubric(path: Path, criteria: list[dict] | None = None) -> Path:
    criteria = criteria or [{"criterion_id": "ok", "field": "ok", "expected": True}]
    path.write_text(json.dumps({"rubric_id": "t03", "version": "1", "criteria": criteria}), encoding="utf-8")
    return path


def _request(dataset: Path, rubric: Path, aggregation: str = "all_pass", **extra) -> ProductEvalRequest:
    return ProductEvalRequest(
        baseline_digest=None,
        candidate_digest="sha256:candidate",
        dataset_path=dataset,
        rubric_path=rubric,
        aggregation=aggregation,  # type: ignore[arg-type]
        baseline_required=False,
        baseline_primary=None,
        network_used=False,
        compile_ok=True,
        security_ok=True,
        **extra,
    )


def _case(case_id: str, ok: bool, req: str = "REQ-EVAL-001", **extra) -> dict:
    return {"case_id": case_id, "req_ids": [req], "observations": {"ok": ok}, **extra}


# --- F02: duplicate and colliding identifiers --------------------------------------------


def test_duplicate_case_ids_are_rejected_by_loader(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("same", False), _case("same", True)])
    with pytest.raises(ValueError, match="duplicate case_id"):
        load_dataset(dataset)


def test_duplicate_criterion_ids_are_rejected_by_loader(tmp_path: Path) -> None:
    rubric = _rubric(
        tmp_path / "r.json",
        [
            {"criterion_id": "ok", "field": "ok", "expected": True},
            {"criterion_id": "ok", "field": "other", "expected": True},
        ],
    )
    with pytest.raises(ValueError, match="duplicate criterion_id"):
        load_rubric(rubric)


def test_probe_duplicate_pass_can_no_longer_erase_fail(tmp_path: Path) -> None:
    """The exact review probe: [fail, pass] under one id must not become PASS."""
    rubric = _rubric(tmp_path / "r.json")
    for rows in ([_case("same", False), _case("same", True)], [_case("same", True), _case("same", False)]):
        dataset = _write_rows(tmp_path / "d.jsonl", rows)
        with pytest.raises(ValueError, match="duplicate case_id"):
            evaluate_product(_request(dataset, rubric))


def test_cli_evaluate_product_rejects_duplicates_as_usage_error(tmp_path: Path, capsys) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("same", False), _case("same", True)])
    rubric = _rubric(tmp_path / "r.json")
    code = compiler_main(
        ["evaluate-product", "--dataset", str(dataset), "--rubric", str(rubric), "--candidate-digest", "sha256:c", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code != 0
    assert payload["status"] == "error"
    assert "duplicate case_id" in json.dumps(payload)


def test_colliding_composite_keys_keep_every_result(tmp_path: Path) -> None:
    """``"a:b"+"c"`` and ``"a"+"b:c"`` collided as ``"a:b:c"`` string keys on 78e512c."""
    rubric = _rubric(
        tmp_path / "r.json",
        [
            {"criterion_id": "c", "field": "f1", "expected": True},
            {"criterion_id": "b:c", "field": "f2", "expected": True},
        ],
    )
    dataset = _write_rows(
        tmp_path / "d.jsonl",
        [
            {"case_id": "a:b", "req_ids": ["REQ-EVAL-001"], "observations": {"f1": False, "f2": True}},
            {"case_id": "a", "req_ids": ["REQ-EVAL-001"], "observations": {"f1": True, "f2": True}},
        ],
    )
    result = evaluate_product(_request(dataset, rubric))
    assert len(result.case_results) == 4
    assert result.status == "FAIL"
    failing = [row for row in result.case_results if row["score"] == 0.0]
    assert failing == [{"case_id": "a:b", "criterion_id": "c", "score": 0.0, "req_ids": ["REQ-EVAL-001"]}]


@pytest.mark.parametrize(
    "row",
    [
        pytest.param({"case_id": "", "req_ids": ["REQ-EVAL-001"], "observations": {}}, id="empty-id"),
        pytest.param({"case_id": 7, "req_ids": ["REQ-EVAL-001"], "observations": {}}, id="numeric-id"),
        pytest.param({"case_id": "x", "req_ids": "REQ-EVAL-001", "observations": {}}, id="req-ids-string"),
        pytest.param({"case_id": "x", "req_ids": ["REQ-EVAL-001"], "observations": []}, id="observations-array"),
        pytest.param({"case_id": "x", "req_ids": ["REQ-EVAL-001"]}, id="observations-missing"),
        pytest.param(["not", "an", "object"], id="row-array"),
        pytest.param({"case_id": "x", "req_ids": ["REQ-EVAL-001", "REQ-EVAL-001"], "observations": {}}, id="dup-req"),
    ],
)
def test_malformed_dataset_rows_raise_value_error_with_line(tmp_path: Path, row) -> None:
    dataset = tmp_path / "d.jsonl"
    dataset.write_text(json.dumps(_case("ok-1", True)) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_dataset(dataset)


def test_nonfinite_observation_values_are_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "d.jsonl"
    dataset.write_text('{"case_id": "x", "req_ids": ["REQ-EVAL-001"], "observations": {"ok": NaN}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        load_dataset(dataset)


# --- permutation invariance and monotonicity ----------------------------------------------


@pytest.mark.parametrize("aggregation", ["min", "max", "mean", "any_fail", "all_pass"])
def test_aggregation_is_permutation_invariant(tmp_path: Path, aggregation: str) -> None:
    rubric = _rubric(tmp_path / "r.json")
    rows = [_case("c1", True), _case("c2", False), _case("c3", True), _case("c4", True)]
    outcomes = set()
    for order in itertools.permutations(rows):
        dataset = _write_rows(tmp_path / "d.jsonl", list(order))
        result = evaluate_product(_request(dataset, rubric, aggregation))
        outcomes.add((result.status, result.scores["primary"]))
    assert len(outcomes) == 1, outcomes


@pytest.mark.parametrize("aggregation", ["min", "any_fail", "all_pass"])
def test_property_adding_a_failing_case_never_improves_strict_aggregations(tmp_path: Path, aggregation: str) -> None:
    rng = random.Random(7)
    rubric = _rubric(tmp_path / "r.json")
    rank = {"PASS": 1, "FAIL": 0}
    for trial in range(40):
        rows = [_case(f"c{i}", rng.random() < 0.7) for i in range(rng.randint(1, 6))]
        before = evaluate_product(_request(_write_rows(tmp_path / "a.jsonl", rows), rubric, aggregation))
        rows_after = rows + [_case(f"fail-{trial}", False)]
        rng.shuffle(rows_after)
        after = evaluate_product(_request(_write_rows(tmp_path / "b.jsonl", rows_after), rubric, aggregation))
        assert after.status == "FAIL"
        assert rank[after.status] <= rank[before.status]


# --- F03: requirement coverage and binding in the closed loop ------------------------------


def _closed_loop(dataset: Path, rubric: Path, repair_budget: int = 1):
    return closed_loop_from_json(
        FIXTURE.read_text(encoding="utf-8"),
        ClosedLoopOptions(repair_budget=repair_budget, product_eval=_request(dataset, rubric)),
    )


def test_probe_unrelated_requirement_coverage_is_blocked(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", True, req="REQ-OTHER-001")])
    result = _closed_loop(dataset, _rubric(tmp_path / "r.json"))
    assert result.status == "BLOCKED"
    assert "EVR-COV-0001" in result.diagnostics
    coverage = result.evidence_bundle["requirement_coverage"]
    assert coverage["required"] == ["REQ-EVAL-001"]
    assert coverage["missing"] == ["REQ-EVAL-001"]
    assert coverage["covered"] == []
    assert coverage["not_declared"] == ["REQ-OTHER-001"]


def test_covered_requirements_record_binding(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", True)])
    rubric = _rubric(tmp_path / "r.json")
    result = _closed_loop(dataset, rubric)
    # Unbound rows score (stage PASS) but cannot vouch for this candidate; see
    # test_closed_loop_candidate_binding.py.
    assert result.status == "BLOCKED"
    assert any(code.startswith("EVR-BND-0002") for code in result.diagnostics)
    assert result.evidence_bundle["stages"]["product_evaluation"]["status"] == "PASS"
    evidence = result.evidence_bundle
    assert evidence["requirement_coverage"]["missing"] == []
    assert evidence["requirement_coverage"]["covered"] == ["REQ-EVAL-001"]
    product = evidence["stages"]["product_evaluation"]
    assert product["evaluator"]["id"] == PRODUCT_EVALUATOR_ID
    assert product["observation_source"] == "imported"
    assert product["dataset_sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert product["rubric_sha256"] == hashlib.sha256(rubric.read_bytes()).hexdigest()
    assert product["candidate_digest"] == evidence["candidate_digest"]
    assert product["candidate_binding"] == "unbound"
    assert evidence["evaluator"]["id"] == PRODUCT_EVALUATOR_ID


def test_observations_bound_to_a_different_candidate_are_blocked(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", True, candidate_digest="sha256:" + "0" * 64)])
    result = _closed_loop(dataset, _rubric(tmp_path / "r.json"))
    assert result.status == "BLOCKED"
    assert "EVR-BND-0001" in result.diagnostics
    assert result.evidence_bundle["stages"]["product_evaluation"]["candidate_binding"] == "mismatch"


def test_closed_loop_duplicate_dataset_is_blocked_not_raised(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("same", False), _case("same", True)])
    result = _closed_loop(dataset, _rubric(tmp_path / "r.json"))
    assert result.status == "BLOCKED"
    assert any(code.startswith("EVR-DUP-0001") for code in result.diagnostics)


def test_standalone_evaluate_product_reports_uncovered_required_ids(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", True, req="REQ-OTHER-001")])
    result = evaluate_product(_request(dataset, _rubric(tmp_path / "r.json"), required_req_ids=("REQ-EVAL-001",)))
    assert result.status == "BLOCKED"
    assert "EVR-COV-0001" in result.diagnostic_codes


# --- F06 / T05: stage identity, repair truthfulness, retained failure evidence -------------


def test_probe_product_failure_records_true_evaluator_and_repair_reason(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", False)])
    result = _closed_loop(dataset, _rubric(tmp_path / "r.json"), repair_budget=2)
    evidence = result.evidence_bundle
    assert result.status == "FAIL"
    assert evidence["evaluator"]["id"] == PRODUCT_EVALUATOR_ID
    stages = evidence["stages"]
    assert stages["compile"]["status"] == "success"
    assert stages["deterministic_evaluation"]["status"] == "PASS"
    assert stages["deterministic_evaluation"]["evaluator"]["id"] == "evr-det-compile-security-v1"
    assert stages["product_evaluation"]["status"] == "FAIL"
    repair = stages["repair"]
    assert repair["attempted"] == 0
    assert repair["budget"] == 2
    assert repair["terminal_reason"] == "repair_unsupported_imported_observations"
    assert "EVR-REP-0005" in result.diagnostics
    failing = [row for row in stages["product_evaluation"]["case_results"] if row["score"] == 0.0]
    assert failing and failing[0]["case_id"] == "c1"


def test_default_closed_loop_records_stages_without_product(tmp_path: Path) -> None:
    result = run_closed_loop(json.loads(FIXTURE.read_text(encoding="utf-8")))
    stages = result.evidence_bundle["stages"]
    assert result.status == "PASS"
    assert stages["product_evaluation"] is None
    assert stages["repair"]["attempted"] == 0
    assert stages["repair"]["terminal_reason"] == "not_needed"
    # The structural oracle never claims to have measured output quality.
    assert result.evidence_bundle["evidence_classes"] == ["structural_compile_check"]
    assert "semantic_quality" in result.evidence_bundle["not_measured"]


# --- Review of 8b5a187: duplicate JSON keys inside a row or rubric ------------------------


def test_duplicate_observation_key_cannot_turn_a_fail_into_pass(tmp_path: Path) -> None:
    dataset = tmp_path / "d.jsonl"
    dataset.write_text(
        '{"case_id": "a", "req_ids": ["REQ-EVAL-001"], "observations": {"ok": false, "ok": true}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="line 1: .*duplicate JSON key 'ok'"):
        load_dataset(dataset)


def test_duplicate_top_level_key_in_a_row_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "d.jsonl"
    dataset.write_text('{"case_id": "a", "case_id": "b", "req_ids": ["REQ-EVAL-001"], "observations": {}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key 'case_id'"):
        load_dataset(dataset)


def test_rubric_with_two_criteria_arrays_is_rejected(tmp_path: Path) -> None:
    rubric = tmp_path / "r.json"
    rubric.write_text(
        '{"rubric_id": "r", "version": "1", "criteria": [{"criterion_id": "ok", "field": "ok", "expected": true}],'
        ' "criteria": [{"criterion_id": "x", "field": "x", "expected": true}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key 'criteria'"):
        load_rubric(rubric)


@pytest.mark.parametrize("missing", ["rubric_id", "version"])
def test_rubric_without_identity_is_rejected_not_recorded_as_none(tmp_path: Path, missing: str) -> None:
    doc = {"rubric_id": "r", "version": "1", "criteria": [{"criterion_id": "ok", "field": "ok", "expected": True}]}
    del doc[missing]
    rubric = tmp_path / "r.json"
    rubric.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match=f"{missing} must be a non-empty string"):
        load_rubric(rubric)
