# Changelog

## 0.6.0 - 2026-10-12

`execute-openai` now refuses before sending when the worst-case cost is over your ceiling.

### Upgrade notes (read first)

- **(breaking)** `execute-openai` refuses before sending when the worst-case estimate of its cost is over `--max-cost-usd` (`PHC-COST-0001`), **and refuses every model that has no entry in the shipped price table** (`PHC-COST-0002`). The price table ships with no entries: no price has been read from a provider's official page and cited yet. **Until a price entry exists for the model you pass, `execute-openai` refuses to send.** Both refusals exit 7, like every other `execute-openai` refusal, and send nothing.
- `--json` output of `execute-openai`: `admission.cost_ceiling` now states the gate's decision (`enforcement: refused_pre_send_when_worst_case_over_ceiling`, `decision`, `worst_case_usd`, bounds, the price entry used); `pricing_source` and `input_token_estimate` are gone. A sent call adds `cost`.
- Case, run and export files are unchanged. A case touched by this version still opens in 0.5.0.

### Added

- The spend gate (`spend.send_within_ceiling`): the only way the live path sends. It works out the worst case from the exact request bytes: input tokens at most the UTF-8 bytes of the body as sent plus 1024 (on the stated assumption of at most one token per byte), output tokens taken to be at most `--max-output-tokens` (on the stated assumption that this cap covers every billed output token, reasoning included), at table prices, in exact decimals. An amount that would need rounding, an unreadable table, or a request above the size its price applies to is refused (`PHC-COST-0003`). The bytes counted are the bytes sent; the model and output cap are read from them, and a request with a field or content the estimate does not cover (such as image or audio parts), or a ceiling outside 0.000000000001 to under 10000000000000, is refused (`PHC-COST-0003`). No flag, setting or environment variable skips it. See [decision 0006](docs/decisions/0006-refuse-before-sending-over-the-ceiling.md).
- A versioned price table shipped in the package (`proofhouse.price_table/v1`, `data/price_table.json`), pinned by a test to its content. Each entry cites the provider's official pricing page and the date it was read. A model matches only by its exact id.
- `execute-openai` results carry `cost`: the token counts the provider reports and the wall time are measured; `usd` is estimated from those tokens at table prices, never measured, and is not your bill. A figure nobody knows is `unknown`, never `0`. When the provider reports more tokens than the gate's bound, the result adds `PHC-COST-0004` and one line on stderr; the output is still returned.
- An architecture test that fails the build if a module other than the live path can reach the network or its raw sender, or if the one send step is used other than through the gate; and two new mutations in `scripts/mutation_check.py`.

### Changed

- `execute-openai` posts the exact bytes the gate counted, instead of letting the HTTP client serialise the body again. The JSON content is the same.
- CI checks that the price table ships in the wheel and loads.

## 0.5.0 - 2026-10-12

The spine slice: prompts and skills go from objective to export through the same commands, the same case, the same pass rule and the same part contract.

### Upgrade notes (read first)

- **(breaking, one-way)** Cases move to `proofhouse.optimize.case/v1`. A 0.4.x case still opens, reports the same results and takes new versions; its revision and run files are never rewritten. The first command that writes its `case.json` copies the old file to `case.v0-backup.json` (never overwritten) and upgrades it. **An upgraded case no longer opens in 0.4.x**, which refuses a schema it does not know. Keep the backup, or an export made with 0.4.x, if you need to go back. Read-only commands never upgrade a case. Export bundles written by 0.4.x still import.
- **(breaking)** One command, `proofhouse`. Both console scripts now run the same command tree. `proofhouse-compiler` still works and prints a one-line notice on stderr (`--json` output on stdout is unchanged).
- **(breaking)** The eval harness moved under `proofhouse eval`: `eval validate --dataset`, `eval report`, `eval loadouts`, `eval compile-loadout`, `eval generate`. The old top-level forms are not forwarded; each exits 2 with one line naming the new form. `proofhouse validate` without `--dataset` is IR validation, as `proofhouse-compiler validate` was. `scan` stays top-level.
- `proofhouse case` carries every `optimize` subcommand with the same names and flags. `proofhouse optimize ...` still works for 0.5 and prints a notice; it will be removed after 0.5. JSON `command` values (`"optimize new"`, ...) are unchanged.
- Run records are `proofhouse.optimize.run/v2`; `run/v1` files still read.

### Added

