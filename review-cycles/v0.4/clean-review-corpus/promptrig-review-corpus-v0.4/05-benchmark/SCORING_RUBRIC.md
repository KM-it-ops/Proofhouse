# PromptRig Build-Off Scoring Rubric

## Hard gates

Hard gates in `ACCEPTANCE_CRITERIA.md` are reported separately from weighted quality. A submission failing a critical security or isolation gate cannot be labeled production-ready regardless of score.

## Weighted score

| Dimension | Weight |
|---|---:|
| Functional correctness | 25 |
| Compiler and IR quality | 15 |
| Evaluation reliability | 12 |
| Nontechnical UX | 10 |
| Developer UX | 5 |
| Security and privacy | 10 |
| Code quality and maintainability | 7 |
| Provider adapter quality | 6 |
| Test quality | 5 |
| Performance and cost | 3 |
| Documentation and reproducibility | 2 |

## Scoring sources

1. deterministic hidden and public tests
2. static analysis and schema validation
3. recorded product scenario
4. blind human review
5. cost and runtime telemetry

## Reporting

Report autonomous and steered results separately. For repeated runs report median, best, worst, variance, completion rate, intervention count, and total cost. Never collapse an infrastructure failure into a functional failure without labeling it.
