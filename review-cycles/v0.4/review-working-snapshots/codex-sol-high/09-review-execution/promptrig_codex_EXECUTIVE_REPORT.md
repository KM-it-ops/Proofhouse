# PromptRig v0.4 Independent Codex Preimplementation Audit

## Reviewer identity and mandate

- Reviewer: `openai-codex`
- Product surface: OpenAI Codex desktop
- Observed model identifier: `unknown`
- Specialist mandate: benchmark validity, autonomous executability, repository operability, contract/test completeness, scope sequencing, silent ambiguity, and requirement-to-architecture-to-test traceability
- Independence: canonical supplied corpus only; no other review was inspected and no prior project memory was used

## Corpus identity

- Corpus version: `v0.4`
- Declared archive: `promptrig-review-corpus-v0.4.zip`
- Declared SHA-256: `a0bd3c1a6d91bb2330cd41d8933a723d94fc01ea40cfe824aca707a4666902e2`
- Verification limitation: the extracted corpus contains the declared digest in `PACK_MANIFEST_v0.4.json` and `09-review-execution/evidence/CORPUS_SHA256.txt`, but the ZIP itself is `NOT FOUND IN PROVIDED MATERIAL`, so the archive digest could not be independently recomputed.

## Executive verdict

**Reject for architecture freeze.**

This is not a rejection of the v0.4 independent-review intake. `00-governance/STATUS_AND_DECISIONS.md § v0.4 status` and `08-release/RELEASE_NOTES_v0.4.md` correctly limit the current release to review execution and state that architecture is unfrozen. The package is adequate to solicit review, subject to the Round 1 validator defect below. It is not an executable benchmark starter and must not be used to launch production implementation.

Two conditions independently invalidate a freeze:

1. Benchmark-defining variables remain unresolved: mandatory adapters, budgets, network semantics, source snapshot, environment digests, secrets policy, and final repetition policy.
2. The canonical IR and adjacent result/manifest schemas validate structures that cannot enforce the stated semantics. A schema-valid submission can be functionally empty.

The design direction is coherent: canonical IR, provider-specific lowering, deterministic checks before model grading, bounded repair, whole-configuration benchmarking, and autonomous/steered separation are defensible. The failure is at the executable-contract boundary, not the product thesis.

## Traceability assessment

| Requirement chain | Architecture/contract evidence | Test evidence | Verdict |
|---|---|---|---|
| Canonical, versioned IR (`PROJECT_CHARTER § Governing principles`; `PROMPTRIG_MASTER_SCOPE § Compiler pipeline`) | ADR-001 accepted; RFC-001 in Review; `PROMPTRIG_IR.schema.json` present | `VALIDATION_MATRIX` says public/hidden tests “yes,” but supplies no test IDs or fixtures | **Fail:** schema accepts empty instructions, opaque core domains, and five repair passes |
| Provider-aware lowering and two mandatory adapters (`PRD § Compilation`; Acceptance gate 7) | RFC-002 in Review; provider manifest schema present | Hidden-test interface names fake provider and registry only | **Fail:** providers are unselected; interface and conformance vectors are absent |
| Evaluation, baseline, bounded repair (`PRD § Evaluation`; ADR-006) | RFC-003 in Review; evaluation schemas present | Matrix names bounded repair; no scoring goldens | **Fail:** evaluator identity/threshold/aggregation are unspecified; empty passed result validates |
| One shared Simple/Developer project (`PROMPTRIG_MASTER_SCOPE § Primary experience`; Acceptance gates 8-9) | UX states parity; baseline architecture says UI edits IR | Matrix names e2e/diff but no canonical scenarios or assertions | **Incomplete:** central IR cannot yet encode the full shared state |
| Tenant isolation and credential safety (Acceptance gates 14-17) | Threat model and database entity list present | Matrix says public/hidden/security review | **Fail for freeze:** no authorization matrix, role model, RLS contract, storage policy, or deletion state machine |
| Reproducible whole-agent benchmark (ADR-004, ADR-005) | Rules, environment prose, submission schema present | No executable starter, pinned image, source mirror, or preflight fixture in supplied corpus | **Fail:** parameters are unresolved and the manifest accepts empty evidence/environment |

