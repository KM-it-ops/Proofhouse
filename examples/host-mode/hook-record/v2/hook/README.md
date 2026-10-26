# git-guard (PreToolUse hook)

Blocks an agent from running a short list of destructive shell commands while everything else passes through unchanged.

## What it blocks

- `git push` with `--force`, `-f`, or a `+ref` refspec (`--force-with-lease` is allowed)
- `rm -rf` aimed at `/`, `~`, `$HOME`, or a bare `*`
- `git reset --hard` or `git clean -fd` in the same chained command as `git push`
- `DROP DATABASE` or `DROP TABLE` inside a `psql`, `sqlite3`, or `mysql` invocation

Malformed hook input or non-`Bash` tools exit **0** so a hook bug never stops your session.

## Install (Claude Code)

1. Copy this folder somewhere inside your project (or keep it in this repo).
2. Open **Claude Code** user or project settings (`settings.json`).
3. Add a **PreToolUse** command hook that runs only for **Bash**, pointing at `guard.py` with your Python interpreter.

Example snippet (paths are relative to the folder that contains `guard.py`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python guard.py"
          }
        ]
      }
    ]
  }
}
```

(`matcher` limits the hook to the **Bash** tool; `command` runs with the hook folder as the working directory.)

On Windows, use `python` from your PATH or the full path to `python.exe` in the `command` field. Run the hook with this folder as the working directory, or change `command` to include the path to `guard.py`.

After `proofhouse record hook`, you can also copy `settings-snippet.json` from the record output folder; it is generated for your layout.

## Manual test

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push -f origin main"}}' | python guard.py
echo exit:$?
```

Exit **2** means blocked (reason on stderr). Exit **0** means allowed.
