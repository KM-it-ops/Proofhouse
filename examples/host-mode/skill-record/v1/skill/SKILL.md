---
name: changelog-from-git
description: Use when preparing a release and you need a Keep a Changelog entry from conventional commits in a git repository—run the script, polish the wording, confirm the version, and prepend to CHANGELOG.md.
---

# Changelog from git

Turn a repository's **conventional commit** history into a **Keep a Changelog** release section you can paste at the top of `CHANGELOG.md`.

## When to use

- Cutting a release and the team already uses `feat:`, `fix:`, `refactor:` (and similar) commit subjects.
- You want grouped **Added / Changed / Fixed** bullets with optional **scope** prefixes, without hand-sorting `git log`.

Do **not** use this for repos that do not use conventional commits, or when you only need a raw commit list.

## Workflow

1. From the skill folder (or anywhere), run the script against the target repo path (relative paths only):

   ```bash
   python scripts/changelog.py <repo-path>
   ```

   Optional flags:

   - `--since <git-ref>` — only commits after that ref (default: everything since the **latest tag**, or the **full history** if there is no tag).
   - `--version X.Y.Z` — use that version in the `## [X.Y.Z] - date` heading; omit it when you are still drafting.

2. Read the Markdown on **stdout**. Progress notes and errors go to **stderr**; a bad repo path or unknown `--since` ref exits non-zero.

3. **Review and tidy** the bullets (tense, duplicates, user-facing wording). The script only maps types; you judge quality.

4. **Ask the user for the release version** if you did not pass `--version`.

5. **Prepend** the block to `CHANGELOG.md` (create the file with a short Keep a Changelog header if missing). Keep older releases below the new entry.

## What the script includes

| Commit type | Section |
|-------------|---------|
| `feat` | ### Added |
| `fix` | ### Fixed |
| `refactor`, `perf` | ### Changed |
| `chore`, `docs`, `test`, `ci` | omitted |

- Scope in parentheses becomes a bold prefix, e.g. `feat(api): …` → `- **api:** …`
- `type!:` or a `BREAKING CHANGE:` footer appends **BREAKING** on that line.

## Example

**Commits (oldest first):**

```
feat(api): add export endpoint
fix(ui): stop the modal flickering
chore: bump deps
docs: fix typo
refactor(core): split the parser
feat!: drop Python 3.9
```

**Command:**

```bash
python scripts/changelog.py . --version 2.0.0
```

**Output (abbreviated):**

```markdown
## [2.0.0] - 2026-10-25

### Added
- **api:** add export endpoint

### Changed
- **core:** split the parser

### Fixed
- **ui:** stop the modal flickering
- drop Python 3.9 **BREAKING**
```

## Edge cases

- **No commits:** prints an empty release stub on stdout; message on stderr.
- **No matching commits in range:** `## [version] - date` with a short “no user-facing changes” note.
- **Not a git repo / bad ref:** error on stderr, non-zero exit.
