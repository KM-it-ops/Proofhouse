# MISSION-022 Design — Remaining OQ-008-003/004/005/007/008/009/010

**Date:** 2026-08-23
**Baseline:** local `main` @ `6331287` (OAR-015 Accepted; OQ-008-001/002/006 implemented).
**Authority:** Boss authorized this campaign 2026-08-23 (remaining OQs 003–005 and 007–010; write design spec + SDD plan; never push `origin/main`).
**Not authorized:** M3 / Simple Mode UI, live providers, freeform NLP, PRS language/grammar, IR v0.2 fields, Phase 6 runtime permissions, CERTIFIED requirements compiler, full Phase 4B exit, alias-group implementation study as a product feature, dropping `-draft`, accepting production 0.1.

**Numbering note:** This 022 is Campaign COMPILER remaining 008 policy implementation for the OQs MISSION-021 left unimplemented. Not a full 008 compiler. Not Phase 4B exit.

## Goal

Implement the *executable* remainder of owner-resolved OQ-008 policy in the existing sole `evaluate_contract_rules` engine and producers, and lock the *deferred* remainder so later campaigns cannot silently invent identity-merge, PRS language, continuation IR, or reasoning IR.

## Do not authorize M3 in this campaign

M3 / Simple Mode is DFR-002 (broad UI) and Roadmap **Phase 8**. Entry requires a CERTIFIED headless requirements compiler and a shared canonical project model. Remaining OQs do not produce CERTIFIED, do not exit Phase 4B, and do not unblock M3. Mixing M3 here would smuggle a product UI into a compiler-policy campaign.

## Honesty (read first)

Completing these OQs still leaves:

- Requirements compiler maturity **PARTIAL**.
- Valid constrained `plain_language_v0` numbered/constraint records **BLOCKED** (`RQC-BLK-0001`).
- PRS **language** DEFERRED.
- Full MISSION-008 production compiler unclaimed.
- Phase 4B unexited.
- M3 unauthorized.

Several resolutions are *do not build yet*. Those are lock-in tests and honesty, not feature work.

## What each remaining OQ does in this campaign

| OQ | Owner resolution | This campaign |
|---|---|---|
| 003 | Policy-defined consequential authority; undeterminable stays BLOCKED; live model is Phase 6 | **Implement fail-closed policy lookup.** No frozen owner-only category list. No credentials, no runtime ACL. |
| 004 | Deterministic alias group; identities not merged; implementation later | **Lock-in only.** Multi-source equivalents keep separate IDs. Do not merge. Do not ship alias groups. |
| 005 | Strict exact version for a future accepted 0.1; unknown → `RQC-VER-0001`; do not drop `-draft` | **Implement/name exact-match gate.** Keep `0.1.0-draft`. Reject ranges, other versions, missing version. |
| 007 | PRS remains deferred | **Lock-in only.** Structured `authoring_mode=prs` envelopes stay envelopes. No grammar/parser/CONTRACT_CANDIDATE. |
| 008 | Defer opaque continuation-state shape | **Lock-in only.** No canonical IR field. Compact `unsupported` fixtures stay valid. ADR-007 stays Proposed. |
| 009 | Reasoning controls remain unsupported in IR v0.1 | **Lock-in only.** No IR `reasoning` block. ADR-006 stays gap-only. |
| 010 | Structured-only assumption/open-question records | **Implement production fail-closed.** Schema already structured-only; producers/engine must reject bare strings. 41-case compact corpus remains test-only projection. |

## Approaches considered

1. **One MISSION-022 with implement + lock split (chosen).** Highest coupling to the engine just landed. One OAR. Clear non-claims. Matches 016–021 campaign shape.
2. **Two missions (executable OQs vs lock-in).** Cleaner theoretically; doubles ceremony for tests that must land together anyway.
3. **Honesty-only docs claiming remaining OQs done.** Dishonest where 003/005/010 are not named production gates.

## Policies to implement

### OQ-008-003 — policy-defined authority, fail-closed

In `evaluate_contract_rules` / existing approval chain only:

