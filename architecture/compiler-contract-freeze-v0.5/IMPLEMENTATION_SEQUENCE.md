# Implementation sequence

1. Accept the v0.5 candidate decisions and freeze schema fixtures.
2. Create immutable contract types, canonical JSON hashing, diagnostic registry, and source-path helpers.
3. Implement normalization and strict validation with adversarial valid/invalid fixtures.
4. Implement pass protocol, traced no-op optimization, and pipeline stop rules.
5. Implement versioned capability manifests and the deterministic fake adapter.
6. Implement safety checks and fake-adapter lowering.
7. Expose the public library operations.
8. Wrap those operations with the CLI and golden JSON/exit-code tests.
9. Add cross-platform installation and reproducibility tests.
10. Independently review the vertical slice before any live adapter work.

Live OpenAI adapter work follows only after the fake-adapter conformance suite passes. Anthropic is the second required conformance target; Gemini follows before any multi-provider completeness claim.
