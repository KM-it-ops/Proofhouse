"""The documented reference workflow runs end to end (plan T11 acceptance, criterion 6 support).

scripts/reference_workflow.py is the single executable copy of the commands in
docs/reference-workflow.md; the wheel-install CI job runs it against the
installed console script as well.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reference_workflow.py"


def test_reference_workflow_script_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PYTHONUTF8", "1")
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--workspace", str(tmp_path / "ws"), "--quiet"],
        capture_output=True, text=True, encoding="utf-8", timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "reference workflow: OK" in completed.stdout
    report = (tmp_path / "ws" / "report.md").read_text(encoding="utf-8")
    assert "Overall: **PASS**" in report
    assert "What this report does not show" in report
