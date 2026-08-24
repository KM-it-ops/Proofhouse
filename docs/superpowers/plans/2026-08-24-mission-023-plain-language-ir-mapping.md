# MISSION-023 Constrained Prose IR Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire numbered requirement lines and constraint lines in the existing `plain_language_v0` producer so a valid write-up compiles `SUCCESS` instead of `BLOCKED`.

**Architecture:** Same producer as MISSION-020 (`produce_plain_language_requirements`). Goal already emits `direct` → `/objective/goal`. Change numbered and constraint maps from `unresolved` (no pointer) to `direct` with `/requirements/{n}/statement` and `/behavior/constraints/{n}`. Assign pointers with `enumerate` at emit time, before the existing id sort. Do not change the parser, the rule engine, envelope producers, IR schema, or closed-loop defaults.

**Tech stack:** Python 3.11+, `promptrig.compiler`, pytest via `uv run --with pytest python -m pytest`.

## Global constraints

- Spec: `docs/superpowers/specs/2026-08-24-mission-023-plain-language-ir-mapping-design.md`
- Orientation: `architecture/strategy/PROJECT_ORIENTATION.md`
- Baseline: local `main` @ `e2cc33b`. Isolated worktree only during SDD: `C:/AI/projects/PromptRig/.worktrees/mission-023-plain-language-ir-mapping` on `feature/mission-023-plain-language-ir-mapping`. Do not edit the `main` checkout.
- Live identifiers (do not invent 022-doc dialect names): profile `plain_language_v0`; records `REQ-PL-GOAL` / `REQ-PL-001` / `REQ-PL-C001`; outcome `direct`; field `target_pointer`; compile `compile_requirements_input`; producer `produce_plain_language_requirements`; blocked code `RQC-BLK-0001`; parse codes `PL-PARSE-*`.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 / Simple Mode UI forbidden.** No freeform NLP. No PRS language/grammar. No IR v0.2 fields. Do not unlock OQ-008-004/007/008/009.
- Exactly one rule-engine implementation (`evaluate_contract_rules`). Do not change it in this mission.
- Do not invent default instruction/constraint mappings the user did not write.
- Pointer indices are 0-based parse order at emit time, **before** id sort.
- OAR-017 is **Ready** until Boss says Accepted. OAR-009 through OAR-016 stay Accepted and must not be rewritten.
- Leave 020–022 certification READMEs and `MISSION_020_REPORT.md` / `021` / `022` frozen. The 020 schedule test still requires the word `blocked` in the 020 README — do not strip it.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `architecture/mission-023-certification/README.md`
- Create: `tests/compiler/test_mission_023_schedule.py`
- Create: `tests/compiler/test_mission_023_produce.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-017.md`
- Create: `MISSION_023_REPORT.md`
- Modify: `src/promptrig/compiler/requirements_plain_produce.py` (numbered + constraint maps only)
- Modify: `tests/compiler/test_mission_020_produce.py` (live SUCCESS assertions)
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`, `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: root `README.md` — **add** a MISSION-023 current-state bullet. Do not rewrite 020–022 bullets (historical snapshots).

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-023-certification/README.md`
- Create: `tests/compiler/test_mission_023_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-016 Accepted; this campaign maps numbered/constraint prose; maturity stays PARTIAL
- Produces: certification README; schedule test that can go green after the README exists (no producer/engine asserts in this task)

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_023_schedule.py`:

```python
from pathlib import Path


