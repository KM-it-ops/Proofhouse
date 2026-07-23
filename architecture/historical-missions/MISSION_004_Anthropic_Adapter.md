# MISSION-004 — PromptRig Anthropic Adapter (Third Conformance Target)

## Repository Target
Repository: `KM-it-ops/PromptRig`
Local repository rule: Use an isolated local worktree or fresh clone dedicated to this mission (e.g. `C:\tmp\promptrig-mission-004`). Do not check out, reset, or modify the owner's existing active local checkout.
Starting branch: `feature/promptrig-framework`
Required starting point: merge commit `bb3bb3acaf89199c9abeecdd77caa86787cc82e6` (MISSION-003 merge, containing the OpenAI adapter)
Working branch: `feature/anthropic-adapter-v0.1`
PR target: `feature/promptrig-framework`
Merge authorization: No merge is authorized under this mission. Open the PR and stop. The owner alone decides whether and when to merge.
Tag behavior: Do not create, move, or delete any Git tag under this mission.

Do not use:
- `integration/promptrig-part1-centralization`
- `feature/compiler-contract-freeze-v0.5`
- `feature/compiler-core-scaffold-v0.1` (merged and closed)
- `feature/openai-adapter-v0.1` (merged and closed; do not resume work there)

## Preconditions
Do not begin until:
- `feature/promptrig-framework` HEAD is confirmed at or descended from `bb3bb3acaf89199c9abeecdd77caa86787cc82e6`
- CI on that commit passes
- `src/promptrig/compiler/adapters/openai.py` and `openai_schema_subset.py` are present and unmodified as your implementation baseline pattern

## Objective
Implement the Anthropic adapter as the third conformance target for Compiler Core v0.1, per OAR-001-02's ratified adapter order (fake → OpenAI → Anthropic → Gemini). Prove the adapter contract and conformance suite generalize to a provider with materially different tool and reasoning semantics than OpenAI's — specifically the client/server tool distinction and extended-thinking/reasoning-block handling — without weakening any frozen invariant or silently reinterpreting Anthropic-specific state as if it were OpenAI-shaped.

This mission stays fully offline, exactly like MISSION-003. No live Anthropic API call, no credential handling, at any point.

## Frozen Decisions Governing This Mission
- OAR-001-02: adapter order is fake → OpenAI → Anthropic → Gemini; no provider may be silently substituted or downgraded.
- `PROVIDER_ADAPTER_CONTRACT.md`: every adapter implements `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)`; v0.1 adapters must not execute provider APIs; live execution is a separate, future interface/permission boundary. Provider-specific required state — explicitly including "reasoning signatures... or tool-loop continuation tokens" — must be modeled in adapter artifacts and provenance, and adapters must never emulate support by silently dropping such state or downgrading to free-form text.
- `PROVIDER_SELECTION_MATRIX.md`: Anthropic supports JSON outputs and strict tool use "with schema limits," and has a documented distinction between typed client tools and server-executed tools, plus adaptive/extended thinking "with preservation rules." These are exactly the capabilities this mission must model explicitly rather than flatten into OpenAI-shaped assumptions.
- `COMPILER_PASS_ARCHITECTURE.md`: adapter lowering never mutates canonical IR and never bypasses prior diagnostics.
- ADR-005: `promptrig-compiler` remains the CLI entry point for Compiler Core commands. Not open for reconsideration here.

## Scope
1. Add an `anthropic` entry to the adapter registry in `src/promptrig/compiler/adapters/`, alongside (not replacing) `fake` and `openai`.
2. Implement `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)` for the Anthropic adapter, following the same structural pattern as `openai.py`, adapted where Anthropic's actual model requires genuine divergence rather than copied for convenience.
3. Define a versioned Anthropic capability manifest using the existing namespaced/versioned capability vocabulary, distinguishing at minimum:
   - `tools.function_calling@1` or an Anthropic-appropriately-named equivalent capturing **client-executed (typed) tools**
   - a separate capability identifier for **server-executed tools**, since these are contractually distinct per the matrix and must not be collapsed into one capability
   - `reasoning.effort_control@1` or an Anthropic-appropriate equivalent for extended/adaptive thinking, explicitly modeling whatever preservation/continuation state Anthropic's documented thinking-block model requires
   - `output.structured_json@1` reflecting Anthropic's actual documented JSON-output and strict-tool-use schema limits
   Each capability's machine-readable limits must be sourced from current Anthropic documentation. Follow the same "only assert what's independently corroborated across multiple distinct sources" discipline used in MISSION-003 for `openai_schema_subset.py`. Where a claim can't be corroborated to that standard, leave it unasserted and record it as technical debt rather than guessing.
4. `lower()` MUST produce a deterministic, offline-computable artifact representing the exact request structure Anthropic would receive, including explicit representation of thinking-block/reasoning-preservation state and the client-vs-server tool distinction in the artifact and its provenance — not silently dropped or flattened into a single generic "tools" field if the distinction matters to correctness.
5. Investigate whether Anthropic's documented tool/output model makes the carried-over `output_contracts[0]`-only limitation (see Technical Debt Context below) matter in practice for this adapter. If it does, resolve it as part of this mission. If it doesn't, leave it as recorded technical debt and say so explicitly in the report — do not silently expand scope either way without stating which path you took and why.
6. Extend the existing conformance suite pattern (golden fixtures, capability-decision tests, explicit-failure-on-required-gap tests, non-mutation tests, zero-network enforcement) to cover the Anthropic adapter.
7. Register the Anthropic adapter so it appears correctly in `promptrig-compiler adapters` output and is selectable via `promptrig-compiler compile --adapter anthropic`.
8. If you discover a factual discrepancy between `PROVIDER_SELECTION_MATRIX.md`'s Anthropic claims and current Anthropic documentation, stop and flag it rather than editing the frozen document unilaterally — same rule as MISSION-003.

