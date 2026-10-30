# Changelog

## Unreleased

### Changed

- The video engine now finishes a film itself. Shots dissolve into each other instead of cutting hard (the film keeps its length, so captions stay on time), and the picture and sound fade in and out. The voice is cleaned up and lightly levelled, the music dips under the voice and comes back when it stops, and the whole mix is brought to a normal listening level. Before, this polish lived only in a one-off example script. Applies to every film the engine makes, including `proofhouse render video`.

## 0.10.1 - first-run fixes

### Added

- `proofhouse setup` looks at your machine (AI tools, local model servers, browser, Node, ffmpeg, git, hosting tools, which provider keys are set, never their values), says what each missing piece would unlock and how to get it, and ends with what you can do now and the first command to try.

- `proofhouse agent-server claude|codex|grok` lets a coding agent you are already logged in to answer as a model provider on this machine only. Each request is one headless call to the agent's own command line, billed to that agent's plan. Add your own agent in `agent_commands.json` with no code change.
- `proofhouse render video` cuts still pictures and video clips together in one film; before, a script that mixed them was refused.

### Fixed

- The hook writer is now told which Claude Code event names exist, and that a git hook is not one. Before, it could pick a git hook name and the hook never ran.
- A saved prompt or learned kind no longer starts with the model's lead-in line ("Here is the improved prompt:").
- First-run dead ends now say what to do next: `check agent` or `check rule` given a folder says a file is expected; an unknown agent for `install-skill` says to pass `--dest`; a local model server that is not running says what to start; a self-judged record is no longer called independent because the labels differ.
- `proofhouse deploy` starts a found tool by its full path, so Windows tools such as `vercel` run; a `--name` the target cannot use is now said, not silently dropped.
- `proofhouse media add` accepts a list, one service, or the wrapped file `media list` style tools write, and names the missing `id` otherwise.
- `proofhouse uninstall` accepts `--into` as well as `--from`, matching `install`.
- `proofhouse render video` prints each file it wrote and how many checks passed.
- The front door sends "a rule that ..." to a rule and "a hook that blocks commits ..." to a hook.
- `proofhouse make` no longer reports a site, app, rule, MCP server or hook as made when the model's reply could not be written. Before, a high judge score on such a version printed "made" with a path to files that did not exist; now that version is never picked, and the result line says how many checks the chosen version passed.

## 0.10.0 - 2026-10-27

### Added

- **Host mode** for agents you already use: `proofhouse check`, `proofhouse record` and `proofhouse render video` need no API key and make no network calls of their own (`--allow-commands` runs model-written code, which may); the `proofhouse-host` skill teaches the write-check-record loop.
- `proofhouse install-skill --skill proofhouse-host` installs that skill from the package itself, no checkout needed (plain `install-skill` still installs `proofhouse`).
- `proofhouse demo` ends by saying where the report is and which commands reopen the case (`case status`, `case check`).
- `proofhouse --version` prints the installed version.

### Changed

- **Checks that did not run are saved as "not measured"**, never as passed. A site check that cannot start a browser, or gets a screenshot at the wrong width, exits 3 and says why.
- `proofhouse --help` names `proofhouse`, the one front door (`proofhouse-compiler` still works as an alias).
- The demo guide states the run time measured on 2026-10-27: about 70 seconds, about 100 seconds for the first run after a clean install.

### Fixed

- **Spending-limit holes:** `train start` refuses a bad epoch count before pricing or uploading anything, and `generate` refuses a length of zero or less before any paid request.
- Clean messages, not tracebacks, for a folder given as a file, a bad or binary claims file, a half-written `case.json`, a model name the console cannot print, and a failed compile (which no longer leaves an empty folder).
- The referee, build, render, hook and train limits each have a test that proves they hold.
- The lock file pins `certifi` 2026.10.23, which drops root certificates whose keys were compromised (it only reaches installs that add the optional `live` extra).
- The unit-desk MCP example refuses requests that are not JSON-RPC 2.0, and its install steps give the full path to `server.py`.
- The film example's shot builder is back, and its README points at the tracked MP4.
- Older saved rounds whose checks never ran are read back as "not measured", not as passed; the site and launch examples are relabelled to match.
- The unit-desk MCP example handed out is now the exact version that was checked and scored (record version 4).
- The public Stage 3 report hides profile folders on Windows, macOS and Linux, including names with spaces and lower-case paths.

### Security

- The README video project forces zod 4.6.6 under Remotion (not part of the Python package).

## 0.9.1 - 2026-10-25

First release published to PyPI. The code is the same as 0.9.0; the package page and the docs changed.

### Changed

- **The README is rewritten for the PyPI page.** It now leads with what Proofhouse makes, how to install it and a first run, and links out for the rest. Links are absolute so they work on PyPI.
- **Detail moved out of the README into the docs:** every make, run and deliver command is in `docs/usage.md`, the `proofhouse case` evidence walk is in `docs/evidence-trail.md`, and how to check the repository, the experimental parts, the design rules and the repository map are in `docs/development.md`.
- The honesty lines (not a hosted service, not isolation, worst-case estimates are not your bill, shipped model notes are unverified) are now checked on the page that carries them.

### Fixed

- Two stale claims in the docs: native app builds are proven on all six platforms, and the `execute-openai` description now says it runs on any provider through the spend gate.

## 0.9.0 - 2026-10-23

### Added

