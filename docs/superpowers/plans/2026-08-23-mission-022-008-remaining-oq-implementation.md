# MISSION-022 Remaining OQ-008 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OQ-008-003, OQ-008-005, and OQ-008-010 as fail-closed production gates in the existing sole `evaluate_contract_rules` engine (and producers where 010 emits records), and lock OQ-008-004/007/008/009 as not-built — without M3, without CERTIFIED, without Phase 4B exit.

**Architecture:** Same engine as MISSION-016–021. 005 is exact `0.1.0-draft` match (Class 0). 003 is undeterminable required-authority → BLOCKED (no frozen owner-only list, no Phase 6). 010 rejects bare-string assumption/open-question items on the canonical path. 004/007/008/009 are honesty + negative tests.

**Tech stack:** Python 3.11+, `promptrig.compiler`, pytest via `uv run --with pytest python -m pytest`.

## Global constraints

- Spec: `docs/superpowers/specs/2026-08-23-mission-022-008-remaining-oq-design.md`
- Orientation: `architecture/strategy/PROJECT_ORIENTATION.md`
- Baseline: local `main` @ `6331287`. Isolated worktree only during SDD: `C:/AI/projects/PromptRig/.worktrees/mission-022-remaining-oq` on `feature/mission-022-remaining-oq`. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 / Simple Mode UI forbidden.** No freeform NLP. No PRS language/grammar. No IR v0.2 fields. No alias-group implementation. Do not drop `-draft`.
- Exactly one rule-engine implementation (`evaluate_contract_rules`).
- OAR-016 is **Ready** until Boss says Accepted. OAR-009 through OAR-015 Accepted.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `architecture/mission-022-certification/README.md`
- Create: `tests/compiler/test_mission_022_schedule.py`
- Create: `tests/compiler/test_mission_022_oq.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md`
- Create: `MISSION_022_REPORT.md`
- Modify: `src/promptrig/compiler/requirements_contract.py` (003/005/010 gates; module docstring)
- Modify: `src/promptrig/compiler/requirements_produce.py` (010: never emit string assumptions/open_questions)
- Modify only if a new diagnostic is required: registry twins
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (021-style implemented vs remaining-lock wording)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/mission-021-certification/README.md` only if a sentence still says remaining OQs authorize no implementation after 022 lands

Reuse linked-artifact fixtures from `architecture/requirements-compiler-contract-v0.1/fixtures/linked_artifact_sets.json` via the same loader pattern as `tests/compiler/test_mission_016_engine.py`.

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-022-certification/README.md`
- Create: `tests/compiler/test_mission_022_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-015 Accepted; OQ-008-003/005/010 authorized to implement; 004/007/008/009 lock-only
- Produces: certification README; schedule test

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_022_schedule.py`:

```python
from pathlib import Path


def test_mission_022_implements_003_005_010_locks_004_007_008_009_not_m3() -> None:
    note = Path("architecture/mission-022-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "oq-008-003",
        "oq-008-005",
        "oq-008-010",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
        "partial",
        "oar-016",
        "phase 4b",
        "blocked",
    ):
        assert token in lower, token
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "alias" in lower
    assert "deferred" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    engine = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    assert "OQ-008-003" in engine
    assert "OQ-008-005" in engine
    assert "OQ-008-010" in engine
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_022_schedule.py -v`

Expected: FAIL because `architecture/mission-022-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-022-certification/README.md` stating:

