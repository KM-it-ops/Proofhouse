"""examples/ir_minimal.json is the committed, human-readable copy of the canonical minimal IR.

It exists so a presenter can run `proofhouse-compiler validate|compile` on a static
file instead of piping a Python fixture factory. This test keeps it from drifting.
"""

from __future__ import annotations

import json
from pathlib import Path

from .fixtures.ir_fixtures import minimal_valid_ir

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "ir_minimal.json"


def test_example_ir_matches_canonical_minimal_fixture() -> None:
    assert json.loads(EXAMPLE.read_text(encoding="utf-8")) == minimal_valid_ir()
