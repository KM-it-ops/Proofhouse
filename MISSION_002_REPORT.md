# MISSION-002 Report — PromptRig Compiler Core Scaffold

## Status

Implementation complete per the scope authorized in `MISSION_002_PromptRig_Compiler_Core_Scaffold.md`. 126 tests passing (114 new Compiler Core tests + 12 pre-existing legacy PromptOps tests, no regressions). PR opened against `feature/promptrig-framework`, not merged, per Git Workflow.

## Starting freeze SHA

- `v0.5-architecture-freeze` tag → `7948c9a419dc02ea43ca994f0334733ea4b08855` (verified unchanged and unmoved throughout the mission)
- Working branch base (owner-designated starting commit, includes OAR-001 and the diagnostic registry): `808681d0198deef75d45146a0eed6abbdfb0d884`

## Branch and PR

- Working branch: `feature/compiler-core-scaffold-v0.1`
- PR: "Compiler Core Scaffold v0.1", base `feature/promptrig-framework`, not merged (see PR link in the mission chat response)
- Commits on the mission branch:
  - `a7b6c02` — docs: add MISSION-002 Compiler Core Scaffold mission file
  - `a8f9ba2` — docs: record active-checkout isolation deviation
  - `bea279c` — feat(compiler): canonical hashing, diagnostics, IR validation, pass pipeline, fake adapter
  - `795eaee` — feat(compiler): artifact sink, vendored contract schemas, public library API
  - `fbba9fd` — feat(compiler): CLI wrapper, library/CLI parity tests, doctor fallback fix
  - `fbd1da4` — feat(compiler): TypeScript contract generation, CI matrix, no-network + determinism tests
  - this report finalization commit

## Package structure

```
src/promptrig/compiler/
  __init__.py            # COMPILER_ID / COMPILER_VERSION / IR_CONTRACT_VERSION
  canonical.py            # RFC 8785-style JCS, UTF-8, SHA-256, structural rejection rules
  contracts.py             # immutable boundary dataclasses (Diagnostic, Artifact, CompileResult, ResultEnvelope, ...)
  diagnostics.py           # registry + diagnostic-contract-schema-conformant emission
  ir.py                    # strict IR schema validation + semantic invariant checks
  capability.py            # versioned capability manifest model
  sink.py                  # ArtifactSink protocol, InMemorySink, path-safe DirectorySink
  paths.py                 # resolves vendored schema files
  api.py                   # public library ops: compile / validate / inspect / list_adapters / doctor
  cli_compiler.py          # promptrig-compiler CLI (argument parsing + exit codes only)
  schemas/                 # vendored, drift-tested copies of the frozen IR/diagnostic/registry files
  passes/
    base.py                 # CompilationState + Pass protocol
    normalization.py, validation.py, optimization.py,
    capability_resolution.py, safety.py, adapter_lowering.py
  pipeline.py               # fixed-order pass runner with per-pass digest/duration trace
  adapters/
    base.py                  # Adapter protocol, AdapterDescriptor, LoweringResult, AdapterNotFoundError
    fake.py                   # deterministic fake adapter (describe/check_capabilities/lower)
    __init__.py                # registry: only "fake" registered; openai/anthropic/gemini fail explicitly
  codegen/
    typescript.py             # dependency-free JSON-Schema -> TypeScript generator

architecture/typescript/     # committed generated output (promptrig_ir.ts, diagnostic.ts)
scripts/generate_typescript_contracts.py

tests/compiler/               # 114 tests across 12 files, fixtures/, fixtures/golden/
```

Legacy `src/promptrig/{cli,loadouts,runner,schemas,scoring,templates}.py` are untouched. `pyproject.toml` gained a `jsonschema` dependency, `requires-python = ">=3.11"` (OAR-001-01), a `promptrig-compiler` console script, and package-data for the vendored schemas.

## Public API

`promptrig.compiler.api` exposes five operations, each returning a `ResultEnvelope` (never raising for expected user errors):

- `validate(ir_raw, *, source_document)` — normalization + schema validation only
- `inspect(ir_raw, *, source_document)` — validation plus a non-lowering manifest summary
- `compile(ir_raw, *, adapter_id, options, sink, source_document)` — full six-pass pipeline
- `list_adapters()` — registered adapters (`fake` only) plus reserved-but-unimplemented ids
- `doctor()` — offline environment checks (Python version, registry/schema loadability, offline-mode declaration)

## Pass scaffold

Six passes behind a shared `Pass` protocol (`CompilationState -> (CompilationState, diagnostics)`), run by `pipeline.run_pipeline` in the fixed order `normalization → validation → optimization → capability_resolution → safety → adapter_lowering`, stopping at the first pass that emits an error diagnostic:

