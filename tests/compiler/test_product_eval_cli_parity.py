"""Library/CLI parity for opt-in product eval on promptrig-compiler.

CLI JSON ``data`` must deep-equal the serialized library
``ProductEvaluationResult`` (tuples as lists). Default closed-loop stays
oracle-only. Invalid product-eval paths fail closed with an immutable
diagnostic and no network.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from proofhouse.compiler.api import ClosedLoopOptions, closed_loop_from_json
from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.eval_product import ProductEvalRequest, evaluate_product

CASES = Path(__file__).parent / "fixtures" / "mission_027" / "cases.jsonl"
RUBRIC = Path(__file__).parent / "fixtures" / "mission_027" / "rubric.json"
CLOSED_LOOP_FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _jsonable(result) -> dict:
    return json.loads(json.dumps(asdict(result)))


def _strip_volatile(data: dict) -> dict:
    return json.loads(json.dumps(data))


def test_evaluate_product_library_cli_json_data_parity(capsys: pytest.CaptureFixture[str]) -> None:
    request = ProductEvalRequest(
        baseline_digest=None,
        candidate_digest="sha256:cand",
        dataset_path=CASES,
        rubric_path=RUBRIC,
        aggregation="any_fail",
        baseline_required=False,
        baseline_primary=None,
        network_used=False,
        compile_ok=True,
        security_ok=True,
    )
    library = evaluate_product(request)
    exit_code = compiler_main(
        [
            "evaluate-product",
            "--dataset",
            str(CASES),
            "--rubric",
            str(RUBRIC),
            "--candidate-digest",
            "sha256:cand",
            "--json",
        ]
    )
    cli_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(_jsonable(library))
    assert library.status in {"PASS", "FAIL"}
    assert "EVR-DET-0001" not in library.diagnostic_codes
    assert "EVR-NET-0001" not in library.diagnostic_codes
    assert "EVR-BSL-0001" not in library.diagnostic_codes


@pytest.mark.parametrize("repair_budget", [0, 1, 2])
def test_closed_loop_without_product_eval_flags_oracle_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repair_budget: int,
) -> None:
    fixture_bytes = CLOSED_LOOP_FIXTURE.read_bytes()
    library = closed_loop_from_json(
        fixture_bytes,
        ClosedLoopOptions(repair_budget=repair_budget),
    )
    req_path = tmp_path / "req.json"
    req_path.write_bytes(fixture_bytes)
    code = compiler_main(
        ["closed-loop", str(req_path), "--json", "--repair-budget", str(repair_budget)],
    )
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["status"] == library.status
    assert cli["evidence_bundle"]["evaluation"] == library.evidence_bundle["evaluation"]
    assert library.evidence_bundle["evaluation"]["status"] == "PASS"


def test_evaluate_product_invalid_path_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbid_network(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("product-eval CLI must not use the network")

    monkeypatch.setattr("urllib.request.urlopen", _forbid_network)
    missing = tmp_path / "missing-dataset.jsonl"
    exit_code = compiler_main(
        [
            "evaluate-product",
            "--dataset",
            str(missing),
            "--rubric",
            str(RUBRIC),
            "--candidate-digest",
            "sha256:cand",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code != 0
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
    codes = [d["code"] for d in payload["diagnostics"]]
    assert "PRG-CLI-0001" in codes
    for diagnostic in payload["diagnostics"]:
        assert diagnostic["code"] == "PRG-CLI-0001"
        assert diagnostic["severity"] == "error"
        assert diagnostic["phase"] == "cli"


def test_closed_loop_product_eval_flags_require_both(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _forbid_network(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("unpaired product-eval flags must not use the network")

    monkeypatch.setattr("urllib.request.urlopen", _forbid_network)
    req_path = tmp_path / "req.json"
    req_path.write_bytes(CLOSED_LOOP_FIXTURE.read_bytes())
    exit_code = compiler_main(
        [
            "closed-loop",
            str(req_path),
            "--json",
            "--product-eval-dataset",
            str(CASES),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code != 0
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
    assert any(d["code"] == "PRG-CLI-0001" for d in payload["diagnostics"])


def test_closed_loop_product_eval_flags_reach_hook(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_bytes = CLOSED_LOOP_FIXTURE.read_bytes()
    oracle = closed_loop_from_json(fixture_bytes, ClosedLoopOptions())
    assert oracle.status == "PASS"
    req_path = tmp_path / "req.json"
    req_path.write_bytes(fixture_bytes)
    exit_code = compiler_main(
        [
            "closed-loop",
            str(req_path),
            "--json",
            "--product-eval-dataset",
            str(CASES),
            "--product-eval-rubric",
            str(RUBRIC),
        ]
    )
    cli = json.loads(capsys.readouterr().out)
    assert exit_code != 0
    assert cli["status"] != "PASS"
    assert cli["evidence_bundle"]["evaluation"]["status"] != "PASS"


def test_doctor_json_succeeds_without_product_eval_files(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = compiler_main(["doctor", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert out["status"] == "success"
    assert out["command"] == "doctor"
