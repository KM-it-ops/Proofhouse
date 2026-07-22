# Decision log

| ID | Decision | Status | Evidence |
|---|---|---|---|
| D-050-001 | Freeze only the Compiler Core v0.1 boundary, not the hosted product or benchmark architecture. | Accepted | Review synthesis; unresolved benchmark and tenant findings; OAR-001 |
| D-050-002 | Use strict PromptRig IR v0.1 with no unknown fields and no duplicate semantic owners. | Accepted | Claude/Codex/Gemini IR findings; OAR-001 |
| D-050-003 | Set repair limit to 0–2 in IR; repair execution remains out of v0.1. | Accepted | Accepted v0.4 intent and cross-schema contradiction findings; OAR-001 |
| D-050-004 | Use Python 3.11+ for Compiler Core and CLI; generate TypeScript contracts for consumers. | Accepted | Existing package, platform matrix, cross-platform goals; OAR-001 |
| D-050-005 | Keep all v0.1 compiler passes deterministic and offline. | Accepted | Reproducibility and benchmark findings; OAR-001 |
| D-050-006 | Make OpenAI the first live adapter target, Anthropic the second conformance target, Gemini the third. | Accepted | Provider matrix and strategic validation breadth; OAR-001 |
| D-050-007 | CLI wraps the same public library and returns stable JSON envelopes and exit codes. | Accepted | Mission requirement; parity contract; OAR-001 |
| D-050-008 | Preserve historical review artifacts byte-for-byte. | Accepted | Architect Mode law and mission policy |

OAR-001 is the owner acceptance record. The accepted decisions are binding for Compiler Core v0.1; deferred product-surface questions remain outside this freeze.