- `proofhouse case new --kind skill` opens a skill case; `case record --skill-folder DIR` records a skill folder (`SKILL.md` at its root) as a version. Kinds are `prompt.text@1` (digest = the old `prompt_sha256`) and `agent.skill@1` (digest = RFC 8785 + SHA-256 over a sorted per-file manifest of paths and bytes; empty folders and permissions such as the execute bit are not part of it, and `install-skill` does not copy them); any other kind is refused (`PHC-KIND-0001`).
- `proofhouse parts` lists every registered part with role, kinds, status and conformance suite version (`--json` for full descriptors). `adapters` keeps its output (request builders only).
- Skill checker part and `case criteria add --skill-check install-roundtrip`: frontmatter, then an install round trip into a temporary skills folder (write, read back, reinstall changes nothing, uninstall restores the prior folder exactly). It does not test behaviour in real hosts, and the report says no independent pass ran.
- `install-skill --bundle` takes any skill, as a zip (`<name>/...`) or a folder. The name comes from validated `SKILL.md` frontmatter. With no bundle it installs Proofhouse's own skill exactly as before.
- `proofhouse uninstall-skill NAME` removes only a skill `install-skill` recorded installing and restores what that install replaced, only if its backup still holds exactly that; it refuses a folder that changed since install unless `--force` (then backs it up first, verifies that copy, and refuses a folder that holds a link or junction, which the copy would follow), and removes a link, never what it points at.
- `proofhouse "<objective>"` (the overseer) now acts on its route decision: a routed `prompt` or `skill` opens a case through the same function as `case new` (in `./case-<words>`, or `--case DIR`; `--model NAME`), and the case records the class, rationale and whether it was forced. Every other class opens nothing and is appended as "no part yet" to `PROOFHOUSE_HOME/demand/no-part-yet.jsonl`. `nothing_new` and `one_prompt` are unchanged. Stdout is still the route decision; what the overseer did is one line on stderr. `route()` itself is unchanged.
- Run records carry `part` and `cost`. Nothing measures cost yet, so every figure is `unknown`, never `0`; `usd` is never filled. The report sums cost per version, and a sum that includes an unknown is unknown. A figure must be finite (`NaN` and `Infinity` are refused). A run's entry in `case.json` must be listed once and match its run file (part, cost, revision and every other field it lists); import, `case output list` and `case report` check every entry, and any command that loads a run checks that run, refusing a mismatch (exit 2) instead of showing its figures or failing with an internal error.
- A report with a skill check names, below the overall result, the part that produced the evidence (`skill-checker`), that part's own status and what it did not measure.

### Changed

- **(breaking)** `proofhouse proof` no longer reports `SHIP` when no review pass ran. With no pass wired to the command it reports `UNJUDGED` with `passes: 0` and exits 3. The real-pass rules are unchanged.
- **(breaking)** `install-skill --force` refuses to replace a skill folder that is, or holds, a link or junction (exit 2), as 0.4.2 already does; 0.4.1 backed up what the link pointed at and replaced the link, so an uninstall could not put the link back. Remove or replace the link yourself, then install. This is checked again right before the backup copy, a backup that came out holding a link is refused, and without `--force` a skill folder that appears while `install-skill` runs is refused (exit 2).
- A backup that fails or does not match is removed again (never one another run left at the same path), and anything that could not be removed is named in the error. If a failed install or uninstall cannot put its install record back, the error says `record not restored` and names the record.
- Reading a skill folder refuses one whose folder, or a folder inside it, is replaced while it is being read (`PHC-SKILL-0003`).
- Skill file names that are not portable to every OS (Windows reserved names such as `CON`, `nul.txt` or `CONIN$`, a trailing dot or space, characters Windows forbids) are refused on every OS (`PHC-SKILL-0009`), in skill versions and in `install-skill` input.
- README, docs and CI use `proofhouse`; CI runs `proofhouse demo` from the built wheel outside the checkout.

## 0.4.2 - 2026-10-12

### Fixed

- `install-skill --force` refuses to replace a skill folder that is, or holds, a symbolic link or a Windows
  directory junction. It exits 2 and changes nothing; remove or replace the link, then install again. Before
  this fix, the backup copy under `PROOFHOUSE_HOME/skill-backups/` followed such a link and copied what it
  pointed to. The backup copy now never follows a link.
- A skill folder that is a link to a folder that no longer exists is refused the same way (exit 2), instead of
  failing with "cannot place the new skill" (exit 7).
- A backup copy that fails or is refused is removed from `PROOFHOUSE_HOME/skill-backups/`; if it cannot be
  removed, the error names where it is.
- Removing a copy never changes the permissions of a file that a link in it points to.

## 0.4.1 - 2026-10-08

### Added

- `proofhouse-compiler demo` runs the reference advisory workflow from files shipped in the package. It replays recorded outputs, calls no model, and does not need a git clone.