- OAR-016 Ready (not Accepted).
- Implements OQ-008-003 (policy-defined authority, undeterminable BLOCKED), OQ-008-005 (exact `0.1.0-draft`), OQ-008-010 (structured-only assumption/open-question records).
- Locks OQ-008-004 (no identity merge / no alias-group object), OQ-008-007 (PRS language DEFERRED), OQ-008-008 (no continuation IR field), OQ-008-009 (no reasoning IR field).
- Not full MISSION-008 production compiler. Maturity PARTIAL. Not Phase 4B exit. Not M3. Not live. Not freeform NLP. Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`).
- No Phase 6 permission model. No frozen owner-only consequential category list.

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: FAIL on engine docstring / maturity wording until later tasks; keep this test red until Task 6 if needed, or land docstring stubs in Task 1 so the schedule test only requires the README + PARTIAL + DEFERRED, and add the engine-token asserts in Task 6.

**Preferred:** Task 1 schedule test **does not** assert engine source tokens. Move those three `OQ-008-00x` engine asserts to Task 6 so Task 1 can go green after the README exists.

- [ ] **Step 5: Commit**

```text
docs: add MISSION-022 certification README and schedule honesty test
```

---

### Task 2: OQ-008-005 exact version gate

**Files:**
- Modify: `src/promptrig/compiler/requirements_contract.py` (Class 0; docstring names OQ-008-005)
- Test: `tests/compiler/test_mission_022_oq.py`

**Interfaces:**
- Consumes: `REQUIREMENTS_CONTRACT_VERSION == "0.1.0-draft"`; linked SUCCESS set `LAS-POS-SUCCESS-001`
- Produces: exact-match rejection for any other version string

- [ ] **Step 1: Write failing tests**

Create `tests/compiler/test_mission_022_oq.py` with a LAS loader copied from `tests/compiler/test_mission_016_engine.py` (`_set`). Tests:

```python
from copy import deepcopy

from promptrig.compiler.requirements_contract import (
    REQUIREMENTS_CONTRACT_VERSION,
    compile_requirements,
)


def test_oq_008_005_exact_draft_version_still_required() -> None:
    assert REQUIREMENTS_CONTRACT_VERSION == "0.1.0-draft"
    result = compile_requirements(_set("LAS-POS-SUCCESS-001")["artifacts"])
    assert result.status == "SUCCESS"
    assert result.contract_version == "0.1.0-draft"


def test_oq_008_005_rejects_non_exact_versions() -> None:
    for version in ("0.1.0", "0.1.0-draft.1", ">=0.1.0", "", "1.0.0"):
        artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
        artifacts["intent_input"]["contract_version"] = version
        result = compile_requirements(artifacts)
        assert result.status == "INVALID_OUTPUT", version
        assert "RQC-VER-0001" in result.reason_codes, version
```

If `intent_input.contract_version` is not how LAS stores version, inspect `LAS-POS-SUCCESS-001` and mutate the field `context_from_artifacts` actually reads (`intent_input.contract_version`). Do not invent a second version field.

- [ ] **Step 2: Run tests — expect FAIL** if Class 0 currently defaults missing/other versions instead of `RQC-VER-0001` for every listed value. If they already pass, keep them as characterization and note that in the task commit: behavior existed; 022 names it as OQ-008-005.

- [ ] **Step 3: Implement only the gap**

Keep `if context["version"] != REQUIREMENTS_CONTRACT_VERSION: return "INVALID_OUTPUT", ["RQC-VER-0001"]`. If `context_from_artifacts` substitutes the default version when the input is missing or empty, stop substituting for explicit wrong/empty values. Never strip `-draft`. Never add range parsing.

- [ ] **Step 4: Re-run tests — expect PASS**

`uv run --with pytest python -m pytest tests/compiler/test_mission_022_oq.py -v`

- [ ] **Step 5: Commit**

```text
feat: name exact 0.1.0-draft match as OQ-008-005
```

---

### Task 3: OQ-008-003 undeterminable authority is BLOCKED

**Files:**
- Modify: `src/promptrig/compiler/requirements_contract.py` (`subject_authorized` / Class 6a; no owner-only category enum)
- Test: `tests/compiler/test_mission_022_oq.py`

**Interfaces:**
- Consumes: existing approval chain: subject → approval → `policy_ref` → accepted `approval_threshold` policy → `required_authority`
- Produces: BLOCKED when required authority cannot be uniquely determined

- [ ] **Step 1: Write failing tests**

Add tests that deepcopy `LAS-POS-SUCCESS-001` (or `LAS-POS-BLOCKED-001` if that set is already the undeterminable-authority case — inspect before duplicating):

1. Consequential requirement with `approval_refs` pointing at an approval whose `policy_ref` is missing/unresolvable → `BLOCKED`, `RQC-APR-0001` (or existing code if that set already uses another APR code — **do not invent a second authority-missing code**).
2. Two resolvable policies in the same chain with different `required_authority` values (`owner` vs `user`) → `BLOCKED` (undeterminable). Reuse `RQC-APR-0001` unless a specific undeterminable code already exists; do not add a frozen category list.
3. Negative: do **not** introduce `OWNER_ONLY_CATEGORIES` (or similar) in `requirements_contract.py`. Assert via schedule/honesty later; in this task, grep-guard in the test file:

```python
def test_oq_008_003_does_not_freeze_owner_only_categories() -> None:
    source = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    assert "OWNER_ONLY" not in source
    assert "owner_only_categories" not in source
