# PromptRig Database Model

## Required entities

- users/profiles
- organizations
- organization_members
- projects
- project_versions
- compilation_runs
- provider_manifests
- provider_credentials
- generated_artifacts
- evaluation_suites
- evaluation_cases
- evaluation_runs
- evaluation_case_results
- execution_traces
- exports
- audit_events
- usage_events
- benchmark_runs
- benchmark_submissions

## Invariants

- Every project belongs to one tenant.
- Every project version is immutable after creation.
- A compilation references exactly one source project version and produces a new immutable result version.
- Credentials are referenced, never copied into project or trace records.
- Artifact and export hashes are stored.
- Deletion follows a documented cascade or tombstone policy.
- Row-level access rules are tested for every tenant-owned table.

## Hosted MVP

Use Supabase Postgres/Auth/Storage. Keep compiler-domain tables portable Postgres and isolate Supabase-specific authentication/storage adapters so PromptRig Core does not depend on Supabase.
