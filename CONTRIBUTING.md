# Contributing

Proofhouse is intentionally small. Contributions should keep it practical, testable, and easy to inspect.

## Local Checks

```bash
python -m pip install -e ".[test]"        # or: uv sync --extra test
python -m pytest
python scripts/reference_workflow.py --quiet
python scripts/generate_model_surfaces.py --check
python -m proofhouse.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

Validate every dataset you add under `evals/datasets/`. After changing `model_registry.json` or `proofhouse-framework.json`, run `python scripts/generate_model_surfaces.py` and then `python scripts/build_skill_bundle.py`. After changing CLI help, regenerate the hosted OpenAPI fixture with `PROOFHOUSE_EXPERIMENTAL=1 python scripts/generate_hosted_openapi.py`.

## Contribution Rules

- Do not add secrets, API keys, or account-specific data.
- Do not add provider integrations before the offline harness and prompt assets remain stable.
- Runtime dependencies are jsonschema>=4.18 and rfc8785==0.1.4. Optional extra [live] installs httpx>=0.27. Adding a runtime dependency needs a decision record (below).
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, and `NOT FOUND IN PROVIDED MATERIAL`.
- Update `CHANGELOG.md` for user-visible changes.
- A fix for a defect starts with a failing regression test that reproduces it.

## Decisions

Changes to a public contract (a record schema, what a command or a PASS means, a new runtime dependency) need a short decision record in [`docs/decisions/`](docs/decisions/): open an issue describing the problem and the option you prefer, and include the record in the pull request. The maintainer accepts or declines it in review. Older history refers to internal "OAR" approvals; those are not published and are not required from contributors.
