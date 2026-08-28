# Review pack — PromptRig compiler slice at 2831cda

You are reviewing one exact snapshot of the code: git SHA `2831cda`.
Do not review later branches. A sibling job called MISSION-027 may add evaluation engines later. Those engines are not in this snapshot.

## What this system is

PromptRig is a compiler. It turns structured requirements into an internal record, then into a fake offline artifact, then checks that artifact with a small deterministic checker.

The requirements compiler is **PARTIAL**. That word means: some structured paths work; the product is not finished; it is **not CERTIFIED**.

The fake closed loop (compile → check → bounded repair, offline only) is already CERTIFIED. That is a narrow path. It is not the full product.

## Architecture

These files are the slice:

- `src/promptrig/compiler/requirements_contract.py` — `compile_requirements_input` and `evaluate_contract_rules` (the only RC-065 rule engine).
- `src/promptrig/compiler/requirements_plain_produce.py` — turns constrained `plain_language_v0` prose into the same canonical records.
- `src/promptrig/compiler/cli_compiler.py` — `promptrig-compiler compile-requirements`. Certified path sets `network_allowed=false`.
- `src/promptrig/compiler/closed_loop.py` — fake-adapter loop only. No live providers. `ClosedLoopOptions.repair_budget` accepts only `{0,1,2}`.
- `src/promptrig/compiler/evaluation.py` — `evaluate_deterministic`. Checks compile success, security, and whether the network was used. The primary score may be 0, 1, or absent (`None`). If `baseline_required` is true but its digest is missing, evaluation returns `BLOCKED` with `EVR-BSL-0001`. This is the oracle, not a rubric/dataset product engine.
- `src/promptrig/compiler/repair.py` — `plan_repair` must not weaken security (`EVR-SEC-0001`). Test-only hooks must not be reachable from production CLI.

Already on this snapshot: tests `test_mission_023_produce.py`, `test_mission_024_schedule.py`, `test_mission_025_schedule.py`.

A valid constrained Goal + numbered list can compile SUCCESS after OAR-017. Locked questions OQ-008-004, 007, 008, 009 are still not built.

## Security

- No network on the certified path. `network_allowed=false`.
- No credentials. No live model calls.
- Repair must not drop security constraints (`EVR-SEC-0001`).
- `ClosedLoopOptions.repair_budget` in `src/promptrig/compiler/closed_loop.py` permits only `{0,1,2}`.
- Production CLI must not expose `force_*` test hooks.
- Freeform natural language is still blocked. Simple Mode UI (M3) is not this phase.

## What this pack does not claim

- Not CERTIFIED requirements compiler.
- Not full MISSION-008 production compiler.
- Not Roadmap Phase 4B exit.
- Not a rubric/dataset evaluation engine (that is MISSION-027, not this SHA).
- Not enterprise SAST.
- Not certification of the full Phase 4B boundary.

## Questions you must answer

Write answers in `VERDICT.md`, not here.

1. Architecture: does this slice match the claims above, or is something over-claimed or missing?
2. Security: is the offline / no-credential / no-weaken-security story true in these files, or did you find a hole?
3. Blockers: anything that should stop owner acceptance of this pack?
4. Accept or reject the pack as a review of SHA `2831cda` only.
