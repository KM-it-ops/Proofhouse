# Review Output Contract

Every reviewer must return three artifacts.

## 1. Executive report

Markdown containing:

- reviewer identity and specialist mandate;
- corpus version and checksum;
- executive verdict: approve, approve with conditions, or reject for freeze;
- blocking findings;
- nonblocking findings;
- contradictions;
- missing evidence;
- assumptions rejected;
- proposed ADR/RFC/schema changes;
- validation plan;
- residual risks;
- confidence and limitations.

## 2. Findings JSON

A JSON array. Every item must conform to `03-architecture/REVIEW_FINDING_SCHEMA.json`. Finding IDs use:

`REV-<REVIEWER>-<SEVERITY>-NNN`

Examples: `REV-CODEX-HIGH-001`, `REV-KIMI-MEDIUM-004`.

## 3. Run manifest

A JSON object based on `templates/REVIEW_RUN_MANIFEST.template.json`. It records the actual product/harness/model configuration, timestamps, intervention count, network/tool access, result files, and checksums.

No finding is accepted into the resolution docket until both its schema and evidence references validate.