- **normalization** — recomputes the canonical digest; a `CanonicalizationError` becomes `PRG-NORMALIZATION-0001` and stops the pipeline.
- **validation** — checks `spec_version` first (`PRG-VALIDATION-0003` on mismatch), then full JSON Schema validation (`PRG-VALIDATION-0001`), then duplicate semantic-owner ids within `requirements`/`tools`/`workflow.steps` (`PRG-VALIDATION-0004`).
- **optimization** — traced no-op, per v0.1 scope.
- **capability_resolution** — required-capability gaps are `PRG-CAPABILITY-0001` (fatal); optional gaps are `PRG-CAPABILITY-0002` (warning-only, pipeline continues).
- **safety** — flags side-effecting tools declaring `approval: never` as `PRG-SAFETY-0001`.
- **adapter_lowering** — only reached if nothing upstream stopped the pipeline; delegates to the selected adapter's `lower()`.

`pipeline.run_pipeline` rejects a passes tuple whose order doesn't match the fixed `PASS_ORDER` prefix. Mutation-protection is enforced and tested: `CompilationState` is a frozen dataclass, every pass returns a new instance, and a test asserts the caller's original IR dict is byte-identical (via deep equality) after a full pipeline run.

## Canonicalization behavior

`canonical.py` implements the OAR-001-04 profile: UTF-8, RFC 8785-style key ordering (by UTF-16-BE code-unit comparison), ECMAScript-style number formatting (integral floats and `-0` serialize without a decimal point / as `0`), duplicate-key rejection during parsing (before any canonicalization is attempted), and lone-surrogate rejection both in raw UTF-8 decoding and in `\uXXXX`-escaped strings. No Unicode normalization is ever applied — NFD and NFC forms of the same visual string canonicalize to different bytes, verified by test. 19 adversarial tests cover key ordering, numbers (including NaN/Infinity rejection), string escaping, duplicate keys (top-level and nested), invalid UTF-8, lone surrogates (value and key position), and valid surrogate pairs.

## Diagnostic enforcement and diagnostic-contract conformance

`diagnostics.py`'s `DiagnosticFactory.emit()` is the only way to produce a `Diagnostic` inside the compiler passes/adapter: it (1) resolves the code against `DIAGNOSTIC_CODE_REGISTRY.json`, rejecting unregistered or retired codes and refusing any attempt to override a code's fixed severity; (2) computes a deterministic fingerprint (SHA-256 of canonical `{code, phase, document, json_pointer}` — same location + code always fingerprints identically regardless of message text); and (3) validates the resulting object against the vendored `DIAGNOSTIC_CONTRACT.schema.json` via `jsonschema`, raising `DiagnosticRegistryError` if a registry-valid code somehow produces a non-conforming object. 13 registry/contract tests cover: known-code resolution, unregistered-code rejection, wrong-phase rejection, severity-override rejection, retired-code rejection, active/retired overlap rejection, contract-schema conformance (validated against the real schema, not a mock), and fingerprint determinism/uniqueness-by-location.

## Fake adapter behavior

`adapters/fake.py`'s `FakeAdapter` implements all three named operations from `PROVIDER_ADAPTER_CONTRACT.md`:

- `describe()` — returns an `AdapterDescriptor` (`adapter_id="fake"`, `provider_id="fake"`, capability-manifest version + digest, artifact kinds, conformance-suite version); deterministic across calls; asserted to never equal a live-provider id.
- `check_capabilities(validated_ir)` — resolves each declared required/optional capability against the manifest (`output.structured_json@1`, `tools.function_calling@1`, `reasoning.effort_control@1` are supported; anything else is `unsupported`).
- `lower(validated_ir, resolution)` — fails explicitly with `status="failure"` and no artifacts if any required capability is unsupported; otherwise produces one deterministic `compiled_prompt` artifact (canonical-JSON payload, SHA-256-addressed).

It requires no credentials, performs no network access (asserted via a `socket.socket`/`socket.create_connection`-patching test fixture across every public-API operation), and the adapter registry (`adapters/__init__.py`) raises `AdapterNotFoundError` for `openai`/`anthropic`/`gemini` rather than silently substituting the fake adapter — verified by test. A committed golden fixture (`tests/compiler/fixtures/golden/fake_adapter_minimal_ir.json`) pins the exact lowering output for the minimal valid IR.

## CLI commands

`promptrig-compiler` (installed script) / `python -m promptrig.compiler.cli_compiler` (module form) — both invocation forms verified end-to-end against a real built wheel installed into a throwaway venv, run from outside the repository entirely:

