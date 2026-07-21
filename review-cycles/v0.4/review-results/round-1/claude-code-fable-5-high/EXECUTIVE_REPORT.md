# PromptRig Round 1 Independent Review — Executive Report

## Reviewer identity and mandate

- **Reviewer:** anthropic-claude-code (Claude Code, requested model label "Claude Fable 5", observed identifier `claude-fable-5`)
- **Specialist mandate:** Architecture coherence, long-horizon maintainability, system boundaries, coupling, state ownership, evolvability, failure containment, contract consistency, survival under provider/product change (per `review-kits/CLAUDE_CODE_FABLE_REVIEW.md` and `09-review-execution/REVIEWER_REGISTRY.md`).
- **Corpus:** v0.4, archive SHA-256 `a0bd3c1a6d91bb2330cd41d8933a723d94fc01ea40cfe824aca707a4666902e2` (recorded in `PACK_MANIFEST_v0.4.json` and `09-review-execution/evidence/CORPUS_SHA256.txt`; review performed on the extracted directory tree).

## Executive verdict

**Approve with conditions.** The core architectural commitments — versioned IR as semantic source of truth (ADR-001), adapter contract with capability manifests (RFC-002), bounded repair (ADR-006), whole-system benchmark unit (ADR-004), and evidence-first governance — are justified and internally motivated. However, the contract layer that everything else depends on is not yet coherent enough to freeze. Five high-severity findings (REV-CLAUDE-HIGH-001 through -005) individually meet the corpus's own definition of freeze-blocking ("likely major rework, security failure, or misleading result", `03-architecture/ARCHITECTURE_REVIEW_PLAN.md` §Severity). None invalidates the product concept; all are resolvable with small ADR/schema changes before freeze. Implementation should not be authorized until they are dispositioned.

## Blocking findings (block freeze unless waived)

1. **REV-CLAUDE-HIGH-001 — Repair-limit contract contradicts itself across four normative sources, with dual state ownership.** The canonical IR allows `repair_limit` 0–5 (`schemas/PROMPTRIG_IR.schema.json` lines 162–166); `CompilationRequest.repair_limit` allows 0–2 default 1 (`schemas/COMPILATION_REQUEST.schema.json` lines 36–41); `EvaluationResult.repair_pass` caps at 2 (`schemas/EVALUATION_RESULT.schema.json` lines 62–66); accepted decision D-008 says "default one pass, configurable zero to two" (`00-governance/LEGACY_DECISION_LOG.md` D-008), as do `04-specification/ACCEPTANCE_CRITERIA.md` (Developer Mode: "configure zero to two repair passes") and `01-vision/PROMPTRIG_MASTER_SCOPE.md` (MVP inclusions). Separately, the same knob is owned twice — required in the semantic IR *and* settable per compilation request — with no precedence rule. Smallest fix: remove the runtime budget from the IR (or make it advisory), make the request the single owner, align all bounds to 0–2, and state precedence in ADR-006.

2. **REV-CLAUDE-HIGH-002 — The provenance/trace contract cannot reconstruct a compilation run.** `CompilationResult.provenance` is a `$ref` to a *single* `TRACE_EVENT` (`schemas/COMPILATION_RESULT.schema.json` lines 55–57) for an 11-stage pipeline (`03-architecture/rfcs/RFC-001-COMPILER-PIPELINE.md`). `TRACE_EVENT.schema.json` has no compilation/run correlation key and no parent/span linkage — `trace_id` is per-event. RFC-001's invariant "Every artifact traces back to IR fields and compiler version" has no schema carrier: `ARTIFACT_MANIFEST.schema.json` records only `generated_from_version`, not IR field paths or compiler version. As specified, "traceable provider calls" (PRD NFR) and benchmark evidence reassembly are unimplementable.

