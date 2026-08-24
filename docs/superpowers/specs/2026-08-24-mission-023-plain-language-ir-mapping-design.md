# MISSION-023 Design — Constrained Prose Numbered/Constraint IR Mapping

**Date:** 2026-08-24
**Baseline:** local `main` @ `e2cc33b` (OAR-016 Accepted; MISSION-022 closed).
**Authority:** Boss authorized this campaign 2026-08-24 (next compiler job = wire numbered lines and constraints so a valid write-up can succeed; approach A; design chunks 1–3 accepted).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, new grammar, PRS language/grammar, IR v0.2 fields, CERTIFIED requirements compiler, full Phase 4B exit, unlocking OQ-008-004/007/008/009, inventing lines the user did not write.

**Numbering note:** This 023 is Campaign COMPILER remaining MISSION-020 mapping honesty: the same `plain_language_v0` grammar, with numbered and constraint records emitting to frozen IR v0.1 leaves. Not a full 008 compiler. Not Phase 4B exit. Not M3.

**Identifier note:** Live code names win over older 022-doc dialect. Profile `plain_language_v0`. Records `REQ-PL-GOAL` / `REQ-PL-001` / `REQ-PL-C001`. Goal pointer `/objective/goal`. Numbered `/requirements/{n}/statement`. Constraints `/behavior/constraints/{n}`. Outcome `direct`. Field `target_pointer`. Engine `evaluate_contract_rules`. Compile `compile_requirements_input`.

## Goal

Change the existing plain-language producer so numbered requirement lines and constraint lines get **direct** maps onto the same IR slots the offline closed loop already uses. A valid Goal + numbered list + (optional) constraints write-up compiles **SUCCESS**, not **BLOCKED**.

## Do not authorize M3 in this campaign

M3 / Simple Mode is DFR-002 (broad UI) and Roadmap **Phase 8**. SUCCESS on constrained prose does not make the compiler CERTIFIED and does not exit Phase 4B. Mixing M3 here would smuggle a product UI into a mapping campaign.

## Honesty (read first)

Completing this job still leaves:

- Requirements compiler maturity **PARTIAL** (not CERTIFIED).
- PRS **language** DEFERRED.
- OQ-008-004 / 007 / 008 / 009 locked-not-built.
- Full MISSION-008 production compiler unclaimed.
- Phase 4B unexited.
- M3 unauthorized.
- Freeform English still parse-blocked (`PL-PARSE-*`).

MISSION-020’s original BLOCKED result for valid grammar was honest *then* (no guessed leaves). This campaign names the leaves. It does not rewrite accepted OAR-014 / OAR-015 / OAR-016 or 020–022 reports; those stay snapshots of that day’s truth.

## Approaches considered

1. **Change the existing 020 producer (chosen).** Numbered line *n* → `/requirements/{n}/statement`; constraint *n* → `/behavior/constraints/{n}`. Goal mapping unchanged. Smallest change. Same grammar. No new UI. No live model.
2. **Reuse the closed-loop converter, then copy its output.** One pipeline in theory; it also injects default instructions (“Follow requirements exactly”) and sometimes a default constraint. Those are not in the write-up. Copying them would pretend the user wrote them.
3. **New mapping module beside the producer.** Same end result as (1), extra file and ceremony.

## Mapping table

Same grammar as MISSION-013 / MISSION-020. Only mapping outcomes change.

| What the user writes | Record | Outcome | IR slot |
|---|---|---|---|
| `Goal: …` | `REQ-PL-GOAL` | `direct` (already) | `/objective/goal` |
| `1. …` | `REQ-PL-001` | `direct` (new) | `/requirements/0/statement` |
| `2. …` | `REQ-PL-002` | `direct` (new) | `/requirements/1/statement` |
| first `- …` under Constraints | `REQ-PL-C001` | `direct` (new) | `/behavior/constraints/0` |
| second `- …` | `REQ-PL-C002` | `direct` (new) | `/behavior/constraints/1` |

- File numbering stays 1-based. Pointer indices stay 0-based, in listed order (`enumerate` on the parsed lists at emit time, **before** the existing id sort; do not invent IDs).
- Emitting outcome is `direct` (already in `_EMITTING_OUTCOMES` in `evaluate_contract_rules`).
- `target_pointer` is required for `direct` maps. Pointers must classify as `valid` against frozen IR v0.1 (`/requirements/#/statement` and `/behavior/constraints/#` are leaves).

