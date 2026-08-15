from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
EXTERNAL_CONSUMER = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_closed_loop.py"


def test_external_consumer_closed_loop_smoke() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(EXTERNAL_CONSUMER), str(FIXTURE)],
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
    assert payload["ir_sha256"]  # canonical hex digest from evidence bundle
