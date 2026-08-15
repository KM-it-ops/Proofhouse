# Plain-Language M1 Certification Package (MISSION-013)

**Status:** Implemented; OAR-007 Ready for owner acceptance (not Accepted).  
**Baseline:** MISSION-012 certification (`9e5028d`, OAR-006 Accepted 2026-08-12).  
**Intake profile:** `plain_language_v0` → `structured_minimal_v0` → existing closed loop.

## Scope

MISSION-013 adds a producing intake stage only:

- Constrained prose grammar (`PLAIN_LANGUAGE_V0_GRAMMAR.md`) — not freeform NLP
- Deterministic parser (`plain_language.py`) with `PL-PARSE-*` fail-closed diagnostics
- JSON envelope dispatch on `closed_loop_from_json` with `intake_profile` in evidence
- Library/CLI parity and minimal external-consumer smoke (public `promptrig.compiler.api` only)

Semantic validation and IR mapping remain on structured records (RC-001, RC-003). Canonical evaluation does not interpret ordinary language (RC-005).

## Evidence pointers

| Evidence | Location |
|---|---|
| Grammar contract | `PLAIN_LANGUAGE_V0_GRAMMAR.md` |
| Parser tests | `tests/compiler/test_plain_language.py` |
| Closed-loop intake | `tests/compiler/test_plain_language_closed_loop.py` |
| Library/CLI parity | `tests/compiler/test_plain_language_parity.py` |
| Certification / non-claims | `tests/compiler/test_mission_013_certification.py` |
| Schedule honesty | `tests/compiler/test_mission_013_schedule.py` |
| MISSION-012 regression | `tests/compiler/test_mission_012_certification.py`, `test_closed_loop.py` |
| MISSION-009 contract regression | `tests/evaluation/test_evaluation_repair_contract.py` |
| Mission report | `MISSION_013_REPORT.md` |
| Owner acceptance (draft) | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-007.md` |

## Approved authoring profiles

| Profile | Status |
|---|---|
| `structured_minimal_v0` | Implemented in `closed_loop.requirements_to_ir` (OAR-005/OAR-006) |
| `structured_developer_v0` | Implemented (developer envelope → IR) |
| `plain_language_v0` | M1 intake only — parses to `structured_minimal_v0`; awaits OAR-007 |

M2 model-assisted and M3 Simple Mode UI remain future per [PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md](../mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md).

## Non-claims

- Not freeform NLP — lines outside the grammar are parse errors, never guessed requirements.
- Not M2 model-assisted suggestion, not M3 / Simple Mode UI semantics.
- Not full MISSION-008 production requirements compiler; maturity map row stays `PARTIAL`.
- Not full Roadmap Phase 4B exit (thin perf ceilings; smoke scripts, not full consumer matrix).
- Not a live-provider runtime, hosted UI, benchmark suite, MissionRig, or IR v0.2.
- OAR-007 Ready does not Accept; evaluation/repair/headless loop OAR-006 `CERTIFIED` status is unchanged.
