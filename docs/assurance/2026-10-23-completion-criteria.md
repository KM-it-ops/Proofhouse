# Assurance statement: completion criteria, 2026-10-23

| | |
|---|---|
| Scope | Pass/fail for each of the ten completion criteria in [product-scope.md](../product-scope.md), after the U5 fixes (PRs 71, 76), learned kinds and `models update` (U6, U7, PR 72), the install-path fix (PR 73) and learning the other lists (U8, PR 77) |
| Code revision verified | `main` at `38ce5f7957f871d95ae74c7f696c93c9cf1fcdc7` (PR 77 squash-merged; its last commit `9a3ae05` passed CI). This statement is added in the 0.9.0 release commit, which changes only the version number and documents. |
| Package | `proofhouse` 0.9.0: built and checked; tagged `v0.9.0` and released on GitHub 2026-10-25; not published to PyPI (held) |
| Platform | Windows 11, CPython 3.14.6, uv; macOS and Linux through GitHub Actions |
| Maintainer | KM-it-ops (repository owner); audit done by an AI coding agent. Each status below is the agent's reading of the evidence, not a sign-off. |
| Independent review | No second full review of the whole code was run. Instead each change was checked by a tool from a different company than the one that wrote it, with a separate Opus security pass on anything that handles keys or model-written entries. The U5 fix commits: Codex, no problems (PR 76). U6 and U7: a cross-check and a security review; each safeguard's test fails with that safeguard turned off (PR 72). U8: built by Cursor, fixed in three rounds by Cursor, Codex and Cursor; each round checked by a different tool (agy, Codex, a Claude Opus security pass, Cursor), and the last re-check by agy on Opus found nothing and showed each fix's test fails without its fix. CI then found one gap on Linux and macOS (a Windows drive path counted as inside the home folder), fixed in `9a3ae05`. |

## Commands and results

| Command | Result |
|---|---|
| `uv run --frozen --extra test python -m pytest -q -p no:cacheprovider tests` (U8 round-3 fix run, Windows) | **2263 passed, 46 skipped** |
| GitHub CI on PR 77 at `9a3ae05` | success, all 15 checks (run 39973470423) |
| `uv run --frozen python scripts/generate_model_surfaces.py --check` | in sync (27 models) |
| `uv build` then `uvx twine check dist/*` | `proofhouse-0.9.0.tar.gz` and `proofhouse-0.9.0-py3-none-any.whl` built; both `PASSED` |
| `native-builds` workflow | last green run [39161715167](https://github.com/KM-it-ops/Proofhouse/actions/runs/39161715167); not re-run for this statement |
| `gh issue list --state open` | no open issues |

## Completion criteria

| # | Criterion (short) | Status | Evidence / gap |
|---|---|---|---|
| 1 | Required requirements reach the model or stop the run | met | Unchanged since 2026-10-18 (U1, PR 68). `execute_on_provider` now also checks the final address's host just before the key is attached. |
| 2 | Evaluation cannot silently ignore bad input | met | Unchanged since 2026-10-18. Learned entries are checked too: size, depth and file-type limits, and deep nesting gives a plain error instead of a crash. |
| 3 | Every outcome records what was tested | met | Unchanged. Learned kinds and learned services record their source and date. |
| 4 | Kinds of evidence are visibly distinct | met | Unchanged. Notes a model picks out of a release page are marked `from_page_unreviewed` and kept out of prompts until reviewed with `models remember`. |
| 5 | Review findings have regression tests; no open high-priority defect | met | Every finding from the U5, U6/U7 and U8 checks has a test that fails without its fix. No open issues. |
| 6 | A fresh user completes the reference workflow | **needs Boss** | `test_reference_workflow::test_demo_command_passes` runs it automatically. An agent cannot stand in for a fresh user, and no fresh user has tried it. |
| 7 | A failed install or update keeps existing data | met | Unchanged: `tests/test_failed_update_keeps_data.py` and the T06 tests. Install paths are now compared after `..` is folded out (PR 73). |
| 8 | Model claims have sources or are labelled | met | `generate_model_surfaces.py --check` in sync (27 models); the built-in list was checked against official pages on 2026-10-18; `models update` cites the page each new model came from. |
| 9 | The interface passes functional, keyboard, layout and error checks | met | Unchanged since 2026-10-18 (U4, PR 67). |
| 10 | Release docs match the released revision | **not met** | CHANGELOG `0.9.0`, the README and the master plan describe this revision, and the 0.9.0 package is built and checked. It was tagged `v0.9.0` and the GitHub releases for 0.8.0 and 0.9.0 were created on 2026-10-25. It is not published to PyPI (held by Boss), so this stays not met. |

## Gaps

- **C6:** a fresh user still needs to try the reference workflow (Boss).
- **C10:** PyPI publishing waits on Boss. The 0.9.0 tag and the GitHub releases for 0.8.0 and 0.9.0 were done 2026-10-25.
- **Live checks:** learned kinds, learned services (U8) and `models update` are tested offline with recorded answers. None has run against a real provider yet.
- **App builds:** unchanged since 2026-10-18. The native builds are proven with the fixed sample app; signed store builds are not checked.
- **Goal picker:** unchanged since 2026-10-18 (15 of 30 unseen goals with built-in rules; with a model set, the model picks).

## Exclusions

- No live provider call was made for this audit.
- No second full review of the whole code; per-change cross-checks and Opus security passes stood in for it.
- No full-history secret scan, dependency vulnerability audit, or formal accessibility certification.
