# MISSION-030 Task U4 — 008 SUCCESS→IR bridge

**Worktree:** `C:\AI\projects\PromptRig\.worktrees\mission-030-008-ir-bridge`
**Branch:** `feature/mission-030-008-ir-bridge`
**HEAD before:** `eb58a13` (U3 CLI parity on top of 027)

## What you implemented

Explicit 008→structured_minimal_v0→existing fake closed-loop bridge. Constructor override: do **not** apply RFC 6901 pointers onto IR v0.1.

- `compile_requirements` on the canonical 008 artifact set. Only SUCCESS, or honest PARTIAL with representable meaning, continues. BLOCKED / REFUSED / INVALID_OUTPUT do not lower.
- Projection into `structured_minimal_v0`: `contract_version` `0.1.0-draft` (accepted by `validate_structured_requirements`), `objective.goal` from the emitting mapping whose `target_pointer` is `/objective/goal` (that requirement's statement), `requirements` every 008 REQ-* `id`+`statement` (goal mapping does not drop the requirement), `network_allowed: false`.
- Then existing `requirements_to_ir` via `run_closed_loop`. No second IR compiler. `evaluate_contract_rules` remains sole RC-065.
- Unbridged 008 JSON on `closed_loop_from_json` / `closed-loop` stays `BLOCKED` + `EVR-RQC-0001`. `closed_loop.py` was not taught to parse 008 envelopes.
- PARTIAL without representable goal/requirements fails closed with immutable `EVR-BRG-0001` (no invented meaning).
- Library: `bridge_008_to_structured`, `closed_loop_from_bridged_008`. CLI: `promptrig-compiler closed-loop-bridged-008`. Lazy API exports added. No `force_*` on production CLI.
- `simple_mode_ui` / `simple_ui_only` stay forbidden. `network_allowed=true` still `EVR-NET-0001`. Repair budgets `{0,1,2}` and `EVR-SEC-0001` unchanged.
- Honesty pack: `architecture/mission-030-certification/README.md`, `OAR-023.md` Ready (not Accepted). OAR-022 skip-cert not rewritten.

## What you tested (commands + results)

RED (tests only, before `requirements_ir_bridge.py`):

```text
uv run --with pytest python -m pytest tests/compiler/test_requirements_ir_bridge.py -v
```

Result: **collection ERROR** in 2.00s. `ModuleNotFoundError: No module named 'promptrig.compiler.requirements_ir_bridge'`.

GREEN (after library/CLI/honesty pack):

```text
uv run --with pytest python -m pytest tests/compiler/test_requirements_ir_bridge.py tests/compiler/test_mission_016_closed_loop.py tests/compiler/test_mission_030_schedule.py tests/compiler/test_mission_012_certification.py tests/compiler/test_evaluation_engine.py tests/compiler/test_no_network_and_determinism.py -v
```

Result: **34 passed** in 1.62s.

## TDD Evidence

- **RED command:** `uv run --with pytest python -m pytest tests/compiler/test_requirements_ir_bridge.py -v`
- **RED reason:** bridge module did not exist; collection failed with `ModuleNotFoundError: No module named 'promptrig.compiler.requirements_ir_bridge'`.
- **GREEN command:** required six-file suite above.
- **GREEN output:** 34 passed in 1.62s (13 bridge tests, 4 closed-loop 016 tests including unbridged `EVR-RQC-0001`, 1 schedule honesty test, plus 012/eval/network regressions).

## Files changed

- Create: `src/promptrig/compiler/requirements_ir_bridge.py`
- Modify: `src/promptrig/compiler/api.py` (lazy exports)
- Modify: `src/promptrig/compiler/cli_compiler.py` (`closed-loop-bridged-008`)
- Create: `tests/compiler/test_requirements_ir_bridge.py`
- Create: `tests/compiler/test_mission_030_schedule.py`
- Create: `architecture/mission-030-certification/README.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-023.md`
- Create: `docs/superpowers/reports/mission-030-task.md`
- Not committed: `uv.lock`
- Not modified: `closed_loop.py` intake of 008 envelopes; 027/029 engines; OAR-021; OAR-022

## Self-review findings

- Completeness: AE1 happy, AE2 unbridged, PARTIAL representable, BLOCKED/REFUSED/INVALID_OUTPUT do not lower, PARTIAL missing goal fail-closed, AE5 simple-mode + network, repair budgets `{0,1,2}` and out-of-range, CLI/library parity on SUCCESS fixture.
- YAGNI: no RFC-6901 IR patcher, no second compiler, no native 008 parse on `closed-loop`, no IR v0.2, no U5.
- Naming: `bridge_008_to_structured` / `closed_loop_from_bridged_008` / `closed-loop-bridged-008` match the constructor.
- Test honesty: unbridged path still `EVR-RQC-0001`. PARTIAL evidence does not claim 008 SUCCESS. OAR-023 Ready not Accepted. Compiler stays PARTIAL. Skip-cert (OAR-022) not undone.

## Concerns / residual honesty gaps

- Bridge diagnostic `EVR-BRG-0001` is a closed-loop/bridge string (same pattern as `EVR-RQC-0001`); it is not added to the CERTIFIED eval/repair registry.
- PARTIAL that lowers can still `PASS` the fake loop; 008 compile status is carried as `requirements_compile_status` and must be read separately.
- Requirements compiler remains PARTIAL. Not M3. Not live. Not CERTIFIED. OAR-023 is Ready, not Accepted.
