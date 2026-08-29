# Generated-TypeScript impact note (IR v0.2 planning)

**Status:** Impact note only. The generator still emits **IR v0.1 only**.

## Current binding

- Source schema: `architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json` (`$id` `https://promptrig.dev/schemas/ir/0.1.0`).
- Generator: `src/promptrig/compiler/codegen/typescript.py` via `scripts/generate_typescript_contracts.py`.
- Output: `architecture/typescript/promptrig_ir.ts`.
- Drift gate: `tests/compiler/test_typescript_generation.py` requires byte-identical regeneration.
- Root type: `export interface PromptRigIR { spec_version: "0.1.0"; ... }` with no `continuation` / `reasoning` fields.

Python remains the authoritative compiler. TypeScript consumes generated contracts. Compiler logic is not duplicated in TypeScript (`LANGUAGE_PLATFORM_DECISION.md`).

## What MISSION-031 does not do

- Does not add continuation or reasoning to the freeze schema, so generated types do not gain those fields.
- Does not retarget the generator at a v0.2 schema (there is no production v0.2 schema).
- Does not overwrite `promptrig_ir.ts` with a mixed 0.1/0.2 shape.

## If Q4 later authorizes a production v0.2 schema

A later implementation mission would need a **new** generated artifact (for example `promptrig_ir_v0_2.ts`) or an explicit versioned output path. Silently replacing v0.1 types would break v0.1 consumers. The drift test would bind each generated file to its source schema. This package does not implement that.

## Honesty

Generator remains v0.1 only. Not CERTIFIED IR v0.2. Not a production schema.
