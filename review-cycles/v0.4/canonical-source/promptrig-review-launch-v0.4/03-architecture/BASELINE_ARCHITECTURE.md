# PromptRig Architecture v0.1

## System Shape

- `apps/web`: Next.js user interface
- `services/compiler-api`: FastAPI compiler/evaluation service
- `packages/contracts`: generated TypeScript/Python contracts
- `packages/ui`: reusable UI components
- `packages/provider-sdk`: provider adapter contracts
- `providers/*`: provider packs
- `cli`: local PromptRig CLI
- `evals`: test sets, rubrics, conformance suites
- `docs`: product and engineering documentation

## Primary Engines

1. Requirements Compiler
2. PromptRig IR
3. Capability and Policy Engine
4. Provider Compilers
5. Evaluation and Repair Engine
6. Artifact Generator

## Data Flow

User intent -> normalized requirements -> PromptRig IR -> policy/capability resolution -> provider-specific IR -> generated artifacts -> validation -> execution tests -> bounded repair -> final package.

## Architectural Constraints

- The IR is the source of truth.
- UI forms may edit the IR but may not introduce hidden configuration.
- Provider adapters must implement a shared interface.
- Provider-specific behavior must remain outside the core semantic IR unless it changes the requested meaning.
- Evaluation must be independently runnable from the UI.
- Local CLI and hosted service must share compiler logic.
- Cross-service contracts are generated, not manually duplicated.

## Suggested Initial Technology

- Next.js, TypeScript, React
- FastAPI, Python, Pydantic
- JSON Schema and OpenAPI
- Supabase Postgres/Auth/Storage
- Background jobs introduced only when synchronous execution becomes inadequate
- Containerized benchmark environment
