# Headless Offline Graduation Package v0.1 (MISSION-012)

**Status:** Graduation evidence for offline eval/repair/evidence promotion; OAR-006 ready for owner acceptance.  
**Baseline:** MISSION-011 certification (`9d7321c`, OAR-005).  
**Loop identity:** `mission-012-headless-closed-loop-v0.1` / `eeb-headless-v0.1`.

## Scope

MISSION-012 graduates MISSION-010 prototype closed-loop semantics:

- Deterministic evaluator module with authoritative EVR rules (network, compile, baseline, security)
- Bounded repair planner with immutable objective/constraints/requirement IDs
- Versioned evidence bundle with accepted contract versions `0.1.0` on emit
- Library/CLI deep parity and minimal external-consumer smoke (public `promptrig.compiler.api` only)

## Evidence pointers

| Evidence | Location |
|---|---|
| Evaluator tests | `tests/compiler/test_evaluation_engine.py` |
| Repair tests | `tests/compiler/test_repair_engine.py` |
| Evidence bundle tests | `tests/compiler/test_evidence_bundle.py` |
| Library/CLI parity | `tests/compiler/test_closed_loop_parity.py` |
| External consumer smoke | `tests/compiler/test_mission_012_certification.py`, `tests/compiler/fixtures/external_consumer_closed_loop.py` |
| MISSION-009 contract regression | `tests/evaluation/test_evaluation_repair_contract.py` |
| Mission report | `MISSION_012_REPORT.md` |
| Owner acceptance | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-006.md` |

## Approved authoring profiles (unchanged)

| Profile | Status |
|---|---|
| `structured_minimal_v0` | Implemented in `closed_loop.requirements_to_ir` |
| `structured_developer_v0` | Implemented (developer envelope → IR with tool/stop constraints) |

Plain-language / model-assisted Simple Mode is **not** implemented. See [PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md](../mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md).

## Non-claims

- Not full Roadmap Phase 4B exit (thin perf ceilings; single external-consumer smoke, not a full matrix).
- Not a live-provider runtime, hosted UI, benchmark suite, MissionRig, or IR v0.2.
- Evaluator is a deterministic fake-adapter oracle — not a full rubric/dataset product engine.
- OAR-006 is draft until Boss accepts; maturity map rows are `IMPLEMENTED_NOT_CERTIFIED` until then.
