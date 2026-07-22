# ADR-005 — Compiler Core CLI entry point disambiguation

**Status:** Accepted
**Date:** 2026-07-22
**Owner ratification:** Confirmed by the Project Owner during MISSION-002 review, prior to any merge decision.

## Context

`architecture/compiler-contract-freeze-v0.5/LIBRARY_CLI_CONTRACT.md` is a frozen, normative contract requiring Compiler Core v0.1 to expose `promptrig compile`, `promptrig validate`, `promptrig inspect`, `promptrig adapters`, and `promptrig doctor` under the `promptrig` command name.

The existing legacy PromptOps CLI already implements `promptrig validate --dataset X` under the same binary name, with different semantics. `LIBRARY_CLI_CONTRACT.md` itself states that legacy `report`, `loadouts`, `compile-loadout`, and `generate` commands remain supported and must not be reimplemented inside Compiler Core — but it did not anticipate a direct name collision on `validate` between the legacy surface and the new one.

MISSION-002 discovered this collision during implementation. Reimplementing or shadowing `promptrig validate` would either break legacy behavior or silently reinterpret Compiler Core's contractually-required command semantics — both prohibited by Architect Mode law (adapters/CLI never silently discard or reinterpret meaning; existing behavior is not overwritten for implementation convenience).

## Decision

Compiler Core v0.1 ships as its own binary, `promptrig-compiler`, exposing `compile`, `validate`, `inspect`, `adapters`, and `doctor` exactly as specified in `LIBRARY_CLI_CONTRACT.md`, under this separate entry point rather than under the shared `promptrig` binary.

The legacy `promptrig` binary and all of its existing commands, including `validate --dataset X`, remain completely untouched by Compiler Core.

This ADR formally amends the entry-point naming assumption in `LIBRARY_CLI_CONTRACT.md` (which uses `promptrig <command>` in its illustrative command list) to `promptrig-compiler <command>`. All other requirements in that contract — JSON envelope shape, exit codes, parity rules, installation testing — apply unchanged to the `promptrig-compiler` binary.

## Alternatives considered

- **Deprecate or rename the legacy `validate` command.** Rejected: legacy CLI modification is explicitly out of MISSION-002 scope and was not authorized by any accepted decision; doing so here would be unreviewed scope expansion into a system this mission was never authorized to change.
- **Shadow/override `promptrig validate` conditionally based on input shape.** Rejected: implicit dispatch based on argument shape is exactly the kind of silent reinterpretation of meaning the compiler invariants prohibit, and it would make CLI behavior non-obvious and untestable as a stable contract.
- **Block MISSION-002 entirely pending a full CLI namespace redesign.** Rejected as disproportionate: the underlying compiler, schemas, and passes are unaffected by this naming question, and a full redesign is unnecessary to resolve a single command-name collision.

## Consequences

- `LIBRARY_CLI_CONTRACT.md` is amended, not violated: the contract's semantic requirements (envelope, exit codes, parity, offline behavior) hold; only the illustrative binary name changes.
- Any future consumer, packaging, or documentation work must refer to `promptrig-compiler`, not `promptrig`, for Compiler Core commands.
- If a future decision unifies the legacy and Compiler Core CLIs into one binary, that unification requires its own ADR and is out of scope for this one.
- No code in PR #4 (`Compiler Core Scaffold v0.1`) needs to change as a result of this ADR; the existing `promptrig-compiler` binary already conforms to this decision.

## Evidence

- `architecture/compiler-contract-freeze-v0.5/LIBRARY_CLI_CONTRACT.md`
- MISSION-002 implementation report (`MISSION_002_REPORT.md`), Deviations section, item 1
- PromptRig PR #4 — Compiler Core Scaffold v0.1
