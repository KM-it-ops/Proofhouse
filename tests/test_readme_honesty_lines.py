"""Status and honesty lines the pre-0.3.0 README carried must still be stated somewhere in the README."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

REQUIRED = [
    "does not call a model",      # optimize never calls a provider
    "does not rate quality",      # optimize does not score output quality
    "not a hosted service",
    "not isolation",
    "PARTIAL",
    "recorded, not enforced",
    "unverified",
    "Nothing here is a benchmark",
]


def test_readme_keeps_every_honesty_line() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED if phrase not in readme]
    assert not missing, missing
