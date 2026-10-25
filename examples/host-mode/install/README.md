# install and uninstall, proved on a throwaway folder

`prove.py` installs an agent, a rule (Claude Code and Cursor) and an MCP server into a temporary project, checks the installed server answers, then uninstalls everything and compares every file with what it was before. `proof-output.txt` is a saved run. `release-notes-writer.md` is the agent being installed; `../install-record/` holds its two rounds.

```bash
uv run --no-sync python examples/host-mode/install/prove.py
```

Known weakness shown in the output: uninstall leaves empty `.claude` and `.cursor` folders, and keeps two backup copies in the Proofhouse home.
