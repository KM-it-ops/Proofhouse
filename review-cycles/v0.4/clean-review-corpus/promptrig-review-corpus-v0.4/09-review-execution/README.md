# PromptRig Review Launch v0.4

This directory executes Round 1 of the PromptRig architecture review.

## What the owner does

1. Upload the complete `promptrig-review-corpus-v0.4.zip` to one clean conversation/session per reviewer.
2. Paste only that reviewer's launch prompt.
3. Do not show reviewers any other review result.
4. Save the result exactly as returned into `results/raw/<reviewer-id>/`.
5. Run the validator.
6. Move valid findings into `results/validated/` and preserve rejected outputs with validation errors.
7. Do not resolve findings until all intended independent reviews are sealed.

## Round 1 completion gate

Round 1 is complete only when:

- every required reviewer either submitted a valid review or has a documented nonparticipation record;
- all raw outputs, timestamps, model labels, harness versions, and human interventions are preserved;
- no reviewer had access to another reviewer's findings;
- every accepted finding validates against the finding schema;
- the corpus checksum matches the launch manifest.

The next release after completed intake is the Resolution Docket and Architecture Freeze Candidate.
