# Secret Scan Report

## Methodology

Conservative, filename- and content-pattern based scan (no third-party scanner dependency, no secret
values echoed anywhere in this report or in any generated file). Two passes:

1. **Filename patterns**: `.env*`, `*credentials*.json`, `*.pem`/`*.key`/`id_rsa`/`id_ed25519`,
   `secrets*.json|yaml|txt`, any filename containing `token`.
2. **Content patterns** (text files only: `.md .json .txt .csv .py .yml .yaml .toml`, under 5MB):
   PEM private-key blocks, AWS access key IDs (`AKIA...`), OpenAI-style secret keys (`sk-...`),
   GitHub PATs (`ghp_...`), Slack tokens (`xox[baprs]-...`), and generic `password=`/`api_key=` key-value
   patterns.

Scans were run against:
- Each of the four confirmed reviewer working folders in their original locations, before any copying.
- The final `PromptRig-Central` tree after all copies completed (canonical-source, clean-review-corpus,
  review-results, review-working-snapshots).

## Results

**Zero matches in every scan.** No files matching either the filename or content secret patterns were
found in any reviewer working folder or anywhere in the resulting `PromptRig-Central` tree.

| Location scanned | Matches |
|---|---|
| `claude promptrig-review-launch-v0.4` (source) | 0 |
| `gemini promptrig-review-launch-v0.4` (source) | 0 |
| `kimi k3 promptrig audit` (source) | 0 |
| `Codex\codex promptrig v0.4 audit` (source) | 0 |
| `PromptRig-Central\canonical-source` (destination) | 0 |
| `PromptRig-Central\clean-review-corpus` (destination) | 0 |
| `PromptRig-Central\review-results` (destination) | 0 |
| `PromptRig-Central\review-working-snapshots` (destination) | 0 |

## Quarantine

`audit/quarantine/` was created per the standard structure but is **empty** — no suspicious file was
found that required quarantining.

## Out-of-scope material with likely credentials (not scanned in depth, not copied)

`C:\AI\CodexHome` (the Codex CLI's own application state directory) contains `auth.json` and
`.credentials.json` by filename. This directory was excluded from the consolidation entirely on the
grounds that it is not a PromptRig review folder (see `EXCLUSIONS.md`) — it was never opened, read,
copied, or included in any hash/inventory operation, so no determination about its contents beyond the
filenames themselves was made or is needed.