3. **REV-CLAUDE-HIGH-003 — Synchronous-first execution posture contradicts the job-based API contract; no component owns durable job state.** `03-architecture/BASELINE_ARCHITECTURE.md` defers background jobs ("introduced only when synchronous execution becomes inadequate"), yet `04-specification/API_CONTRACTS.md` already mandates "Long-running operations return a job identifier and resumable status", `CompilationResult` carries `queued/running/canceled` states, `04-specification/UX_SPEC.md` requires those states for every async operation, and the threat model requires cancellation. A compile spanning provider calls, evaluation, and bounded repair across multiple `target_providers` is long-running at MVP by definition, not at some future scale threshold (Open Question 6 defers exactly the wrong thing). The contract has already decided; the architecture hasn't. Smallest fix: an ADR committing MVP to job *semantics* over a Postgres-backed job table (no external queue), adding a jobs entity to `04-specification/DATABASE_MODEL.md`.

4. **REV-CLAUDE-HIGH-004 — Tenant-isolation enforcement point is ambiguous between Supabase RLS and the FastAPI compiler service.** `04-specification/DATABASE_MODEL.md` mandates tested row-level rules on every tenant-owned table, and the threat model requires enforcement "server-side and through database row-level policies" (`07-verification/SECURITY_THREAT_MODEL.md` §Cross-tenant access). But nothing specifies how `services/compiler-api` connects to Postgres. The default Supabase pattern for a backend service is a service-role credential that *bypasses RLS*, making the RLS test gate false assurance for the primary compute plane. Trust boundaries 2 and 3 also imply two independent write paths to the same tables (browser→Supabase and web→compiler-api→Postgres) with different authorization regimes. This is the corpus's own R-06 critical risk left with an unspecified control point. Smallest fix: an ADR naming the single enforcement point per table class and pinning the compiler-api DB access mode (user-scoped JWT vs service role + mandatory application-layer authz tests).

5. **REV-CLAUDE-HIGH-005 — The canonical IR is untyped exactly where the product's differentiating levels depend on it, making the schema-validation gate vacuous and threatening benchmark comparability.** In `schemas/PROMPTRIG_IR.schema.json`, `knowledge`, `memory`, `workflow`, `autonomy`, `security`, `privacy`, `provider_requirements`, `deployment` are bare `{"type":"object"}`, and `tools`, `input_contracts`, `output_contracts` items are untyped (lines 82–147, 179–181). Acceptance hard gates 6 and 10 ("IR validates against the canonical schema"; "static validation catches malformed IR") pass trivially over these regions. The `agent_blueprint` and `application_specification` compilation levels depend precisely on the untyped fields, so independent benchmark competitors will invent incompatible shapes — undermining ADR-001's portability claim and Stage 1 comparability. Smallest fix: type `tools` and `output_contracts` before freeze and cut or defer `application_specification` (and, if unresolved, `agent_blueprint`) from Benchmark 1.

## Nonblocking findings