```

If SUCCESS LAS has no consequential requirement, construct the smallest overlay: set one requirement `consequential: true`, add `approvals`/`policies` lists on the document according to existing schema IDs (`APR-*`, policy ids already used in LAS). Match field names in `subject_authorized` exactly (`policy_ref`, `required_authority`, `decision`, `scope`).

- [ ] **Step 2: Run — expect FAIL** where chain currently assumes an authority or skips undeterminable conflict.

- [ ] **Step 3: Implement fail-closed uniqueness**

In `subject_authorized`, `len(required) != 1` already returns False. Wire Class 6a so False → BLOCKED, never SUCCESS. If two policies can currently collapse via `set` uniqueness of the same token, add a test that distinct tokens stay undeterminable. Do not implement sessions, credentials, or Phase 6.

- [ ] **Step 4: Re-run Task 3 tests — PASS**

- [ ] **Step 5: Commit**

```text
feat: fail-closed undeterminable approval authority (OQ-008-003)
```

---

### Task 4: OQ-008-010 structured-only records

**Files:**
- Modify: `src/promptrig/compiler/requirements_contract.py` (Class 0 type check)
- Modify: `src/promptrig/compiler/requirements_produce.py` (emit lists of objects only)
- Test: `tests/compiler/test_mission_022_oq.py`

- [ ] **Step 1: Write failing tests**

```python
def test_oq_008_010_string_assumption_is_invalid_output() -> None:
    artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
    artifacts["requirements_document"]["assumptions"] = ["bare string is not canonical"]
    result = compile_requirements(artifacts)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes or "RQC-SEM-0001" in result.reason_codes


def test_oq_008_010_string_open_question_is_invalid_output() -> None:
    artifacts = deepcopy(_set("LAS-POS-SUCCESS-001")["artifacts"])
    artifacts["requirements_document"]["open_questions"] = ["bare string is not canonical"]
    result = compile_requirements(artifacts)
    assert result.status == "INVALID_OUTPUT"
```

Also: `produce_requirements` on a minimal envelope must leave `assumptions` as `[]` or a list of dicts, never `list[str]`.

Pick **one** diagnostic code and use it in both tests. Prefer `RQC-SCH-0001` unless the engine already classifies this as `RQC-SEM-0001`. Do not add a new registry code unless both existing codes would mis-label the case in honesty docs.

- [ ] **Step 2: Run — expect FAIL** if strings are skipped or treated as empty.

- [ ] **Step 3: Implement Class 0**

Before semantic evaluation, if any `assumptions` or `open_questions` item is not a `dict`, return `INVALID_OUTPUT` with the chosen code. Producers: do not append raw strings to those lists.

- [ ] **Step 4: Re-run — PASS**

- [ ] **Step 5: Commit**

```text
feat: reject string assumption and open-question records (OQ-008-010)
```

---

### Task 5: Lock OQ-008-004 / 007 / 008 / 009

**Files:**
- Test: `tests/compiler/test_mission_022_oq.py`
- Read-only: `architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md`
- Read-only: frozen IR schema under `architecture/` (the v0.1 IR schema file already used by `_default_ir_pointer_index`)

- [ ] **Step 1: Write failing/characterization tests**

```python
def test_oq_008_004_does_not_merge_requirement_identities() -> None:
    source = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    for banned in ("alias_group", "merge_identities", "coalesce_requirements"):
        assert banned not in source


