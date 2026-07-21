# PromptRig API Contract Overview

The normative API definition is generated as OpenAPI by FastAPI. This document defines required resource behavior.

## Core resources

- `/v1/projects`
- `/v1/projects/{project_id}/versions`
- `/v1/projects/{project_id}/compile`
- `/v1/compilations/{compilation_id}`
- `/v1/compilations/{compilation_id}/evaluate`
- `/v1/evaluations/{evaluation_id}`
- `/v1/projects/{project_id}/try`
- `/v1/projects/{project_id}/exports`
- `/v1/providers`
- `/v1/credentials`
- `/v1/health`

## Contract rules

- UUID identifiers are opaque.
- Every mutable project operation creates or references a version.
- Long-running operations return a job identifier and resumable status.
- Idempotency keys are required for compile, evaluate, repair, and export creation.
- API errors use the canonical error schema.
- Authentication and authorization are checked server-side.
- Raw provider secrets are write-only.
- Trace and cost metadata are visible only to authorized project users.
- Benchmark mode records immutable environment and harness metadata.
