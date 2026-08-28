# MISSION-026 Independent-Person Review Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use PromptRig SDD (`promptrig-sdd-implementer` + `promptrig-sdd-task-reviewer`). Superpowers SDD only if that pair is unavailable. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a plain-language architecture and security review pack of the PARTIAL compiler slice and fake-adapter eval/repair oracle at SHA `2831cda`. Agents write the pack. Humans write the verdict. Do not promote CERTIFIED. Do not change the producer or engine.

**Architecture:** Docs + schedule test + pack + empty verdict template. Approach A (Boss 2026-08-28). SDD stops at OAR-020 Ready.

**Tech stack:** Python 3.11+, pytest via `uv run --with pytest python -m pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-28-mission-026-independent-review-pack-design.md`
- Orientation: `architecture/strategy/PROJECT_ORIENTATION.md`
- Baseline: local `main` after the 026/027 spec commit (`9d606fd` or later plan commit). Isolated worktree only: `C:/AI/projects/PromptRig/.worktrees/mission-026-independent-review-pack` on `feature/mission-026-independent-review-pack`. Do not edit the `main` checkout.
- Reviewed compiler tree pin: `2831cda`. The pack must name that SHA. Spec/plan commits after it do not change the reviewed files.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 / Simple Mode UI forbidden.** No freeform NLP. No PRS language/grammar. No IR v0.2. Do not unlock OQ-008-004/007/008/009.
- Do not change `produce_plain_language_requirements`, `evaluate_contract_rules`, envelope producers, IR schema, `evaluation.py`, `repair.py`, or closed-loop defaults.
- Do not implement the evaluation/repair product bar (that is MISSION-027).
- OAR-020 is **Ready** until Boss says Accepted. OAR-009 through OAR-019 stay Accepted and must not be rewritten.
- Leave `architecture/mission-020-certification` through `mission-025-certification` READMEs and `MISSION_020_REPORT.md` through `MISSION_025_REPORT.md` frozen.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, full MISSION-008 production compiler, enterprise SAST, or that this pack certifies the Phase 4B boundary.
- Agents must not fill `VERDICT.md` findings. No agent-authored “clean bill of health.”
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `architecture/mission-026-certification/README.md`
- Create: `architecture/mission-026-certification/PACK.md`
- Create: `architecture/mission-026-certification/INSTRUCTIONS.md`
- Create: `architecture/mission-026-certification/VERDICT.md`
- Create: `tests/compiler/test_mission_026_schedule.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md`
- Create: `MISSION_026_REPORT.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only: 026 pack Ready; keep `PARTIAL`; keep 004/007/008/009 locked)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets
- Modify: root `README.md` — **append** a MISSION-026 current-state bullet. Do not rewrite 020–025 bullets.

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-026-certification/README.md`
- Create: `tests/compiler/test_mission_026_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-019 Accepted; this campaign is an owner + second-person pack at `2831cda`
- Produces: certification README; schedule test green after README exists (do not require PACK/INSTRUCTIONS/VERDICT/OAR-020 yet)

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_026_schedule.py`:

```python
from pathlib import Path


def test_mission_026_pack_not_certified_not_m3() -> None:
    note = Path("architecture/mission-026-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "partial",
        "oar-020",
        "phase 4b",
        "2831cda",
        "second person",
        "verdict",
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
    assert "027" in text
    assert "enterprise sast" in lower
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_019_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md")
    assert oar_019_path.is_file()
    oar_019_text = oar_019_path.read_text(encoding="utf-8")
    status_019 = next(
        line for line in oar_019_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_019.lower()
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_026_schedule.py -v`

Expected: FAIL because `architecture/mission-026-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-026-certification/README.md` with this exact content:

