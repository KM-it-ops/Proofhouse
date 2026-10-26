# git-guard (PreToolUse hook)

Blocks an agent from running a short list of destructive shell commands while everything else passes through unchanged.

## What it blocks

- `git push` with `--force`, `-f`, or a `+ref` refspec (`--force-with-lease` is allowed)
- `rm -r` (with or without `-f`) aimed at `/`, `/*`, `~`, `~/`, `$HOME`, `$USERPROFILE`, `$HOME/*`, or `..` / `../..` (a project folder under your home, such as `rm -rf ~/app/build`, is allowed)
- `git reset --hard` or `git clean -fd` in the same chained command as `git push`
- `DROP DATABASE` or `DROP TABLE` fed to `psql`, `sqlite3`, `mysql` or `mariadb` (on the command line, through a pipe, a here-string or a heredoc). The database shell has to be the command being run: a commit message that only mentions psql is fine
- All of the above when hidden inside `bash -c` / `sh -c` (including `-lc`, `-o pipefail -c`), `eval`, `exec`, `env` (including `-u`), `sudo` (including `-iu user` and `--user root`), `time`, `nohup`, `nice`, `stdbuf`, `timeout`, `setsid`, `xargs`, `$(...)`, backticks, `( )`, `{ }`, `if ... then`, a `NAME="quoted value"` prefix, or called by full path or Windows name such as `/usr/bin/git` or `git.exe`
- A here-document is read the way the shell reads it: `cat > NOTES.md <<'EOF'` followed by text that mentions `git push --force` is just text and is allowed. The same body is checked when a shell runs it (`bash <<EOF`, `... | bash`), when a database shell reads it (`psql <<EOF` with a `DROP`), or when it is unquoted and contains `$(...)`.
- A command nested so deeply that it cannot be inspected is blocked rather than waved through.

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

## Limits

A shell is a full programming language. This hook only inspects the **text** of the Bash command string: it splits chains, pipelines, subshells, and a few wrappers (`bash -c`, `env`, `sudo`, `xargs`, and similar), then pattern-matches known destructive shapes. It is a **seat belt**, not a sandbox.

It does **not** catch, among other things:

- Commands built at runtime (`$VAR`, `${VAR:0:1}`, indirect expansion, `eval` of computed strings unless the payload is a literal `-c` argument we can read).
- Obfuscation (`base64 -d | bash`, scripts written to disk then executed, `source` / `.` of a file). A line such as `echo "<<EOF"` that only looks like a here-document start can hide the lines after it.
- Shell aliases, functions, or `git` aliases configured outside the command line.
- Path tricks and links: `rm -rf /home/..`, `rm -rf /./`, a symlink that points at `/`, `cd / && rm -rf *`, your home folder spelled out (`/home/alice`, `/c/Users/alice`), or an unquoted Windows path with backslashes.
- Commands run somewhere else or one step removed: `docker exec ... psql`, `kubectl exec ...`, `ssh host "git push -f"`, `git submodule foreach`, `git rebase --exec`, and wrappers not in the list above (`watch`, `ionice`).
- Other ways to lose data that are not in the list: `git push origin :main` (deletes a remote branch), `git push --mirror`, `find / -delete`, `dd`, `truncate`.
- Over-blocking: text that merely hands a dangerous command to something else, such as `echo bash -c "git push -f"` or `grep eval ...`, can be blocked. Rephrase it.
- Typos or synonyms that do not match the guarded tokens (`--forc` instead of `--force`).
- Destructive operations outside the listed patterns (for example `dd`, `mkfs`, `curl | bash`, deleting data through APIs instead of `psql`).

A determined agent or user with shell access can always bypass a text guard. Use repository protections (branch rules, protected paths, backups) for real safety.

## How this was checked

Cursor wrote the first version, then an independent Claude Opus review and hand-written probes found gaps that Cursor's own tests had missed. The first pass missed `/usr/bin/git push --force`, `bash -lc` and `$(git push -f)`. The second review found a `NAME="quoted value"` prefix, `sudo -iu`, `timeout`, parentheses, `rm -rf ../..`, `.exe` names, and harmless here-documents being blocked. On Windows, a command containing a character such as `Ł` made the guard fail to read its input and let the command through; it now reads stdin as UTF-8 bytes. `test_guard.py` holds every one of those cases. A writer and a judge from the same model miss the same things, so keep a second reviewer in the loop for guards like this.
