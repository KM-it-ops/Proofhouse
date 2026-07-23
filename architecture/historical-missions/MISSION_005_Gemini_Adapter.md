# MISSION-005 — PromptRig Gemini Adapter (Fourth Conformance Target)

## Repository Target
Repository: `KM-it-ops/PromptRig`
Local repository rule: Use an isolated local worktree or fresh clone dedicated to this mission (e.g. `C:\tmp\promptrig-mission-005`). Do not check out, reset, or modify the owner's existing active local checkout.
Starting branch: `feature/promptrig-framework`
Required starting point: merge commit `7ce633d123b8f74f7e823a1d3b1f0c0cc5cbfa07` (contains PR #7 and PR #8 — ADR-006 and the CI trigger fix)
Working branch: `feature/gemini-adapter-v0.1`
PR target: `feature/promptrig-framework`
Merge authorization: No merge is authorized under this mission. Open the PR and stop. The owner alone decides whether and when to merge.
Tag behavior: Do not create, move, or delete any Git tag under this mission.

Do not use:
- `integration/promptrig-part1-centralization`
- `feature/compiler-contract-freeze-v0.5`
- `feature/compiler-core-scaffold-v0.1`, `feature/openai-adapter-v0.1`, `feature/anthropic-adapter-v0.1`, `fix/ci-trigger-coverage`, `docs/adr-006-reasoning-ir-gap` (all merged and closed; do not resume work on any of them)

## Preconditions
Do not begin until:
- `feature/promptrig-framework` HEAD is confirmed at or descended from `7ce633d123b8f74f7e823a1d3b1f0c0cc5cbfa07`
- CI on that commit passes (confirm via a genuine run — either trigger path is now valid per the PR #8 fix; do not assume without checking, given the trigger-gap history)
- `src/promptrig/compiler/adapters/anthropic.py` and `anthropic_schema_subset.py` are present and unmodified as your most recent implementation baseline

## Objective
Implement the Gemini adapter as the fourth and final planned conformance target for Compiler Core v0.1's initial adapter set, per OAR-001-02's ratified order (fake → OpenAI → Anthropic → Gemini). Prove the adapter contract generalizes to a provider with schema-subset constraints and a thought-signature/continuation-token model, per `PROVIDER_SELECTION_MATRIX.md`'s explicit note that Gemini is expected to be the highest-complexity adapter ("High; schema subset and thought-signature continuity").

This mission stays fully offline, exactly like MISSION-003 and MISSION-004. No live Gemini API call, no credential handling, at any point.

## Frozen Decisions Governing This Mission
- OAR-001-02: adapter order is fake → OpenAI → Anthropic → Gemini; no provider may be silently substituted or downgraded. This is the last adapter in that ratified order.
- `PROVIDER_ADAPTER_CONTRACT.md`: `describe()`, `check_capabilities(validated_ir)`, `lower(validated_ir, resolution)`; no live execution; provider-specific required state (explicitly including "thought-signature continuity") must be modeled in adapter artifacts and provenance, never silently dropped or downgraded to free-form text.
- `PROVIDER_SELECTION_MATRIX.md`: Gemini offers "broad multimodal, tool, grounding, and code-execution surfaces"; structured output "with a supported schema subset"; "function calling plus built-in tools"; "thinking levels/signatures with model-specific continuation rules."
- `COMPILER_PASS_ARCHITECTURE.md`: adapter lowering never mutates canonical IR and never bypasses prior diagnostics.
- ADR-005: `promptrig-compiler` remains the CLI entry point. Not open for reconsideration.
- **ADR-006 (Proposed):** a reasoning/thinking-configuration IR gap has already been found independently twice — MISSION-003 (OpenAI `reasoning.effort_control@1`) and MISSION-004 (Anthropic `reasoning.extended_thinking@1`'s `budget_tokens`). This mission is explicitly instrumented to check whether Gemini's thought-signature/continuation-token model hits the same gap (see the dedicated Scope item below).

## Scope
1. Add a `gemini` entry to the adapter registry in `src/promptrig/compiler/adapters/`, alongside (not replacing) `fake`, `openai`, and `anthropic`.
2. Implement `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)` for the Gemini adapter, following the established structural pattern, adapted where Gemini's actual model genuinely diverges.
3. Define a versioned Gemini capability manifest, at minimum distinguishing:
   - `output.structured_json@1` reflecting Gemini's actual documented schema-subset constraints for structured output
   - `tools.function_calling@1` for caller-defined function tools
   - a distinct capability identifier for Gemini's built-in/grounding tools (e.g. code execution, search grounding), analogous to how MISSION-004 separated client vs. server tools for Anthropic — do not collapse built-in tools into the same capability as caller-defined function tools if they have materially different semantics or constraints
   - a reasoning/thinking capability identifier covering Gemini's thinking levels and signature/continuation-token model
   Source every machine-readable limit from current Gemini documentation, using the same "only assert what's independently corroborated across multiple distinct sources" discipline as MISSION-003 and MISSION-004. Where a claim can't be corroborated to that standard, leave it unasserted and record it as technical debt.
4. `lower()` MUST produce a deterministic, offline-computable artifact representing the exact request structure Gemini would receive, including explicit representation of any thought-signature/continuation-token state and the built-in-vs-function-tool distinction — never silently dropped or flattened.
5. **Reasoning-gap check (required, explicit finding needed either way):** Investigate whether Gemini's thinking-levels/signature/continuation-token model requires a field the frozen IR v0.1 cannot supply, the same category of gap found in MISSION-003 and MISSION-004. Whichever way this comes out, state it explicitly and prominently in the report:
   - If Gemini hits the same gap: this is the third independent confirmation. Do **not** attempt to resolve it yourself, do **not** modify ADR-006 or any frozen schema, and do **not** decide on your own whether to escalate ADR-006's status. Flag this finding clearly and separately in the report (its own subsection, not buried in Technical Debt) so the architect can make the escalation call explicitly, per ADR-006's own stated threshold.
   - If Gemini does *not* hit the same gap (e.g. its continuation-token model can be fully represented without needing new IR fields): state that explicitly too, with your reasoning — this would be evidence *against* generalizing the gap, which is equally worth recording accurately.
6. Investigate whether Gemini's structured-output model changes the standing finding on `output_contracts[0]`-only lowering (three data points now, per MISSION-004's own recommendation). State your conclusion and reasoning explicitly, whichever way it goes.
7. Extend the existing conformance suite pattern (golden fixtures, capability-decision tests, explicit-failure-on-required-gap tests, non-mutation tests, zero-network enforcement) to cover the Gemini adapter.
8. Register the Gemini adapter so it appears correctly in `promptrig-compiler adapters` output and is selectable via `promptrig-compiler compile --adapter gemini`.
9. If you discover a factual discrepancy between `PROVIDER_SELECTION_MATRIX.md`'s Gemini claims and current Gemini documentation, stop and flag it rather than editing the frozen document unilaterally — same rule as MISSION-003 and MISSION-004.

## Explicitly Optional / Separate Interface (Out of Scope Boundary)
Same boundary as MISSION-003 and MISSION-004: a live execution path calling the real Gemini API is a separate, future interface and permission boundary. This mission:
- MAY read Gemini's public API documentation to build an accurate, current capability manifest and payload shape.
- MAY write and run tests against a fully mocked/fake HTTP layer, with zero real network calls and zero real credentials at any point.
- MUST NOT make a real network call to any Gemini endpoint, store or read any real API key, or add any code path that could execute a live request without a separately-authorized future mission.

If accurately modeling Gemini's schema-subset or thought-signature semantics seems to require live-call validation, stop and flag this as a stop condition rather than adding live-call capability.

## Documentation Access Note
MISSION-003 and MISSION-004 both found that direct fetches of provider guide pages often return JS-rendered shell content only, and worked around this via search plus multi-source cross-checking. Expect the same possibility with Gemini's documentation. Apply the same discipline: don't treat a source as confirmed unless it demonstrably contains the actual guide body, and cross-check any claim across multiple independently-authored sources before encoding it into the capability manifest.

## Out of Scope
Do not implement:
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
- any modification to ADR-006 itself, its status, or the frozen IR schema — this mission gathers evidence relevant to ADR-006, it does not act on that evidence
- any change to the fake, OpenAI, or Anthropic adapters' existing behavior or golden fixtures, except additive test-suite generalization needed to share conformance-test infrastructure with the new Gemini adapter
- provider adapters beyond Gemini (this is the last adapter in OAR-001-02's stated initial order; anything beyond it is a future, separately-scoped decision)

## Technical Debt Context (informational, not automatically in scope)
Carried over from `MISSION_004_REPORT.md`:
- `anthropic_schema_subset.py`'s scope boundary and lack of a soft/warning-severity diagnostic for documented-but-unenforced keywords — not this mission's job unless directly blocking.
- `tools.server_executed@1` permanently `unsupported` under frozen IR v0.1 — informational; if Gemini's built-in/grounding tools hit an analogous representational gap, note it as a parallel finding, but do not attempt an IR fix here.
- The reasoning/thinking-configuration IR gap (see Scope item 5 — this mission's job is to investigate and report, not resolve).
- `_CODE_TO_EXIT`, `iter_schema_errors` first-failure-only behavior, TypeScript generator keyword coverage, `doctor()`'s limited checks — unresolved, out of scope unless directly blocking.

## Quality Gates
At minimum:
- Gemini adapter unit tests (describe/check_capabilities/lower)
- capability-decision tests: required-capability-gap failure, optional-capability-gap warning
- golden fixture tests for deterministic `lower()` output given fixed IR + capability manifest + options
- non-mutation tests (canonical IR unchanged after lowering)
- explicit tests distinguishing built-in/grounding tools vs. caller-defined function tools (not collapsed into one path)
- explicit test(s) covering thought-signature/continuation-token representation in the lowered artifact, to whatever extent the frozen IR allows
- schema-subset limit tests matching only the independently-corroborated Gemini constraints actually encoded
- zero-network enforcement test proving no real HTTP call occurs anywhere in the test suite
- `promptrig-compiler adapters` and `compile --adapter gemini` CLI parity tests
- full existing regression suite (currently 192 tests) continues passing with zero regressions
- historical review artifacts remain byte-for-byte unchanged

## Git Workflow
1. Fetch latest `feature/promptrig-framework`
2. Verify starting commit `7ce633d123b8f74f7e823a1d3b1f0c0cc5cbfa07` or its current descendant HEAD
3. Create `feature/gemini-adapter-v0.1` in the isolated worktree
4. Commit logically
5. Push normally
6. Open PR titled `Gemini Adapter v0.1 (Fourth Conformance Target)`
7. Base: `feature/promptrig-framework`
8. Do not merge

## Final Report
Create `MISSION_005_REPORT.md` with:
- starting commit SHA
- branch and PR
- Gemini adapter structure and how it parallels/diverges from the OpenAI and Anthropic adapters, with reasoning for any divergence
- capability manifest content, documentation sources, and corroboration method for each asserted constraint
- how built-in/grounding tools vs. function tools are represented in the artifact
- how thought-signature/continuation-token state is represented in the artifact
- **a dedicated, clearly labeled subsection: "ADR-006 third-confirmation check"** — explicit finding on whether Gemini hits the same reasoning-configuration IR gap, with reasoning either way
- explicit statement on the `output_contracts[0]` question with Gemini as a third data point
- conformance suite results
- explicit confirmation of zero live network calls and zero credential handling anywhere in the change
- CLI integration results
- deviations
- technical debt (new and carried-over)
- deferred work
- recommendation for what comes after MISSION-005 (the four-adapter initial set is now complete; recommend next priorities — e.g. evaluation/repair scoping, live-execution permission boundary design, or IR v0.2 planning if ADR-006 is confirmed a third time)

## Stop Conditions
Stop only for: a missing or altered starting commit, a Gemini capability claim in `PROVIDER_SELECTION_MATRIX.md` that conflicts with current Gemini documentation, any requirement that would require a real network call or real credential to implement or validate, a destructive Git requirement, unacceptable dependency risk, ambiguous repository state, or a contradiction requiring a new ADR.
