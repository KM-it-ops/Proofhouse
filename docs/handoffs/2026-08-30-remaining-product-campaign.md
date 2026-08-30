---
artifact_contract: "ce-handoff/v1"
created_at: "2026-08-30T04:42:00Z"
title: "PromptRig remaining-product campaign, local finish"
summary: "U1-U9 implemented on feature/mission-035-product-finish; do not burn GitHub Actions; owner Accept still outstanding. Canonical handoff lives in-repo because /tmp scratch is not visible on a new VM."
keywords: ["promptrig", "ce-work", "remaining-product-campaign", "mission-034", "mission-035", "mission-036", "hosted-slice", "missionrig", "github-actions", "stay-local", "ce-handoff"]
cwd: "."
resume_focus: "PR into main if Boss wants GitHub Actions. OAR-021 through OAR-029 Accepted 2026-08-30. Do not restore feature/** push CI. Do not treat Accepted as CERTIFIED."
repository: "km-it-ops/promptrig"
repo_root_sha: "5210cf3892e6d680e1ad1c90db769af4a4243e05"
branch: "feature/mission-035-product-finish"
head: "77a4c9c85cd09c3edb4fcdc5ca1377ffd4215f2b"
---

# PromptRig remaining-product campaign handoff

Fresh agents: this is orientation, not an instruction to merge, run GitHub Actions, or Accept OARs.

**Portable copy.** The original `/tmp/compound-engineering-*/ce-handoff/` scratch is host-local and will not exist on a new VM. This file in git is the resume source.

## Objective and latest intent

Boss invoked `/ce-plan` for remaining PromptRig work, then `/ce-work`. Horizon is full ROADMAP_V1 Phases 5-9. Session-settled: peer review is not a gate; remaining Phase 4B is engineering the product consumes, not a CERTIFIED/review campaign; the finished product is the success signal.

Latest explicit orders (2026-08-30):

1. GitHub Actions minutes ran out. Do not use Actions willy-nilly.
2. Cheap CI fix now; stay local for campaign work; ask before running hosted CI.
3. Carry on and finish the project (U8 runtime + U9).
4. Create a ce-handoff for the next session.
5. The `/tmp` scratchpad is not available on the new VM — persist this handoff in the repo.

Do not re-run workflows unless Boss explicitly asks. A PR into `main` is the appropriate Actions spend.

## Work completed

Campaign plan: `docs/plans/2026-08-29-1732-feat-remaining-product-campaign-plan.md` (`ce-unified-plan/v1`, `implementation-ready`, `execution: code`).

| Unit | Mission / OAR | Tip | What it is |
|---|---|---|---|
| U1 | MISSION-028 / OAR-022 Ready | origin `feature/mission-028-skip-cert-law` | Skip-cert law. ROADMAP Phase 5-implementation and 6-9 entry no longer require independent 4B-exit certification. |
| U2 | MISSION-027 / OAR-021 Ready | origin stacked under later feature branches | Product eval/repair bar; default-off closed-loop hook. Product surface not CERTIFIED. |
| U3 | MISSION-029 | origin | `promptrig-compiler evaluate-product` library/CLI JSON parity. |
| U4 | MISSION-030 / OAR-023 Ready | origin | 008 SUCCESS/PARTIAL into `structured_minimal_v0` then closed-loop. Unbridged `closed-loop` stays `EVR-RQC-0001`. |
| U5 | MISSION-031 / OAR-024 Ready | origin | IR v0.2 planning package. Frozen IR v0.1 schema unchanged. ADR-007 still Proposed. Q4 unpicked. |
| U6 | MISSION-032 / OAR-025 Ready | origin | Fail-closed opt-in `execute-openai`. Not closed-loop. Q1 unpicked. pytest marker `live`; `addopts = -m "not live"`. |
| U7 | MISSION-033 / OAR-026 Ready | origin `feature/mission-033-sealed-benchmark` at `32b6842` | Sealed offline benchmark. Not a published claim. |
| U8 contracts | MISSION-034 / OAR-027 Ready | `feature/mission-034-hosted-slice` at `d9b1398` | Stack-agnostic hosted contracts and generated OpenAPI. |
| U8 runtime | MISSION-035 / OAR-028 Ready | `feature/mission-035-product-finish` | Stdlib `HostedSlice`. Q2 pick `STACK-OWNER-SELECTED`. |
| U9 | MISSION-036 / OAR-029 Ready | same branch | One-profile MissionRig generator; workspace consume read-only; IR write-back `EVR-WS-0001`. |

Cheap CI trigger fix (on this branch at `5e7b2b2`): `.github/workflows/ci.yml` push is **main-only**; keep `pull_request` to `main` / `feature/promptrig-framework`; add `workflow_dispatch`. Dropped `feature/**`, `docs/**`, and `fix/**` push triggers. Also committed on `cursor/cloud-agent-1788048916910-1tqgz` at `0fc33d0`.

Local test fix (`f8c95a5`): `tests/compiler/test_mission_021_oq.py` valid numbered/constraint prose is SUCCESS (MISSION-023), not BLOCKED. Frozen IR sha256 pins updated to committed file digest `082e03e9b7c920a84b0359e71cb7429bf76a412cfcdc0b7d27f9d247ab0074e6` (schema bytes were never edited; the old pin was stale).

## Decisions and constraints

