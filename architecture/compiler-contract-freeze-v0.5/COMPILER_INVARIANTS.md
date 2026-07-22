# Compiler invariants

1. Canonical IR is the sole semantic source of truth after normalization.
2. Validation completes before optimization, capability resolution, safety, or lowering.
3. Every pass is independently invocable and testable through the library's internal pass protocol.
4. Pass outputs are new immutable values; input IR is never mutated.
5. Optimization preserves objective, requirements, contracts, constraints, policies, and required capabilities.
6. Lowering never mutates canonical IR and never silently discards semantics.
7. Unsupported mandatory semantics produce an error diagnostic.
8. Diagnostics are append-only immutable values with stable codes and source paths.
9. Identical offline inputs produce identical semantic outputs and digests.
10. Every artifact and diagnostic traces to IR paths, compiler version, adapter version, and capability-manifest digest.
11. Credentials never enter canonical IR, diagnostics, traces, or artifacts.
12. Provider-specific semantics stay behind the adapter boundary unless they change requested meaning, in which case the IR must represent them explicitly.
13. A CLI command calls the same public library operation as its programmatic equivalent.
14. A failed validation or safety pass prevents adapter lowering.
15. User intent is never changed to improve a score, reduce cost, or satisfy a provider.
