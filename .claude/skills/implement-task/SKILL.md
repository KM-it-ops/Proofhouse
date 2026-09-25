---
name: implement-task
description: Implements one Proofhouse SDD task from a task brief with TDD, Proofhouse campaign invariants, and a fixed report contract. Use when dispatching or acting as the implementer for Proofhouse MISSION/SDD tasks (compiler core, closed-loop, contracts, OARs), run in a task worktree.
---

# Implement task

You implement **exactly one** SDD task. You do not review, package diffs, or start the next task.

## Startup (every invocation)

1. Read the **task brief** path given by the controller (single source of requirements).
2. Read **Global Constraints** from the plan file (section only — do not re-read the whole plan unless brief says to).
3. Confirm work directory is the authorized **worktree** (never edit `main` checkout for mission work).
4. If anything in the brief conflicts with invariants below — **stop** with `NEEDS_CONTEXT` or `BLOCKED`.

## Proofhouse invariants (non-negotiable)

- Offline default: no network, no credentials, no live providers on the certified path.
- Repair budgets exactly `{0,1,2}`; never weaken `accepted_objectives` / `security_constraints` (`EVR-SEC-0001`).
- Approved structured profiles only unless the brief explicitly authorizes a new profile: `structured_minimal_v0`, `structured_developer_v0`.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no benchmark claims; no Simple Mode UI semantics.
- Production CLI must never expose `force_*` / test hooks; quarantine behind `ClosedLoopTestHooks` or equivalent.
- Honesty: do not claim full Phase 4B exit, enterprise SAST, or adoption metrics unless the brief and evidence say so.
- Prefer `uv run python -m pytest` (install pytest into the env if needed); else `python -m pytest`.

## Execution protocol

1. Ask clarifying questions **before** coding if the brief is ambiguous.
2. **TDD** when the brief includes tests: write failing test → run (RED) → implement → run (GREEN). Record commands and relevant output in the report.
3. Run focused tests while iterating; run the brief's required suite once before commit.
4. Commit on the feature branch only (authorized for mission branches). **Do not push** unless the brief explicitly says so.
5. Self-review: completeness, YAGNI, naming, test honesty.
6. Write the **full** report to the report path; return only the short status block to the controller.

## Report file (required sections)

- What you implemented
- What you tested (commands + results)
- TDD Evidence when required: RED command/output reason; GREEN command/output
- Files changed
- Self-review findings
- Concerns / residual honesty gaps

## Controller return (≤15 lines)

- **Status:** `DONE` | `DONE_WITH_CONCERNS` | `BLOCKED` | `NEEDS_CONTEXT`
- Commits (short SHA + subject)
- One-line test summary
- Concerns if any
- Report file path

## Anti-patterns

- Do not re-implement prior tasks "to be helpful."
- Do not update maturity maps / OARs / README Status unless this task's brief lists those files.
- Do not paste the whole plan into the report.
- Do not invent enterprise or adoption claims.

## Host notes (Claude Code)

- Use the **Write/Edit** tools for file changes — edits made through shell heredocs or sandboxed subprocess tools may not persist.
- Use **Bash** or **PowerShell** for test runs and git; both are available and take their own syntax.
- On Windows, `python -m pytest` may need `PYTHONPATH=src` when the package is not installed into the active interpreter.
- Run tests with the worktree's own environment (`uv run ...`); a bare `python` outside it can miss runtime deps like `rfc8785`.
