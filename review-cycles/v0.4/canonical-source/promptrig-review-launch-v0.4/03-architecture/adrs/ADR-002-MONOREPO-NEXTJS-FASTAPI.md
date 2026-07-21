# ADR-002-MONOREPO-NEXTJS-FASTAPI — Next.js and FastAPI Monorepo

**Status:** Accepted

## Context

The hosted UX benefits from TypeScript while the compiler, evaluation, and research ecosystem benefit from Python.

## Decision

Use Next.js for the product interface and FastAPI for the compiler/evaluation service, with generated contracts in a monorepo.

## Consequences

Two runtimes increase integration complexity; contract generation and conformance tests are required.

## Review trigger

Revisit when evidence materially changes the tradeoff, not merely because an implementer prefers another stack.
