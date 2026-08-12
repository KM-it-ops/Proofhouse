# MISSION-012 Report — Offline Headless Eval/Repair/Evidence Graduation

**Status:** Graduation package prepared; OAR-006 ready for owner acceptance (not Accepted).  
**Baseline:** `9d7321c` (MISSION-011 certification).  
**Branch:** `feature/mission-012-compiler-graduation`  
**Commits:** `ce0c617` … `ffeadef`

## Scope

Campaign COMPILER Phase A graduates MISSION-010 prototype closed-loop semantics toward production-grade **offline** headless behavior:

1. Governance honesty sync (OAR-005 alignment)
2. Deterministic evaluator module (`evaluation.py`)
3. Bounded repair module + test-hook quarantine (`repair.py`, `ClosedLoopTestHooks`)
4. Versioned evidence bundle (`evidence.py`, `eeb-headless-v0.1`)
5. Library/CLI deep parity + external-consumer smoke
6. This report, OAR-006 draft, maturity promotion, certification README

## Deliverables

| Area | Artifact |
|---|---|
| Evaluator | `src/promptrig/compiler/evaluation.py` — `evaluate_deterministic`, EVR-NET/DET/BSL rules |
| Repair | `src/promptrig/compiler/repair.py` — budgets `{0,1,2}`, `EVR-SEC-0001` refuse |
| Evidence | `src/promptrig/compiler/evidence.py` — `loop_id`, `evidence_schema`, contract `0.1.0` emit |
| Public API | `promptrig.compiler.api` re-exports `run_closed_loop`, `closed_loop_from_json`, options/result types |
| Governance | OAR-006 draft, maturity map rows, `architecture/mission-012-certification/` |

## Test evidence (branch HEAD)

| Suite | Coverage |
|---|---|
| `tests/compiler/test_evaluation_engine.py` | Network block, compile fail, baseline-required block, PASS |
| `tests/compiler/test_repair_engine.py` | Security weaken refuse, immutable-field preservation |
| `tests/compiler/test_evidence_bundle.py` | Graduated IDs, `prototype_id` alias, contract_version dual accept |
| `tests/compiler/test_closed_loop_parity.py` | Library/CLI deep parity for budgets 0/1/2 |
| `tests/compiler/test_mission_012_certification.py` | External-consumer subprocess smoke (api-only import) |
| `tests/compiler/test_closed_loop.py` | End-to-end loop, CLI has no `force_*` flags |
| `tests/compiler/test_mission_011_certification.py` | OAR-005 schedule/profile gates (regression) |
| `tests/evaluation/test_evaluation_repair_contract.py` | MISSION-009 contract package validator (unchanged PASS) |

**Verification command:** `uv run pytest tests/compiler tests/evaluation -v`

## Residual gaps (honest)

MISSION-012 does **not** claim full Roadmap Phase 4B exit:

- Evaluator is a deterministic compile/security/network oracle for fake-adapter artifacts — not a full rubric/dataset product engine.
- External-consumer proof is a single subprocess smoke script, not a full consumer matrix.
- Performance/resource ceilings and cross-platform packaging gates are thin relative to full Phase 4B bar.
- Requirements compiler remains structured profiles only (`PARTIAL`); plain-language (M1/M2) is out of scope.
- No live providers, hosted UI, benchmarks, MissionRig, IR v0.2, or enterprise SAST.

Owner acceptance via OAR-006 is required before treating this graduation as certified beyond `IMPLEMENTED_NOT_CERTIFIED`.

## Non-claims

Live execution, API keys on the certified path, Simple Mode UI semantics, benchmark results, and production hosted surfaces remain unauthorized.
