from __future__ import annotations

import json
import subprocess
from pathlib import Path

from packaging_util import clean_child_env, install_isolated

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_matrix.py"
STRUCTURED = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
PLAIN_TXT = ROOT / "tests" / "compiler" / "fixtures" / "plain_language_minimal.txt"
CREDENTIAL_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)


def _run_matrix(py: Path, json_path: Path, *flags: str) -> dict:
    env = clean_child_env()
    for key in CREDENTIAL_KEYS:
        env.pop(key, None)
    proc = subprocess.run(
        [str(py), str(MATRIX), str(json_path), *flags],
        cwd=json_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_consumer_matrix_doc_exists() -> None:
    text = Path("architecture/mission-015-certification/CONSUMER_MATRIX.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "promptrig.compiler.api" in lower
    assert "structured" in lower
    assert "plain_language_v0" in lower
    assert "fake-suggester-v0" in lower or "fake_suggester" in lower
    assert "simple mode" in lower
    assert "network_allowed" in lower


def test_installed_consumer_matrix(tmp_path: Path) -> None:
    py = install_isolated(ROOT, tmp_path / "venv")

    structured = _run_matrix(py, STRUCTURED)
    assert structured["status"] == "PASS"
    assert structured["ir_sha256"]
    assert structured["proposal_acceptance"] is None

    plain_envelope = {
        "profile": "plain_language_v0",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "repair_budget": 1,
        "text": PLAIN_TXT.read_text(encoding="utf-8"),
    }
    plain_path = tmp_path / "plain.json"
    plain_path.write_text(json.dumps(plain_envelope), encoding="utf-8")
    plain = _run_matrix(py, plain_path)
    assert plain["status"] == "PASS"
    assert plain["intake_profile"] == "plain_language_v0"

    suggested = _run_matrix(py, STRUCTURED, "--enable-model-suggestions")
    assert suggested["status"] == "PASS"
    assert suggested["suggestion_profile"] == "fake_suggester_v0"
    assert suggested["proposal_acceptance"] == "proposed"
    assert suggested["proposal_authority"] == "model_suggested"
    assert suggested["proposed_records"] == ["REQ-MS-001"]
    assert suggested["ir_sha256"] == structured["ir_sha256"]

    blocked_ui = {
        "profile": "plain_language_v0",
        "authoring_mode": "simple_ui_only",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "text": "Goal: G\nRequirements:\n1. A\n",
    }
    ui_path = tmp_path / "ui.json"
    ui_path.write_text(json.dumps(blocked_ui), encoding="utf-8")
    ui = _run_matrix(py, ui_path)
    assert ui["status"] == "BLOCKED"
    assert any("Simple Mode" in d for d in ui["diagnostics"])

    net_doc = json.loads(STRUCTURED.read_text(encoding="utf-8"))
    net_doc["network_allowed"] = True
    net_path = tmp_path / "net.json"
    net_path.write_text(json.dumps(net_doc), encoding="utf-8")
    net = _run_matrix(py, net_path)
    assert net["status"] == "BLOCKED"
    assert "EVR-NET-0001" in net["diagnostics"]
