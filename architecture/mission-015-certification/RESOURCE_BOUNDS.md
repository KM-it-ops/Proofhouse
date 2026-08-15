# Operational resource bounds (MISSION-015)

These are fail-closed **operational** ceilings for `run_closed_loop` on
`tests/compiler/fixtures/closed_loop_requirements_minimal.json` with
`repair_budget=1`. They are **not a benchmark** and are **not comparative**
product-performance claims (REJ-005).

Canonical values (must match `src/promptrig/compiler/resource_bounds.py`):

- `WALL_SECONDS_MAX` = 5.0
- `TRACEMALLOC_PEAK_BYTES_MAX` = 8388608 (8 MiB)

Basis: local measurement ~0.16s wall / ~153 KiB tracemalloc peak; 3× would be
~0.47s / ~459 KiB. Floors of 5.0 seconds and 8 MiB absorb CI variance.

Scope: fake adapter, offline, this fixture only. Not a live-provider bound.
