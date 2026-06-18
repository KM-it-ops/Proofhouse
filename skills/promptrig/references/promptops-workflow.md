# PromptRig Workflow Reference

Use this compact reference when a task needs more structure than the base skill body.

## Audit Checklist

- Identify the target runtime and audience.
- Extract confirmed project facts.
- List missing context using exact labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Check instruction hierarchy, tool permissions, safety boundaries, output contract, and verification.
- Return findings by severity, then rewrite or recommend next steps.

## Rewrite Checklist

- Preserve accurate project-specific details.
- Remove vague authority such as "do anything" unless bounded by permissions and verification.
- Prefer explicit goals, inputs, outputs, constraints, and stop conditions.
- Add examples only when they reduce ambiguity.
- Keep the prompt as short as practical without weakening reliability.

## Agentic Workflow Checklist

- Define allowed tools and forbidden actions.
- Require repo/context inspection before edits.
- Require approval for destructive actions, credential use, publishing, or production changes.
- Include verification commands or acceptance criteria.
- Include a stop condition for ambiguity, repeated failures, missing authority, or unsafe scope.

## Eval Case Checklist

Every JSONL case needs:

```json
{
  "id": "string",
  "type": "normal | edge | missing_context | adversarial | regression",
  "input": "string",
  "expected_behavior": "string",
  "failure_signals": ["string"],
  "pass_criteria": "string"
}
```

Rubric scores must be integer values from 1 to 5.
