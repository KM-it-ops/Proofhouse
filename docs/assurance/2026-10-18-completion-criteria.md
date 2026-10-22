# Assurance statement: completion criteria, 2026-10-18

| | |
|---|---|
| Scope | Pass/fail for each of the ten completion criteria in [product-scope.md](../product-scope.md), after units U0 to U4 (PRs 65 to 70) and the U5 final review |
| Code revision verified | `main` at `f939f957db2ce6bea2546beb2df374dcac3d8013`, plus the review fixes on branch `claude/u5-final-gate` (tests run at `d652b7fad8db19cef309fd87c4ee29f2210963d8`). This statement is added in a later commit that changes no code. |
| Package | `proofhouse` 0.8.0 (0.9.0 not cut yet) |
| Platform | Windows 11, CPython 3.14.6, uv; macOS and Linux through GitHub Actions |
| Maintainer | KM-it-ops (repository owner); audit done by an AI coding agent. Each status below is the agent's reading of the evidence, not a sign-off. |
| Independent review | A fresh full review of `f939f95` (record `review-f939f95.md`, kept with the owner's review records, outside this repository) found two wrong behaviours and four safeguards no test checked. All six are fixed or tested on `claude/u5-final-gate`. The one fix that touches key handling had a separate Opus security pass, which found no problem. **The fix commits have not had their own fresh review.** |

## Commands and results

| Command | Result |
|---|---|
| `uv run --frozen --extra test python -m pytest -q -p no:cacheprovider tests` at `f939f95` | **2132 passed, 46 skipped, 1 deselected** in 616.10s (the deselected test is the opt-in live test) |
| The same, at the fix branch | **2144 passed, 46 skipped, 1 deselected** in 286.33s (12 more than `main`: the new tests) |
| `uv run --frozen python scripts/generate_model_surfaces.py --check` | in sync (18 models) |
| `uv build` then `uvx twine check dist/*` | `proofhouse-0.8.0.tar.gz` and `proofhouse-0.8.0-py3-none-any.whl` built; both `PASSED` |
| GitHub CI on `main` at `f939f95` | success (run 39164750401) |
| `native-builds` workflow | web app, Windows, macOS, Linux, iOS and Android all green ([run 39161715167](https://github.com/KM-it-ops/Proofhouse/actions/runs/39161715167), same build code and data as `main`) |
| Safeguards turned off one at a time (`revert_check`, 15 safeguards) | 9 caught at `f939f95`; the other 6 are the review findings, now each caught by a test or deliberately changed (F2) |
| `gh issue list --state all` | no issues |

## Completion criteria

| # | Criterion (short) | Status | Evidence / gap |
|---|---|---|---|
| 1 | Required requirements reach the model or stop the run | met | `execute-openai --provider ID` runs a compiled artifact on any provider in the shipped list, an add-on or your own `providers.json`, always through the spend gate (U1, PR 68). A required capability the provider cannot carry stops the run before sending (`EXE-CAP-0001`); an ignored optional one is written into the prompt. Checked in `tests/compiler/test_run_on_any_provider.py` against the final request body. |
| 2 | Evaluation cannot silently ignore bad input | met | Unchanged since 2026-10-16: T03/T04 tests, `test_strict_json_inputs`, `test_required_coverage`, `test_rubric_strict_match`. A malformed provider `ignores` list is now refused under test (`test_a_bad_ignores_list_is_refused`). |
| 3 | Every outcome records what was tested | met | Unchanged: records hold provider, model, calls, rounds and `proofhouse_version`. |
| 4 | Kinds of evidence are visibly distinct | met | Unchanged: judge notes are "advice, not proof"; `evidence_classes`; `checks.json` kept apart from model output. |
| 5 | Review findings have regression tests; no open high-priority defect | met | Every finding of the `f939f95` review has a test that fails without its fix or safeguard. No open issues. |
| 6 | A fresh user completes the reference workflow | **needs Boss** | `test_reference_workflow::test_demo_command_passes` runs it automatically. An agent cannot stand in for a fresh user, and no fresh user has tried it. |
| 7 | A failed install or update keeps existing data | met | Unchanged: `tests/test_failed_update_keeps_data.py` and the T06 tests. |
| 8 | Model claims have sources or are labelled | met | `generate_model_surfaces.py --check` in sync; `test_t07_notes_provenance` passes. |
| 9 | The interface passes functional, keyboard, layout and error checks | met | The command line has functional and error-recovery tests. The dashboard now has browser checks on every pull request (U4, PR 67): keyboard reach with visible focus, no sideways scroll at 375 px, animations that stop under reduced motion, and the error state. Each must fail on a copy broken on purpose. |
| 10 | Release docs match the released revision | **not met** | CHANGELOG `Unreleased` and the master plan describe the current code. 0.9.0 is not cut, tagged or published, and the 0.8.0 GitHub release is missing too (Boss). |

## Gaps

- **Fix review:** the six fix commits on `claude/u5-final-gate` were checked by their own tests and, for the key-handling fix, one security pass; they have not had a fresh full review.
- **C6:** a fresh user still needs to try the reference workflow (Boss).
- **C10:** 0.9.0, PyPI and the GitHub releases for 0.8.0 and 0.9.0 wait on Boss.
- **App builds:** the native builds are proven with the fixed sample app. An app a model writes can still need setup the sample did not. Signed iOS device builds and signed Android release builds are not checked.
- **Goal picker:** the built-in rules pick correctly on 15 of 30 goals they never saw (accepted by the owner); with a model set, the model picks.
- **Not built yet (owner's correction, 2026-10-18):** anything new is learned, not refused. Today `make --kind <new kind>` refuses, the goal picker swaps a kind the model names for a built-in one, a forced unknown artifact class falls back to a prompt, and there is no `proofhouse models update`. Master plan units U6 to U8 build this.
- **Follow-up from the review, not a defect today:** `execute_on_provider` does not re-check the final address's host as `proofhouse run` does (safe today because the address is always the validated base URL plus `/chat/completions`).

## Exclusions

- No live provider call was made for this audit.
- No full-history secret scan, dependency vulnerability audit, or formal accessibility certification.
