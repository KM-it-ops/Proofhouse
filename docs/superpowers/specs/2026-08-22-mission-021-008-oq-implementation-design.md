# MISSION-021 Design — OQ-008-001 / 002 / 006 Engine Implementation

**Date:** 2026-08-22  
**Baseline:** local `main` @ `ca888a8` (OAR-009 Accepted; OAR-014 Accepted; OQ-008-001–010 owner-resolved as policy only).  
**Authority:** Boss authorized this batch 2026-08-22 (implement named OQ-008-001, OQ-008-002, and OQ-008-006 in the existing engine/producers; SDD; never push `origin/main`).  
**Not authorized:** OQ-008-003, OQ-008-004, OQ-008-005, OQ-008-007, OQ-008-008, OQ-008-009, OQ-008-010 engine/schema rewrites, `RCD-008-*` rewrites, D-050 appends, freeform NLP, M3 / Simple Mode UI, live providers, PRS language/grammar, Requirements compiler CERTIFIED, full Phase 4B exit, inventing IR leaves for MISSION-020 numbered/constraint records.

**Numbering note:** This 021 is Campaign COMPILER remaining 008 policy implementation for three named OQs. Not a full 008 compiler.

## Goal

Implement three already-resolved owner policies in the **existing** sole rule engine (`evaluate_contract_rules`) and the file-envelope producer, without a second engine, without claiming CERTIFIED, and without making valid constrained prose SUCCESS.

## Honesty (read first)

OQ-008-002 does **not** unblock MISSION-020 valid grammar. Numbered and constraint records are `priority=required` with `outcome=unresolved`. Required unmapped accepted meaning stays `BLOCKED` / `RQC-BLK-0001`. Optional unmapped/no-IR meaning becomes `PARTIAL` with evidence.

## Policies to implement

### OQ-008-001 — digest when stable bytes exist

- File sources (`kind=file`) with neither `sha256` nor `fragment_digest`: keep fail-closed. Demote accepted `directly_stated` claims to `unresolved`, emit an `OQN-*` with `impact=required` whose text contains `OQ-008-001` and does **not** say `unanswered`. Compile remains `BLOCKED` / `RQC-AMB-0001`.
- Fragment present without `fragment_digest`: keep producer `{}` → `INVALID_OUTPUT` / `RQC-SCH-0001`.
- Non-file kinds (api, ordinary_language, developer_config, prs, decision, contract): do not invent a digest; skip the file-digest gate.
- Never hash missing bytes.

### OQ-008-002 — optional unresolved meaning is PARTIAL with evidence

In `evaluate_contract_rules` only:

- Class 5 security/privacy fail-closed is unchanged (unmapped security/privacy stays BLOCKED/REFUSED even if `priority=optional`).
- Class 6f `no_ir_representation`: if **every** such mapping belongs to a requirement with `priority=optional`, do not return BLOCKED here; Class 7 returns `PARTIAL` with `RQC-IRG-0001` (and `RQC-AMB-0001` if optional unresolved acceptance also applies). If any `no_ir_representation` mapping belongs to a non-optional requirement, keep `BLOCKED` / `RQC-BLK-0001`+`RQC-IRG-0001`.
- Class 6j accepted without emitting mapping: if **every** such requirement has `priority=optional`, do not return BLOCKED here; Class 7 returns `PARTIAL` / `RQC-AMB-0001`. If any is not optional, keep `BLOCKED` / `RQC-BLK-0001`.
- Required unresolved acceptance (6i) stays BLOCKED.
- Existing optional `acceptance_state=unresolved` PARTIAL path stays.

### OQ-008-006 — advisory + SUCCESS only when non-semantic

- Registry records may include boolean `semantic`. **Missing `semantic` means `true`** (fail-closed).
- `RQC-SRC-0005` stays advisory and semantic (default). Replaced source still Class 7 `PARTIAL`.
- Add `RQC-ADV-0001`: `severity=warning`, `class=advisory`, `semantic=false`, `message_key=requirements.advisory_nonsemantic`.
- Duplicate the registry in `src/promptrig/compiler/schemas/requirements_diagnostic_registry.json` (drift test).
- Class 8: if all requirements are `accepted` and earlier classes did not return, `SUCCESS` with reason codes = sorted unique **emitted** diagnostic codes whose registry entry has `class=advisory` and `semantic is False`. Otherwise `SUCCESS` with `[]` as today.
- `validate_contract.py`: `SUCCESS` plus any diagnostic `severity==error` remains `success_with_error_evidence`. `SUCCESS` plus `declared_reasons` is allowed only when every declared reason is advisory and `semantic is False`. Do not allow arbitrary reason codes on SUCCESS.

## Non-claims

- Not full MISSION-008 production compiler.
- Not CERTIFIED. Maturity stays `PARTIAL`.
- Not full Phase 4B exit. Not M3. Not live. Not freeform NLP. Not PRS language.
- OAR-015 Ready, not Accepted, until Boss says so.

## Components

| Unit | Path | Responsibility |
|------|------|----------------|
| Engine | `src/promptrig/compiler/requirements_contract.py` | 6f/6j optional PARTIAL; Class 8 advisory non-semantic codes |
| Producer | `src/promptrig/compiler/requirements_produce.py` | OQ-008-001 implemented wording |
| Registry | `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json` and vendored copy | `semantic` + `RQC-ADV-0001` |
| Harness | `architecture/requirements-compiler-contract-v0.1/validate_contract.py` | SUCCESS + advisory non-semantic reasons |
| Honesty | `architecture/mission-021-certification/README.md` | Scope and non-claims |
| Owner record | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-015.md` | Ready, not Accepted |
| Tests | `tests/compiler/test_mission_021_schedule.py`, `test_mission_021_oq.py` | Honesty + 001/002/006 |
