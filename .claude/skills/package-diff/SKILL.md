---
name: package-diff
description: Builds a unique SDD review package file (commits, stat, full unified diff) for BASE..HEAD without loading the diff into the controller context. Part of the Proofhouse SDD skill set (implement-task, review-task, package-diff). Use before dispatching review-task on Windows, or whenever a bash review-package script is unavailable. Prefer the PowerShell script in this skill's scripts/ folder.
---

# Package diff

Produce one review-package markdown file for a task reviewer. Controllers should **not** paste the diff into chat.

## When to use

- After implement-task reports `DONE` / `DONE_WITH_CONCERNS`
- BASE = commit recorded **before** dispatching the implementer (never `HEAD~1` for multi-commit tasks)
- HEAD = current task branch tip

## Windows (PowerShell 7+)

The script is bundled with this skill at `.claude\skills\package-diff\scripts\New-SddReviewPackage.ps1`
(repo-relative). Run it from the worktree being packaged, not from a fixed drive path.

Run:

```powershell
pwsh -File "<worktree>\.claude\skills\package-diff\scripts\New-SddReviewPackage.ps1" `
  -RepoRoot "<worktree>" `
  -BaseSha "<BASE>" `
  -HeadSha "<HEAD>" `
  -OutFile "<worktree>\.superpowers\sdd\task-N-review-package.md" `
  -TaskLabel "Task N"
```

The script prints the outfile path on success.

## Package contents (required)

1. Title + BASE + HEAD SHAs
2. `git log --oneline BASE..HEAD`
3. `git diff --stat BASE..HEAD`
4. `git diff -U10 BASE..HEAD` fenced as `diff`

## Controller rules

- Do not Read the whole package into your own context after writing it — hand the **path** to the reviewer.
- If HeadSha is omitted, resolve `git rev-parse HEAD` inside RepoRoot.
- Fail if RepoRoot is not a git work tree or BASE is not an ancestor of HEAD.

## Anti-patterns

- Using `HEAD~1` as BASE for a multi-commit task
- Truncating the diff "to save space"
- Running from the wrong worktree (main vs mission worktree)

## Host notes (Claude Code)

- Invoke the script through the **PowerShell** tool (it is PowerShell 7+, so `pwsh -File` and the backtick line continuations above work as written). The **Bash** tool is Git Bash and will not parse this syntax.
- After the script prints the path, hand that path to `review-task`. Do **not** call **Read** on the package yourself — that defeats the entire purpose of packaging it.
- The script takes every input as a parameter and hardcodes no paths, so it is safe to run against any worktree.
