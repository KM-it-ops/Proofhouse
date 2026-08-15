from __future__ import annotations

import json
import subprocess
from pathlib import Path

from packaging_util import clean_child_env, install_isolated, venv_python

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
CONSUMER = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_closed_loop.py"


def test_pyproject_declares_pep517_build_system() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[build-system]" in text
    assert "setuptools" in text
    assert "wheel" in text


def test_isolated_venv_doctor_and_closed_loop_consumer(tmp_path: Path) -> None:
    py = install_isolated(ROOT, tmp_path / "venv")
    env = clean_child_env()
    doctor = subprocess.run(
        [str(py), "-m", "promptrig.compiler.cli_compiler", "doctor", "--json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert doctor.returncode == 0, doctor.stderr
    payload = json.loads(doctor.stdout)
    assert payload["status"] == "success"
    assert payload["command"] == "doctor"
    names = {c["name"]: c["ok"] for c in payload["data"]["checks"]}
    assert names["ir_schema"] is True
    assert names["diagnostic_registry"] is True
    assert names["offline_mode"] is True

    consumer = subprocess.run(
        [str(py), str(CONSUMER), str(FIXTURE)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert consumer.returncode == 0, consumer.stderr
    out = json.loads(consumer.stdout)
    assert out["status"] == "PASS"
    assert out["loop_id"] == "mission-012-headless-closed-loop-v0.1"
    assert out["ir_sha256"]
    assert "src" not in (env.get("PYTHONPATH") or "")
    scripts = venv_python(tmp_path / "venv")
    assert scripts.exists()
