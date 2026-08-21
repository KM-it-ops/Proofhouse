# MISSION-017 Design — File/API Envelope Producers

**Date:** 2026-08-21  
**Baseline:** local `main` @ `9b69729` (MISSION-016 / OAR-010 Accepted).  
**Authority:** Boss authorized this slice 2026-08-21 (file+api producers, separate `produce_requirements` stage, ponytail-full).  
**Not authorized:** M3 / Simple Mode UI, OQ-008-001–009 answers, simple/developer/prs producers, freeform NLP, live providers, Requirements compiler CERTIFIED, full Phase 4B exit, OAR-009 Accepted.

## Goal

Turn **file** and **api** authoring envelopes into canonical MISSION-008 artifact mappings, then evaluate them with the existing `compile_requirements` engine. This is not a second rule engine and not a full 008 compiler.

## Ponytail constraints (full)

Stop at the first rung that holds:

- Reuse `intent-input.schema.json`, `source-evidence.schema.json`, `requirement.schema.json`, and `compile_requirements`. No new envelope schema file. No new dependency. No new CLI subcommand.
- One new module. One public producer function. CLI dispatch on the existing `compile-requirements` command.
- Do not scaffold simple/developer/prs "for later".
- Not lazy about: trust-boundary validation, fail-closed security, PromptRig pytest evidence.

## Architecture

```text
JSON payload
  ├─ "requirements_document" present → compile_requirements (MISSION-016, unchanged)
  ├─ intent_input.authoring_mode in {file, api}
  │     → produce_requirements(envelope) → artifacts
  │     → compile_requirements(artifacts)
  └─ else (missing intent_input, simple/developer/prs, malformed)
        → mapping without requirements_document
        → compile_requirements → INVALID_OUTPUT / RQC-SCH-0001
```

`evaluate_contract_rules` remains the sole RC-065 implementation. `context_from_artifacts` still reads no authoring prose (only `intent_input.contract_version` plus records). Closed-loop and `EVR-RQC-0001` stay unchanged.

## Components

