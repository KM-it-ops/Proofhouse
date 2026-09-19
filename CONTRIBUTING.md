# Contributing

Proofhouse is intentionally small. Contributions should keep it practical, testable, and easy to inspect.

## Local Checks

```bash
python -m pip install -e .
python -m pytest
python -m proofhouse.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

Validate every dataset you add under `evals/datasets/`.

## Contribution Rules

- Do not add secrets, API keys, or account-specific data.
- Do not add provider integrations before the offline harness and prompt assets remain stable.
- Runtime dependencies are jsonschema>=4.18 and rfc8785==0.1.4. Optional extra [live] installs httpx>=0.27. Do not add further runtime deps without an OAR.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, and `NOT FOUND IN PROVIDED MATERIAL`.
- Update `CHANGELOG.md` for user-visible changes.