### Changed

- Package metadata for a PyPI page: SPDX `MIT` license, project links, and classifiers. The README leads with `uv tool install proofhouse` / `pip install proofhouse`.
- README demo is a 42-second walk through the standalone app (`apps/proofhouse.jsx`) on the Grok 4.7 Facebook run: objective, loop, answers, compiled prompt. Remotion animates the terminal, cursor, particles, and spinning light. Hyperframes runs the same screens as sub-compositions. The soundtrack is original and synthesized.
- The manual publish workflow can upload to the real PyPI index when the run chooses `pypi`. The default choice remains TestPyPI.

## 0.4.0 - 2026-10-04

### Added

- `proofhouse-compiler install-skill --host claude` installs the skill into
  Claude Code's `~/.claude/skills`; `--host cursor` installs into `~/.cursor/skills`.
- `proofhouse scan [PATH]` reads a project folder and reports its language,
  frameworks, package manager, test tools, CI, agent instruction files, layout
  and a short README excerpt, so the skill can pre-fill the environment questions
  and ask fewer. It is read-only, stays inside the folder (never follows symlinks
  or junctions, refuses a drive root or the home folder), and never reads dotenv
  or key files. The same file ships in the skill as `scripts/scan_project.py`,
  and a test fails if the two copies differ.
- `skills/proofhouse/INSTALL.md`: short instructions written for an AI agent, so a user can
  hand the skill folder to Claude Code, Cursor or another agent and say "install this".

### Changed

- **(breaking)** `install-skill` no longer defaults to Cursor. With no `--host` and no `--dest` in a terminal,
  it asks which agent: every known agent (marked when its folder exists) or another agent you
  name with its skills folder. Run by a program, it installs for the one agent whose folder
  (`~/.cursor` or `~/.claude`) exists; with none or both it exits 2 and lists the choices.
  `--json` output now includes `host` and `agent`.
- **(breaking)** The Python `install()` and `default_dest()` functions no longer assume Cursor either: they
  need an agent or a destination folder, and refuse with exit code 2 otherwise.

## 0.3.0 - Evidence Integrity

### Removed

- Removed the deprecated pre-Proofhouse console-script aliases and live-test
  environment fallback at the documented 0.3.0 boundary.

### Changed

- Completed the Proofhouse identity migration across active wire media types,
  semantic-context keys, benchmark and diagnostic identifiers, generated
  TypeScript names, schema filenames, dashboard metadata, CI, docs, and tests.
- Bumped the package to 0.3.0. Frozen v0.5 contract fixtures, requirements
  contract evidence, the original dashboard backup, and changelog history keep
  their historical names intentionally.
- README leads with one story, the offline prompt-revision workflow, and moves
  experimental and prototype parts into their own section. It now states the CI
  matrix (Linux, macOS, Windows; Python 3.11 to 3.14) and shows the CI badge.

### Evidence integrity (adversarial review of 78e512c, findings F01-F12)

Behavior changes a user will notice are marked **(breaking)**. See
[docs/decisions/](docs/decisions/) for the reasoning and
[docs/assurance/](docs/assurance/) for what was verified.

#### Fixed

- **Live requests keep every mandatory field (F01).** `execute-openai` renders
  requirements (id, mandatory flag, acceptance), success/failure criteria,
  uncertainty and evidence policies, workflow, autonomy and assumptions into
  the system message from an explicit per-field map; fields a single request
  cannot honor refuse with `EXE-SEM-0001` before sending. The envelope records
  the mapping and the system-message digest.
- **(breaking)** **Duplicate evaluation ids are rejected (F02).** `case_id` and
  `criterion_id` duplicates, duplicate JSON keys inside a dataset row or rubric,
  malformed rows and non-finite values raise with the line number; scores use
  structured keys; aggregation is order-independent. A rubric must name
  `rubric_id` and `version` as non-empty strings.
- **(breaking)** **Coverage and binding (F03).** A mandatory requirement with no
  product-eval case is `BLOCKED` (`EVR-COV-0001`); rows declaring another
  candidate digest are `BLOCKED` (`EVR-BND-0001`). Results carry dataset/rubric
  digests and per-case results. `closed-loop` withholds a candidate PASS unless
  every row declares the candidate's `candidate_digest`: unbound or partially
  bound rows give `BLOCKED` (`EVR-BND-0002`, exit 5), which includes every
  dataset written before this change. Standalone `evaluate-product` still
  PASSes them; a declared digest is caller-supplied, not authenticated.
