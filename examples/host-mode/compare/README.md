# Host-mode compare example (Tidewatch)

Tidewatch is an invented pocket tide-table app. It exists only so three agents can answer the same tiny copy job without Proofhouse calling any model.

## The job

`job.txt` asks for the opening paragraph (45–60 words) of a landing page: plain words, concrete detail, no filler such as revolutionary, seamless, or game-changing, and the app must work fully offline. The reply should be only the paragraph.

## Who wrote the three answers

| Label | Source |
|-------|--------|
| **codex** | Codex CLI, using that tool’s own subscription (saved before this example) |
| **grok** | Grok CLI, using that tool’s own subscription (saved before this example) |
| **cursor** | The Cursor agent in this repo session (host mode: no Proofhouse API key) |

Files live under `outputs/`. Codex and Grok outputs were not edited for this example.

## Rubric and scores

The Cursor agent judged all three with the same rubric:

1. Word count between 45 and 60 (counted with a small Python script using `[A-Za-z0-9]+` tokens, not by eye).
2. Concrete places or uses, not vague hype.
3. No banned filler words from the job.
4. Readable in one pass.
5. States clearly that the app works offline (not only “no signal”).

| Label | Words | Score | Note |
|-------|------:|------:|------|
| codex | 51 | 7/10 | Never says offline; signal-free wording is still clear and concrete. |
| grok | 46 | 9/10 | Says offline upfront with plain high/low language and sharp scenes. |
| cursor | 48 | 8/10 | Offline and local data are clear; slack or flood is slightly niche jargon. |

Scores are one agent’s advice on style and rubric fit, not proof of quality. The paragraphs were **not** checked for factual claims about tides or apps, because Tidewatch is fictional.

## Command

From the repo root, after `outputs/cursor.md` exists:

```bash
uv run --no-sync proofhouse compare "$(cat examples/host-mode/compare/job.txt)" \
  --entry codex=examples/host-mode/compare/outputs/codex.md \
  --entry grok=examples/host-mode/compare/outputs/grok.md \
  --entry cursor=examples/host-mode/compare/outputs/cursor.md \
  --score codex=7 --score grok=9 --score cursor=8 \
  --note codex="Never says offline; signal-free wording is still clear and concrete." \
  --note grok="Says offline upfront with plain high/low language and sharp scenes." \
  --note cursor="Offline and local data are clear; slack or flood is slightly niche jargon." \
  --out examples/host-mode/compare/result
```

On Windows PowerShell, read `job.txt` into a variable and pass it as the first argument instead of `$(cat ...)`.

## What `result/` shows

- **`compare.json`** — job text, labels, byte sizes, SHA-256 hashes, scores, notes, and which label had the highest score (`grok` here).
- **`side-by-side.html`** — the job and all three paragraphs in columns, with scores and notes. Untrusted text is HTML-escaped; there is no `<script>` in the page.
- **`outputs/`** — copies of the three source files used for the record.

## What this does and does not prove

**Does:** Proofhouse can assemble a file-based comparison and a readable side-by-side page with no API key and no model call inside Proofhouse.

**Does not:** Pick a universally best writer, validate tide science, or show that any CLI subscription is “better” in general. This is one run, one short job, and three subjective scores from the same Cursor session that also wrote the third answer.
