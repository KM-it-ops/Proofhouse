# Hidden-Test Interface Contract

Competitor implementations must expose stable commands without seeing hidden test contents.

## Required commands

- `make setup`
- `make dev`
- `make test`
- `make test-unit`
- `make test-integration`
- `make test-e2e`
- `make lint`
- `make typecheck`
- `make security`
- `make benchmark-fixture`
- `make export-example`

Equivalent cross-platform scripts may wrap these targets, but the targets must exist in the benchmark container.

## Required service probes

- web health endpoint
- compiler API health endpoint
- database migration status
- provider adapter registry

## Required fixtures

- seeded user and tenant
- valid sample PromptRig request
- invalid IR samples
- deterministic fake provider
- deterministic evaluator
- export verification fixture

Hidden tests may exercise public APIs, CLI commands, database authorization, malformed inputs, idempotency, retries, cancellation, export validation, and prompt-injection boundaries.
