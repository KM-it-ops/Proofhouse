---
name: proofhouse-host
description: Use when you write and judge Proofhouse work in Cursor, Codex, Gemini CLI, Grok CLI or Claude Code with no API key—check, record and render locally.
---

# Proofhouse host mode

You write and score the work with your own model and shell. Proofhouse checks, keeps every version and assembles the best one. No API key for `proofhouse check`, `proofhouse record` and `proofhouse render video`, and Proofhouse itself makes no network calls on them. With `--allow-commands` it runs the code you wrote, and that code may use the network, so only pass it for code you trust.

## Loop

1. Write version 1 in a folder (shapes below).
2. Run `proofhouse check <kind> <path>` and fix every line that says FAIL.
3. Run `proofhouse record <kind> <path> --out <dir> --request "<goal>" --agent <name> --score <0-10>` for each round. Be honest on the score.
4. Stop when checks pass and the score is high enough, or when you hit the round limit the person set.

Scores are advice because the same model writes and judges. If the person has a second agent (e.g. Codex or Gemini CLI), ask it to judge a version and record that score instead. Paid image, voice or music services still go through Proofhouse spending limits and need the person's dollar cap.

## Kinds and folders

| Kind | What to create |
|------|----------------|
| **prompt** | A single `prompt.md` (or any `.md` file) with the prompt text. |
| **skill** | Folder with `SKILL.md` (YAML frontmatter: `name`, `description`) and any support files. |
| **agent** | One `.md` file with the same frontmatter as a skill. |
| **rule** | One `.md` file with standing instructions (no frontmatter required). |
| **site** | Folder with `index.html` and linked pages/assets (static, no build). Page checks always run; add `--allow-commands` to also open it in a headless browser. |
| **app** | Folder with `index.html`, `manifest.webmanifest` (`name`, `start_url`, `display`, `icons`) and `service-worker.js`; the page links the manifest and registers the worker. Use `--allow-commands` to also open it in a headless browser. |
| **copy** | A single `copy.md` with the page or message text. Checked for presence and leftover filler only. |
| **mcp** | Folder with `manifest.json` (`name`, `command`, `args`, optional `files`) plus server files. Use `--allow-commands` on check/record to start the server. |
| **hook** | Folder with `manifest.json` (`event`, `matcher`, `command`, `sample_event`) plus hook script. Use `--allow-commands` on check/record. |
| **video** | Folder with `script.json` (`title`, `voiceover`, `music`, `shots[{seconds, visual, caption, file}]`, optional `voice_file`, `music_file`) and your shot images or clips, voice and music files. Then `proofhouse render video <folder> [--formats 16x9,9x16,1x1]`. |

## Commands

```bash
proofhouse check site ./my-site
proofhouse check mcp ./my-mcp --allow-commands
proofhouse record site ./my-site --out ./out --request "bakery landing" --agent cursor --score 8
proofhouse compare "the job" --entry cursor=out-a.md --entry codex=out-b.md --score cursor=8 --score codex=9
proofhouse render video ./my-video --formats 1x1 --size-scale 0.25
```

Delivered output lands under `--out` (site copy, skill folder, `final.md` for prompts, `INSTALL-MCP.txt` or `settings-snippet.json` for MCP/hook). Video renders write `video-<format>.mp4`, `captions.srt` and `studio.json` in the video folder.

## Limits to know

- `--out` must be a new or empty folder (or one a previous `record` made), and must not hold or sit inside the thing you record.
- Folders may not contain symbolic or hard links.
- An MCP or hook is not counted as passed until its check has actually run, which needs `--allow-commands`.
- Video shots are pictures or clips (png, jpg, webp, gif, bmp, mp4, webm, mov, mkv); voice and music are wav, mp3, m4a, aac, ogg, flac or opus.
