# Codex repeat of the `prompt` example

The original example (`../prompt` and `../prompt-record`) was written by Cursor. This folder is the same request given to a different agent, Codex, to show that Proofhouse's record and check work with more than one agent.

- Request (identical): `Prompt: ticket-handoff turns a support thread into a handoff note`
- Writer: Codex, handed the job through the delegate script in a clean scratch repo that held nothing but a brief. It never saw the original prompt, so this is an independent attempt, not a copy.
- Judge: Claude (Sonnet 5.5), not the writer. Score 8 of 10. The writer gave no self-score, so the record's `score` is `null`.
- Files: `prompt.md` is what Codex wrote, unedited. `../prompt-codex-repeat-record/` holds the record that `proofhouse record prompt` produced (`record.json`, `v1/checks.json`, `final.md`).

## What this proves

- `proofhouse check prompt` and `proofhouse record prompt` pass on a prompt written by Codex. The record's `agent` field says `codex`.
- The record keeps the judge apart from the writer and does not treat a self-score as proof.
- A separate acceptance script confirmed, before the record was made, that the file had at least 150 words, a `{{placeholder}}`, section headings, a worked example, a missing-detail rule and no filler words. It failed before Codex ran and passed after.

## What this does not prove

- It does not show Codex writes better prompts than Cursor. One run each, and the two prompts use different section layouts, so they are not scored on the same scale.
- The built-in prompt checks are shallow (present, no filler, length). They do not run the prompt on a real ticket thread, so the prompt's actual output quality is untested.
- The score of 8 is one judge's opinion, not a measurement. The judge's note: the prompt never tells the model to keep ticket IDs or error codes the next agent needs.
- It is a single round (v1). There was no fix round, so the "improves it" part of the loop is not shown here.
- The paid-plan cost of the Codex run (about one point of its 5-hour window) is from the delegate script's usage reading, not a bill, and other Codex sessions shared the same window while it ran.
