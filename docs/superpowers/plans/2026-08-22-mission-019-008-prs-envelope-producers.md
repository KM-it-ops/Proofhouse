# MISSION-019 PRS Envelope Producers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `produce_requirements` so structured `authoring_mode=prs` envelopes assemble canonical MISSION-008 artifact mappings and evaluate via `compile_requirements` — without implementing the deferred PRS language, without answering OQs, without M3/live/IR v0.2, and without claiming CERTIFIED or full Phase 4B exit.

**Architecture:** Same producer + compose path as 017/018. Add `prs` to `MODE_SOURCE_KINDS`. One rule engine. No new schema, CLI subcommand, or dependency.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

**Baseline:** local `main` @ `15d588a` (OAR-012 Accepted). **Branch / worktree (execution time only):** `feature/mission-019-prs-envelope-producers` in `C:/AI/projects/PromptRig/.worktrees/mission-019-prs-envelope-producers`. Spec: `docs/superpowers/specs/2026-08-22-mission-019-008-prs-envelope-producers-design.md`. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `15d588a`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- M3 / Simple Mode UI forbidden. `authoring_mode=prs` is the **008 envelope mode**, not a PRS language parser.
- RCD-008-009 / PRS language disposition remains **DEFERRED**. Do not add grammar, parser, or CONTRACT_CANDIDATE claims.
- Do **not** resolve OQ-008-001 through OQ-008-009.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler (authoring-prose still unauthorized).
- Exactly one rule-engine implementation.
- No new schema file, dependency, or `produce-requirements` CLI command.
- OAR-013 is **Ready** until Boss says Accepted. OAR-012/011/010 Accepted. OAR-009 Ready.
- Keep digest `promptrig-mission-017-producer`.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest`. Do not commit `uv.lock`.

## File structure

- Modify: `src/promptrig/compiler/requirements_produce.py` — add `prs` mode/kinds
- Modify: `src/promptrig/compiler/cli_compiler.py` — help names `prs`
- Modify: `tests/compiler/test_mission_017_produce.py` — remove/repurpose `test_prs_is_invalid_output` (prs becomes valid)
- Modify: `tests/compiler/test_mission_018_produce.py` — remove/repurpose `test_prs_still_invalid_output`
- Create: `tests/compiler/test_mission_019_schedule.py`, `tests/compiler/test_mission_019_produce.py`
- Create: `architecture/mission-019-certification/README.md`, `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-013.md`, `MISSION_019_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-019-certification/README.md`
- Create: `tests/compiler/test_mission_019_schedule.py`

**Interfaces:**
- Consumes: OAR-012 Accepted; OAR-009 Ready; OQs open; PRS language DEFERRED
- Produces: certification README; schedule test

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_019_schedule.py`:

```python
from pathlib import Path


def test_mission_019_not_full_008_not_m3_oqs_open_prs_language_deferred() -> None:
    note = Path("architecture/mission-019-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "produce_requirements" in lower
    assert "prs" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "freeform" in lower or "authoring-prose" in lower or "prose" in lower
    assert "oq-008-001" in lower
    assert "oar-013" in lower
    assert "deferred" in lower
    assert "grammar" in lower or "parser" in lower or "language" in lower
    assert "phase 4b" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    for qid in (
        "OQ-008-001",
        "OQ-008-002",
        "OQ-008-003",
        "OQ-008-004",
        "OQ-008-005",
        "OQ-008-006",
        "OQ-008-007",
        "OQ-008-008",
        "OQ-008-009",
    ):
        assert qid in oq
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/compiler/test_mission_019_schedule.py -v`

Expected: FAIL (missing README)

- [ ] **Step 3: Write certification README**

Name: `produce_requirements`, prs envelope (structured), canonical, PARTIAL, not full 008, not M3 UI, no live, OQ-008-001, OAR-013 Ready, PRS **language** still DEFERRED (not grammar/parser), Phase 4B, file/api/simple/developer remain.

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-019-certification/README.md tests/compiler/test_mission_019_schedule.py
git commit -m "test: add MISSION-019 honesty schedule for prs envelope producers"
```

---

### Task 2: Producer + produce tests

**Files:**
- Modify: `src/promptrig/compiler/requirements_produce.py`
- Modify: `tests/compiler/test_mission_017_produce.py`
- Modify: `tests/compiler/test_mission_018_produce.py`
- Create: `tests/compiler/test_mission_019_produce.py`

**Interfaces:**
- Consumes: MODE_SOURCE_KINDS from 018
- Produces: `prs` mode; prior `prs` rejection tests updated

- [ ] **Step 1: Write failing tests**

In `test_mission_017_produce.py`: delete or rewrite `test_prs_is_invalid_output` so it no longer expects INVALID_OUTPUT for `authoring_mode=prs` with matching `kind=prs` (move positive coverage to 019). Prefer deleting that test if 019 covers it.

In `test_mission_018_produce.py`: delete `test_prs_still_invalid_output` (019 owns prs validity).

Create `tests/compiler/test_mission_019_produce.py`:

```python
def test_prs_envelope_produces_prs_sources() -> None: ...
def test_wrong_kind_for_prs_is_schema_invalid() -> None:  # prs + kind=file → INVALID_OUTPUT
def test_imports_rejected_on_prs() -> None: ...
```

- [ ] **Step 2: Run focused tests — expect FAIL**

- [ ] **Step 3: Implement**

```python
MODE_SOURCE_KINDS = {
    ...
    "prs": frozenset({"prs", "decision", "contract"}),
}
```

Update module docstring to mention prs envelopes. Keep digest.

- [ ] **Step 4: Run**

`uv run python -m pytest tests/compiler/test_mission_019_produce.py tests/compiler/test_mission_018_produce.py tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_016_engine.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_produce.py tests/compiler/test_mission_019_produce.py tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_018_produce.py
git commit -m "feat: produce prs envelopes into canonical 008 artifacts"
```

---

### Task 3: CLI help + OAR-013 Ready + honesty docs

**Files:**
- Modify: `src/promptrig/compiler/cli_compiler.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-013.md`
- Create: `MISSION_019_REPORT.md`
- Modify: maturity map, deferred registry, README.md
- Modify: `tests/compiler/test_mission_019_produce.py` (CLI help assertion)
- Update 017/018 help tests if they assert exact help strings without `prs`

- [ ] **Step 1: Failing CLI help test** asserting `prs` in compile-requirements help

- [ ] **Step 2: Update CLI help** to name file/api/simple/developer/prs

- [ ] **Step 3: Write OAR-013 Ready** (not Accepted). Certified-if-accepted: prs envelope producers alongside file/api/simple/developer; still unauthorized: PRS language/grammar, authoring-prose, M3, OQs, full 008, Phase 4B exit. OAR-009 Ready. OAR-010–012 Accepted.

- [ ] **Step 4: Maturity / deferred / README / report** — PARTIAL; remaining gaps: authoring-prose, OQs, full 008, M3; note structured prs envelope landed; PRS language still DEFERRED.

- [ ] **Step 5: Suite**

`uv run python -m pytest tests/compiler tests/evaluation tests/requirements -q`

- [ ] **Step 6: Commit**

```powershell
git commit -m "docs: MISSION-019 report and OAR-013 draft for prs envelope producers"
```

---

## Spec coverage check

- prs envelope → canonical: Task 2
- prior modes unchanged: Task 2 suite
- PRS language still deferred: Tasks 1, 3
- One engine / no new schema/CLI command: Tasks 2–3
- Honesty / PARTIAL / OAR-013 Ready / no M3: Tasks 1, 3
