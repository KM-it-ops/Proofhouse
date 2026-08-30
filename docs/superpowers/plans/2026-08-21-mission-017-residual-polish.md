# MISSION-017 Residual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the three recorded MISSION-017 whole-branch review leftovers: CLI `input` help names file/api envelopes, producer reuses the contract version constant, maturity map attributes produce vs compose to the correct files.

**Architecture:** No new producer, schema, CLI command, or rule engine. Import-cycle fix: `compile_requirements_input` locally imports `produce_requirements` so `requirements_produce` can import `REQUIREMENTS_CONTRACT_VERSION` from `requirements_contract`.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

**Baseline:** local `main` @ `8f84fb8`. **Branch / worktree (execution time only):** `feature/mission-017-residual-polish` in `C:/AI/projects/PromptRig/.worktrees/mission-017-residual-polish`. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `8f84fb8`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers, no provider SDK/HTTP client.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Do not add profiles.
- Repair budgets remain `{0,1,2}`; `EVR-SEC-0001` unchanged.
- Simple Mode UI-only semantics stay forbidden. M3 is not this work.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no DFR-003 live-provider path.
- Do **not** resolve OQ-008-001 through OQ-008-009. Unknown answers stay `BLOCKED` / `PARTIAL` / gap evidence.
- Do **not** claim full Roadmap Phase 4B exit. Do **not** graduate Requirements compiler from `PARTIAL`. Do **not** claim a full MISSION-008 production compiler.
- Exactly one rule-engine implementation: do not copy RC-065; do not extend `context_from_artifacts` with text matching; do not stuff `artifacts.diagnostics` to force reason codes.
- `compile_requirements` still requires `requirements_document` for the canonical path.
- Production CLI must never expose `force_*` / test hooks. No new `produce-requirements` command.
- Ponytail-full: no new schema file, no new dependency, no new constants module, fewest files.
- OAR-011 is **Ready** until Boss says Accepted. OAR-010 stays Accepted. OAR-009 stays Ready.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest` or `.venv/Scripts/python -m pytest`.
- Do not commit `uv.lock`.
- Do not add simple/developer/prs producers.

## File structure

- Modify: `src/promptrig/compiler/cli_compiler.py` — positional `input` help
- Modify: `src/promptrig/compiler/requirements_produce.py` — import `REQUIREMENTS_CONTRACT_VERSION`
- Modify: `src/promptrig/compiler/requirements_contract.py` — local-import `produce_requirements` in `compile_requirements_input`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` — split produce/compose file attribution
- Modify: `tests/compiler/test_mission_017_produce.py` — identity + help + map wording tests

---

### Task 1: CLI help, shared version, maturity attribution

**Files:**
- Modify: `src/promptrig/compiler/cli_compiler.py`
- Modify: `src/promptrig/compiler/requirements_produce.py`
- Modify: `src/promptrig/compiler/requirements_contract.py`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`
- Modify: `tests/compiler/test_mission_017_produce.py`

**Interfaces:**
- Consumes: MISSION-017 producers already on `8f84fb8`; OAR-011 Ready
- Produces: help/constant/map leftovers only; compiler still `PARTIAL`

- [ ] **Step 1: Write the failing tests**

Append to `tests/compiler/test_mission_017_produce.py`:

```python
def test_producer_reuses_contract_version_constant() -> None:
    from promptrig.compiler import requirements_contract
    from promptrig.compiler import requirements_produce

    assert (
        requirements_produce.REQUIREMENTS_CONTRACT_VERSION
        is requirements_contract.REQUIREMENTS_CONTRACT_VERSION
    )


def test_compile_requirements_input_help_names_envelope() -> None:
    from promptrig.compiler.cli_compiler import build_parser

    parser = build_parser()
    req = None
    for action in parser._subparsers._group_actions:
        req = action.choices.get("compile-requirements")
        if req is not None:
            break
    assert req is not None
    help_text = req.format_help()
    assert "file/api envelope" in help_text
    input_action = next(a for a in req._actions if getattr(a, "dest", None) == "input")
    assert input_action.help == (
        "Path to canonical artifact JSON or file/api envelope, or '-' for stdin."
    )


