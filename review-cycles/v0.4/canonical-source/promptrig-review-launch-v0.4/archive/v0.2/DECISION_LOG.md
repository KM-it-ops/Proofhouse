# PromptRig Decision Log

## D-001 — Product model
Commercial-first hosted cloud plus open-source Core companion. Full open-source release remains a fallback, not the initial assumption.

## D-002 — Primary audience
Nontechnical users by default; Developer Mode reveals advanced controls for the same project.

## D-003 — Application architecture
Next.js web application plus FastAPI compiler/evaluation service in a monorepo.

## D-004 — Hosted data platform
Supabase for MVP Postgres, authentication, and storage. Core compiler remains platform-independent.

## D-005 — Benchmark design
Three stages: Core Production Build, Provider Expansion, Product Scenario. Multiple independent runs and autonomous/steered reporting are required.

## D-006 — Benchmark unit
Evaluate model + harness + tools + permissions + environment + instructions, not model labels alone.

## D-007 — Source of truth
Repository specifications and schemas supersede chat history.

## D-008 — Repair policy
Bounded repair only; default one pass, configurable zero to two.

## Open decisions

- final open-source licenses
- mandatory Benchmark 1 provider pair
- managed-credit provider and pricing strategy
- background job platform after synchronous MVP threshold is exceeded
- public benchmark run budget and number of repetitions
