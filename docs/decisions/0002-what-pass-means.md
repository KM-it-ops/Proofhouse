# 0002: What a PASS means

Accepted 2026-09-21.

## Decision

`optimize check` reports a revision as `PASS` only when:

1. every declared criterion is `PASS` — `UNJUDGED` (a manual criterion without a bound verdict) and `NOT_EVALUATED` (an output criterion with no recorded output) are not passes; and
2. every **accepted** constraint is `satisfied`, meaning it is linked to at least one criterion and all linked criteria passed. A constraint with no linked criterion has `no_evidence`.

Every input to that decision is bound by digest: the revision's prompt, each recorded output, each criterion definition, and each human verdict (which applies only to the exact revision/output and criterion it judged). Edited material fails to load or turns a verdict stale; it is never evaluated as the original.

Each result is labeled with its evidence class — prompt-text check, recorded-output check, or human judgement — and reports say what they do not measure.

## Why

Before this, a manual PASS kept counting after the prompt it approved was edited, and nothing connected the requirements a user gave to the checks that claimed to test them. A PASS that users read as "my requirements are met" has to be built from evidence for each requirement.

## Consequences

- Clarification answers become accepted constraints at compile time, so a case with answers but no linked checks does not pass. That is intentional: link a check (`optimize constraints link`) or record a human verdict.
- The closed-loop compiler path keeps its structural meaning; its evidence bundle lists `evidence_classes` and `not_measured` so a structural PASS is not read as a quality result.