- Frozen `architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json` must not change.
- Requirements compiler stays **PARTIAL**. Fake-adapter eval/repair oracle stays **CERTIFIED**. CERTIFIED never expands scope.
- Do not fill `architecture/mission-026-certification/VERDICT.md`. Do not unlock PRS as a language. Do not label the requirements compiler CERTIFIED.
- Vite `apps/dashboard` and `apps/promptrig.jsx` are not Simple or Developer Mode. `simple_mode_ui` / `simple_ui_only` stay forbidden on closed-loop (AE5).
- Adapter order remains fake, then OpenAI, then Anthropic, then Gemini (OAR-001). Q1 (live model/ceilings/credential store) still unpicked. Live is a separate module, not a closed-loop flag.
- Q2 was unpicked in MISSION-034 `OPTIONS.json` (leave that file as the contract catalog). MISSION-035 ratified **STACK-OWNER-SELECTED** in `architecture/hosted-slice-v0.1/RUNTIME_PICK.json`: stdlib `HostedSlice.dispatch` plus file store plus JSON Simple/Developer views. Not FastAPI. Not Next.js.
- Q4 (IR v0.2 field shapes) still unpicked. U6 live is single-request; continuation recommendation is evidence-only (MISSION-031).
- 008 join is projection into `structured_minimal_v0` then `requirements_to_ir`, not RFC 6901 onto IR.
- Isolated worktree per unit. Stop at OAR **Ready**. Owner **Accept** is a separate human gate. Do not treat Ready as Accepted.
- Plan global DoD said Accept before dependent units; Boss later said finish the product, so 035/036 proceeded on Ready siblings.
- Python via `uv run` on Boss's machine. The cloud host that implemented 034-036 had `uv` missing and used `pip3` plus `python3 -m pytest`. Do not commit `uv.lock`.
- `promptrig-sdd-implementer` subagent may be absent; implementation was inline on that host.
- Dual CLIs: `promptrig` (legacy PromptOps) vs `promptrig-compiler` (Compiler Core). Do not reimplement PromptOps commands inside Compiler Core.

## Current state

Campaign tip: `feature/mission-035-product-finish`. Origin already had mission-028 through mission-033. 034/035/036 and the CI trigger fix live on this branch.

A new VM will **not** have the original gitignored `.worktrees/` paths (`/workspace/.worktrees/mission-034-hosted-slice`, `/workspace/.worktrees/mission-035-product-finish`) or `/tmp/compound-engineering-*`. Checkout this branch from origin instead.

Sibling local-only branches if this VM still exists: `feature/mission-034-hosted-slice` at `d9b1398`; cloud checkout `cursor/cloud-agent-1788048916910-1tqgz` at `0fc33d0` (CI fix only, based on MISSION-026).

## Authoritative references

- Plan: `docs/plans/2026-08-29-1732-feat-remaining-product-campaign-plan.md`
- Hosted contracts: `architecture/hosted-slice-v0.1/`
- Hosted runtime: `src/promptrig/compiler/hosted_slice.py`
- Q2 pick: `architecture/hosted-slice-v0.1/RUNTIME_PICK.json`
- MissionRig: `src/promptrig/compiler/missionrig.py`, `architecture/missionrig-v0.1/README.md`
- CI: `.github/workflows/ci.yml`
- OARs: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md` through `OAR-029.md` (all Ready, not Accepted, on this tip; 021-026 also on origin stacked branches)
- Skip-cert honesty: `tests/compiler/test_mission_028_schedule.py`
- Mode parity / AE5: `tests/compiler/test_mission_035_hosted.py`
- MissionRig: `tests/compiler/test_mission_036_missionrig.py`

## Verification already run (local, 035 worktree)

Passed: `test_mission_034_schedule`, `test_mission_035_hosted`, `test_mission_035_schedule`, `test_mission_036_missionrig`, `test_mission_036_schedule`, `test_mission_028_schedule`, `test_mission_021_oq`, `test_no_network_and_determinism`, `test_library_cli_parity`, `test_mission_033_schedule`, `test_benchmark_manifest_validation`, `test_closed_loop`, `test_mission_012_certification`.

GitHub Actions were not re-run after the cheap fix. Earlier origin pushes of mission-028-033 burned about 48 jobs; test jobs failed on the stale 021 BLOCKED assertion (fixed in `f8c95a5`).

## Unfinished / blockers

- OAR-021 through OAR-029 **Accepted 2026-08-30** by Boss.
- OAR-020 remains Ready (not Accepted).
- A PR into `main` will run the eight-job matrix; ask first. Do not restore `feature/**` push CI.
- Q1 unpicked: no real-network live tests.
- Q4 unpicked: no IR v0.2 production schema.
- FastAPI/Next.js not implemented (explicit non-pick).
- No public benchmark claim. Historical `review-cycles/v0.4/` is not a result.
- Draft PR #14 (`ci/tiered-gates-v0.1`) is a larger unmerged consumption-aware CI redesign; the cheap fix is the smaller trigger narrowing. Do not treat #14 as merged.

## Plausible next steps

One continuation: Boss Accepts the Ready OARs they want, then (if they ask) open a PR from `feature/mission-035-product-finish` into `main` so GitHub Actions runs once. Do not start a FastAPI/Next.js restack, live-network work, or IR v0.2 schema without a new owner pick (Q1, Q2 restack, or Q4).

## Skills that fit

- `ce-work` if implementing a new owner-authorized unit
- `ce-commit` / `ce-commit-push-pr` only after Boss explicitly authorizes a PR
- `verification-before-completion` / `verify-this` for local pytest
- Do not use GitHub Actions (`loop-on-ci`, `fix-ci`) unless Boss asks
