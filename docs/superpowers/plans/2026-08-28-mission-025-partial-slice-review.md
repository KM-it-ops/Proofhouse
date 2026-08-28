# MISSION-025 Same-Host PARTIAL Slice Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use PromptRig SDD (`promptrig-sdd-implementer` + `promptrig-sdd-task-reviewer`). Superpowers SDD only if that pair is unavailable. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record a bounded same-host architecture and security review of the current PARTIAL requirements-compiler slice. Do not promote CERTIFIED. Do not change the producer or engine.

**Architecture:** Docs + schedule test + review artifact. Approach A (Boss 2026-08-28). Task 2 (REVIEW.md) MUST be a different agent than Task 1.

**Tech stack:** Python 3.11+, pytest via `uv run --with pytest python -m pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-28-mission-025-partial-slice-review-design.md`
- Orientation: `architecture/strategy/PROJECT_ORIENTATION.md`
- Baseline: local `main` @ `56d484e`. Isolated worktree only: `C:/AI/projects/PromptRig/.worktrees/mission-025-partial-slice-review` on `feature/mission-025-partial-slice-review`. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 / Simple Mode UI forbidden.** No freeform NLP. No PRS language/grammar. No IR v0.2. Do not unlock OQ-008-004/007/008/009.
- Do not change `produce_plain_language_requirements`, `evaluate_contract_rules`, envelope producers, IR schema, or closed-loop defaults.
- Do not implement the evaluation/repair product bar (rubric/dataset engine, production regression gate).
- OAR-019 is **Ready** until Boss says Accepted. OAR-009 through OAR-018 stay Accepted and must not be rewritten.
- Leave 020–024 certification READMEs and `MISSION_020_REPORT.md` through `MISSION_024_REPORT.md` frozen.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, full MISSION-008 production compiler, third-party audit, or enterprise SAST.
- Same-host independence limit is binding: this review is not “independent architecture and security review certify the boundary” in the Phase 4B exit-criteria sense.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `architecture/mission-025-certification/README.md`
- Create: `architecture/mission-025-certification/REVIEW.md`
- Create: `tests/compiler/test_mission_025_schedule.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md`
- Create: `MISSION_025_REPORT.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only: 025 review pack; keep `PARTIAL`; keep 004/007/008/009 locked)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph (add 025 review / OAR-019 Ready; keep “policy only” or “authorize no production implementation” somewhere in the file)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets (add 025 same-host review; do not unlock locks; eval/repair product bar still outstanding)
- Modify: root `README.md` — **append** a MISSION-025 current-state bullet. Do not rewrite 020–024 bullets.

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-025-certification/README.md`
- Create: `tests/compiler/test_mission_025_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-018 Accepted; this campaign is a same-host PARTIAL-slice review pack; maturity stays PARTIAL
- Produces: certification README; schedule test that goes green after the README exists (no producer/engine asserts; do not require `REVIEW.md` or `OAR-019.md` yet)

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_025_schedule.py`:

```python
from pathlib import Path


def test_mission_025_same_host_review_not_certified_not_m3() -> None:
    note = Path("architecture/mission-025-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-019",
        "phase 4b",
        "same-host",
        "independent",
        "review",
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
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_018_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md")
    assert oar_018_path.is_file()
    oar_018_text = oar_018_path.read_text(encoding="utf-8")
    status_018 = next(
        line for line in oar_018_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_018.lower()
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_025_schedule.py -v`

Expected: FAIL because `architecture/mission-025-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-025-certification/README.md` with this exact content:

