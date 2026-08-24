# MISSION-023 Report — Constrained Prose Numbered/Constraint IR Mapping

**Status:** OAR-017 Accepted 2026-08-24.
**Baseline:** local `main` @ `e2cc33b`.
**Branch:** `feature/mission-023-plain-language-ir-mapping`.
**HEAD (OAR-017 Accept):** `eccecd9`

## Scope

Campaign COMPILER maps constrained `plain_language_v0` numbered requirement lines `direct` to `/requirements/{n}/statement` and constraint lines `direct` to `/behavior/constraints/{n}`. Goal remains `direct` to `/objective/goal`. A valid Goal + numbered list + optional constraints write-up compiles `SUCCESS` rather than `RQC-BLK-0001` for this hole. `produce_plain_language_requirements` assigns 0-based pointers at emit time before id sort. Optional `Project:` and closed-loop default instructions are not minted as mappings. `evaluate_contract_rules` remains the sole RC-065 implementation. OQ-008-004 (no identity merge / no alias-group object), OQ-008-007 (PRS language DEFERRED), OQ-008-008 (no continuation IR field), and OQ-008-009 (no reasoning IR field) are locked-not-built. `compile_requirements` / `promptrig-compiler compile-requirements` dispatch unchanged. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

Does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, a full MISSION-008 production compiler, PRS **language** implementation, live providers, M3, freeform NLP, IR v0.2, alias-group implementation, or dropping `-draft`.

OAR-009 through OAR-016 remain **Accepted**. OAR-017 is **Accepted 2026-08-24**.

## Tasks 1–3

| Task | Commit | Deliverable |
|---|---|---|
| 1 | `fc94205` | MISSION-023 certification README and schedule honesty test |
| 2 | `8cb7384` | Map plain-language numbered and constraint lines to IR leaves |
| 3 | `3765965` | Honesty docs, OAR-017 Ready, campaign report |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-023-certification/README.md` |
| Numbered maps | `direct` → `/requirements/{n}/statement` |
| Constraint maps | `direct` → `/behavior/constraints/{n}` |
| Goal map | unchanged `direct` → `/objective/goal` |
| Compile outcome | valid Goal + numbered list + optional constraints → `SUCCESS` (not `RQC-BLK-0001` for this hole) |
| Shared engine | `evaluate_contract_rules` sole RC-065 implementation |
| Governance | OAR-017 Accepted 2026-08-24; Requirements compiler stays `PARTIAL`; OAR-009 through OAR-016 Accepted |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_023_schedule.py` | Certification README honesty; PARTIAL; OAR-016 Accepted; OQ-008-004/007/008/009 locked; no full 008 / no M3 |
| `tests/compiler/test_mission_023_produce.py` | Numbered/constraint `direct` pointers; SUCCESS; empty Constraints header; freeform still parse-blocked |
| `tests/compiler/test_mission_020_produce.py` | Live SUCCESS assertions for previously BLOCKED valid prose |
| `tests/compiler/test_mission_020_schedule.py` | Regression: OPEN_QUESTIONS still contains “authorize no production implementation” or “policy only”; 020 README still says `blocked` |
| `tests/compiler/test_mission_022_schedule.py` | Regression: 022 honesty tokens; OAR-016 Accepted; PARTIAL |

**Verification command:** `uv run --with pytest python -m pytest tests/compiler/test_mission_023_schedule.py tests/compiler/test_mission_023_produce.py tests/compiler/test_mission_020_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_022_schedule.py -v`

## Residual gaps (honest)

MISSION-023 does **not** claim full Roadmap Phase 4B exit, a CERTIFIED requirements compiler, or a full MISSION-008 production compiler:

- Mapped this campaign: numbered/constraint `plain_language_v0` records to existing v0.1 IR leaves; valid grammar compiles `SUCCESS` for this hole.
- Locked not-built: OQ-008-004, OQ-008-007, OQ-008-008, OQ-008-009.
- Not freeform NLP; PRS **language** remains **DEFERRED** per `PRS_DISPOSITION.md`.
- Requirements compiler maturity remains **`PARTIAL`** — not CERTIFIED.
- OAR-017 Accepted 2026-08-24. OAR-009 through OAR-016 Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, alias-group implementation, or enterprise SAST.
- This mission does **not** unblock M3.

## Non-claims

Matching OAR-017: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS language/grammar/parser, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST, and dropping `-draft` remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-017 Accepted 2026-08-24. OAR-009 through OAR-016 remain Accepted.
