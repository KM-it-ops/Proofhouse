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
| Make prompts, skills, agents, copy | works |
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
