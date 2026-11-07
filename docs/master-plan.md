# Proofhouse master plan

This is the one plan. If another document disagrees with it, this one wins. Keep it current: when the
owner changes direction, change this file in the same session.

## What the finished product does

You say what you want and pick any model from any provider. Proofhouse makes it, runs it, improves it
and delivers it where you work. It keeps every version and every result.

It makes:

- **Text and code:** prompts, agents, skills, rules, MCP servers (tool servers an AI app can call), and
  hooks (small programs an AI coding tool runs on events).
- **Media:** images, video, voice, music, and finished edited pieces.
- **Sites and apps:** websites, and apps for every platform: an installable web app (PWA), Windows,
  macOS and Linux desktop apps, iOS and Android apps, and any other platform added as data.
- **Loops** that run on their own within limits you set.
- **Fine-tuned and trained models.**
- **Multi-part launches** from one goal.

How it behaves everywhere:

- **Any provider, any model, any modality:** known or unknown, commercial or open source, cloud or local.
  Providers, media services, training services, deploy targets, coding-tool hosts and app platforms are
  data. Adding one is a line or an add-on, not a code change.
- **Nothing new is refused for being new.** A kind of thing Proofhouse has never made is researched by
  the chosen model and learned as an add-on kind. A model or AI workspace released after this list was
  written is found by `proofhouse models update`, which asks each provider for its models and reads the
  official release pages, then records what it found.
