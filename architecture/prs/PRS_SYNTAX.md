# PRS syntax proposals

**Status:** Non-binding proposal; no syntax is frozen.

Candidate properties:

- UTF-8, line-oriented, deterministic parsing.
- Explicit version declaration and stable identifiers.
- Named sections for objective, inputs, outputs, constraints, tools, policy, providers, and evaluation.
- No embedded arbitrary executable code.
- Source locations preserved into IR provenance and diagnostics.
- Unknown keys are errors unless a versioned extension namespace declares them.

Grammar, escaping, imports, macros, and extension semantics remain `UNKNOWN` pending post-v0.1 design work.
