# MISSION-018 Design — Simple/Developer Envelope Producers

**Date:** 2026-08-21  
**Baseline:** local `main` @ `afcf9f8` (OAR-011 Accepted).  
**Authority:** Boss authorized this slice 2026-08-22 (simple+developer producers after OAR-011 Accept; SDD; P2 feature-branch PR only; never push `main`).  
**Not authorized:** M3 / Simple Mode UI, OQ-008-001–009 answers, `prs`/authoring-prose producers, freeform NLP, live providers, Requirements compiler CERTIFIED, full Phase 4B exit, OAR-009 Accepted, OAR-012 Accepted (draft Ready only).

**Numbering note:** Historical ambition-gap P3 “MISSION-018 vertical slice (transport + UI)” is **not** this mission. This 018 is Campaign COMPILER remaining 008 envelope producers (simple+developer).

## Goal

Extend `produce_requirements` so **simple** and **developer** authoring envelopes assemble canonical MISSION-008 artifact mappings, then evaluate with the existing `compile_requirements` engine. Same producer stage as MISSION-017; not a second rule engine; not a full 008 compiler.

## Ponytail constraints (full)

- Reuse existing 008 schemas and `produce_requirements` / `compile_requirements_input`. No new schema file. No new dependency. No new CLI subcommand.
- Extend the one producer module. CLI help names the new modes on existing `compile-requirements`.
- Do not scaffold `prs` “for later”.
- Not lazy about: trust-boundary validation, fail-closed security, PromptRig pytest evidence.

## Architecture

```text
JSON payload
  ├─ "requirements_document" present → compile_requirements (MISSION-016, unchanged)
  ├─ intent_input.authoring_mode in {file, api, simple, developer}
  │     → produce_requirements(envelope) → artifacts
  │     → compile_requirements(artifacts)
  └─ else (missing intent_input, prs, malformed)
        → mapping without requirements_document
        → compile_requirements → INVALID_OUTPUT / RQC-SCH-0001
```

`evaluate_contract_rules` remains the sole RC-065 implementation. Closed-loop and `EVR-RQC-0001` stay unchanged.

## Mode → source kinds

| `authoring_mode` | Allowed source `kind` values |
|------------------|------------------------------|
| `file` | `file`, `decision`, `contract` (unchanged) |
| `api` | `api_request`, `decision`, `contract` (unchanged) |
| `simple` | `ordinary_language`, `decision`, `contract` |
| `developer` | `developer_config`, `decision`, `contract` |

`imports`: file-only (unchanged). Presence on simple/developer/api → trust-boundary `{}`.

Digest-ambiguity fail-closed (OQ-008-001 text + claim `unresolved`) remains **file-source** only, as in 017.

## Producer changes

In `requirements_produce.py`:

1. Allow `authoring_mode in {"file", "api", "simple", "developer"}`.
2. Select `allowed_kinds` from the table above.
3. Keep all other trust-boundary and assembly rules from MISSION-017.
4. Optionally bump producer validation digest string to a MISSION-018 marker **only if** tests require identity; prefer keeping `promptrig-mission-017-producer` digest unless a task brief says otherwise (avoid churn). Default: **keep** existing digest.

`compile_requirements_input` unchanged.

## CLI

`compile-requirements` help for the command and positional `input` must name file/api/**simple**/**developer** envelopes (not prose; not closed-loop).

## Testing

- New `tests/compiler/test_mission_018_schedule.py` and `tests/compiler/test_mission_018_produce.py`.
- Update `tests/compiler/test_mission_017_produce.py`: `prs` remains `INVALID_OUTPUT`; **remove** simple/developer from that rejection test (they become 018 positive cases).
- Minimal valid simple envelope → sources `ordinary_language`; compose returns engine-owned status.
- Minimal valid developer envelope → sources `developer_config`.
- Wrong kind for mode → `INVALID_OUTPUT` / `RQC-SCH-0001`.
- `prs` → `INVALID_OUTPUT`.
- 016/017 regressions still pass.

## Governance

- Requirements compiler stays **PARTIAL**.
- OAR-012 **Ready** (not Accepted by this mission).
- OAR-011 stays Accepted; OAR-010 Accepted; OAR-009 Ready.
- Deferred: still no `prs`/prose; OQs open; no full 008; no M3.

## Success criteria

1. `promptrig-compiler compile-requirements` on simple and developer envelopes returns engine-owned terminal status.
2. File/api behavior unchanged; 017 suite green after rejection-test update.
3. Honesty tests pass; OAR-012 Ready; PARTIAL; OQs open.

## Out of scope

Push of `main`. Accept OAR-012. Ambition-map UI vertical slice. `prs` producers. M3 UI. Live providers. OQ answers.
