# 0004: Model-note provenance and gate precedence

Accepted 2026-09-21.

## Decision

- Every resolved model profile carries `source` (where the text came from: `builtin`, `cached`, `researched`, `user_supplied`, `fallback`) and `evidence` (`unverified`, `sourced`, `reviewed`). A profile without cited sources is `unverified`; a review date alone is not verification.
- Notes from a local file (`optimize new --notes-file`) are `user_supplied`, undated and unverified. They are never labeled researched.
- Notes produced by a model's web search (the artifact, a host agent) are `researched` and `unverified` unless sources are stored with them.
- Model-specific efficiency advice and token discipline may remove redundant wording only. They never remove a user's mandatory requirements, acceptance checks, tests, permission or approval gates, or requested verification steps. This rule is in the compile system prompt, the artifact, the skill, and the framework (`policyPrecedence`).

## Why

The shipped registry dated 17 profiles with no sources, a local file of invented notes was labeled researched and verified today, and one profile advised stripping verification instructions without distinguishing redundant wording from required gates.

## Consequences

All shipped profiles currently show `unverified`. Promoting one to `sourced` means adding primary vendor documentation URLs to its registry entry; `reviewed` additionally needs a named reviewer. Profiles older than the review window are flagged stale.
