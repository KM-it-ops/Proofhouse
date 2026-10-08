"""The documented reference workflow runs end to end (plan T11 acceptance, criterion 6 support).

``proofhouse-compiler demo`` and ``scripts/reference_workflow.py`` both call
``proofhouse.optimize.reference_workflow``. This module runs that body once,
through ``demo``, and checks the script wrapper points at the same ``main``.
The wheel-install CI job also runs the script against the installed console script.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import reference_workflow

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reference_workflow.py"


def test_demo_command_passes(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PYTHONUTF8", "1")
    code = cli_compiler.main(["demo", "--workspace", str(tmp_path / "ws"), "--quiet"])
    captured = capsys.readouterr()
    assert code == 0, captured.err + captured.out
    assert "reference workflow: OK" in captured.out
    report = (tmp_path / "ws" / "report.md").read_text(encoding="utf-8")
    assert "Overall: **PASS**" in report
    assert "What this report does not show" in report


def test_script_wrapper_uses_the_same_runner() -> None:
    spec = importlib.util.spec_from_file_location("reference_workflow_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main is reference_workflow.main
