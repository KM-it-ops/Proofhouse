# MISSION-020 Design — Authoring-Prose Producers (plain_language_v0 → 008)

**Date:** 2026-08-22  
**Baseline:** local `main` @ `af40a53` (OAR-013 Accepted; OQ-008-001–010 owner-resolved as policy only).  
**Authority:** Boss authorized this batch 2026-08-22 (parse-and-lower on existing `plain_language_v0`; SDD; never push `main`).  
**Not authorized:** freeform NLP, new prose grammar, sixth `authoring_mode` envelope, OQ-008-* engine implementation, `RCD-008-*` rewrites, D-050 appends, M3 / Simple Mode UI, live providers, PRS language/grammar, Requirements compiler CERTIFIED, full Phase 4B exit, OAR-009 Accepted, OAR-014 Accepted (draft Ready only).

**Numbering note:** No historical ambition-gap “MISSION-020” collides. This 020 is Campaign COMPILER remaining 008 authoring-prose producers (constrained interpreter, not another envelope).

## Goal

Give `compile-requirements` a third dispatch so a **constrained** `plain_language_v0` text envelope (`{profile, text}` only) is parsed by the existing MISSION-013 parser, lowered into canonical MISSION-008 artifacts, and evaluated by the existing `compile_requirements` engine. Closed-loop keeps its own `{profile, text, …}` path. Envelope producers (file/api/simple/developer/prs) stay unchanged. Not freeform NLP. Not a second rule engine.

## Ponytail constraints (full)

- Reuse `parse_plain_language_v0`, 008 schemas, and `compile_requirements`. No new schema file. No new dependency. No new CLI subcommand. No new grammar.
- One new producer module. Dispatch on existing `compile-requirements` / `compile_requirements_input`.
- Do not scaffold a sixth `authoring_mode` or a generic `structured_minimal_v0` → 008 lower “for later”.
- Not lazy about: exact-key trust boundary, fail-closed parse, no invented IR leaves, PromptRig pytest evidence.

## Architecture

```text
JSON payload
  ├─ "requirements_document" present
  │     → compile_requirements (MISSION-016, unchanged)
  ├─ keys exactly {profile, text}
  │   and profile == "plain_language_v0"
  │   and text is str
  │     → parse_plain_language_v0(text)
  │           ├─ PlainLanguageParseError → BLOCKED + PL-PARSE-*
  │           └─ structured_minimal_v0 parse tree
  │                 → produce_plain_language_requirements(text)
  │                 → compile_requirements(artifacts)
  ├─ intent_input.authoring_mode in {file, api, simple, developer, prs}
  │     → produce_requirements(envelope) → artifacts
  │     → compile_requirements(artifacts)
  └─ else (extra keys, missing text, malformed)
        → mapping without requirements_document
        → compile_requirements → INVALID_OUTPUT / RQC-SCH-0001
```

`evaluate_contract_rules` remains the sole RC-065 implementation. `context_from_artifacts` still reads no authoring prose (only `intent_input.contract_version` plus records). Closed-loop CLI and `EVR-RQC-0001` stay unchanged.

A closed-loop envelope that includes `repair_budget` / `network_allowed` / extra keys is **not** a compile-requirements prose payload. Exact-key match only. Those envelopes stay on `closed-loop`.

## Components

| Unit | Path | Responsibility |
|------|------|----------------|
| Parser | `src/promptrig/compiler/plain_language.py` | Unchanged `plain_language_v0` grammar |
| Lowerer | `src/promptrig/compiler/requirements_plain_produce.py` | Text → canonical artifact mapping |
| Compose | `compile_requirements_input` in `requirements_contract.py` | Canonical vs prose vs envelope |
| Envelope producer | `requirements_produce.py` | Unchanged file/api/simple/developer/prs |
| Public export | `src/promptrig/compiler/api.py` | `produce_plain_language_requirements` |
| CLI | `cli_compiler.py` | Help names `plain_language_v0` text envelope |
| Honesty | `architecture/mission-020-certification/README.md` | Scope and non-claims |
| Owner record | `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-014.md` | Ready, not Accepted |
| Tests | `tests/compiler/test_mission_020_schedule.py`, `test_mission_020_produce.py` | Honesty + producer cases |

Do not add `produce-requirements` or `produce-plain-language` as a CLI command.

## Payload

Top-level JSON object. **No new schema file.**

| Key | Required | Rule |
|-----|----------|------|
| `profile` | yes | exactly `plain_language_v0` |
| `text` | yes | `str` (may be empty; parser fail-closes) |