The corpus therefore does not satisfy `ARCHITECTURE_FREEZE_CHECKLIST § Scope and value` (“Every P0 requirement maps to architecture and acceptance tests”) or `§ Benchmark` (“Task, environment, budgets, intervention policy, hidden-test contract, sealing, and scoring are executable”).

## Blocking findings

### Critical

- `REV-CODEX-CRITICAL-001`: Benchmark launch controls are unresolved and therefore non-comparable.
- `REV-CODEX-CRITICAL-002`: Canonical IR schema cannot enforce the canonical semantics.

### High

- `REV-CODEX-HIGH-001`: Requirements do not trace to architecture and executable tests.
- `REV-CODEX-HIGH-002`: Evaluation results and weighted scoring lack executable decision semantics.
- `REV-CODEX-HIGH-003`: Asynchronous API and job lifecycle are not contractually executable.
- `REV-CODEX-HIGH-004`: Provider adapter contract is prose-only and conformance cannot be shared.
- `REV-CODEX-HIGH-005`: Benchmark and review provenance manifests do not seal the claimed evidence.
- `REV-CODEX-HIGH-006`: Benchmark 1 scope and milestone sequencing invite silent feature triage.
- `REV-CODEX-HIGH-007`: Tenant, credential, deletion, and storage boundaries are not implementation contracts.

## Nonblocking findings

- `REV-CODEX-MEDIUM-001`: Supabase is simultaneously locked and provisional across the source hierarchy.
- `REV-CODEX-MEDIUM-002`: The Round 1 validator does not validate run-manifest shape, checksums, artifact existence, or evidence sufficiency.

The second finding does not prevent reviewers from producing useful work, but it prevents “validator passed” from being sufficient evidence that a review meets the output contract.

## Contradictions and silent ambiguities

1. **Repair limit:** `PROMPTRIG_MASTER_SCOPE § MVP inclusions` and `ACCEPTANCE_CRITERIA § Required Developer Mode capabilities` require 0-2; `PROMPTRIG_IR.schema.json /properties/evaluation/properties/repair_limit` permits 0-5.
2. **Supabase status:** `PROMPTRIG_MASTER_SCOPE § Locked architecture decisions` says locked; `STATUS_AND_DECISIONS § Provisional` and ADR-003 say provisional.
3. **Compilation level:** `PRD § Compilation` requires Application Specification selection; `PROMPTRIG_MASTER_SCOPE § MVP inclusions` lists only Prompt, Prompt System, and Agent Blueprint.
4. **Frozen sources:** `SOURCE_MANIFEST` calls itself frozen but says the snapshot “should contain” sources and provides no actual URLs, versions, files, or hashes.
5. **Job behavior:** API rules require resumable jobs and idempotent repair, while the resource list contains no job, repair, or cancellation contract.
6. **Release provenance:** `README.md` remains titled v0.3 and predicts v0.4 as an executable benchmark starter, while actual v0.4 is a review-launch release. This is explainable evolution but should be made unambiguous before sealing.

## Missing evidence

- `NOT SPECIFIED`: the two Benchmark 1 provider adapters.
- `NOT SPECIFIED`: autonomous wall-clock, cost, CPU, memory, disk, token/tool-call, and retry budgets.
- `NOT SPECIFIED`: Frozen-mode connectivity implementation (fully offline versus allowlisted frozen mirror).
- `NOT FOUND IN PROVIDED MATERIAL`: executable starter commit, Git metadata, Makefile, containers, migrations, public tests, deterministic fake provider, database seed, and benchmark runner. This is consistent with `ROADMAP § Phase C` being future work, but it means implementation is not authorized.
- `NOT FOUND IN PROVIDED MATERIAL`: frozen official-document snapshot with URLs, versions, retrieval timestamps, and hashes.
- `NOT FOUND IN PROVIDED MATERIAL`: stable requirement IDs, defined P0 classification, and a complete traceability matrix.
- `NOT FOUND IN PROVIDED MATERIAL`: scoring scale, threshold, aggregation formula, tie/missing-run rules, and human inter-rater protocol.
- `UNKNOWN`: selected/requested model label, observed model identifier, Codex harness version, and account tier; the surface did not expose them.

## Assumptions rejected

