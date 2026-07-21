# Validation Report

Each check below was actually executed (SHA-256 hashing, JSON parsing, directory listing) — not asserted.

## 1. All copied files exist and hashes match their sources

Ran a script that reads every row of `FILE_INVENTORY.csv` (234 rows), re-hashes the destination file,
confirms it matches the recorded SHA-256, and — for every row marked `copied_verbatim` — re-hashes the
original source file and confirms it also matches.

**Result: 234/234 rows checked, 0 destination-hash mismatches, 0 source-hash mismatches, 0 missing sources.**

## 2. No original candidate folder was deleted or modified

Re-hashed all four reviewer working folders (`claude promptrig-review-launch-v0.4`,
`gemini promptrig-review-launch-v0.4`, `kimi k3 promptrig audit\promptrig-review-launch-v0.4`,
`Codex\codex promptrig v0.4 audit\promptrig-review-launch-v0.4`) at the end of the run and compared the
full per-file hash map against the map captured at the start of the run.

**Result: all four folders identical, file-for-file, byte-for-byte, before and after consolidation.**
No file in any original was moved, renamed, deleted, or edited. Nothing was deleted from `C:\AI` at any
point in this run.

## 3. Each identified reviewer has a result directory

`review-results/round-1/` contains one subdirectory per identified reviewer:
`codex-sol-high/`, `claude-code-fable-5-high/`, `gemini-3.5-flash-high-antigravity/`, and
`kimi-k3-high/` (the fourth reviewer found beyond the three originally expected). **Result: confirmed.**

## 4. Every result directory has all three standard files or a documented deficiency

| Reviewer | EXECUTIVE_REPORT | FINDINGS | RUN_MANIFEST | Status |
|---|---|---|---|---|
| claude-code-fable-5-high | present | present | present | Complete |
| gemini-3.5-flash-high-antigravity | present | present | present | Complete |
| codex-sol-high | present (prefixed filename, content maps 1:1) | present | present | Complete |
| kimi-k3-high | absent | absent | absent | **Documented deficiency** — see `review-results/round-1/kimi-k3-high/NO_REVIEWER_OUTPUT_FOUND.md` |

**Result: confirmed — 3 of 4 complete, 1 documented deficiency, 0 silent gaps.**

## 5. All JSON files parse, or invalidity is reported

Recursively parsed every `.json` file present anywhere under `PromptRig-Central` after all copy
operations completed.

**Result: 59/59 JSON files parse successfully. 0 invalid JSON files found** (so no
`FINDINGS.json`-vs-schema validation failure needed to be preserved-but-flagged — all reviewer JSON
output was syntactically valid).

## 6. Canonical source and clean corpus are separate

`canonical-source/promptrig-review-launch-v0.4/` (123 files) and
`clean-review-corpus/promptrig-review-corpus-v0.4/` (86 files) are distinct directory trees with
different file counts and different content (the launch pack additionally contains `archive/v0.2/`,
an `09-review-execution/evidence/` directory, and `PACK_MANIFEST_v0.4.json` that the corpus pack does
not). **Result: confirmed separate, never merged.**

## 7. No known secret was copied into a normal project directory

See `SECRET_SCAN_REPORT.md` — 0 matches across every reviewer source folder and the entire destination
tree, using both filename and content-pattern heuristics. `audit/quarantine/` was created but is empty.
**Result: confirmed, with the caveat that this is a heuristic scan, not a guarantee** (see limitations below).

## 8. Audit records match actual destination contents

`FILE_INVENTORY.csv` was built by walking `PromptRig-Central` in its final state (234 files) and mapping
each one to its provenance; `verify_inventory.py` (check 1 above) then round-tripped every row back
against the live filesystem and found zero discrepancies. Total file count in `PromptRig-Central`
outside of `audit/` is 234, matching `FILE_INVENTORY.csv` row count exactly. The `audit/` directory's
own generated deliverables (this report, `CONSOLIDATION_REPORT.md`, etc.) document the process itself
and are intentionally out of scope for `FILE_INVENTORY.csv`, which tracks project/review content.
**Result: confirmed consistent.**

## Known limitations (documented, not hidden)

- The secret scan is pattern-based, not a dedicated secret-scanning engine; it will not catch every
  possible credential format.
- `FINDINGS.json` was not validated against `03-architecture/REVIEW_FINDING_SCHEMA.json` field-by-field
  (only checked for well-formed JSON) — a full schema validation was out of scope for this pass and
  would be a reasonable Part 2 follow-up before any downstream tooling assumes strict schema conformance.
- Gemini's `RUN_MANIFEST.json` references `outputs.transcript_path = "transcript.jsonl"`, but no such
  file exists in the source folder. This is reported as-is; the manifest was not edited to remove the
  dangling reference (rule: never modify reviewer output).
