# MISSION-033 Task U7 — Sealed offline whole-configuration benchmark

**Worktree:** `C:\AI\projects\PromptRig\.worktrees\mission-033-sealed-benchmark`
**Branch:** `feature/mission-033-sealed-benchmark`
**HEAD before:** `bfb091b` (U6 live fail-closed)
**Track:** offline-only. No live track. U8/U9 not started.

## What you implemented

Sealed **offline** whole-configuration benchmark: versioned manifest contract, validator, runner, and evidence sealer.

- Manifest contract under `architecture/sealed-benchmark-v0.1/` (version, environment digest, source hashes, secrets policy, budgets `{0,1,2}`, repetition default 3, `network_mode=offline`, `network_allowed=false`).
- Runner `src/promptrig/compiler/benchmark.py`. Hidden tests stay on the runner (`config_accessible_paths` empty). Default 3 autonomous attempts; smaller budget only if owner-ratified with a note.
- Published scorer is U2 product eval (`evaluate_product`). Oracle `evaluate_deterministic` is rank-1 compile/security/network gate. Sealer rejects product-eval PASS when oracle has `EVR-SEC-0001` (`BMK-ORC-0001`).
- Infrastructure missing hidden suite → `INFRA` / `BMK-INF-0001`, not product FAIL.
- Mutated source hash fails validation (`BMK-HASH-0001`). Two identical configs, same sealed env → matching scores.
- Honesty: OAR-026 Ready (021=027, 022=028, 023=030, 024=031, 025=032). Compiler PARTIAL. Not CERTIFIED. Not a published claim. `review-cycles/v0.4/` is historical, not a result. Skip-cert law not undone. Root README does not treat a v0.4 document as a benchmark result.
- No CLI, no live track, no U8/U9, `review-cycles/v0.4/` not edited.

## What you tested (commands + results)

Required suite:

```text
uv run --with pytest python -m pytest tests/compiler/test_benchmark_manifest_validation.py tests/compiler/test_mission_033_schedule.py tests/compiler/test_eval_product.py tests/compiler/test_evaluation_engine.py tests/compiler/test_no_network_and_determinism.py -v
```

Result: **45 passed** in 0.96s.

## TDD Evidence

- **RED command:** `uv run --with pytest python -m pytest tests/compiler/test_benchmark_manifest_validation.py -v`
- **RED reason:** `ModuleNotFoundError: No module named 'promptrig.compiler.benchmark'` (collection error; 0 items).
- **GREEN command:** required five-file suite above.
- **GREEN output:** 45 passed in 0.96s.

## Files changed

- Create: `src/promptrig/compiler/benchmark.py`
- Create: `tests/compiler/test_benchmark_manifest_validation.py`
- Create: `tests/compiler/test_mission_033_schedule.py`
- Create: `architecture/sealed-benchmark-v0.1/BENCHMARK_MANIFEST.md`
- Create: `architecture/sealed-benchmark-v0.1/benchmark-manifest.schema.json`
- Create: `architecture/mission-033-certification/README.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-026.md`
- Modify: `README.md` (MISSION-033 status; v0.4 is not a benchmark result)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Benchmark runner `IMPLEMENTED_NOT_CERTIFIED`, not a published claim)
- Create: `docs/superpowers/reports/mission-033-task.md`
- Not committed: `uv.lock`
- Not modified: `review-cycles/v0.4/`; frozen IR schema; U8/U9; live track

## Self-review findings

- Completeness: manifest validation, mutated hash, offline-only network, secrets policy, 3-attempt default, owner-ratified smaller budget, identical-config determinism, infra vs product FAIL, oracle security vs published PASS, hidden tests inaccessible, schedule honesty, skip-cert not undone, frozen IR unchanged.
- YAGNI: no live track, no benchmark CLI, no U8/U9, no marketing scores.
- Naming: BMK-* codes stay off the frozen PRG diagnostic registry.
- Test honesty: OAR-026 is Ready, not Accepted. Runner is not CERTIFIED and not a published claim. v0.4 docs are not results.

## Concerns / residual honesty gaps

- No independent dry-run publication was performed; that remains an owner gate before any public score.
- Environment digest is declared and sealed; this freeze does not pin a container image.
- Product eval remains implemented and not CERTIFIED. Oracle stays the only CERTIFIED eval slice.
