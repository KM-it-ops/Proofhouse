from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json

ROOT = Path(__file__).resolve().parents[2]
PLAIN_FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"


def test_plain_language_module_has_no_provider_imports() -> None:
    src = Path("src/promptrig/compiler/plain_language.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()


def test_simple_ui_still_rejected_on_plain_envelope() -> None:
    raw = json.dumps(
        {
            "profile": "plain_language_v0",
            "authoring_mode": "simple_ui_only",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "text": "Goal: G\nRequirements:\n1. A\n",
        }
    ).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions())
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in d for d in result.diagnostics)


def test_freeform_prose_never_becomes_ir() -> None:
    raw = json.dumps(
        {
            "profile": "plain_language_v0",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "repair_budget": 1,
            "text": "Please build a helpful assistant that does stuff.",
        }
    ).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "BLOCKED"
    assert any(d.startswith("PL-PARSE-") for d in result.diagnostics)
    assert result.evidence_bundle.get("ir_sha256") is None
    assert "ir" not in result.evidence_bundle


def test_cli_subprocess_plain_language_smoke(tmp_path: Path) -> None:
    text = PLAIN_FIXTURE.read_text(encoding="utf-8")
    envelope = {
        "profile": "plain_language_v0",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "repair_budget": 1,
        "text": text,
    }
    req_path = tmp_path / "plain_language.json"
    req_path.write_text(json.dumps(envelope), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "promptrig.compiler.cli_compiler",
            "closed-loop",
            str(req_path),
            "--json",
            "--repair-budget",
            "1",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "PASS"
    assert payload["evidence_bundle"]["intake_profile"] == "plain_language_v0"
    assert payload["evidence_bundle"]["ir_sha256"]