- **(breaking)** **Edited revisions and stale verdicts (F04).** Revisions are
  digest-checked on load; verdicts bind to revision and criterion digests and
  go stale when either changes; check runs are immutable files; `case.json`
  writes are atomic; revision files are never overwritten. Verdicts recorded
  before this change carry no digests and now show as stale (`UNJUDGED`);
  record them again with `optimize verdict`.
- **(breaking)** **Model-note provenance (F05).** Notes files are
  `user_supplied`, undated and unverified (they were `researched`, verified
  today). Every profile carries an `evidence` label; unsourced profiles say
  `unverified`; `models list` says "reviewed", not "verified". The Opus 5
  note no longer advises stripping verification, and every compile prompt says
  efficiency advice never removes a required gate.
- **Stage identity and repair (F06).** Closed-loop evidence reports compile,
  deterministic evaluation, product evaluation and repair as separate stages
  with true evaluator identities; a failing product evaluation stops with
  `EVR-REP-0005` and a terminal reason instead of a silent zero-attempt FAIL.
- **Malformed input (F07).** Closed-loop intake rejects non-object roots,
  wrong nested types, non-boolean `network_allowed`, non-finite numbers,
  duplicate keys/ids and excessive nesting with `EVR-INP-*`/`EVR-DUP-0001`
  instead of raising or passing.
- **Transactional skill install (F08).** A failed forced install leaves the
  previous skill unchanged; replacements keep a backup under
  `PROOFHOUSE_HOME/skill-backups/`; unsafe archive paths and oversized
  bundles are refused.
- **Budget inputs (F09).** `NaN`/`Infinity`/non-positive ceilings are rejected
  without raising; the envelope states the cost ceiling is declared only.
  Library callers must pass `max_cost_usd` as a decimal string (as the CLI
  does) and `max_output_tokens` as a positive `int` (not `bool`).
- **Artifact responses (F10).** The JSX artifact schema-validates every model
  response, excludes answers to hidden questions, and adds timeout/cancel,
  including for the unfamiliar-model research call (a cancel stops the run
  rather than falling back to generic notes).
- **Revision context (F11).** Revise packets (CLI and artifact) carry the
  clarification answers and accepted constraints. The artifact describes the
  answers as still in force unless the new feedback changes one, not as
  overriding it.
- **Public trust docs (F12).** SECURITY.md names a private reporting route;
  CONTRIBUTING installs the test extra and documents a public decision
  process; CLI help no longer cites unpublished internal ids.
- `proofhouse.__version__` reads the installed version (it said 0.1.1).

#### Added

- `optimize constraints add|list|propose|accept|reject|link`: a constraint
  ledger outside the prompt, seeded from clarification answers.
- `optimize output add|list`: record imported outputs bound to a revision.
- `criteria add --target output`, `verdict --run`: checks on recorded outputs.
- **(breaking)** `optimize check` passes only when every accepted constraint
  is satisfied by linked criteria ([decision 0002](docs/decisions/0002-what-pass-means.md)).
- `optimize compare`, `optimize report`, `optimize export|import`.
- `examples/reference-advisory/` and `scripts/reference_workflow.py`, run by
  the test suite and by the wheel-install CI job.
- Docs: product scope, architecture, surfaces and contracts, evidence format,
  reference workflow, troubleshooting, decision records, assurance statement.

### Added

- `docs/assets/proofhouse-demo.mp4` (23 s) and its poster, linked from the top
  of the README. The terminal lines in it are the reference workflow's real
  `optimize check` output (case path shortened); the soundtrack is original
  and synthesized.
- `[test]` extra declaring pytest, locked in `uv.lock`, so `uv sync --extra test`
  and `pip install -e ".[test]"` establish the test prerequisite on a clean clone.
- `examples/ir_minimal.json` — static, human-readable copy of the canonical
  minimal IR (`tests/compiler/test_examples_ir_minimal.py` pins it to the
  fixture factory) for `validate` / `compile` demos without a Python pipeline.
- README and `docs/quickstart.md` now separate the two console scripts
  (`proofhouse-compiler`, `proofhouse`), lead with tested uv commands, and give
  the Cursor skill install command (`python -m zipfile -e … ~/.cursor/skills`).
  `docs/showcase.md` is an executable 5-minute offline script.
- `proofhouse-compiler optimize new|compile|record|revise|status|criteria|verdict|check`:
  offline case workflow that renders the framework's clarify / compile / self-heal
  prompts as packets for the user's own host agent, records revisions, and checks
  them against user-declared criteria. No provider call, no scoring.
- `proofhouse-compiler models list|show|remember|forget`: model-note provenance
  (`builtin|cached|researched|fallback`), canonical ids, aliases, `verified_at`,
  stale warnings, and a local cache under `~/.proofhouse/` (`PROOFHOUSE_HOME`).
  The CLI never researches online.
