# MISSION-024 Remaining Phase 4B Honesty Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use PromptRig SDD (`promptrig-sdd-implementer` + `promptrig-sdd-task-reviewer`). Superpowers SDD only if that pair is unavailable. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record remaining Phase 4B compiler blockers honestly. Do not promote CERTIFIED. Do not change the producer or engine.

**Architecture:** Docs + schedule test only. Approach A (Boss 2026-08-24).

**Tech stack:** Python 3.11+, pytest via `uv run --with pytest python -m pytest`.

## Global constraints

- Spec: `docs/superpowers/specs/2026-08-24-mission-024-4b-honesty-design.md`
- Orientation: `architecture/strategy/PROJECT_ORIENTATION.md`
- Baseline: local `main` @ `e9c7b0f`. Isolated worktree only: `C:/AI/projects/PromptRig/.worktrees/mission-024-4b-certified-slice` on `feature/mission-024-4b-certified-slice`. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 / Simple Mode UI forbidden.** No freeform NLP. No PRS language/grammar. No IR v0.2. Do not unlock OQ-008-004/007/008/009.
- Do not change `produce_plain_language_requirements`, `evaluate_contract_rules`, envelope producers, IR schema, or closed-loop defaults.
- OAR-018 is **Ready** until Boss says Accepted. OAR-009 through OAR-017 stay Accepted and must not be rewritten.
- Leave 020–023 certification READMEs and `MISSION_020_REPORT.md` through `MISSION_023_REPORT.md` frozen.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `architecture/mission-024-certification/README.md`
- Create: `tests/compiler/test_mission_024_schedule.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md`
- Create: `MISSION_024_REPORT.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only: 024 inventory; keep `PARTIAL`; keep 004/007/008/009 locked)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph (add 024 inventory / OAR-018 Ready; keep “policy only” or “authorize no production implementation” somewhere in the file)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets (add 024 inventory; do not unlock locks)
- Modify: root `README.md` — **append** a MISSION-024 current-state bullet. Do not rewrite 020–023 bullets.

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-024-certification/README.md`
- Create: `tests/compiler/test_mission_024_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-017 Accepted; this campaign is remaining-4B inventory; maturity stays PARTIAL
- Produces: certification README; schedule test that goes green after the README exists (no producer/engine asserts; do not require `OAR-018.md` yet)

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_024_schedule.py`:

```python
from pathlib import Path


def test_mission_024_remaining_4b_inventory_not_certified_not_m3() -> None:
    note = Path("architecture/mission-024-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-018",
        "phase 4b",
        "independent",
        "inventory",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
    ):
        assert token in lower, token
    assert "not certified" in lower or "not certif" in lower
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "rubric" in lower or "dataset" in lower
    assert "review" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_017_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-017.md")
    assert oar_017_path.is_file()
    oar_017_text = oar_017_path.read_text(encoding="utf-8")
    status_017 = next(
        line for line in oar_017_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_017.lower()
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_024_schedule.py -v`

Expected: FAIL because `architecture/mission-024-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-024-certification/README.md` stating:

- OAR-018 Ready (not Accepted).
- This mission is a remaining-Phase-4B **inventory**, not a producer/engine change.
- Requirements compiler stays PARTIAL. Not CERTIFIED. Not full MISSION-008. Not Phase 4B exit.
- Remaining blockers: no independent architecture and security review of the current PARTIAL compiler slice; evaluation/repair product bar (rubric/dataset engine, production regression gate) still missing — fake-oracle evaluation remains the CERTIFIED slice only; OQ-008-004 / 007 / 008 / 009 remain locked-not-built.
- Constrained `plain_language_v0` valid grammar still compiles SUCCESS after OAR-017; this inventory does not reopen that mapping.
- Not M3. Not live. Not freeform NLP.
- OAR-009 through OAR-017 stay Accepted historical snapshots.

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add MISSION-024 remaining 4B honesty inventory and schedule test
```

---

### Task 2: OAR-018 Ready and current-state docs

**Files:**
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md`
- Create: `MISSION_024_REPORT.md`
- Modify: `tests/compiler/test_mission_024_schedule.py` (assert OAR-018 Ready, not Accepted)
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets
- Modify: root `README.md` (append MISSION-024 bullet; do not rewrite 020–023)

