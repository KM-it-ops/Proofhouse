# Assurance statement: completion criteria, 2026-10-16

| | |
|---|---|
| Scope | Pass/fail for each of the ten completion criteria in [product-scope.md](../product-scope.md), for the 0.8.0 release candidate |
| Code revision verified | `33e9b25ce6afea96c70b05fef6257b29305ba57f` on branch `finish/2026-10-16` (base `3663a9d`). This statement was updated in a later commit that changes no code. |
| Package | `proofhouse` 0.8.0 |
| Platform | Windows 11, CPython 3.14.6, uv |
| Maintainer | KM-it-ops (repository owner); audit done by an AI coding agent. Each status below is the agent's reading of the evidence, not a sign-off. |
| Independent review | The two fixes made during this audit (safe writes on failed install or update, and the version in every run record) each had an independent review pass, and every finding was fixed or is listed under Gaps. An independent full review of `ba43b47` found four issues; the two code fixes (`4ad6cbc`, `33e9b25`) each had two further independent security reviews, and every finding was fixed or is listed under Gaps. **The final head has not had a fresh full review.** |

## Commands and results

| Command | Result |
|---|---|
| `uv run --frozen --extra test python -m pytest -q -p no:cacheprovider tests` | **1937 passed, 44 skipped, 1 deselected** in 421.38s (the deselected test is the opt-in live test) |
| `uv build` then `uvx twine check dist/*` | `proofhouse-0.8.0.tar.gz` and `proofhouse-0.8.0-py3-none-any.whl` built; both `PASSED` |
| `uv run --frozen python scripts/generate_model_surfaces.py --check` | in sync (18 models) |
| `gh issue list --state all` | no issues |

## Completion criteria

| # | Criterion (short) | Status | Evidence / gap |
|---|---|---|---|
| 1 | Required requirements reach the model or stop the run | **partly met** | Met for the only path that runs a compiled artifact against a model, `execute-openai`: `tests/compiler/test_t02_runtime_semantics.py` checks the final request body (for example `test_probe_sentinels_reach_the_transport_body`). The other provider adapters only describe capabilities and have no run path. This conflicts with "any provider", and it is not a small fix. |
| 2 | Evaluation cannot silently ignore bad input | met | T03/T04 tests, `test_strict_json_inputs`, `test_required_coverage`, `test_rubric_strict_match`. |
| 3 | Every outcome records what was tested | met | Records hold provider, model, calls and rounds. Since this audit, every make, studio, compare, loop, launch and train record also names the Proofhouse version that made it (`proofhouse_version`), checked in six test files. |
| 4 | Kinds of evidence are visibly distinct | met | The judge's note is labelled "advice, not proof" (`test_make_engine::test_a_prompt_is_written_tried_judged_and_improved_until_the_target`). Closed-loop runs list `evidence_classes` (`test_t03_eval_integrity::test_default_closed_loop_records_stages_without_product`). `checks.json` is kept separate from model output. |
| 5 | Review findings have regression tests; no open high-priority defect | met for review findings | Each review fix has a test. `gh issue list --state all` shows no open issues. Not met in full until the combined head is independently reviewed. |
| 6 | A fresh user completes the reference workflow | **needs Boss** | `test_reference_workflow::test_demo_command_passes` runs it automatically. An agent cannot stand in for a fresh user, and no fresh user has tried it. |
| 7 | A failed install or update keeps existing data | met | `install-skill` (T06 tests). Since this audit, provider, media and train settings, tool installs (agent, rule, MCP) and add-on packs are written safely: `tests/test_failed_update_keeps_data.py` (17 tests) forces the write to fail and checks that the old files are unchanged and nothing half-written is left. Each write uses its own temporary file, so two runs saving the same file at once do not collide (`test_two_writers_never_share_a_temporary_file`). |
| 8 | Model claims have sources or are labelled | met | `generate_model_surfaces.py --check` is in sync. `test_t07_notes_provenance` passes. |
| 9 | The interface passes functional, keyboard, layout and error checks | **partly met** | The supported interface is the command line, which has functional and error-recovery tests. No browser keyboard, responsive-layout or reduced-motion test was run on the web pieces. |
| 10 | Release docs match the released revision | **partly met** | README, quickstart, showcase, the skill, CHANGELOG and the 0.8.0 release notes all say 0.8.0 and describe the current commands. Not met until 0.8.0 is tagged and published from this revision. The prototype images in `docs/assets/` are not referenced as product screenshots. |

## Gaps

- **C1:** only the OpenAI-compatible path runs compiled artifacts. Other providers need their own run path before the claim holds for "any provider".
- **C5:** the fixes from the full review of `ba43b47` were reviewed on their own; the final head has not had a fresh full review.
- **App builds:** the iOS build has no output path to check, so any successful exit passes it (to check on a Mac). A file system with coarse timestamps can make a real rebuild of output that already existed look unchanged, which fails the build.
- **C6:** a fresh user still needs to try the reference workflow (Boss).
- **C9:** no browser keyboard, layout or reduced-motion checks.
- **C10:** the release is not tagged or published yet (Boss).

## Exclusions

- No live provider call was made for this audit.
- The Windows, macOS, Linux, iOS and Android app builds have not been run end to end on real machines. The release notes mark them "to check".
- No full-history secret scan, dependency vulnerability audit, or formal accessibility certification.
- CI for the latest commits has not run, because they are not pushed.
