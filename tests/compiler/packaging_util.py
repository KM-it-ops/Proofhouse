from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def clean_child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def install_isolated(repo_root: Path, venv_dir: Path) -> Path:
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    py = venv_python(venv_dir)
    env = clean_child_env()
    upgrade = subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    installed = subprocess.run(
        [str(py), "-m", "pip", "install", str(repo_root)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    return py
