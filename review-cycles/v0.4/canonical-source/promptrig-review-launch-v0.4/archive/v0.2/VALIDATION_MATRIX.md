# Validation Matrix

| Requirement area | Public test | Hidden test | Human review | Evidence |
|---|---|---|---|---|
| IR/schema validity | yes | yes | no | test report |
| provider conformance | yes | yes | optional | traces/results |
| Simple Mode completion | yes | yes | yes | e2e/video |
| Developer Mode parity | yes | yes | yes | e2e/diff |
| bounded repair | yes | yes | no | trace |
| tenant isolation | yes | yes | security review | test report |
| prompt injection | yes | yes | security review | results |
| export integrity | yes | yes | optional | hash manifest |
| accessibility | yes | limited | yes | audit |
| cost and latency | instrumentation | aggregation | no | telemetry |
