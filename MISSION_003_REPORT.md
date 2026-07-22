# MISSION-003 Report — PromptRig OpenAI Adapter (Second Conformance Target)

## Status

Implementation complete per the scope authorized in `MISSION_003_OpenAI_Adapter.md`. 154 tests passing (28 new/updated Compiler Core tests on top of MISSION-002's 126, zero regressions). PR opened against `feature/promptrig-framework`, not merged, per Git Workflow. **Zero live network calls and zero credential handling anywhere in this change** — see the dedicated confirmation section below.

## Starting commit SHA

- `feature/promptrig-framework` HEAD, confirmed via `git merge-base --is-ancestor`: `11b5a89e8353465b665dad7563ba8578f4a84abe` (the MISSION-002 merge commit)
- CI on that commit: `completed success` (run `29892572290`, verified before this mission began)
- ADR-005 and decision log entry `D-050-009`: confirmed present and unchanged before implementation began; not reopened or re-litigated

## Branch and PR

- Working branch: `feature/openai-adapter-v0.1`, created from `11b5a89` in the isolated worktree `C:\tmp\promptrig-mission-003`
- PR: "OpenAI Adapter v0.1 (Second Conformance Target)", base `feature/promptrig-framework`, not merged
- Commits on the mission branch:
  - `fe1d962` — feat(compiler): OpenAI adapter, second conformance target (OAR-001-02)
  - this report commit

## OpenAI adapter structure and how it parallels the fake adapter

`adapters/openai.py` follows the exact structural pattern of `adapters/fake.py`: a class exposing `adapter_id`/`adapter_version` class attributes and `capability_manifest()`, `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)` instance methods, constructed the same way (`DiagnosticFactory`, `source_document`). `check_capabilities()` has the identical required/optional capability-decision loop as the fake adapter (deliberately duplicated rather than shared, to keep each adapter independently reviewable and to avoid any risk of coupling the fake adapter's tested behavior to a new shared helper). `lower()` follows the fake adapter's fail-fast-on-required-gap pattern, then diverges to add the schema-subset validation this provider actually requires (see below), and produces one deterministic artifact via the same `canonicalize`/`canonical_sha256` primitives.

The adapter registry (`adapters/__init__.py`) now returns `openai` from `list_registered_adapter_ids()` alongside `fake`; `anthropic` and `gemini` remain in `RESERVED_LIVE_ADAPTER_IDS` and still raise `AdapterNotFoundError` rather than falling back to any other adapter.

## Capability manifest content and its documentation sources

Verified against current OpenAI documentation (2026-07-22) via web search against `platform.openai.com` guide content, since a direct fetch of the JS-rendered guide pages returned only navigation chrome, not body text — the underlying facts below were corroborated across the OpenAI developer community and multiple independent technical summaries citing the same guides, not a single unverified source:

| Capability | Resolution | Basis |
|---|---|---|
| `output.structured_json@1` | `supported` | OpenAI Structured Outputs (strict mode) |
| `tools.function_calling@1` | `supported` | OpenAI Function Calling (`strict: true`) |
| `reasoning.effort_control@1` | `conditional` | Model-specific; not available on all OpenAI models, matching `PROVIDER_SELECTION_MATRIX.md`'s "Model-specific reasoning effort" |

Both `supported` capabilities carry identical machine-readable `limits` (via the new `CapabilityManifest.limits`/`limits_for()` field, additive and backward-compatible — the fake adapter's manifest still defaults to `{}`):
- `additional_properties_must_be_false: true` — every object-typed schema node must set `additionalProperties: false`.
- `all_properties_must_be_required: true` — every property declared in `properties` must also appear in `required`; "optional" fields are expressed as a nullable type union (e.g. `["string", "null"]`), not by omission from `required`.
- `supported_types`: `string, number, integer, boolean, array, object, null`.
- a `source` URL for each (`https://platform.openai.com/docs/guides/structured-outputs`, `https://platform.openai.com/docs/guides/function-calling`).

**No conflict found** between `PROVIDER_SELECTION_MATRIX.md`'s claim ("OpenAI supports strict JSON Schema response formats and function tools") and current documentation — confirmed accurate, so the frozen matrix was not modified, per the mission's instruction to only touch it on a genuine factual discrepancy.

**Scope boundary, stated honestly:** `openai_schema_subset.py`'s checker encodes only the two hard constraints above (`additionalProperties: false`, all-properties-required) plus the supported type set — these are the constraints I could confirm with reasonable confidence against current documentation via the available research tools. It does **not** assert anything about `minLength`, `pattern`, `format`, numeric bounds, or other JSON Schema keywords' support/non-support in strict mode, because I did not obtain solid, current-dated confirmation of those specifics. This is called out explicitly in the module's docstring and in Technical Debt below, rather than presented as more complete than it is.

## `lower()` output shape and determinism evidence

`lower()` produces one artifact (`name="openai_request_payload"`, media type `application/vnd.promptrig.openai.request-payload+json`) containing canonical-JSON bytes of:

```json
{
  "adapter_id": "openai",
  "adapter_version": "0.1.0",
  "ir_sha256": "<sha256 of canonical validated IR>",
  "model_selection": "runtime-configured; not frozen by the compiler artifact",
  "instructions": "<deterministically built from objective.goal + behavior.instructions + behavior.constraints>",
  "tools": [{"type": "function", "function": {"name", "description", "parameters", "strict": true}}, ...],
  "response_format": {"type": "json_schema", "json_schema": {"name", "strict": true, "schema"}} | null,
  "capability_decisions": [...]
}
```

`model_selection` is deliberately never a concrete model id/brand alias — `PROVIDER_SELECTION_MATRIX.md`: "Exact models and API versions are runtime configuration and provenance, never frozen brand aliases."

Determinism evidence:
- `test_lower_is_deterministic_across_runs` — two `lower()` calls on identical input produce byte-identical artifact `data` and `sha256`.
- `test_lower_matches_committed_golden_fixture` — output for a fixed IR is pinned against `tests/compiler/fixtures/golden/openai_adapter_structured_output.json`, generated once and asserted unchanged.
- `test_lower_never_mutates_input_ir` — the caller's IR dict is deep-equal to a pre-call snapshot after lowering (mutation-protection, matching the same pattern used for the fake adapter in MISSION-002).

## Conformance suite results

24 new tests, all passing:
- 9 in `test_openai_schema_subset.py` — compliant/non-compliant object schemas, nullable-union support, unsupported-type detection, nested-object JSON-pointer reporting, array/items handling.
- 15 in `test_openai_adapter.py` — `describe()` determinism and identity, capability manifest resolution (`supported`/`conditional`) and machine-readable limits, `check_capabilities()` gap detection, `lower()` required-capability-gap failure, compliant/non-compliant structured-output and tool lowering (explicit `PRG-ADAPTER-0001` failure on non-compliance, never silent), determinism, non-mutation, and golden-fixture match.

Additive coverage in existing suites (extending, not replacing, the MISSION-002 infrastructure): `api.compile(..., adapter_id="openai")` success (`test_api.py`), CLI `compile --adapter openai` (`test_cli.py`), an 11th library/CLI parity case (`PARITY-011`, `test_library_cli_parity.py`) proving CLI JSON deep-equals the library result for the OpenAI path exactly as the original 10 cases do for fake/validate/inspect/adapters/doctor, and zero-network enforcement (below).

## Zero live network calls and zero credential handling — explicit confirmation

- **No code path in `adapters/openai.py`, `adapters/openai_schema_subset.py`, or any test file constructs an HTTP client, opens a socket, or references an API key, environment variable for credentials, or any authentication header.** `lower()` operates purely on the in-memory validated IR dict and returns a payload description — it never calls `requests`, `httpx`, `urllib`, the `openai` SDK, or any other network-capable library. No such dependency was added to `pyproject.toml`.
- **Enforced by test, not just by inspection:** every test in `test_openai_adapter.py` runs under an autouse fixture (`forbid_network`) that monkeypatches `socket.socket` and `socket.create_connection` to raise `AssertionError` if called — so any future accidental network call in this file's coverage fails loudly rather than silently passing. `test_no_network_and_determinism.py` additionally covers the full `api.compile(..., adapter_id="openai")` path under the same enforcement.
- **No live-call validation was performed or needed.** Capability facts were established via public documentation research only (see sourcing above); no stop condition was triggered on this front.
- Documentation research used `WebSearch` (returns search-result snippets, not live provider API calls) and an attempted `WebFetch`/`ctx_fetch_and_index` of the guide pages themselves (which returned mostly JS-shell chrome, not usable body text, and was not an OpenAI *API* call in any case — it's a public docs page, not `api.openai.com`).

## CLI integration results

`promptrig-compiler adapters --json` now lists both `fake` and `openai` (order: `["fake", "openai"]`, matching `list_registered_adapter_ids()`). `promptrig-compiler compile INPUT --adapter openai --json` succeeds for compliant IR and exits with the correct code (`4` via `PRG-CAPABILITY-0001` for a missing required capability; the schema-subset failure path returns `PRG-ADAPTER-0001`, mapped to exit `6` by the existing `_CODE_TO_EXIT` table from MISSION-002 — no changes to `cli_compiler.py` were needed, its adapter-agnostic design already covered this). No changes were made to ADR-005's settled CLI entry-point decision, the legacy `promptrig` CLI, or the fake adapter's existing CLI behavior.

## Deviations

1. **Two MISSION-002 tests updated to reflect the now-larger adapter registry.** `test_compile_unknown_adapter_fails_explicitly_never_substitutes` and `test_list_adapters_reports_only_fake_as_registered` (renamed to `test_list_adapters_reports_fake_and_openai_as_registered`) hardcoded `openai` as *the* example of an unregistered/reserved adapter id, which stopped being true the moment this mission legitimately registered it. Updated to use `anthropic` as the still-unimplemented example and to expect both `fake` and `openai` in the registry listing. This is a registry-membership assertion update, not a change to the fake adapter's actual behavior or its golden fixtures (both untouched — `fake.py` was not modified at all).
2. **`WebFetch` of the OpenAI guide pages returned unusable content** (JS-rendered navigation chrome only, not the guide body). Fell back to `WebSearch`, cross-checking the resulting claims across multiple independent sources (OpenAI developer community, several third-party technical write-ups) rather than trusting a single result, before encoding them into the capability manifest.

## Technical debt

New, from this mission:
- `openai_schema_subset.py` encodes only the two constraints confirmed with confidence (see Scope boundary above); it does not model every OpenAI strict-mode keyword restriction. A future mission with more reliable access to the current guide's full body text (e.g. an authenticated fetch, or a maintained schema fixture from OpenAI's own SDK/OpenAPI spec) should tighten this.
- `lower()`'s structured-output handling only ever considers `output_contracts[0]` — an IR with multiple `output_contracts` entries silently lowers only the first. Not exercised by any IR in the current fixture set, but worth an explicit multi-contract test/behavior decision before it matters.
- No capability-mismatch test yet covers a `reasoning.effort_control@1` request end-to-end through `lower()` (the manifest correctly reports it `conditional`, but no artifact field currently reflects a reasoning-effort setting, since the frozen IR schema itself has no such field to source it from).

Carried over from `MISSION_002_REPORT.md` (informational only, not touched, none of them blocked this mission):
- `_CODE_TO_EXIT` in `cli_compiler.py` remains a hand-maintained static mapping.
- `iter_schema_errors` still returns only the first validation failure per run.
- The TypeScript generator still doesn't handle `oneOf`/`allOf`/`anyOf`/`patternProperties`.
- `doctor()`'s environment checks remain limited in scope.

## Deferred work

Anthropic and Gemini adapters (per OAR-001-02's stated order, next up per the matrix). Live OpenAI execution (a separate, future interface/permission boundary per `PROVIDER_ADAPTER_CONTRACT.md`, explicitly out of scope here). Multi-`output_contracts` lowering behavior (see Technical Debt). Broader strict-schema-subset keyword coverage beyond the two confirmed constraints.

## Recommendation for MISSION-004

1. **Anthropic adapter**, per OAR-001-02's order, following this mission's pattern: `describe/check_capabilities/lower` mirroring `fake.py`'s and `openai.py`'s structure, a capability manifest with machine-readable limits sourced from current Anthropic documentation (JSON outputs, strict tool use, distinct client/server tool contracts per `PROVIDER_SELECTION_MATRIX.md`), and the same golden-fixture/determinism/non-mutation/zero-network conformance suite shape.
2. Resolve the `output_contracts[0]`-only limitation (Technical Debt) before or during the Anthropic adapter work if Anthropic's schema model makes multi-contract lowering more likely to matter.
3. If a future mission gets reliable access to the full current text of provider strict-mode documentation (rather than JS-shell-only fetches), revisit `openai_schema_subset.py` to confirm whether additional keywords are actually restricted, and extend the checker accordingly with the same "only assert what's confirmed" discipline used here.
