# 0001: A local-first prompt revision and evidence workspace

Accepted 2026-09-21 by the maintainer, following an adversarial review of revision `78e512c`.

## Decision

Proofhouse's product is a local workspace in which one objective moves through requirements, a prompt, recorded model output, checks, revision, comparison and export, with every result tied to the exact material it evaluated. The Python library and CLI own the records; the Cursor skill is an entry point; any interface calls the same services. Provider calls are optional and opt-in, and imported outputs keep the workflow usable offline.

## Why

The review found a solid engineering base whose evidence could not yet support its strongest promise: a PASS could survive a changed prompt, ignore an uncovered requirement, or be produced by a duplicate case id, and a live request could drop requirements its artifact still held. The most useful product is the one that makes a PASS mean exactly what a user thinks it means. That is achievable locally, without a hosted service.

## Consequences

- Correctness of the evidence comes before interface work, provider breadth, and hosted features.
- The dashboard prototype stays a prototype until it shows this workflow's real records.
- Public claims are limited to what the reference workflow demonstrates; no quality, "best prompt" or savings claims without controlled evidence.
