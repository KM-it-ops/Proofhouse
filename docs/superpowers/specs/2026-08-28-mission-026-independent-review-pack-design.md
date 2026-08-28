# MISSION-026 Design — Independent-Person Review Pack of the PARTIAL Slice at 2831cda

**Date:** 2026-08-28
**Baseline:** local `main` @ `2831cda` (OAR-019 Accepted; MISSION-025 closed).
**Authority:** Boss approved campaign split A, owner+second-person review, Sections 1–4 (2026-08-28).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, unlocking OQ-008-004/007/008/009, IR v0.2, claiming CERTIFIED or Phase 4B exit, enterprise SAST, eval/repair product-bar implementation (that is MISSION-027), `origin/main` push, agent-authored Accept or “clean bill of health.”

## Goal

Produce a **plain-language** architecture and security review pack of the current **PARTIAL** compiler slice and the current fake-adapter eval/repair **oracle** at exact SHA `2831cda`. You review it. A second person reviews it from the same pack. Agents write the pack. Humans write the verdict. Do **not** change producer or engine. Do **not** promote CERTIFIED.

## Honesty (read first)

After 025:

- Constrained `plain_language_v0` valid grammar compiles SUCCESS (OAR-017).
- Remaining 4B holes inventoried (OAR-018). Compiler stays **PARTIAL**.
- Same-host PARTIAL-slice review recorded (OAR-019). That pack is **not** this mission and does **not** count as independent-person review.
- Fake closed loop remains CERTIFIED (offline fake only).
- OQ-008-004 / 007 / 008 / 009 stay locked-not-built.
- Evaluation/repair **product** bar is MISSION-027, a sibling branch from the same baseline. It is **not** in the reviewed tree.

This pack reviews **this HEAD only**. It does not certify Roadmap Phase 4B exit. It does not certify architecture/security of 027 engines. A delta review of 027 is a later campaign.

Independence limit (binding): owner review plus a second person who can do architecture and security but needs short words, not jargon-first prose. Not enterprise SAST. Not a same-host agent filling `REVIEW.md` (that was 025). Not “independent review certifies the Phase 4B boundary” in the exit-criteria sense while 027 is in flight and locked OQs remain.

## Slice under review (named files)

- `src/promptrig/compiler/requirements_contract.py` — `compile_requirements_input`, `evaluate_contract_rules` (sole RC-065).
- `src/promptrig/compiler/requirements_plain_produce.py` — constrained prose lowerer.
- `src/promptrig/compiler/cli_compiler.py` — `compile-requirements` / `network_allowed=False`.
- `src/promptrig/compiler/closed_loop.py`, `evaluation.py`, `repair.py` — offline default, `EVR-SEC-0001`, repair budgets `{0,1,2}`.
- Behavior evidence already on `main`: `tests/compiler/test_mission_023_produce.py`, `tests/compiler/test_mission_024_schedule.py`, `tests/compiler/test_mission_025_schedule.py`.

Out of scope for the pack body: locked OQ implementation, M3, live providers, 027 rubric/dataset/baseline/aggregation/regression engines, IR v0.2.

## Deliverables

1. `architecture/mission-026-certification/README.md` — honesty/schedule: OAR-020 Ready; PARTIAL; not CERTIFIED; not Phase 4B exit; pin `2831cda`; 027 sibling not in this tree; independence = owner + second person; not enterprise SAST; OQs 004/007/008/009 locked; no M3; no live; product bar outstanding on the sibling.
2. `architecture/mission-026-certification/PACK.md` — the review document. Short sentences. Define a term once when first used. Architecture of the named files. Security properties (`network_allowed=false`, `EVR-SEC-0001`, budgets `{0,1,2}`). What exists vs what does not. Questions the reviewer must answer. No strategy-package dump. No pre-scripted clean bill of health.
3. `architecture/mission-026-certification/INSTRUCTIONS.md` — for the second person: reading order, which files, what to ignore, how to record a finding, “I don’t know” is allowed.
4. `architecture/mission-026-certification/VERDICT.md` — empty template only: Architecture, Security, Blockers, Accept/Reject, unknowns. Humans fill this after SDD. Agents must not fill findings.
5. `tests/compiler/test_mission_026_schedule.py` — asserts README + PACK + INSTRUCTIONS tokens, SHA pin `2831cda`, empty verdict template (no filled findings), OAR-020 Ready (not Accepted). No producer/engine asserts.
6. `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md` Ready, plus current-state honesty (orientation Picture 3 Job 026 Ready — pack, not Accepted; maturity-map compiler row note; OPEN_QUESTIONS last paragraph; deferred blocking bullets; root README append). Leave `architecture/mission-020-certification` through `mission-025-certification` READMEs and OAR-009 through OAR-019 frozen.

No edits to `produce_plain_language_requirements`, `evaluate_contract_rules`, envelope producers, IR schema, `evaluation.py`, `repair.py`, or closed-loop defaults.

## Approaches (this campaign)

A. **Owner + second-person pack at 2831cda (selected).** Honesty README + PACK + INSTRUCTIONS + empty VERDICT + schedule test + OAR-020 Ready. No producer/engine change. No CERTIFIED promotion. SDD stops at Ready.

B. **Same-host agent REVIEW.md again.** Rejected. That was 025. Does not match the second-person path.

C. **Treat this pack as Phase 4B / CERTIFIED certification.** Rejected. Wrong bar. 027 in flight; locked OQs remain.

## Recommendation

Execute A. Land Ready on local `main` so the pack can be sent. Do not Accept OAR-020 inside SDD. Do not merge/push `origin/main` unless asked. Do not claim Phase 4B exit.

## Worktree

`C:/AI/projects/PromptRig/.worktrees/mission-026-independent-review-pack` on `feature/mission-026-independent-review-pack` @ `2831cda`.

## Execution

Spec → plan → subagent-driven-development (one implementer at a time in this worktree). Stop at OAR-020 Ready.