- **Unknown platforms, hosts, deploy targets, and media and training services are learned, not refused.** The chosen model researches the name through the spend gate, and the checked answer is saved in the `learned` add-on pack. The requested use waits for `proofhouse addons approve learned <id>`; learned commands also need `--allow-commands`.
- **Compiled artifacts run on any provider.** `execute-openai --provider ID` sends a compiled artifact to any provider in the shipped list, an add-on, or your own `providers.json`, always through the spend gate. A required capability the provider cannot carry stops the run before sending and is named (`EXE-CAP-0001`). An entry may list `ignores`, capabilities its address accepts and drops; an ignored optional capability is written into the prompt instead. The key comes only from the provider entry's own `key_env`.
- **`proofhouse "<goal>"` answers with make kinds** (agent, mcp, video, ...) and falls back to the older classes only where `make` has none. With `--provider` and `--model` a model picks, through the spend gate, and the built-in rules take over when its answer cannot be used. A goal that could be two kinds gets one short question when a person is at the terminal; unattended, the safer kind is picked and the reason says so. The answer key is `docs/overseer-test-set.md`.
- **Native app builds proven on real machines.** A fixed sample app (`samples/native_build/`, built by `scripts/native_build_sample.py`) builds as a web app and on Windows, macOS, Linux, iOS and Android, with no model and no keys. `.github/workflows/native-builds.yml` runs it on GitHub's machines.
  - iOS builds an unsigned simulator app and Android a debug APK, so neither needs signing set up. Both check that the expected file was made.
  - Desktop output paths come from the app's own `mainBinaryName` and `productName` in `src-tauri/tauri.conf.json`.
