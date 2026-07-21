# PromptRig Part 1 — Consolidation Report

## Executive Summary

Three PromptRig v0.4 review working folders (Codex, Claude Code, Gemini) were consolidated into a single
canonical directory, `C:\AI\PromptRig-Central`, alongside the editable canonical source, the clean
baseline corpus, and the immutable reference ZIPs. A **fourth** candidate reviewer folder — Kimi K3 — was
also discovered, inspected, and preserved; it was fully prepared but never produced any review output,
which is documented as a deficiency rather than silently omitted. All three completed reviewers passed
every integrity check: their entire copy of the corpus was byte-for-byte unchanged from the pristine
launch pack, and each contributed exactly three new files (their standard artifacts) with no collisions,
no duplicates, and no detected secrets. No original source folder was moved, modified, or deleted at any
point in this run.

**Readiness status: READY_WITH_WARNINGS** (the warning being the missing Kimi K3 deliverables — see
below; nothing about the three completed reviewers is blocked).

## Exact source folders examined

| Path | Role |
|---|---|
| `C:\AI\promptrig-part1-consolidation-handoff-v1.0\canonical-source\promptrig-review-launch-v0.4` | Editable canonical project source (seed) |
| `C:\AI\promptrig-part1-consolidation-handoff-v1.0\canonical-source\promptrig-review-corpus-v0.4` | Clean baseline corpus (seed) |
| `C:\AI\promptrig-part1-consolidation-handoff-v1.0\reference-packages\*.zip` | Immutable reference backups (seed) |
| `C:\AI\claude promptrig-review-launch-v0.4` | Reviewer working folder — Claude Code |
| `C:\AI\gemini promptrig-review-launch-v0.4` | Reviewer working folder — Gemini |
| `C:\AI\Codex\codex promptrig v0.4 audit\promptrig-review-launch-v0.4` | Reviewer working folder — Codex |
| `C:\AI\kimi k3 promptrig audit\promptrig-review-launch-v0.4` | Reviewer working folder — Kimi K3 (no output produced) |
| `C:\AI\CodexHome`, `C:\AI\Gemini`, `C:\AI\Codex\1st`, `C:\AI\Codex\KM-it-ops.github.io`, `C:\AI\Codex\preview-screenshots` | Inspected and excluded — not review folders (see `EXCLUSIONS.md`) |

Full evidence and confidence for every classification is in `CLASSIFICATION_RECORD.json`.

## Reviewer classification and confidence

| Reviewer | Folder | reviewer_id (from RUN_MANIFEST) | Confidence |
|---|---|---|---|
| Claude Code (Fable 5) | `claude promptrig-review-launch-v0.4` | `anthropic-claude-code` | High |
| Gemini (3.5 Flash, Antigravity harness) | `gemini promptrig-review-launch-v0.4` | `google-gemini` | High |
| Codex (OpenAI) | `Codex\codex promptrig v0.4 audit\...` | `openai-codex` | High |
| Kimi K3 | `kimi k3 promptrig audit\...` | n/a (no RUN_MANIFEST was ever produced) | High confidence this is the staged Kimi K3 folder; confirmed deficiency of output |

## Files copied for each reviewer

All figures below are drawn from `audit/FILE_INVENTORY.csv` and `audit/CLASSIFICATION_RECORD.json`.

- **claude-code-fable-5-high**: `EXECUTIVE_REPORT.md`, `FINDINGS.json`, `RUN_MANIFEST.json` copied into
  `review-results/round-1/claude-code-fable-5-high/` (verbatim, hash-verified). Same 3 files also copied
  into `review-working-snapshots/claude-code-fable-5-high/09-review-execution/evidence/claude-code/`
  with a `SNAPSHOT_MANIFEST.json` documenting the 123 omitted-but-unchanged baseline files.
- **gemini-3.5-flash-high-antigravity**: `EXECUTIVE_REPORT.md`, `FINDINGS.json`, `RUN_MANIFEST.json`
  copied the same way (root-level source location).
