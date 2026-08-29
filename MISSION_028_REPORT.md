# MISSION-028 Report — Skip-Cert Law for Phase 5–9 Entry

**Status:** OAR-022 Ready (not Accepted).
**Baseline:** local `main` after MISSION-026 Ready (`5475ac9`).
**Branch:** `feature/mission-028-skip-cert-law`.
**Worktree:** `C:/AI/projects/PromptRig/.worktrees/mission-028-skip-cert-law`.

## Scope

Campaign remaining-product amends ROADMAP_V1 Phase 5-implementation and Phase 6–9 entry so later units do not wait on independent 4B-exit certification. Peer review is not a gate. Remaining Phase 4B engineering (product eval, CLI parity, 008 join) plus owner Accept is what later phases consume. Approach: docs and honesty tests only. No producer/engine change.

Does **not** claim full Roadmap Phase 4B exit, CERTIFIED compiler promotion, a full MISSION-008 production compiler, PRS **language** implementation, live providers, M3, freeform NLP, IR v0.2 production schema, alias-group implementation, or dropping `-draft`.

OAR-009 through OAR-019 remain **Accepted**. OAR-020 remains **Ready (not Accepted)**. OAR-021 is reserved for MISSION-027. OAR-022 is **Ready (not Accepted)**. Requirements compiler stays `PARTIAL`. Fake-adapter eval/repair oracle stays `CERTIFIED`.

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-028-certification/README.md` |
| Governance | OAR-022 Ready (not Accepted); D-050-014 Ready; Requirements compiler stays `PARTIAL`; OAR-009 through OAR-019 Accepted |
| Strategy package | ROADMAP_V1 Phase 4B exit and Phase 5–9 entry; vision headless-first (law 5 unchanged); orientation; maturity promotion rule; deferred registry; requirement-to-roadmap traceability; strategy index |
| Honesty tests | `tests/compiler/test_mission_028_schedule.py` |
| Producer/engine | unchanged |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_028_schedule.py` | Skip-cert law; Phase 5–9 entry; PARTIAL compiler; CERTIFIED oracle; OAR-022 Ready; vision law 5 preserved; Simple Mode still Phase 8 and UI must not own semantics |
| `tests/compiler/test_mission_026_schedule.py` | Regression: 026 honesty pack unchanged |
| `tests/compiler/test_mission_025_schedule.py` | Regression: 025 honesty unchanged |
| `tests/compiler/test_mission_024_schedule.py` | Regression: 024 honesty unchanged |

**Verification command:** `uv run --with pytest python -m pytest tests/compiler/test_mission_*_schedule.py -v`

## Residual gaps (honest)

MISSION-028 does **not** claim full Roadmap Phase 4B exit or CERTIFIED compiler promotion:

- Recorded this campaign: skip-cert strategy amendment. No producer/engine change.
- Outstanding 4B engineering: evaluation/repair product bar (MISSION-027); 008 SUCCESS/PARTIAL join.
- Locked not-built: OQ-008-004, OQ-008-007, OQ-008-008, OQ-008-009.
- Requirements compiler maturity remains **`PARTIAL`**.
- OAR-022 Ready (not Accepted). OAR-020 Ready (not Accepted). OAR-009 through OAR-019 Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2 production schema, alias-group implementation, or enterprise SAST.
- This mission does **not** unblock M3 by itself.

## Non-claims

Matching OAR-022: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS language/grammar/parser, alias-group implementation, IR v0.2 production schema, full MISSION-008 production compiler, full Roadmap Phase 4B exit, CERTIFIED compiler promotion, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST, and dropping `-draft` remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-022 Ready (not Accepted).
