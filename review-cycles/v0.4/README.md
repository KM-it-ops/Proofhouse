# PromptRig-Central

Consolidated PromptRig v0.4 review working folders (Codex, Claude Code, Gemini, and Kimi K3) plus the
canonical project source and clean baseline corpus. Produced by an automated, evidence-based
consolidation pass — see `audit/CONSOLIDATION_REPORT.md` for the full account.

## ⚠️ Do not delete the original source folders yet

This directory is a **copy**. The originals it was built from are still on disk under `C:\AI`:

- `C:\AI\claude promptrig-review-launch-v0.4`
- `C:\AI\gemini promptrig-review-launch-v0.4`
- `C:\AI\kimi k3 promptrig audit`
- `C:\AI\Codex\codex promptrig v0.4 audit`
- `C:\AI\promptrig-part1-consolidation-handoff-v1.0`

**Do not delete any of them until Part 2 has verified the GitHub copy.** This consolidation pass did not
push anything to GitHub, initialize git, or begin Part 2 in any way.

## Layout

- `canonical-source/promptrig-review-launch-v0.4/` — the editable canonical project source (as seeded
  from the handoff package). Not modified by any reviewer's changes.
- `clean-review-corpus/promptrig-review-corpus-v0.4/` — the clean baseline corpus used for comparison.
  Distinct from the launch pack above (86 files vs. 123).
- `reference-packages/` — the two immutable reference ZIPs, copied verbatim, never edited.
- `review-results/round-1/<reviewer>/` — each reviewer's standard deliverables
  (`EXECUTIVE_REPORT.md`, `FINDINGS.json`, `RUN_MANIFEST.json`, or their reviewer-specific equivalent
  filenames) plus a `supplemental/` folder for any extra artifacts (empty for all four reviewers in this
  round — see `audit/CONSOLIDATION_REPORT.md`). `kimi-k3-high/` contains no reviewer deliverables and
  instead documents that absence in `NO_REVIEWER_OUTPUT_FOUND.md`.
- `review-working-snapshots/<reviewer>/` — a **differential** snapshot of each reviewer's working
  folder: only the files unique to or modified within that folder (relative to the pristine launch pack)
  were copied here, to avoid duplicating ~120 unchanged corpus files four times over. Each snapshot's
  `SNAPSHOT_MANIFEST.json` lists every omitted-but-unchanged file by path and SHA-256, so the omission is
  fully auditable.
- `audit/` — the full audit trail: `CONSOLIDATION_REPORT.md` (start here), `FILE_INVENTORY.csv`,
  `CLASSIFICATION_RECORD.json`, `DUPLICATE_AND_CONFLICT_REPORT.md`, `EXCLUSIONS.md`,
  `SECRET_SCAN_REPORT.md`, `VALIDATION_REPORT.md`, `SHA256SUMS.txt`, and an empty `quarantine/`
  (nothing needed quarantining).

## Reviewers found (round 1)

| Reviewer | Standard artifacts | Notes |
|---|---|---|
| Claude Code (Fable 5) | ✅ all 3 | — |
| Gemini (3.5 Flash) | ✅ all 3 | — |
| Codex (OpenAI) | ✅ all 3 | Original filenames used a `promptrig_codex_` prefix; preserved verbatim |
| Kimi K3 | ❌ none | Working folder exists and is untouched/pristine, but no review output was ever produced or saved. See `review-results/round-1/kimi-k3-high/NO_REVIEWER_OUTPUT_FOUND.md`. |

Readiness status: **READY_WITH_WARNINGS** (Kimi K3 gap only — the three originally-expected reviewers
are complete and verified). Full details in `audit/CONSOLIDATION_REPORT.md`.
