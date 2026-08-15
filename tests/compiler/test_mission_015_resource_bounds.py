from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop
from promptrig.compiler.resource_bounds import TRACEMALLOC_PEAK_BYTES_MAX, WALL_SECONDS_MAX

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"


def test_resource_bounds_doc_forbids_benchmark_claims() -> None:
    text = Path("architecture/mission-015-certification/RESOURCE_BOUNDS.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "not a benchmark" in lower or "not comparative" in lower
    assert "operational" in lower
    assert "5.0" in text
    assert "8388608" in text
    assert WALL_SECONDS_MAX == 5.0
    assert TRACEMALLOC_PEAK_BYTES_MAX == 8388608


def test_closed_loop_minimal_respects_operational_ceilings() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))  # warmup
    tracemalloc.start()
    t0 = time.perf_counter()
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    elapsed = time.perf_counter() - t0
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result.status == "PASS"
    assert elapsed < WALL_SECONDS_MAX
    assert peak < TRACEMALLOC_PEAK_BYTES_MAX
