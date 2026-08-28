# Instructions for the second reviewer

You do not need PromptRig jargon. You do need to judge architecture and security.

## Read in this order

1. This file.
2. `PACK.md` (the review).
3. `README.md` (honesty limits — what we are not claiming).
4. The named source files listed in `PACK.md` if you can open them. If you cannot, say so under Unknowns. Do not guess.
5. Fill `VERDICT.md` only. Do not edit `PACK.md`.

## What to ignore

- Strategy books under `architecture/strategy/` except where `PACK.md` already stated a fact.
- MISSION-027 code if it appears later. This review is SHA `2831cda` only.
- Marketing, benchmarks, live APIs, Simple Mode UI.

## How to record a finding

In `VERDICT.md`, use one bullet per finding:

- file path and, if you have it, line
- what is wrong
- why it matters for architecture or security

If you are unsure, write it under Unknowns. **I don't know** is allowed.

## Verdict

Accept means: the pack is an honest architecture and security review of this snapshot.
Reject means: the pack is wrong, incomplete, or unsafe to treat as that review.
