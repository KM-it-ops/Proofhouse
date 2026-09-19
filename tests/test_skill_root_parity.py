"""Root framework/jsx copies must match skills/proofhouse sources."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_builder():
    path = REPO_ROOT / "scripts" / "build_skill_bundle.py"
    spec = importlib.util.spec_from_file_location("build_skill_bundle", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_skill_bundle"] = module
    spec.loader.exec_module(module)
    return module


def test_root_copies_match_skill_sources() -> None:
    builder = _load_builder()
    pairs = (
        (
            REPO_ROOT / "proofhouse-framework.json",
            REPO_ROOT / "skills" / "proofhouse" / "references" / "proofhouse-framework.json",
        ),
        (
            REPO_ROOT / "proofhouse-framework.md",
            REPO_ROOT / "skills" / "proofhouse" / "references" / "proofhouse-framework.md",
        ),
        (
            REPO_ROOT / "apps" / "proofhouse.jsx",
            REPO_ROOT / "skills" / "proofhouse" / "assets" / "proofhouse.jsx",
        ),
    )
    for canonical, skill_copy in pairs:
        assert canonical.is_file(), f"missing canonical {canonical}"
        assert skill_copy.is_file(), f"missing skill copy {skill_copy}"
        assert builder.entry_bytes(canonical) == builder.entry_bytes(skill_copy), (
            f"{skill_copy.relative_to(REPO_ROOT)} differs from "
            f"{canonical.relative_to(REPO_ROOT)}"
        )
