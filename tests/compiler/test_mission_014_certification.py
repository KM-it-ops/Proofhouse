from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json, run_closed_loop
from promptrig.compiler.repair import ClosedLoopTestHooks

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def test_model_suggest_module_has_no_provider_imports() -> None:
    src = (ROOT / "src" / "promptrig" / "compiler" / "model_suggest.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()


def test_cli_compiler_has_no_force_hooks() -> None:
    src = (ROOT / "src" / "promptrig" / "compiler" / "cli_compiler.py").read_text(encoding="utf-8")
    assert "force_" not in src


def test_simple_ui_still_rejected_with_suggestions_flag() -> None:
    raw = json.dumps(
        {
            "profile": "plain_language_v0",
            "authoring_mode": "simple_ui_only",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "enable_model_suggestions": True,
            "text": "Goal: G\nRequirements:\n1. A\n",
        }
    ).encode()
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(enable_model_suggestions=True),
    )
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in d for d in result.diagnostics)


def test_invented_owner_decision_hook() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = run_closed_loop(
        doc,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_invent_owner_decision=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0002" in result.diagnostics


def test_security_weaken_via_suggestion_hook() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = run_closed_loop(
        doc,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_weaken_security_via_suggestion=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0003" in result.diagnostics
