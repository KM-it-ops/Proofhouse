# Round 1 Execution Runbook

## Isolation

Use a new session for each reviewer. Upload the same corpus. Do not paste summaries from prior sessions. Disable memory/project carryover when the product permits it. Do not ask follow-up questions that reveal other findings.

## Launch sequence

1. Record the start time in UTC.
2. Record product, harness/app version, selected model label, account tier, tool/network settings, and context settings.
3. Upload `promptrig-review-corpus-v0.4.zip`.
4. Paste the relevant prompt from `prompts/` without modification.
5. Answer clarification questions only with facts already present in the corpus. Log every answer verbatim as a human intervention.
6. Request one final response containing:
   - a readable Markdown report;
   - a JSON findings array conforming to `REVIEW_FINDING_SCHEMA.json`;
   - a run manifest conforming to `REVIEW_RUN_MANIFEST.template.json`.
7. Save all three outputs and the full session transcript where export is supported.
8. Compute SHA-256 checksums.
9. Validate findings with `scripts/validate_review.py`.
10. Seal the result; do not edit reviewer language. Corrections must be submitted as an appended reviewer amendment.

## Invalid-review conditions

Reject or quarantine a review when it:

- fails to identify the corpus version;
- omits evidence locations for material findings;
- exposes unverifiable hidden reasoning instead of inspectable rationale;
- invents project requirements;
- returns no structured findings;
- modifies the supplied source files;
- appears contaminated by another review;
- cannot identify the product/harness/model surface used;
- contains critical factual claims with no source or corpus evidence.

A rejected review may be rerun from a fresh session. Preserve the rejected attempt.
