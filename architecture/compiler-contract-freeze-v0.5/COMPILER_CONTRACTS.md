# Compiler contracts

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Scope

Compiler Core v0.1 accepts a PromptRig IR document, validates it, performs intent-preserving deterministic passes, resolves a versioned provider capability manifest, and emits artifacts, immutable diagnostics, and provenance. Offline validation and inspection MUST require no network or credentials.

Live model execution, evaluation, repair, persistence, hosted jobs, tenant authorization, billing, and UI orchestration are out of v0.1 scope.

## Compile request

A library compile request MUST contain:

- parsed IR conforming to `PROMPTRIG_IR_V0_1.schema.json`;
- a selected adapter identifier and exact adapter version;
- a versioned capability manifest or the deterministic fake adapter;
- an options object with `offline` defaulting to `true`.

The request MUST NOT contain a second authoritative mode, repair limit, objective, or policy outside IR. Callers MAY attach an idempotency key for orchestration, but it does not affect semantic output.

## Compile result

The result MUST contain `contract_version`, `status`, canonical `ir_sha256`, compiler identity/version, adapter identity/version, ordered diagnostics, artifacts, and an ordered pass trace. A successful result MUST have no error-severity diagnostic. A failed result MUST NOT claim deployable artifacts.

Artifact entries MUST contain a stable logical name, media type, SHA-256 digest, and either bytes/path supplied by the caller-controlled artifact sink. Compiler Core MUST NOT silently write outside that sink.

## Determinism

Given byte-equivalent canonical IR, compiler version, adapter version, manifest, and options, offline compilation MUST produce semantically identical results and artifact digests. Timestamps and invocation IDs are excluded from semantic equality and MUST be identified as volatile metadata.

## Traceability

Every diagnostic and artifact MUST reference source IR paths. Each pass trace MUST record input and output digests. Lowering MUST record the capability decisions that affected each artifact.

## Failure

Unknown fields, unsupported contract versions, invalid IR, unsupported mandatory capabilities, unsafe policy conflicts, adapter contract violations, and integrity failures MUST fail explicitly. Unsupported optional features MAY emit warnings only when the IR marks them optional and the result records omission.

## Versioning

Public contracts begin at `0.1.0`. Schema `$id`, document `spec_version`, diagnostic `contract_version`, and library package version are distinct and MUST be reported. Migration is an explicit operation; compilation MUST NOT auto-upgrade IR silently.
