# Troubleshooting

| Message | Meaning | What to do |
|---|---|---|
| `revision vN content does not match its recorded sha256` | `revisions/vN.json` was edited after it was recorded | Restore the original, or record the edited text as a new revision with `optimize record`. |
| `revision vN sha256 differs from the digest recorded in case.json` | The revision file and `case.json` disagree | Same as above; do not edit digests by hand. |
| `run R<k> output does not match its recorded sha256` | A recorded output was edited | Record the corrected output with `optimize output add` (a new run id). |
| `run R<k> in case.json differs from its run file`, `case.json lists run R<k> twice`, `run R<k> cost must have exactly ...` or `run R<k> cost has a usd figure` | A run's entry in `case.json` was edited (or a bundle was altered and its manifest recomputed) | Nothing was imported or changed. Restore `case.json`, or get a fresh export; do not edit run entries by hand. |
| `vN.json already exists; another writer may have recorded it` | A revision/run file exists that `case.json` does not list (an interrupted or concurrent record) | Inspect the file; move it aside if it is not yours, then record again. |
| check shows `UNJUDGED` with `stale_verdict: true` | Your verdict was for different text or a different criterion definition | Record the verdict again for the current revision (`optimize verdict`). |
| check shows `NOT_EVALUATED` | An output criterion has no recorded output for this revision | `optimize output add --revision N ...` |
| constraint `no_evidence` | The accepted constraint has no linked criterion (or a linked one has no result) | `optimize constraints link --id K<n> --criterion <id>` |
| closed-loop `BLOCKED` with `EVR-INP-000x` | The input document has the wrong shape or type | The message names the field; `network_allowed` must be a JSON boolean. |
| closed-loop `BLOCKED` with `EVR-COV-0001` | The product-eval dataset has no case for a mandatory requirement | Add a case whose `req_ids` includes it. |
| closed-loop `FAIL` with `EVR-REP-0005` | Product evaluation failed; repair is not attempted against imported observations | Revise the prompt, produce new outputs, and evaluate again. |
| `execute-openai` `EXE-SEM-0001` | The IR needs something a single request cannot provide (required knowledge content, persistent memory) | Nothing was sent. Remove or restructure that requirement, or use another path. |
| `execute-openai` `EXE-CEIL-0001` | Missing or invalid ceilings (`NaN`, `Infinity`, non-positive) | Pass a positive integer `--max-output-tokens` and a positive finite `--max-cost-usd`. The cost value is recorded, not enforced. |
| `install-skill` error mentioning `no agent chosen`, `name an agent` or `found ... agent folder` | No agent was named and none could be chosen: the question got no valid answer, or a program ran it with no single agent folder in your home directory | Nothing was installed. Answer the question in a terminal, or pass `--host claude`, `--host cursor` or `--dest <skills folder>`. |
| `install-skill` error mentioning `nothing was installed` or `previous installation restored` | The new bundle failed validation or could not be placed | Your previous skill is unchanged. Forced replacements keep the old copy under `PROOFHOUSE_HOME/skill-backups/`. |
| `install-skill --force` error mentioning `is a link or junction` | The skill folder is, or holds, a link (for example to your own checkout); its backup could not be restored exactly | Nothing was changed. Remove or replace the link yourself, then install again. |
| `uninstall-skill` error mentioning `no longer matches what the install replaced` | The backup under `PROOFHOUSE_HOME/skill-backups/` was changed after the install | Nothing was removed. Put the backup back as it was, or remove the skill folder yourself. |
| `uninstall-skill --force` error mentioning `is a link or junction` | The skill folder holds a link (for example `node_modules` pointing elsewhere); the safety copy taken before removal would follow it | Nothing was removed. Remove or replace the link yourself, then uninstall again. |
| `install-skill` error mentioning `appeared while the skill was being installed` | Another program created the skill folder while Proofhouse was installing | Nothing was installed. Check what is there, then re-run with `--force` to replace it. |
| `install-skill --force` or `uninstall-skill --force` error mentioning `changed while it was being backed up` | Something wrote to the skill folder while Proofhouse copied it | Nothing was changed. Close whatever is writing to it, then run the command again. |
| `install-skill` or `uninstall-skill` error mentioning `a copy is left at` | A backup that failed or did not match could not be removed | The skill folder is as the rest of the message says. Delete the named copy once you no longer need it. |
| `install-skill` or `uninstall-skill` error mentioning `record not restored` | The command failed and could not put its install record under `PROOFHOUSE_HOME/skill-installs/` back | The skill folder is as the rest of the message says, but the named record no longer describes it. Move that record file aside before running `install-skill` or `uninstall-skill` on that folder again. |
| `PHC-SKILL-0003` `was replaced while it was being read` | A file or folder in the skill was swapped while Proofhouse read it | Nothing was recorded or installed. Make sure nothing else is changing the folder, then run the command again. |
| import: `sha256 does not match the manifest` | The bundle was altered after export | Get a fresh export; nothing was written. |
| Garbled output on Windows consoles | Legacy code page | Set `PYTHONUTF8=1`. |
