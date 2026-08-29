# MISSION-032 Task U6 — Bounded live OpenAI execution

**Worktree:** `C:\AI\projects\PromptRig\.worktrees\mission-032-live-openai`
**Branch:** `feature/mission-032-live-openai`
**HEAD before:** `d5388ea` (U5 IR v0.2 planning)
**Q1:** unpicked (no ratified first live model; no vault; no ceiling table)

## What you implemented

Fail-closed opt-in single-request live OpenAI execution in a **new module** (`execution.py`), not a flag on `closed_loop.py`. Adapters remain offline lowerers. `compile --adapter openai` still lowers only. `closed-loop` stays fake-only / `EVR-NET-0001` if `network_allowed`.

- Call-time required: `opt_in`, model, token/cost ceilings, credential env name and/or value. Missing any → fail closed (`EXE-OPT-0001`, `EXE-CRED-0001` AE4, `EXE-MODEL-0001`, `EXE-CEIL-0001`).
- Credential store is caller-supplied env var name / value at invoke time, not a vault. CLI accepts `--credential-env` only.
- Egress allowlist: `https://api.openai.com` + `/v1/` only; else `EXE-EGRESS-0001`.
- Optional extra `[project.optional-dependencies] live = ["httpx"]`. Default install unchanged (`jsonschema` + `rfc8785`). Missing extra when a real send is requested → `EXE-DEP-0001`.
- One send, idempotency key, no retry on success. Cancel-before-send preserves evidence.
- Lazy `api.execute_openai` / `LiveOpenAIRequest` / `ExecutionResult`. New CLI `promptrig-compiler execute-openai`.
- pytest marker `live` + `addopts = -m "not live"`. Default-suite happy path uses a test double.
- Architecture: execution contract, threat model, redaction rules. OAR-025 Ready (021=027, 022=028, 023=030, 024=031). Compiler PARTIAL. Live DEFERRED-to-opt-in, not CERTIFIED. Skip-cert law not undone.
- No continuation fields on IR v0.1 (evidence-only / omitted for single-request). U7/U8/U9 not started.

## What you tested (commands + results)

Characterization (before live code; existing offline goldens):

```text
uv run --with pytest python -m pytest tests/compiler/test_no_network_and_determinism.py tests/compiler/test_openai_adapter.py tests/compiler/test_fake_adapter_golden.py tests/compiler/test_mission_012_certification.py -v
```

Result: **33 passed** in 1.79s, including `test_compile_with_openai_adapter_makes_no_network_access`.

Required suite (after implementation):

```text
uv run --with pytest python -m pytest tests/compiler/test_live_execution_fail_closed.py tests/compiler/test_no_network_and_determinism.py tests/compiler/test_mission_012_certification.py tests/compiler/test_mission_032_schedule.py -v
```

Result: **38 passed** in 1.80s.

Live marker exclusion: `pytest tests/compiler/live --collect-only` → 1 deselected / 0 selected. No real-network tests run.

## TDD Evidence

- **RED command:** `uv run --with pytest python -m pytest tests/compiler/test_live_execution_fail_closed.py -v`
- **RED reason:** `ModuleNotFoundError: No module named 'promptrig.compiler.execution'` (collection error; 0 items).
- **GREEN command:** required four-file suite above.
- **GREEN output:** 38 passed in 1.80s.

## Files changed

- Create: `src/promptrig/compiler/execution.py`
- Modify: `src/promptrig/compiler/api.py` (lazy exports)
- Modify: `src/promptrig/compiler/cli_compiler.py` (`execute-openai`)
- Modify: `src/promptrig/compiler/__init__.py` (honesty)
- Modify: `pyproject.toml` (optional `live` extra; pytest `live` marker + addopts)
- Create: `tests/compiler/test_live_execution_fail_closed.py`
- Create: `tests/compiler/test_mission_032_schedule.py`
- Create: `tests/compiler/live/test_live_openai_q1_gate.py`
- Modify: `tests/compiler/test_no_network_and_determinism.py`
- Create: `architecture/live-openai-execution-v0.1/EXECUTION_CONTRACT.md`
- Create: `architecture/mission-032-certification/README.md`
- Create: `architecture/mission-032-certification/THREAT_MODEL.md`
- Create: `architecture/mission-032-certification/REDACTION.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-025.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Live execution row stays `DEFERRED`; evidence notes opt-in / Q1 unpicked / not CERTIFIED)
- Create: `docs/superpowers/reports/mission-032-task.md`
- Not committed: `uv.lock`
- Not modified: frozen IR schema; `closed_loop.py`; openai adapter `lower()`; U7/U8/U9

## Self-review findings

- Completeness: AE4, missing model/ceilings, no-opt-in no-sockets, closed-loop `EVR-NET-0001`, compile openai offline, happy double + byte-stable compile, redaction, egress, missing httpx, cancel evidence, no retry, CLI, lazy export, schedule honesty, live marker exclusion.
- YAGNI: no IR v0.2 fields, no vault, no price table, no default model id, no closed-loop live flag, no real-network run.
- Naming: `execute_openai` / `execute-openai` kept off `closed-loop`.
- Test honesty: default suite is fail-closed + test double. Marker `live` is not collected. Q1 remains an owner gate. OAR-025 is Ready, not Accepted. Live is DEFERRED-to-opt-in, not CERTIFIED.

## Concerns / residual honesty gaps

- The real `httpx` send path is implemented but not exercised against the network (intentional; owner must pick Q1 first).
- `max_cost_usd` is a required declared ceiling, not a priced-token enforcement table (that would pick Q1).
- Optional `httpx` is imported inside `_httpx_send` so default install does not require it.
- Maturity map Live row remains `DEFERRED` with opt-in evidence; it is not promoted to CERTIFIED or IMPLEMENTED_NOT_CERTIFIED.
