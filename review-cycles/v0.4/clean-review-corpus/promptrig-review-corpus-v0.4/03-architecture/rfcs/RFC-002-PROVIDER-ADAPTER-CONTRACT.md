# RFC-002 — Provider Adapter Contract

**Status:** Review

A provider adapter consumes validated PromptRig IR plus a versioned provider capability manifest and returns provider-specific artifacts, diagnostics, test fixtures, and provenance.

## Required behavior

- Capability negotiation
- Exact model and API surface identification
- Structured-output mapping
- Tool/function schema mapping
- Context and token-budget planning
- Safety and approval mapping
- Deterministic fake-provider conformance mode
- Explicit unsupported-feature diagnostics
- Versioned source references

Adapters must pass shared conformance tests before provider-specific quality tests. Provider documentation is versioned data, not embedded folklore inside prompts.
