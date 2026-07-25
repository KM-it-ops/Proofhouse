# PRS Disposition

**Status:** Proposed owner decision.  
**Recommendation:** `DEFERRED`.

## Decision requested

Choose exactly one permitted disposition for PromptRig Specification (PRS):

1. `CONTRACT_CANDIDATE`
2. `DEFERRED` — recommended
3. `REJECTED`

The recommended owner decision is:

> Keep PRS as a separately reviewable future source-language candidate, but defer grammar, parser, conformance, and contract status until representative authoring evidence proves value beyond JSON/API/file inputs and resolves the gaps below.

This recommendation does not change the `Candidate / Deferred` status of ADR-001.

## Evidence-based assessment

| Question | Current evidence | Finding |
|---|---|---|
| Does PRS add value beyond JSON/API/file inputs? | One non-binding example and four short proposal documents | `UNPROVEN`; the 41-case fixture set is not rendered in PRS |
| Can PRS preserve exact source locations? | Syntax proposal says it should; no grammar, parser, or source map exists | `UNPROVEN` |
| Is deterministic parsing feasible? | Candidate properties say UTF-8 and line-oriented | `PLAUSIBLE_NOT_PROVEN`; escaping and grammar are unknown |
| Does syntax convenience pressure canonical semantics? | Example directly names objective, input, output, constraint, and evaluation constructs | `RISK_PRESENT`; source syntax could accidentally define meaning not owned by the requirements contract |
| Can grammar represent ambiguity, conflict, evidence, approvals, and unresolved meaning? | No representative examples or productions | `UNPROVEN` |
| Are imports, macros, and extensions bounded? | Explicitly unknown in `PRS_SYNTAX.md` | `UNPROVEN_HIGH_COMPLEXITY` |
| Are current examples representative? | One happy-path support-triage illustration | `NO` |
| Is grammar freeze timely? | Source-neutral semantics are only Proposed; no parser conformance corpus exists | `PREMATURE` |

The machine-readable assessment is [evidence/prs-evaluation-matrix.json](evidence/prs-evaluation-matrix.json).

## Why not `CONTRACT_CANDIDATE`

The current PRS material does not demonstrate deterministic grammar, escaping, version negotiation, source maps, error recovery, imports, macros, extensions, or lossless representation of the adversarial case set. Promoting it would make syntax choices before owner ratification of the semantic boundary and could pressure frozen IR v0.1 to fit authoring convenience.

## Why not `REJECTED`

A compact declarative source language may still improve reviewability, version control, stable source locations, and authoring ergonomics. The evidence does not show that PRS is harmful or valueless; it shows that the present proposal is not mature enough to contract.

## Re-entry evidence

Reconsider `CONTRACT_CANDIDATE` only after a separately authorized mission provides:

- PRS renderings for the full evidence-first case set, including all five terminal statuses;
- a versioned grammar and unambiguous escaping rules;
- deterministic parse and diagnostic rules with exact source spans;
- explicit representation of assumptions, questions, conflicts, authority, defaults, approvals, refusal, unsupported meaning, and IR gaps;
- bounded or excluded imports, macros, and extensions;
- lossless mapping into the source-language-neutral requirements records;
- proof that PRS adds measurable value beyond JSON/API/file authoring;
- independent architectural review and explicit owner approval.

## Non-authorization

Selecting `DEFERRED` does not authorize a PRS parser, grammar freeze, language server, formatter, model integration, IR change, implementation mission, or ADR-001 status change. PRS remains one possible producer of requirements records and can never become the semantic owner.