- `proofhouse-compiler install-skill`: extracts the bundled `proofhouse.skill` into
  `~/.cursor/skills` and verifies `name: proofhouse`. The bundle, the framework
  JSON, and the model registry ship as package data.
- One reviewed registry (`src/proofhouse/optimize/data/model_registry.json`) now
  generates the framework `modelNotes` + `modelRegistry`, the framework Markdown
  table, the JSX `MODEL_NOTES`, the skill model paragraph, and the README
  supported-models table (`scripts/generate_model_surfaces.py --check` is a test).
- README "Surfaces" matrix scopes auto-research to the skill and artifact.

### Changed

- CI test matrix now includes Python 3.13 and 3.14 on Ubuntu, Windows, and
  macOS. Typescript-drift and wheel-install stay on 3.11.
- The reference model for live runs is `gpt-5.6-luna`. `execute-openai` still
  requires `--model` at call time; envelopes record that the reference model
  has been chosen (`q1_unpicked: false`). Cost ceilings remain recorded, not
  enforced. Live stays opt-in and not CERTIFIED.
- Live OpenAI payload uses `max_completion_tokens` (the reference model
  `gpt-5.6-luna` rejects `max_tokens`).
- `execute-openai` reports `error` / `EXE-HTTP-0001` when the provider HTTP
  status is not 2xx (a completed send is not a successful completion).

## 0.2.1 - Skill Bundle Rebuild

### Fixed

- `skills/proofhouse/proofhouse.skill` was a hand-packed artifact last built
  2026-07-04. It shipped framework **v1.2** while the repository was on v1.3, so
  its model tables still listed superseded entries. Rebuilt from the source
  directory; the bundle now carries v1.3 and its entries are named `proofhouse/`.

### Added

- `scripts/build_skill_bundle.py` builds the bundle reproducibly — fixed
  timestamps and attributes, entry order sorted by name, text normalised to LF,
  and stored uncompressed, so the output does not depend on the platform or the
  Python version that packed it.
- `tests/test_skill_bundle.py` fails if the committed bundle and its source
  directory disagree, which is what went unnoticed for two months.


## 0.2.0 - Proofhouse Rename

### Changed

- Renamed the project from PromptRig to Proofhouse across the package, console
  scripts, schema `$id` namespaces, environment variables, generated TypeScript,
  brand-named files, and documentation.
- Python package `promptrig` is now `proofhouse` (`src/proofhouse/`).
- Schema `$id` namespaces moved to `proofhouse.dev` and `proofhouse.local`.
  `proofhouse.local` remains a deliberately non-resolving namespace.

### Added

- Console scripts `proofhouse` and `proofhouse-compiler`.
- Test-only environment names `PROOFHOUSE_LIVE*` (legacy fallback
  `PROMPTRIG_LIVE*`) are read by
  `tests/compiler/live/test_live_openai_q1_gate.py` under pytest marker `live`
  (deselected by default). `execution.py` does not read them. Removable at
  0.3.0 with the aliases.

### Deprecated

- Console scripts `promptrig` and `promptrig-compiler` remain as aliases for one
  minor version and are removable at 0.3.0.

### Unchanged

- The frozen contract schema `PROMPTRIG_IR_V0_1.schema.json` keeps its filename
  and its `$id`; it is a historical artifact and its identity is part of the record.
- Wire identifiers, media types, and canonical digest inputs are untouched. The
  three pinned `ir_sha256` digests are byte-identical across the rename.
- Maturity is unchanged: the requirements compiler remains `PARTIAL`.


## 0.1.1 - Showcase and Local Skill Adoption

### Added

- Public-facing README with quickstart, feature map, and repo navigation.
- Quickstart, showcase, Custom GPT setup, security, and contribution docs.
- Prompt audit example for before/after positioning.
- GitHub Actions CI workflow for tests and dataset validation.
- Source-controlled Codex skill package under `skills/promptrig/`.

### Changed

- Rubric scoring now accepts only integer values from 1 to 5.

## 0.1.0 - Initial PromptRig Scaffold

### Added

- PromptRig project identity
- Custom GPT identity: PromptOps Architect powered by PromptRig
- Core prompt
- Mode prompts for Default, Audit, Meta-Prompting, Agentic, and Evaluator modes
- Modular prompt components
- Reference policy
- Prompt quality rubrics
- JSONL test datasets
- Offline Python eval harness
- Basic tests

### Notes

This scaffold is intentionally lightweight. Provider-specific adapters can be added later after the core prompt architecture and eval datasets stabilize.
