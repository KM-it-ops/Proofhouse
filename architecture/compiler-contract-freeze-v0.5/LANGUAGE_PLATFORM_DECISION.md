# Language and platform decision

**Status:** Recommended for owner acceptance  
**Assessed:** 2026-07-21

## Context

PromptRig already ships a Python package and CLI, while the accepted broader architecture includes a TypeScript/Next.js web surface and generated cross-language contracts. Compiler Core v0.1 needs strict schemas, deterministic offline behavior, cross-platform installation, and one implementation shared by library and CLI.

## Comparison

| Criterion | Python | TypeScript | Hybrid |
|---|---|---|---|
| Type safety | Strong with strict typing, but runtime validation is separate | Strong structural compile-time typing | Strong at each boundary if contracts are generated |
| JSON Schema tooling | Mature runtime validators and Pydantic schema support | Strong validators and excellent typed consumer ergonomics | Best coverage, with generation drift risk |
| CLI/library distribution | Mature `pyproject.toml` scripts and wheels | Mature npm packages and `bin` commands | Two release systems and higher operational cost |
| Provider SDK maturity | First-class across OpenAI, Anthropic, Gemini | First-class across all three | Broadest access but duplicates integration paths |
| Offline deterministic validation | Excellent | Excellent | Excellent if one runtime remains authoritative |
| Existing PromptRig fit | Native: current package, tests, and CLI are Python | Would replace or bridge the current core | Preserves current core and future web consumers |
| Cross-platform | Strong on Windows/Linux/macOS | Strong on Windows/Linux/macOS | Strong, with a larger installation surface |
| Long-term maintainability | Best for compiler/eval-oriented core | Best for shared web/server implementation | Best strategic boundary when code generation is controlled |

Python packaging formally supports CLI entry points through `[project.scripts]` ([Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)). TypeScript can publish declaration files with packages ([TypeScript publishing guidance](https://www.typescriptlang.org/docs/handbook/declaration-files/publishing.html)), making it suitable for generated consumer contracts without making Node a v0.1 compiler dependency.

## Decision

Use **Python 3.11+** as the authoritative Compiler Core v0.1 runtime and CLI. Generate JSON Schema and TypeScript declaration/types as artifacts for web and SDK consumers. Do not implement compiler logic in TypeScript. Keep provider adapters in Python for v0.1 so the public library, CLI, fake adapter, and live adapters share one execution path.

This is a controlled hybrid architecture: Python owns semantics; language-neutral JSON Schema owns interchange; TypeScript consumes generated contracts. Generated outputs MUST be reproducible and drift-tested against the source schemas.

## Rejected alternatives

- **TypeScript-only now:** strong typing and web alignment do not justify replacing the existing Python library/CLI before the compiler boundary is proven.
- **Two authoritative cores:** violates the no-duplicated-logic and parity requirements.
- **FastAPI service in the first slice:** hosted transport is deferred; the library contract comes first.

## Revisit triggers

Revisit after the offline vertical slice if Python packaging fails cross-platform installation gates, generated TypeScript contracts cannot represent required semantics, or measured adapter SDK limitations block a mandatory provider.