def test_mission_023_maps_numbered_constraints_not_m3_still_partial() -> None:
    note = Path("architecture/mission-023-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    for token in (
        "plain_language_v0",
        "success",
        "numbered",
        "constraint",
        "partial",
        "oar-017",
        "phase 4b",
        "direct",
        "/requirements/",
        "/behavior/constraints",
    ):
        assert token in lower, token
    assert "not full" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "oq-008-004" in lower
    assert "oq-008-007" in lower
    assert "oq-008-008" in lower
    assert "oq-008-009" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
    oar_path = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md")
    assert oar_path.is_file()
    oar_text = oar_path.read_text(encoding="utf-8")
    status_line = next(
        line for line in oar_text.splitlines() if line.lower().startswith("**status:**")
    )
    assert "accepted" in status_line.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_023_schedule.py -v`

Expected: FAIL because `architecture/mission-023-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-023-certification/README.md` stating:

- OAR-017 Ready (not Accepted).
- Maps numbered `plain_language_v0` lines `direct` to `/requirements/{n}/statement` and constraint lines `direct` to `/behavior/constraints/{n}`. Goal remains `direct` to `/objective/goal`.
- Valid constrained write-up (Goal + numbered list + optional constraints) compiles **SUCCESS**, not invented IR and not `RQC-BLK-0001` for this hole.
- Does not mint mappings for optional `Project:` or for closed-loop default instructions.
- Not full MISSION-008 production compiler. Maturity PARTIAL. Not Phase 4B exit. Not M3. Not live. Not freeform NLP.
- OQ-008-004 / 007 / 008 / 009 remain locked-not-built.
- OAR-014 / OAR-015 / OAR-016 stay Accepted historical snapshots (including their “blocked” wording).

- [ ] **Step 4: Re-run schedule test**

Same pytest command. Expected: PASS (maturity map already says PARTIAL; PRS already DEFERRED; OAR-016 already Accepted).

- [ ] **Step 5: Commit**

```text
docs: add MISSION-023 certification README and schedule honesty test
```

---

### Task 2: Direct maps + live produce tests

**Files:**
- Modify: `src/promptrig/compiler/requirements_plain_produce.py`
- Modify: `tests/compiler/test_mission_020_produce.py`
- Create: `tests/compiler/test_mission_023_produce.py`

**Interfaces:**
- Consumes: `parse_plain_language_v0`; `_mapping(..., outcome=, target_pointer=)`; `compile_requirements_input`
- Produces: numbered/constraint maps with `outcome="direct"` and 0-based pointers assigned before id sort

- [ ] **Step 1: Write failing tests**

Create `tests/compiler/test_mission_023_produce.py`:

```python
from __future__ import annotations

from pathlib import Path

from promptrig.compiler.requirements_contract import compile_requirements_input
from promptrig.compiler.requirements_plain_produce import produce_plain_language_requirements

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"

TWO_NUMBERED = """Goal: Summarize incidents without inventing facts.
Requirements:
1. Label missing context as UNKNOWN.
2. Keep original timestamps.
"""

EMPTY_CONSTRAINTS = """Goal: Summarize incidents without inventing facts.
Requirements:
1. Label missing context as UNKNOWN.
Constraints:
"""


def test_minimal_fixture_succeeds_with_direct_numbered_and_constraint_maps() -> None:
    artifacts = produce_plain_language_requirements(FIXTURE.read_text(encoding="utf-8"))
    numbered = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    constraint = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-C001")
    goal = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-GOAL")
    assert goal["outcome"] == "direct"
    assert goal["target_pointer"] == "/objective/goal"
    assert numbered["outcome"] == "direct"
    assert numbered["target_pointer"] == "/requirements/0/statement"
    assert constraint["outcome"] == "direct"
    assert constraint["target_pointer"] == "/behavior/constraints/0"
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": FIXTURE.read_text(encoding="utf-8")}
    )
    assert result.status == "SUCCESS"
    assert "RQC-BLK-0001" not in result.reason_codes


def test_two_numbered_lines_map_in_listed_order() -> None:
    artifacts = produce_plain_language_requirements(TWO_NUMBERED)
    first = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    second = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-002")
    assert first["target_pointer"] == "/requirements/0/statement"
    assert second["target_pointer"] == "/requirements/1/statement"
    assert not any(item["requirement_id"].startswith("REQ-PL-C") for item in artifacts["mappings"])
    result = compile_requirements_input({"profile": "plain_language_v0", "text": TWO_NUMBERED})
    assert result.status == "SUCCESS"


