# Lineage: AgentForge

AgentForge was a Node tool that wrote one agent rulebook (identity, routing, memory, telemetry and
automation, kept in five YAML files) into each coding assistant's own config files:
`CLAUDE.md` and hooks for Claude Code, `AGENTS.md` for Codex and generic agents, `.cursor/rules/*.mdc`
for Cursor, `GEMINI.md` for Gemini CLI, and `CONVENTIONS.md` for Aider. Its web playground,
AgentForge Studio, compiled an edited spec in the browser and previewed the files.

It was retired in October 2026 and Proofhouse is its successor. The code is frozen, unchanged, at
tag [`v0.3.1-final`](https://github.com/KM-it-ops/AgentForge/tree/v0.3.1-final) in the archived
[KM-it-ops/AgentForge](https://github.com/KM-it-ops/AgentForge) repository. The npm package
`@kmitops/agentforge` is deprecated, and the Studio site and the Pages demo are offline.

Nothing from AgentForge ships inside Proofhouse. This page keeps what it proved, so the work can
be picked up again without re-learning it.

## Where it would fit

Proofhouse's experimental `route` command (`proofhouse-compiler route`) sorts an objective into an
artifact class: skill, hook, subagent, harness, MCP and others. Writing host config files is the
natural next step after `route` picks one of those. That would be a **host config writer**, a
future Proofhouse part.

**Status: not scheduled.** It waits on the Proofhouse architecture redesign. Do not confuse it
with the existing compiler adapters in `src/proofhouse/compiler/adapters/`, which build model API
requests, not config files. The only per-host code in Proofhouse today is `install-skill --host`.

## Lessons worth reusing

Each lesson below links to its source in the frozen tag.

### 1. Run it twice; the second run must change nothing (idempotency round-trip)

Every writer was run twice into a fresh git sandbox. The second run had to meet three
conditions: exit 0, leave `git status --porcelain` empty, and report `"files_changed": 0` in its
JSON receipt. CI ran this on Ubuntu, Windows and macOS with Node 20 and 22. It caught real defects
that a single-run test passes.
Source: [`scripts/round-trip-test.sh`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/scripts/round-trip-test.sh).

### 2. Edit only a marked section of the user's file (managed blocks)

A writer must not overwrite a file the user also edits. AgentForge wrote its content between
`AGENTFORGE:BEGIN` and `AGENTFORGE:END` marker lines, and replaced only that span on later runs.
When the user's file could not be parsed (for example, broken JSON settings), it wrote a side
file (`settings.agentforge.json`) instead of touching theirs.
Source: the `AF_BLOCK_BEGIN` handling in
[`adapters/codex/emit.js`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/adapters/codex/emit.js)
and
[`adapters/aider/emit.js`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/adapters/aider/emit.js).

### 3. Build in a throwaway folder and always clean up

Studio compiled each request in its own fresh temp folder (`agentforge-studio-<uuid>`) and ran
the writer as a child process. It capped output at 16 MB, kept only the last lines of stderr as
the error, and deleted the folder in `finally`. It never wrote into a real home folder.
Source: [`studio/lib/compile.ts`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/studio/lib/compile.ts).

### 4. Point the tool at another input folder through an environment variable

Writers read their spec from `AGENTFORGE_SPEC_DIR` when it was set, and otherwise from the repo
copy. That one variable let tests and the web playground feed edited input without touching the
canonical files.
Source: [`docs/solutions/2026-06-21-studio-agentforge-spec-dir.md`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/docs/solutions/2026-06-21-studio-agentforge-spec-dir.md).

### 5. Validate web input strictly, and cap its size

Studio's API used strict Zod schemas that reject unknown fields, a 512 KB body cap (413 when
exceeded, 400 on bad JSON) and a per-IP rate limit. The rate limit was held in memory, so it only
applied per server instance. That is weak on serverless hosting and would need shared storage
there.
Source: [`studio/lib/`](https://github.com/KM-it-ops/AgentForge/tree/v0.3.1-final/studio/lib).

### 6. Web build gotchas, if Proofhouse ever gets a Next.js surface

- **Zod 4 broke the Next.js 15 (Turbopack) build** of API routes. Pinning Zod 3 fixed it.
  Source: [`2026-06-21-studio-zod-v3-pin.md`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/docs/solutions/2026-06-21-studio-zod-v3-pin.md).
- **Deploy a monorepo from its root.** Uploading only the app subfolder to Vercel broke every
  route that read sibling folders.
  Source: [`2026-06-21-studio-vercel-monorepo-deploy.md`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/docs/solutions/2026-06-21-studio-vercel-monorepo-deploy.md).

### 7. Keep personal paths out of a public spec with a check

A CI script failed the build when the public spec contained personal paths. The rule had a check
behind it, so it held.
Source: [`scripts/check-spec-public.sh`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/scripts/check-spec-public.sh).

## The writer contract (summary of `spec/SPEC.md`)

This is the starting spec for a future host config writer. In full:
[`spec/SPEC.md`](https://github.com/KM-it-ops/AgentForge/blob/v0.3.1-final/spec/SPEC.md).

A writer MUST:

- read every spec file; there are no optional reads
- write the host's own identity file
- create the memory folders
- wire telemetry to the host's hooks, or state the gap honestly in its README
- install the scheduled clean-up
- copy the shared layer
- change nothing on a second run
- leave a git checkpoint so the install can be undone
- refuse an unknown `schema_version`

A writer MUST NOT:

- touch files outside its host's own folder
- import another writer
- hard-code values that belong in the spec
- quietly drop a feature the host can't support

Per-host values were filled from a table of variables:

| Variable | Example (Claude Code) | Example (Codex) |
| --- | --- | --- |
| `{agent_home}` | `~/.claude/` | `~/.codex/` |
| `{identity_file}` | `CLAUDE.md` | `AGENTS.md` |
| `{skills_root}` | `~/.claude/skills/` | `~/.codex/skills/` |

## Skills it carried

- **`write-a-skill`** is superseded by the maintainer's current skill-writing rules. Nothing to
  carry over.
- **`agentic-prompt-architect`** turned a project idea into a governing spec for a coding agent,
  using fill-in templates. The templates are not carried over. Three of its rules are worth
  keeping for the redesign, as a possible "project spec" artifact class:
  - Every spec states its failure conditions, the things that mean "not done".
  - The stack is fixed up front.
  - The spec's size scales with the job.
