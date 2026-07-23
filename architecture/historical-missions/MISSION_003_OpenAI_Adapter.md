# MISSION-003 — PromptRig OpenAI Adapter (Second Conformance Target)

## Repository Target
Repository: `KM-it-ops/PromptRig`
Local repository rule: Use an isolated local worktree or fresh clone dedicated to this mission (e.g. `C:\tmp\promptrig-mission-003`). Do not check out, reset, or modify the owner's existing active local checkout.
Starting branch: `feature/promptrig-framework`
Required starting point: merge commit `11b5a89e8353465b665dad7563ba8578f4a84abe` (MISSION-002 merge, containing the Compiler Core v0.1 scaffold)
Working branch: `feature/openai-adapter-v0.1`
PR target: `feature/promptrig-framework`
Merge authorization: No merge is authorized under this mission. Open the PR and stop. The owner alone decides whether and when to merge.
Tag behavior: Do not create, move, or delete any Git tag under this mission.

Do not use:
- `integration/promptrig-part1-centralization`
- `feature/compiler-contract-freeze-v0.5`
- `feature/compiler-core-scaffold-v0.1` (merged and closed; do not resume work there)

## Preconditions
Do not begin until:
- `feature/promptrig-framework` HEAD is confirmed at or descended from `11b5a89e8353465b665dad7563ba8578f4a84abe`
- CI on that commit passes
- ADR-005 and decision log entry `D-050-009` are present and unchanged

## Objective
Implement the OpenAI adapter as the second conformance target for Compiler Core v0.1, per OAR-001-02's ratified adapter order (deterministic fake adapter → OpenAI → Anthropic → Gemini). Prove the adapter contract, capability model, and conformance suite generalize beyond the fake adapter to a real provider without weakening any frozen invariant.

This mission MAY perform live OpenAI API calls strictly within the bounds defined below. This is the first mission in the PromptRig project authorized to leave fully offline/no-network territory — treat that boundary with extra care.

## Frozen Decisions Governing This Mission
- OAR-001-02: adapter order is fake → OpenAI → Anthropic → Gemini; no provider may be silently substituted or downgraded.
- `PROVIDER_ADAPTER_CONTRACT.md`: every adapter implements `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)`; v0.1 adapters must not execute provider APIs from within `lower()` itself — live execution is a separate, future interface and permission boundary. `lower()` in this mission produces the OpenAI-specific artifact (e.g. the exact request payload/prompt structure OpenAI would receive), not a live response.
- `COMPILER_PASS_ARCHITECTURE.md`: adapter lowering never mutates canonical IR and never bypasses prior diagnostics.
- `PROVIDER_SELECTION_MATRIX.md`: OpenAI supports strict JSON Schema response formats and function/tool calling; the adapter must model the documented schema-subset and tool-mapping constraints explicitly rather than silently dropping unsupported capability requests.
- ADR-005: the `promptrig-compiler` binary remains the CLI entry point for all Compiler Core commands, including any new `adapters`/`inspect` output referencing the OpenAI adapter. Do not reopen or re-litigate this decision.

## Scope
1. Add an `openai` entry to the adapter registry in `src/promptrig/compiler/adapters/`, alongside (not replacing) the existing fake adapter.
2. Implement `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)` for the OpenAI adapter, following the same structural pattern as the existing fake adapter in that directory.
3. Define a versioned OpenAI capability manifest using the existing namespaced/versioned capability vocabulary (e.g. `output.structured_json@1`, `tools.function_calling@1`), reflecting OpenAI's actual documented support and limits — not aspirational or assumed capabilities.
4. `lower()` MUST produce a deterministic, offline-computable artifact (the exact structured request/prompt payload OpenAI would receive) from validated IR and resolved capabilities. `lower()` MUST NOT itself call the OpenAI API, handle credentials, or touch the network — that stays out of scope per the note below.
5. Extend the existing conformance suite pattern (golden fixtures, capability-decision tests, explicit-failure-on-required-gap tests, non-mutation tests) to cover the OpenAI adapter, reusing the structure already proven against the fake adapter.
6. Register the OpenAI adapter so it appears correctly in `promptrig-compiler adapters` output, and is selectable via `promptrig-compiler compile --adapter openai`.
7. Update `architecture/compiler-contract-freeze-v0.5/PROVIDER_SELECTION_MATRIX.md` or an equivalent evidence file only if you discover a factual discrepancy between the matrix's OpenAI capability claims and current OpenAI API documentation — do not alter it to fit implementation convenience; if you find a discrepancy, stop and flag it rather than editing the frozen document unilaterally.

