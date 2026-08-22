# MISSION-020 Report — Authoring-Prose Producers

**Status:** OAR-014 Ready for owner acceptance.  
**Baseline:** `af40a53`.  
**Branch:** `feature/mission-020-authoring-prose-producers`  
**HEAD (Tasks 1–3):** `41c34cc`

## Scope

Campaign COMPILER constrained authoring-prose producers for **`plain_language_v0` text envelopes** (`{profile, text}`) alongside MISSION-017 file/api, MISSION-018 simple/developer, and MISSION-019 prs. `parse_plain_language_v0` and `produce_plain_language_requirements` in `promptrig.compiler.requirements_plain_produce` lower constrained prose into canonical MISSION-008 artifact mappings. `compile_requirements_input` dispatches: `requirements_document` present → MISSION-016 canonical path; `{profile, text}` prose envelope → plain producer then compile; else `produce_requirements` envelope path. One rule engine: `evaluate_contract_rules` (sole RC-065 implementation). Public `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch canonical vs prose vs file/api/simple/developer/prs envelope; CLI help names `plain_language_v0`. Goal maps `direct` to `/objective/goal`; numbered and constraint records remain unresolved mappings, so valid grammar is BLOCKED / `RQC-BLK-0001` rather than invented SUCCESS. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`.

Does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, a full MISSION-008 production compiler, PRS **language** implementation (grammar/parser; RCD-008-009 remains DEFERRED), live providers, M3, freeform NLP, or benchmarks.

OAR-009 remains **Ready for owner acceptance** (not Accepted). OAR-010, OAR-011, OAR-012, and OAR-013 remain **Accepted**. OAR-014 is **Ready for owner acceptance** (not Accepted).

## Tasks 1–3

| Task | Commit | Deliverable |
|---|---|---|
| 1 | `fb2a46a` | Certification README + schedule honesty test (`test_mission_020_schedule.py`) |
| 2 | `4f8aab9` | Plain-language lowerer in `requirements_plain_produce.py`; dispatch in `requirements_contract.py`; `test_mission_020_produce.py` |
| 3 | `41c34cc` | CLI help naming `plain_language_v0`; OAR-014 Ready; maturity/deferred/README/OPEN_QUESTIONS; this report |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-020-certification/README.md` |
| Plain-language lowerer | `src/promptrig/compiler/requirements_plain_produce.py` |
| Compose dispatch | `compile_requirements_input` third dispatch for `{profile, text}` prose envelopes |
| CLI | `promptrig-compiler compile-requirements` help names `plain_language_v0` text envelope |
| Shared engine | `evaluate_contract_rules` unchanged (MISSION-016) |
| Governance | OAR-014 Ready for owner acceptance; Requirements compiler stays `PARTIAL`; OAR-009 still Ready; OAR-010/OAR-011/OAR-012/OAR-013 Accepted |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_020_schedule.py` | Certification README honesty; OQ-008-001–010 still listed; PRS language DEFERRED; no full 008 / no M3 |
| `tests/compiler/test_mission_020_produce.py` | Valid grammar BLOCKED not SUCCESS; freeform parse blocked; extra keys schema invalid; prs envelope regression; CLI help names `plain_language_v0` |

**Verification command:** `uv run --with pytest python -m pytest tests/compiler tests/evaluation tests/requirements -q`

**Result (Task 3, pre-commit):** 499 passed in 82.56s

## Residual gaps (honest)

MISSION-020 does **not** claim full Roadmap Phase 4B exit, a CERTIFIED requirements compiler, or a full MISSION-008 production compiler:

- Constrained `plain_language_v0` lowerer only — valid grammar yields BLOCKED not SUCCESS; not freeform NLP; PRS **language** (grammar, parser, CONTRACT_CANDIDATE) remains **DEFERRED** per `PRS_DISPOSITION.md`; compact `cases.json` stays test-only.
- Requirements compiler maturity remains **`PARTIAL`** — structured profiles + M1 intake + M2 fake sidecar + MISSION-016 canonical-record engine + MISSION-017 file/api + MISSION-018 simple/developer + MISSION-019 prs + this authoring-prose lowerer; not CERTIFIED.
- OQ-008-001 through OQ-008-010 remain owner-resolved policy only (fail closed; not implemented).
- OAR-006/007/008 **Accepted** boundaries unchanged; OAR-009 is still **Ready for owner acceptance**, not Accepted; OAR-010, OAR-011, OAR-012, and OAR-013 are **Accepted**; OAR-014 is **Ready**, not Accepted.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, or enterprise SAST.
- This mission does **not** unblock M3. Next authorized step remains M3 per schedule **and** OQ implementation (owner-resolved, not implemented).

## Non-claims

Matching OAR-014: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS language/grammar/parser, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, and implementing OQ-008-001 through OQ-008-010 remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-009 remains Ready (not Accepted by this record). OAR-010, OAR-011, OAR-012, and OAR-013 remain Accepted. OAR-014 is Ready (not Accepted).
