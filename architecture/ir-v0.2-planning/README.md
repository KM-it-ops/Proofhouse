# IR v0.2 planning package (MISSION-031)

**Status:** Planning only. Not a production schema. Not CERTIFIED IR v0.2.
**Owner gate:** Q4 — continuation and reasoning field shapes. The owner picks later.
**Live campaign constraint:** single-request. Do not implement U6 here.

This directory is the Phase 5 planning package. Frozen IR v0.1 (`architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json`) is unchanged.

## Documents

| File | Role |
|---|---|
| [SPEC.md](SPEC.md) | SPEC + semantic delta (continuation vs reasoning) |
| [OPTIONS.json](OPTIONS.json) | Machine-readable Q4 options; each has a provider-neutral owner or is explicitly rejected |
| [COMPATIBILITY_MIGRATION.md](COMPATIBILITY_MIGRATION.md) | v0.1 retain defined behavior; unknown-version / downgrade fail-closed |
| [THREAT_MODEL.md](THREAT_MODEL.md) | Opaque provider-returned state |
| [TYPESCRIPT_IMPACT.md](TYPESCRIPT_IMPACT.md) | Generator remains v0.1 only |
| [fixtures/](fixtures/) | v0.1 valid + fail-closed unknown/downgrade cases |

## U6 recommendation

**Evidence-only continuation** for the U6 live path: store provider-returned continuation in artifact/evidence, not as an IR field. Reasoning stays unsupported in IR v0.1 (ADR-006 gap).

## Honesty

- Requirements compiler stays PARTIAL.
- Not M3. Not a live implementation. Not CERTIFIED IR v0.2.
- Skip-cert law (OAR-022) is not undone.
- A proposed field without a provider-neutral owner is invalid.
