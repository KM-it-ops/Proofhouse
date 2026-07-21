# Universal Coding-Agent Master Build Prompt

You are one competitor in the PromptRig Build-Off. Build the PromptRig MVP end to end from the attached frozen repository specification.

## Authority

Read and follow the source-of-truth order in `README.md`. Do not use chat history or assumptions to override repository requirements. When documents conflict, follow the higher-priority document and record the conflict.

## Required method

1. Inspect the entire repository and validate the environment.
2. Create `IMPLEMENTATION_PLAN.md` mapping every acceptance criterion to code and tests.
3. Implement milestones in dependency order.
4. Keep the canonical PromptRig IR and generated contracts as the semantic source of truth.
5. Build the headless compiler and CLI before depending on the hosted UI.
6. Implement one complete vertical slice before broadening features.
7. Implement the two frozen Benchmark 1 provider adapters through the shared adapter contract.
8. Implement Simple Mode and Developer Mode over the same versioned project state.
9. Add deterministic validation, baseline evaluation, bounded repair, provenance, and export.
10. Add authentication, tenant authorization, credential protection, and security tests.
11. Run all required checks from a clean environment.
12. Produce a sealed evidence package and submission manifest.

## Constraints

- Do not weaken requirements to make tests pass.
- Do not expose or seek hidden tests.
- Do not inspect competitor branches or submissions.
- Do not claim commands or tests were run unless they completed and evidence exists.
- Do not place secrets in code, logs, prompts, traces, screenshots, or exports.
- Do not introduce unbounded retries or agent loops.
- Do not perform external publication, purchases, production deployment, or destructive actions.
- Prefer working software and verified vertical slices over decorative breadth.

## Completion report

Produce `FINAL_EVIDENCE_REPORT.md` containing:

- implemented scope
- architecture summary
- acceptance-criterion matrix
- exact test/build commands and outcomes
- unresolved defects
- security findings
- model/harness/environment metadata
- cost and duration summary
- artifact hashes
- instructions for clean reproduction

Then generate `submission-manifest.json` conforming to the canonical schema.