**Interfaces:**
- Consumes: Task 1 README
- Produces: Ready OAR-018; current-state honesty

- [ ] **Step 1: Extend the schedule test (RED)**

Append to `test_mission_024_remaining_4b_inventory_not_certified_not_m3`:

```python
    oar_018_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md")
    assert oar_018_path.is_file()
    oar_018_text = oar_018_path.read_text(encoding="utf-8")
    status_018 = next(
        line for line in oar_018_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_018.lower()
    assert "accepted" not in status_018.lower()
```

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_024_schedule.py -v`

Expected: FAIL (OAR-018.md missing).

- [ ] **Step 2: Write OAR-018 Ready**

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md`:

```markdown
# OAR-018 — MISSION-024 Remaining Phase 4B Compiler Honesty Inventory

**Status:** Ready (not Accepted).

**Certified if accepted:** remaining Phase 4B compiler blockers are inventoried in `architecture/mission-024-certification/README.md` without promoting the requirements compiler to CERTIFIED and without claiming full Roadmap Phase 4B exit or a full MISSION-008 production compiler. No producer/engine change. Independent architecture and security review of the current PARTIAL compiler slice is recorded as outstanding. Evaluation/repair product bar (rubric/dataset engine, production regression gate) remains outstanding; the fake-adapter deterministic oracle stays the CERTIFIED evaluation/repair slice. OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST. Do not drop `-draft`. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-017 remain Accepted.
```

- [ ] **Step 3: Update current-state docs**

`PROJECT_ORIENTATION.md`:

- Picture 3: Job 024 in (remaining 4B inventory; not CERTIFIED).
- Picture 4 / short answers: last closed *Accepted* job remains 023 / OAR-017. Last code/honesty job becomes 024 / OAR-018 Ready (not Accepted). Compiler still PARTIAL. Simple Mode still no.
- Keep “do not push unless you say to.” Local `main` is ahead of `origin/main`.
- Point last accept at OAR-017; add 024 spec/plan as the open job until Accepted.

`OPEN_QUESTIONS.md` last paragraph: add MISSION-024 remaining-4B inventory (OAR-018 Ready). Keep OQ-008-004/007/008/009 locked-not-built and M3 / CERTIFIED / Phase 4B unauthorized. Keep a “policy only” or “authorize no production implementation” phrase somewhere in the file.

`CAPABILITY_MATURITY_MAP.md`: keep `| Requirements compiler | `PARTIAL` |`. In that row, state MISSION-024 inventoried remaining 4B blockers (OAR-018 Ready). Do not promote CERTIFIED.

`DEFERRED_AND_REJECTED_WORK.md` blocking bullets: add 024 inventory (OAR-018 Ready); keep locks.

Root `README.md`: append a MISSION-024 bullet (inventory + PARTIAL + not CERTIFIED + not M3 + OAR-018 Ready). Leave 020–023 bullets unchanged.

- [ ] **Step 4: Write MISSION_024_REPORT.md**

Mirror `MISSION_023_REPORT.md` shape: what landed, HEAD placeholder, tests run, non-claims (PARTIAL, not CERTIFIED, not Phase 4B, not M3, OQs 004/007/008/009 locked, OAR-018 Ready).

- [ ] **Step 5: Run honesty tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_024_schedule.py tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```text
docs: add OAR-018 Ready and current-state MISSION-024 honesty
```

---

## Execution notes

- Worktree: `C:/AI/projects/PromptRig/.worktrees/mission-024-4b-certified-slice`
- Branch: `feature/mission-024-4b-certified-slice`
- After Task 2: stop for Boss Accept of OAR-018. Do not merge. Do not push `origin/main`.
- Spec coverage: remaining-hole inventory → Tasks 1–2; no producer; frozen OARs 009–017.