### Not mapped (on purpose)

- Optional `Project:` line — still used as project name on the closed-loop structured doc; this producer does not mint a requirement for it.
- Default instruction “Follow requirements exactly.” — closed-loop injects that. This path does not mint a requirement or mapping for it.
- Missing Constraints header, or a Constraints header with zero items — no `REQ-PL-C*` records, therefore no fake constraint mapping. Goal + numbered maps are enough for SUCCESS.

### Still blocked

- Freeform text, missing Goal, empty numbered list, numbering gaps → `BLOCKED` + `PL-PARSE-*` (parser unchanged).
- Extra JSON keys on the `{profile, text}` envelope → `INVALID_OUTPUT` / `RQC-SCH-0001` (dispatch unchanged).
- Required accepted meaning with no emitting map → still `BLOCKED` / `RQC-BLK-0001` (engine unchanged). After this job, valid constrained grammar is no longer that case.

## Behavior change

**Single code unit:** `src/promptrig/compiler/requirements_plain_produce.py`

Today numbered and constraint maps use `outcome="unresolved"` and omit `target_pointer`. After this job they use `outcome="direct"` and the pointers in the table.

Do **not** change:

- `parse_plain_language_v0` / grammar
- `evaluate_contract_rules` / RC-065
- envelope producers (file/api/simple/developer/prs)
- closed-loop `requirements_to_ir` defaults
- IR schema
- CLI surface beyond any honesty wording that would otherwise lie

Expected compile path for the existing minimal fixture (`Goal` + `1.` + one constraint):

- `compile_requirements_input({profile: plain_language_v0, text})` → `status == SUCCESS`
- `RQC-BLK-0001` absent

## Components

| Unit | Path | Responsibility |
|------|------|----------------|
| Producer | `src/promptrig/compiler/requirements_plain_produce.py` | Direct maps for numbered + constraint records |
| Live 020 produce tests | `tests/compiler/test_mission_020_produce.py` | Flip assertions: SUCCESS + new pointers (this file is the live check, not a frozen report) |
| New 023 produce tests | `tests/compiler/test_mission_023_produce.py` | Two numbered lines; constraints omitted; empty Constraints header; parse still blocked; extra keys still invalid |
| New 023 honesty test | `tests/compiler/test_mission_023_schedule.py` | PARTIAL, not CERTIFIED, not M3, not freeform, OAR-017 named |
| Honesty note | `architecture/mission-023-certification/README.md` | Scope and non-claims |
| Owner record | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-017.md` | Ready, not Accepted, until Boss says so |
| Current-state docs | `PROJECT_ORIENTATION.md`, `CAPABILITY_MATURITY_MAP.md`, `OPEN_QUESTIONS.md` last paragraph, root `README.md` **new 023 bullet** | Say numbered/constraint prose now maps; maturity stays PARTIAL. Leave 020–022 README bullets as historical snapshots. |

Leave frozen: OAR-014 / OAR-015 / OAR-016, `MISSION_020_REPORT.md` / `021` / `022`, and 020–022 certification READMEs (historical wording, including “blocked,” may remain). 020 schedule test still requires the word `blocked` in the 020 README — do not strip it. 021/022 engine tests that assert `RQC-BLK-0001` for *other* holes stay.

## Success criteria

- Minimal valid fixture compiles `SUCCESS` with goal/numbered/constraint `direct` maps to the pointers above.
- Constraints omitted (or empty Constraints section) still `SUCCESS` when Goal + at least one numbered line map.
- Freeform / grammar errors still `BLOCKED` + `PL-PARSE-*`. Extra keys still `INVALID_OUTPUT`.
- Honesty tests: maturity `PARTIAL`; not M3; not freeform; OQ-008-004/007/008/009 still locked-not-built.
- No new grammar, no IR schema fields, no live provider, no Simple Mode files.

## Out of scope

M3, CERTIFIED / Phase 4B exit, PRS language, OQ-008-004/007/008/009 implementation, IR v0.2, live model-assisted suggestion, rewriting accepted OARs, mapping default instructions as if the user wrote them.

## Process

Windows. Implement on a worktree / feature branch, not the `main` checkout. Editor-written briefs. `uv run --with pytest python -m pytest`. Do not push `origin/main` unless Boss asks.
