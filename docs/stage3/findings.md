# Stage 3 findings

78 cases, two for each of the 39 `proofhouse` commands, run by `scripts/stage3_hard_cases.py`. Every case runs in
its own throwaway folder, with every key-like variable removed, a fake key where a limit check needs one, and a
dead network address, so nothing can be sent and nothing is spent. The full table is in [hard-cases.md](hard-cases.md).

**Result: 78 held, 0 broke, 0 commands under two cases.** Paid calls: $0.

## First run: 18 cases broke

Triage found 9 real defects and 9 wrong expectations in my own case list. All 9 defects are fixed, each with a
test that failed first.

| Defect | What happened | Fix |
| --- | --- | --- |
| inspect, a folder as input | "internal error", exit 8 | 4e04676 |
| demo, workspace path is a file | "internal error: [WinError 183]" | 4e04676 |
| compile, a failed compile | left an empty output folder behind | 4e04676 |
| assay, claims file `{}` | said PASS | 4e04676 |
| assay, binary claims file | Python traceback | 4e04676 |
| case status, half-written `case.json` | Python traceback | 4e04676 |
| models show, name the console cannot print | Python traceback | 4e04676 |
| train start, epochs of -2 | priced as free and uploaded the data before refusing (a hole in the spend gate) | d338472 |
| generate, seconds of 0 or less | passed through to the paid request | d530ff4 |

The last two were found while re-aiming cases at the spending-limit path, not by the first run.

## Wrong expectations, corrected

Each says why in its case description: `compile-2` (adapter failure is exit 6), `execute-openai-1` (refusal is
EXE-OPT-0001, exit 7), `install-skill-1` and `-2` (exit 7), `check-2` (a folder with no SKILL.md is a usage error),
`models-1` and `-2` (the console escapes the name). Cases that stopped at an earlier refusal were given a fake key
and a real service id so they reach the limit they were written for: `run-1`, `train-2`, `generate-1`, `generate-2`, `media-1`.

A check that passed when it should not: several "nothing was saved" cases looked for a guessed file path that the
product never uses, so they could not fail. They now fail if anything at all is written into the isolated Proofhouse home (`home_clean`).

## What held

Every spend-gate case: no paid request starts without a stated limit, and nothing leaves the machine. Existing
files in folders the commands refused to use were never overwritten. Duplicate JSON keys, binary bytes with a
`.json` name, oversize files, conflicting flags and half-written records were all refused with a plain message and the documented exit code.

## Left out on purpose

`models update` (needs the network), `deploy` without a dry run, and `delegate` are never run by the runner.

## Cost

About 3 minutes of machine time per full run, $0 paid.

## Independent end review (Codex, whole diff against main)

Codex did not write the product fixes; Claude did not run the review. It raised 3 serious and 8 smaller points.

Fixed, each with a failing test first (`tests/test_stage3_runner.py`, `tests/test_stage3_breaks.py`):
- The runner returned success even when a case broke. It now fails if any case broke.
- `--name=value` options slipped past the "no outside paths" guard. The value after `=` is now checked, including a leading slash.
- Output from a case that timed out was saved without removing local paths. It is now scrubbed like every other output.
- Variables ending in `_URL`, `_URI`, `_PAT`, or containing `CONNECTION`, `SESSION`, `DSN`, `COOKIE` were not stripped from the case environment. They are now.
- `compare-1` stopped at "name at least two outputs" and never read the directory. It now has two entries and expects "file not found".
- `referee-2` damaged a file the command never reads. It now damages `loop.json` and expects "not readable JSON".
- The narrow-console test accepted exit 0 or 2. It now needs exit 0 and the replaced name.
- The plan claimed folder-escape cases. The runner refuses those paths, so the claim is removed.
- The film example imported `build_shots`, which was missing. It is back in `film/` and `v4/video/`.

Not changed:
- `train-2` cannot reach a real upload (no price, bad data), so its "nothing uploaded" line is matched text only. The upload boundary itself is covered by the mocked unit test in `tests/test_train.py`. Reaching a real upload would need a paid call, which this stage does not make. Boss accepted this gap on 2026-10-26: no live check with a real key.
- The finished film MP4 stays out of the repo. That was chosen earlier to keep the repo small and is now written in the example's README. Putting it back is Boss's call.
- `compare` says "file not found" for a directory given as an output file. It is clear enough and does not crash.

Result after the fixes: 78 held, 0 broke, $0 spent.
