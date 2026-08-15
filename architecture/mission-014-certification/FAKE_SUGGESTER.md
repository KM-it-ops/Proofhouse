# Fake Model-Assisted Suggester Contract (MISSION-014 M2)

**Producer:** `fake-suggester-v0` / version `0.1.0`  
**Mission:** MISSION-014 M2 (authorized, in progress)  
**Profile key:** `fake_suggester_v0`

## Scope and non-claims

- This is an **optional headless suggestion sidecar only**. Proposals are sidecar evidence; they are **never mapped to IR** by `requirements_to_ir`.
- **Not a live model.** No provider SDK, HTTP client, credentials, or network on the certified path. The suggester is fake/scripted and offline (`network_allowed=false`).
- **Not M3 / Simple Mode UI.** Product UI semantics remain forbidden until M3.
- **Not freeform NLP.** Suggestions are structured proposal records with fixed fields, not unconstrained natural-language interpretation.
- **Not full MISSION-008.** Semantic validation and IR mapping remain on accepted structured records; the suggester does not replace deterministic validation.

## Proposal contract

Each proposal emitted by `fake-suggester-v0` carries:

| Field | Value |
|---|---|
| `producer_id` | `fake-suggester-v0` |
| `producer_version` | `0.1.0` |
| `acceptance_state` | `proposed` (never `accepted` on the certified path) |
| `authority_basis` | `model_suggested` (never `owner_decision` from the suggester) |
| `proposed_records` | e.g. `["REQ-MS-001"]` |
| `proposed_requirements` | structured records with `id` (e.g. `REQ-MS-001`), `statement`, `acceptance_state=proposed`, `authority_basis=model_suggested` |

Proposals **cannot bypass** deterministic validation, authority/defaults rules, or evidence requirements. Gate diagnostics use prefix `MAS-GATE-` only (`MAS-PARSE-` is reserved and unused).

## Hard rules

- Same structured input bytes → identical proposal (including digests).
- The suggester must not mutate the input document, `security_constraints`, or accepted objectives.
- Any attempt to self-accept a proposal or invent owner authority is a gate failure (`MAS-GATE-0001`, `MAS-GATE-0002`).
- IR `requirement_ids` with suggestions on must equal the suggestion-off run for the same structured document.