- **codex-sol-high**: `promptrig_codex_EXECUTIVE_REPORT.md`, `promptrig_codex_FINDINGS.json`,
  `promptrig_codex_RUN_MANIFEST.json` copied verbatim with their original (non-standard, prefixed)
  filenames preserved — filename mapping to the standard artifact roles is recorded in
  `FILE_INVENTORY.csv`'s `artifact_role` column.
- **kimi-k3-high**: 0 reviewer files exist to copy. One audit-authored note,
  `NO_REVIEWER_OUTPUT_FOUND.md`, was placed in its result directory to document the absence, clearly
  labeled as not being reviewer output.
- No `supplemental/` artifacts were found for any reviewer beyond the three standard files — each
  reviewer's diff against baseline showed exactly 3 added files (0 for Kimi) and nothing else unique.

## Files excluded and why

See `EXCLUSIONS.md` for the full table. In short: two empty/disposable directories inside the Codex
working folder (`.git`, `.agents` — both empty), and five sibling folders under `C:\AI` that are not
PromptRig review material at all (Codex CLI's own app-state/credentials directory, an unrelated Gemini
notes folder, an empty folder, and a personal portfolio site + its screenshots).

## Conflicts and duplicates

**None.** See `DUPLICATE_AND_CONFLICT_REPORT.md` for the full per-reviewer diff table. No two reviewers'
output ever collided on a destination path; the only byte-identical file shared across all reviewers is
the launch pack's own `CORPUS_SHA256.txt` scaffold file, which is not reviewer-generated.

## Validation failures

**None found** — see `VALIDATION_REPORT.md`. All 59 JSON files present in the final tree parse
successfully; all 234 destination files hash-match their sources. One informational note (not a
failure): Gemini's `RUN_MANIFEST.json` references a `transcript.jsonl` that does not exist on disk —
preserved as-is, reported, not fabricated or removed.

## Suspected secrets

**None.** See `SECRET_SCAN_REPORT.md`. Pattern-based scan (filenames + content) found zero matches
across all four reviewer source folders and the entire destination tree. `audit/quarantine/` exists and
is empty.

## Methodology note: differential-snapshot baseline choice

Per the mission brief, `promptrig-review-corpus-v0.4` is "the clean baseline corpus used for comparison."
However, the four reviewers were actually issued and worked from `promptrig-review-launch-v0.4`, a
distinct pack that differs from the corpus pack only in scaffold-level additions present identically in
every reviewer copy (`archive/v0.2/`, an empty `09-review-execution/evidence/` directory, and
`PACK_MANIFEST_v0.4.json`). Diffing each reviewer against `promptrig-review-corpus-v0.4` would have
misreported those three scaffold items as "reviewer-added" in every single reviewer folder, obscuring
the real signal. This report and `SNAPSHOT_MANIFEST.json` instead diff each reviewer against the
`promptrig-review-launch-v0.4` baseline (what they actually started from), which is documented here per
the "choose preservation over cleanup and document the ambiguity" rule. Both packs are preserved intact
and separately in `canonical-source/` and `clean-review-corpus/` regardless of this diffing choice.

## Final destination path

```
C:\AI\PromptRig-Central
```

## Originals were not deleted

Explicitly confirmed by re-hashing all four reviewer working folders at the end of the run and comparing
against hashes captured at the start: **zero bytes changed in any original folder.** Nothing under
`C:\AI\claude promptrig-review-launch-v0.4`, `C:\AI\gemini promptrig-review-launch-v0.4`,
`C:\AI\kimi k3 promptrig audit`, or `C:\AI\Codex` was moved, renamed, edited, or deleted by this process.

## Readiness status

**READY_WITH_WARNINGS**

Warning: the Kimi K3 review has no deliverables anywhere on disk. If a fourth reviewer's findings are
expected for Part 2 synthesis, that review needs to be re-run (or its output located and supplied)
before synthesis proceeds. The three originally-expected reviewers (Codex, Claude Code, Gemini) are
fully complete, verified, and ready.

**Do not begin Part 2 (GitHub upload) from this report.** Part 2 happens in a fresh chat per the
mission brief.
