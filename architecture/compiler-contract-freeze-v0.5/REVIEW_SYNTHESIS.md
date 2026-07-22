# Review synthesis

## Evidence set

This synthesis uses the immutable v0.4 canonical corpus and the complete saved outputs from Claude Code, Codex, and Gemini under `review-cycles/v0.4/review-results/round-1/`. Kimi produced no saved findings. The evidence set contains 33 findings: 2 critical, 16 high, 12 medium, and 3 low.

## Convergent findings

1. **Canonical semantics were under-specified.** All reviewers found IR fields, mode ownership, repair bounds, or user-facing schema semantics that could validate while failing intended behavior.
2. **Execution contracts were prose, not executable boundaries.** Job lifecycle, provider negotiation, multi-provider failure, provenance, diagnostics, and idempotency lacked testable shapes.
3. **Traceability was insufficient.** Requirements did not map to contracts and executable tests, and run manifests could not seal claimed evidence.
4. **Hosted-product and benchmark concerns were mixed into Compiler Core.** Tenant isolation, benchmark bookkeeping, deployment, and UI flows need separate contracts rather than expanding the first compiler slice.
5. **User intent needed explicit preservation rules.** Provider lowering, repair, mode selection, compilation-level selection, and tool execution could not silently reinterpret intent.

## Resolution strategy

The v0.5 candidate narrows Compiler Core v0.1 to deterministic, offline, library-first compilation and inspection. It provides strict IR and diagnostic schemas, six independently testable passes, an adapter boundary, stable CLI behavior, and traceability requirements. It explicitly excludes network execution, hosted jobs, tenant data, billing, UI workflows, benchmark launch, model grading, and automated repair from the first slice.

This resolves the contract boundary without pretending the entire v0.4 product architecture is frozen. Benchmark comparability, hosted job infrastructure, identity/storage boundaries, and nontechnical UX remain open or deferred. Their findings are retained in [FINDINGS_MATRIX.json](FINDINGS_MATRIX.json).

## Freeze recommendation

Approve this package as the **Compiler Core v0.1 contract baseline** only after:

- owner acceptance of the language and provider decisions;
- test fixtures prove strict invalid/valid behavior for both schemas;
- CLI exit-code and JSON-envelope golden tests exist;
- fake-adapter conformance and library/CLI parity tests exist; and
- blocking items in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) are closed or explicitly deferred by an owner.

Do not use this approval to claim benchmark-launch readiness or hosted-product architecture freeze.