def test_maturity_map_splits_produce_and_compose_files() -> None:
    text = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "`produce_requirements` in `requirements_produce.py`" in text
    assert "`compile_requirements_input` in `requirements_contract.py`" in text
    assert "| Requirements compiler | `PARTIAL`" in text
    assert "requirements_produce.py` / `requirements_contract.py`" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py::test_producer_reuses_contract_version_constant tests/compiler/test_mission_017_produce.py::test_compile_requirements_input_help_names_envelope tests/compiler/test_mission_017_produce.py::test_maturity_map_splits_produce_and_compose_files -v`

Expected: FAIL (duplicate constant identity; input help lacks envelope; slash path still present)

- [ ] **Step 3: Implement the three leftovers**

In `src/promptrig/compiler/cli_compiler.py`, change only the positional argument:

```python
    p_req.add_argument(
        "input",
        help="Path to canonical artifact JSON or file/api envelope, or '-' for stdin.",
    )
```

In `src/promptrig/compiler/requirements_contract.py`:

- Remove the module-top `from .requirements_produce import produce_requirements`.
- In `compile_requirements_input`, after the canonical `requirements_document` branch, local-import and call produce. Comment: local import avoids a cycle because `requirements_produce` imports `REQUIREMENTS_CONTRACT_VERSION` from this module.

```python
def compile_requirements_input(
    payload: Mapping[str, Any] | object,
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult:
    if isinstance(payload, Mapping) and "requirements_document" in payload:
        return compile_requirements(payload, registry=registry)
    # Local import avoids a cycle: produce_requirements imports REQUIREMENTS_CONTRACT_VERSION from this module.
    from .requirements_produce import produce_requirements

    return compile_requirements(produce_requirements(payload), registry=registry)
```

In `src/promptrig/compiler/requirements_produce.py`:

- Delete the local `REQUIREMENTS_CONTRACT_VERSION = "0.1.0-draft"` assignment.
- Add a top-level import (with other imports): `from .requirements_contract import REQUIREMENTS_CONTRACT_VERSION`.

In `architecture/strategy/CAPABILITY_MATURITY_MAP.md` Requirements compiler evidence cell, replace the slash attribution so the cell contains:

- `` `produce_requirements` in `requirements_produce.py` ``
- `` `compile_requirements_input` in `requirements_contract.py` ``
- Keep `| Requirements compiler | `PARTIAL` ``
- Do not mark OAR-011 Accepted. Do not promote maturity.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_017_schedule.py tests/compiler/test_mission_016_api.py tests/compiler/test_mission_016_engine.py -q`

Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/cli_compiler.py src/promptrig/compiler/requirements_produce.py src/promptrig/compiler/requirements_contract.py architecture/strategy/CAPABILITY_MATURITY_MAP.md tests/compiler/test_mission_017_produce.py
git commit -m "fix: land MISSION-017 leftover help, version import, and map attribution"
```

---

## Spec coverage check

- CLI input help names file/api envelope: Task 1
- Shared `REQUIREMENTS_CONTRACT_VERSION` identity: Task 1
- Maturity map split file attribution; compiler stays PARTIAL: Task 1
- No second engine; no produce-requirements CLI; OQs open; OAR-011 Ready: Global Constraints

## Pre-flight (plan vs review rubric)

- Tests assert identity and exact help, not tautologies. Governs.
- Local import in `compile_requirements_input` is the documented cycle exception. Governs.
- Reviewer flags CERTIFIED / M3 / OQ answers as defects. Governs.

## Worktree / stacking

- Branch: `feature/mission-017-residual-polish`
- Worktree: `.worktrees/mission-017-residual-polish`
- Baseline: local `main` @ `8f84fb8`
- After whole-branch review: stop. No push, PR, merge, or OAR-011 Accepted unless Boss asks.
