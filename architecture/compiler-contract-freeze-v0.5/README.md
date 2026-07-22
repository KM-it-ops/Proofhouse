# Compiler Contract Freeze v0.5

**Status:** Freeze candidate — implementation is not authorized until the acceptance gates in this package are approved.  
**Prepared:** 2026-07-21

This package converts the v0.4 review evidence into a coherent Compiler Core v0.1 contract boundary. It does not implement the compiler, modify historical review evidence, or declare the broader hosted product and benchmark architecture frozen.

## Normative candidate contracts

- [Compiler contracts](COMPILER_CONTRACTS.md)
- [Compiler invariants](COMPILER_INVARIANTS.md)
- [PromptRig IR v0.1 schema](PROMPTRIG_IR_V0_1.schema.json)
- [Diagnostic schema](DIAGNOSTIC_CONTRACT.schema.json)
- [Provider adapter contract](PROVIDER_ADAPTER_CONTRACT.md)
- [Library and CLI contract](LIBRARY_CLI_CONTRACT.md)
- [Compatibility promise](COMPATIBILITY_PROMISE.md)
- [Compiler pass architecture](COMPILER_PASS_ARCHITECTURE.md)

## Evidence and decisions

- [Review synthesis](REVIEW_SYNTHESIS.md)
- [Findings matrix](FINDINGS_MATRIX.json)
- [Decision log](DECISION_LOG.md)
- [Open questions](OPEN_QUESTIONS.md)
- [Language/platform decision](LANGUAGE_PLATFORM_DECISION.md)
- [Provider selection](PROVIDER_SELECTION_MATRIX.md)

## Execution planning

- [First vertical slice](VERTICAL_SLICE_V0_1.md)
- [Implementation sequence](IMPLEMENTATION_SEQUENCE.md)
- [Library/CLI parity matrix](LIBRARY_CLI_PARITY_MATRIX.json)

The package freezes only after schema meta-validation, contract fixture tests, owner acceptance of candidate decisions, and closure or explicit deferral of every blocking open question.
