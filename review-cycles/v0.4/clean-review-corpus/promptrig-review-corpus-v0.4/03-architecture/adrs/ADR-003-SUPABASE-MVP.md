# ADR-003-SUPABASE-MVP — Supabase for MVP Platform Services

**Status:** Provisional

## Context

It reduces the number of infrastructure services required for an early multi-tenant SaaS.

## Decision

Use Supabase for MVP Postgres, authentication, storage, and realtime features, subject to review of portability and benchmark isolation.

## Consequences

Avoid business logic that depends irreversibly on proprietary platform behavior.

## Review trigger

Revisit when evidence materially changes the tradeoff, not merely because an implementer prefers another stack.
