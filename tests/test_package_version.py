"""The importable version matches the packaged version (it previously said 0.1.1 at 0.2.1)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import proofhouse


def test_dunder_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert proofhouse.__version__ == pyproject["project"]["version"]