```markdown
# MISSION-026 Independent-Person Review Pack

**Status:** OAR-020 Ready (not Accepted).
**Baseline:** Campaign COMPILER remaining work after MISSION-025 / OAR-019 Accepted.
**Scope:** Plain-language architecture and security **pack** of the current PARTIAL compiler slice and fake-adapter eval/repair oracle at SHA `2831cda`. Not a producer/engine change. Humans write the verdict.

This is a remaining-Phase-4B review pack. It does not promote the requirements compiler.

## What this mission records (narrow)

- **OAR-020 Ready (not Accepted).** This record is an owner + second-person pack until Boss Accepts.
- Requirements compiler stays **PARTIAL**. **Not CERTIFIED**. **Not full** MISSION-008 production compiler. Not full Roadmap **Phase 4B** exit.
- **Independence limit:** owner review plus a second person. Not enterprise SAST. Not a same-host agent filling findings. Not independent architecture and security review that certifies the Phase 4B boundary while MISSION-027 is a sibling and locked OQs remain.
- Reviewed tree pin: **`2831cda`**. MISSION-027 is a sibling branch from the same baseline and is **not** in this tree.
- Remaining blockers after this pack:
  - Evaluation/repair product bar (**rubric**/dataset engine, production regression gate) still missing on this tree — fake-oracle evaluation remains the CERTIFIED slice only.
  - **OQ-008-004** / **OQ-008-007** / **OQ-008-008** / **OQ-008-009** remain locked-not-built.
- Constrained `plain_language_v0` valid grammar still compiles SUCCESS after OAR-017; this pack does not reopen that mapping.
- `EVR-SEC-0001` and `network_allowed=false` unchanged.

## Non-claims

- Not CERTIFIED. Not full MISSION-008. Not Phase 4B exit.
- Not **M3** / **Simple Mode** UI.
- **Not a live** provider path; no credentials; `network_allowed` remains false on the certified path.
- **Not freeform** NLP; not live model-assisted suggestion; no PRS language/grammar unlock.
- No IR v0.2 fields. No Phase 6–9 product surfaces.
- OAR-009 through OAR-019 stay **Accepted** historical snapshots.
- Agents do not fill `VERDICT.md`.
```

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add MISSION-026 review-pack honesty inventory and schedule test
```

---

### Task 2: PACK, INSTRUCTIONS, empty VERDICT

**Files:**
- Create: `architecture/mission-026-certification/PACK.md`
- Create: `architecture/mission-026-certification/INSTRUCTIONS.md`
- Create: `architecture/mission-026-certification/VERDICT.md`
- Modify: `tests/compiler/test_mission_026_schedule.py`

**Interfaces:**
- Consumes: Task 1 README; named slice files (read-only)
- Produces: pack + instructions + empty verdict template; schedule test green on README + PACK + INSTRUCTIONS + VERDICT (still no OAR-020.md)

**Named files the pack describes (do not edit them):**

- `src/promptrig/compiler/requirements_contract.py`
- `src/promptrig/compiler/requirements_plain_produce.py`
- `src/promptrig/compiler/cli_compiler.py`
- `src/promptrig/compiler/closed_loop.py`
- `src/promptrig/compiler/evaluation.py`
- `src/promptrig/compiler/repair.py`
- `tests/compiler/test_mission_023_produce.py`
- `tests/compiler/test_mission_024_schedule.py`
- `tests/compiler/test_mission_025_schedule.py`

- [ ] **Step 1: Extend the schedule test (RED)**

Append to `test_mission_026_pack_not_certified_not_m3`:

```python
    pack = Path("architecture/mission-026-certification/PACK.md")
    assert pack.is_file()
    pack_text = pack.read_text(encoding="utf-8")
    pack_lower = pack_text.lower()
    for heading in (
        "## what this system is",
        "## architecture",
        "## security",
        "## what this pack does not claim",
        "## questions you must answer",
    ):
        assert heading in pack_lower, heading
    for token in (
        "2831cda",
        "partial",
        "compile_requirements_input",
        "evaluate_contract_rules",
        "evaluate_deterministic",
        "evr-sec-0001",
        "network_allowed",
        "027",
    ):
        assert token in pack_lower, token
    assert "not certified" in pack_lower or "not certif" in pack_lower

    instructions = Path("architecture/mission-026-certification/INSTRUCTIONS.md")
    assert instructions.is_file()
    inst_lower = instructions.read_text(encoding="utf-8").lower()
    assert "verdict.md" in inst_lower
    assert "i don't know" in inst_lower or "i do not know" in inst_lower
    assert "pack.md" in inst_lower

    verdict = Path("architecture/mission-026-certification/VERDICT.md")
    assert verdict.is_file()
    verdict_text = verdict.read_text(encoding="utf-8")
    verdict_lower = verdict_text.lower()
    for heading in (
        "## architecture",
        "## security",
        "## blockers",
        "## accept or reject",
        "## unknowns",
    ):
        assert heading in verdict_lower, heading
    assert "human fills" in verdict_lower
    assert "no material architecture/security defect" not in verdict_lower
```

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_026_schedule.py -v`

Expected: FAIL because PACK.md does not exist.

