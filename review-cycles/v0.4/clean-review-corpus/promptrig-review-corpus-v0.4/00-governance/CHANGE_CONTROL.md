# PromptRig Change-Control Policy

## Before benchmark freeze

Changes may be accepted through a documented proposal containing rationale, affected requirements, schema impact, tests, migration plan, and benchmark fairness impact.

## After benchmark freeze

Normative requirements, scoring, hidden-test interfaces, and environment limits may not change for active runs. Critical defects require:

1. pause all competitors
2. publish the defect and proposed correction
3. reset every competitor from the same corrected commit
4. increment the benchmark specification version

## Agent behavior

Coding agents may file ambiguities in `OPEN_QUESTIONS.md`; they may not silently weaken requirements. When blocked, they must implement the safest reversible interpretation and document it.
