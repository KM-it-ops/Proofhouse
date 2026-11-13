# Stage 3 hard cases

88 cases across 44 subcommands. What broke, what held and what it cost: [findings.md](findings.md).

| Case | What makes it hard | Verdict | What happened | Seconds |
| --- | --- | --- | --- | ---: |
| validate-1 | An IR file has a .json name but contains binary bytes. | held | Exit 3; validate: error | 1.581 |
| validate-2 | A sparse IR file is one byte past the documented 8 MiB limit. | held | Exit 2; error: EVR-RES-0001: input exceeds MAX_INPUT_BYTES | 1.607 |
| inspect-1 | An input path names a directory instead of an IR file. | held | Exit 2; error: [Errno 13] Permission denied: 'looks.json' | 0.931 |
| inspect-2 | A JSON file repeats a key, which must not be silently accepted. | held | Exit 3; inspect: error | 0.948 |
| compile-1 | A binary input must fail before creating the requested output folder. | held | Exit 3; compile: error | 0.997 |
| compile-2 | An unsupported adapter and an existing output folder cannot produce an artifact (adapter failure is documented as exit 6). | held | Exit 6; compile: error | 1.263 |
| adapters-1 | Repeated JSON switches should still return one parseable registry result. | held | Exit 0; {"command": "adapters", "contract_version": "0.1.0", "data": {"adapters": [{"adapter_id": "fake", "adapter_version": "0.1.0", "artifact_kinds": ["compiled_promp | 1.244 |
| adapters-2 | A plausible but unsupported adapter filter must be rejected. | held | Exit 2; usage: proofhouse [-h] [--version] | 1.074 |
| doctor-1 | Doctor runs with every credential-like variable stripped. | held | Exit 0; {"command": "doctor", "contract_version": "0.1.0", "data": {"checks": [{"detail": "3.12.12 (requires >= 3.11)", "name": "python_version", "ok": true}, {"detail" | 1.026 |
| doctor-2 | A repeated output switch must not turn a health result into a traceback. | held | Exit 0; {"command": "doctor", "contract_version": "0.1.0", "data": {"checks": [{"detail": "3.12.12 (requires >= 3.11)", "name": "python_version", "ok": true}, {"detail" | 0.934 |
| closed-loop-1 | A negative repair budget is outside the advertised 0 to 2 range. | held | Exit 2; usage: proofhouse closed-loop [-h] [--repair-budget {0,1,2}] | 1.014 |
| closed-loop-2 | A product dataset without its rubric must be refused before reading input. | held | Exit 2; closed-loop: error | 0.916 |
| compile-requirements-1 | A JSON envelope with duplicate keys must be rejected. | held | Exit 2; compile-requirements: error | 0.971 |
| compile-requirements-2 | A binary file using a .json extension must be rejected cleanly. | held | Exit 2; compile-requirements: error | 0.985 |
| evaluate-product-1 | The dataset path is a folder while the rubric is a real file. | held | Exit 2; evaluate-product: error | 1.119 |
| evaluate-product-2 | The rubric path is a folder while the dataset is a real file. | held | Exit 2; evaluate-product: error | 1.23 |
| closed-loop-bridged-008-1 | A repeated JSON key must fail before bridging requirements. | held | Exit 2; closed-loop-bridged-008: error | 0.962 |
| closed-loop-bridged-008-2 | An enormous repair budget must fail argument parsing. | held | Exit 2; usage: proofhouse closed-loop-bridged-008 [-h] [--repair-budget {0,1,2}] | 0.931 |
| route-1 | Routing constraints contain a JSON array where an object is required. | held | Exit 2; route: error | 1.034 |
| route-2 | Routing constraints contain truncated JSON. | held | Exit 2; route: error | 0.929 |
| assay-1 | Claims are stored as a JSON object instead of the required array. | held | Exit 2; assay: error | 0.918 |
| assay-2 | A .json claims file contains binary bytes. | held | Exit 2; assay: error | 0.952 |
| proof-1 | Empty artifact and spec must never be described as reviewed. | held | Exit 3; proof: UNJUDGED | 0.938 |
| proof-2 | Unicode claims and a contradictory spec must remain unjudged without a review pass. | held | Exit 3; {"findings": [], "passes": 0, "status": "UNJUDGED"} | 0.944 |
| execute-openai-1 | Live execution receives an IR file but no explicit opt-in; the documented refusal is EXE-OPT-0001 with exit 7. | held | Exit 7; {"command": "execute-openai", "diagnostics": ["EXE-OPT-0001"], "envelope": {"q1_model": "gpt-5.6-luna", "q1_unpicked": false, "single_request": true}, "status": | 0.974 |
| execute-openai-2 | A provider and target URL conflict must fail before any network access. | held | Exit 2; error: --target-url cannot be used with --provider | 0.923 |
| case-1 | A new case collides with an existing folder holding another user's file. | held | Exit 2; error: case directory already exists: case dir | 0.971 |
| case-2 | An objective file path names a folder. | held | Exit 2; error: objective file not found: goal.txt | 0.929 |
| optimize-1 | The deprecated alias must still reject a case folder that already exists. | held | Exit 2; notice: 'proofhouse optimize' is now 'proofhouse case' (same subcommands and flags); the optimize alias will be removed after 0.5 | 0.93 |
| optimize-2 | The alias status command sees a half-written case folder. | held | Exit 2; notice: 'proofhouse optimize' is now 'proofhouse case' (same subcommands and flags); the optimize alias will be removed after 0.5 | 0.93 |
| demo-1 | The offline demo gets a workspace path that is a file. | held | Exit 2; error: [WinError 183] Cannot create a file when that file already exists: '<case>\\workspace' | 0.943 |
| demo-2 | The offline demo gets an already populated workspace and must preserve its file. | held | Exit 0; reference workflow: OK in 23.5s -- v1 FAIL ['ACC', 'CITE', 'NOGUESS', 'UNK'], v2 PASS with 4 constraints satisfied; export/import reproduced; workspace <case>\w | 24.525 |
| models-1 | A model name with Unicode has no local notes and cannot trigger research. | held | Exit 0; warning: no notes for "unknown-?"; using the generic profile (source=fallback) | 0.933 |
| models-2 | Forgetting a never-cached model must not create a notes file. | held | Exit 2; error: nothing cached for "never-cached-?" | 0.931 |
| install-skill-1 | A bundle path names a plain text file rather than a skill archive (environment failure, exit 7). | held | Exit 7; error: bundle unreadable: fake.skill: File is not a zip file | 1.017 |
| install-skill-2 | A bundle folder has no SKILL.md and must leave the destination empty. | held | Exit 7; error: installed skill failed verification: SKILL.md missing; nothing was installed in <case>\skills | 0.951 |
| uninstall-skill-1 | A named skill was never installed in the isolated destination. | held | Exit 2; error: Proofhouse has no record of installing <case>\skills\proofhouse; it removes only what it installed. Nothing was removed. | 0.927 |
| uninstall-skill-2 | An untracked skill folder must not be removed without a matching install record. | held | Exit 2; error: Proofhouse has no record of installing <case>\skills\proofhouse; it removes only what it installed. Nothing was removed. | 0.943 |
| check-1 | A rule path is a directory instead of a rules file. | held | Exit 2; error: rules.md is a folder; a rule check needs one file (for example a .md file) | 1.004 |
| check-2 | A skill folder is half written and lacks SKILL.md, so it is not a skill (usage error, exit 2). | held | Exit 2; error: SKILL.md not found in skill dir | 1.032 |
| record-1 | A score below zero must be rejected before recording anything. | held | Exit 2; no output | 1.001 |
| record-2 | The same agent cannot also be its independent judge. | held | Exit 2; error: judge must be a different agent from the one that wrote this version | 0.911 |
| render-1 | An empty format list must fail before FFmpeg sees a folder. | held | Exit 2; error: name at least one format | 0.938 |
| render-2 | A movie folder is actually a file. | held | Exit 2; error: script.json not found in film | 0.94 |
| make-1 | A paid maker request has no spending ceiling or credential. | held | Exit 2; error: name a spending limit for the whole make (--max-cost-usd) | 1.128 |
| make-2 | A video request has no visual service or model. | broke | missing text 'video needs' | 0.932 |
| providers-1 | An invalid negative cloud price must not alter the provider registry. | held | Exit 2; error: --input must be a plain decimal such as 2.50 (USD per million tokens), above zero for a paid provider | 0.954 |
| providers-2 | Removing a shipped provider must leave the local registry untouched. | held | Exit 2; error: openai is not in your providers file (<case>\proofhouse_home\providers.json); shipped providers can be overridden, not removed | 1.231 |
| run-1 | A paid run with a (fake) key and prompt text lacks the required spending ceiling. | held | Exit 7; PHC-RUN-0002: name a spending limit for a paid provider (--max-cost-usd) | 1.158 |
| run-2 | A prompt file is actually a directory. | held | Exit 2; error: cannot read a file: [Errno 13] Permission denied: 'prompt.txt' | 1.055 |
| loop-1 | A negative duration is not a valid length of time. | held | Exit 2; error: '-1' is not a length of time; use for example 90, 30s, 5m, 2h or 1d | 0.971 |
| loop-2 | A watch loop without an interval must refuse to start. | held | Exit 2; error: a watch needs --every (seconds between looks) | 1.046 |
| referee-1 | Starting a check without opt-in must not run a shell command. | held | Exit 2; error: a check command needs --allow-commands | 0.913 |
| referee-2 | A record folder is only half written before status reads it. | held | Exit 2; error: loop.json in <case>\rounds is not readable JSON | 0.926 |
| compare-1 | Saved-output mode receives a directory instead of an output file. | held | Exit 2; error: file not found: <case>\output.txt | 0.925 |
| compare-2 | Saved outputs and live model selections conflict and must never call a model. | held | Exit 2; error: --entry and --on are mutually exclusive | 1.031 |
| train-1 | An empty training file cannot be divided into training and validation data. | held | Exit 2; error: empty.jsonl has no examples | 1.021 |
| train-2 | Training start has a negative epoch count, which used to price as free and upload first. | held | Exit 7; PHC-RUN-0002: epochs must be a whole number from 1 to 50; nothing was uploaded | 1.028 |
| addons-1 | An add-on folder lacks the required addon.json manifest. | held | Exit 2; error: pack\addon.json is unreadable: FileNotFoundError | 1.025 |
| addons-2 | Removing a pack that was never installed must leave other state alone. | held | Exit 2; error: no installed pack named 'never-installed'; see `proofhouse addons list` | 1.051 |
| deploy-1 | A deployment dry run receives a path that is a file. | held | Exit 2; error: <case>\site has no index.html to deploy | 1.051 |
| deploy-2 | A populated site can produce a dry-run command without deploying it. | held | Exit 0; {"command": ["netlify", "deploy", "--dir", "<case>\\site with spaces", "--prod"], "folder": "<case>\\site with spaces", "status": "dry run", "target": "netlify" | 0.94 |
| hosts-1 | The host registry should remain readable without any account credentials. | held | Exit 0; {"hosts": [{"agent": {"format": "file", "project": "{project}/.claude/agents/{name}.md", "user": "~/.claude/agents/{name}.md"}, "aliases": ["claude code", "clau | 0.999 |
| hosts-2 | A repeated JSON flag should still return one host registry. | held | Exit 0; {"hosts": [{"agent": {"format": "file", "project": "{project}/.claude/agents/{name}.md", "user": "~/.claude/agents/{name}.md"}, "aliases": ["claude code", "clau | 1.024 |
| install-1 | An agent file lacks required frontmatter and must not be installed into the project. | held | Exit 2; error: an agent file needs frontmatter with name: and description: (or pass --name) | 1.041 |
| install-2 | An MCP server has no command and cannot be installed into the project. | held | Exit 2; error: an MCP server needs --command | 0.988 |
| uninstall-1 | A project install was never recorded and must not remove anything. | held | Exit 2; error: Proofhouse has no record of installing agent missing into Cursor at <case>\project\.cursor\agents\missing.md | 0.977 |
| uninstall-2 | An existing hand-written rule must survive an uninstall without a record. | held | Exit 2; error: Proofhouse has no record of installing rule handmade into Cursor at <case>\project\.cursor\rules\handmade.mdc | 0.952 |
| generate-1 | A paid image request with a (fake) key has no spending ceiling. | held | Exit 7; PHC-RUN-0002: name a spending limit for a paid service (--max-cost-usd) | 0.983 |
| generate-2 | A negative video length must be rejected before any paid request is priced or sent. | held | Exit 2; error: --seconds must be a whole number of seconds, 1 or more | 0.998 |
| media-1 | A negative declared unit price must not be saved. | held | Exit 2; error: --usd must be a plain decimal above zero (USD per image) | 0.975 |
| media-2 | A media service template is actually a binary file. | held | Exit 2; error: 'utf-8' codec can't decode byte 0xff in position 1: invalid start byte | 0.997 |
| eval-1 | A JSONL dataset contains a broken line after a valid-looking extension. | held | Exit 1; Dataset validation failed: data with spaces.jsonl | 1.016 |
| eval-2 | A loadout id does not exist and must not create output. | held | Exit 2; error: [Errno 2] No such file or directory: 'loadouts\\legendary_loadouts.json' | 1.012 |
| scan-1 | The scan target is a file instead of a project folder. | held | Exit 2; scan: not a folder: <case>\project.txt | 0.965 |
| scan-2 | A directory with a Unicode name and binary file must still scan safely. | held | Exit 0; { | 0.944 |
| agent-server-1 | The named agent is not in the shipped or user agent table, so no server may start. | held | Exit 2; error: unknown agent 'no-such-agent'. Known: claude, codex, grok | 0.948 |
| agent-server-2 | The port is not a number, which must fail argument parsing before anything listens. | held | Exit 2; usage: proofhouse agent-server [-h] [--port PORT] [--timeout TIMEOUT] agent | 0.925 |
| connect-1 | Undo is asked for on a machine connect never touched; it must say so and change nothing. | held | Exit 0; Nothing to undo: `proofhouse connect` has not changed anything on this machine. | 0.934 |
| connect-2 | A stray word after --undo must fail argument parsing before any app's settings are read. | held | Exit 2; usage: proofhouse [-h] [--version] | 0.937 |
| mcp-1 | The agent option has no value, which must fail argument parsing before the tools start. | held | Exit 2; usage: proofhouse mcp [-h] [--agent AGENT] | 1.328 |
| mcp-2 | The app that started the tools goes away at once (no input); they must end cleanly and leave nothing behind. | held | Exit 0; no output | 1.181 |
| setup-1 | A tool is declared as a program but no program name is given, and nothing may be saved. | held | Exit 2; error: a command-line tool needs --command: the program's name, as you type it in a terminal | 0.977 |
| setup-2 | Forgetting a tool that was never declared must say so and leave other state alone. | held | Exit 2; error: no declared tool named 'never-declared'; see `proofhouse setup` | 0.938 |
| watch-1 | A film file is really text, so FFmpeg cannot read a picture and nothing is written. | held | Exit 2; error: FFmpeg could not read the picture in film.mp4 | 1.61 |
| watch-2 | More labels than films must fail before any film is read. | held | Exit 2; error: more --captions or --name values than films | 0.972 |
| parts-1 | The part registry must serialize in an isolated home with no keys. | held | Exit 0; { | 0.956 |
| parts-2 | An unsupported filter must fail rather than print an incomplete part list. | held | Exit 2; usage: proofhouse [-h] [--version] | 0.958 |

## Broke cases

- **make-2**: missing text 'video needs'
