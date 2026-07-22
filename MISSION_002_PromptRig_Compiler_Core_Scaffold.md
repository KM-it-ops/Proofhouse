# MISSION-002 — PromptRig Compiler Core Scaffold

## Repository Target
Repository: `KM-it-ops/PromptRig`
Starting branch: `feature/promptrig-framework`
Required starting point: merge commit tagged `v0.5-architecture-freeze`
Working branch: `feature/compiler-core-scaffold-v0.1`
PR target: `feature/promptrig-framework`

Do not use:
- `integration/promptrig-part1-centralization`
- `feature/compiler-contract-freeze-v0.5` as the implementation base after merge

## Preconditions
Do not begin until:
- PR #2 is merged
- `v0.5-architecture-freeze` exists on the PR #2 merge commit
- OAR-001 exists
- all five decisions are marked Accepted
- CI on the merged freeze passes

## Objective
Create the deterministic Compiler Core v0.1 scaffold without live provider calls, evaluation, repair, hosted execution, or UI orchestration.

## Frozen Decisions
- Python 3.11+ authoritative runtime
- JSON Schema as language-neutral interchange
- generated TypeScript boundary artifacts
- CLI wraps the public Python library
- deterministic fake adapter first
- PromptRig IR public lineage begins at 0.1.0
- accepted RFC 8785-style canonical hashing profile
- immutable central diagnostic registry

## Scope
Create the initial architecture for:
1. Public compiler library API
2. CLI entry point
3. Compiler pass protocol
4. IR loading and strict validation
5. Canonical serialization and SHA-256 hashing
6. Immutable diagnostics
7. Artifact model and caller-controlled sink
8. Capability manifests
9. Deterministic fake adapter
10. Ordered pass traces
11. Stable result envelopes
12. Golden fixtures
13. Library/CLI parity tests
14. Cross-platform installation tests
15. Reproducible TypeScript contract generation
16. CI integration

## Out of Scope
Do not implement:
- OpenAI, Anthropic, or Gemini calls
- network access or credentials
- live execution
- evaluation or repair
- persistence or hosted jobs
- tenant authorization or billing
- UI
- PRS compiler
- MissionRig compiler

## Compiler Passes
Create independently testable boundaries for:
1. Normalization
2. Validation
3. Optimization
4. Capability Resolution
5. Safety
6. Adapter Lowering

Validation must precede lowering. Lowering must not mutate canonical IR.

## Canonicalization
Implement:
- UTF-8
- RFC 8785-compatible canonical JSON behavior
- deterministic number serialization
- duplicate-key rejection before canonicalization
- invalid Unicode/lone-surrogate rejection
- no implicit Unicode normalization
- SHA-256 over canonical bytes

Add adversarial fixtures for key ordering, numbers, escapes, Unicode normalization distinctions, duplicate keys, and invalid surrogates.

## Diagnostics
Load and validate codes through:

`architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json`

Enforce:
- no unregistered stable code
- retired codes cannot be newly emitted
- codes are never reused
- severity/meaning cannot silently change

## Deterministic Fake Adapter
It must:
- require no credentials
- perform no network access
- consume a versioned capability manifest
- produce deterministic artifacts
- emit explicit capability decisions
- support golden fixtures
- expose adapter identity/version
- never silently substitute for a requested live provider

## CLI
Implement or scaffold:
- `promptrig compile`
- `promptrig validate`
- `promptrig inspect`
- `promptrig adapters`
- `promptrig doctor`

Requirements:
- stable exit codes
- JSON output mode
- human-readable mode where appropriate
- no duplicated compiler logic
- library/CLI parity tests

## Generated TypeScript Contracts
Create a reproducible generation path from canonical schemas to TypeScript consumer types with drift checks in CI.

## Quality Gates
At minimum:
- unit tests
- schema validation tests
- canonicalization adversarial tests
- diagnostic registry tests
- fake adapter golden tests
- compiler pass ordering tests
- mutation-protection tests
- library/CLI parity tests
- install tests
- Windows/Linux/macOS CI where feasible
- no-network enforcement
- repeated-run determinism

All prior tests must continue passing. Historical review artifacts remain byte-for-byte unchanged.

## Git Workflow
1. Fetch latest `feature/promptrig-framework`
2. Verify `v0.5-architecture-freeze`
3. Create/reuse `feature/compiler-core-scaffold-v0.1`
4. Commit logically
5. Push normally
6. Open PR titled `Compiler Core Scaffold v0.1`
7. Base: `feature/promptrig-framework`
8. Do not merge

## Final Report
Create `MISSION_002_REPORT.md` with:
- starting freeze SHA
- branch and PR
- package structure
- public API
- pass scaffold
- canonicalization behavior
- diagnostic enforcement
- fake adapter behavior
- CLI commands
- TypeScript generation path
- tests and CI
- deviations
- technical debt
- deferred work
- recommendation for MISSION-003

## Stop Conditions
Stop only for a missing freeze, impossible frozen contract, destructive Git requirement, unacceptable dependency risk, ambiguous repository state, or a contradiction requiring a new ADR.
