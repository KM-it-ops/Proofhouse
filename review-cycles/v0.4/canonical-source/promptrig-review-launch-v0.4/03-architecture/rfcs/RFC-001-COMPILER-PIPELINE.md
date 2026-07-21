# RFC-001 — Compiler Pipeline

**Status:** Review

## Proposed stages

1. Intake normalization
2. Requirement extraction
3. Ambiguity and conflict detection
4. IR construction
5. Policy and capability resolution
6. Provider-specific lowering
7. Artifact generation
8. Static validation
9. Evaluation execution
10. Bounded repair
11. Evidence packaging and export

## Invariants

- Every artifact traces back to IR fields and compiler version.
- Provider lowering may specialize behavior but cannot silently weaken mandatory requirements.
- Unsupported capabilities produce explicit diagnostics and documented fallbacks.
- Repair never mutates the accepted objective or safety policy merely to improve a score.
- Compilation is reproducible when model sampling and external retrieval are disabled or pinned.

## Open review questions

- Which stages are deterministic versus model-assisted?
- What is the minimum viable migration policy for IR schema upgrades?
- How are retrieved sources hashed and preserved?
- Which policy conflicts require human approval?
