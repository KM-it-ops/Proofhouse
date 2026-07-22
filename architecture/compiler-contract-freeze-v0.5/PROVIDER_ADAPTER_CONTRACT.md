# Provider adapter contract

## Identity

Every adapter exposes an immutable descriptor containing adapter ID/version, provider ID, supported IR range, capability-manifest version and digest, artifact kinds, and conformance-suite version.

## Interface

An adapter MUST implement deterministic `describe()`, `check_capabilities(validated_ir)`, and `lower(validated_ir, resolution)` operations. v0.1 adapters MUST NOT execute provider APIs. Future execution is a separate interface and permission boundary.

## Capability vocabulary

Capabilities use namespaced, versioned identifiers such as `output.structured_json@1`, `tools.function_calling@1`, and `reasoning.effort_control@1`. A manifest states `supported`, `unsupported`, or `conditional` plus machine-readable limits. Free-text capability claims are informative only.

## Results

Lowering returns artifacts, immutable diagnostics, capability decisions, and provider provenance. It MUST distinguish full success, failure, and partial artifact production. Partial production is never reported as deployable success when a required artifact failed.

## Conformance

All adapters pass the same offline suite covering identity, deterministic output, unknown capability rejection, required/optional gaps, schema-subset limits, tool mapping, safety/approval mapping, provenance, and non-mutation. The deterministic fake adapter is the reference implementation.

## Provider semantics

Provider-specific required state—such as reasoning signatures, schema subsets, or tool-loop continuation tokens—must be modeled in adapter artifacts and provenance. Adapters never emulate support by silently dropping such state or downgrading to free-form text.
