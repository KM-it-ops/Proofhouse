# Compiler pass architecture

Each pass accepts an immutable compilation state and returns a new state plus zero or more diagnostics. Passes have stable names and ordered trace entries.

1. **Normalization** — canonicalize Unicode, ordering, identifiers, and schema representations without changing meaning. Output: canonical IR candidate and source map.
2. **Validation** — validate the strict IR schema and semantic rules. Output: validated IR or error diagnostics. No later pass runs on error.
3. **Optimization** — perform deterministic, provably intent-preserving simplifications such as duplicate optional tag removal. v0.1 MAY be a traced no-op.
4. **Capability Resolution** — compare required/optional IR capabilities with the selected versioned manifest. Required gaps are errors; optional gaps are recorded warnings.
5. **Safety** — enforce declared permissions, data handling, tool approval, and policy conflicts. Safety rules never weaken user constraints.
6. **Adapter Lowering** — produce provider-specific artifacts from validated canonical IR and resolved capabilities. It cannot mutate IR or bypass prior diagnostics.

The pipeline MUST expose per-pass input/output digests and duration as non-semantic telemetry. Model-assisted passes are excluded from v0.1; introducing one requires a new contract defining sampling, provenance, replay, and failure semantics.
