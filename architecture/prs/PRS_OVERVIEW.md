# PromptRig Specification overview

**Status:** Documentation only; deferred until after Compiler Core v0.1.

PromptRig Specification (PRS) is a proposed human-readable declarative source language for expressing user intent, contracts, policies, tools, evaluation requirements, and provider constraints. A future front end may parse PRS and compile it into canonical PromptRig IR.

PRS is not the IR. The IR is the versioned semantic contract; PRS is one possible source representation. Unsupported PRS semantics must produce diagnostics and must never be silently discarded.

See [ADR-001](../adr/ADR-001-PromptRig-Specification.md), [syntax proposals](PRS_SYNTAX.md), [examples](PRS_EXAMPLES.md), and the [roadmap](PRS_ROADMAP.md).
