# MISSION-027 Design — Evaluation/Repair Product Bar (not compiler CERTIFIED)

**Date:** 2026-08-28
**Baseline:** local `main` @ `2831cda` (OAR-019 Accepted; MISSION-025 closed). Rebase onto local `main` after MISSION-026 Ready lands.
**Authority:** Boss approved campaign split A, full leftover product bar (rubric/dataset, baseline comparison, scoring aggregation, regression gate), Sections 1–4 (2026-08-28).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, unlocking OQ-008-004/007/008/009, IR v0.2, claiming CERTIFIED requirements compiler or Phase 4B exit, model judges as required infrastructure, promoting legacy `evals/` to Compiler Core, enterprise SAST, rewriting the 026 pack, `origin/main` push, breaking the certified fake closed-loop oracle.

## Goal

Implement the MISSION-009 evaluation/repair **product** bar against `architecture/evaluation-repair-contract-v0.1`: rubric/dataset engine, baseline comparison, scoring aggregation, production regression gate. Keep `evaluate_deterministic` as the rank-1 compile/security/network oracle. Fake-adapter only. Do **not** promote the requirements compiler to CERTIFIED. Do **not** claim the new product surface is CERTIFIED.

## Honesty (read first)

- Evaluation and Repair oracle slice stays **CERTIFIED** (OAR-003 / OAR-006): `evaluate_deterministic` + bounded instruction-append repair, budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false`.
- The 009 contract package is **PROPOSED**, not production-certified. 027 implements engines from it. The contract status may stay PROPOSED. New product surface is **IMPLEMENTED_NOT_CERTIFIED** until a later review.
- Requirements compiler stays **PARTIAL**. Locked OQs stay locked. No M3.
- MISSION-026 is a sibling review pack of SHA `2831cda` (oracle-era tree). 027 must not rewrite 026 pack files. After 027 lands, a delta review of the new engines is a later campaign.
- Legacy `evals/` JSONL/YAML is PromptOps, not the Compiler Core stage. Do not promote it.

## Product path (additive)

Keep the certified closed loop green. Product evaluation is a new path beside the oracle, not a replacement.

1. **Dataset** — versioned JSONL cases with `REQ-*` ids. Fixtures live with compiler tests/contract (`tests/compiler/` and/or `architecture/evaluation-repair-contract-v0.1/fixtures/`), not `evals/`.
2. **Rubric** — versioned YAML/JSON criteria; deterministic scores only.
3. **Baseline comparison** — candidate vs baseline digests; missing/mismatched/stale baseline on the regression path → `BLOCKED` (`EVR-BSL-0001` / `EVR-BSL-0002`).
4. **Scoring aggregation** — `min` | `max` | `mean` | `any_fail` | `all_pass`. Evaluator errors cannot become a silent PASS (`EVR-SCR-0001`).
5. **Regression gate** — candidate worse than baseline → status `REGRESSION`. Failed attempts kept (`EVR-EVD-0001`). Repair still `{0,1,2}` and `EVR-SEC-0001`.

Statuses used: `PASS`, `FAIL`, `ERROR`, `BLOCKED`, `UNAVAILABLE`, `REGRESSION`, `UNRESOLVED_DEFECT` per `EVALUATION_REPAIR_SPEC.md`.

Authority: deterministic / schema / security remain rank 1. Score aggregator and fake-adapter oracle remain below that. Model judge is out of scope.

## Data flow

Request → `evaluate_deterministic` (unchanged) → rubric/dataset scores → aggregate → baseline compare → product result + evidence (`REQ-*`, failed attempts). Fail-closed: schema miss, authority miss, evidence gap, `network_used` → `BLOCKED` / `ERROR` / `UNAVAILABLE`, never silent PASS.

## Deliverables

1. New compiler modules for dataset, rubric, aggregation, baseline compare, regression gate. Do not stuff this into `evaluate_deterministic`.
2. Wiring: library API for the product path; closed-loop hook that does not change default oracle behavior. No new CLI command this mission.
3. `tests/compiler/` TDD for each product piece plus a 027 schedule/honesty test (PARTIAL compiler; oracle CERTIFIED; product surface not CERTIFIED; locked OQs; no M3; no live).
4. Existing 006/012/023/024/025 closed-loop and honesty tests stay green.
5. `architecture/mission-027-certification/README.md` + `OAR-021.md` Ready. Maturity map: Evaluation/Repair rows keep CERTIFIED for the oracle slice and record the product surface as not CERTIFIED. Orientation Picture 3 Job 027. Deferred bullets: product bar no longer “missing”; 026 pack/independence wording unchanged except 027 sibling note. Do not edit `architecture/mission-026-certification/` pack files.

## Approaches (this campaign)

A. **Additive 009 engines, oracle kept (selected).** Full leftover bar. Fake-adapter only. Compiler PARTIAL. Product surface not CERTIFIED.

B. **Regression gate only on the existing oracle.** Rejected. Boss picked full leftover bar.

C. **Replace oracle / promote `evals/` / add model judges / claim CERTIFIED.** Rejected.

## Recommendation

Execute A. Rebase onto local `main` after 026 Ready lands. SDD stops at OAR-021 Ready. Boss Accepts later. Do not merge/push `origin/main` unless asked. Do not claim Phase 4B exit.

## Worktree

`C:/AI/projects/PromptRig/.worktrees/mission-027-eval-repair-product` on `feature/mission-027-eval-repair-product` @ `2831cda` (rebase after 026 Ready).

## Execution

Spec → plan → subagent-driven-development (one implementer at a time in this worktree). Do not run a 027 implementer in the 026 worktree. Stop at OAR-021 Ready.
