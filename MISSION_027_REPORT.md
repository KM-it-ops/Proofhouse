# MISSION-027 Report — Evaluation/Repair Product Bar

**Status:** OAR-021 Ready.
This record is Ready and is not Accepted until Boss Accepts it.
**Baseline:** rebased onto `7f1e64c` (MISSION-028 / OAR-022 skip-cert law).
**Branch:** `feature/mission-027-eval-repair-product`.
**Worktree:** `C:/AI/projects/PromptRig/.worktrees/mission-027-eval-repair-product`.

## Scope

Additive rubric/dataset engine, baseline comparison, scoring aggregation, and a production regression gate beside the existing fake-adapter oracle. Closed-loop `product_eval` defaults off. No new CLI. `evaluate_deterministic` unchanged.

Does **not** promote the requirements compiler to CERTIFIED. Does **not** certify the new product surface. Does **not** claim full Roadmap Phase 4B exit, a full MISSION-008 production compiler, PRS **language**, live providers, M3, freeform NLP, IR v0.2, alias-group implementation, or dropping `-draft`.

OAR-009 through OAR-020 remain historical snapshots (do not rewrite). OAR-022 exists as a sibling skip-cert record (Ready; not rewritten). Peer review is not a gate. Independent 4B-exit certification is not a Phase 5–9 entry gate. Remaining 4B engineering after this mission is the 008 SUCCESS/PARTIAL join.

Requirements compiler stays `PARTIAL`. Fake-adapter eval/repair oracle stays `CERTIFIED`. Product surface is implemented and **not CERTIFIED**. OAR-021 is **Ready** (not Accepted).

## Tasks 1–6

| Task | Commit | Deliverable |
|---|---|---|
| 1 | `8d838ae` | JSONL dataset loader (`eval_dataset.py`) |
| 2 | `cbdf4c5` | Deterministic JSON rubric scorer (`eval_rubric.py`) |
| 3 | `38f2f94` | Score aggregation with `EVR-SCR-0001` (`eval_aggregate.py`) |
| 4 | `e2318ea` | Product evaluation path with baseline regression gate (`eval_product.py`) |
| 5 | `f686ab3` | Opt-in closed-loop `product_eval` hook (default off) |
| 6 | this commit | OAR-021 Ready, mission-027 honesty pack, current-state docs |

## Deliverables

| Area | Artifact |
|---|---|
| Certification package | `architecture/mission-027-certification/README.md` |
| Governance | OAR-021 Ready (not Accepted); Requirements compiler stays `PARTIAL`; oracle Evaluation/Repair stay `CERTIFIED`; product surface not CERTIFIED |
| Current-state docs | PROJECT_ORIENTATION, CAPABILITY_MATURITY_MAP (Evaluation/Repair oracle CERTIFIED; product not CERTIFIED; compiler PARTIAL), OPEN_QUESTIONS last paragraph, DEFERRED_AND_REJECTED_WORK OAR-006 engines now implemented, root README append |
| Engines (Tasks 1–5) | `eval_dataset.py`, `eval_rubric.py`, `eval_aggregate.py`, `eval_product.py`; closed-loop hook default off |
| Producer/CLI | no new CLI; `evaluate_deterministic` unchanged |

## Tests added

| Suite | Coverage |
|---|---|
| `tests/compiler/test_mission_027_schedule.py` | Mission README honesty; PARTIAL compiler; Evaluation CERTIFIED; OAR-021 Ready (status line has Ready, not Accepted) |
| `tests/compiler/test_eval_dataset.py` | JSONL loader |
| `tests/compiler/test_eval_rubric.py` | Rubric scorer |
| `tests/compiler/test_eval_aggregate.py` | Aggregation / `EVR-SCR-0001` |
| `tests/compiler/test_eval_product.py` | Baseline, regression, network block, closed-loop default off |

**Verification command:** `uv run --with pytest python -m pytest tests/compiler/test_mission_027_schedule.py tests/compiler/test_eval_dataset.py tests/compiler/test_eval_rubric.py tests/compiler/test_eval_aggregate.py tests/compiler/test_eval_product.py tests/compiler/test_evaluation_engine.py tests/compiler/test_mission_012_certification.py tests/compiler/test_mission_025_schedule.py tests/compiler/test_mission_026_schedule.py tests/compiler/test_mission_028_schedule.py -v`

Result: **24 passed**. `test_mission_026_schedule.py` present and green; 026 pack files unmodified. Skip-cert law (`test_mission_028_schedule.py`) green.

## Residual gaps (honest)

MISSION-027 does **not** claim full Roadmap Phase 4B exit, a CERTIFIED requirements compiler, or a CERTIFIED product evaluation surface:

- Recorded this campaign: product eval/repair bar implemented beside the oracle. Fake-adapter only.
- Product surface (rubric, dataset, aggregation, regression) is implemented and **not CERTIFIED**.
- Remaining 4B engineering: the 008 SUCCESS/PARTIAL join (later unit).
- Locked not-built: OQ-008-004, OQ-008-007, OQ-008-008, OQ-008-009.
- Requirements compiler maturity remains **`PARTIAL`** — not CERTIFIED.
- OAR-021 Ready (not Accepted). OAR-022 skip-cert Ready (sibling, not rewritten). OAR-009 through OAR-020 historical.
- No live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, hosted UI, MissionRig, IR v0.2, alias-group implementation, or enterprise SAST.
- This mission does **not** unblock M3.

## Non-claims

Matching OAR-021: live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS language/grammar/parser, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, CERTIFIED evaluation/repair product surface, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST, and dropping `-draft` remain unauthorized. Requirements compiler stays `PARTIAL`. OAR-021 Ready (not Accepted).
