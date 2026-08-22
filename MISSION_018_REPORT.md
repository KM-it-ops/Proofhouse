# MISSION-018 Report — Simple/Developer Envelope Producers

**Status:** OAR-012 Ready for owner acceptance (not Accepted).  
**Baseline:** local `main` @ `6c807b4`.  
**Branch:** `feature/mission-018-simple-developer-producers`  
**HEAD (Tasks 1–3):** `5943090`

## Scope

Campaign COMPILER remaining MISSION-008 envelope producers for **simple and developer authoring envelopes** alongside MISSION-017 file/api. `produce_requirements` in `promptrig.compiler.requirements_produce` assembles canonical MISSION-008 artifact mappings. `compile_requirements_input` dispatches: `requirements_document` present → MISSION-016 canonical path; else produce then compile. One rule engine: `evaluate_contract_rules` (sole RC-065 implementation). Public `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch envelope vs canonical payload; CLI help names file/api/simple/developer envelopes. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`.

Does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, a full MISSION-008 production compiler (no prs/authoring-prose producers), live providers, M3, freeform NLP, or benchmarks.

OAR-009 remains **Ready for owner acceptance** (not Accepted). OAR-010 and OAR-011 remain **Accepted**. OAR-012 is **Ready for owner acceptance** (not Accepted by this report).

## Tasks 1–3

| Task | Commit | Deliverable |
|---|---|---|
| 1 | `421b729` | Certification README + schedule honesty test (`test_mission_018_schedule.py`) |
| 2 | `a6bf52e` | Simple/developer envelope producers in `requirements_produce.py`; `test_mission_018_produce.py` |
| 3 | `5943090` | CLI help naming simple/developer; OAR-012 Ready; maturity/deferred/README; this report |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-018-certification/README.md` |
| Envelope producers | `src/promptrig/compiler/requirements_produce.py` (simple/developer modes + kinds) |
| Compose dispatch | `compile_requirements_input` unchanged dispatch path; CLI `compile-requirements` help updated |
| Shared engine | `evaluate_contract_rules` unchanged (MISSION-016) |
| Governance | OAR-012 Ready for owner acceptance; Requirements compiler stays `PARTIAL`; OAR-009 still Ready; OAR-010/OAR-011 Accepted |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_018_schedule.py` | Certification README honesty; OQ-008-001–009 still listed; no full 008 / no M3 |
| `tests/compiler/test_mission_018_produce.py` | Simple/developer envelope assembly; prs rejection; wrong-kind schema invalid; imports rejected; CLI help names simple/developer |

**Verification command:** `uv run python -m pytest tests/compiler tests/evaluation tests/requirements -q`

**Result (Task 3, pre-commit):** 490 passed in 60.44s

## Residual gaps (honest)

MISSION-018 does **not** claim full Roadmap Phase 4B exit, a CERTIFIED requirements compiler, or a full MISSION-008 production compiler:

- Simple/developer envelope assembly only — not prs/authoring-prose producers; compact `cases.json` stays test-only.
- Requirements compiler maturity remains **`PARTIAL`** — structured profiles + M1 intake + M2 fake sidecar + MISSION-016 canonical-record engine + MISSION-017 file/api + this simple/developer producer layer; not CERTIFIED.
- OQ-008-001 through OQ-008-009 remain **open** (fail closed; no invented owner answers).
- OAR-006/007/008 **Accepted** boundaries unchanged; OAR-009 is still **Ready for owner acceptance**, not Accepted; OAR-010 and OAR-011 are **Accepted**; OAR-012 is **Ready for owner acceptance**, not Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, or enterprise SAST.
- This mission does **not** unblock M3. Next authorized step remains M3 per schedule **and** remaining 008 authoring envelopes / OQ decisions.

## Non-claims

Matching OAR-012: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, prs/authoring-prose producers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, and resolving OQ-008-001 through OQ-008-009 remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-009 remains Ready (not Accepted by this record). OAR-010 and OAR-011 remain Accepted.
