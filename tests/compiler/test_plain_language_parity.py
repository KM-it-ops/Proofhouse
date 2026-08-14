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
PLAIN_TEXT = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"
EXTERNAL_CONSUMER = Path(__file__).parent / "fixtures" / "external_consumer_plain_language.py"


def _plain_language_envelope_bytes(repair_budget: int = 1) -> bytes:
    text = PLAIN_TEXT.read_text(encoding="utf-8")
    return json.dumps(
        {
            "profile": "plain_language_v0",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "repair_budget": repair_budget,
            "text": text,
        }
    ).encode()


def _parity_fields_from_result(result) -> dict[str, str]:
    evidence = result.evidence_bundle
    return {
        "status": result.status,
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "intake_profile": evidence.get("intake_profile"),
    }


def _parity_fields_from_cli(payload: dict) -> dict[str, str]:
    evidence = payload["evidence_bundle"]
    return {
        "status": payload["status"],
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "intake_profile": evidence.get("intake_profile"),
    }


def test_plain_language_public_api_exports() -> None:
    from promptrig.compiler import api

    assert callable(api.closed_loop_from_json)
    assert callable(api.parse_plain_language_v0)


@pytest.mark.parametrize("repair_budget", [0, 1, 2])
def test_library_cli_plain_language_deep_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repair_budget: int,
) -> None:
    fixture_bytes = _plain_language_envelope_bytes(repair_budget)
    library = closed_loop_from_json(
        fixture_bytes,
        ClosedLoopOptions(repair_budget=repair_budget),
    )
    req_path = tmp_path / "plain_language.json"
    req_path.write_bytes(fixture_bytes)
    code = compiler_main(
        ["closed-loop", str(req_path), "--json", "--repair-budget", str(repair_budget)],
    )
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert _parity_fields_from_cli(cli) == _parity_fields_from_result(library)


def test_external_consumer_plain_language_smoke(tmp_path: Path) -> None:
    fixture_bytes = _plain_language_envelope_bytes(repair_budget=1)
    req_path = tmp_path / "plain_language.json"
    req_path.write_bytes(fixture_bytes)
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
    assert payload["loop_id"] == "mission-012-headless-closed-loop-v0.1"
    assert payload["evaluation_status"] == "PASS"
    assert payload["intake_profile"] == "plain_language_v0"
    assert payload["ir_sha256"]
