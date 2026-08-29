# Compatibility and migration draft (IR v0.1 → possible v0.2)

**Status:** Draft for owner Q4. Not a production migrator. Not a production schema.

Frozen IR v0.1 remains the only executable interchange. `spec_version` is const `"0.1.0"`. `additionalProperties` is false.

## v0.1 inputs retain defined behavior

A document that is valid IR v0.1 today remains valid IR v0.1 after this planning package. No new required fields. No silent ignore of unknown keys (already forbidden). Compilation of a v0.1 document does not migrate.

Fixture: `fixtures/v0_1_valid.json` → `schema_valid`.

## Unknown version fails closed

A reader bound to IR v0.1 rejects any `spec_version` other than `"0.1.0"`. There is no negotiated minor compatibility on the frozen 0.1 schema. Unknown major and unknown minor both fail closed.

Fixture: `fixtures/unknown_version.json` (`spec_version` `9.9.9`) → `fail_closed` at `/spec_version`.

This matches `COMPATIBILITY_PROMISE.md`: readers reject unknown major contract versions; unsupported semantics are never silently ignored.

## Downgrade fails closed

A document that declares a later version (for example `0.2.0`), with or without extra continuation/reasoning keys, is not silently stripped to v0.1. The v0.1 reader fails closed. Automatic IR migration stays opt-in and must emit provenance; compilation never migrates silently (`COMPATIBILITY_PROMISE.md`). This package does not implement a migrator.

Fixture: `fixtures/downgrade_v0_2_shape.json` → `fail_closed`.

## If Q4 later authorizes a production v0.2 schema

Not authorized here. A later mission would still owe:

- version negotiation written down before code;
- opt-in migration with provenance, never a silent compile-time rewrite;
- fail-closed unknown-version and fail-closed downgrade for v0.1-only consumers;
- generated TypeScript as a new v0.2 artifact, not an overwrite of v0.1 types (see `TYPESCRIPT_IMPACT.md`).

## Non-claims

This draft does not change frozen v0.1 bytes, drop `-draft` on the requirements contract, or certify IR v0.2.