- `promptrig-compiler validate INPUT [--json]`
- `promptrig-compiler inspect INPUT [--json]`
- `promptrig-compiler compile INPUT [--adapter ID] [--output DIR] [--json]`
- `promptrig-compiler adapters [--json]`
- `promptrig-compiler doctor [--json]`

Exit codes follow `LIBRARY_CLI_CONTRACT.md` exactly (0/2/3/4/5/6/7/8), computed from diagnostic codes via a fixed priority table (`_CODE_TO_EXIT`) with the lowest applicable code winning. `--json` mode writes exactly one JSON object to stdout (verified by a newline-count test) with human-readable diagnostics/artifact locations on stderr-free stdout otherwise. The CLI module contains no compiler logic of its own — every subcommand handler is a thin wrapper calling the matching `api.py` function and mapping its `ResultEnvelope` to stdout + exit code.

All 10 `LIBRARY_CLI_PARITY_MATRIX.json` cases (PARITY-001 through PARITY-010) are implemented as tests proving CLI JSON deep-equals the library result (modulo the volatile `duration_seconds` field, which the parity rule's "declared transport metadata" removal is understood to cover).

## TypeScript generation path

`codegen/typescript.py` is a small, dependency-free JSON-Schema → TypeScript generator (no `datamodel-code-generator` or similar, to avoid adding a dependency for a narrow need) covering exactly the shapes the two frozen schemas use: objects (as `interface`s, with required/optional fields), arrays, `enum`, `const`, `$ref` into `$defs`, and the four JSON Schema primitive types. `scripts/generate_typescript_contracts.py` regenerates `architecture/typescript/{promptrig_ir,diagnostic}.ts` from the vendored schemas; a committed-output drift test (`test_committed_typescript_matches_regenerated_output`) fails if regeneration doesn't byte-match what's committed, and the `typescript-drift` CI job runs the same check via `git diff --exit-code`.

## Tests and CI

- 114 new tests across `tests/compiler/` (canonicalization: 19, diagnostics: 13, IR validation: 9, pass pipeline: 11, fake adapter golden: 6, artifact sink: 4, contract-schema drift: 3, public API: 16, CLI: 12, library/CLI parity: 11, TypeScript generation: 4, no-network/determinism: 8) plus the 12 pre-existing legacy tests — 126 total, all passing.
- `.github/workflows/ci.yml`: the `test` job now runs on a `{ubuntu, windows, macos}-latest × {3.11, 3.12}` matrix, runs the full pytest suite, keeps the legacy dataset-validation step untouched, and adds a Compiler Core CLI smoke test for both the installed-script and `python -m` invocation forms. A new `typescript-drift` job fails the build on any uncommitted TypeScript regeneration diff.
- Manually verified outside the automated suite (not itself a CI step, but exercised once during this mission): built a real wheel with `python -m build`, installed it into a throwaway venv, and ran both CLI forms from a directory outside the repository — confirms the vendored-schema approach makes the installed package genuinely self-contained.
- `git diff --stat` of `review-cycles/` between the starting commit and the final mission-branch commit is empty: all 244 historical review files remain byte-for-byte unchanged.

## Deviations

1. **Active-checkout isolation correction.** `feature/compiler-core-scaffold-v0.1` was briefly created and committed to directly against the owner's active local checkout at `C:\Users\alkur\Projects\PromptRig`, before a corrected mission-file version reconfirmed the local-repository rule requiring an isolated worktree. Corrected before any Compiler Core implementation began: the active checkout was restored to `feature/promptrig-framework` via a plain non-destructive `git checkout` (nothing to stash — it was already clean), the mission branch and its one existing commit (`a7b6c02`) were verified untouched (local and `origin` SHAs identical before and after), and all further work moved to the isolated worktree `C:\tmp\promptrig-mission-002`. No destructive Git action occurred.

2. **`promptrig` CLI name collision — Compiler Core ships as `promptrig-compiler`, not merged into `promptrig`.** `LIBRARY_CLI_CONTRACT.md` specifies `promptrig validate INPUT [--json]` etc. under the same binary as the legacy commands. But the pre-existing legacy CLI (`src/promptrig/cli.py`) already defines `promptrig validate --dataset DATASET` — a different command with incompatible arguments and semantics (JSONL eval-dataset validation, not IR validation) under the same subcommand name. Merging both under one `promptrig` entry point would require either breaking/renaming the legacy `validate` command (which the mission explicitly forbids: "no reimplementation of legacy `report`, `loadouts`, `compile-loadout`, or `generate` commands") or silently shadowing one implementation with the other, which risks a user's existing `promptrig validate --dataset ...` workflow either breaking or resolving to the wrong command depending on dispatch order. Rather than silently deciding this either way, Compiler Core was given its own console-script name, `promptrig-compiler` (plus `python -m promptrig.compiler.cli_compiler`), fully satisfying the mission's functional CLI requirements (stable exit codes, JSON envelope, parity with the library, both required invocation forms) without touching legacy behavior. **This is an open question for the owner / a future ADR**: whether to (a) keep two separate binaries permanently, (b) rename the legacy `validate` subcommand to free up the name, or (c) namespace Compiler Core under a `promptrig compiler <cmd>` subcommand group inside the existing binary.

3. **`requires-python` bumped from `>=3.10` to `>=3.11`.** Per OAR-001-01 (Python 3.11+ is the authoritative Compiler Core v0.1 runtime). This is a floor increase for the whole package, including legacy PromptOps code; legacy code was not audited for 3.10-only features, but none were found in the (small, dependency-light) legacy modules during this mission.

4. **Frozen schemas are vendored into the package (`src/promptrig/compiler/schemas/`), not read from `architecture/` at runtime.** The frozen contract files live outside `src/`, so an installed wheel would not otherwise include them. Vendored copies are pinned to their `architecture/` source via a byte-equality drift test (`test_contract_schema_drift.py`) — any future edit to the frozen files must be mirrored into `schemas/` or CI fails. Verified end-to-end with a real wheel build/install run from outside the repo.

5. **`Artifact.to_dict()` includes a `data_base64` field when no sink path exists.** The frozen contract requires artifact entries to contain "either bytes/path"; the initial implementation only ever exposed `path`, silently dropping in-memory artifact content from JSON output when no `--output` directory was given. Fixed to base64-encode `data` into the envelope when `path` is absent, so CLI `--json` output without `--output` still carries the actual artifact bytes, not just its digest.

## Technical debt

- The exit-code priority table (`_CODE_TO_EXIT` in `cli_compiler.py`) is a static mapping maintained by hand; it will need a corresponding entry whenever a new diagnostic code is added to the registry. There's no test asserting every active registry code has a mapping (only that the codes actually exercised by tests map correctly).
- `iter_schema_errors` returns only the *first* schema-validation failure per run (validation pass returns on first batch of errors rather than accumulating across multiple independent invalid fields in one document) — sufficient for v0.1's "fail explicitly" requirement but less helpful for a caller with many simultaneous errors to fix.
- The TypeScript generator is intentionally narrow (handles exactly the two frozen schemas' shapes: no `oneOf`/`allOf`/`anyOf`, no `patternProperties`). It will need extension before it can generalize to a schema using those constructs.
- `doctor()`'s environment checks are limited to Python version, registry loadability, and IR schema loadability; it does not yet check for e.g. filesystem write permissions in a caller-supplied sink directory, or validate the diagnostic contract schema itself as a separate check (schema-load failure there would currently surface as a generic internal error rather than a named `doctor` check).

## Deferred work

Everything explicitly Out of Scope for MISSION-002 remains deferred: OpenAI/Anthropic/Gemini adapters (the adapter registry recognizes but rejects these ids, per OAR-001-02's stated order), network access and credential handling, evaluation, repair, persistence, hosted jobs, tenant authorization, billing, UI, the PRS compiler, and the MissionRig compiler. Within scope but intentionally minimal for v0.1: the optimization pass (traced no-op only, per `COMPILER_PASS_ARCHITECTURE.md`), and the safety pass (one rule implemented — side-effecting tools requiring approval — as a representative, testable instance of the safety-policy-conflict pattern rather than a full policy engine).

## Recommendation for MISSION-003

1. Resolve the `promptrig` vs `promptrig-compiler` CLI naming question (Deviation 2) via ADR before any further CLI-surface work, since later missions will make the split harder to unwind.
2. Implement the OpenAI adapter as the second conformance target per OAR-001-02, reusing the same `describe/check_capabilities/lower` contract and adding it to the adapter registry — the fake-adapter conformance suite pattern (golden fixtures, capability-decision tests, explicit-failure-on-required-gap tests) should transfer directly.
3. Expand the safety pass beyond the single side-effecting-tool-approval rule into a fuller policy engine once real policy requirements are specified (currently a representative stub, per Technical Debt above).
4. Consider whether `iter_schema_errors` should accumulate and report all schema violations in one pass rather than stopping at the first, to reduce validate-fix-revalidate cycles for IR authors.
