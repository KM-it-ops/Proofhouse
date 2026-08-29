# MISSION-029 Task U3 — product-eval CLI parity

**Worktree:** `C:\AI\projects\PromptRig\.worktrees\mission-029-product-eval-cli`
**Branch:** `feature/mission-029-product-eval-cli`
**HEAD before:** `d68641c` (MISSION-027 OAR-021 Ready)

## What you implemented

Opt-in product eval on `promptrig-compiler` only (`promptrig` dual CLI untouched).

- New subcommand `evaluate-product` builds `ProductEvalRequest` and calls library `evaluate_product`. JSON `--json` envelope `data` is the serialized `ProductEvaluationResult` (tuples as lists). Flags: `--dataset`, `--rubric`, `--candidate-digest`, optional `--baseline-digest` / `--baseline-primary`, `--aggregation` default `any_fail`, `--json`. `compile_ok=True`, `security_ok=True`, `network_used=False`. `baseline_required` is true when a baseline digest or primary is supplied.
- Closed-loop opt-in flags `--product-eval-dataset` and `--product-eval-rubric` (both required together). Omit both = existing oracle-only default. One only → `PRG-CLI-0001`, non-zero exit, no loop/network. Both → `ClosedLoopOptions.product_eval`; `run_closed_loop` still replaces `candidate_digest`.
- Invalid dataset/rubric path → immutable `PRG-CLI-0001` envelope, exit 2, no network.
- Did not re-implement MISSION-027 engines. Did not change `api.py` `_LAZY_EXPORTS`. No `force_*` hooks. Product surface not CERTIFIED. Compiler stays PARTIAL.

## What you tested (commands + results)

RED (tests only, before `cli_compiler.py` change):

```text
uv run --with pytest python -m pytest tests/compiler/test_product_eval_cli_parity.py -v
```

Result: **3 failed, 4 passed** in 1.20s. Failures: `evaluate-product` unknown (empty stdout); unpaired `--product-eval-dataset` unknown. Passed: default closed-loop oracle-only (budgets 0/1/2); `doctor --json`.

GREEN (after CLI wiring):

```text
uv run --with pytest python -m pytest tests/compiler/test_product_eval_cli_parity.py -v
```

Result: **7 passed** in 0.32s, then **8 passed** after adding `test_closed_loop_product_eval_flags_reach_hook`.

Required suite:

```text
uv run --with pytest python -m pytest tests/compiler/test_product_eval_cli_parity.py tests/compiler/test_library_cli_parity.py tests/compiler/test_closed_loop_parity.py tests/compiler/test_eval_product.py tests/compiler/test_mission_012_certification.py -v
```

Result: **33 passed** in 1.40s.

## TDD Evidence

- **RED command:** `uv run --with pytest python -m pytest tests/compiler/test_product_eval_cli_parity.py -v`
- **RED reason:** `evaluate-product` was not a subcommand (argparse usage, no JSON on stdout). `--product-eval-dataset` was not a closed-loop flag (same). Doctor and oracle-only closed-loop already matched the default-bytes cases.
- **GREEN command:** same pytest file after `cli_compiler.py` changes, then the required five-file suite.
- **GREEN output:** 8 passed in `test_product_eval_cli_parity.py`; 33 passed in the verification suite.

## Files changed

- Create: `tests/compiler/test_product_eval_cli_parity.py`
- Modify: `src/promptrig/compiler/cli_compiler.py`
- Create: `docs/superpowers/reports/mission-029-task.md`
- Not committed: `uv.lock`

## Self-review findings

- Completeness: required happy / edge / error / integration scenarios are covered. Closed-loop hook reachability is covered with both flags vs oracle-only PASS.
- YAGNI: no new engine modules, no `api.py` wrapper, no PyYAML, no HTTP client, no OAR, no `promptrig` CLI change.
- Naming: `evaluate-product` vs closed-loop `--product-eval-*` matches the brief.
- Test honesty: 027 fixtures still yield product `FAIL` (`EVC-002` `compile_ok: false`, `any_fail`). Oracle is PASS (`compile_ok`/`security_ok` true, `network_used` false, `baseline_required` false). CLI envelope `status` is `success` when `evaluate_product` returns; product outcome lives in `data.status`.

## Concerns / residual honesty gaps

- `evaluate-product` exits 0 after a completed library call even when `data.status` is `FAIL`/`REGRESSION`. Invalid path / unpaired flags remain non-zero. Callers must read `data.status`.
- CLI aggregation default `any_fail` is a CLI default; library `ProductEvalRequest.aggregation` has no default.
- Product eval is implemented-not-CERTIFIED. Requirements compiler stays PARTIAL. No OAR Accept. U4 not started.