## Explicitly Optional / Separate Interface (Out of Scope Boundary)
Same boundary as MISSION-003: a live execution path calling the real Anthropic API is a separate, future interface and permission boundary. This mission:
- MAY read Anthropic's public API documentation to build an accurate, current capability manifest and payload shape.
- MAY write and run tests against a fully mocked/fake HTTP layer, with zero real network calls and zero real credentials at any point.
- MUST NOT make a real network call to any Anthropic endpoint, store or read any real API key, or add any code path that could execute a live request without a separately-authorized future mission.

If accurately modeling Anthropic's thinking-block or tool semantics seems to require live-call validation, stop and flag this as a stop condition rather than adding live-call capability.

## Documentation Access Note (informational, from MISSION-003 experience)
MISSION-003 found that direct fetches of `platform.openai.com` guide pages returned only JS-rendered shell content, and worked around this via search plus cross-checking multiple independent sources. Anthropic's documentation may or may not have the same limitation. Apply the same discipline regardless: if a source can't be verified to contain the actual guide body (not just navigation chrome), don't treat it as confirmed, and cross-check any claim across multiple independently-authored sources before encoding it into the capability manifest.

## Out of Scope
Do not implement:
- Gemini adapter (deferred to its own future mission per OAR-001-02's stated order)
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
- any change to the fake adapter's or OpenAI adapter's existing behavior or golden fixtures, except additive test-suite generalization needed to share conformance-test infrastructure with the new Anthropic adapter

## Technical Debt Context (informational, not automatically in scope)
Carried over from `MISSION_003_REPORT.md`:
- `openai_schema_subset.py` only models two confirmed strict-mode constraints, not full keyword coverage. Not this mission's job to fix unless directly blocking.
- `lower()`'s structured-output handling considers only `output_contracts[0]`. **See Scope item 5 above — this mission must explicitly decide whether to resolve this, not just carry it forward silently.**
- No capability-mismatch test covers `reasoning.effort_control@1` end-to-end, since the frozen IR schema has no field to source a reasoning-effort setting from. If Anthropic's thinking-block model has the same gap, note whether this mission encounters and handles it, or whether it remains an open IR-schema question for a future ADR.
- `_CODE_TO_EXIT`, `iter_schema_errors` first-failure-only behavior, TypeScript generator keyword coverage, and `doctor()`'s limited checks remain unresolved and out of scope unless directly blocking.

## Quality Gates
At minimum:
- Anthropic adapter unit tests (describe/check_capabilities/lower)
- capability-decision tests: required-capability-gap failure, optional-capability-gap warning
- golden fixture tests for deterministic `lower()` output given fixed IR + capability manifest + options
- non-mutation tests (canonical IR unchanged after lowering)
- explicit tests distinguishing client-tool vs. server-tool capability handling (not collapsed into one path)
- explicit test(s) covering thinking-block/reasoning-preservation representation in the lowered artifact
- schema/tool-use limit tests matching only the independently-corroborated Anthropic constraints actually encoded
- zero-network enforcement test proving no real HTTP call occurs anywhere in the test suite
- `promptrig-compiler adapters` and `compile --adapter anthropic` CLI parity tests
- full existing regression suite (fake, OpenAI, legacy — currently 154 tests) continues passing with zero regressions
- historical review artifacts remain byte-for-byte unchanged

## Git Workflow
1. Fetch latest `feature/promptrig-framework`
2. Verify starting commit `bb3bb3acaf89199c9abeecdd77caa86787cc82e6` or its current descendant HEAD
3. Create `feature/anthropic-adapter-v0.1` in the isolated worktree
4. Commit logically
5. Push normally
6. Open PR titled `Anthropic Adapter v0.1 (Third Conformance Target)`
7. Base: `feature/promptrig-framework`
8. Do not merge

## Final Report
Create `MISSION_004_REPORT.md` with:
- starting commit SHA
- branch and PR
- Anthropic adapter structure and how it parallels/diverges from the OpenAI adapter, with reasoning for any divergence
- capability manifest content, documentation sources, and corroboration method for each asserted constraint
- how client-tool vs. server-tool distinction is represented in the artifact
- how thinking-block/reasoning-preservation state is represented in the artifact
- explicit statement on the `output_contracts[0]` decision (resolved here, or still deferred, and why)
- conformance suite results
- explicit confirmation of zero live network calls and zero credential handling anywhere in the change
- CLI integration results
- deviations
- technical debt (new and carried-over)
- deferred work
- recommendation for MISSION-005 (expected: Gemini adapter, per OAR-001-02 order)

## Stop Conditions
Stop only for: a missing or altered starting commit, an Anthropic capability claim in `PROVIDER_SELECTION_MATRIX.md` that conflicts with current Anthropic documentation, any requirement that would require a real network call or real credential to implement or validate, a destructive Git requirement, unacceptable dependency risk, ambiguous repository state, or a contradiction requiring a new ADR.
