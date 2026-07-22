# Open questions

## Ratified Compiler Core v0.1 decisions

The five blocking questions are resolved by [OAR-001](../OWNER_ACCEPTANCE_RECORDS/OAR-001.md), ratified by the Project Owner on 2026-07-21. They are binding for Compiler Core v0.1:

- Python 3.11+ is authoritative, with generated TypeScript boundary contracts.
- Adapter order is deterministic fake adapter → OpenAI → Anthropic → Gemini.
- PromptRig IR 0.1.0 is the first frozen public contract; historical 0.2.0 is noncanonical prototype history.
- Canonical hashing uses RFC 8785-style JCS, UTF-8, SHA-256, duplicate-key rejection, no implicit Unicode normalization, and lone-surrogate rejection.
- Diagnostic codes use the central immutable registry and are never reused.

## Explicitly deferred, non-blocking for the offline vertical slice

- Live execution, evaluation, and repair contracts.
- Hosted job lifecycle and durable idempotency storage.
- Tenant authorization, credential vault, retention, and deletion contracts.
- Benchmark budgets, sealed environments, repetitions, and network policy.
- UI mode mapping, compilation-level disclosure, tool consent, accessibility, and model-grade confidence display.
- PRS grammar and MissionRig implementation.

Deferred items block their respective product surfaces and must not be presented as solved by Compiler Core v0.1.
