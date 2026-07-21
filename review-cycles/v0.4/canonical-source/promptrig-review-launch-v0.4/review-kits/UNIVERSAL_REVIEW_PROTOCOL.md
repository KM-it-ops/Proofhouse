# Universal Review Protocol

You are reviewing PromptRig before production implementation. Do not rewrite the product from personal preference. Identify concrete conflicts, inaccuracies, missing requirements, unsafe assumptions, untestable claims, unnecessary complexity, and likely implementation failures.

## Required method

1. Read the source hierarchy and accepted decisions.
2. Build a requirement-to-architecture traceability map.
3. Test each major workflow against failure, security, cost, portability, and operability scenarios.
4. Distinguish fact, inference, preference, and unknown.
5. Cite the exact document and section for every finding.
6. Propose the smallest correction that resolves the root cause.
7. Provide a validation test for each recommendation.

## Output schema

Return: executive verdict; blocking findings; nonblocking findings; contradictions; missing evidence; rejected assumptions; proposed ADR/RFC changes; validation plan; residual risk; confidence.

Do not expose private chain-of-thought. Provide concise rationale and inspectable evidence.