- **The model list keeps itself current.** `proofhouse models update` asks every provider you have a key for which models it serves (with that provider's own key, sent only to its own address), and reads the official release pages in `release_sources.json` through the spend gate. New models and AI workspaces go into your catalog; `models list` shows them and says when an update is due. You can add or replace release pages in your own `release_sources.json`. Safeguards: an add-on provider that names another provider's key is not sent it; a page is read only if it ends on https at its own site; at most 5 MB of any answer is read; notes a model picked out of a page are shown by `models show` but are not put into prompts until you review them with `models remember`.
- **A kind Proofhouse does not know is learned, not refused.** A forced or typed kind that is neither built in nor from an add-on is researched by the chosen model through the spend gate, checked like an add-on kind, and saved in the `learned` pack.
- **Grok Bot** is listed as a host. It is xAI's cloud teammate, so `install` says it has no place for rules on your machine.
- **Dashboard browser checks.** Keyboard reach with visible focus, no sideways scroll at 375 px, animations that stop under reduced motion, and the error state, run on every pull request. The same tests must fail on four copies of the dashboard broken on purpose.

### Changed

- **Every learned platform, host, deploy target, and media or training service needs approval before it is used,** with or without a key. `proofhouse addons approve learned <id> --list <list>` approves one entry when that id is in more than one list.
- **The built-in model list is current as of 2026-10-18,** checked against Anthropic's, OpenAI's, Google's and xAI's official pages: Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5; GPT-6 Astra, GPT-6.1 Sol, GPT-6 Sol and GPT-6 Luna; Gemini 4 Argon; Grok 4.7. The models they replace are marked legacy.
- **Running a compiled artifact on a provider checks the send address against the provider's host last,** just before the key is attached, as `proofhouse run` does.
- **One run reads your providers file once.** The run and the spend gate use the same read, so the gate prices the same provider entry the request is sent to.
- The built-in goal rules score every kind and ask on close calls. They were tuned to the 32-goal answer key and pass it in full, but pick correctly on only 15 of 30 goals they never saw; the test asks for at least 24 of 32.

### Fixed

- U8 learned entries now show all platform and host paths before approval, preserve leading dots in skill folders, and leave output and destination folders untouched while approval is pending. Service prices, status reads and removals also honor approval. Learned media checks returned file, result and status addresses and reports redirects; local training receives only its named key. Invalid learned pack sections are kept aside, and answer size limits include object keys. Offline command-line tests now cover use after approval for all five learned lists.
- Add-ons can no longer claim the built-in kind names `rule`, `mcp` and `hook`.
- The dashboard's reduced-motion rule left some animations looping; they now stop.
- **App build output check.** A build that rewrites its output within the same clock tick now passes. The check never follows symbolic links or Windows junctions out of the app folder, opens only plain files (a named pipe used to hang it), and stops hashing past 1 GB. A `.cmd` build tool whose path holds cmd.exe special characters is refused.
- A compiled artifact sent to a server on this machine runs without a key when the provider's key variable is unset, as `proofhouse run` already did. Before, it was refused unless the entry had no `key_env` at all.
- Native build notes for Windows, macOS, Linux, iOS and Android no longer say the builds were never run; they say what the sample-app runs proved and what is still unchecked.
- New tests for four safeguards that no test checked: a malformed provider `ignores` list, build output linked outside the app folder, a model writing the build output named in its own Tauri config, and an answer to the goal question that names two kinds.

## 0.8.0 - 2026-10-16

Rules, MCP servers, hooks and apps for every platform.

### Added

- **Rules, MCP servers and hooks.** `proofhouse make "..." --kind rule|mcp|hook` makes each one and tries it for real before the judge sees it.
  - `--kind rule` makes a Markdown instruction and checks that it installs into, and cleanly comes out of, every rule-capable tool, using throwaway settings.
  - `--kind mcp` makes a stdio tool server, starts it, and checks its `initialize` and `tools/list` replies. Every listed tool must be valid. The best folder includes an exact install line.
  - `--kind hook` makes a command hook for a Claude Code event, runs it on a sample event, and includes a settings snippet. A blocking hook must give a reason.
  - Every version keeps `checks.json`.
- **Apps for every platform.** `proofhouse make "..." --kind app` makes one shared web app and a separate package for each selected platform. Use repeatable `--platform` (for example `--platform pwa --platform android`); without it, every platform in the list is selected.
  - Platforms are data. `app_platforms.json` ships an installable web app (PWA), Windows, macOS and Linux (Tauri), and iOS and Android (Capacitor). Add or override any platform in `PROOFHOUSE_HOME/app_platforms.json`.
  - Each platform is checked offline: required files and keys, and for the PWA the manifest, icon and service worker.
  - With `--allow-commands`, setup steps (such as `npm install --ignore-scripts` and `npx cap add android`) and the build run on a matching machine. The build fails if its output folder is missing, or if it already existed before the build ran.
  - The delivered `README.md` lists the files, where the build output is, and how to build by hand.
  - The desktop and phone builds have not yet been run end to end on real machines, so each is marked "to check".
- **`--allow-commands` for `make`.** Nothing a model wrote is started without it. Commands run with a cleaned environment, a timeout, and a kill of every process they start (a job object on Windows). Shell characters, absolute paths, device file names and leading `-` are refused before anything starts. This is an opt-in, not a sandbox: an allowed program runs with your rights.
- `proofhouse evaluate-product --require-req ID` (repeatable) and benchmark `required_req_ids`: a run that does not cover every required requirement fails. The ids are part of the sealed record and its checksum.
- `docs/master-plan.md`: one plan for what Proofhouse does, where it stands, and the build order.

### Changed

- The hosted API contract publishes repeatable flags (`--require-req`, `compare --on`) as lists.
- Every run record (`make`, `video`, `compare`, `loop`, `launch`, `train`) names the Proofhouse version that made it (`proofhouse_version`).

### Fixed

- **A failed install or update keeps what you had.** Your providers, media and training settings, installed add-ons, and agents, rules, MCP servers and hooks installed into your tools are now written in one step. If the disk is full or a file is locked, the old file stays as it was, nothing half-written is left, and you get a clear error instead of a traceback. If a tool install cannot save its record, the tool's file is put back, so a later uninstall still works. Rewritten files keep their permissions. Each write uses its own temporary file, so two Proofhouse runs saving the same file at once no longer collide.
- **An app build cannot be faked.** Package install scripts no longer run (`npm install --ignore-scripts`). A build whose output was already there before the build step fails. The model cannot write files into dotted folders (such as `.cargo`, `node_modules/.bin` or `.npmrc`), a model-written `package.json` may only use registry versions (no `file:`, `link:`, git, URL, alias, workspace or tarball packages), and model-written lockfiles and other package-manager files are refused. File names are compared without regard to letter case; a `.well-known` folder and a `.gitignore` file are still allowed. Each platform can refuse config files and keys that would run the model's own code: Capacitor JS/TS configs and `capacitor:` package scripts, and Tauri's extra config files and its `runner` and `before…Command` settings. The build tool must come from its real package (`@tauri-apps/cli` or `@capacitor/cli`): `npx --no-install` never downloads a stand-in, and the build stops if another installed package also provides the tool. A brand-new file written safely gets your normal file permissions.
- **Evidence record.** Rubric scoring is type-strict: `true` no longer matches `1`, and each kind of value matches only its own kind. Rubric matching now scores list, dict and null expected values as 0.0. Repeated JSON keys are rejected in the compiler commands that read JSON, and very deep nesting is a clear, line-numbered error instead of a crash.
- **Project scan** (about 21 review fixes):
  - It reads only regular files and never follows links, so a pipe or a link named like a manifest cannot hang or misdirect it.
  - One unreadable folder gives a clean `scan:` line instead of a traceback, and no longer stops the scan.
  - Every string taken from the folder is cleaned and length-bounded before printing.
  - Pasted private keys (PEM, PuTTY, SSH2) and more token shapes are redacted from the README excerpt.
  - Manifests with a BOM or in UTF-16 are read, and ones that cannot be parsed are noted. The README is found whatever its letter case.
  - The folder walk is bounded by folders as well as files.

## 0.7.0 - 2026-10-12

Any provider, any model.

### Added

- **Deploy.** `proofhouse deploy FOLDER --to netlify|vercel|cloudflare|surge` puts a finished site online with that service's own command-line tool, signed in your usual way. `--dry-run` prints the exact command, and `--list` shows the targets. Any other target is one entry in `PROOFHOUSE_HOME/deploy_targets.json` or an add-on. The address is printed and every deploy is logged in `PROOFHOUSE_HOME/deploys.jsonl`. Nothing is deployed unless you run it.
- **Add-ons.** `proofhouse addons list|install|remove`. A pack (`addon.json`, data only) or a Python package (entry point group `proofhouse.addons`) adds providers, media services, training services, tools to install into, and new `make` kinds (a writer prompt and a judge label), with no change to Proofhouse. Shipped entries load first, then add-ons, then yours. A pack is fully checked before it is installed, and a broken add-on is skipped and reported. `make --kind` now takes any kind an add-on adds.
- **Training.** `proofhouse train data|services|price|add|start|status` trains a model on your examples. `train data` turns JSONL or CSV into chat-format `train.jsonl` and `valid.jsonl`. `train start` uses any fine-tuning service as a template (OpenAI and Together ship), or your own machine with a command (MLX LoRA ships), and prints how to run the trained model. A paid job goes through the spend gate: worst case = every byte of data x epochs, as training tokens, at your declared price per million (`train price`). It is refused, with nothing uploaded, when that is over `--max-cost-usd` or there is no price. Training on your machine costs nothing.
- **One goal, many outputs.** `proofhouse make "goal" --kind launch` has a model plan the parts a launch needs (site, video, agent, skill, prompt, copy) with consistent briefs. Each part is then made by its own engine (`make`, or the video studio). `--parts` picks them. One spending limit covers the plan and every part, and parts that would not fit are skipped with the reason. The folder holds `README.md`, `launch.json` and one numbered folder per part. New `--kind copy` makes announcement copy.
- **Same job, many models.** `proofhouse compare "job" --on provider:model --on ...` runs one job on any number of models at the same time. It prints a table of status, judge score, cost and time, and writes `side-by-side.html`, `compare.json` and every output. `--judge provider:model` scores the anonymous outputs and names the best (advice, not proof). One spending limit covers every call and the judge, in equal shares.
- **Agents that run on their own.** `proofhouse loop "goal" --in FOLDER --provider P --model M` works in a folder round after round: it reads and writes files, and with `--allow-commands` runs commands. It stops when `--check` passes, the agent says it is done, `--rounds` or `--for` runs out, the one spending limit (`--max-cost-usd`) is reached, or you press Ctrl-C. With `--watch CMD --every 5m` it watches a command and acts only when the output changes; a look with no change costs nothing. Every round is kept in `rounds.jsonl`. Provider keys are blanked out of command output.
- **Websites.** `proofhouse make "brief" --kind site` has any text model write a whole site, writes it safely to disk (relative paths only, at most 60 files and 3 MB), and checks it like a visitor: title, language and phone viewport on every page, alt text on images, every internal link and file present. With Chrome or Chromium installed (or `PROOFHOUSE_BROWSER`), it takes desktop and phone screenshots and reports JavaScript errors. The judge sees the pages and the checks; the best version is copied to `site/`.
- **Media engine.** `proofhouse generate image|video|speech|music --provider S --model M --prompt ...` uses any image, video, speech or music service.
  - Services are request templates (data): OpenAI images and speech, ElevenLabs, Replicate and fal.ai ship. Any other service, including a local GPU server, is one template (`proofhouse media add --from file.json`).
  - Slow jobs are waited for, and finished files are downloaded with plain reads.
  - Every paid request goes through the spend gate. The gate builds the request from the template itself and prices it per image, per second, per 1,000 characters or per request, from your declared price (`proofhouse media price`). A service on this machine costs nothing.
- **Video production.** `proofhouse make "brief" --kind video --visual-provider ... --voice-provider ... --music-provider ...`:
  - script and shot list from any text model;
  - shots from any image or video service;
  - voice-over, and a music bed (generated or your own);
  - FFmpeg edit, mix and burned-in captions;
  - 16:9, 9:16 and 1:1 renders, each checked for length, frame size and sound, with captions checked against the script.

  One spending limit covers the whole video; everything is kept in one folder.
- `proofhouse install agent|rule|mcp ... --into claude|cursor|codex` and `proofhouse uninstall ... --from ...`. Proofhouse writes a marked block into shared files (`CLAUDE.md`, `AGENTS.md`, Codex `config.toml`), an entry into `mcp.json` (Cursor, or a project's `.mcp.json` for Claude Code), or a file of its own (a Claude Code subagent, a Cursor `.mdc` rule). It keeps a record and a copy of every changed file under `PROOFHOUSE_HOME`. Installing twice changes nothing; an uninstall removes only what it wrote, and refuses if you edited it since unless `--force`. `proofhouse hosts list` shows the tools; any other tool is one entry in `PROOFHOUSE_HOME/hosts.json`.
- `proofhouse make "what you want" --provider P --model M` makes a prompt, an agent skill (`--kind skill`) or a Claude Code subagent (`--kind agent`). It writes version 1, tries it, has a judge model score it against your request, and revises until `--target`, `--rounds`, or the spending limit (`--max-cost-usd`, one limit for the whole command) stops it. Everything is kept in one folder (`record.json`, every version, `final.md`); a made skill comes out as a folder `install-skill --bundle` accepts. Judge scores are advice from a model, not proof.
- `proofhouse run --provider P --model M --prompt "..."` runs a prompt on any provider that speaks the OpenAI chat format. With `--input`, the prompt becomes the system message. It prints the output, and on stderr the tokens and the estimated cost. `--json` prints the full result (output, admission, cost). One request per call, never retried.
- `proofhouse providers list|add|remove|price`. Shipped providers:
  - cloud: OpenAI, Anthropic and Google (their OpenAI-compatible endpoints), Mistral, Groq, Together, Fireworks, OpenRouter, DeepSeek, xAI;
  - on your machine: Ollama, LM Studio, vLLM, llama.cpp.

  Any other provider is one `providers add` line, saved in `PROOFHOUSE_HOME/providers.json`, with no code change. Keys are read from the provider's environment variable at call time and never appear in any output.
- Every run goes through the spend gate. A price comes from the shipped table, then from a price you declare (`providers price`, labelled "declared by you"). A provider on this machine costs nothing unless you declare a price. A paid model with no price is refused (`PHC-COST-0002`), and a paid run needs `--max-cost-usd`. New refusal codes `PHC-RUN-0001` to `0006`.

### Changed

- The README opens with the product: you say what you want, any model makes it, and every version is kept. The 44-second clip is labeled the older evidence walk.
- `proofhouse install` refuses a symlink or junction on the way to the file it would write, and changes nothing. A link cannot be backed up and put back as a link.

## 0.6.0 - 2026-10-12

`execute-openai` now refuses before sending when the worst-case cost is over your ceiling.

### Upgrade notes (read first)

- **(breaking)** `execute-openai` refuses before sending when the worst-case estimate of its cost is over `--max-cost-usd` (`PHC-COST-0001`), **and refuses every model that has no entry in the shipped price table** (`PHC-COST-0002`). The price table ships with no entries: no price has been read from a provider's official page and cited yet. **Until a price entry exists for the model you pass, `execute-openai` refuses to send.** Both refusals exit 7, like every other `execute-openai` refusal, and send nothing.
- `--json` output of `execute-openai`: `admission.cost_ceiling` now states the gate's decision (`enforcement: refused_pre_send_when_worst_case_over_ceiling`, `decision`, `worst_case_usd`, bounds, the price entry used); `pricing_source` and `input_token_estimate` are gone. A sent call adds `cost`.
- Case, run and export files are unchanged. A case touched by this version still opens in 0.5.0.

### Added

- The spend gate (`spend.send_within_ceiling`): the only way the live path sends. It works out the worst case from the exact request bytes: input tokens at most the UTF-8 bytes of the body as sent plus 1024 (on the stated assumption of at most one token per byte), output tokens taken to be at most `--max-output-tokens` (on the stated assumption that this cap covers every billed output token, reasoning included), at table prices, in exact decimals. An amount that would need rounding, an unreadable table, or a request above the size its price applies to is refused (`PHC-COST-0003`). The bytes counted are the bytes sent; the model and output cap are read from them, and a request with a field or content the estimate does not cover (such as image or audio parts), or a ceiling outside 0.000000000001 to under 10000000000000, is refused (`PHC-COST-0003`). No flag, setting or environment variable skips it. See [decision 0006](docs/decisions/0006-refuse-before-sending-over-the-ceiling.md).
- A versioned price table shipped in the package (`proofhouse.price_table/v1`, `data/price_table.json`), pinned by a test to its content. Each entry cites the provider's official pricing page and the date it was read. A model matches only by its exact id.
- `execute-openai` results carry `cost`: the token counts the provider reports and the wall time are measured; `usd` is estimated from those tokens at table prices, never measured, and is not your bill. A figure nobody knows is `unknown`, never `0`. When the provider reports more tokens than the gate's bound, the result adds `PHC-COST-0004` and one line on stderr; the output is still returned.
- An architecture test that fails the build if a module other than the live path can reach the network or its raw sender, or if the one send step is used other than through the gate; and two new mutations in `scripts/mutation_check.py`.

### Changed

- `execute-openai` posts the exact bytes the gate counted, instead of letting the HTTP client serialise the body again. The JSON content is the same.
- CI checks that the price table ships in the wheel and loads.

## 0.5.0 - 2026-10-12

The spine slice: prompts and skills go from objective to export through the same commands, the same case, the same pass rule and the same part contract.

### Upgrade notes (read first)

- **(breaking, one-way)** Cases move to `proofhouse.optimize.case/v1`. A 0.4.x case still opens, reports the same results and takes new versions; its revision and run files are never rewritten. The first command that writes its `case.json` copies the old file to `case.v0-backup.json` (never overwritten) and upgrades it. **An upgraded case no longer opens in 0.4.x**, which refuses a schema it does not know. Keep the backup, or an export made with 0.4.x, if you need to go back. Read-only commands never upgrade a case. Export bundles written by 0.4.x still import.
- **(breaking)** One command, `proofhouse`. Both console scripts now run the same command tree. `proofhouse-compiler` still works and prints a one-line notice on stderr (`--json` output on stdout is unchanged).
- **(breaking)** The eval harness moved under `proofhouse eval`: `eval validate --dataset`, `eval report`, `eval loadouts`, `eval compile-loadout`, `eval generate`. The old top-level forms are not forwarded; each exits 2 with one line naming the new form. `proofhouse validate` without `--dataset` is IR validation, as `proofhouse-compiler validate` was. `scan` stays top-level.
- `proofhouse case` carries every `optimize` subcommand with the same names and flags. `proofhouse optimize ...` still works for 0.5 and prints a notice; it will be removed after 0.5. JSON `command` values (`"optimize new"`, ...) are unchanged.
- Run records are `proofhouse.optimize.run/v2`; `run/v1` files still read.

### Added

- `proofhouse case new --kind skill` opens a skill case; `case record --skill-folder DIR` records a skill folder (`SKILL.md` at its root) as a version. Kinds are `prompt.text@1` (digest = the old `prompt_sha256`) and `agent.skill@1` (digest = RFC 8785 + SHA-256 over a sorted per-file manifest of paths and bytes; empty folders and permissions such as the execute bit are not part of it, and `install-skill` does not copy them); any other kind is refused (`PHC-KIND-0001`).
- `proofhouse parts` lists every registered part with role, kinds, status and conformance suite version (`--json` for full descriptors). `adapters` keeps its output (request builders only).
- Skill checker part and `case criteria add --skill-check install-roundtrip`: frontmatter, then an install round trip into a temporary skills folder (write, read back, reinstall changes nothing, uninstall restores the prior folder exactly). It does not test behaviour in real hosts, and the report says no independent pass ran.
- `install-skill --bundle` takes any skill, as a zip (`<name>/...`) or a folder. The name comes from validated `SKILL.md` frontmatter. With no bundle it installs Proofhouse's own skill exactly as before.
- `proofhouse uninstall-skill NAME` removes only a skill `install-skill` recorded installing and restores what that install replaced, only if its backup still holds exactly that; it refuses a folder that changed since install unless `--force` (then backs it up first, verifies that copy, and refuses a folder that holds a link or junction, which the copy would follow), and removes a link, never what it points at.
- `proofhouse "<objective>"` (the overseer) now acts on its route decision: a routed `prompt` or `skill` opens a case through the same function as `case new` (in `./case-<words>`, or `--case DIR`; `--model NAME`), and the case records the class, rationale and whether it was forced. Every other class opens nothing and is appended as "no part yet" to `PROOFHOUSE_HOME/demand/no-part-yet.jsonl`. `nothing_new` and `one_prompt` are unchanged. Stdout is still the route decision; what the overseer did is one line on stderr. `route()` itself is unchanged.
- Run records carry `part` and `cost`. Nothing measures cost yet, so every figure is `unknown`, never `0`; `usd` is never filled. The report sums cost per version, and a sum that includes an unknown is unknown. A figure must be finite (`NaN` and `Infinity` are refused). A run's entry in `case.json` must be listed once and match its run file (part, cost, revision and every other field it lists); import, `case output list` and `case report` check every entry, and any command that loads a run checks that run, refusing a mismatch (exit 2) instead of showing its figures or failing with an internal error.
- A report with a skill check names, below the overall result, the part that produced the evidence (`skill-checker`), that part's own status and what it did not measure.

### Changed

- **(breaking)** `proofhouse proof` no longer reports `SHIP` when no review pass ran. With no pass wired to the command it reports `UNJUDGED` with `passes: 0` and exits 3. The real-pass rules are unchanged.
- **(breaking)** `install-skill --force` refuses to replace a skill folder that is, or holds, a link or junction (exit 2), as 0.4.2 already does; 0.4.1 backed up what the link pointed at and replaced the link, so an uninstall could not put the link back. Remove or replace the link yourself, then install. This is checked again right before the backup copy, a backup that came out holding a link is refused, and without `--force` a skill folder that appears while `install-skill` runs is refused (exit 2).
- A backup that fails or does not match is removed again (never one another run left at the same path), and anything that could not be removed is named in the error. If a failed install or uninstall cannot put its install record back, the error says `record not restored` and names the record.
- Reading a skill folder refuses one whose folder, or a folder inside it, is replaced while it is being read (`PHC-SKILL-0003`).
- Skill file names that are not portable to every OS (Windows reserved names such as `CON`, `nul.txt` or `CONIN$`, a trailing dot or space, characters Windows forbids) are refused on every OS (`PHC-SKILL-0009`), in skill versions and in `install-skill` input.
- README, docs and CI use `proofhouse`; CI runs `proofhouse demo` from the built wheel outside the checkout.

## 0.4.2 - 2026-10-12

### Fixed

- `install-skill --force` refuses to replace a skill folder that is, or holds, a symbolic link or a Windows
  directory junction. It exits 2 and changes nothing; remove or replace the link, then install again. Before
  this fix, the backup copy under `PROOFHOUSE_HOME/skill-backups/` followed such a link and copied what it
  pointed to. The backup copy now never follows a link.
- A skill folder that is a link to a folder that no longer exists is refused the same way (exit 2), instead of
  failing with "cannot place the new skill" (exit 7).
- A backup copy that fails or is refused is removed from `PROOFHOUSE_HOME/skill-backups/`; if it cannot be
  removed, the error names where it is.
- Removing a copy never changes the permissions of a file that a link in it points to.

## 0.4.1 - 2026-10-08

### Added

- `proofhouse-compiler demo` runs the reference advisory workflow from files shipped in the package. It replays recorded outputs, calls no model, and does not need a git clone.

### Changed

- Package metadata for a PyPI page: SPDX `MIT` license, project links, and classifiers. The README leads with `uv tool install proofhouse` / `pip install proofhouse`.
- README demo is a 42-second walk through the standalone app (`apps/proofhouse.jsx`) on the Grok 4.7 Facebook run: objective, loop, answers, compiled prompt. Remotion animates the terminal, cursor, particles, and spinning light. Hyperframes runs the same screens as sub-compositions. The soundtrack is original and synthesized.
- The manual publish workflow can upload to the real PyPI index when the run chooses `pypi`. The default choice remains TestPyPI.

## 0.4.0 - 2026-10-04

### Added

- `proofhouse-compiler install-skill --host claude` installs the skill into
  Claude Code's `~/.claude/skills`; `--host cursor` installs into `~/.cursor/skills`.
- `proofhouse scan [PATH]` reads a project folder and reports its language,
  frameworks, package manager, test tools, CI, agent instruction files, layout
  and a short README excerpt, so the skill can pre-fill the environment questions
  and ask fewer. It is read-only, stays inside the folder (never follows symlinks
  or junctions, refuses a drive root or the home folder), and never reads dotenv
  or key files. The same file ships in the skill as `scripts/scan_project.py`,
  and a test fails if the two copies differ.
- `skills/proofhouse/INSTALL.md`: short instructions written for an AI agent, so a user can
  hand the skill folder to Claude Code, Cursor or another agent and say "install this".

### Changed

- **(breaking)** `install-skill` no longer defaults to Cursor. With no `--host` and no `--dest` in a terminal,
  it asks which agent: every known agent (marked when its folder exists) or another agent you
  name with its skills folder. Run by a program, it installs for the one agent whose folder
  (`~/.cursor` or `~/.claude`) exists; with none or both it exits 2 and lists the choices.
  `--json` output now includes `host` and `agent`.
- **(breaking)** The Python `install()` and `default_dest()` functions no longer assume Cursor either: they
  need an agent or a destination folder, and refuse with exit code 2 otherwise.

## 0.3.0 - Evidence Integrity

### Removed

- Removed the deprecated pre-Proofhouse console-script aliases and live-test
  environment fallback at the documented 0.3.0 boundary.

### Changed

- Completed the Proofhouse identity migration across active wire media types,
  semantic-context keys, benchmark and diagnostic identifiers, generated
  TypeScript names, schema filenames, dashboard metadata, CI, docs, and tests.
- Bumped the package to 0.3.0. Frozen v0.5 contract fixtures, requirements
  contract evidence, the original dashboard backup, and changelog history keep
  their historical names intentionally.
- README leads with one story, the offline prompt-revision workflow, and moves
  experimental and prototype parts into their own section. It now states the CI
  matrix (Linux, macOS, Windows; Python 3.11 to 3.14) and shows the CI badge.

### Evidence integrity (adversarial review of 78e512c, findings F01-F12)

Behavior changes a user will notice are marked **(breaking)**. See
[docs/decisions/](docs/decisions/) for the reasoning and
[docs/assurance/](docs/assurance/) for what was verified.

#### Fixed

- **Live requests keep every mandatory field (F01).** `execute-openai` renders
  requirements (id, mandatory flag, acceptance), success/failure criteria,
  uncertainty and evidence policies, workflow, autonomy and assumptions into
  the system message from an explicit per-field map; fields a single request
  cannot honor refuse with `EXE-SEM-0001` before sending. The envelope records
  the mapping and the system-message digest.
- **(breaking)** **Duplicate evaluation ids are rejected (F02).** `case_id` and
  `criterion_id` duplicates, duplicate JSON keys inside a dataset row or rubric,
  malformed rows and non-finite values raise with the line number; scores use
  structured keys; aggregation is order-independent. A rubric must name
  `rubric_id` and `version` as non-empty strings.
- **(breaking)** **Coverage and binding (F03).** A mandatory requirement with no
  product-eval case is `BLOCKED` (`EVR-COV-0001`); rows declaring another
  candidate digest are `BLOCKED` (`EVR-BND-0001`). Results carry dataset/rubric
  digests and per-case results. `closed-loop` withholds a candidate PASS unless
  every row declares the candidate's `candidate_digest`: unbound or partially
  bound rows give `BLOCKED` (`EVR-BND-0002`, exit 5), which includes every
  dataset written before this change. Standalone `evaluate-product` still
  PASSes them; a declared digest is caller-supplied, not authenticated.
- **(breaking)** **Edited revisions and stale verdicts (F04).** Revisions are
  digest-checked on load; verdicts bind to revision and criterion digests and
  go stale when either changes; check runs are immutable files; `case.json`
  writes are atomic; revision files are never overwritten. Verdicts recorded
  before this change carry no digests and now show as stale (`UNJUDGED`);
  record them again with `optimize verdict`.
- **(breaking)** **Model-note provenance (F05).** Notes files are
  `user_supplied`, undated and unverified (they were `researched`, verified
  today). Every profile carries an `evidence` label; unsourced profiles say
  `unverified`; `models list` says "reviewed", not "verified". The Opus 5
  note no longer advises stripping verification, and every compile prompt says
  efficiency advice never removes a required gate.
- **Stage identity and repair (F06).** Closed-loop evidence reports compile,
  deterministic evaluation, product evaluation and repair as separate stages
  with true evaluator identities; a failing product evaluation stops with
  `EVR-REP-0005` and a terminal reason instead of a silent zero-attempt FAIL.
- **Malformed input (F07).** Closed-loop intake rejects non-object roots,
  wrong nested types, non-boolean `network_allowed`, non-finite numbers,
  duplicate keys/ids and excessive nesting with `EVR-INP-*`/`EVR-DUP-0001`
  instead of raising or passing.
- **Transactional skill install (F08).** A failed forced install leaves the
  previous skill unchanged; replacements keep a backup under
  `PROOFHOUSE_HOME/skill-backups/`; unsafe archive paths and oversized
  bundles are refused.
- **Budget inputs (F09).** `NaN`/`Infinity`/non-positive ceilings are rejected
  without raising; the envelope states the cost ceiling is declared only.
  Library callers must pass `max_cost_usd` as a decimal string (as the CLI
  does) and `max_output_tokens` as a positive `int` (not `bool`).
- **Artifact responses (F10).** The JSX artifact schema-validates every model
  response, excludes answers to hidden questions, and adds timeout/cancel,
  including for the unfamiliar-model research call (a cancel stops the run
  rather than falling back to generic notes).
- **Revision context (F11).** Revise packets (CLI and artifact) carry the
  clarification answers and accepted constraints. The artifact describes the
  answers as still in force unless the new feedback changes one, not as
  overriding it.
- **Public trust docs (F12).** SECURITY.md names a private reporting route;
  CONTRIBUTING installs the test extra and documents a public decision
  process; CLI help no longer cites unpublished internal ids.
- `proofhouse.__version__` reads the installed version (it said 0.1.1).

#### Added

- `optimize constraints add|list|propose|accept|reject|link`: a constraint
  ledger outside the prompt, seeded from clarification answers.
- `optimize output add|list`: record imported outputs bound to a revision.
- `criteria add --target output`, `verdict --run`: checks on recorded outputs.
- **(breaking)** `optimize check` passes only when every accepted constraint
  is satisfied by linked criteria ([decision 0002](docs/decisions/0002-what-pass-means.md)).
- `optimize compare`, `optimize report`, `optimize export|import`.
- `examples/reference-advisory/` and `scripts/reference_workflow.py`, run by
  the test suite and by the wheel-install CI job.
- Docs: product scope, architecture, surfaces and contracts, evidence format,
  reference workflow, troubleshooting, decision records, assurance statement.

### Added

- `docs/assets/proofhouse-demo.mp4` (23 s) and its poster, linked from the top
  of the README. The terminal lines in it are the reference workflow's real
  `optimize check` output (case path shortened); the soundtrack is original
  and synthesized.
- `[test]` extra declaring pytest, locked in `uv.lock`, so `uv sync --extra test`
  and `pip install -e ".[test]"` establish the test prerequisite on a clean clone.
- `examples/ir_minimal.json` — static, human-readable copy of the canonical
  minimal IR (`tests/compiler/test_examples_ir_minimal.py` pins it to the
  fixture factory) for `validate` / `compile` demos without a Python pipeline.
- README and `docs/quickstart.md` now separate the two console scripts
  (`proofhouse-compiler`, `proofhouse`), lead with tested uv commands, and give
  the Cursor skill install command (`python -m zipfile -e … ~/.cursor/skills`).
  `docs/showcase.md` is an executable 5-minute offline script.
- `proofhouse-compiler optimize new|compile|record|revise|status|criteria|verdict|check`:
  offline case workflow that renders the framework's clarify / compile / self-heal
  prompts as packets for the user's own host agent, records revisions, and checks
  them against user-declared criteria. No provider call, no scoring.
- `proofhouse-compiler models list|show|remember|forget`: model-note provenance
  (`builtin|cached|researched|fallback`), canonical ids, aliases, `verified_at`,
  stale warnings, and a local cache under `~/.proofhouse/` (`PROOFHOUSE_HOME`).
  The CLI never researches online.
- `proofhouse-compiler install-skill`: extracts the bundled `proofhouse.skill` into
  `~/.cursor/skills` and verifies `name: proofhouse`. The bundle, the framework
  JSON, and the model registry ship as package data.
- One reviewed registry (`src/proofhouse/optimize/data/model_registry.json`) now
  generates the framework `modelNotes` + `modelRegistry`, the framework Markdown
  table, the JSX `MODEL_NOTES`, the skill model paragraph, and the README
  supported-models table (`scripts/generate_model_surfaces.py --check` is a test).
- README "Surfaces" matrix scopes auto-research to the skill and artifact.

### Changed

- CI test matrix now includes Python 3.13 and 3.14 on Ubuntu, Windows, and
  macOS. Typescript-drift and wheel-install stay on 3.11.
- The reference model for live runs is `gpt-5.6-luna`. `execute-openai` still
  requires `--model` at call time; envelopes record that the reference model
  has been chosen (`q1_unpicked: false`). Cost ceilings remain recorded, not
  enforced. Live stays opt-in and not CERTIFIED.
- Live OpenAI payload uses `max_completion_tokens` (the reference model
  `gpt-5.6-luna` rejects `max_tokens`).
- `execute-openai` reports `error` / `EXE-HTTP-0001` when the provider HTTP
  status is not 2xx (a completed send is not a successful completion).

## 0.2.1 - Skill Bundle Rebuild

### Fixed

- `skills/proofhouse/proofhouse.skill` was a hand-packed artifact last built
  2026-07-04. It shipped framework **v1.2** while the repository was on v1.3, so
  its model tables still listed superseded entries. Rebuilt from the source
  directory; the bundle now carries v1.3 and its entries are named `proofhouse/`.

### Added

- `scripts/build_skill_bundle.py` builds the bundle reproducibly — fixed
  timestamps and attributes, entry order sorted by name, text normalised to LF,
  and stored uncompressed, so the output does not depend on the platform or the
  Python version that packed it.
- `tests/test_skill_bundle.py` fails if the committed bundle and its source
  directory disagree, which is what went unnoticed for two months.


## 0.2.0 - Proofhouse Rename

### Changed

- Renamed the project from PromptRig to Proofhouse across the package, console
  scripts, schema `$id` namespaces, environment variables, generated TypeScript,
  brand-named files, and documentation.
- Python package `promptrig` is now `proofhouse` (`src/proofhouse/`).
- Schema `$id` namespaces moved to `proofhouse.dev` and `proofhouse.local`.
  `proofhouse.local` remains a deliberately non-resolving namespace.

### Added

- Console scripts `proofhouse` and `proofhouse-compiler`.
- Test-only environment names `PROOFHOUSE_LIVE*` (legacy fallback
  `PROMPTRIG_LIVE*`) are read by
  `tests/compiler/live/test_live_openai_q1_gate.py` under pytest marker `live`
  (deselected by default). `execution.py` does not read them. Removable at
  0.3.0 with the aliases.

### Deprecated

- Console scripts `promptrig` and `promptrig-compiler` remain as aliases for one
  minor version and are removable at 0.3.0.

### Unchanged

- The frozen contract schema `PROMPTRIG_IR_V0_1.schema.json` keeps its filename
  and its `$id`; it is a historical artifact and its identity is part of the record.
- Wire identifiers, media types, and canonical digest inputs are untouched. The
  three pinned `ir_sha256` digests are byte-identical across the rename.
- Maturity is unchanged: the requirements compiler remains `PARTIAL`.


## 0.1.1 - Showcase and Local Skill Adoption

### Added

- Public-facing README with quickstart, feature map, and repo navigation.
- Quickstart, showcase, Custom GPT setup, security, and contribution docs.
- Prompt audit example for before/after positioning.
- GitHub Actions CI workflow for tests and dataset validation.
- Source-controlled Codex skill package under `skills/promptrig/`.

### Changed

- Rubric scoring now accepts only integer values from 1 to 5.

## 0.1.0 - Initial PromptRig Scaffold

### Added

- PromptRig project identity
- Custom GPT identity: PromptOps Architect powered by PromptRig
- Core prompt
- Mode prompts for Default, Audit, Meta-Prompting, Agentic, and Evaluator modes
- Modular prompt components
- Reference policy
- Prompt quality rubrics
- JSONL test datasets
- Offline Python eval harness
- Basic tests

### Notes

This scaffold is intentionally lightweight. Provider-specific adapters can be added later after the core prompt architecture and eval datasets stabilize.
