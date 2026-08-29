# MISSION-032 Bounded Live OpenAI Execution

**Status:** OAR-025 Ready (not Accepted).
**Baseline:** Campaign remaining-product U6 on MISSION-031 (`d5388ea` IR v0.2 planning). Skip-cert law is OAR-022 Ready (not undone).
**Scope:** Fail-closed **opt-in** single-request live OpenAI execution in `src/promptrig/compiler/execution.py`. Adapters remain offline lowerers. `closed-loop` stays fake-only.

This mission does not promote the requirements compiler. Live is **DEFERRED-to-opt-in**, **not CERTIFIED**.

## What this mission records (narrow)

- **OAR-025 Ready (not Accepted).** This record is Ready until Boss Accepts. Do not treat it as Accepted.
- Requirements compiler stays **PARTIAL**. **Not CERTIFIED**. Not full MISSION-008. Not full Roadmap **Phase 4B** exit. Not M3.
- Fake-adapter eval/repair oracle stays **CERTIFIED**. CERTIFIED never expands scope.
- Live path is **DEFERRED-to-opt-in**, not CERTIFIED. Default compile/validate/closed-loop remain offline.
- **Q1 is unpicked.** No ratified first live model, token/cost ceiling table, or credential-store product. Model, ceilings, and credential material are required at call time (function args and/or env var name). Missing any of them fail-closes. Credential store is caller-supplied env var name / value at invoke time, not a vault. **Q1 remains an owner gate before real-network tests.**
- Live stays **single-request**. Continuation is **evidence-only** (not an IR field). This path does not add continuation fields to IR v0.1.
- `closed-loop` with `network_allowed` remains `EVR-NET-0001`. `promptrig-compiler compile --adapter openai` lowers only and never calls OpenAI.
- **OQ-008-004** / **OQ-008-007** / **OQ-008-008** / **OQ-008-009** remain locked-not-built.
- `EVR-SEC-0001` and `network_allowed=false` unchanged. Repair budgets `{0,1,2}`.
- `simple_mode_ui` / `simple_ui_only` stay forbidden on closed-loop.
- **Skip-cert** law (OAR-022) is not undone. Peer review is **not a gate**.
- OAR-021 remains MISSION-027. OAR-022 remains MISSION-028. OAR-023 remains MISSION-030. OAR-024 remains MISSION-031. This mission does not Accept them.

## Non-claims

- Not CERTIFIED requirements compiler. Not full MISSION-008. Not full Phase 4B exit.
- Not **M3** / **Simple Mode** UI.
- **Not CERTIFIED live execution.** Opt-in is not certification. **Not a live** certified provider path.
- **Not freeform** NLP. Not CERTIFIED IR v0.2.
- Skip-cert law (OAR-022) is not undone.