def test_empty_constraints_header_still_succeeds() -> None:
    artifacts = produce_plain_language_requirements(EMPTY_CONSTRAINTS)
    assert not any(item["requirement_id"].startswith("REQ-PL-C") for item in artifacts["mappings"])
    result = compile_requirements_input({"profile": "plain_language_v0", "text": EMPTY_CONSTRAINTS})
    assert result.status == "SUCCESS"


def test_freeform_still_parse_blocked() -> None:
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": "Please build a helpful assistant that does stuff."}
    )
    assert result.status == "BLOCKED"
    assert "PL-PARSE-0001" in result.reason_codes


def test_extra_keys_still_schema_invalid() -> None:
    result = compile_requirements_input(
        {
            "profile": "plain_language_v0",
            "text": FIXTURE.read_text(encoding="utf-8"),
            "repair_budget": 1,
        }
    )
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes
```

In `tests/compiler/test_mission_020_produce.py`, change **only** `test_valid_grammar_is_blocked_not_invalid_or_success` to:

```python
def test_valid_grammar_succeeds_with_direct_numbered_and_constraint_maps() -> None:
    from promptrig.compiler.requirements_plain_produce import produce_plain_language_requirements

    artifacts = produce_plain_language_requirements(FIXTURE.read_text(encoding="utf-8"))
    document = artifacts["requirements_document"]
    ids = {item["id"] for item in document["requirements"]}
    assert "REQ-PL-GOAL" in ids
    assert "REQ-PL-001" in ids
    assert "REQ-PL-C001" in ids
    goal_map = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-GOAL")
    assert goal_map["outcome"] == "direct"
    assert goal_map["target_pointer"] == "/objective/goal"
    numbered = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    assert numbered["outcome"] == "direct"
    assert numbered["target_pointer"] == "/requirements/0/statement"
    constraint = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-C001")
    assert constraint["outcome"] == "direct"
    assert constraint["target_pointer"] == "/behavior/constraints/0"
    result = compile_requirements_input(_plain_payload())
    assert result.status == "SUCCESS"
    assert "RQC-BLK-0001" not in result.reason_codes
```

Leave the freeform, goal-only, extra-keys, prs-envelope, and CLI-help tests unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_produce.py::test_valid_grammar_succeeds_with_direct_numbered_and_constraint_maps -v`

Expected: FAIL because numbered/constraint maps are still `unresolved` / compile status is still `BLOCKED`.

- [ ] **Step 3: Implement the producer change**

In `src/promptrig/compiler/requirements_plain_produce.py`, replace the numbered and constraint mapping loops. Goal mapping stays as-is. Assign pointers **before** the existing `.sort` calls:

```python
    for index, item in enumerate(parsed["requirements"]):
        rid = str(item["id"])
        statement = str(item["statement"])
        token = rid.removeprefix("REQ-")
        src_id = f"SRC-{token}"
        sources.append(_source(source_id=src_id, fragment=statement, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="behavior", statement=statement, source_id=src_id)
        )
        mappings.append(
            _mapping(
                map_id=f"MAP-{token}",
                requirement_id=rid,
                source_id=src_id,
                outcome="direct",
                target_pointer=f"/requirements/{index}/statement",
            )
        )

    constraints = list(parsed.get("behavior", {}).get("constraints") or [])
    for index, constraint in enumerate(constraints):
        n = index + 1
        rid = f"REQ-PL-C{n:03d}"
        src_id = f"SRC-PL-C{n:03d}"
        sources.append(_source(source_id=src_id, fragment=constraint, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="constraint", statement=constraint, source_id=src_id)
        )
        mappings.append(
            _mapping(
                map_id=f"MAP-PL-C{n:03d}",
                requirement_id=rid,
                source_id=src_id,
                outcome="direct",
                target_pointer=f"/behavior/constraints/{index}",
            )
        )
```

Do not mint maps for `Project:` or for default instructions.

- [ ] **Step 4: Re-run produce tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_produce.py tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

Expected: PASS.