- [ ] **Step 2: Write PACK.md**

Create `architecture/mission-026-certification/PACK.md` with this exact content:

```markdown
# Review pack — PromptRig compiler slice at 2831cda

You are reviewing one exact snapshot of the code: git SHA `2831cda`.
Do not review later branches. A sibling job called MISSION-027 may add evaluation engines later. Those engines are not in this snapshot.

## What this system is

PromptRig is a compiler. It turns structured requirements into an internal record, then into a fake offline artifact, then checks that artifact with a small deterministic checker.

The requirements compiler is **PARTIAL**. That word means: some structured paths work; the product is not finished; it is **not CERTIFIED**.

The fake closed loop (compile → check → bounded repair, offline only) is already CERTIFIED. That is a narrow path. It is not the full product.

## Architecture

These files are the slice:

- `requirements_contract.py` — `compile_requirements_input` and `evaluate_contract_rules` (the only RC-065 rule engine).
- `requirements_plain_produce.py` — turns constrained `plain_language_v0` prose into the same canonical records.
- `cli_compiler.py` — `promptrig-compiler compile-requirements`. Certified path sets `network_allowed=false`.
- `closed_loop.py` — fake-adapter loop only. No live providers.
- `evaluation.py` — `evaluate_deterministic`. Checks compile success, security, and whether the network was used. Scores are 0 or 1. This is the oracle, not a rubric/dataset product engine.
- `repair.py` — at most 0, 1, or 2 repair tries. Must not weaken security (`EVR-SEC-0001`). Test-only hooks must not be reachable from production CLI.

Already on this snapshot: tests `test_mission_023_produce.py`, `test_mission_024_schedule.py`, `test_mission_025_schedule.py`.

A valid constrained Goal + numbered list can compile SUCCESS after OAR-017. Locked questions OQ-008-004, 007, 008, 009 are still not built.

## Security

- No network on the certified path. `network_allowed=false`.
- No credentials. No live model calls.
- Repair must not drop security constraints (`EVR-SEC-0001`).
- Repair budgets are only `{0,1,2}`.
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
```

- [ ] **Step 3: Write INSTRUCTIONS.md**

Create `architecture/mission-026-certification/INSTRUCTIONS.md` with this exact content:

```markdown
# Instructions for the second reviewer

You do not need PromptRig jargon. You do need to judge architecture and security.

## Read in this order

1. This file.
2. `PACK.md` (the review).
3. `README.md` (honesty limits — what we are not claiming).
4. The named source files listed in `PACK.md` if you can open them. If you cannot, say so under Unknowns. Do not guess.
5. Fill `VERDICT.md` only. Do not edit `PACK.md`.

## What to ignore

- Strategy books under `architecture/strategy/` except where `PACK.md` already stated a fact.
- MISSION-027 code if it appears later. This review is SHA `2831cda` only.
- Marketing, benchmarks, live APIs, Simple Mode UI.

## How to record a finding

In `VERDICT.md`, use one bullet per finding:

- file path and, if you have it, line
- what is wrong
- why it matters for architecture or security

If you are unsure, write it under Unknowns. **I don't know** is allowed.

## Verdict

Accept means: the pack is an honest architecture and security review of this snapshot.
Reject means: the pack is wrong, incomplete, or unsafe to treat as that review.
```

- [ ] **Step 4: Write empty VERDICT.md**

Create `architecture/mission-026-certification/VERDICT.md` with this exact content:

```markdown
# Verdict — MISSION-026 pack at 2831cda

**Human fills this file. Agents must not fill findings.**

Reviewer name:

Date:

## Architecture

(human fills)

## Security

(human fills)

## Blockers

(human fills)

## Accept or Reject

(human fills: Accept or Reject)

## Unknowns

(human fills; I don't know is allowed)
```

- [ ] **Step 5: Re-run schedule test**

Same pytest command. Expected: PASS.

- [ ] **Step 6: Commit**

```text
docs: add MISSION-026 PACK, reviewer instructions, and empty verdict
```

---

### Task 3: OAR-020 Ready and current-state docs

