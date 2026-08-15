# MISSION-013 Report — Plain-Language Headless M1 (Constrained Prose)

**Status:** M1 Accepted via OAR-007 (Boss, 2026-08-14).  
**Baseline:** `9e5028d` (MISSION-012 HEAD).  
**Branch:** `feature/mission-013-plain-language-m1`  
**Commits:** `63ecc7a` … `1b34ec0` (+ OAR-007 acceptance commit)

## Scope

Campaign COMPILER Phase A extends MISSION-012 offline headless closed loop with **M1 constrained prose intake**:

1. Normative grammar contract (`PLAIN_LANGUAGE_V0_GRAMMAR.md`) and schedule honesty
2. Deterministic parser (`plain_language.py`) — `plain_language_v0` → `structured_minimal_v0`
3. Closed-loop JSON dispatch (`closed_loop_from_json`) with `intake_profile` evidence
4. Library/CLI parity and external-consumer smoke for plain-language envelopes
5. Certification tests (no provider imports, freeform rejection, Simple Mode still forbidden)
6. This report, OAR-007, maturity map updates (Requirements compiler stays `PARTIAL`)

## Deliverables

| Area | Artifact |
|---|---|
| Grammar | `architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md` |
| Parser | `src/promptrig/compiler/plain_language.py` — `parse_plain_language_v0`, `PlainLanguageParseError` |
| Closed loop | `closed_loop_from_json` accepts `profile: plain_language_v0` + `text`; threads `intake_profile` |
| Public API | `promptrig.compiler.api` exports `parse_plain_language_v0` (lazy PEP 562) |
| Governance | OAR-007 Accepted 2026-08-14, maturity map, certification README |

## Test evidence (branch HEAD before Task 6 commit)

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_013_schedule.py` | Schedule M1 authorization, grammar file exists |
| `tests/compiler/test_plain_language.py` | Parse minimal fixture, reject freeform, gaps, `#` comments |
| `tests/compiler/test_plain_language_closed_loop.py` | PASS on fixture; `intake_profile` in evidence |
| `tests/compiler/test_plain_language_parity.py` | Library/CLI parity; external-consumer smoke |
| `tests/compiler/test_mission_013_certification.py` | No provider imports; freeform never IR; Simple Mode BLOCKED |
| `tests/compiler/test_closed_loop.py` | Structured profile regression |
| `tests/compiler/test_mission_011_certification.py` | OAR-005 schedule/profile gates (regression) |
| `tests/compiler/test_mission_012_certification.py` | OAR-006 closed-loop smoke (regression) |
| `tests/evaluation/test_evaluation_repair_contract.py` | MISSION-009 contract package (unchanged PASS) |

**Verification command:** `uv run pytest tests/compiler tests/evaluation -v` — **362 passed** (10.08s).

## Residual gaps (honest)

MISSION-013 does **not** claim full Roadmap Phase 4B exit or CERTIFIED requirements compiler:

- M1 is **constrained prose only** — freeform NLP lines fail closed (`PL-PARSE-*`); not a general language understanding path.
- No M2 model-assisted suggestion (MISSION-014, future).
- No M3 / Simple Mode UI semantics (`authoring_mode=simple_ui_only` still BLOCKED).
- Requirements compiler row remains **`PARTIAL`** — structured profiles + M1 intake; not full MISSION-008 production compiler.
- OAR-006 **CERTIFIED** status for evaluation, repair, and headless loop is unchanged; MISSION-013 adds intake only.
- External-consumer proof is subprocess smoke scripts, not a full consumer matrix.
- Performance/resource ceilings remain thin relative to full Phase 4B bar.
- No live providers, hosted UI, benchmarks, MissionRig, IR v0.2, or enterprise SAST.

OAR-007 Accepted 2026-08-14. Narrow M1 constrained-prose intake is certified with the residual gaps above; Requirements compiler remains `PARTIAL`; full Phase 4B exit remains unauthorized.

## Non-claims

Live execution, API keys on the certified path, freeform NLP, model calls, Simple Mode UI semantics, benchmark results, CERTIFIED requirements compiler, and production hosted surfaces remain unauthorized.
