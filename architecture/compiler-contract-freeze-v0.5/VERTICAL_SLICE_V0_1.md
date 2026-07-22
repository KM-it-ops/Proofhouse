# Vertical slice v0.1

## Goal

Prove the contract end to end without network access: load one valid IR document, compile it through all six passes using the deterministic fake adapter, emit one provider-neutral prompt artifact and manifest, and inspect the result through both library and CLI.

## Included

- Strict schema and semantic validation.
- Immutable diagnostics and source paths.
- No-op traced optimization.
- Required/optional capability resolution.
- Safety gate for tool approval and sensitive-data policy.
- Deterministic fake-adapter lowering.
- Artifact and pass digests.
- `compile`, `validate`, `inspect`, `adapters`, and `doctor` parity tests.
- Windows, Linux, and macOS installation smoke tests.

## Excluded

Live provider calls, evaluation, repair, hosted persistence/jobs, UI, authentication, billing, benchmark runner, PRS parsing, and changes to the v0.4 historical corpus.

## Acceptance

Two identical runs produce identical semantic JSON and artifact digests; invalid IR never reaches lowering; a missing required capability fails with a stable diagnostic; optional capability omission warns; library and CLI results match after removal of explicitly volatile fields.
