# MISSION-017 Report — File/API Envelope Producers

**Status:** OAR-011 Ready for owner acceptance (not Accepted).  
**Baseline:** local `main` @ `62a7e1b`.  
**Branch:** `feature/mission-017-008-file-api-producers`  
**HEAD (Tasks 1–3):** `e461797`

## Scope

Campaign COMPILER remaining MISSION-008 envelope producers for **file and api authoring envelopes only**. `produce_requirements` in `promptrig.compiler.requirements_produce` assembles canonical MISSION-008 artifact mappings. `compile_requirements_input` dispatches: `requirements_document` present → MISSION-016 canonical path; else produce then compile. One rule engine: `evaluate_contract_rules` (sole RC-065 implementation). Public `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch envelope vs canonical payload. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`.

Does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, a full MISSION-008 production compiler (no simple/developer/prs/authoring-prose producers), live providers, M3, freeform NLP, or benchmarks.

OAR-009 remains **Ready for owner acceptance** (not Accepted). OAR-010 remains **Accepted**. OAR-011 is **Ready for owner acceptance** (not Accepted by this report).

## Tasks 1–4

| Task | Commit | Deliverable |
|---|---|---|
| 1 | `e750046` | Certification README + schedule honesty test (`test_mission_017_schedule.py`) |
| 2 | `3a8bb56` | `produce_requirements`, `compile_requirements_input`; `requirements_produce.py`; `test_mission_017_produce.py` |
| 3 | `e461797` | Lazy API exports + CLI compose dispatch via `compile_requirements_input` |
| 4 | (this commit) | This report, OAR-011 Ready, maturity map, deferred registry, README Status |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-017-certification/README.md` |
| Envelope producers | `src/promptrig/compiler/requirements_produce.py` (`produce_requirements`) |
| Compose dispatch | `compile_requirements_input` in `requirements_contract.py`; lazy exports in `api.py`; CLI `compile-requirements` |
| Shared engine | `evaluate_contract_rules` unchanged (MISSION-016); architecture re-export unchanged |
| Governance | OAR-011 Ready for owner acceptance; Requirements compiler stays `PARTIAL`; OAR-009 still Ready; OAR-010 Accepted |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_017_schedule.py` | Certification README honesty; OQ-008-001–009 still listed; no full 008 / no M3 |
| `tests/compiler/test_mission_017_produce.py` | File/api envelope assembly; trust-boundary codes; compose dispatch; API/CLI parity; 016 byte-stability |

**Verification command:** `.venv/Scripts/python -m pytest tests/compiler tests/evaluation tests/requirements -q`

**Result (Task 4, pre-commit):** 475 passed in 154.54s

## Residual gaps (honest)

MISSION-017 does **not** claim full Roadmap Phase 4B exit, a CERTIFIED requirements compiler, or a full MISSION-008 production compiler:

- File/api envelope assembly only — not simple/developer/prs/authoring-prose producers; compact `cases.json` stays test-only.
- Requirements compiler maturity remains **`PARTIAL`** — structured profiles + M1 intake + M2 fake sidecar + MISSION-016 canonical-record engine + this file/api producer layer; not CERTIFIED.
- OQ-008-001 through OQ-008-009 remain **open** (fail closed; no invented owner answers).
- OAR-006/007/008 **Accepted** boundaries unchanged; OAR-009 is still **Ready for owner acceptance**, not Accepted; OAR-010 is **Accepted**; OAR-011 is **Ready for owner acceptance**, not Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, or enterprise SAST.
- This mission does **not** unblock M3. Next authorized step remains M3 per schedule **and** remaining 008 authoring envelopes / OQ decisions.

## Non-claims

Matching OAR-011: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, simple/developer/prs/authoring-prose producers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, and resolving OQ-008-001 through OQ-008-009 remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-009 remains Ready (not Accepted by this record). OAR-010 remains Accepted.
