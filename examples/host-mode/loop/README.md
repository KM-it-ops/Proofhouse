# Host-mode referee loop example

## Goal

Fix a small markdown-to-HTML converter in `work/`. Logic is split across four modules (`escape.py`, `inline.py`, `blocks.py`, `markdown.py`). Forty tests in `test_minimd.py` start failing; you edit only those four files until every test passes. Check: `python -m unittest -q` (stdlib only). Cursor (or any host agent) edits the code; Proofhouse does not call a model. After each edit, Proofhouse runs the check and appends one line to `referee-run/rounds.jsonl`.

## Commands

From the repository root:

```bash
uv run --no-sync proofhouse referee start "make every minimd test pass" \
  --check "python -m unittest -q" \
  --folder examples/host-mode/loop/work \
  --out examples/host-mode/loop/referee-run \
  --rounds 20 \
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
| 1 | implement escape_html for the five HTML special characters | fail (exit 1) |
| 2 | implement render_inline for emphasis, strong, code spans, links, and backslash escapes | fail (exit 1) |
| 3 | implement split_blocks with blank-line splits and fenced-code grouping | fail (exit 1) |
| 4 | render ATX headings h1 through h6 with inline formatting inside | fail (exit 1) |
| 5 | render paragraphs and horizontal rules for --- and *** | fail (exit 1) |
| 6 | render unordered and ordered lists with inline formatting in items | fail (exit 1) |
| 7 | render fenced code blocks with escaped bodies and blockquotes from > lines | pass (exit 0) |

## What this does and does not prove

Proofhouse made no paid or hosted model call in this run (`mode: host` in `referee-run/loop.json`). It ran the agent’s shell check after each round and wrote a plain-file record (`loop.json`, `rounds.jsonl`). That record is a log you can read and diff; it is not tamper-proof—the work folder and summaries still come from the agent. Stopping is governed by the check passing, or by `--rounds` / `--for` limits (`referee round` exit `11`). This example is one small bug-fix job (a markdown converter with forty tests), not a guarantee about larger or adversarial loops.

The record was made in a temporary work copy; the absolute folder path Proofhouse stored (it holds a personal path) was rewritten to the repo-relative `examples/host-mode/loop/work` in `loop.json` and in the traceback lines of `rounds.jsonl`. Nothing else in the record was changed.