```markdown
# MISSION-025 Same-Host PARTIAL Slice Review

**Status:** OAR-019 Ready (not Accepted).
**Baseline:** Campaign COMPILER remaining work after MISSION-024 / OAR-018 Accepted.
**Scope:** Same-host architecture and security **review** of the current PARTIAL compiler slice. Not a producer/engine change.

This is a remaining-Phase-4B review pack. It does not promote the requirements compiler.

## What this mission records (narrow)

- **OAR-019 Ready (not Accepted).** This record is a same-host review pack until Boss Accepts.
- Requirements compiler stays **PARTIAL**. **Not CERTIFIED**. **Not full** MISSION-008 production compiler. Not full Roadmap **Phase 4B** exit.
- **Independence limit:** same-host separate reviewer pass. Not a third-party audit. Not enterprise SAST. Not independent architecture and security review that certifies the Phase 4B boundary.
- Remaining blockers after this pack:
  - Evaluation/repair product bar (**rubric**/dataset engine, production regression gate) still missing — fake-oracle evaluation remains the CERTIFIED slice only.
  - **OQ-008-004** / **OQ-008-007** / **OQ-008-008** / **OQ-008-009** remain locked-not-built.
- Constrained `plain_language_v0` valid grammar still compiles SUCCESS after OAR-017; this review does not reopen that mapping.
- `EVR-SEC-0001` and `network_allowed=false` unchanged.

## Non-claims

- Not CERTIFIED. Not full MISSION-008. Not Phase 4B exit.
- Not **M3** / **Simple Mode** UI.
- **Not a live** provider path; no credentials; `network_allowed` remains false on the certified path.
- **Not freeform** NLP; not live model-assisted suggestion; no PRS language/grammar unlock.
- No IR v0.2 fields. No Phase 6–9 product surfaces.
- OAR-009 through OAR-018 stay **Accepted** historical snapshots.
```

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add MISSION-025 same-host review honesty inventory and schedule test
```

---

### Task 2: REVIEW.md (separate reviewer; not the Task 1 implementer)

**Files:**
- Create: `architecture/mission-025-certification/REVIEW.md`
- Modify: `tests/compiler/test_mission_025_schedule.py` (assert REVIEW.md required sections and tokens)

**Interfaces:**
- Consumes: Task 1 README; named slice files in the spec
- Produces: REVIEW.md filled from actually reading those files; schedule test green on README + REVIEW (still no OAR-019.md)

**Controller:** Dispatch a fresh implementer that did **not** write Task 1. Do not let the Task 1 agent fill REVIEW.md.

**Named files the reviewer must read before writing Findings:**

- `src/promptrig/compiler/requirements_contract.py`
- `src/promptrig/compiler/requirements_plain_produce.py`
- `src/promptrig/compiler/cli_compiler.py`
- `src/promptrig/compiler/closed_loop.py`
- `src/promptrig/compiler/evaluation.py`
- `src/promptrig/compiler/repair.py`
- `tests/compiler/test_mission_023_produce.py`
- `tests/compiler/test_mission_024_schedule.py`

- [ ] **Step 1: Extend the schedule test (RED)**

Append to `test_mission_025_same_host_review_not_certified_not_m3`:

```python
    review = Path("architecture/mission-025-certification/REVIEW.md")
    assert review.is_file()
    review_text = review.read_text(encoding="utf-8")
    review_lower = review_text.lower()
    for heading in (
        "## architecture",
        "## security",
        "## findings",
        "## independence limit",
        "## non-claims",
    ):
        assert heading in review_lower, heading
    for token in (
        "partial",
        "same-host",
        "evr-sec-0001",
        "network_allowed",
        "compile_requirements_input",
        "evaluate_contract_rules",
    ):
        assert token in review_lower, token
    assert "not certified" in review_lower or "not certif" in review_lower
    assert "m3" in review_lower or "simple mode" in review_lower
    assert "not a live" in review_lower or "no live" in review_lower
    assert "named files read" in review_lower
```

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_025_schedule.py -v`

Expected: FAIL because `architecture/mission-025-certification/REVIEW.md` does not exist.

- [ ] **Step 2: Read the named files**

Read every path listed above. Do not write REVIEW.md before this step. Do not change any of those files.

- [ ] **Step 3: Write REVIEW.md**

Create `architecture/mission-025-certification/REVIEW.md`. Use the required sections and honesty sentences below **verbatim**. Fill **Findings** only after Step 2. Do not pre-script a clean bill of health. If nothing material is in-scope for the claimed PARTIAL slice, Findings must still list the files read and say so explicitly.

Required file shape (honesty sections fixed; Findings filled by the reviewer):

```markdown
# MISSION-025 Review — PARTIAL compiler slice (same-host)

## Architecture

Reviewed library `compile_requirements_input` / `evaluate_contract_rules` (sole RC-065), `produce_plain_language_requirements` in `requirements_plain_produce.py`, and `promptrig-compiler compile-requirements`. Constrained `plain_language_v0` valid grammar compiles SUCCESS after OAR-017. Requirements compiler remains PARTIAL. Fake closed loop remains the CERTIFIED evaluation/repair slice. This review does not change the producer or engine.

## Security

Certified path stays `network_allowed=false` with no credentials. `EVR-SEC-0001` and repair budgets `{0,1,2}` unchanged. Production CLI must not expose `force_*` / test hooks. Freeform NLP remains parse-blocked. Not a live provider path.

## Findings

Named files read:
- `src/promptrig/compiler/requirements_contract.py`
- `src/promptrig/compiler/requirements_plain_produce.py`
- `src/promptrig/compiler/cli_compiler.py`
- `src/promptrig/compiler/closed_loop.py`
- `src/promptrig/compiler/evaluation.py`
- `src/promptrig/compiler/repair.py`
- `tests/compiler/test_mission_023_produce.py`
- `tests/compiler/test_mission_024_schedule.py`

<REVIEWER: after reading those files, either (a) list each in-scope finding as `- file:line — severity — what is wrong — why it matters for the claimed PARTIAL slice` or (b) write exactly: `No material architecture/security defect found inside the claimed PARTIAL slice (library/CLI/constrained plain_language_v0 SUCCESS path). Residual 4B holes remain: evaluation/repair product bar; OQ-008-004/007/008/009 locked; not CERTIFIED; not Phase 4B exit.` Do not invent findings. Do not omit a real in-scope defect to keep the pack pretty.>

## Independence limit

Same-host separate reviewer pass from the Task 1 honesty-shell implementer. Not a third-party audit. Not enterprise SAST. Not independent architecture and security review that certifies the Phase 4B boundary.

## Non-claims

Not CERTIFIED. Not full MISSION-008. Not Phase 4B exit. Not M3 / Simple Mode UI. Not a live provider path. Not freeform NLP. No IR v0.2. Evaluation/repair product bar (rubric/dataset engine, production regression gate) remains outstanding.
```

