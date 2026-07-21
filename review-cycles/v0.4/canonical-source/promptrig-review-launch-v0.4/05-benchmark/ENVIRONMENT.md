# Benchmark Environment

## Fairness requirements

Every competitor starts from the same commit, container image, database seed, documentation snapshot, resource limits, network policy, secrets policy, and time budget.

## Required recorded metadata

- benchmark specification version
- starter commit SHA
- competitor branch
- harness name and version
- requested model and reasoning settings
- observed provider/model identifier when available
- operating system and container digest
- CPU, memory, disk, and wall-clock limits
- network policy
- tool permissions
- environment variables by name only, never secret value
- timestamps
- token usage, provider cost, and tool-call count
- interventions and infrastructure incidents

## Workspace isolation

- separate branch/worktree
- separate database or database branch
- separate storage namespace
- separate trace namespace
- no access to other submissions or hidden tests

## Network modes

### Frozen mode
No public internet. Official documentation is supplied in the frozen source snapshot.

### Research mode
Optional secondary track. Internet access is logged, sources are captured, and results are not merged with Frozen-mode scores.

## Repetition

Run at least three independent autonomous attempts per competitor for the published benchmark unless the final frozen budget explicitly states otherwise. Report median, range, failures, cost, and duration.