If `EMPTY_CONSTRAINTS` fails parse (`PL-PARSE-*`) because a Constraints header with zero items is illegal, stop and report `NEEDS_CONTEXT` — do not invent a grammar change. The spec treats empty header as SUCCESS with no `REQ-PL-C*` records; confirm against `parse_plain_language_v0` before changing the parser.

- [ ] **Step 5: Commit**

```text
feat: map plain-language numbered and constraint lines to IR leaves
```

---

### Task 3: Current-state docs, OAR-017, report

**Files:**
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-017.md`
- Create: `MISSION_023_REPORT.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements-compiler row only: numbered/constraint now mapped; keep `PARTIAL`; keep 004/007/008/009 locked)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: root `README.md` (append MISSION-023 bullet; do not rewrite 020–022 bullets)

**Interfaces:**
- Consumes: Task 2 SUCCESS behavior
- Produces: Ready OAR-017; current-state honesty

- [ ] **Step 1: Write OAR-017 Ready**

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-017.md`:

```markdown
# OAR-017 — MISSION-023 Constrained Prose Numbered/Constraint IR Mapping

**Status:** Ready (not Accepted).

**Certified if accepted:** constrained `plain_language_v0` numbered requirement lines map `direct` to `/requirements/{n}/statement` and constraint lines map `direct` to `/behavior/constraints/{n}`; Goal remains `direct` to `/objective/goal`; a valid Goal + numbered list + optional constraints write-up compiles `SUCCESS` rather than `RQC-BLK-0001` for this hole; `evaluate_contract_rules` remains the sole RC-065 implementation. Optional `Project:` and closed-loop default instructions are not minted as mappings. OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST. Do not drop `-draft`. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-016 remain Accepted.
```

- [ ] **Step 2: Update current-state docs**

`PROJECT_ORIENTATION.md`:

- Picture 3: Job 023 done (numbered + constraints map; Goal already mapped). M1 typing: strict prose now compiles SUCCESS for valid grammar.
- Picture 4 / short answers: last closed job becomes 023 / OAR-017 Ready (not Accepted). Compiler still PARTIAL.
- Fix the stale “local `main` is ahead of `origin/main`” line if git shows they match; keep “do not push unless you say to.”
- Point “last accept” at OAR-016; add 023 spec/plan as the open job until Accepted.

`OPEN_QUESTIONS.md` last paragraph: replace “Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`)” with wording that MISSION-023 maps numbered/constraint records to IR (OAR-017 Ready) while OQ-008-004/007/008/009 stay locked-not-built and M3 / CERTIFIED / Phase 4B remain unauthorized. Keep a “policy only” or “authorize no production implementation” phrase somewhere in the file so the 020 schedule test still passes.

`CAPABILITY_MATURITY_MAP.md`: keep `| Requirements compiler | `PARTIAL` |`. In that row’s evidence/limitations, state MISSION-023 mapped numbered/constraint prose (OAR-017 Ready) instead of “valid constrained prose is BLOCKED.”

Root `README.md`: append a MISSION-023 bullet describing the mapping + SUCCESS + PARTIAL + not M3. Leave 020–022 bullets unchanged.

- [ ] **Step 3: Write MISSION_023_REPORT.md**

Mirror `MISSION_022_REPORT.md` shape: what landed, HEAD placeholder, tests run, non-claims (PARTIAL, not CERTIFIED, not Phase 4B, not M3, OQs 004/007/008/009 locked, OAR-017 Ready).

- [ ] **Step 4: Run honesty + produce tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add OAR-017 Ready and current-state MISSION-023 honesty
```

---

## Execution notes

- Worktree: `C:/AI/projects/PromptRig/.worktrees/mission-023-plain-language-ir-mapping`
- Branch: `feature/mission-023-plain-language-ir-mapping`
- After Task 3: stop for Boss Accept of OAR-017. Do not merge. Do not push `origin/main`.
- Spec coverage: mapping table → Task 2; extra produce cases → Task 2; honesty/PARTIAL/not M3 → Tasks 1 and 3; frozen OARs → Task 3 does not rewrite them.
