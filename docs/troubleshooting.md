# Troubleshooting

| Message | Meaning | What to do |
|---|---|---|
| `revision vN content does not match its recorded sha256` | `revisions/vN.json` was edited after it was recorded | Restore the original, or record the edited text as a new revision with `optimize record`. |
| `revision vN sha256 differs from the digest recorded in case.json` | The revision file and `case.json` disagree | Same as above; do not edit digests by hand. |
| `run R<k> output does not match its recorded sha256` | A recorded output was edited | Record the corrected output with `optimize output add` (a new run id). |
| `vN.json already exists; another writer may have recorded it` | A revision/run file exists that `case.json` does not list (an interrupted or concurrent record) | Inspect the file; move it aside if it is not yours, then record again. |
| check shows `UNJUDGED` with `stale_verdict: true` | Your verdict was for different text or a different criterion definition | Record the verdict again for the current revision (`optimize verdict`). |
| check shows `NOT_EVALUATED` | An output criterion has no recorded output for this revision | `optimize output add --revision N ...` |
| constraint `no_evidence` | The accepted constraint has no linked criterion (or a linked one has no result) | `optimize constraints link --id K<n> --criterion <id>` |
| closed-loop `BLOCKED` with `EVR-INP-000x` | The input document has the wrong shape or type | The message names the field; `network_allowed` must be a JSON boolean. |
| closed-loop `BLOCKED` with `EVR-COV-0001` | The product-eval dataset has no case for a mandatory requirement | Add a case whose `req_ids` includes it. |
| closed-loop `FAIL` with `EVR-REP-0005` | Product evaluation failed; repair is not attempted against imported observations | Revise the prompt, produce new outputs, and evaluate again. |
| `execute-openai` `EXE-SEM-0001` | The IR needs something a single request cannot provide (required knowledge content, persistent memory) | Nothing was sent. Remove or restructure that requirement, or use another path. |
| `execute-openai` `EXE-CEIL-0001` | Missing or invalid ceilings (`NaN`, `Infinity`, non-positive) | Pass a positive integer `--max-output-tokens` and a positive finite `--max-cost-usd`. The cost value is recorded, not enforced. |
| `install-skill` error mentioning `nothing was installed` or `previous installation restored` | The new bundle failed validation or could not be placed | Your previous skill is unchanged. Forced replacements keep the old copy under `PROOFHOUSE_HOME/skill-backups/`. |
| import: `sha256 does not match the manifest` | The bundle was altered after export | Get a fresh export; nothing was written. |
| Garbled output on Windows consoles | Legacy code page | Set `PYTHONUTF8=1`. |