Any other key, missing key, non-string `text`, or other profile → not this dispatcher.

## Lowering (mechanical)

Parse with `parse_plain_language_v0`. Do not invent statements. Each `directly_stated` requirement is byte-backed: `statement` == source `fragment`, `statement_digest` == `fragment_digest` (SHA-256 over UTF-8).

Synthesize `intent_input.authoring_mode` as `simple` (schema enum; ordinary-language surface). This is **not** the MISSION-018 structured simple envelope path.

`input_id` = `INP-PL-` + first 12 hex chars of SHA-256(text), uppercased. `document_id` = `RQD-PL-` + same suffix.

| Grammar | Requirement | Source kind | Mapping |
|---|---|---|---|
| `Goal:` | `REQ-PL-GOAL`, type `objective`, accepted, `directly_stated` | `ordinary_language` `SRC-PL-GOAL` | `direct` → `/objective/goal` |
| numbered `1.` / `2.` | existing `REQ-PL-*`, type `behavior`, accepted, `directly_stated` | `SRC-PL-*` | `outcome=unresolved` (no `target_pointer`) |
| `Constraints:` lines | `REQ-PL-C001`…, type `constraint`, accepted, `directly_stated` | `SRC-PL-C001`… | `outcome=unresolved` |

Validation record `VAL-PL-001` with digest `sha256(b"promptrig-mission-020-plain-producer")`. Keep envelope digest `promptrig-mission-017-producer` unchanged.

Happy path (Goal + at least one numbered requirement) is therefore **BLOCKED** (`RQC-BLK-0001`): accepted required meaning without an emitting IR mapping. That is honest. Do not map numbered/constraint statements onto `/objective/goal` or any other guessed leaf. Do not claim SUCCESS for prose-only input.

Parse failure: `compile_requirements_input` returns `RequirementsCompileResult(status="BLOCKED", reason_codes=(PL-PARSE-*,))` without calling `compile_requirements`. Do not stuff `PL-PARSE-*` into artifact `diagnostics` (those codes are not in the 008 registry).

## CLI

`compile-requirements` help for the command and positional `input` must name canonical JSON, file/api/simple/developer/prs envelopes, **and** `plain_language_v0` text envelopes (constrained; not freeform; not closed-loop).

## Testing

- New `tests/compiler/test_mission_020_schedule.py` and `test_mission_020_produce.py`.
- Minimal fixture `tests/compiler/fixtures/plain_language_minimal.txt` → Goal mapping `direct`; numbered + constraint mappings `unresolved`; status `BLOCKED` not `INVALID_OUTPUT`; `RQC-BLK-0001` present.
- Freeform text → `BLOCKED` + `PL-PARSE-0001`.
- Extra keys (`repair_budget`) → `INVALID_OUTPUT` / `RQC-SCH-0001`.
- file/api/simple/developer/prs envelopes still produce as in 017–019.
- `tests/compiler/test_plain_language_closed_loop.py` still PASS.
- 016–019 honesty/produce regressions still pass.
- Update 017/019 exact CLI help assertions when help text changes.

## Honesty

- This is **constrained** `plain_language_v0`, not freeform NLP, not a new grammar, not M3 UI.
- Requirements compiler stays **PARTIAL**. Not a full MISSION-008 production compiler (OQ policies still unimplemented; PRS language still DEFERRED; no SUCCESS from prose-only input).
- OAR-014 **Ready** (not Accepted). OAR-013/012/011/010 Accepted. OAR-009 Ready.
- OQ-008-001–010 remain owner-resolved **policy only**. Do not implement them in the engine or this lowerer (file-fragment fail-closed in `produce_requirements` stays).
- Compact `cases.json` remains test-only. Do not interpret compact `input.intent` strings.

## Success criteria

1. `promptrig-compiler compile-requirements` on `{profile: plain_language_v0, text: <valid grammar>}` returns engine-owned `BLOCKED` (not `INVALID_OUTPUT`, not guessed `SUCCESS`).
2. Freeform text fail-closes at `PL-PARSE-*`.
3. Envelope modes and closed-loop unchanged.
4. Honesty tests pass; OAR-014 Ready; PARTIAL; OQs unimplemented; PRS language still deferred.

## Out of scope

Freeform NLP. New grammar. Sixth envelope mode. OQ engine implementation. Push of `main`. Accept OAR-014/OAR-009. M3 UI. PRS language/parser. Generic structured-doc → 008 lower.
