# Sealed offline whole-configuration benchmark manifest (v0.1)

**Status:** Contract for MISSION-033 / campaign U7. **Not a published claim.** Not CERTIFIED. Offline-only track; no live track in this freeze.
**Manifest version:** `0.1.0`
**Network:** `network_mode=offline`, `network_allowed=false` (default and only legal value on this track).

This file is the benchmark/version manifest contract. Historical prose under `review-cycles/v0.4/` is **not a result** and is not this runner. Do not treat v0.4 documents as scores.

## Authority

1. `evaluate_deterministic` is the rank-1 compile / security / network gate. An oracle security failure (`EVR-SEC-0001`) **cannot** be published as a product-eval `PASS`.
2. Product eval (`evaluate_product` / `promptrig-compiler evaluate-product`) is the published scorer after the oracle gate. The product surface is implemented and **not CERTIFIED**.
3. Hidden tests are held by the runner. They are inaccessible to the scored configuration (no path, bytes, or case ids in the configuration source).
4. Default autonomous attempts is **3**. A smaller budget is legal only when `owner_ratified_smaller_budget=true` and `owner_ratification_note` is non-empty.
5. Repair budgets remain `{0,1,2}`. `EVR-SEC-0001` is unchanged. Skip-cert law (OAR-022) is not undone.
6. Infrastructure failures (`BMK-INF-0001`) are classified separately from product `FAIL`.
7. Marketing claims remain forbidden until the owner authorizes an independent dry-run reproduction. This contract does not authorize publication.

## Required fields

| Field | Rule |
|---|---|
| `manifest_version` | `0.1.0` |
| `benchmark_id` | Non-empty id for this sealed suite |
| `network_mode` | `offline` only |
| `network_allowed` | `false` only |
| `environment_digest` | `sha256:` + 64 lowercase hex of the sealed environment |
| `source_hashes` | Per configuration id, SHA-256 of exact source bytes (`sha256:` prefix). Mutated hashes fail (`BMK-HASH-0001`) |
| `secrets_policy` | Credentials forbidden; none in artifacts or repository |
| `budgets.repair` | Exactly `[0, 1, 2]` |
| `budgets.autonomous_attempts` | Integer ≥ 1; must match `repetition.autonomous_attempts` |
| `repetition` | Attempts, ratification flag, note |
| `starter_commit` | Starter snapshot identity |
| `permissions` | Network and credentials deny on this track |
| `intervention_policy` | `autonomous` |
| `contamination_controls.hidden_tests_inaccessible` | `true` |
| `scoring.oracle` | `evaluate_deterministic` |
| `scoring.published_scorer` | `evaluate_product` |
| `marketing_claims_policy` | `forbidden_until_owner_authorized_dry_run` |

Schema: `benchmark-manifest.schema.json`. Validation checks content and hashes, not only JSON syntax.

## Diagnostics

| Code | When |
|---|---|
| `BMK-MAN-0001` | Manifest missing fields or fails schema |
| `BMK-HASH-0001` | Source bytes do not match declared hashes |
| `BMK-NET-0001` | Network not offline / `network_allowed` not false |
| `BMK-SEC-0001` | Secret material in scored source |
| `BMK-BUD-0001` | Repair set or repetition policy illegal |
| `BMK-INF-0001` | Infrastructure failure (missing hidden suite, I/O) |
| `BMK-ORC-0001` | Attempt to publish product-eval PASS after oracle security failure |

## Determinism (offline)

Two identical configurations in the same sealed environment must produce matching scores. Evidence checksums cover scores and hashes, not wall-clock timestamps.

## Non-claims

- Not a published benchmark result. Not CERTIFIED. Compiler remains PARTIAL.
- Not a live-network track. No credentials. `review-cycles/v0.4/` is historical only.
