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
- **Every make runs the same loop:** write, try it for real, judge, revise, keep every version.
- **Checks and comparing versions are one feature of the record,** not the product.

## Where it stands

| Area | State |
|------|-------|
| Run any prompt on any provider; compare many models on one job | works |
| Make prompts, skills, agents, copy | works (host mode: examples for prompt, copy, app, rule, agent, skill, hook, site, mcp) |
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
   installing the package and one skill. Version 0.10.0 is prepared in the package and not published.
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
         could not be deleted while in use). The zod alert stays open: Remotion pins zod at exactly 4.5.4,
         so it waits on Remotion.
     - Known issues, only logged: the desktop browser check on the example site can time out (it reports
       "not measured", not PASS); Edge width; delegate run-ID collision.
   - **Stage 3, hard cases.** Two creative, hard cases for every one of the 39 `proofhouse` commands: the
     unusual but realistic use most likely to break each one (odd paths and names, empty, huge or wrong
     files, conflicting flags, bad numbers, repeat runs, half-finished earlier runs). The runner itself
     refuses absolute or parent paths, so folder-escape attempts are not among the 78. Each case states what should happen before it runs. They run offline with no keys and no
     money, each in its own throwaway folder (`scripts/stage3_hard_cases.py`). The results, with what
     broke, what held and what each cost, are in [stage3/hard-cases.md](stage3/hard-cases.md). Every real
     break is fixed with its failing test first.
     - Status: DONE. 78 cases across all 39 commands: 78 held, 0 broke, $0 spent. The first run broke 18; 9 were real defects, now fixed test-first (4e04676, d338472, d530ff4), 9 were wrong expectations. Findings in [stage3/findings.md](stage3/findings.md). Independent end review (Codex) done; its fixes are in the same findings file.

## What is left (updated 2026-10-27)

All build steps above are done. Branch `feat/finish-master-plan` holds 15 commits that are not pushed and
not yet a pull request. What is left is the owner's call, not new building:

1. Push `feat/finish-master-plan`, open the pull request and merge it to `main`.
2. Publish 0.10.0 (version set and CHANGELOG written; not tagged, not on PyPI).
3. U5: a fresh user tries the reference workflow (completion criterion 6). No agent can do this.
4. Put the finished 48.8 s film MP4 back in the repo, or keep it out (kept out today to save space).
5. The zod alert waits on Remotion, which pins zod at exactly 4.5.4.
6. Known issues, only logged: the desktop browser check on the example site can time out (it reports
   "not measured"); Edge width; delegate run-ID collision.
7. Not yet judged: the sound and motion of the example videos (Codex saw frames and text only), and the
   Codex finding that the example MCP server accepts a wrong JSON-RPC version.

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
