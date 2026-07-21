# Duplicate and Conflict Report

## Method

Every reviewer working folder was hashed file-by-file (SHA-256) and diffed against the pristine
`promptrig-review-launch-v0.4` baseline pack (see methodology note in `CONSOLIDATION_REPORT.md` on
why the launch pack, not the corpus pack, was used as the diff baseline). Diff results per reviewer:

| Reviewer | Baseline files | Reviewer files | Unchanged | Modified | Added | Deleted |
|---|---|---|---|---|---|---|
| claude-code-fable-5-high | 123 | 126 | 123 | 0 | 3 | 0 |
| gemini-3.5-flash-high-antigravity | 123 | 126 | 123 | 0 | 3 | 0 |
| codex-sol-high | 123 | 126 | 123 | 0 | 3 | 0 |
| kimi-k3-high | 123 | 123 | 123 | 0 | 0 | 0 |

## Conflicts (same destination path, different content)

**None.** Each reviewer's standard artifacts were copied into its own
`review-results/round-1/<reviewer>/` and `review-working-snapshots/<reviewer>/` subdirectory, so no
two reviewers' files ever competed for the same destination path. No collision-suffix naming was
required anywhere in this consolidation.

## Duplicate content (same bytes, multiple original locations)

**None found among reviewer-added files.** Each reviewer's three artifacts
(EXECUTIVE_REPORT/FINDINGS/RUN_MANIFEST content) are unique per reviewer — no cross-reviewer hash
collisions were observed.

One expected duplicate exists **by design**, not as reviewer output: `09-review-execution/evidence/CORPUS_SHA256.txt`
is byte-identical (same SHA-256) across all four reviewer folders and the canonical launch-pack baseline.
This is scaffold content shipped with the launch pack, not a reviewer artifact — it is preserved once,
under `canonical-source/`, and not duplicated into each reviewer's directory (see `EXCLUSIONS.md`).

## No reviewer modified the shared corpus

For all four reviewers, 100% of the 123 baseline files carried over unchanged (identical SHA-256).
No reviewer edited, deleted, or renamed any file from the corpus/launch pack they were given. All
reviewer contributions took the form of new files added alongside the untouched baseline.
