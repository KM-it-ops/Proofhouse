# Tidewatch host-mode launch example

**Tidewatch is invented.** It is a fictional pocket tide-table app used to show how Proofhouse checks a multi-part launch in host mode (no API key, no model calls from Proofhouse itself).

## What is in this folder

| Part id | Kind | Path | Role |
| --- | --- | --- | --- |
| site | site | `site/` | Static landing page (`index.html`, `style.css`) |
| announce | copy | `announcement/copy.md` | Launch announcement post |
| support | skill | `support-skill/SKILL.md` | Support skill for user questions |
| release-notes | prompt | `prompt/prompt.md` | Prompt another agent can use to draft release notes |
| promo | video | `video/` | `script.json`, six shot clips, voice, music, and the rendered 16:9, 1:1 and 9:16 MP4s (24 s) |

`launch.json` is the manifest: goal, tone, shared names, facts, avoid-words, and the part list.

## Shared story (must stay aligned)

- **Name:** Tidewatch
- **Tagline:** Tide tables in your pocket, no signal required.
- **Price:** $4.99 one-time purchase
- **Three facts** (each must appear somewhere across the parts):
  - Works fully offline with bundled tide data for two years
  - No accounts and no ads
  - $4.99 one-time purchase
- **Avoid words** (must not appear in any part text): revolutionary, seamless, game-changing, lorem

## Commands

From the repository root:

```bash
uv run --no-sync proofhouse check launch examples/host-mode/launch
uv run --no-sync proofhouse record launch examples/host-mode/launch --out examples/host-mode/launch-record --request "your one-line goal" --agent cursor --score 7
```

The promo is built by scripts in `video/`, all free and local:

- `capture_app.py` records the Tidewatch screen prototype (`video/app/index.html`) frame by frame with the installed Chrome. The app really moves: list, tap, tide curve, offline badge, price sheet. Frames go to `video/app/frames/` (git-ignored, 66 MB).
- `build_shots.py` puts that recording in a phone over a blurred backdrop and writes `shot-01.mp4` to `shot-06.mp4`. The backdrop for shots 1 to 5 is `gen/shore.mp4` (dawn low-tide shore) and for shot 6 `gen/dinghy.mp4` (a skipper tying off a dinghy as the water floods back). Both are 10-second 1280x720 clips generated in Gemini ("Create video") on the owner's free allowance, one prompt each, no retakes; the prompts are in `gen/PROMPTS.md`. Shot 1 and shot 6 show the clip as it is; shots 2 to 5 blur it behind the phone.
- `build_voice.py` speaks the lines with Kokoro (Apache-2.0, CPU, no network at run time). `build_music.py` makes the music with numpy. Nothing here is paid.
- `proofhouse render video examples/host-mode/launch/video --formats 16x9,1x1,9x16` joins it all with FFmpeg.

## What `check launch` proves

- `launch.json` is valid and lists at least two parts with safe paths.
- Each part folder or file exists and passes that kind’s own checks (site HTML structure and links, copy/prompt filler scan, skill frontmatter, video `script.json` fields and shot files on disk).
- Every **shared name** appears in every text-bearing part (site HTML text, copy, skill, prompt, video script title/voiceover/captions).
- Every **fact** appears in at least one part somewhere in the bundle.
- **Avoid** words do not appear in any part text.

## What it does not prove

- Visual design quality, accessibility beyond the automated site rules, or whether a human would enjoy the copy.
- Truth of tide predictions, store availability, or any real-world claim (the product is fictional).
- That the promo video looks or sounds good. The check reads `script.json` and the shot files; the render step checks length, size and that sound is present. Frames were looked at; the audio has been measured (mean -23.1 dB) but not listened to.
- That a second agent would produce good release notes from the prompt without your review.

## Record rounds

`examples/host-mode/launch-record/` holds Proofhouse `record` output: delivered parts, `launch.json`, generated `README.md`, and `record.json` with scores.

- **Round 1 (score 6):** First complete pass; support skill still mentioned banned words in a “do not say” example (fixed before final check).
- **Round 2 (score 7):** Removed nested SVG `<title>` tags that confused the site title check, tightened landing accessibility labels, and expanded this README.

**Still rough if this were a real ship:** a real app build instead of the HTML prototype, longer or more varied generated clips (only two were made, and the clips are 720p), a voice and music a person has listened to and chosen, and a second human or agent review of announcement tone.
