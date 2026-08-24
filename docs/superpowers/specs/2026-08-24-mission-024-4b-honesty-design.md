# MISSION-024 Design — Remaining Phase 4B Compiler Honesty (not CERTIFIED)

**Date:** 2026-08-24
**Baseline:** local `main` @ `e9c7b0f` (OAR-017 Accepted; MISSION-023 closed).
**Authority:** Boss picked approach A 2026-08-24 (honesty/schedule inventory; no producer change; no CERTIFIED claim).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, unlocking OQ-008-004/007/008/009, IR v0.2, claiming CERTIFIED or Phase 4B exit in this campaign without independent review + explicit promotion.

## Goal

Keep Campaign COMPILER moving after numbered/constraint mapping closed. Do **not** start M3. Do **not** pretend the requirements compiler is CERTIFIED.

## Honesty (read first)

After 023:

- Constrained `plain_language_v0` valid grammar compiles **SUCCESS**.
- Requirements compiler maturity remains **PARTIAL**.
- Fake closed loop remains CERTIFIED (offline fake only).
- OQ-008-004 / 007 / 008 / 009 stay locked-not-built.
- Full MISSION-008 production compiler, CERTIFIED requirements compiler, and Roadmap Phase 4B exit remain unauthorized.

Roadmap Phase 4B still wants: production compiler for every approved 008 profile, full MISSION-009 evaluation/repair product engines (not only the fake-oracle slice), independent architecture **and** security review, and explicit owner promotion. Green tests and OAR-017 do not satisfy that exit.

## Remaining holes (ranked)

1. **No independent architecture/security review of the current PARTIAL compiler slice.** Promotion rule in `CAPABILITY_MATURITY_MAP.md` requires map + evidence + independent review + owner approval. This is the honest next gate, not more producer code.
2. **Evaluation/repair product bar still missing** (rubric/dataset engine, production regression gate). The fake-adapter deterministic oracle is already CERTIFIED; expanding it is a new campaign, not a 023 leftover.
3. **Locked OQs 004/007/008/009.** Previously locked. Do not reopen here.
4. **M3 / Simple Mode.** Phase 8. Forbidden.

## Approaches

A. **Honesty/schedule inventory (recommended).** Write MISSION-024 certification README + schedule test that lists remaining 4B blockers and explicitly does **not** promote CERTIFIED. No producer/engine change. Smallest keep-going job. Matches 015/023 honesty shape.

B. **Independent review pack.** Same as A plus a bounded review artifact against the current compiler slice (library/CLI/plain-language SUCCESS path). Still no CERTIFIED promotion unless Boss separately Accepts promotion after that review.

C. **Unlock locked OQs or start M3.** Rejected. Prior locks and Phase 8.

## Recommendation

Approach **A** this campaign (Boss picked 2026-08-24). Stop for Boss Accept of OAR-018 Ready after the inventory exists. Do not merge/push `origin/main` unless asked. Do not claim Phase 4B exit.

## Worktree

`C:/AI/projects/PromptRig/.worktrees/mission-024-4b-certified-slice` on `feature/mission-024-4b-certified-slice` @ `e9c7b0f`.