Replace the `<REVIEWER: ...>` placeholder with the real Findings body before saving. The saved file must **not** contain the string `REVIEWER:` or `TODO`.

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add MISSION-025 same-host PARTIAL slice REVIEW.md
```

---

### Task 3: OAR-019 Ready and current-state docs

**Files:**
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md`
- Create: `MISSION_025_REPORT.md`
- Modify: `tests/compiler/test_mission_025_schedule.py` (assert OAR-019 Ready, not Accepted)
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets
- Modify: root `README.md` (append MISSION-025 bullet; do not rewrite 020–024)

**Interfaces:**
- Consumes: Task 1 README; Task 2 REVIEW.md
- Produces: Ready OAR-019; current-state honesty

- [ ] **Step 1: Extend the schedule test (RED)**

Append to `test_mission_025_same_host_review_not_certified_not_m3`:

```python
    oar_019_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md")
    assert oar_019_path.is_file()
    oar_019_text = oar_019_path.read_text(encoding="utf-8")
    status_019 = next(
        line for line in oar_019_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_019.lower()
    assert "accepted" not in status_019.lower()
```

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_025_schedule.py -v`

Expected: FAIL (OAR-019.md missing).

- [ ] **Step 2: Write OAR-019 Ready**

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md`:

```markdown
# OAR-019 — MISSION-025 Same-Host PARTIAL Compiler Slice Review

**Status:** Ready (not Accepted).

**Certified if accepted:** a same-host architecture and security review of the current PARTIAL requirements-compiler slice is recorded in `architecture/mission-025-certification/REVIEW.md` without promoting the requirements compiler to CERTIFIED and without claiming full Roadmap Phase 4B exit or a full MISSION-008 production compiler. No producer/engine change. Independence limit: same-host, not third-party, not enterprise SAST, not Phase 4B-exit boundary certification. Evaluation/repair product bar (rubric/dataset engine, production regression gate) remains outstanding; the fake-adapter deterministic oracle stays the CERTIFIED evaluation/repair slice. OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST. Do not drop `-draft`. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-018 remain Accepted.
```

- [ ] **Step 3: Update current-state docs**

`PROJECT_ORIENTATION.md`:

- Date stays honest: laptop `main` is ahead of `origin/main`. Do not push unless Boss says to.
- Picture 3: add `Job 025 ........... in    (same-host PARTIAL slice review; not CERTIFIED)` under Job 024.
- Picture 4 / short answers: last closed *Accepted* job remains 024 / OAR-018. Last honesty job becomes 025 / OAR-019 Ready (not Accepted). Compiler still PARTIAL. Simple Mode still no.
- Point last accept at OAR-018; prior accept OAR-017; add 025 spec/plan as the open job until Accepted.

`OPEN_QUESTIONS.md` last paragraph: after the 024 sentence, add MISSION-025 same-host PARTIAL-slice review (OAR-019 Ready). Keep OQ-008-004/007/008/009 locked-not-built and M3 / CERTIFIED / Phase 4B unauthorized. Keep a “policy only” or “authorize no production implementation” phrase somewhere in the file.

`CAPABILITY_MATURITY_MAP.md`: keep `| Requirements compiler | `PARTIAL` |`. In that row, state MISSION-025 same-host PARTIAL-slice review (OAR-019 Ready). Do not promote CERTIFIED.

`DEFERRED_AND_REJECTED_WORK.md` blocking bullets: add 025 same-host review (OAR-019 Ready); keep locks; evaluation/repair product bar still outstanding.

Root `README.md`: append a MISSION-025 bullet (same-host review + PARTIAL + not CERTIFIED + not M3 + OAR-019 Ready + independence limit). Leave 020–024 bullets unchanged.

- [ ] **Step 4: Write MISSION_025_REPORT.md**

Mirror `MISSION_024_REPORT.md` shape: what landed, HEAD placeholder (`Task 2 SHA` until the Task 3 commit exists), tests run, non-claims (PARTIAL, not CERTIFIED, not Phase 4B, not M3, same-host independence limit, OQs 004/007/008/009 locked, eval/repair product bar outstanding, OAR-019 Ready).

- [ ] **Step 5: Run honesty tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_025_schedule.py tests/compiler/test_mission_024_schedule.py tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```text
docs: add OAR-019 Ready and current-state MISSION-025 honesty
```

---

## Execution notes

- Worktree: `C:/AI/projects/PromptRig/.worktrees/mission-025-partial-slice-review`
- Branch: `feature/mission-025-partial-slice-review`
- Task 2 must be a different agent than Task 1.
- After Task 3: stop for Boss Accept of OAR-019. Do not merge. Do not push `origin/main`.
- Spec coverage: honesty README → Task 1; REVIEW.md → Task 2; OAR-019 + current-state → Task 3; no producer; frozen OARs 009–018.
