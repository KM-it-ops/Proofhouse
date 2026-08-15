# MISSION-014 Report — Model-Assisted M2 (Fake Suggester Sidecar)

**Status:** M2 implemented on branch; OAR-008 **Ready for owner acceptance** (not Accepted).  
**Baseline:** `9e1afc9` (`main`, PR #20 merge).  
**Branch:** `feature/mission-014-model-assisted-m2`  
**HEAD (pre-Task-6 docs commit):** `f194434`  
**Commits:** `6f1f21a` … `f194434`

## Scope

Campaign COMPILER Phase A extends MISSION-012/013 offline headless closed loop with **M2 optional fake model-assisted suggestion sidecar**:

1. Normative fake-suggester contract (`FAKE_SUGGESTER.md`) and schedule honesty
2. Deterministic proposal builder (`model_suggest.py`) — `fake-suggester-v0` / `fake_suggester_v0`
3. Always-on MAS boundary gate (`validate_model_boundary`) with `MAS-GATE-*` diagnostics
4. Opt-in closed-loop sidecar (`enable_model_suggestions`, default off); proposals never mapped to IR
5. Library/CLI parity and external-consumer smoke; certification tests (no provider imports, no `force_*` CLI, Simple Mode still BLOCKED)
6. This report, OAR-008 draft, maturity map updates (Requirements compiler stays `PARTIAL`)

## Deliverables

| Area | Artifact |
|---|---|
| Contract | `architecture/mission-014-certification/FAKE_SUGGESTER.md` |
| Suggester | `src/promptrig/compiler/model_suggest.py` — `build_fake_model_proposal`, `validate_model_boundary` |
| Closed loop | `closed_loop_from_json` / `run_closed_loop` opt-in `enable_model_suggestions`; sidecar evidence only |
| Public API | `promptrig.compiler.api` exports `build_fake_model_proposal` (lazy PEP 562) |
| CLI | `promptrig-compiler closed-loop --enable-model-suggestions` (opt-in; default off) |
| Governance | OAR-008 Ready for owner acceptance, maturity map, certification README |

## Test evidence (HEAD `f194434`)

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_014_schedule.py` | Schedule hard rule; MISSION-014; `fake-suggester-v0`; `FAKE_SUGGESTER.md` |
| `tests/compiler/test_model_suggest.py` | Deterministic proposal; no input mutation; no provider/HTTP imports; MAS-GATE-0001/0002 |
| `tests/compiler/test_model_suggest_closed_loop.py` | Default off; IR ids unchanged with sidecar; self-accept INVALID_OUTPUT; JSON flag |
| `tests/compiler/test_model_suggest_parity.py` | Public export; library/CLI deep parity; external-consumer smoke |
| `tests/compiler/test_mission_014_certification.py` | No provider imports; no `force_*` CLI; Simple Mode BLOCKED with suggestions; MAS-GATE-0002/0003 hooks |
| `tests/compiler/test_plain_language*.py` | M1 intake regression (unchanged) |
| `tests/compiler/test_mission_012_certification.py` | OAR-006 closed-loop smoke (regression) |
| `tests/evaluation/test_evaluation_repair_contract.py` | MISSION-009 contract package (unchanged PASS) |

**Verification command:** `uv run python -m pytest tests/compiler tests/evaluation -v` — **385 passed** (24.92s).

## Residual gaps (honest)

MISSION-014 does **not** claim full Roadmap Phase 4B exit, CERTIFIED requirements compiler, or live model assistance:

- M2 is **fake/scripted offline only** (`fake-suggester-v0`) — no provider SDK, HTTP client, credentials, or network on the certified path.
- Proposals remain `acceptance_state=proposed` / `authority_basis=model_suggested` sidecar evidence; **never mapped to IR** by `requirements_to_ir`.
- No freeform NLP; no live model-assisted suggestion; no M3 / Simple Mode UI semantics (`authoring_mode=simple_ui_only` still BLOCKED).
- Requirements compiler row remains **`PARTIAL`** — structured profiles + M1 intake + M2 fake sidecar; not full MISSION-008 production compiler.
- OAR-008 is **Ready for owner acceptance** — not Accepted until Boss explicitly accepts.
- OAR-006 **CERTIFIED** status for evaluation, repair, and headless loop is unchanged; MISSION-014 adds optional sidecar evidence only.
- External-consumer proof is subprocess smoke scripts, not a full consumer matrix.
- Performance/resource ceilings remain thin relative to full Phase 4B bar.
- No live providers, hosted UI, benchmarks, MissionRig, IR v0.2, or enterprise SAST.

## Non-claims

Live execution, API keys on the certified path, freeform NLP, live model calls, Simple Mode UI semantics, benchmark results, CERTIFIED requirements compiler, OAR-008 Accepted status, and production hosted surfaces remain unauthorized.
