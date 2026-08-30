# PromptRig hosted Simple+Developer slice SPEC (contracts only)

**Status:** Contract package only. **Not a hosted implementation.** Not CERTIFIED. Not M3.
**Mission:** MISSION-034 / campaign U8.
**Owner gate:** **Q2** — Phase 8 transport and UI stack (FastAPI, Next.js, or owner-selected alternatives). Q2 is **unpicked**. Scaffolding is not authorized.
**Intake:** Hosted Simple Mode uses `plain_language_v0`, structured profiles, or the MISSION-030 008 bridge. `simple_mode_ui` / `simple_ui_only` stay forbidden (AE5).

This document is not an implementation authorization. A service or UI tree requires a later mission after Q2.

## What this slice is

One canonical project produced by the headless compiler. Simple Mode and Developer Mode are reversible views of that project. The transport is a generated OpenAPI wrapper around `promptrig-compiler` / the public library. The UI never owns semantics (vision law 6, REJ-007).

## What this slice is not

- **Not a hosted implementation.** No FastAPI package. No Next.js app. No new `apps/` tree.
- Not `apps/dashboard`. Not `apps/promptrig.jsx`. Vite/JSX prototypes are not this slice.
- Not M3 / Simple Mode UI semantics. `simple_mode_ui` remains forbidden on closed-loop.
- Not CERTIFIED hosted product. Not MissionRig. Not billing (DFR-005).
- Not a live default path. `execute-openai` stays opt-in live and is excluded from the default hosted slice.

## Mode-parity

Library, CLI, API, Simple Mode, and Developer Mode must agree on:

- `project_id`
- IR digest (`ir_sha256`)
- evidence bundle identity
- unresolved defects
- compile/eval/repair status

Simple Mode chrome (copy, layout, nontechnical labels) and Developer Mode chrome (IR inspector, traces) are presentation state. They must not introduce hidden configuration. See `MODE_PARITY.md` and `fixtures/`.

## Transport / OpenAPI

`openapi.json` is generated from the headless CLI (`promptrig.compiler.hosted_openapi`). Default hosted operations are the offline compiler commands. `execute-openai` is documented and marked `x-default-hosted-slice: false`. JSON envelopes keep `contract_version`, `command`, `status`, `data`, and `diagnostics`.

Regenerate with `python scripts/generate_hosted_openapi.py`. Drift is a pytest failure, not a ninth CI job.

## Identity, tenancy, persistence

See `AUTH_TENANCY.md` and `PERSISTENCE_RETENTION.md`. First-slice recommendation: single-tenant closed-alpha identity and a portable local store with export and deletion. Multi-tenant SaaS stays DFR-006. Inherited Supabase is REJ-001. Secrets never enter canonical IR, fixtures, logs, or git.

## Accessibility and defects

See `ACCESSIBILITY.md`. Empty projects and PARTIAL compiles must be visible in both modes. Unresolved defects are not rewritten as SUCCESS.

## Q2 options

See `OPTIONS.json`. Current disposition is `STACK-UNPICKED`. A proposed field without a ratified Q2 pick that scaffolds FastAPI/Next.js or extends Vite/JSX is **invalid**.

## Non-claims

- Not a hosted implementation. Q2 unpicked. No production service.
- Frozen `PROMPTRIG_IR_V0_1.schema.json` bytes stay identical.
- Requirements compiler stays PARTIAL. Fake-adapter oracle stays CERTIFIED.
- Skip-cert law (OAR-022) is not undone.