| Unit | Path | Responsibility |
|------|------|----------------|
| Producer | `src/promptrig/compiler/requirements_produce.py` | Envelope → canonical artifact mapping |
| Compose | `compile_requirements_input` in `src/promptrig/compiler/requirements_contract.py` next to `compile_requirements` | Dispatch canonical vs produce-then-compile |
| Public export | `src/promptrig/compiler/api.py` lazy export | `produce_requirements`, `compile_requirements_input` |
| CLI | `src/promptrig/compiler/cli_compiler.py` | `compile-requirements` calls compose; help text names file/api envelopes |
| Honesty | `architecture/mission-017-certification/README.md` | Scope and non-claims |
| Owner record | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-011.md` | Ready, not Accepted |
| Tests | `tests/compiler/test_mission_017_schedule.py`, `tests/compiler/test_mission_017_produce.py` | Honesty + producer cases |

Do not add `produce-requirements` as a CLI command.

## Envelope

Top-level JSON object. **No new schema file.** Unknown top-level keys are schema violations (`RQC-SCH-0001`), not silently dropped.

| Key | Required | Shape |
|-----|----------|-------|
| `intent_input` | yes | `intent-input.schema.json`; `authoring_mode` must be `file` or `api` |
| `sources` | yes to produce a document | array of `source-evidence.schema.json` |
| `claims` | yes to produce a document | array of `requirement.schema.json` |
| `mappings` | no | if present, copied; if absent, producer emits one `unresolved` non-emitting mapping per claim (TR-004 well-formed fail-closed, not invented IR) |
| `imports` | no; file only | array of strings. Never read from disk. Each import becomes unsupported meaning (`RQC-UNS-0002`) |
| `diagnostics` | no | copied into artifacts if present |

`intent_input.authoring_mode` vs source `kind`:

- `file` → every produced source `kind` must be `file` (or `decision`/`contract` already in the envelope). `api_request` / `ordinary_language` / `developer_config` / `prs` on a file envelope is `RQC-SCH-0001`.
- `api` → every produced source `kind` must be `api_request` (or `decision`/`contract`). Same rejection for mismatched kinds.

The envelope is self-contained. The CLI reads one path (or stdin). No filesystem walk, no HTTP.

## Producer algorithm

`produce_requirements(envelope: Mapping) -> dict`

1. Trust boundary — return `{}` if any of: envelope is not a mapping; extra top-level keys outside `{intent_input, sources, claims, mappings, imports, diagnostics}`; `intent_input` missing; `authoring_mode` not in `{file, api}`; `intent_input` extra keys outside `{contract_version, input_id, authoring_mode, intent, authoritative_inputs, non_authoritative_inputs, source_ids}`; `contract_version` not `0.1.0-draft`; `sources`/`claims` missing or empty; any source `kind` illegal for the mode (`file` allows `file|decision|contract`; `api` allows `api_request|decision|contract`); `imports` present on an `api` envelope. `compile_requirements({})` is `INVALID_OUTPUT` + `RQC-SCH-0001`. Canonical payloads with a bad version still hit existing engine `RQC-VER-0001`.
2. Build `requirements_document`:
   - `contract_version` is `0.1.0-draft` (step 1 already rejected anything else).
   - `document_id` = `RQD-` + `intent_input.input_id` with leading `INP-` stripped.
   - `input_ref` = `intent_input.input_id`.
   - `requirements` = `claims` in ID-sorted order (RC-015).
   - `sources` = envelope sources in ID-sorted order.
   - `assumptions` / `open_questions` / `conflicts` start empty except as synthesized below.
3. Copy claims/sources into the document. Do **not** stuff `artifacts.diagnostics` to force reason codes — `evaluate_contract_rules` derives codes from records; unknown/extra diagnostic codes only trigger `RQC-DIA-0001`. Duplicate IDs, invalid JSON pointers, missing/replaced lifecycle, and `model_suggested`+`accepted` are copied unchanged for the engine.
4. Synthesize only what the engine will not derive from a raw copy:
   - Distinct sources, equivalent statements: **do not coalesce** (OQ-008-004 unanswered).
   - `imports` (file envelopes): never open those paths. For each string, append one required requirement `REQ-IMP-{NNN}` with `acceptance_state=unsupported`, `authority_basis=unsupported`, `source_refs` = first envelope source id. Canonical path has `unsupported_behavior=None`, so the engine yields `BLOCKED` + `RQC-UNS-0001` (not `RQC-UNS-0002`, which is the compact-oracle `recursive_import` signal). Do not text-match. Do not extend `context_from_artifacts`.
   - Digest ambiguity: a `directly_stated` **accepted** claim cites a `kind=file` source that has `fragment` but neither `sha256` nor `fragment_digest`. Do not treat that as ephemeral SUCCESS (engine would). Copy the claim with `acceptance_state=unresolved` and append an open question whose `text` contains `OQ-008-001` (`impact=required`, `resolution_state=unresolved`). Engine: `BLOCKED` + `RQC-AMB-0001`. Do not invent a digest. Do not resolve OQ-008-002–009; if a later producer step would require one of those answers, stop that step and emit an unresolved question naming the OQ instead of choosing.
   - Advisory-on-SUCCESS (OQ-008-006): producer emits no advisory-only diagnostics.
5. Attach `intent_input`. Mappings: if envelope `mappings` present, copy. Else emit one `outcome=unresolved` mapping per claim (`authority_ref.kind=source`, `ref` = that claim’s first `source_refs` entry) plus one `validations` record `VAL-PROD-001` (`validator_version=0.1.0`, `result=PASS`, `content_digest` = SHA-256 UTF-8 of `promptrig-mission-017-producer`). Unresolved mappings are non-emitting; accepted claims without emitting mappings stay fail-closed via the engine (`RQC-BLK-0001`), not invented IR.
6. Return the artifacts dict. Never call `evaluate_contract_rules` from the producer.

`compile_requirements_input(payload)`:

```python
if isinstance(payload, Mapping) and "requirements_document" in payload:
    return compile_requirements(payload)
