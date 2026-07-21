# Exclusions

Material deliberately left out of `PromptRig-Central`, and why.

## Non-candidate folders (not reviewer working folders)

| Path | Reason |
|---|---|
| `C:\AI\CodexHome` | The OpenAI Codex CLI's application home/state directory: `config.toml`, `sessions/`, sqlite databases, `plugins/`, `.sandbox/`, `auth.json`, `.credentials.json`. No PromptRig corpus markers anywhere in it. Contains what appear to be live application credentials — not opened, not copied, not hashed. |
| `C:\AI\Gemini` | Unrelated Gemini-branded personal project notes (Adversarial Encyclopedia plan, Project Alexandria Wiki, Universal Web Clipper, WebClipper). No PromptRig corpus markers. |
| `C:\AI\Codex\1st` | Completely empty directory. |
| `C:\AI\Codex\KM-it-ops.github.io` | Unrelated personal portfolio / GitHub Pages site (contains its own `.git/`). No PromptRig corpus markers. |
| `C:\AI\Codex\preview-screenshots` | Screenshots belonging to the KM-it-ops.github.io portfolio site above. Unrelated to PromptRig. |

None of the above were copied, hashed for inventory purposes, or mutated in any way.

## Disposable material excluded from within the four confirmed reviewer working folders

All four working folders (`claude promptrig-review-launch-v0.4`, `gemini promptrig-review-launch-v0.4`,
`kimi k3 promptrig audit`, `Codex\codex promptrig v0.4 audit`) were otherwise copied in full via the
canonical/clean-corpus seed and the reviewer-specific differential snapshots. The following disposable
items were excluded per the standing rule against caches/VCS/dependency directories:

| Path | Reason |
|---|---|
| `Codex\codex promptrig v0.4 audit\promptrig-review-launch-v0.4\.git` | Git metadata directory. Present but empty (no commits) — disposable VCS state, not review evidence. |
| `Codex\codex promptrig v0.4 audit\promptrig-review-launch-v0.4\.agents` | Tool-state directory. Present but empty. |

No `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, build output, or editor cache
directories were found in any of the four reviewer working folders — the corpus is documentation/schema/
script content only.

## Scaffold files common to every reviewer copy (not reviewer-specific, not duplicated per-reviewer)

`09-review-execution/evidence/CORPUS_SHA256.txt` is byte-identical across all four reviewer folders and
the canonical launch-pack baseline (verified by SHA-256). It is part of the launch pack scaffold, not
reviewer-generated evidence, and is already preserved once under `canonical-source/`. It was not
duplicated into each reviewer's result/snapshot directory.
