# deploy, dry run only

`prove.py` runs `proofhouse deploy --dry-run` for the example site on all four targets with the network and program launching switched off, so nothing can be published. `proof-output.txt` is a saved run. `copy.md` is the runbook; `../deploy-record/` holds its two rounds.

```bash
uv run --no-sync python examples/host-mode/deploy/prove.py
```

A real deploy needs the hosting tool installed and its key in your environment. It is not exercised here.
