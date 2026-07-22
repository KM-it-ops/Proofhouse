# MISSION-006 Report — Compiler Contract Recovery and Re-Certification v0.1

## 1. Starting state and isolation

- **Repository:** `KM-it-ops/PromptRig`
- **Required integration commit:** `65cd2d216a8a0a29030ee159d47a155344abf4a5`
- **Recovery branch:** `fix/compiler-contract-recovery-v0.1`
- **Isolated clean clone:** `C:\Users\alkur\Projects\PromptRig-mission-006`
- **Original owner checkout:** `C:\Users\alkur\Projects\PromptRig` was not modified.

The original local checkout was stale. The clean clone verified `origin/feature/promptrig-framework` at the required commit. The annotated tag object is `c6006c42639cbe33755999fb66e49f29bb849fef`; its required peeled commit, checked with `git rev-parse "refs/tags/v0.5-architecture-freeze^{}"`, is `7948c9a419dc02ea43ca994f0334733ea4b08855`.

## 2. Commits and pull request

1. `11a9a3d58ca65b813f4aff848a09b3fd66018658` — `test: add failing frozen-contract recovery cases`
2. `54927001f6d7abb4d537c9a99ad6a2d03e60400a` — `fix(compiler): fail closed on contract recovery gaps`
3. `0de31938d46518f402ead439f20deb7fbfcffb4c` — `docs(governance): recover contract evidence`

The recovery-test commit was run before production fixes: **14 failed, 2 passed**, exercising the intended defects. PR status is recorded after push/creation in this report's final update.

## 3. Frozen-contract corrections

- Canonicalization rejects unsafe integers, NaN, Infinity, and normalizes the tested ECMAScript/JCS exponent boundaries.
- Semantic sections and `output.structured_json@1` / `tools.function_calling@1` declarations must agree; contradictions fail with an existing validation diagnostic.
- Multiple required output contracts fail explicitly instead of lowering index zero.
- Required conditional capabilities fail; optional unresolved capabilities are warnings/recorded omissions.
- Partial lowering quarantines artifacts and cannot become deployable success.
- Public API and CLI require an exact adapter version; unavailable or missing versions fail at the public boundary.
- Every successful artifact receives immutable, machine-readable provenance: IR paths/digest, compiler/adapter identities, complete manifest digest/version, decisions, and deployability.
- Capability-manifest digests cover identity, version, supported/conditional capabilities, and limits.
- Compiler-state and capability-manifest nested JSON structures are recursively immutable.
- RFC 6901 escaping is used for schema and validation pointers; normalization produces an identity source map.
- Safety rejects side-effecting/no-approval conflicts, read-only autonomy conflicts, and free-text security/privacy policies that cannot be machine enforced by frozen IR v0.1.

## 4. Semantic and safety coverage

`architecture/compiler-contract-freeze-v0.5/SEMANTIC_COVERAGE_MATRIX.md` classifies every frozen v0.1 path. Provider-request fields lower where representable; all successful artifacts retain source-path and canonical-IR traceability. Free-text security and privacy rules fail closed rather than being treated as enforceable.

`architecture/compiler-contract-freeze-v0.5/SAFETY_COVERAGE_MATRIX.md` records the exact implemented controls and explicitly identifies execution as out of scope.

## 5. Governance and historical evidence

- ADR-006 is internally consistent with its Accepted status and no longer claims that the OpenAI artifact has an unfillable reasoning field.
- ADR-007 remains Proposed. Its evidence now records Anthropic, OpenAI, and Gemini continuation-state evidence; `architecture/adr/OWNER_DECISION_REQUEST_ADR_007.md` asks the owner whether that evidence warrants acceptance.
- MISSION-003, -004, and -005 original files were recovered from retained downloads and committed under `architecture/historical-missions/`.
- SHA-256 source/copy pairs matched exactly:
  - MISSION-003: `2abf2239fb84d563296c7b10821e98285488f00291fe01abefde905498044669`
  - MISSION-004: `256b4b5206197217d47c318219aa88e93e6bad9d168b23d5c9879eab90687e42`
  - MISSION-005: `48b9ee9741a40e50a281df91eb39df84e4dd632ddc1787f34acb9eba3f3ab6f6`
- Provider evidence was refreshed from primary provider documentation only, without provider API execution or credentials.

## 6. Validation evidence

| Check | Result |
|---|---|
| Untouched baseline | 236 passed (Python 3.14.6) |
| Pre-fix recovery suite | 14 failed, 2 passed as expected |
| Final full pytest suite | 252 passed in 5.77s (Python 3.14.6, Windows) |
| Focused recovery suite | 16 passed |
| Determinism/no-network | covered by passing compiler suite; no provider APIs were called |
| TypeScript drift | generator run; no content diff |
| Package build | sdist and wheel built successfully |
| Clean wheel install | successful in isolated venv |
| Installed console script | `doctor --json` and `adapters --json` successful |
| Module entry point | `python -m promptrig.compiler.cli_compiler` doctor/adapters successful |
| Historical review artifacts | 242 SHA-256 entries verified |
| Frozen tag | peeled commit exactly `7948c9a419dc02ea43ca994f0334733ea4b08855` |
| CI (Windows/Linux/macOS, Python 3.11/3.12) | pending PR CI; not represented as locally complete |

The packaging tool emitted an existing setuptools deprecation warning for the table-form `project.license`; it did not fail the build and is unrelated to this mission's frozen contracts.

## 7. Deviations and remaining decisions

- No frozen IR schema, tag, diagnostic registry, review-cycle artifact, credential, or provider-execution path was changed.
- Provider documentation is evidence only; no live API behavior was tested.
- Cross-platform/Python-3.11/3.12 validation is delegated to the repository's existing PR CI matrix and remains pending until CI completes.
- The frozen IR does not supply a machine-readable security/privacy policy language. MISSION-006 fails such populated policy sections closed. A future owner/architect decision is needed to authorize any policy-language design.
- ADR-007 acceptance and any future multi-turn/session schema remain owner/architect decisions.
- No merge recommendation is made. Independent architect review and explicit owner authorization remain required.

## 8. Stop conditions

No binding mission stop condition was triggered after the clean-clone preconditions passed. The stale original clone and annotated-tag-object versus peeled-tag distinction were recorded as precondition evidence, not treated as contract defects.
