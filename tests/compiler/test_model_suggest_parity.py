from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json
from promptrig.compiler.cli_compiler import main as compiler_main

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"
EXTERNAL_CONSUMER = Path(__file__).parent / "fixtures" / "external_consumer_model_suggest.py"


def test_model_suggest_public_api_exports() -> None:
    from promptrig.compiler import api

    assert callable(api.build_fake_model_proposal)
    assert callable(api.closed_loop_from_json)


def _parity_fields_from_result(result) -> dict[str, str | None]:
    evidence = result.evidence_bundle
    proposal = evidence["model_proposal"]
    return {
        "status": result.status,
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_output_digest": proposal["output_digest"],
    }


def _parity_fields_from_cli(payload: dict) -> dict[str, str | None]:
    evidence = payload["evidence_bundle"]
    proposal = evidence["model_proposal"]
    return {
        "status": payload["status"],
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_output_digest": proposal["output_digest"],
    }


@pytest.mark.parametrize("repair_budget", [0, 1, 2])
def test_library_cli_model_suggest_deep_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repair_budget: int,
) -> None:
    fixture_bytes = FIXTURE.read_bytes()
    library = closed_loop_from_json(
        fixture_bytes,
        ClosedLoopOptions(repair_budget=repair_budget, enable_model_suggestions=True),
    )
    req_path = tmp_path / "req.json"
    req_path.write_bytes(fixture_bytes)
    code = compiler_main(
        [
            "closed-loop",
            str(req_path),
            "--json",
            "--repair-budget",
            str(repair_budget),
            "--enable-model-suggestions",
        ],
    )
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert _parity_fields_from_cli(cli) == _parity_fields_from_result(library)


def test_cli_default_omits_model_proposal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    req_path = tmp_path / "req.json"
    req_path.write_bytes(FIXTURE.read_bytes())
    code = compiler_main(["closed-loop", str(req_path), "--json", "--repair-budget", "1"])
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert "model_proposal" not in cli["evidence_bundle"]


def test_external_consumer_model_suggest_smoke(tmp_path: Path) -> None:
    req_path = tmp_path / "req.json"
    req_path.write_bytes(FIXTURE.read_bytes())
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(EXTERNAL_CONSUMER), str(req_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "PASS"
    assert payload["suggestion_profile"] == "fake_suggester_v0"
