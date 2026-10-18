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
| Make apps for every platform | works for the source and checks; native builds to check (below) |
| Images, video, voice, music; full video engine (generated clips, images, voice, music, editing, render) | works |
| Multi-part launch from one goal | works |
| Install agents, rules and MCP servers into Claude Code, Cursor, Codex, or any tool added | works |
| Loops that run on their own within limits | works |
| Train and fine-tune models (online services or on your own machine) | works |
| Add-ons that add providers, services, tools and make kinds | works |
| Project scan | works |
| Evidence record: sealed benchmarks, type-strict rubric scoring, strict JSON inputs, required requirement coverage | works (four old defects fixed 2026-10-16) |

### Apps in detail

`proofhouse make --kind app` makes one shared web app, then wraps it for each platform listed in
`app_platforms.json` (shipped list plus your own in `~/.proofhouse/app_platforms.json`). Each platform
says what the model writes, what is checked, and how it is built.

| Platform | Made with | Checked offline | Built (with `--allow-commands`) |
|----------|-----------|-----------------|--------------------------------|
| Installable web app (PWA) | manifest, icon, service worker | manifest linked, icon exists, worker exists and registered, page opens in a browser | nothing to build |
| Windows, macOS, Linux | Tauri v2 around the web app in `www/` | required files, JSON keys | setup (`npm install`, `tauri icon`), then `tauri build` on a matching machine; fails if the output folder is missing |
| iOS, Android | Capacitor around the web app in `www/`; native projects made by `cap add`, not by the model | required files, JSON keys | setup (`npm install`, `cap add`), then `cap build` |

To check on real machines (not yet run end to end):

- Tauri: `tauri icon` with an SVG source, and the `www/` layout as the web folder.
- Capacitor: `cap build` needs signing set up (Xcode team on iOS, a keystore on Android) and may stop
  without it; where iOS writes its app file is not checked yet.

## Build order

1. Rules, MCP servers and hooks as make kinds. Done.
2. Apps for every platform as one make kind. Done for source, checks and builds; native builds to check.
3. Next, as units (approved 2026-10-17). Each unit runs in its own session and branch. Claude writes
   the failing test first and judges the result; Cursor, Codex or agy runs the edit-test loop, and a
   tool from a different company checks each diff.
   - **U0, tidy-up.** Land the answer key below, stop add-ons from claiming the built-in kind names
     rule, mcp and hook (the way `app` already is), and delete stale branches.
   - **U1, run compiled artifacts on every provider,** not only OpenAI-compatible ones (completion
     criterion 1, [audit](assurance/2026-10-16-completion-criteria.md)). A requirement a provider
     cannot carry stops the run before sending. Codex loop, agy check, one Opus security pass.
   - **U2, `proofhouse "<goal>"` picks the right kind of thing to make.** A model picks when one is set
     up; better built-in rules pick otherwise. Today's word-matching picks correctly on 7 of 32 goals in
     the approved answer key, [overseer-test-set.md](overseer-test-set.md). The rules are also scored on
     a second set of goals the loop never sees. Cursor loop, Codex check.
   - **U3, native app builds on real machines.** A fixed sample app builds on Windows here and on Linux,
     macOS, iOS and Android in a GitHub Actions job started by hand. The iOS build gets an output path
     to check, and coarse file timestamps stop causing false failures. One Opus security pass.
   - **U4, the dashboard works by keyboard, at phone width and with reduced motion** (completion
     criterion 9). The tests must fail on three copies broken on purpose. Cursor loop, Codex check.
   - **U5, final gate,** once U1 to U4 are merged: a fresh full review and fix, a new completion-criteria
     statement, a try by a fresh user, then the 0.9.0 release on the owner's word.

## Known limits

- `--allow-commands` is an opt-in, not a sandbox. Made MCP servers, hooks and app builds run
  model-written code with your rights.
- App setup runs `npm install --ignore-scripts`, but the build itself still runs the project's own build
  files, such as a Rust `build.rs` or Gradle scripts. The iOS build has no output path to check yet, so
  any successful exit passes it (to check on a Mac).
- Builds get a cleaned environment plus named tool locations only; names that look like keys, tokens or
  passwords are refused. On Linux and macOS a process that detaches itself can outlive the build's
  time limit.
- The real tool folders a platform names (such as `CARGO_HOME`, `GRADLE_USER_HOME`, `APPDATA`) are visible
  to its build, so a build script can read whatever those tools keep there.
