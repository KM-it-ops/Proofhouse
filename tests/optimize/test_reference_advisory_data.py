"""The installed package carries the same reference-advisory files as the repo examples."""

from __future__ import annotations

from pathlib import Path

from proofhouse.optimize.reference_workflow import EXAMPLE, EXAMPLE_NAMES

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "reference-advisory"


def test_packaged_reference_advisory_matches_examples() -> None:
    example_files = sorted(path.name for path in EXAMPLES.iterdir() if path.is_file())
    packaged_files = sorted(path.name for path in EXAMPLE.iterdir() if path.is_file())
    assert example_files == packaged_files == sorted(EXAMPLE_NAMES)
    for name in EXAMPLE_NAMES:
        assert (EXAMPLES / name).read_bytes() == (EXAMPLE / name).read_bytes()