**Files:**
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md`
- Create: `MISSION_026_REPORT.md`
- Modify: `tests/compiler/test_mission_026_schedule.py`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullets
- Modify: root `README.md` (append MISSION-026 bullet; do not rewrite 020–025)

**Interfaces:**
- Consumes: Task 1 README; Task 2 pack files
- Produces: Ready OAR-020; current-state honesty

- [ ] **Step 1: Extend the schedule test (RED)**

Append to `test_mission_026_pack_not_certified_not_m3`:

```python
    oar_020_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md")
    assert oar_020_path.is_file()
    oar_020_text = oar_020_path.read_text(encoding="utf-8")
    status_020 = next(
        line for line in oar_020_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status_020.lower()
    assert "accepted" not in status_020.lower()
```

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_026_schedule.py -v`

Expected: FAIL (OAR-020.md missing).

- [ ] **Step 2: Write OAR-020 Ready**

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md`:

```markdown
# OAR-020 — MISSION-026 Independent-Person PARTIAL Slice Review Pack

**Status:** Ready (not Accepted).

**Certified if accepted:** a plain-language architecture and security review pack of the current PARTIAL requirements-compiler slice and fake-adapter eval/repair oracle at SHA `2831cda` is recorded in `architecture/mission-026-certification/PACK.md` without promoting the requirements compiler to CERTIFIED and without claiming full Roadmap Phase 4B exit or a full MISSION-008 production compiler. No producer/engine change. Independence limit: owner plus a second person; not enterprise SAST; not Phase 4B-exit boundary certification; humans fill `VERDICT.md`. MISSION-027 is a sibling and is not in the reviewed tree. Evaluation/repair product bar remains outstanding on this SHA; the fake-adapter deterministic oracle stays the CERTIFIED evaluation/repair slice. OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST. Do not drop `-draft`. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-019 remain Accepted.
```

- [ ] **Step 3: Update current-state docs**

`PROJECT_ORIENTATION.md`:

- Date stays honest: laptop `main` is ahead of `origin/main`. Do not push unless Boss says to.
- Picture 3: add `Job 026 ........... in    (independent-person review pack; OAR-020 Ready; not CERTIFIED)` under Job 025.
- Picture 4 / short answers: last closed *Accepted* job remains 025 / OAR-019. Last honesty job becomes 026 / OAR-020 Ready (not Accepted). Compiler still PARTIAL. Simple Mode still no.
- Point last accept at OAR-019; add 026 spec/plan as the open job until Accepted.

`OPEN_QUESTIONS.md` last paragraph: after the 025 sentence, add MISSION-026 independent-person pack (OAR-020 Ready). Keep OQ-008-004/007/008/009 locked-not-built and M3 / CERTIFIED / Phase 4B unauthorized. Keep a “policy only” or “authorize no production implementation” phrase somewhere in the file.

`CAPABILITY_MATURITY_MAP.md`: keep `| Requirements compiler | `PARTIAL` |`. In that row, state MISSION-026 independent-person pack (OAR-020 Ready). Do not promote CERTIFIED. Do not claim Phase 4B-boundary certification.

`DEFERRED_AND_REJECTED_WORK.md` blocking bullets: add 026 pack (OAR-020 Ready, owner + second person, not 4B-exit certification); keep locks; evaluation/repair product bar still outstanding on this tree (027 sibling).

Root `README.md`: append a MISSION-026 bullet (independent-person pack + PARTIAL + not CERTIFIED + not M3 + OAR-020 Ready + SHA `2831cda` + humans fill verdict). Leave 020–025 bullets unchanged.

- [ ] **Step 4: Write MISSION_026_REPORT.md**

Mirror `MISSION_025_REPORT.md` shape: what landed, HEAD placeholder (`Task 3 SHA` until that commit exists), tests run, non-claims (PARTIAL, not CERTIFIED, not Phase 4B, not M3, owner+second-person independence limit, OQs 004/007/008/009 locked, eval/repair product bar outstanding on this SHA, OAR-020 Ready, VERDICT empty).

- [ ] **Step 5: Run honesty tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_026_schedule.py tests/compiler/test_mission_025_schedule.py tests/compiler/test_mission_024_schedule.py tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```text
docs: add OAR-020 Ready and current-state MISSION-026 honesty
```

---

## Execution notes

- Worktree: `C:/AI/projects/PromptRig/.worktrees/mission-026-independent-review-pack`
- Branch: `feature/mission-026-independent-review-pack`
- After Task 3: stop for Boss to send the pack and fill `VERDICT.md`. Do not Accept OAR-020 inside SDD. Do not push `origin/main`.
- Spec coverage: honesty README → Task 1; PACK/INSTRUCTIONS/VERDICT → Task 2; OAR-020 + current-state → Task 3; no producer; frozen OARs 009–019.
