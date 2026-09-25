# 0005: Live requests carry every mandatory IR field, or refuse

Accepted 2026-09-21.

## Decision

`execute-openai` builds its system message from `compiler/runtime_context.py`, where every top-level IR field has one explicit disposition:

| Disposition | Fields |
|---|---|
| rendered into the system message | objective (goal, users, success and failure criteria), requirements (id, mandatory flag, priority, acceptance), instructions, constraints, uncertainty and evidence policies, input contracts, workflow, autonomy, memory mode, assumptions, open questions |
| enforced by a request parameter | output contract (`response_format`), tools |
| enforced by the compiler | provider capability requirements |
| metadata only | spec version, project, evaluation config, deployment, provenance |
| unsupported → refuse before sending (`EXE-SEM-0001`) | required knowledge sources (no content available), persistent memory |

Security and privacy policy blocks are free text the compiler cannot enforce; compilation already fails closed on them (`PRG-SAFETY-0001`), so nothing is sent. A new IR field without a disposition fails the test suite.

The cost ceiling must be a positive finite decimal and is recorded as `declared_only_not_enforced_pre_send`; no pricing data ships, so no pre-send cost admission is claimed. The output-token ceiling is sent as `max_completion_tokens`.

## Why

The review sent sentinel text in a requirement, the uncertainty policy and the evidence policy through a recording transport: the request succeeded and none of the three reached the provider body. The artifact retained them; the request lost them.

## Consequences

Tests assert on the final prepared request, not on intermediate artifacts. Real budget admission would need versioned pricing, input estimates, output/reasoning charges, refusal when pricing is unknown, and usage reconciliation; until then the budget stays a declaration and is labeled as one.
