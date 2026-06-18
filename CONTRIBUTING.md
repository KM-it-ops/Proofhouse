# Contributing

PromptRig is intentionally small. Contributions should keep it practical, testable, and easy to inspect.

## Local Checks

```bash
python -m pip install -e .
python -m pytest
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

Validate every dataset you add under `evals/datasets/`.

## Contribution Rules

- Do not add secrets, API keys, or account-specific data.
- Do not add provider integrations before the offline harness and prompt assets remain stable.
- Keep runtime dependencies at standard library only unless there is a clear design decision to change that.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, and `NOT FOUND IN PROVIDED MATERIAL`.
- Update `CHANGELOG.md` for user-visible changes.