- **REV-CLAUDE-MEDIUM-006** — Idempotency keys are mandated for compile/evaluate/repair/export (`API_CONTRACTS.md`) but optional in `COMPILATION_REQUEST.schema.json`; no request schemas exist for evaluate/repair/export; repair is not an addressable API resource at all.
- **REV-CLAUDE-MEDIUM-007** — `PROVIDER_MANIFEST.schema.json` `capabilities` is a free-form key/value bag with no controlled vocabulary; capability negotiation (RFC-002) and pipeline stage 5 cannot be conformance-tested consistently across four adapters.
- **REV-CLAUDE-MEDIUM-008** — Multi-provider compilation partial failure is unrepresentable: one `CompilationRequest` targets N providers but `CompilationResult` has a single status and single `result_version_id`, and `evaluation_summary` is untyped.
- **REV-CLAUDE-MEDIUM-009** — `mode` is owned twice (IR `project.mode` and required `CompilationRequest.mode`) with no precedence; a request-level mode that changes compilation behavior is configuration outside the IR, in tension with the master-scope rule against non-IR behavior configuration.
- **REV-CLAUDE-MEDIUM-010** — `benchmark_runs`/`benchmark_submissions` sit in the product database model while the benchmark environment mandates separate database/storage/trace namespaces; harness bookkeeping is coupled into the tenant SaaS schema and inflates every competitor's Stage 1 scope.
- **REV-CLAUDE-MEDIUM-011** — IR `spec_version` is `const "0.2.0"` with no migration mechanism; `schemas/` is byte-identical to `archive/v0.2/schemas/` (verified by directory diff), and the freeze checklist requires accepted "IR ownership, versioning, and migration rules" that do not exist yet.
- **REV-CLAUDE-MEDIUM-012** — Compiler-core location drifts across documents: `BASELINE_ARCHITECTURE.md` has no core library (logic implicitly in `services/compiler-api`), `REPOSITORY_SCAFFOLD.md` adds root `promptrig_core/`, master scope says CLI and hosted API "share the same Python compiler core". Root `README.md` also self-identifies as v0.3 inside the v0.4 corpus, and its precedence list omits `00-governance/STATUS_AND_DECISIONS.md` and `09-review-execution/`.
- **REV-CLAUDE-LOW-013** — `EvaluationResult` requires `baseline` unconditionally while PRD says baseline comparison applies "where applicable" and the IR has `baseline_required`; evaluation category vocabulary drifts (`format` vs "formatting"; IR `test_categories` are free strings unbound to the `EVALUATION_CASE` enum).
- **REV-CLAUDE-LOW-014** — `scripts/validate_review.py` enforces neither the `REV-<REVIEWER>-<SEVERITY>-NNN` ID convention (schema pattern accepts any `^REV-[A-Z0-9-]+$`) nor the run-manifest structure beyond top-level key presence, so the review process's own "no finding accepted until schema and evidence validate" gate is weaker than stated.

## Contradictions (summary)

1. Repair limit: 0–5 (IR) vs 0–2 (request/result/D-008/acceptance/master scope). *(HIGH-001)*
2. Jobs: deferred by baseline architecture vs mandated by API contract, UX spec, and threat model. *(HIGH-003)*
3. Idempotency: required by API contract vs optional/absent in schemas. *(MEDIUM-006)*
4. Tenant isolation: RLS-everywhere invariant vs unspecified service-plane DB access mode. *(HIGH-004)*
5. Managed credits: `STATUS_AND_DECISIONS.md` lists managed-credit billing as provisional/unconfirmed, while `PROMPTRIG_MASTER_SCOPE.md` puts "foundations for managed credits" inside MVP inclusions.
6. Compiler-core location and README release identity drift. *(MEDIUM-012)*
7. Baseline "where applicable" vs always-required. *(LOW-013)*

## Missing evidence

- No specification of compiler-api's database access mode or an RLS test harness design (needed to trust hard gates 14–15).
- No IR migration policy or worked example of a spec_version bump (freeze checklist item; RFC-001 open question).
- No capability key registry or sample provider manifest instance demonstrating cross-provider negotiation.
- No trace-correlation design tying `execution_traces` rows to `compilation_runs` (the DB model names both but defines no linkage).
- No sizing evidence that a Stage 1 build (18 hard gates including e2e, a11y, security suites) fits any agent's autonomous run budget — R-01 is asserted mitigated by "frozen MVP" but the MVP was not correspondingly cut.

## Assumptions rejected

1. **"Background jobs can be added later without contract change."** Rejected: the API contract, UX states, cancellation, and idempotency semantics already constitute a job model; only the mechanism is deferred, which is the cheap half.
2. **"RLS testing on every tenant table equals tenant isolation."** Rejected while the primary compute plane's DB credential mode is unspecified.
3. **"An untyped-but-required IR section still provides a portability guarantee."** Rejected: `additionalProperties:false` at the top level with open interiors validates shape, not meaning.
4. **"Four compilation levels belong in the MVP/benchmark because the compiler concept requires them."** Rejected as premature: levels 3–4 rest entirely on the untyped IR regions; they should be sequenced behind IR typing rather than benchmarked now.

