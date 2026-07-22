# MISSION-006 Report — Compiler Contract Recovery and Re-Certification v0.1

## Status

PR #11 remains the existing recovery vehicle: **draft, open, unmerged, and
without auto-merge**. This correction does not move tags, change the frozen IR
schema, alter the owner checkout, or accept ADR-007.

- Repository: `KM-it-ops/PromptRig`
- Base / head: `feature/promptrig-framework` ← `fix/compiler-contract-recovery-v0.1`
- Isolated worktree: `C:\Users\alkur\Projects\PromptRig-mission-006`
- Owner checkout left untouched: `C:\Users\alkur\Projects\PromptRig`
- Frozen tag peeled commit: `7948c9a419dc02ea43ca994f0334733ea4b08855`

## Independent review correction

The independent review requested changes for six defects. Their resolutions
are deliberately behavioral, not source-identity claims:

1. **RFC 8785 numbers:** `rfc8785==0.1.4` replaces the hand-rolled Python
   float serializer. Every finite Appendix B vector is decoded from its
   IEEE-754 hexadecimal representation and asserted; NaN and both infinities
   are hard failures. The dependency review is
   `architecture/dependency-reviews/RFC8785_0_1_4.md`.
2. **Semantic fidelity:** every successful artifact retains exact canonical IR
   values in `promptrig_semantic_context.ir` and records one per-leaf
   `retained` disposition pointing to that artifact path. A digest or an
   all-pointer list is no longer called semantic coverage.
3. **Metamorphic proof:** generated regression cases mutate each frozen
   semantic family (including schemas, booleans, limits, arrays, capability
   requirements, and provenance) and require a different deployable artifact
   SHA-256.
4. **Output contracts:** all adapters and the compiler reject any
   `output_contracts` length above one. No required/optional ordering can
   select index zero.
5. **Omissions/deployability:** unsupported or conditional optional
   capabilities create machine-readable omissions with source path, semantic
   identifier, resolution, reason, and nondeployable effect. Artifact and
   envelope deployability agree.
6. **Evidence:** the semantic and safety matrices now describe actual
   retention, rejection, and omission paths. ADR-007 remains Proposed.

## Preserved and appended commits

The original five PR commits were preserved exactly. The correction commits
are appended; no commit was amended or rewritten.

1. `11a9a3d58ca65b813f4aff848a09b3fd66018658` — `test: add failing frozen-contract recovery cases`
2. `54927001f6d7abb4d537c9a99ad6a2d03e60400a` — `fix(compiler): fail closed on contract recovery gaps`
3. `0de31938d46518f402ead439f20deb7fbfcffb4c` — `docs(governance): recover contract evidence`
4. `6fb79b2673d7e4531127630b4815f972bccfcb0a` — `docs: add mission 006 recovery report`
5. `fc1088ced555cd956b9389c446643acd29628998` — `docs: record recovery pull request state`
6. `9ffe74a0beaadfc0a92e1c96bf80e0351482530b` — `test: expose remaining contract recovery defects`
7. `e2d569c45904d442ed5256894de6b9239aacad66` — `fix(canonical): use verified RFC 8785 serialization`
8. `e9517cf4ec715e08b4acf7449b13a9fa725c592a` — `fix(compiler): preserve or reject every IR semantic disposition`
9. `a99625ef5874a0bdc34d877b04b9e32d2ed9d8b4` — `docs(governance): correct semantic coverage evidence`
10. `6c27b81862ee66f254135c4a06e1f776e6cd18a6` — `docs(governance): record independent review correction evidence`
11. `eaca67c01f9a9b2d041d4ab1b1429d67ba42783f` — `test: cover DirectorySink provenance propagation`
12. `7f2763a00c69feb7bec6dd0856396658e75d9eac` — `fix(compiler): retain provenance through DirectorySink`

Before implementation, the independent-audit regression suite produced
**10 failed, 59 passed**. After the corrections it produced **69 passed**.

## Validation evidence

| Check | Result |
|---|---|
| Complete local pytest | 322 passed (Windows, Python 3.14.6) |
| RFC 8785 Appendix B / non-finite suite | 27 passed |
| Semantic metamorphic, output-contract, omission checks | 42 passed |
| Repeated determinism / no-network | covered by the passing compiler suite; no provider API was called |
| Legacy dataset validation | all four datasets passed |
| TypeScript drift | generator ran; no content diff |
| sdist and wheel | built successfully |
| Clean wheel install | successful in an isolated temporary venv |
| Installed CLI and module smoke tests | `doctor --json` and `adapters --json` passed for both entry points |
| Whitespace | `git diff --check` passed |
| Historical artifacts | MISSION-003/004/005 SHA-256 values matched recorded evidence |
| Frozen tag | peeled commit exactly `7948c9a419dc02ea43ca994f0334733ea4b08855` |
| GitHub CI | [run #40](https://github.com/KM-it-ops/PromptRig/actions/runs/29965354904) completed successfully |

CI run #40 completed all seven jobs successfully:

- `typescript-drift`
- Ubuntu, Windows, and macOS on Python 3.11
- Ubuntu, Windows, and macOS on Python 3.12

The package build retains the pre-existing setuptools deprecation warning for
the table-form `project.license`; it is unrelated to this correction.

## Remaining limitations and owner decisions

- The semantic context is a deterministic PromptRig sidecar, not a claim that
  every provider natively executes every IR field.
- The frozen IR still has no machine-readable security/privacy policy grammar;
  populated free-text policy blocks fail closed.
- No provider API behavior or credentials were used.
- ADR-007 remains Proposed, and multi-turn/session or composite output-contract
  lowering requires separate owner/architect authorization.
