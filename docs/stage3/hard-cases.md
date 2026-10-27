# Stage 3 hard cases

78 cases across 39 subcommands. What broke, what held and what it cost: [findings.md](findings.md).

| Case | What makes it hard | Verdict | What happened | Seconds |
| --- | --- | --- | --- | ---: |
| validate-1 | An IR file has a .json name but contains binary bytes. | held | Exit 3; validate: error | 2.051 |
| validate-2 | A sparse IR file is one byte past the documented 8 MiB limit. | held | Exit 2; error: EVR-RES-0001: input exceeds MAX_INPUT_BYTES | 1.868 |
| inspect-1 | An input path names a directory instead of an IR file. | held | Exit 2; error: [Errno 13] Permission denied: 'looks.json' | 1.587 |
| inspect-2 | A JSON file repeats a key, which must not be silently accepted. | held | Exit 3; inspect: error | 1.608 |
| compile-1 | A binary input must fail before creating the requested output folder. | held | Exit 3; compile: error | 1.426 |
| compile-2 | An unsupported adapter and an existing output folder cannot produce an artifact (adapter failure is documented as exit 6). | held | Exit 6; compile: error | 1.548 |
| adapters-1 | Repeated JSON switches should still return one parseable registry result. | held | Exit 0; {"command": "adapters", "contract_version": "0.1.0", "data": {"adapters": [{"adapter_id": "fake", "adapter_version": "0.1.0", "artifact_kinds": ["compiled_promp | 1.575 |
| adapters-2 | A plausible but unsupported adapter filter must be rejected. | held | Exit 2; usage: proofhouse-compiler [-h] | 1.568 |
| doctor-1 | Doctor runs with every credential-like variable stripped. | held | Exit 0; {"command": "doctor", "contract_version": "0.1.0", "data": {"checks": [{"detail": "3.14.6 (requires >= 3.11)", "name": "python_version", "ok": true}, {"detail": | 1.535 |
| doctor-2 | A repeated output switch must not turn a health result into a traceback. | held | Exit 0; {"command": "doctor", "contract_version": "0.1.0", "data": {"checks": [{"detail": "3.14.6 (requires >= 3.11)", "name": "python_version", "ok": true}, {"detail": | 1.547 |
| closed-loop-1 | A negative repair budget is outside the advertised 0 to 2 range. | held | Exit 2; usage: proofhouse-compiler closed-loop [-h] [--repair-budget {0,1,2}] | 1.574 |
| closed-loop-2 | A product dataset without its rubric must be refused before reading input. | held | Exit 2; closed-loop: error | 1.511 |
| compile-requirements-1 | A JSON envelope with duplicate keys must be rejected. | held | Exit 2; compile-requirements: error | 1.482 |
| compile-requirements-2 | A binary file using a .json extension must be rejected cleanly. | held | Exit 2; compile-requirements: error | 1.408 |
| evaluate-product-1 | The dataset path is a folder while the rubric is a real file. | held | Exit 2; evaluate-product: error | 1.751 |
| evaluate-product-2 | The rubric path is a folder while the dataset is a real file. | held | Exit 2; evaluate-product: error | 2.102 |
| closed-loop-bridged-008-1 | A repeated JSON key must fail before bridging requirements. | held | Exit 2; closed-loop-bridged-008: error | 1.522 |
| closed-loop-bridged-008-2 | An enormous repair budget must fail argument parsing. | held | Exit 2; usage: proofhouse-compiler closed-loop-bridged-008 [-h] | 1.53 |
| route-1 | Routing constraints contain a JSON array where an object is required. | held | Exit 2; route: error | 1.615 |
| route-2 | Routing constraints contain truncated JSON. | held | Exit 2; route: error | 1.565 |
| assay-1 | Claims are stored as a JSON object instead of the required array. | held | Exit 2; assay: error | 1.786 |
| assay-2 | A .json claims file contains binary bytes. | held | Exit 2; assay: error | 1.583 |
| proof-1 | Empty artifact and spec must never be described as reviewed. | held | Exit 3; proof: UNJUDGED | 1.529 |
| proof-2 | Unicode claims and a contradictory spec must remain unjudged without a review pass. | held | Exit 3; {"findings": [], "passes": 0, "status": "UNJUDGED"} | 1.601 |
| execute-openai-1 | Live execution receives an IR file but no explicit opt-in; the documented refusal is EXE-OPT-0001 with exit 7. | held | Exit 7; {"command": "execute-openai", "diagnostics": ["EXE-OPT-0001"], "envelope": {"q1_model": "gpt-5.6-luna", "q1_unpicked": false, "single_request": true}, "status": | 1.488 |
| execute-openai-2 | A provider and target URL conflict must fail before any network access. | held | Exit 2; error: --target-url cannot be used with --provider | 1.639 |
| case-1 | A new case collides with an existing folder holding another user's file. | held | Exit 2; error: case directory already exists: case dir | 1.632 |
| case-2 | An objective file path names a folder. | held | Exit 2; error: objective file not found: goal.txt | 1.423 |
| optimize-1 | The deprecated alias must still reject a case folder that already exists. | held | Exit 2; notice: 'proofhouse optimize' is now 'proofhouse case' (same subcommands and flags); the optimize alias will be removed after 0.5 | 1.537 |
| optimize-2 | The alias status command sees a half-written case folder. | held | Exit 2; notice: 'proofhouse optimize' is now 'proofhouse case' (same subcommands and flags); the optimize alias will be removed after 0.5 | 1.612 |
| demo-1 | The offline demo gets a workspace path that is a file. | held | Exit 2; error: [WinError 183] Cannot create a file when that file already exists: '<case>\\workspace' | 1.413 |
| demo-2 | The offline demo gets an already populated workspace and must preserve its file. | held | Exit 0; reference workflow: OK in 36.0s -- v1 FAIL ['ACC', 'CITE', 'NOGUESS', 'UNK'], v2 PASS with 4 constraints satisfied; export/import reproduced; workspace <case>\w | 37.553 |
| models-1 | A model name with Unicode has no local notes and cannot trigger research. | held | Exit 0; warning: no notes for "unknown-?"; using the generic profile (source=fallback) | 1.512 |
| models-2 | Forgetting a never-cached model must not create a notes file. | held | Exit 2; error: nothing cached for "never-cached-?" | 1.418 |
| install-skill-1 | A bundle path names a plain text file rather than a skill archive (environment failure, exit 7). | held | Exit 7; error: bundle unreadable: fake.skill: File is not a zip file | 1.529 |
| install-skill-2 | A bundle folder has no SKILL.md and must leave the destination empty. | held | Exit 7; error: installed skill failed verification: SKILL.md missing; nothing was installed in <case>\skills | 1.426 |
| uninstall-skill-1 | A named skill was never installed in the isolated destination. | held | Exit 2; error: Proofhouse has no record of installing <case>\skills\proofhouse; it removes only what it installed. Nothing was removed. | 1.204 |
| uninstall-skill-2 | An untracked skill folder must not be removed without a matching install record. | held | Exit 2; error: Proofhouse has no record of installing <case>\skills\proofhouse; it removes only what it installed. Nothing was removed. | 1.5 |
| check-1 | A rule path is a directory instead of a rules file. | held | Exit 2; error: rules.md | 1.418 |
| check-2 | A skill folder is half written and lacks SKILL.md, so it is not a skill (usage error, exit 2). | held | Exit 2; error: SKILL.md not found in skill dir | 1.362 |
| record-1 | A score below zero must be rejected before recording anything. | held | Exit 2; no output | 1.353 |
| record-2 | The same agent cannot also be its independent judge. | held | Exit 2; error: judge must be a different agent from the one that wrote this version | 1.385 |
| render-1 | An empty format list must fail before FFmpeg sees a folder. | held | Exit 2; error: name at least one format | 1.416 |
| render-2 | A movie folder is actually a file. | held | Exit 2; error: script.json not found in film | 1.469 |
| make-1 | A paid maker request has no spending ceiling or credential. | held | Exit 2; error: name a spending limit for the whole make (--max-cost-usd) | 1.425 |
| make-2 | A video request has no visual service or model. | held | Exit 2; error: a video needs --visual-provider and --visual-model (see `proofhouse media list`) | 1.282 |
| providers-1 | An invalid negative cloud price must not alter the provider registry. | held | Exit 2; error: --input must be a plain decimal such as 2.50 (USD per million tokens), above zero for a paid provider | 1.488 |
| providers-2 | Removing a shipped provider must leave the local registry untouched. | held | Exit 2; error: openai is not in your providers file (<case>\proofhouse_home\providers.json); shipped providers can be overridden, not removed | 1.495 |
| run-1 | A paid run with a (fake) key and prompt text lacks the required spending ceiling. | held | Exit 7; PHC-RUN-0002: name a spending limit for a paid provider (--max-cost-usd) | 1.484 |
| run-2 | A prompt file is actually a directory. | held | Exit 2; error: cannot read a file: [Errno 13] Permission denied: 'prompt.txt' | 1.571 |
| loop-1 | A negative duration is not a valid length of time. | held | Exit 2; error: '-1' is not a length of time; use for example 90, 30s, 5m, 2h or 1d | 1.474 |
| loop-2 | A watch loop without an interval must refuse to start. | held | Exit 2; error: a watch needs --every (seconds between looks) | 1.32 |
| referee-1 | Starting a check without opt-in must not run a shell command. | held | Exit 2; error: a check command needs --allow-commands | 1.463 |
| referee-2 | A record folder is only half written before status reads it. | held | Exit 2; error: loop.json in <case>\rounds is not readable JSON | 1.456 |
| compare-1 | Saved-output mode receives a directory instead of an output file. | held | Exit 2; error: file not found: <case>\output.txt | 1.432 |
| compare-2 | Saved outputs and live model selections conflict and must never call a model. | held | Exit 2; error: --entry and --on are mutually exclusive | 1.434 |
| train-1 | An empty training file cannot be divided into training and validation data. | held | Exit 2; error: empty.jsonl has no examples | 1.423 |
| train-2 | Training start has a negative epoch count, which used to price as free and upload first. | held | Exit 7; PHC-RUN-0002: epochs must be a whole number from 1 to 50; nothing was uploaded | 1.515 |
| addons-1 | An add-on folder lacks the required addon.json manifest. | held | Exit 2; error: pack\addon.json is unreadable: FileNotFoundError | 1.712 |
| addons-2 | Removing a pack that was never installed must leave other state alone. | held | Exit 2; error: no installed pack named 'never-installed'; see `proofhouse addons list` | 1.594 |
| deploy-1 | A deployment dry run receives a path that is a file. | held | Exit 2; error: <case>\site has no index.html to deploy | 1.659 |
| deploy-2 | A populated site can produce a dry-run command without deploying it. | held | Exit 0; {"command": ["netlify", "deploy", "--dir", "<case>\\site with spaces", "--prod"], "folder": "<case>\\site with spaces", "status": "dry run", "target": "netlify" | 1.649 |
| hosts-1 | The host registry should remain readable without any account credentials. | held | Exit 0; {"hosts": [{"agent": {"format": "file", "project": "{project}/.claude/agents/{name}.md", "user": "~/.claude/agents/{name}.md"}, "id": "claude", "mcp": {"format" | 1.77 |
| hosts-2 | A repeated JSON flag should still return one host registry. | held | Exit 0; {"hosts": [{"agent": {"format": "file", "project": "{project}/.claude/agents/{name}.md", "user": "~/.claude/agents/{name}.md"}, "id": "claude", "mcp": {"format" | 1.705 |
| install-1 | An agent file lacks required frontmatter and must not be installed into the project. | held | Exit 2; error: an agent file needs frontmatter with name: and description: (or pass --name) | 1.688 |
| install-2 | An MCP server has no command and cannot be installed into the project. | held | Exit 2; error: an MCP server needs --command | 1.688 |
| uninstall-1 | A project install was never recorded and must not remove anything. | held | Exit 2; error: Cursor has no place for agents on your machine | 1.615 |
| uninstall-2 | An existing hand-written rule must survive an uninstall without a record. | held | Exit 2; error: Proofhouse has no record of installing rule handmade into Cursor at <case>\project\.cursor\rules\handmade.mdc | 1.633 |
| generate-1 | A paid image request with a (fake) key has no spending ceiling. | held | Exit 7; PHC-RUN-0002: name a spending limit for a paid service (--max-cost-usd) | 1.62 |
| generate-2 | A negative video length must be rejected before any paid request is priced or sent. | held | Exit 2; error: --seconds must be a whole number of seconds, 1 or more | 1.639 |
| media-1 | A negative declared unit price must not be saved. | held | Exit 2; error: --usd must be a plain decimal above zero (USD per image) | 1.666 |
| media-2 | A media service template is actually a binary file. | held | Exit 2; error: 'utf-8' codec can't decode byte 0xff in position 1: invalid start byte | 1.534 |
| eval-1 | A JSONL dataset contains a broken line after a valid-looking extension. | held | Exit 1; Dataset validation failed: data with spaces.jsonl | 1.639 |
| eval-2 | A loadout id does not exist and must not create output. | held | Exit 2; error: [Errno 2] No such file or directory: 'loadouts\\legendary_loadouts.json' | 1.57 |
| scan-1 | The scan target is a file instead of a project folder. | held | Exit 2; scan: not a folder: <case>\project.txt | 1.585 |
| scan-2 | A directory with a Unicode name and binary file must still scan safely. | held | Exit 0; { | 1.6 |
| parts-1 | The part registry must serialize in an isolated home with no keys. | held | Exit 0; { | 1.687 |
| parts-2 | An unsupported filter must fail rather than print an incomplete part list. | held | Exit 2; usage: proofhouse-compiler [-h] | 1.647 |

## Broke cases

None.