return compile_requirements(produce_requirements(payload))
```

CLI `compile-requirements` loads JSON and calls `compile_requirements_input`. Byte-stable for existing 016 canonical fixtures.

## Error handling

| Input | Result |
|-------|--------|
| Malformed JSON (CLI) | usage/error path already in CLI; no producer |
| Trust-boundary reject (`{}` from producer) | `compile_requirements` → `INVALID_OUTPUT` + `RQC-SCH-0001` |
| Usable envelope with fail-closed records | Engine owns `SUCCESS` / `PARTIAL` / `BLOCKED` / `REFUSED` / `INVALID_OUTPUT` via RC-065 |
| Canonical 016 payload | Unchanged |
| Canonical 008 payload on `closed-loop` | Still `EVR-RQC-0001` |

Trust boundary is a real boundary: validate `authoring_mode`, schema, unknown fields, version before assembling a document.

## Testing

`test_mission_017_schedule.py`:

- Certification README exists and names: `produce_requirements`, file, api, canonical, PARTIAL, not full 008, not M3 / Simple Mode, no live, freeform, OQ-008-001, OAR-011, Phase 4B.
- `OPEN_QUESTIONS.md` still lists OQ-008-001 through OQ-008-009 as open.
- Maturity map Requirements compiler remains `` `PARTIAL` ``.

`test_mission_017_produce.py` (one file; table-driven):

- Canonical payload with `requirements_document` still equals direct `compile_requirements` (016 regression).
- Minimal valid **file** envelope produces a document whose sources are `kind=file` and whose status comes from `compile_requirements`.
- Minimal valid **api** envelope: sources `kind=api_request`.
- `authoring_mode=simple` / `developer` / `prs` → `INVALID_OUTPUT`.
- Unknown top-level field → `INVALID_OUTPUT` / `RQC-SCH-0001`.
- Envelope unknown `contract_version` → `INVALID_OUTPUT` + `RQC-SCH-0001`. Canonical 016 artifacts still own `RQC-VER-0001`.
- File `imports` → `RQC-UNS-0001`; import path must not be opened (tmp file unread).
- Duplicate source IDs copied through → engine `RQC-SRC-0001`.
- Model self-accept claim copied through → not `SUCCESS`; `RQC-MDL-0001`.
- Digest-ambiguous `directly_stated` file source → `open_questions` text contains `OQ-008-001`, citing claim is `unresolved`, status is not SUCCESS.
- `evaluate_contract_rules` identity: `validate_contract.evaluate_contract_rules is requirements_contract.evaluate_contract_rules` still holds.

Reuse 016 engine tests; do not duplicate RC-065 cases.

## Governance

- Requirements compiler stays **PARTIAL**.
- OAR-011 **Ready** (not Accepted by this mission).
- OAR-009 still Ready; OAR-010 stays Accepted.
- README Status: one MISSION-017 sentence after 016; keep 016/OAR-009 language.
- Deferred registry: file/api envelope producers exist for canonical assembly; still no simple/developer/prs/prose compiler; OQs open.
- Ambition-gap numbering collision: historical P2 “MISSION-017 platform SPECs” is **not** this mission. This 017 is Campaign COMPILER remaining 008 producers. Do not implement platform auth/tenancy.

## Non-claims

Not a full MISSION-008 production compiler. Not authoring-prose / Simple / Developer / PRS producers. Not M3 / Simple Mode UI. Not freeform NLP. Not live model-assisted suggestion or live providers. Not CERTIFIED requirements compiler. Not full Roadmap Phase 4B exit. Not IR v0.2. Does not answer OQ-008-001–009. Does not Accept OAR-009. Does not unblock M3.

## Adversarial audit (2026-08-21)

Audited against `evaluate_contract_rules` / `context_from_artifacts` / `authority_backed` at `9b69729` and the 008 schemas. Findings folded into the algorithm above (not a second status matrix):

| Finding | Severity | Resolution |
|---------|----------|------------|
| Stuffing `artifacts.diagnostics` does not set terminal status (engine only uses those codes for `RQC-DIA-0001`) | Critical | Copy records; engine owns codes |
| Canonical `unsupported_behavior` is always `None`; `RQC-UNS-0002` never fires from artifacts | Critical | Imports become `unsupported` requirements → `RQC-UNS-0001` |
| `open_questions` are not in RC-065; adding OQ text alone can still SUCCESS | Critical | Digest ambiguity also sets the claim `unresolved` |
| Engine already treats no-digest sources as ephemeral SUCCESS for `directly_stated` | Important | Producer fail-closes that file+fragment case instead of inheriting ephemeral SUCCESS |
| Synthesized mappings require `validation_ref` / `VAL-*` | Important | Emit `VAL-PROD-001` |

No remaining Critical gaps vs the 016 engine. Spec is implementable.

## Success criteria

1. `promptrig-compiler compile-requirements` on a file envelope and on an api envelope returns engine-owned terminal status (library/CLI JSON parity).
2. Existing 016 canonical fixtures remain byte-stable in behavior.
3. Honesty tests pass; compiler maturity still PARTIAL; OQs still listed open.
4. OAR-011 drafted Ready.

## Out of scope

Ponytail Cursor rule install into this repo (Boss may add `.cursor/rules/ponytail.mdc` separately). Push/PR. Work on `main` checkout during SDD (isolated worktree).
