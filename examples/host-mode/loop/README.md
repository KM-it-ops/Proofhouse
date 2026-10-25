# Host-mode referee loop example

## Goal

Fix a small broken `slugify` helper in `work/` so every test in `test_slugify.py` passes. The check is `python -m unittest -q` (stdlib only). Cursor (or any host agent) edits the code; Proofhouse does not call a model. After each edit, Proofhouse runs the check and appends one line to `referee-run/rounds.jsonl`.

## Commands

From the repository root:

```bash
uv run --no-sync proofhouse referee start "make every slugify test pass" \
  --check "python -m unittest -q" \
  --folder examples/host-mode/loop/work \
  --out examples/host-mode/loop/referee-run \
  --rounds 8 \
  --agent cursor \
  --allow-commands

uv run --no-sync proofhouse referee round examples/host-mode/loop/referee-run \
  --summary "<what you changed>" \
  --agent cursor \
  --allow-commands

uv run --no-sync proofhouse referee status examples/host-mode/loop/referee-run --json
```

`referee round` exits `0` when the check passes, `10` to keep going, and `11` when the round or time limit is hit without a pass.

## Rounds (from `referee-run/rounds.jsonl`)

| Round | What changed | Check result |
|------:|--------------|--------------|
| 1 | lowercase the title before building the slug | fail (exit 1) |
| 2 | strip accents with NFKD before lowercasing | fail (exit 1) |
| 3 | collapse runs of non-alphanumerics to a single dash | fail (exit 1) |
| 4 | strip leading and trailing dashes | fail (exit 1) |
| 5 | truncate at max_length on the last dash, not mid-word | pass (exit 0) |

## What this does and does not prove

Proofhouse made no paid or hosted model call in this run (`mode: host` in `referee-run/loop.json`). It ran the agent’s shell check after each round and wrote a plain-file record (`loop.json`, `rounds.jsonl`). That record is a log you can read and diff; it is not tamper-proof—the work folder and summaries still come from the agent. Stopping is governed by the check passing, or by `--rounds` / `--for` limits (`referee round` exit `11`). This example is one small bug-fix job, not a guarantee about larger or adversarial loops.

The record was made in a temporary work copy; the absolute folder path Proofhouse stored (it holds a personal path) was rewritten to the repo-relative `examples/host-mode/loop/work` in `loop.json` and in the traceback lines of `rounds.jsonl`. Nothing else in the record was changed.