- Rejected: “JSON Schema syntax passes” means the P0 contracts are complete. All ten schemas pass Draft 2020-12 metaschema checks, yet adversarial valid instances demonstrate semantic vacuity.
- Rejected: agents can choose reasonable adapters, budgets, network access, or scoring details without harming fairness. These choices directly affect cost, completion, and score.
- Rejected: `VALIDATION_MATRIX` entries marked “yes” prove coverage. They contain no test identifiers, fixtures, assertions, or evidence paths.
- Rejected: weighted dimensions alone define a score. A scale and deterministic aggregation policy are required.
- Rejected: the v0.3 detailed manifest seals v0.4. It omits every v0.4 execution file and has two observed hash mismatches.
- Rejected: a full-stack breadth-first build is neutral among agents. Under fixed budgets it rewards undocumented feature triage and shallow stubbing.

## Proposed ADR, RFC, and schema changes

1. Accept a **Benchmark Configuration ADR** covering adapters, sealed commit, image/database/source digests, budgets, network and secrets policy, repetitions, intervention/incident rules, and telemetry.
2. Revise **ADR-001/RFC-001** with typed P0 IR domains, requiredness by compilation level, semantic versioning/migration policy, and 0-2 repair limit.
3. Accept **RFC-002** only with a machine-readable adapter protocol, capability vocabulary, fake-provider specification, diagnostics, fallbacks, approval semantics, and conformance vectors.
4. Accept **RFC-003** only with typed evaluation case/result/evaluator records and complete scoring/aggregation rules.
5. Add a **Job Lifecycle RFC/OpenAPI contract** for create, poll, cancel, retry, idempotency, budgets, terminal states, partial artifacts, and authorization.
6. Add a **Tenant and Secret Boundary ADR** with role/resource matrix, RLS/server responsibilities, worker identity, storage paths, retention/deletion, credential indirection, and audit events.
7. Replace opaque IR, evaluation, provider, and submission objects with closed `$defs`; add a strict `REVIEW_RUN_MANIFEST.schema.json`; require finding evidence.
8. Generate a canonical v0.4 per-file manifest and frozen-source index; label or remove stale release manifests from the active provenance chain.

## Validation plan

1. **Contract gate:** metaschema validation plus negative fixtures for every P0 schema. Required probes must reject empty instructions, repair limit 3+, empty provider capabilities/models, empty passed evaluation evidence, and empty submission environment/evidence/artifacts.
2. **Trace gate:** CI verifies every P0 requirement ID maps to an accepted architecture component and executable public/hidden test or approved human protocol.
3. **Adapter gate:** one shared suite passes unchanged against the deterministic fake provider and the two named adapters.
4. **Job gate:** contract tests cover duplicate idempotency keys, concurrent cancel, timeout, partial provider failure, retry, unauthorized polling, and exactly-once versioning.
5. **Security gate:** generated cross-tenant tests cover every table, API resource, storage object, trace, export, credential metadata path, and worker action.
6. **Scoring gate:** two independent scorers produce identical outcomes for golden fixtures spanning regression, evaluator error, infrastructure failure, missing run, tie, and human disagreement.
7. **Benchmark preflight:** two clean-room executions from the sealed starter reproduce configuration metadata and deterministic fixture outputs; undeclared network or environment drift fails closed.
8. **Evidence gate:** deterministic archive build verifies per-file and archive hashes; one-byte mutation, missing file, wrong checksum, missing output, or malformed run manifest is rejected.

## Residual risks

Even after these corrections, model/provider drift, evaluator bias, supply-chain drift, nontechnical usability, and the commercial open-core boundary remain real. They are manageable only if Frozen-mode evidence is separated from research mode, deterministic tests retain priority, human UX/security review remains explicit, and public claims stay configuration-specific. Supabase portability and long-running-job infrastructure should remain evidence-triggered decisions, but their Benchmark 1 boundaries cannot remain implicit.

## Confidence and limitations

- Overall confidence: **0.98**
- High-confidence basis: direct cross-document conflicts, schema inspection, Draft 2020-12 metaschema validation, adversarial valid-instance probes, detailed-manifest hash comparison, and repository inventory.
- Limitations: no private reasoning is claimed or used; no other reviewer output was inspected; no internet research was used; the declared ZIP was absent; this extracted review corpus is not a Git worktree; no implementation, public tests, hidden tests, containers, or provider calls were available to execute.
