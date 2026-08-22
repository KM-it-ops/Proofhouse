# MISSION-019 Design — PRS Envelope Producers (structured)

**Date:** 2026-08-22  
**Baseline:** local `main` @ `15d588a` (OAR-012 Accepted).  
**Authority:** Boss authorized this batch 2026-08-22 (structured `authoring_mode=prs` envelopes via SDD; PR tip sync; never push `main`).  
**Not authorized:** PRS language grammar/parser (RCD-008-009 DEFERRED), authoring-prose producers, OQ-008-001–009 answers, M3 / Simple Mode UI, live providers, Requirements compiler CERTIFIED, full Phase 4B exit, OAR-009 Accepted, OAR-013 Accepted (draft Ready only).

**Numbering note:** Ambition-gap “MISSION-019 benchmark runner” is **not** this mission. This 019 is Campaign COMPILER remaining 008 envelope producers (`prs` mode).

## Goal

Extend `produce_requirements` so **prs** authoring envelopes (structured claims/sources with `kind=prs`) assemble canonical MISSION-008 artifact mappings, then evaluate with the existing `compile_requirements` engine. Same producer stage as MISSION-017/018. Not a PRS language implementation. Not a second rule engine.

## Ponytail constraints (full)

- Reuse existing 008 schemas and `produce_requirements` / `compile_requirements_input`. No new schema file. No new dependency. No new CLI subcommand.
- Extend the one producer module. CLI help names `prs` on existing `compile-requirements`.
- Do not scaffold PRS grammar/parser “for later”.
- Not lazy about: trust-boundary validation, fail-closed security, PromptRig pytest evidence.

## Architecture

```text
JSON payload
  ├─ "requirements_document" present → compile_requirements (MISSION-016, unchanged)
  ├─ intent_input.authoring_mode in {file, api, simple, developer, prs}
  │     → produce_requirements(envelope) → artifacts
  │     → compile_requirements(artifacts)
  └─ else (missing intent_input, malformed)
        → mapping without requirements_document
        → compile_requirements → INVALID_OUTPUT / RQC-SCH-0001
```

## Mode → source kinds

| `authoring_mode` | Allowed source `kind` values |
|------------------|------------------------------|
| `file` | `file`, `decision`, `contract` (unchanged) |
| `api` | `api_request`, `decision`, `contract` (unchanged) |
| `simple` | `ordinary_language`, `decision`, `contract` (unchanged) |
| `developer` | `developer_config`, `decision`, `contract` (unchanged) |
| `prs` | `prs`, `decision`, `contract` |

`imports`: file-only. Presence on `prs` → trust-boundary `{}`.

Keep producer validation digest `promptrig-mission-017-producer`.

## Honesty

- This is **not** promoting PRS to CONTRACT_CANDIDATE. RCD-008-009 / `PRS_DISPOSITION.md` remain DEFERRED for the PRS **language**.
- Requirements compiler stays **PARTIAL**.
- OAR-013 **Ready** (not Accepted). OAR-012/011/010 Accepted. OAR-009 Ready.
- OQs open. No M3. No freeform NLP / authoring-prose interpreter.

## Success criteria

1. `promptrig-compiler compile-requirements` on a prs envelope returns engine-owned terminal status.
2. file/api/simple/developer behavior unchanged.
3. Honesty tests pass; OAR-013 Ready; PARTIAL; OQs open; PRS language still deferred.

## Out of scope

PRS grammar/parser. Push of `main`. Accept OAR-013/OAR-009. M3 UI. OQ answers. Authoring-prose producers.