- Required authority for a consequential subject comes from an **accepted** approval-threshold policy referenced by the approval chain (`policy_ref` → accepted policy → `required_authority`).
- If the required authority cannot be uniquely determined (missing policy, unaccepted policy, conflicting `required_authority` values, unknown token): **BLOCKED** with evidence. Never assume `owner` or `user`.
- Do **not** add a frozen list of owner-only consequential categories.
- Do **not** implement Phase 6 live permissions, sessions, or credentials.
- Existing owner/user conflict (`RQC-AUT-0001`) and missing approval (`RQC-APR-0001`) stay.

### OQ-008-005 — strict exact version

- Canonical compile/evaluate path accepts only `REQUIREMENTS_CONTRACT_VERSION` (`0.1.0-draft`) as exact string match.
- Any other value (including `0.1.0`, `0.1.0-draft.1`, `>=0.1.0`, empty, missing when a version is required) is unsupported (`RQC-VER-0001` / existing Class 0 `INVALID_OUTPUT`).
- Do not strip `-draft`. Do not accept a production 0.1 contract. Do not implement range matching or migration adapters.

### OQ-008-010 — structured-only canonical records

- Canonical `assumptions` / `open_questions` items must be structured records matching `requirements-document.schema.json`. Bare strings are not canonical.
- Producers must not emit string items.
- Engine/input compile path: a string item is `INVALID_OUTPUT` with a named diagnostic (reuse schema/invalid-output codes; add a dedicated code only if honesty tests cannot bind to an existing one).
- The 41-case semantic-oracle corpus remains a **test-only projection**, not proof of canonical record shape.

## Lock-in (must not grow features)

### OQ-008-004

Two semantically equivalent requirements from distinct sources remain two records with two identities. No merge. No alias-group object in canonical output.

### OQ-008-007

`PRS_DISPOSITION.md` stays DEFERRED. No parser module, grammar artifact, or CONTRACT_CANDIDATE promotion. MISSION-019 structured PRS envelopes unchanged.

### OQ-008-008 / OQ-008-009

Frozen IR v0.1 schema gains no continuation-state field and no reasoning-controls field. Fixtures that mark those meanings `unsupported` remain valid.

## Non-claims

- Not full MISSION-008 production compiler.
- Not CERTIFIED. Maturity stays `PARTIAL`.
- Not full Phase 4B exit. Not M3. Not live. Not freeform NLP. Not PRS language.
- Not IR v0.2. Not alias-group implementation study.
- OAR-016 Ready, not Accepted, until Boss says so.

## Components

| Unit | Path | Responsibility |
|------|------|----------------|
| Engine | `src/promptrig/compiler/requirements_contract.py` | 003 fail-closed policy authority; 005 exact version; 010 reject string records |
| Producers | `src/promptrig/compiler/requirements_produce.py` and sibling produce modules as needed | 010 emit structured records only |
| Registry | `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json` and vendored twin | New code only if required for 010 |
| Honesty | `architecture/mission-022-certification/README.md` | Scope and non-claims |
| Owner record | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md` | Ready, not Accepted |
| Orientation | `architecture/strategy/PROJECT_ORIENTATION.md` | Durable you-are-here map (this session) |
| Tests | `tests/compiler/test_mission_022_schedule.py`, `test_mission_022_oq.py` | Honesty + implement + lock-in |
| Policy docs | `OPEN_QUESTIONS.md`, `CAPABILITY_MATURITY_MAP.md`, `DEFERRED_AND_REJECTED_WORK.md` | Name 022 scope; remaining non-claims |

## Success criteria

- Schedule/honesty tests name 003/005/010 implemented and 004/007/008/009 locked-not-built.
- Focused pytest for 022 passes; existing 021 honesty still holds (001/002/006 remain implemented; constrained prose still BLOCKED).
- Maturity row stays `PARTIAL`.
- No M3/Simple Mode files, no live provider, no IR schema additive fields for 008/009.

## Out of scope

M3, CERTIFIED/Phase 4B exit, PRS language, alias-group study, IR v0.2, live model-assisted suggestion, rewriting `RCD-008-*`, appending D-050.
