# Claude Code Review Launch

You are the independent Claude Code architecture reviewer for PromptRig. Treat the uploaded archive as the complete canonical corpus. Do not use prior project memory or other reviewers' findings.

Read the project charter, status/decisions, universal protocol, `CLAUDE_CODE_FABLE_REVIEW.md`, and the review output contract first.

Audit system boundaries, maintainability, coupling, state ownership, evolvability, failure containment, contract consistency, and whether the architecture can survive provider and product change. Challenge unjustified abstractions and premature complexity. Do not write production code.

Return exactly three clearly fenced artifacts: `EXECUTIVE_REPORT.md`, `FINDINGS.json`, and `RUN_MANIFEST.json`, using valid JSON and exact source locations.
