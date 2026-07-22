# Open questions

## Blocking Compiler Core v0.1 freeze

1. Does the owner accept Python 3.11+ as the core runtime with generated TypeScript boundary contracts?
2. Does the owner accept OpenAI → Anthropic → Gemini as adapter implementation order?
3. Is `0.1.0` the accepted new IR version despite the historical prototype using `0.2.0`, or should the new contract be numbered `0.3.0` to avoid perceived regression?
4. Which canonicalization profile defines JSON number handling and Unicode normalization for digests?
5. Which diagnostic-code registry process reserves and retires codes?

## Explicitly deferred, non-blocking for the offline vertical slice

- Live execution, evaluation, and repair contracts.
- Hosted job lifecycle and durable idempotency storage.
- Tenant authorization, credential vault, retention, and deletion contracts.
- Benchmark budgets, sealed environments, repetitions, and network policy.
- UI mode mapping, compilation-level disclosure, tool consent, accessibility, and model-grade confidence display.
- PRS grammar and MissionRig implementation.

Deferred items block their respective product surfaces and must not be presented as solved by Compiler Core v0.1.
