# MISSION-025 Design — Same-Host Architecture/Security Review of the PARTIAL Compiler Slice

**Date:** 2026-08-28
**Baseline:** local `main` @ `56d484e` (OAR-018 Accepted; MISSION-024 closed).
**Authority:** Boss picked approach A 2026-08-28 (024’s approach B: bounded review pack; no producer change; no CERTIFIED claim).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, unlocking OQ-008-004/007/008/009, IR v0.2, claiming CERTIFIED or Phase 4B exit, third-party/enterprise audit, eval/repair product-bar implementation, `origin/main` push.

## Goal

Record a bounded architecture and security review of the current **PARTIAL** requirements-compiler slice (library `compile_requirements_input` / `evaluate_contract_rules`, `promptrig-compiler compile-requirements`, constrained `plain_language_v0` SUCCESS path). Do **not** change the producer or engine. Do **not** promote CERTIFIED.

## Honesty (read first)

After 024:

- Constrained `plain_language_v0` valid grammar compiles **SUCCESS** (OAR-017).
- Remaining 4B blockers are inventoried (OAR-018). Compiler stays **PARTIAL**.
- Fake closed loop remains CERTIFIED (offline fake only).
- OQ-008-004 / 007 / 008 / 009 stay locked-not-built.
- Evaluation/repair **product** bar (rubric/dataset engine, production regression gate) remains outstanding. That is the next campaign after this one, not this job.
- Roadmap Phase 4B exit still wants full 008 production compiler, full MISSION-009 product engines, independent review that **certifies the boundary**, and explicit owner promotion. This mission does **not** satisfy that exit.

Independence limit (binding): this is a **same-host** review (separate reviewer pass from the implementer who writes the honesty shell). It is **not** a third-party audit, not enterprise SAST, and not “independent architecture and security review certify the boundary” in the Phase 4B exit-criteria sense. The pack exists so the PARTIAL-slice review hole inventoried in OAR-018 is no longer “none recorded.”

## Slice under review (named files)

- `src/promptrig/compiler/requirements_contract.py` — `compile_requirements_input`, `evaluate_contract_rules` (sole RC-065).
- `src/promptrig/compiler/requirements_plain_produce.py` — constrained prose lowerer.
- `src/promptrig/compiler/cli_compiler.py` — `compile-requirements` / `network_allowed=False`.
- `src/promptrig/compiler/closed_loop.py`, `evaluation.py`, `repair.py` — offline default, `EVR-SEC-0001`, repair budgets `{0,1,2}`.
- Behavior evidence already on `main`: `tests/compiler/test_mission_023_produce.py`, `tests/compiler/test_mission_024_schedule.py`.

Out of scope for the review body: locked OQ implementation, M3, live providers, rubric/dataset product engines, IR v0.2.

## Deliverables

1. `architecture/mission-025-certification/README.md` — honesty/schedule: OAR-019 Ready; PARTIAL; not CERTIFIED; not Phase 4B exit; same-host independence limit; OQs 004/007/008/009 locked; no M3; no live; eval/repair product bar still outstanding.
2. `architecture/mission-025-certification/REVIEW.md` — the review body, filled by a **separate reviewer pass** (not the honesty-shell implementer). Required sections: Architecture, Security, Findings (may be empty only if the named files were actually read), Independence limit, Non-claims. Must state PARTIAL / not CERTIFIED / `EVR-SEC-0001` / `network_allowed=false`. Must not pre-script a “clean bill of health.”
3. `tests/compiler/test_mission_025_schedule.py` — asserts README + REVIEW tokens and OAR-019 Ready (not Accepted). No producer/engine asserts.
4. `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md` Ready, plus current-state honesty (orientation, maturity-map compiler row, OPEN_QUESTIONS last paragraph, deferred blocking bullets, root README append). Leave 020–024 cert READMEs and OAR-009 through OAR-018 frozen.

No edits to `produce_plain_language_requirements`, `evaluate_contract_rules`, envelope producers, IR schema, or closed-loop defaults.

## Approaches (this campaign)

A. **Bounded same-host review pack (selected).** Honesty README + REVIEW.md + schedule test + OAR-019 Ready. No producer/engine change. No CERTIFIED promotion.

B. **Skip review, start eval/repair product bar.** Rejected for this mission (Boss picked A). Next campaign after OAR-019 Accept.

C. **Treat this review as Phase 4B / CERTIFIED certification.** Rejected. Wrong bar.

## Recommendation

Execute A. Stop for Boss Accept of OAR-019 after the pack exists. Do not merge/push `origin/main` unless asked. Do not claim Phase 4B exit.

## Worktree

`C:/AI/projects/PromptRig/.worktrees/mission-025-partial-slice-review` on `feature/mission-025-partial-slice-review` @ `56d484e`.
