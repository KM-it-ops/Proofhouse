# Host-mode examples: what each one is, who made it, and what is proved

Everything here was made with **no API key**: an AI app you already use (the "agent") wrote the work, and Proofhouse checked it, kept every version and wrote the record. Tidewatch, Maple & Rye and the other names are invented.

How to read the table:

- **Folder** is the finished thing. **Record** is its history (every version, score and check).
- **Agent** is who wrote it. **Judge** is a different agent that scored it, where there was one. Scores written by the same agent that made the work are that agent's own advice, not proof.
- **Works?** says only what was actually checked. "Record check passed" means Proofhouse's own check of that kind passed on the best version. It is weaker than "I ran it and it did the job".
- **Cost** is what Proofhouse paid. The agents ran on their own subscriptions, and what those cost was not measured.

| Command | Folder / record | Agent | Judge | Works? | Cost |
|---|---|---|---|---|---|
| `record prompt` | `prompt/`, `prompt-record/` | Cursor | none (own 9/10) | Record check passed | $0 |
| `record skill` | `skill/`, `skill-record/` | Cursor, reviewed and fixed by Claude | none (own 9/10) | Record check passed | $0 |
| `record agent` | `agent/`, `agent-record/` | Cursor, reviewed and fixed by Claude | none (own 9/10) | Record check passed | $0 |
| `record rule` | `rule/`, `rule-record/` | Cursor, reviewed and fixed by Claude | none (own 9/10) | Record check passed | $0 |
| `record copy` | `copy/`, `copy-record/` | Cursor | none (own 9/10) | Record check passed | $0 |
| `record mcp` | `mcp/`, `mcp-record/` | Cursor | none (own 9/10) | Record check passed; the server was called by hand and answers. `mcp/` answers bad input with a proper error; the copies in `mcp-record/` are older and stay silent | $0 |
| `record hook` | `hook/`, `hook-record/` | Cursor and Claude | none (own 9/10) | Record check passed; the folder holds its own tests | $0 |
| `record site` | `site/`, `site-record/` | Cursor | none (own 9/10) | Record check passed; the page was opened and works | $0 |
| `record app` | `app/`, `app-record/` | Cursor | none (own 9/10) | Record check passed; not run by hand | $0 |
| `record` + `render video` | `video/`, `video-record/` | Claude Code | none (own 8/10, for the 30 s film) | Both films play to the end with sound. `final.mp4` is 30 s; `final-premium.mp4` is 48.8 s. The record and its score describe the 30 s film | $0 paid. Two clips came from Gemini's free allowance |
| `record launch` | `launch/`, `launch-record/` | Cursor | Codex 5/10 (read the text parts only) | Record check passed. The record's README says the `site` part is `not measured` (its browser check was not run when it was made). Run afterwards with `--allow-commands` on `launch/`, all 36 checks passed, including no JavaScript errors in a real browser; that run is not saved in the record | $0 paid. Same two Gemini clips |
| `compare` | `compare/` | Codex, Grok, Cursor | Claude | Words counted by script; scores are one agent's advice | $0 |
| `referee` (loop) | `loop/` | Cursor | the 40 tests | Finished in 7 of 20 rounds; the check exits 0 | $0 |
| `install` / `uninstall` | `install/`, `install-record/` | Claude | Codex 7/10 | `prove.py` passed every check on a throwaway folder | $0 |
| `deploy --dry-run` | `deploy/`, `deploy-record/` | Claude | Codex 6/10 | `prove.py` passed with the network off. Nothing is published | $0 |
| `train data` | `train/`, `train-record/` | Claude | Codex 7/10 | `prove.py` passed. No model was trained | $0 |

## What this does not prove

- **install, deploy, train:** the proof scripts show the files and refusals behave. A real deploy needs the hosting tool and your key, and a real fine-tune needs a service key and more than 20 examples. Neither was run.
- **Scores:** a score from the same agent that wrote the work is advice. A judge that saw only text (Codex on the launch) cannot judge pictures, voice or music.
- **Video:** the voice, music and motion have been judged only by a person listening, not by any model.
- **Facts:** Tidewatch and the other products are invented, so claims about them are not true or false in the real world.

## Run any proof yourself

```bash
uv run --no-sync python examples/host-mode/install/prove.py
uv run --no-sync python examples/host-mode/deploy/prove.py
uv run --no-sync python examples/host-mode/train/prove.py
```
