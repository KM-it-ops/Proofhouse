from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, requirements_to_ir, run_closed_loop, validate_structured_requirements
from promptrig.compiler.contracts import CompileOptions

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "architecture" / "mission-011-certification"


def test_plain_language_schedule_exists() -> None:
    path = CERT / "PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md"
    text = path.read_text(encoding="utf-8")
    assert "MUST NOT be the first or only semantic implementation" in text
    assert "M1" in text and "M3" in text


def test_simple_ui_only_profile_rejected() -> None:
    doc = {
        "profile": "structured_minimal_v0",
        "authoring_mode": "simple_ui_only",
        "contract_version": "0.1.0-draft",
        "network_allowed": False,
        "objective": {"goal": "x"},
        "requirements": [{"id": "REQ-EVAL-001", "statement": "y", "priority": "required"}],
    }
    errors = validate_structured_requirements(doc)
    assert any("Simple Mode" in e for e in errors)


def test_developer_profile_closed_loop() -> None:
    doc = {
        "profile": "structured_developer_v0",
        "contract_version": "0.1.0-draft",
        "project_name": "agent-desk",
        "network_allowed": False,
        "repair_budget": 1,
        "objective": {
            "goal": "Operate tools within permission map.",
            "success_criteria": ["tool_policy_honored"],
            "failure_conditions": ["disallowed_tool_use"],
        },
        "requirements": [
            {
                "id": "REQ-EVAL-001",
                "statement": "Respect stop conditions.",
                "priority": "required",
                "acceptance": ["stops_on_condition"],
            }
        ],
        "behavior": {
            "instructions": ["Plan then act."],
            "constraints": ["No credential exfiltration."],
        },
        "tool_permissions": {"allowed_tools": ["read_file", "run_tests"]},
        "stop_conditions": ["ambiguous_security_impact", "missing_required_context"],
    }
    ir = requirements_to_ir(doc)
    assert "Tool permission map" in " ".join(ir["behavior"]["instructions"])
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["network_used"] is False


def test_compile_options_offline_default() -> None:
    assert CompileOptions().offline is True


def test_maturity_map_reflects_oar005_headless_partial() -> None:
    text = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Headless requirements/evaluation/repair loop | `NOT_STARTED`" not in text
    assert "OAR-005" in text
    assert "`PARTIAL`" in text or "`CERTIFIED`" in text


def test_packaging_cli_entry_smoke() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "promptrig.compiler.cli_compiler", "doctor", "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["command"] == "doctor"
