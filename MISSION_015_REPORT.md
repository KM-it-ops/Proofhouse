# MISSION-015 Report — Phase 4B Residual Evidence

**Status:** OAR-009 Ready for owner acceptance (not Accepted).  
**Baseline:** `8fc5c43` (`main`, PR #21 merge / OAR-008 Accepted).  
**Branch:** `feature/mission-015-phase4b-residual`

## Scope

Campaign COMPILER residual evidence for the already-certified offline fake-adapter closed loop (OAR-006/007/008). No new semantic compiler path. Does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, live providers, M3, or benchmarks.

Ambition-gap C4 (IR v0.2 planning) is **not** this mission.

## Tasks 1–6

| Task | Deliverable |
|---|---|
| 1 | Residual contract README + schedule honesty test (`test_mission_015_schedule.py`) |
| 2 | PEP 517 `[build-system]`, `packaging_util.py`, isolated-venv clean-install (`test_mission_015_clean_install.py`) |
| 3 | Installed-package consumer matrix doc + `external_consumer_matrix.py` (`test_mission_015_consumer_matrix.py`) |
| 4 | Operational resource ceilings `resource_bounds.py` / `RESOURCE_BOUNDS.md` (`test_mission_015_resource_bounds.py`) |
| 5 | CI `wheel-install` job on `ubuntu-latest` (`test_mission_015_ci.py`) |
| 6 | This report, OAR-009 draft, maturity map and README honesty updates |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-015-certification/README.md`, `CONSUMER_MATRIX.md`, `RESOURCE_BOUNDS.md` |
| Packaging | `pyproject.toml` `[build-system]`; `tests/compiler/packaging_util.py` |
| Consumer matrix | `tests/compiler/fixtures/external_consumer_matrix.py` |
| Resource bounds | `src/promptrig/compiler/resource_bounds.py` |
| CI | `.github/workflows/ci.yml` `wheel-install` job (eighth job) |
| Governance | OAR-009 Ready for owner acceptance; maturity map; deferred registry; root README Status |

## Test evidence

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_015_schedule.py` | Residual scope; explicit non-claims; OAR-009 |
| `tests/compiler/test_mission_015_clean_install.py` | PEP 517 build-system; isolated pip install; doctor + closed-loop consumer |
| `tests/compiler/test_mission_015_consumer_matrix.py` | Matrix doc; structured / `plain_language_v0` / fake suggester / Simple Mode / `network_allowed` |
| `tests/compiler/test_mission_015_resource_bounds.py` | Operational ceilings; not-a-benchmark doc; fixture respects bounds |
| `tests/compiler/test_mission_015_ci.py` | Eight-job CI shape; `wheel-install` job |
| `tests/compiler/test_mission_012_certification.py` | OAR-006 regression (unchanged) |
| `tests/compiler/test_mission_013_certification.py` | OAR-007 regression (unchanged) |
| `tests/compiler/test_mission_014_certification.py` | OAR-008 regression (unchanged) |
| `tests/evaluation/test_evaluation_repair_contract.py` | MISSION-009 contract package (unchanged PASS) |

**Verification command:** `.venv/Scripts/python -m pytest tests/compiler tests/evaluation -q`

## Residual gaps (honest)

MISSION-015 does **not** claim full Roadmap Phase 4B exit or CERTIFIED requirements compiler:

- Residual evidence only: PEP 517 clean-install, installed-package public-API consumer matrix, operational fail-closed resource ceilings for `closed_loop_requirements_minimal.json` + `repair_budget=1` — **not a benchmark** (REJ-005).
- Requirements compiler maturity remains **`PARTIAL`** — structured profiles + M1 intake + M2 fake sidecar; not full MISSION-008 production compiler.
- OAR-006/007/008 **Accepted** boundaries unchanged; OAR-009 is **Ready for owner acceptance**, not Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, or enterprise SAST.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.

## Non-claims

Matching OAR-009: live execution, API keys on the certified path, freeform NLP, live model calls, Simple Mode UI semantics, benchmark/comparative performance claims, CERTIFIED requirements compiler, full MISSION-008 production compiler, full Roadmap Phase 4B exit, and production hosted surfaces remain unauthorized.
