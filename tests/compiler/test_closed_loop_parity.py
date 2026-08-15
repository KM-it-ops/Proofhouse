from __future__ import annotations

import json
from pathlib import Path

import pytest

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json
from promptrig.compiler.cli_compiler import main as compiler_main

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _parity_fields_from_result(result) -> dict[str, str]:
    evidence = result.evidence_bundle
    return {
        "status": result.status,
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
    }


def _parity_fields_from_cli(payload: dict) -> dict[str, str]:
    evidence = payload["evidence_bundle"]
    return {
        "status": payload["status"],
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
    }


def test_closed_loop_public_api_exports() -> None:
    from promptrig.compiler import api

    assert callable(api.closed_loop_from_json)
    assert callable(api.run_closed_loop)


@pytest.mark.parametrize("repair_budget", [0, 1, 2])
def test_library_cli_closed_loop_deep_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repair_budget: int,
) -> None:
    fixture_bytes = FIXTURE.read_bytes()
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
    assert _parity_fields_from_cli(cli) == _parity_fields_from_result(library)