- **One front door:** the `proofhouse` command.
- **Every paid call goes through the spending limit** (`spend.send_within_ceiling`).
- **Make starts by working out what you mean (owner's correction, 2026-11-01).** The core of Proofhouse
  is writing prompts and other instructions for you, well. So for a prompt, skill, agent, rule or any other
  text kind, `make` first asks the questions it needs answered (the interview), then says back in plain
  words what it understood so you can correct it (the reverse prompt), then asks which AI tool or model the
  result is for. It writes for that tool: its file format and where the file lives (a rule is `CLAUDE.md`
  for Claude Code, `.cursor/rules/*.mdc` for Cursor, `AGENTS.md` for Codex; a skill is that tool's skill
  format) and that tool's own prompting habits. A tool or model it does not know is researched and
  learned, never refused. Scripts and AI apps answer from a file (`--answers`, `--for`) instead.
- **Every make runs the same loop:** (for text kinds, interview first), write, try it for real, judge,
  revise, keep every version.
- **Checks and comparing versions are one feature of the record,** not the product.

## Where it stands

| Area | State |
|------|-------|
| Run any prompt on any provider; compare many models on one job | works |
| Make prompts, skills, agents, copy | works (host mode: examples for prompt, copy, app, rule, agent, skill, hook, site, mcp) |
| Interview first for text kinds: asks its questions, says back what it understood, asks which AI tool or model it is for, then makes it in that tool's format and tries it there when it can | works (terminal or an answers file; an unknown tool is researched, not refused) |
| Interview first for sites, apps and launches: where it will be published or which platforms, a few questions, a say-back, then build and check against the answers | works (terminal or an answers file; a launch asks shared questions once, then per part) |
| Every run asks: with no terminal and no `--for`, a make or launch stops with its questions (which tool, model or place first) and exit code 9, then goes on from `--answers`; the record says who answered (terminal, answers file, launch, or none when called from code) | works |
| Media through the same front door: `make --kind video\|image\|voice\|music` (and add-on media kinds) asks first, picks the service and model from the media list (local programs included; an unknown one is learned), then plans, renders, checks, judges and re-plans, keeps every version and delivers the best one in the shapes asked for; video goes through the beat-film engine | works (the judge reads the plan and the file checks; it does not see or hear the result itself) |
| Make rules, MCP servers, hooks (each one tried for real before delivery) | works |
| Make websites and put them online (Netlify, Vercel, Cloudflare, Surge, or any target added) | works |
| Make apps for every platform | works; native builds proven on all six platforms ([run](https://github.com/KM-it-ops/Proofhouse/actions/runs/39161715167)) |
| Images, video, voice, music; full video engine (generated clips, images, voice, music, editing, render) | works |
| Multi-part launch from one goal | works |
| Install agents, rules and MCP servers into Claude Code, Cursor, Codex, or any tool added | works |
| Loops that run on their own within limits | works |
| Train and fine-tune models (online services or on your own machine) | works |
| Add-ons that add providers, services, tools and make kinds | works |
| Learn a kind it does not know instead of refusing it | works |
| Learn an app platform, coding-tool host, deploy target, media or training service it does not know | works; each is saved unapproved and does nothing until `proofhouse addons approve learned <id>` |
| Keep the model and AI-workspace list current (`proofhouse models update`) | works; list checked against official pages 2026-10-18 |
| Project scan | works |
| Evidence record: sealed benchmarks, type-strict rubric scoring, strict JSON inputs, required requirement coverage | works (four old defects fixed 2026-10-16) |

### Apps in detail

`proofhouse make --kind app` makes one shared web app, then wraps it for each platform listed in
`app_platforms.json` (shipped list plus your own in `~/.proofhouse/app_platforms.json`). Each platform
says what the model writes, what is checked, and how it is built.

| Platform | Made with | Checked offline | Built (with `--allow-commands`) |
|----------|-----------|-----------------|--------------------------------|
| Installable web app (PWA) | manifest, icon, service worker | manifest linked, icon exists, worker exists and registered, page opens in a browser | nothing to build |
| Windows, macOS, Linux | Tauri v2 around the web app in `www/` | required files, JSON keys | setup (`npm install`, `tauri icon`), then `tauri build` on a matching machine; the output path comes from the app's own `mainBinaryName` and `productName`, and the build fails if that file is missing or unchanged |
| iOS, Android | Capacitor around the web app in `www/`; native projects made by `cap add`, not by the model | required files, JSON keys | setup (`npm install`, `cap add`), then an unsigned simulator `xcodebuild` (iOS) or `gradlew assembleDebug` (Android); no signing needed, and the build fails if the app file is missing |

A fixed sample app (`samples/native_build/`) builds on every platform with no model and no keys:
`scripts/native_build_sample.py <platform>` locally, or the `native-builds` workflow on GitHub's machines
([first green run](https://github.com/KM-it-ops/Proofhouse/actions/runs/39157949115)). Signed release builds for the app stores are not covered.

### How far each part has been proved (updated 2026-10-29)

"Works" above means the offline tests pass. Three levels are kept apart, because they are not the same:
tested offline (recorded answers, no network), run live once (a real model on the owner's machine, files
opened and checked), and shown to a stranger (not done yet; it waits on the owner's tester).

| Part | Offline tests | Run live once (2026-10-29, logged-in coding agent, paid spend $0) | Shown to a stranger |
|------|---------------|-------------------------------------------------------------------|---------------------|
| Prompt, skill, agent, rule | yes | prompt 8/10; skill 10/10; agent 10/10; rule 10/10 with 3 of 3 checks | no |
| MCP server | yes | 9/10 after two rounds, but 0 of 1 checks passed; one still to fix | no |
| Hook | yes | first runs failed the event-name check three times; fixed test-first (the writer is now told every allowed event); re-run 7/10 with 1 of 1 checks | no |
| Website | yes | 6/10, 7 of 7 checks, opened and shot on desktop and phone; a real Vercel deploy answered HTTP 200 | no |
| App | yes | 4/10, 46 of 52 checks passed | no |
| Launch (site, copy, prompt from one goal) | yes | site 8/10, copy 8/10, prompt 10/10 | no |
| Site and app asking first (step 7a) | yes | run live 2026-11-02 through the agent bridge, answered from files: site for Netlify 9/10, 7 of 7 checks; app for PWA only 8/10, 22 of 23 checks (the one left is "nothing to build"); the answers show up in both | no |
| Every run asks (step 7b) | yes | run live 2026-11-02 through the agent bridge with no terminal: paused three times with exit 9 (which tool, then 14 questions, then the say-back), then made a Claude Code skill from the answers file, 6/10, $0 over 12 calls; the record says "answers file" | no |
| Media through the front door (step 7c) | yes | run live 2026-11-02 through the agent bridge with local programs only (a card painter standing in for an image service, Windows speech for voice), paid spend $0: a voice piece paused with 14 questions, then made 3 versions, best 8/10, delivered as wav and mp3 (8.8 s of real speech); a 12-second video paused with 15 questions, then made 3 versions re-planned from the judge, best 6/10 with 8 of 8 checks, delivered as a 1920x1080 mp4 of 12.3 s with sound | no |
| Loop | yes | broken code fixed in 2 rounds, 4 of 4 tests pass, run again by hand | no |
| Video engine | yes | two finished films with voice, music and burned-in captions, in three shapes (60 s and 45 s) | no |
| Another provider (the Claude and Grok agent bridges, Ollama) | yes | not run live | no |
| Paid image, voice, music and video services; training start; learning an unknown kind; model-list update | yes | not run live (spend limit 0, no keys) | no |

Notes from that run: the film's music is a locally built bed, because the Gemini music attempt failed twice.
Since then (`feat/video-finishing`, now on main through #100): the engine itself now dissolves between shots, fades the film in and out,
cleans the voice, dips the music under it and levels the mix to -16 LUFS. That polish used to exist only in the example scripts.
Tested on a short local film (no model calls, $0). Still not done in the video engine: the voice and music still come only from a
service or a file you give (nothing is made locally when you have neither), and shots are not timed to the spoken words.
Since then (`feat/video-motion`, now on main through #100): films can be written beat by beat, each beat timed to its spoken words, with
moving graphics, sound effects, picked cuts and real screen recordings (at most a third of the film); the voice can come from a
program on your own machine (Kokoro), so a film costs $0. Still not done: recordings have no `proofhouse` command yet
(only `proofhouse.recording`). Music and the 9:16 layout were done later, in step 8.
The agent bridge (`proofhouse agent-server`) was added in this run; its API entry is in the OpenAPI fixture.

## Build order

1. Rules, MCP servers and hooks as make kinds. Done.
2. Apps for every platform as one make kind. Done, including native builds on all six platforms.
3. Next, as units (approved 2026-10-17). Each unit runs in its own session and branch. Claude writes
   the failing test first and judges the result; Cursor, Codex or agy runs the edit-test loop, and a
   tool from a different company checks each diff.
   - **U0, tidy-up.** Land the answer key below, stop add-ons from claiming the built-in kind names
     rule, mcp and hook (the way `app` already is), and delete stale branches. Done (PRs 65, 66),
     except deciding the `join/evidence-workflow` branch.
   - **U1, run compiled artifacts on every provider,** not only OpenAI-compatible ones (completion
     criterion 1, [audit](assurance/2026-10-16-completion-criteria.md)). A requirement a provider
     cannot carry stops the run before sending. Codex loop, agy check, one Opus security pass. Done (PR 68).
   - **U2, `proofhouse "<goal>"` picks the right kind of thing to make.** Done (PR 69). A model, when one is set up, is
     the main picker; better built-in rules pick otherwise. The built-in rules now pick correctly on all 32
     goals of the approved answer key, [overseer-test-set.md](overseer-test-set.md), but they were fitted to
     those 32: on a separate set of 30 goals they never saw they pick correctly on 15. So the test asks for
     at least 24 of 32. Cursor loop, Codex check.
   - **U3, native app builds on real machines.** Done (PR 70). A fixed sample app builds on Windows here
     and on Linux, macOS, iOS and Android in a GitHub Actions job. The iOS build gets an output path
     to check, and coarse file timestamps stop causing false failures. One Opus security pass.
   - **U4, the dashboard works by keyboard, at phone width and with reduced motion** (completion
     criterion 9). The tests must fail on three copies broken on purpose. Cursor loop, Codex check.
     Done (PR 67).
   - **U5, final gate.** Review and fixes done (2026-10-18): a fresh full review of main at f939f95 found
     two wrong behaviours and four safeguards no test checked; all six are fixed or tested. New
     statement: [assurance/2026-10-18-completion-criteria.md](assurance/2026-10-18-completion-criteria.md).
     Still open: a try by a fresh user (criterion 6). The v0.9.0 tag and the GitHub releases for
     0.8.0 and 0.9.0 were made on 2026-10-25, and 0.9.1 (the first release with the PyPI README) was
     tagged, released and published to PyPI the same day: `pip install proofhouse`.
   - **0.9.0 prepared (2026-10-23).** Version set, CHANGELOG closed, package built and checked, not
     published. Tagged `v0.9.0` and released on GitHub 2026-10-25. Statement:
     [assurance/2026-10-23-completion-criteria.md](assurance/2026-10-23-completion-criteria.md).
4. Owner's corrections (2026-10-18). Done: a kind Proofhouse does not know is researched and learned, not
   refused; the model list keeps itself current (`proofhouse models update`) and now has GPT-6.1, GPT-6,
   Claude Opus/Sonnet/Haiku 5.5, Gemini 4 Argon, Grok 4.7 and Grok Bot; the send address is checked
   against the provider's host last; one run reads the providers file once.
   - **U8, learn the other lists too.** Done (2026-10-23). An app platform, coding-tool host, deploy
     target, media service or training service Proofhouse does not know is researched by the chosen
     model and learned, from the command line as well as the Python API. A learned entry is saved
     unapproved: until the owner runs `proofhouse addons approve learned <id>`, it sends, runs and
     writes nothing, and shows exactly what it would do. Learned addresses must be https on a public
     host, and the key never leaves that host; learned file paths stay inside the home folder.
     `proofhouse generate image|video|speech|music` now reaches media from the command line. Cursor
     and Codex built and fixed it; agy, Codex, Cursor and two Opus security passes checked each round.

5. **Host mode (owner's correction, 2026-10-25): works for anyone, with no API key.** `make` today needs a
   provider key, so a person who only has an AI app or a monthly plan (Cursor, Codex, Gemini CLI, Grok CLI,
   Claude Code) cannot use it. In host mode the AI app they already use is the writer and the judge, using its
   own model, and Proofhouse is the referee, the assembler and the recorder. No key, no setup beyond
   installing the package and one skill. Version 0.10.3 is published (see the CHANGELOG).
   - `proofhouse check <kind> <folder>` runs the same real-world checks `make` runs (site opened like a
     visitor; MCP server answers `initialize` and `tools/list`; hook run on a sample event; rule installed and
     removed on every tool; skill and agent files accepted by the installers) and prints pass or fail.
   - `proofhouse record` saves each version the agent writes, with its checks and the agent's own score, and
     delivers the best one in exactly the layout `make` uses (`v1/`, `v2/`, `record.json`, `site/`, `mcp/`...).
   - `proofhouse render video` assembles a finished video from a script and the shots, voice and music the
     agent supplies (FFmpeg, 16:9, 9:16, 1:1, captions, length and sound checks), with no paid call.
   - A skill (`skills/proofhouse-host`) teaches the agent the loop: write, check, revise, record.
   - Second-agent judge: `record --judge NAME --judge-score N` keeps another agent's score (the judge must
     differ from the writer) and ranks judged rounds above self-scored ones. Still advice, not proof. Any
     paid media service still goes through the spending limit.
   - Quality checks in `check`: word counts, filler and vague-claim scan, a concrete detail, launch parts that
     repeat each other, and site readability (contrast, text size, one heading, image alt, page title).
   - `render video` can take a local voice file and a generated music file. Both Tidewatch videos (the
     3-format promo and the 30 s film) are built from recorded screen footage of an app prototype, two
     Gemini-generated clips (free allowance), a local Kokoro voice and numpy-made music. Limits: only two
     10 s clips at 720p shared by both videos, the app is an HTML prototype, nobody has listened to the
     audio yet, and the scores are the writer's own.
   - `proofhouse compare "job" --entry LABEL=file ...` puts saved answers from any agents side by side
     (`side-by-side.html` plus `compare.json`), with optional scores and notes, no model call.
   - `proofhouse referee start|round|status` lets the agent run its own improve loop while Proofhouse runs
     the agent's check after each round, enforces the round and time limits, and keeps `loop.json` and
     `rounds.jsonl`. The check runs with secret-named variables removed. The record is a plain log, not
     tamper-proof, and two rounds at once are not locked.
   - `proofhouse check|record launch` covers a multi-part launch from one goal: each part is checked as its
     own kind (video parts structurally only), shared names must appear in every text part, every fact in at
     least one, and avoid-words nowhere; record delivers every part plus a generated README.
   - Examples built by Cursor, Codex and Grok with no key: `examples/host-mode/` has one per kind, plus
     `compare`, `loop` (a 40-test markdown converter) and `launch` with their records. `install`, `deploy`
     and `train` each have a proof script and its saved output: install and uninstall on a throwaway folder,
     deploy as a dry run with the network switched off, and training data prepared and checked with no
     model trained or paid for. The compare scores
     (Claude as judge) and the launch score (Codex, blind: 5/10, weakest part the video script) come from
     an agent that did not write the work; the rest are the writers' own advice.
   - Stage 2 status (updated 2026-10-26; PR #85 is merged, see below). Eleven one-goal sessions
     ran; their work sat on separate branches (the fix branches are now merged, see below):
     - Proved by hand: install, deploy and train examples pass 4 of 5 claims; the README now says what each
       check does not prove (`caababc`). The example site, the call-MCP server and both videos work
       for real (videos play to the end, sound is present).
     - Fixes on their own branches: record keeps each version's agent (`8953149`); the example MCP server
       answers garbage input with -32700 (`0ace81b`); a test for `caption_style` (`cd56c24`); a fix for
       absolute paths in record output (`992ccfe` test, `1d98d93` fix; full suite 2385 passed, 51 skipped; the install
       help now uses a `<this-folder>` placeholder plus a new `INSTALL-HOOK.txt`; committed examples not regenerated).
     - Other-agent repeat: Codex redid the `prompt` example, check and record pass (`5a20791`).
     - Independent Codex score: promo 6/10, film 6/10 (the film's own score was 8). Codex saw frames and
       text only, so voice, music and motion are still unjudged. A person must listen.
     - `_pick_best` fix approved and built: judged ties go to the later version (`a7d8d40` on
       `claude/stage2-pick-best-tie`; 79 passed, 4 skipped, all 14 records unchanged).
     - `tests/test_native_build_sample.py` failed only under bare `pytest`; fixed by `pythonpath = ["src", "."]`
       in `pyproject.toml`.
     - Full suite on c6163dc (before any fix branch): 2385 passed, 50 skipped (all Windows limits), 0 failed,
       0 errors; `tests/test_native_build_sample.py` left out (needs the one-line `pyproject.toml` fix).
     - Film replaced (2026-10-26, `e494cfc`, local, not pushed): `video/final-premium.mp4` is a 48.8 s,
       1920x1080 film with a new script and a new local voice (no paid calls); the old 30 s `final.mp4` is kept.
       `video-record` and the Codex 6/10 score still describe the old 30 s film. Boss watched and listened to the
       new film and accepted it as is (voice, pacing, music, visuals frozen). The 24 s launch promo is on hold.
     - Merged locally into `feat/host-mode` (2026-10-26, nothing pushed, no conflicts): `a7d8d40`, `cd56c24`,
       `0ace81b`, `8953149`, `992ccfe` + `1d98d93`, plus `db942a4` (`pythonpath = ["src", "."]`, so
       `tests/test_native_build_sample.py` collects under bare `pytest`; its 5 tests pass). Not merged: the two
       Codex branches (`5a20791` repeat, `1d1f922` scores).
     - Full suite on c58b62f (bare `uv run pytest -q -p no:cacheprovider`, native test included): 2416 passed,
       50 skipped, 1 deselected, 0 failed, 0 errors.
     - "Not measured" counted as passed: fixed in the browser check (`f92bb83`, `sitecheck.py`) and the site
       total (`c58b62f`, `make.py`). A sweep of `src/proofhouse` found no other place. Still by design: a site
       checked without `--allow-commands` is saved as `"passed": true` and the count of checks that did not run
       is printed with `--json` only (`host.py` `_check_rows_pass_exit`). This was settled later: such checks are now saved as "not measured" (`7fce0a9`, below).
     - Limits audit (read only): the spend gate, most `--allow-commands` refusals and the install/deploy
       refusals have tests that fail if the limit is removed. No such test for: the referee's per-check time
       stop and its round/time settings; most secret-looking names (only `TOKEN` is proved removed, and the
       build list in `app_platforms.py` lacks `DATABASE_URL` and `CONNECTION_STRING`); render video failing on
       length, sound or frame size; `check hook` refusing without the flag; train's 1-50 epochs and same-host
       address rule. Boss chose all of them; they are done (`02f74b3`, below).
     - Checked by the new coordinator (2026-10-26, read-only): both Codex score files judge the old 30 s
       `film/final.mp4` (version 3) and the rebuilt 24 s promo, from 12 frames each, so they say nothing about the
       48.8 s film; the record-paths test diff (`992ccfe`) asserts the `<this-folder>` placeholder and that no
       machine path appears. Not re-checked: the 2409-passed suite figure, the earlier site/MCP/video proof reports.
     - Final examples table written (`examples/host-mode/README.md`, 16 rows, from the records and READMEs; the
       launch record's `site` part shows `failed` only because its browser check was not measured; the label
       is fixed in `host_launch.py` (now "not measured"), and the committed README was corrected by hand, not re-recorded; a later `check launch examples/host-mode/launch --allow-commands` passed all 36 checks, browser included, and is not saved in the record).
     - Final independent review (Opus, 2026-10-26, code diff vs main, read only): 7 findings, 4 proved by
       failing tests. High: `record launch` deletes and overwrites folders outside `--out` through an
       unchecked part `id` ("../x", absolute path, drive name; `host_launch.py` `_deliver_part`). Medium: a
       drive name such as "C:" in a record's `delivered` list wipes the saved versions (`host.py`
       `_clear_delivery`); the referee's cleaned environment is a deny list, so names like `GH_PAT` and
       `POSTGRES_URL` reach the check and are not redacted (builds use an allow list); the browser
       "no JavaScript errors" check passes when the browser never loaded the page (`sitecheck.py`); `record`
       prints nothing and returns 0 when the recorded version failed. Low: empty `facts` and empty shared
       names count as passed in launch checks; `compare` labels "a:b" and "a/b" save to the same file.
       The four proved findings are fixed, each with its failing test (`c0e5ec7` launch part ids, `394318c`
       referee allow list, `1efb23f` browser that exits with an error is "not measured", `e8535a7` only
       direct children of `--out` are cleared). Full suite after the fixes: 2421 passed, 50 skipped,
       1 deselected. The other three are fixed too, each with its failing test (`c8c907e` `record` says so and
       exits 1 when the version failed its checks, `0e09c4e` empty facts, avoid words and text-less shared
       names are not a pass, `bd8ba27` compare labels that clean to one name get their own file). Full suite
       after all seven: 2425 passed, 50 skipped, 1 deselected.
     - PR #85 merged into `main` (`a99773a`). The rest of Stage 2 is on `feat/finish-master-plan`
       (local, not pushed):
       - Checks that did not run are saved as "not measured", never as passed; `check` and `record` exit 3
         when nothing failed but something was not measured (`7fce0a9`).
       - The Codex repeat of the `prompt` example is merged (`e4ead31`); the branch with its scores
         (`1d1f922`) is left unmerged on purpose.
       - Limit tests, all of them (`02f74b3`): referee rounds, time and per-check timeout; build secret
         names; render video finished-file checks; hooks and MCP servers not started without
         `--allow-commands`; train epochs and model names that try to leave the service's host. Each
         limit was removed once by a script and a test caught every removal. Three real bugs found and
         fixed: `render video` returned 0 when the finished file had the wrong length, size or sound; the
         referee accepted `--for 0`; the build's secret-name list missed `DATABASE_URL` and
         `CONNECTION_STRING`.
       - Re-recorded with a score from an agent that did not write them (`62d13fc`): `mcp-record` version 3
         is the current server (Codex ran it: 7/10; it accepts a wrong JSON-RPC version and the install
         steps are unclear); `video-record` version 4 is the 48.8 s film, unchanged (Codex 7/10 from 16
         frames, the script and loudness; it cannot hear sound).
       - Housekeeping: merged worktrees removed (one locked folder, `.claude/worktrees/ok-none-sweep-266dd5`,
         could not be deleted while in use). The zod alert is closed: an npm override forces zod 4.6.6
         under Remotion, and the film re-renders with it (`2ce7084`).
     - Known issues, closed 2026-10-27: the desktop browser timeout no longer reproduces and reports
       "not measured" if it does; a screenshot at the wrong width (the Edge issue) is now "not measured",
       not passed (`61d1056`); the delegate run-ID collision is in the delegate tool, not Proofhouse.
   - **Stage 3, hard cases.** Two creative, hard cases for every one of the 39 `proofhouse` commands: the
     unusual but realistic use most likely to break each one (odd paths and names, empty, huge or wrong
     files, conflicting flags, bad numbers, repeat runs, half-finished earlier runs). The runner itself
     refuses absolute or parent paths, so folder-escape attempts are not among the 78. Each case states what should happen before it runs. They run offline with no keys and no
     money, each in its own throwaway folder (`scripts/stage3_hard_cases.py`). The results, with what
     broke, what held and what each cost, are in [stage3/hard-cases.md](stage3/hard-cases.md). Every real
     break is fixed with its failing test first.
     - Status: DONE. 82 cases across all 41 commands: 82 held, 0 broke, $0 spent. The first run broke 18; 9 were real defects, now fixed test-first (4e04676, d338472, d530ff4), 9 were wrong expectations. Findings in [stage3/findings.md](stage3/findings.md). Independent end review (Codex) done; its fixes are in the same findings file.

6. **Interview first (owner's correction, 2026-11-01).** Since `make` became the front door (PR #57) it wrote
   from one sentence, asked nothing and wrote for no tool in particular. That dropped the core of the
   product. `make` for text kinds (prompt, skill, agent, rule, copy, MCP server, hook, and add-on or learned
   kinds) now starts with the existing question engine (the framework's `generateQuestions`, used by
   `proofhouse case`), not a second one:
   - **Interview:** the questions for this request, asked one at a time on a terminal (pick a number, type
     an answer, or press Enter to let the model decide); follow-up questions appear only when an earlier
     answer calls for them.
   - **Say-back:** a short plain summary of what it understood; you accept it or correct it, and the
     correction is folded in.
   - **Target tool:** which AI tool or model the result is for (`--for`, or asked). Known tools come from the
     coding-tool host list (`hosts.json`), which now also carries how each tool wants a rule, skill, agent
     or prompt written; known models come from the model list. Anything else is researched by the writing
     model and saved like other learned entries. The writer, the judge and the reviser all see the answers,
     the agreed summary and the target's format and habits.
   - **Delivery for the target:** the rule, skill or agent comes out in that tool's format and the install
     line names that tool. When the target can be reached as a provider (for example the free agent bridge
     `agent-claude`), each version is also tried on it (`--try-on`); otherwise the record says it was not.
   - **Scripts and AI apps:** with no terminal and `--for` given, `make` writes the questions and an answers template into the
     folder and stops; running it again with `--answers` continues. Everything asked and answered is kept in
     `record.json`.
7. **Every make, every kind, the same way (owner's direction, 2026-11-02).** Step 6 covered text kinds only.
   Three gaps are left, each fixed in its own branch and pull request:
   - **7a. Sites, apps and launches ask first.** Today they go straight to building (`make.py`
     `interviewing` leaves out site and app; the CLI never builds an interviewer for them; `launch` has none).
     They get the same interview, say-back and target question. Here the target is where it will live and
     run: a deploy target for a site, the platforms for an app, and for a launch each part's target. The
     answers and agreed summary feed the writer, the existing build-and-check loop and the judge, and the
     result is scored against them. For a launch, one interview covers the goal and only the questions
     specific to a part are asked per part.
     **Done (branch `feat/make-interview-site-app`).** A site is asked where it will be published (the
     deploy list), an app which platforms (`app_platforms.json`; `--platform` answers it), and a launch
     asks the shared questions once and then each part only its own. An unknown place is learned, not
     refused; a learned platform still needs `proofhouse addons approve learned <id>` before anything is
     built for it, because platforms carry build commands. Pause and resume work through `--answers`.
   - **7b. Every run asks.** A run with no terminal and no `--for` now pauses like any other: it writes the
     questions, including which tool or model it is for, into the folder with an answers template and
     stops. It no longer prints a tip and makes the thing blind. `--answers` resumes and `--preset` fills
     answers ahead. Nothing goes round the interview without saying so in the record.
     **Done (branch `feat/make-always-asks`).** Every paused make or launch exits 9, so a script can tell
     "waiting for answers" from "made". `record.json` has `interview_from`.
   - **7c. Media through the same front door.** `make --kind video|image|voice|music` (and any media kind
     learned or added as data) runs the full loop: interview (purpose, audience, length, look, voice, music,
     where it will be shown), say-back, target (which service and model, any provider in
     `media_providers.json`, local programs included; an unknown one is learned, not refused), make, check,
     judge, improve, keep every version, deliver in the shapes asked for. Video builds on the beat-film
     engine in PR #96 (`feat/video-motion`) rather than beside it. `generate` stays as the one-shot
     command. Every paid call goes through the spending limit.
     **Done (branch `feat/make-media`, on top of PR #96 and 7b).** Each version's plan is kept in
     `v<n>/plan.json` and only the best version that passed every check is delivered into `delivered/`.
     The record says what the judge was sent (`judging`, and `judged_on` per version). image, voice and music are now
     reserved kinds, so a learned kit or add-on cannot take them over. A paused run prints a command to
     run again that keeps the length, shapes and other choices given. A film missing a shape it was asked
     for fails its checks; a studio stopped by the spending limit stops the whole make; a shape that could
     not be delivered is named (`undelivered`) and the run exits 7. A launch's video part is now
     interviewed and made through this same loop. Still open: a kind nobody taught
     (such as "podcast") is not learned as a media kind yet.
8. **The full video engine behind `make --kind video`** (branch `feat/video-engine`). One goal: a film
   with pictures, voice, music, sound and editing comes out of the front door on any machine, at $0 with
   local programs and at full quality with any paid service, and the judge looks at it before scoring.
   - **8a. $0 makers ship as data.** A music bed maker (`local-music`, made from scratch in Python: chords,
     bass, pads and drums picked from the mood words) and a local voice (`local-voice`: the speech engine
     this machine already has, such as Windows speech, macOS `say`, espeak-ng, Piper or Kokoro) ship as
     entries in the media list. A run entry may start the Python that runs Proofhouse (`@python`).
   - **8b. Gaps filled, never failed.** A film with words and no voice service named gets the local voice; a
     film with no music service gets the local bed. The record names what stood in.
   - **8c. The judge looks and listens.** Each version's judge gets frames from the film (a contact sheet),
     the picture itself for an image, and measured sound facts (loudness, how much of the film has voice,
     music and silence). The spending limit counts each picture at a fixed worst case. A model that cannot
     take pictures is asked again with words only, and the record says exactly what the judge saw and heard.
     **Done.** The judge is sent a smaller copy of an image, or a 4 x 3 contact sheet of twelve moments
     from a film, as an inline picture through the spend gate (each counted as 32,768 tokens, at most 1024 px
     a side). For sound it reads measured loudness, peak, length and the share that is silent; telling
     voice from music is not measured yet. Each version's `judged_on` keeps the picture sent, the sound
     facts, why it judged from words alone when it did, and what the model said it saw (its own claim).
   - **8d. Finishing.** The voice must fit the film (no words cut off), a film that fails a check is not
     left behind as if it were finished, beat films lay out properly in 9:16, and a callout over a
     recording finds its place by itself.
     **Done.** When the voice runs long, the shots are lengthened a second at a time (the busiest first)
     and the record says so; a beat film checks that its last word ends before the film does. A render
     with a failed check is renamed `video-<shape>.failed.mp4` and never delivered. In 9:16 the words are
     half again as large, boxes widen, cards wrap to two columns and the layout spreads down the frame.
     A callout or pointer on footage that holds still is given in the footage's own pixels and placed by
     itself. The lower-third plate, the callout's label and the words inside cards, panels and terminals
     are enlarged in 9:16 too (`text_scale`).
   - **8e. Front door details.** The interview record names `--for` and presets correctly, and
     `docs/usage.md` covers the media interview and exit 9.
     **Done.** `interview_from` names the answers file, the terminal, a launch or the caller, and the flag
     that named the tool (`--for`, `--platform` or the service flags); the record keeps `interview_preset`.
     A media part made inside a launch now records "launch", as text parts already did.
   - **8f. A free film made end to end.** A whole film made at a $0 limit with a free local model and the
     local picture program, with every weakness the run showed fixed rather than worked around.
     **Done.** A $0 limit runs free local models, and the model is asked for JSON only. A film fits the
     length asked for, and beats with no layers still move. The picture service is never the film's subject:
     the plan and script writers and the judge are told only what each tool makes, never its name.
     The interview asks each question once, gives each one its own id, and never asks what the command
     already set (length, shapes, the services the flags name, even when an answers file is given); a
     question about a length or shape the command set is dropped even when the model asks it anyway.
     A layer time or beat pace (energy, cut) the script writer never fixes plays at its default instead of
     losing the film.
     When the script has several problems, the writer is told all of them at once.
     Stray text in a script's beats is named to the writer, and left out if it stays. A script that is still
     too long after its fixes keeps its opening and close and cuts middle beats to fit, and the record names
     each cut. The plan and the judge are asked for JSON; a plan with no prompt is asked for once more, and
     its reply is kept if it still has none. A model that refuses a picture is not sent one again.
     A number the writer gives as text ("500") is read as that number, and a model on this machine is
     waited for up to 600 seconds (120 elsewhere), since a CPU model is slow but never billed. A shape
     question in plain words ("wide, tall or square?") is dropped like "16:9?" when the command set the shapes.
     Runs on 2026-11-04: llama3.2 plus the local picture program made the 10-second film at $0 each time.
     After the last fixes, all three versions were made with none lost (9 calls); llama3.2 cannot see
     pictures, so it judged on the words alone, and the record says so.
   - **8g. Quick local films.** No step of a film waits minutes on a model on this machine.
     **Started.** llama.cpp (`llama-server`) is the first local engine `proofhouse setup` suggests, started with
     room for a film script (`-c 16384`) and thinking off (`--reasoning-budget 0`); Ollama, LM Studio and vLLM
     still work. Run on 2026-11-07 with LFM2.5-8B-A1B on the Vulkan build: every model step took under 80 s and
     the judge gave 9/10, at $0. `--judge PROVIDER/MODEL` now lets a model that sees pictures judge while the
     quick text model writes; Qwen3-VL-4B on this PC reads 140 and writes 10 tokens a second. Still to do: a
     whole film judged by it, and making the pictures and the final render, which still take the whole run past
     5 minutes.
     **Measured 2026-11-07, one model for everything** (Qwen3-VL-4B Q4_K_M, plain `-c 8192 --jinja`; the
     quantised-cache flags hang on this build). The film was written, judged and rendered on this PC at $0,
     and the judge looked at the pictures: it gave 0/10 because the pictures showed factory scenes, not the
     terminal the brief asked for. That is a fair verdict, so the plan is still not met. Steps over 5 minutes:
     the script writer (three tries of 276, 321 and 317 s; the whole script is 4 to 6 thousand tokens at about
     7 a second, and each fix round sends it all again), the voice (40 clips, about 15 s each, 10 minutes), and
     the pictures (made by hand through Gemini in the browser, about 19 minutes for 10). Under 5 minutes: music
     (seconds), final render (about 4 minutes), judge (about 12 s). Whole run 51 minutes. Two film faults are
     fixed with a test each: a version counter that showed a stray "1" because the facts said "one line" (a
     spelled-out "one" no longer licenses a counter to 1), and a blank caption line, which now says a full stop.
     To do: write the script one beat at a time so no request is long, fix the rounds that resend it all,
     and speed up the voice.

## What is left (updated 2026-10-27)

All build steps above are done, and the gaps between "works" and "ready to hand out" found on 2026-10-27
are fixed test-first: `proofhouse --version`, help that names `proofhouse`, the demo's reopen lines and
measured run time, the MCP example's JSON-RPC check and install steps, the wrong-width screenshot, the
film record pointing at the tracked MP4, zod forced to 4.6.6, and the full 0.10.0 CHANGELOG.

1. Done: pull request #86 passed the full suite, CI on all three systems and an independent review and
   re-review, and was merged on 2026-10-27.
2. Done: v0.10.0 is on PyPI and GitHub. 0.10.1 (the #88 fix, the agent bridge, mixed stills and clips,
   the hook-writer fix) is prepared on a branch and held until the owner says to push it.
3. U5: a fresh user tries the reference workflow (completion criterion 6). No agent can do this; it waits
   on the owner's tester, with the wheel rebuilt in `dist-tester/`.

Settled: the owner judged the example videos' sound and motion fine; the train-2 upload gap is accepted
with no live key; the film MP4 stays out of the repo and the record points at `../video/final-premium.mp4`.

## Known limits

- `--allow-commands` is an opt-in, not a sandbox. Made MCP servers, hooks and app builds run
  model-written code with your rights.
- App setup runs `npm install --ignore-scripts`, but the build itself still runs the project's own build
  files, such as a Rust `build.rs` or Gradle scripts.
- Builds get a cleaned environment plus named tool locations only; names that look like keys, tokens or
  passwords are refused. On Linux and macOS a process that detaches itself can outlive the build's
  time limit.
- The real tool folders a platform names (such as `CARGO_HOME`, `GRADLE_USER_HOME`, `APPDATA`) are visible
  to its build, so a build script can read whatever those tools keep there.
