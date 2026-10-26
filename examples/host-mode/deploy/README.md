# deploy, dry run only

`prove.py` runs `proofhouse deploy --dry-run` for the example site on all four targets with the network and program launching switched off, so nothing can be published. `proof-output.txt` is a saved run. `copy.md` is the runbook; `../deploy-record/` holds its two rounds.

```bash
uv run --no-sync python examples/host-mode/deploy/prove.py
```

A real deploy needs the hosting tool installed and its key in your environment. It is not exercised here.

What this does not prove: that anything is live. Nothing was published, the hosting tools and their keys were never touched, and the check covers the one example site on the four targets in a dry run only.
