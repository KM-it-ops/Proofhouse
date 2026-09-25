# Product scope

Decided 2026-09-21 (see [decision 0001](decisions/0001-local-first-evidence-workspace.md)).

## What Proofhouse is

**A local workspace for building, revising and testing prompts with evidence you can trace.** You take one objective through requirements, a prompt, recorded model output, checks, revision, comparison and export, without losing a constraint and without mistaking a structural check for a quality judgement.

- **First audience:** developers and technical operators who maintain recurring prompts, especially security-adjacent ones. This is where the project starts, not a claim about every possible user.
- **Flagship case:** summarising a (synthetic) security advisory while keeping the uncertainty, evidence and format requirements. It ships as [`examples/reference-advisory/`](../examples/reference-advisory/) and runs end to end with [`scripts/reference_workflow.py`](../scripts/reference_workflow.py).
- **Shape:** the Python library and CLI own the records and the behavior. The Cursor skill is a conversational way in. Any future interface calls the same services. Provider calls stay optional and need explicit opt-in; imported outputs keep the whole workflow usable without credentials.

## The supported journey

```text
optimize new -> answer the clarify packet -> optimize compile
  -> constraints (seeded from your answers; add, link to checks)
  -> criteria add (prompt text or recorded outputs)
  -> optimize record (revision N) -> optimize output add (what a model returned)
  -> optimize check -> optimize revise (packet keeps answers + constraints) -> record N+1
  -> optimize compare -> optimize report -> optimize export / import
```

Every step is offline. The walk-through is [reference-workflow.md](reference-workflow.md).

## Completion criteria

These are the acceptance criteria this work is measured against, frozen from the improvement plan:

1. Mandatory requirements reach the actual execution context or prevent execution with an actionable explanation.
2. Evaluation cannot silently ignore duplicate IDs, failed cases, missing requirement coverage, stale revisions, or changed criteria.
3. Every outcome records exactly what was tested: revision, outputs, dataset, rubric, grader, model/configuration where relevant, and provenance.
4. Structural validation, recorded-observation checks, human judgements, and measured model-output results are visibly distinct.
5. All review reproductions have regression coverage; no unresolved high-priority defect remains in the promoted surface.
6. A fresh user completes the reference workflow and can reopen its evidence without developer assistance.
7. A failed installation/update preserves the user's existing data and configuration.
8. Model profile claims have sources or are clearly labeled unverified/user-supplied; optional efficiency advice cannot weaken mandatory gates.
9. The supported interface passes applicable functional, keyboard, responsive-layout, and error-recovery checks.
10. Release documentation, screenshots, installation instructions, and claims correspond to the exact released revision.

The current status of each is in the latest [assurance statement](assurance/).

## What waits

Sequencing, not deletion. Each needs its own scope decision and acceptance gates:

- Hosted multi-tenancy, accounts, billing, remote execution. The hosted slice has no tenant isolation.
- More providers before one execution path preserves all required semantics.
- Autonomous model research without provenance and review.
- "Best prompt", universal quality, or savings claims without controlled evaluation evidence.
- A visual redesign of the dashboard prototype before the workflow it would show is sound.