## Explicitly Optional / Separate Interface (Out of Scope Boundary)
A **live execution path** that actually calls the OpenAI API with real credentials is a SEPARATE, FUTURE interface and permission boundary per `PROVIDER_ADAPTER_CONTRACT.md` ("Future execution is a separate interface and permission boundary"). This mission:
- MAY read OpenAI's public API documentation to build an accurate, current capability manifest and payload shape.
- MAY write and run tests against a fully mocked/fake HTTP layer to validate payload shape and error handling, with zero real network calls and zero real credentials at any point.
- MUST NOT make a real network call to any OpenAI endpoint, store or read any real API key, or add any code path that could execute a live request without an explicit, separately-authorized future mission enabling it.

If implementing an accurate `lower()` seems to require live-call validation, stop and flag this as a stop condition rather than adding live-call capability.

## Out of Scope
Do not implement:
- Anthropic or Gemini adapters (deferred to their own future missions per OAR-001-02's stated order)
- any live network call to any provider
- credential storage, retrieval, or handling of any kind
- evaluation or repair
- persistence or hosted jobs
- tenant authorization or billing
- UI
- PRS compiler
- MissionRig compiler
- any modification to `promptrig-compiler`'s CLI entry-point naming (ADR-005 is settled)
- any modification to the legacy `promptrig` CLI or its commands
- any change to the fake adapter's existing behavior or golden fixtures, except additive test-suite generalization needed to share conformance-test infrastructure with the new OpenAI adapter

## Technical Debt Context (informational, not in scope to fix)
Carried over from `MISSION_002_REPORT.md`, for awareness only — do not fix these as part of this mission unless they block OpenAI adapter work directly:
- `_CODE_TO_EXIT` in `cli_compiler.py` is a hand-maintained static mapping with no completeness test against the registry.
- `iter_schema_errors` returns only the first validation failure per run.
- The TypeScript generator does not yet handle `oneOf`/`allOf`/`anyOf`/`patternProperties`.
- `doctor()`'s environment checks are limited in scope (no sink-directory write-permission check, no separate diagnostic-schema-load check).

If any of the above genuinely blocks correct OpenAI adapter implementation, stop and flag it rather than silently expanding scope to fix it.

## Quality Gates
At minimum:
- OpenAI adapter unit tests (describe/check_capabilities/lower)
- capability-decision tests: required-capability-gap failure, optional-capability-gap warning
- golden fixture tests for deterministic `lower()` output given fixed IR + capability manifest + options
- non-mutation tests (canonical IR unchanged after lowering)
- schema-subset limit tests (documented OpenAI structured-output/tool-calling constraints modeled explicitly, not silently ignored)
- zero-network enforcement test proving no real HTTP call occurs anywhere in the test suite
- `promptrig-compiler adapters` and `compile --adapter openai` CLI parity tests, matching the existing library/CLI parity pattern
- full existing regression suite (fake adapter, legacy, prior 126 tests) continues passing with zero regressions
- historical review artifacts remain byte-for-byte unchanged

## Git Workflow
1. Fetch latest `feature/promptrig-framework`
2. Verify starting commit `11b5a89e8353465b665dad7563ba8578f4a84abe` or its current descendant HEAD
3. Create `feature/openai-adapter-v0.1` in the isolated worktree
4. Commit logically
5. Push normally
6. Open PR titled `OpenAI Adapter v0.1 (Second Conformance Target)`
7. Base: `feature/promptrig-framework`
8. Do not merge

## Final Report
Create `MISSION_003_REPORT.md` with:
- starting commit SHA
- branch and PR
- OpenAI adapter structure and how it parallels the fake adapter
- capability manifest content and its documentation sources
- `lower()` output shape and determinism evidence
- conformance suite results
- explicit confirmation of zero live network calls and zero credential handling anywhere in the change
- CLI integration results
- deviations
- technical debt (new and carried-over)
- deferred work
- recommendation for MISSION-004 (expected: Anthropic adapter, per OAR-001-02 order)

## Stop Conditions
Stop only for: a missing or altered starting commit/freeze state, an OpenAI capability claim in `PROVIDER_SELECTION_MATRIX.md` that conflicts with current OpenAI documentation, any requirement that would require a real network call or real credential to implement or validate, a destructive Git requirement, unacceptable dependency risk, ambiguous repository state, or a contradiction requiring a new ADR.
