"""Codex binding review of d067e7a: closed-loop must not claim a candidate PASS from unbound observations.

On d067e7a, imported observations that declare no candidate digest (``unbound``)
or only partly do (``partially_bound``) produced a closed-loop PASS, exit 0 and
"closed-loop: PASS", and dropped ``semantic_quality`` from ``not_measured`` --
so observations about another or older candidate read as current evidence.
Standalone ``evaluate_product`` keeps scoring supplied observations unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json
from proofhouse.compiler.eval_product import ProductEvalRequest, evaluate_product

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"
UNBOUND = "EVR-BND-0002"
EXIT_SUCCESS = 0
EXIT_COMPILATION_FAILURE = 5


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def _rubric(path: Path) -> Path:
    criteria = [{"criterion_id": "ok", "field": "ok", "expected": True}]
    path.write_text(json.dumps({"rubric_id": "bnd", "version": "1", "criteria": criteria}), encoding="utf-8")
    return path


def _request(dataset: Path, rubric: Path) -> ProductEvalRequest:
    return ProductEvalRequest(
        baseline_digest=None,
        candidate_digest="sha256:placeholder",
        dataset_path=dataset,
        rubric_path=rubric,
        aggregation="all_pass",
        baseline_required=False,
        baseline_primary=None,
        network_used=False,
        compile_ok=True,
        security_ok=True,
    )


def _case(case_id: str, req: str = "REQ-EVAL-001", ok: bool = True, **extra: object) -> dict:
    return {"case_id": case_id, "req_ids": [req], "observations": {"ok": ok}, **extra}


def _closed_loop(dataset: Path, rubric: Path):
    return closed_loop_from_json(
        FIXTURE.read_text(encoding="utf-8"),
        ClosedLoopOptions(repair_budget=1, product_eval=_request(dataset, rubric)),
    )


@pytest.fixture()
def candidate_digest(tmp_path: Path) -> str:
    probe = _closed_loop(_write_rows(tmp_path / "probe.jsonl", [_case("p")]), _rubric(tmp_path / "probe.json"))
    digest = probe.evidence_bundle["candidate_digest"]
    assert isinstance(digest, str) and digest
    return digest


def _cli(dataset: Path, rubric: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], *, json_out: bool):
    req = tmp_path / "req.json"
    req.write_bytes(FIXTURE.read_bytes())
    argv = ["closed-loop", str(req), "--product-eval-dataset", str(dataset), "--product-eval-rubric", str(rubric)]
    exit_code = compiler_main(argv + (["--json"] if json_out else []))
    return exit_code, capsys.readouterr().out


def _assert_withheld(result, binding: str) -> None:
    assert result.status == "BLOCKED"
    assert any(code.startswith(UNBOUND) and binding in code for code in result.diagnostics)
    evidence = result.evidence_bundle
    assert evidence["evaluation"]["status"] == "BLOCKED"
    product = evidence["stages"]["product_evaluation"]
    # The observation score itself is preserved in the stage.
    assert product["status"] == "PASS"
    assert product["scores"]["primary"] == 1.0
    assert product["candidate_binding"] == binding
    assert "semantic_quality" in evidence["not_measured"]
    assert evidence["stages"]["repair"]["terminal_reason"] == "blocked_unbound_observations"


def test_entirely_unbound_observations_do_not_pass(tmp_path: Path) -> None:
    result = _closed_loop(_write_rows(tmp_path / "d.jsonl", [_case("c1")]), _rubric(tmp_path / "r.json"))
    _assert_withheld(result, "unbound")


def test_partial_binding_with_mandatory_coverage_only_from_unbound_rows(
    tmp_path: Path, candidate_digest: str
) -> None:
    rows = [
        _case("bound-other", req="REQ-OTHER-001", candidate_digest=candidate_digest),
        _case("unbound-mandatory", req="REQ-EVAL-001"),
    ]
    result = _closed_loop(_write_rows(tmp_path / "d.jsonl", rows), _rubric(tmp_path / "r.json"))
    assert result.evidence_bundle["requirement_coverage"]["missing"] == []
    _assert_withheld(result, "partially_bound")


def test_fully_bound_observations_still_pass(tmp_path: Path, candidate_digest: str) -> None:
    rows = [_case("c1", candidate_digest=candidate_digest)]
    result = _closed_loop(_write_rows(tmp_path / "d.jsonl", rows), _rubric(tmp_path / "r.json"))
    assert result.status == "PASS"
    assert not any(code.startswith(UNBOUND) for code in result.diagnostics)
    evidence = result.evidence_bundle
    assert evidence["stages"]["product_evaluation"]["candidate_binding"] == "bound"
    assert "semantic_quality" not in evidence["not_measured"]


def test_unbound_failing_observations_still_fail(tmp_path: Path) -> None:
    result = _closed_loop(_write_rows(tmp_path / "d.jsonl", [_case("c1", ok=False)]), _rubric(tmp_path / "r.json"))
    assert result.status in {"FAIL", "UNRESOLVED_DEFECT"}
    assert not any(code.startswith(UNBOUND) for code in result.diagnostics)


def test_standalone_scoring_of_unbound_observations_is_unchanged(tmp_path: Path) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1")])
    result = evaluate_product(_request(dataset, _rubric(tmp_path / "r.json")))
    assert result.status == "PASS"
    assert result.candidate_binding == "unbound"


@pytest.mark.parametrize("partial", [False, True])
def test_cli_json_and_exit_status_withhold_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], candidate_digest: str, partial: bool
) -> None:
    rows = [_case("c1")]
    if partial:
        rows.insert(0, _case("b1", req="REQ-OTHER-001", candidate_digest=candidate_digest))
    dataset = _write_rows(tmp_path / "d.jsonl", rows)
    exit_code, out = _cli(dataset, _rubric(tmp_path / "r.json"), tmp_path, capsys, json_out=True)
    payload = json.loads(out)
    assert exit_code == EXIT_COMPILATION_FAILURE
    assert payload["status"] == "BLOCKED"
    assert payload["evidence_bundle"]["evaluation"]["status"] == "BLOCKED"
    assert any(code.startswith(UNBOUND) for code in payload["diagnostics"])
    assert "semantic_quality" in payload["evidence_bundle"]["not_measured"]


def test_cli_text_reports_missing_binding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1")])
    exit_code, out = _cli(dataset, _rubric(tmp_path / "r.json"), tmp_path, capsys, json_out=False)
    assert exit_code == EXIT_COMPILATION_FAILURE
    assert "closed-loop: BLOCKED" in out
    assert "closed-loop: PASS" not in out
    assert UNBOUND in out
    assert "candidate_binding: unbound" in out


def test_cli_fully_bound_still_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], candidate_digest: str
) -> None:
    dataset = _write_rows(tmp_path / "d.jsonl", [_case("c1", candidate_digest=candidate_digest)])
    exit_code, out = _cli(dataset, _rubric(tmp_path / "r.json"), tmp_path, capsys, json_out=False)
    assert exit_code == EXIT_SUCCESS
    assert "closed-loop: PASS" in out
    assert "candidate_binding: bound" in out
