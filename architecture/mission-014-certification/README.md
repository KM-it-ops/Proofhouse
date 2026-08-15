# Fake Model-Assisted M2 Certification Package (MISSION-014)

**Status:** OAR-008 Accepted 2026-08-14 — M2 fake suggester sidecar certified.  
**Baseline:** MISSION-013 M1 (`9e1afc9` branch point; OAR-007 Accepted 2026-08-14).  
**Suggester profile:** `fake_suggester_v0` / producer `fake-suggester-v0` — optional sidecar on closed loop.

## Scope

MISSION-014 adds an optional evidence sidecar only:

- Fake/scripted suggester contract (`FAKE_SUGGESTER.md`) — not a live model
- Deterministic proposal builder (`model_suggest.py`) with `MAS-GATE-*` fail-closed diagnostics
- Opt-in `enable_model_suggestions` on `closed_loop_from_json` / CLI (default off); `012`/`013` keys unchanged
- Library/CLI parity and minimal external-consumer smoke (public `promptrig.compiler.api` only)

Proposals are sidecar evidence with `acceptance_state=proposed` and `authority_basis=model_suggested`. They are **never mapped to IR** by `requirements_to_ir`. IR `requirement_ids` with suggestions on must equal the suggestion-off run for the same structured document.

## Evidence pointers

| Evidence | Location |
|---|---|
| Suggester contract | `FAKE_SUGGESTER.md` |
| Unit tests | `tests/compiler/test_model_suggest.py` |
| Closed-loop sidecar | `tests/compiler/test_model_suggest_closed_loop.py` |
| Library/CLI parity | `tests/compiler/test_model_suggest_parity.py` |
| Certification / non-claims | `tests/compiler/test_mission_014_certification.py` |
| Schedule honesty | `tests/compiler/test_mission_014_schedule.py` |
| MISSION-013 regression | `tests/compiler/test_plain_language*.py`, `test_mission_013_certification.py` |
| MISSION-012 regression | `tests/compiler/test_mission_012_certification.py`, `test_closed_loop.py` |
| MISSION-009 contract regression | `tests/evaluation/test_evaluation_repair_contract.py` |
| Mission report | `MISSION_014_REPORT.md` |
| Owner acceptance | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-008.md` |

## Approved authoring profiles

| Profile | Status |
|---|---|
| `structured_minimal_v0` | Implemented in `closed_loop.requirements_to_ir` (OAR-005/OAR-006) |
| `structured_developer_v0` | Implemented (developer envelope → IR) |
| `plain_language_v0` | M1 intake only — parses to `structured_minimal_v0`; OAR-007 Accepted 2026-08-14 |
| `fake_suggester_v0` | M2 sidecar only — proposals as evidence; OAR-008 Accepted 2026-08-14 |

M3 Simple Mode UI remains future per [PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md](../mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md).

## Non-claims

- Not a live model — no provider SDK, HTTP client, credentials, or network on the certified path.
- Not freeform NLP — suggestions are structured proposal records, not unconstrained language understanding.
- Not M3 / Simple Mode UI semantics.
- Not full MISSION-008 production requirements compiler; maturity map row stays `PARTIAL`.
- Not full Roadmap Phase 4B exit (thin perf ceilings; smoke scripts, not full consumer matrix).
- Not a live-provider runtime, hosted UI, benchmark suite, MissionRig, or IR v0.2.
- OAR-008 Accepted certifies the fake sidecar only; evaluation/repair/headless loop OAR-006 `CERTIFIED` status is unchanged; Requirements compiler remains `PARTIAL`.