def test_oq_008_007_prs_language_stays_deferred() -> None:
    text = Path("architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md").read_text(
        encoding="utf-8"
    )
    assert "DEFERRED" in text
    assert not Path("src/promptrig/compiler/prs_parser.py").exists()


def test_oq_008_008_009_ir_has_no_continuation_or_reasoning_fields() -> None:
    # Resolve the actual IR v0.1 schema path the engine indexes; fail if new properties appear.
    schema_text = Path("src/promptrig/compiler/requirements_contract.py").read_text(encoding="utf-8")
    assert "continuation_state" not in schema_text
    assert "reasoning_controls" not in schema_text
    ir_schema = Path("architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json")
    text = ir_schema.read_text(encoding="utf-8")
    assert "thought_signature" not in text
    assert "reasoning_effort" not in text
```

If `_default_ir_pointer_index` reads a different schema file, use that path instead. Do not add a second IR tree.

- [ ] **Step 2: Tests should PASS without product code** if lock-in is already true. If a banned symbol exists, stop and report — do not “fix” by implementing alias groups.

- [ ] **Step 3: Commit**

```text
test: lock OQ-008-004/007/008/009 as not-built
```

---

### Task 6: Honesty docs, OAR-016 Ready, report

**Files:**
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (021 footer: 001/002/006/003/005/010 implemented; 004/007/008/009 locked-not-built; M3 still unauthorized)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (compiler still PARTIAL; cite 022)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md` (022 in progress/closed as appropriate)
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md` (Ready)
- Create: `MISSION_022_REPORT.md`
- Modify: engine module docstring to name 003/005/010 implemented and 004/007/008/009 locked
- Modify: Task 1 schedule test to include engine-token asserts if they were deferred

- [ ] **Step 1: Extend schedule test** so README + OPEN_QUESTIONS + engine docstring + PARTIAL all agree. Run — FAIL until docs land.

- [ ] **Step 2: Write the docs.** OAR-016 Ready, not Accepted. Non-claims copied from the spec.

- [ ] **Step 3: Run**

```text
uv run --with pytest python -m pytest tests/compiler/test_mission_022_schedule.py tests/compiler/test_mission_022_oq.py tests/compiler/test_mission_021_schedule.py tests/compiler/test_mission_021_oq.py -v
```

Expected: PASS. Then a focused compiler suite if time (`tests/compiler/`).

- [ ] **Step 4: Commit**

```text
docs: Ready OAR-016 for MISSION-022 remaining OQ gates
```

---

### Task 7: Whole-branch review gate (no push)

- [ ] Run the same focused suites on the worktree HEAD.
- [ ] Confirm `origin/main` was not pushed.
- [ ] Confirm no M3/UI packages, no IR additive continuation/reasoning properties, no `OWNER_ONLY` category list.
- [ ] Stop for Boss Accept of OAR-016. Fast-forward local `main` only after Accept, same 016–021 pattern (GitHub backup branch; never push `origin/main` unless asked).

---

## Self-review

| Spec requirement | Task |
|---|---|
| OQ-008-003 fail-closed policy authority | Task 3 |
| OQ-008-005 exact version | Task 2 |
| OQ-008-010 structured-only | Task 4 |
| OQ-008-004/007/008/009 lock | Task 5 |
| Honesty / PARTIAL / OAR-016 Ready / no M3 | Tasks 1, 6 |
| No Phase 4B exit / no CERTIFIED | Tasks 1, 6, 7 |
