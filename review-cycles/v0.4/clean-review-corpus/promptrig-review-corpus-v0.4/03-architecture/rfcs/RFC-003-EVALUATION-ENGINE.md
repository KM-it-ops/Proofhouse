# RFC-003 — Evaluation Engine

**Status:** Review

The evaluation engine supports deterministic validators, executable tests, model-based judges, human review, and adversarial cases. It records evaluator identity, rubric version, inputs, outputs, cost, latency, and confidence.

## Guardrails

- Model judges cannot be the sole authority for schema validity, security boundaries, or executable correctness.
- Hidden benchmark tests remain inaccessible to competitors.
- Candidate generation and judging should use separated contexts where feasible.
- Repair attempts are bounded and regression-tested.
- Evaluation datasets are versioned and contamination risks documented.