## Proposed ADR/RFC/schema changes

1. **Amend ADR-006:** single ownership of repair budget (request-level), bounds 0–2 everywhere, precedence rule; align `PROMPTRIG_IR`, `COMPILATION_REQUEST`, `EVALUATION_RESULT`.
2. **New ADR — Execution model:** MVP implements job semantics on a Postgres job table inside the existing service (no external queue); add `jobs` (or extend `compilation_runs`) to `DATABASE_MODEL.md`; resolves Open Question 6 by threshold-free decision.
3. **New ADR — Tenant isolation enforcement:** name the enforcement point per table class; pin compiler-api DB access mode; require application-layer authz tests wherever RLS is bypassed.
4. **Amend RFC-002 + `PROVIDER_MANIFEST.schema.json`:** introduce a versioned capability key registry (enumerated keys with value semantics) in `packages/provider-sdk`.
5. **Amend `COMPILATION_RESULT.schema.json` + `TRACE_EVENT.schema.json`:** add `compilation_id`/`parent_id` correlation to trace events; make provenance an array or a trace-stream reference plus `compiler_version`; add optional `ir_refs` to `ARTIFACT_MANIFEST.schema.json`.
6. **Amend `PROMPTRIG_IR.schema.json`:** type `tools` and `output_contracts` for Benchmark 1; publish a minimal migration policy for `spec_version`; either type or explicitly mark-as-experimental the remaining open sections.
7. **Amend `PROMPTRIG_MASTER_SCOPE.md` / benchmark scope:** cut `application_specification` from Benchmark 1; move benchmark bookkeeping entities out of the product DB model into the benchmark runner; reconcile managed-credit language with STATUS_AND_DECISIONS.

## Validation plan

- **Schema coherence:** a CI script cross-checks numeric bounds and enum vocabularies shared across schemas (repair limits, categories, statuses); fails on divergence. Run against amended schemas.
- **Trace reconstruction test:** given a fake-provider compilation, assert every pipeline stage emits events reconstructible into one ordered chain keyed by `compilation_id`, and every artifact resolves to IR refs + compiler version.
- **Isolation test:** with the compiler-api's declared credential mode, execute cross-tenant direct-object-reference attempts through both write paths; both must fail closed; a test that passes only via the browser path is a gate failure.
- **Job semantics test:** kill the service mid-compile; on restart the compilation resumes or fails cleanly with resumable status; cancellation and duplicate idempotency keys behave per contract.
- **IR typing test:** an adversarial IR instance with garbage in `tools`/`output_contracts` must be *rejected* by the canonical schema; today it validates — that flip is the acceptance signal.
- **Scope-fit evidence:** one timed pilot run of Stage 1 scope against a single agent configuration before sealing the benchmark budget (validates R-01 mitigation empirically).

## Residual risks

- Supabase coupling (ADR-003) remains provisional; the isolation ADR above reduces but does not eliminate migration cost if Supabase Auth/Storage are replaced.
- Model-assisted vs deterministic stage boundaries in RFC-001 remain an open question; until answered, "compilation is reproducible" is aspirational.
- Benchmark Stage 1 may still exceed autonomous run capacity even after cuts; only the pilot run will tell.
- The synthesis phase (Phase E, selecting subsystems from multiple competitor codebases) carries licensing/provenance reconciliation risk acknowledged but not yet designed.

## Confidence and limitations

Overall confidence: **0.85**. High confidence on intra-corpus contradictions (directly cited, line-verified). Moderate confidence on the tenant-isolation finding: it flags an *unspecified* control, not an observed defect — the risk is that the specification permits the unsafe default, not that the unsafe default was chosen. This review covered the documentation corpus only; no production code exists to audit, and no external sources were consulted. The archive SHA-256 was taken from the corpus's own manifest records; this reviewer hashed the extracted tree's contents but not the original zip.
