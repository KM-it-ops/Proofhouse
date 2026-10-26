# Tidewatch host-mode launch example

**Tidewatch is invented.** It is a fictional pocket tide-table app used to show how Proofhouse checks a multi-part launch in host mode (no API key, no model calls from Proofhouse itself).

## What is in this folder

| Part id | Kind | Path | Role |
| --- | --- | --- | --- |
| site | site | `site/` | Static landing page (`index.html`, `style.css`) |
| announce | copy | `announcement/copy.md` | Launch announcement post |
| support | skill | `support-skill/SKILL.md` | Support skill for user questions |
| release-notes | prompt | `prompt/prompt.md` | Prompt another agent can use to draft release notes |
| promo | video | `video/` | `script.json` plus shot PNGs (structure only; not rendered to MP4) |

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

Shot images were generated once with `video/generate_shots.py` (stdlib only). Re-run that script if you change captions.

## What `check launch` proves

- `launch.json` is valid and lists at least two parts with safe paths.
- Each part folder or file exists and passes that kind’s own checks (site HTML structure and links, copy/prompt filler scan, skill frontmatter, video `script.json` fields and shot files on disk).
- Every **shared name** appears in every text-bearing part (site HTML text, copy, skill, prompt, video script title/voiceover/captions).
- Every **fact** appears in at least one part somewhere in the bundle.
- **Avoid** words do not appear in any part text.

## What it does not prove

- Visual design quality, accessibility beyond the automated site rules, or whether a human would enjoy the copy.
- Truth of tide predictions, store availability, or any real-world claim (the product is fictional).
- That the promo video was rendered (no FFmpeg step; PNGs and JSON only).
- That a second agent would produce good release notes from the prompt without your review.

## Record rounds

`examples/host-mode/launch-record/` holds Proofhouse `record` output: delivered parts, `launch.json`, generated `README.md`, and `record.json` with scores.

- **Round 1 (score 6):** First complete pass; support skill still mentioned banned words in a “do not say” example (fixed before final check).
- **Round 2 (score 7):** Removed nested SVG `<title>` tags that confused the site title check, tightened landing accessibility labels, and expanded this README.

**Still rough if this were a real ship:** real app screenshots instead of SVG mocks, rendered promo video, and a second human or agent review of announcement tone.
