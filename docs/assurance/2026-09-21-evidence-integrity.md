# Assurance statement: evidence integrity, 2026-09-21

| | |
|---|---|
| Scope | Fixes for adversarial review findings F01–F12 of `78e512c` and the local evidence workflow (plan work packages T01–T15; T16 in part) |
| Code revision verified | `16d4c04485e6af0a9e262b08cfe23f356d868870` on branch `feat/evidence-integrity` (base `78e512c`). This statement was added in the next commit, which changes no code. |
| Package | `proofhouse` 0.2.1, framework 1.3 |
| Platform | Windows 11, CPython 3.14.6, uv; Node 24.14.0 for artifact checks |
| Maintainer | KM-it-ops (repository owner); implementation assisted by an AI coding agent, reviewed by the maintainer before merge |
| Independent review | **Not yet performed.** The plan requires one before promotion. |

## Commands and results

| Command | Result |
|---|---|
| `uv sync --locked --extra test` then `uv run pytest -q` at `78e512c` | 672 passed, 1 deselected |
| same at `16d4c04` | **867 passed, 1 deselected** (the deselected test is the opt-in live test) |
| Review probe scripts at `78e512c` | all 18 original observations reproduced |
| Same 18 scenarios at `16d4c04` (`work/probes/postfix_probes.py`, local) | all handled — see table below |
| `python scripts/mutation_check.py` | 15/15 targeted mutations of trust-boundary code caught by tests |
| `python scripts/reference_workflow.py` (source tree) | OK, ~13 s |
| `uv build`, fresh venv, `pip install` the wheel, `reference_workflow.py --cli <venv>/proofhouse-compiler` | OK, ~16 s; `proofhouse.__version__` = 0.2.1; `install-skill` and `--force` succeed |
| `python scripts/generate_model_surfaces.py --check` | in sync (18 models) |
| `npm ci && npm run build` in `apps/dashboard` | built (Vite) |
| esbuild transpile of `apps/proofhouse.jsx` and the skill copy | OK |
| `tests/test_artifact_validators.py` (artifact validators under node) | 31 passed |

## Rebase onto 0.3.0, 2026-09-23

`16d4c04` is the pre-rebase revision. The branch was rebased onto the rebrand closeout
(PR #39, `proofhouse` 0.3.0), so its commit ids changed. The rebase surfaced one code defect that
merged cleanly as text: `execute-openai` still read the pre-rename semantic-context key and refused
every artifact. The commit `fix: align evidence-integrity with the Proofhouse rebrand` corrects it.
Re-run on the rebased head, same platform:

| Command | Result |
|---|---|
| `uv run pytest -q` | 869 passed, 1 deselected |
| `python scripts/mutation_check.py` | 15/15 killed |
| `python scripts/reference_workflow.py` (source tree) | OK, ~18 s |
| `python scripts/generate_model_surfaces.py --check` | in sync (18 models) |

The wheel install, dashboard build and artifact checks above were not re-run.

## Review findings

| Finding | Before (`78e512c`) | After (`16d4c04`) | Regression tests |
|---|---|---|---|
| F01 live request drops requirements | sentinels absent from provider body | requirement, uncertainty and evidence sentinels present; unsupported fields refuse with `EXE-SEM-0001`, 0 requests sent | `test_t02_runtime_semantics.py` |
| F02 duplicate ids erase failures | `[fail, pass]` → PASS | rejected with line number; structured keys; permutation-invariant | `test_t03_eval_integrity.py` |
| F03 PASS without coverage | PASS claiming `REQ-EVAL-001` | `BLOCKED`, `EVR-COV-0001`, coverage listed | `test_t03_eval_integrity.py` |
| F04 approval survives edit | tampered revision → PASS | load refused (digest mismatch); verdicts digest-bound; immutable check runs; atomic writes | `test_t04_revision_integrity.py` |
| F05 over-confident provenance | notes file = researched, verified today | `user_supplied`, undated, `unverified`; all unsourced profiles labeled unverified; precedence rule in every compile prompt | `test_t07_notes_provenance.py`, surface tests |
| F06 wrong evaluator, silent no-repair | evaluator `evr-det-…`, 0 attempts, no reason | evaluator `evr-product-v1`; `EVR-REP-0005`; `terminal_reason` recorded; stages separated | `test_t03_eval_integrity.py` |
| F07 malformed input escapes | TypeError / AttributeError; string `"true"` → PASS | `BLOCKED` with `EVR-INP-*` for all; 400-case random substitution never raises | `test_t01_intake_validation.py` |
| F08 failed install destroys skill | previous skill and edits gone | previous skill unchanged; rollback tested; backup kept outside the skills dir | `test_t06_install_transaction.py` |
| F09 nonfinite budgets | `Infinity` accepted; `NaN` raised | both rejected (`EXE-CEIL-0001`), 0 requests; envelope says declared only | `test_t08_live_admission.py` |
| F10 artifact trusts model JSON | raw `JSON.parse` into state | schema + dependency-graph validation; hidden answers excluded; timeout/cancel | `test_artifact_validators.py` |
| F11 revise loses answers | answers absent from revise packets | answers + accepted constraints in every revise packet (CLI and artifact) | `test_t09_t12_workflow.py`, `test_artifact_validators.py` |
| F12 public trust story | no private route; OAR undefined; internal ids | SECURITY route, public decision records, help text without internal ids | documentation (no automated test) |

Still true by design: a closed-loop run with contradictory instructions passes the **structural** check. Its evidence now lists `evidence_classes: [structural_compile_check]` and `not_measured: [live_model_output, semantic_quality]`. A tiny positive cost ceiling is accepted because the ceiling is a declared budget, not an enforced limit.

## Completion criteria (from docs/product-scope.md)

| # | Status | Evidence / gap |
|---|---|---|
| 1 | met for the only live path (OpenAI) | T02 tests on the final request body; other adapters have no live path |
| 2 | met | T03/T04 tests; mutation checks |
| 3 | met for optimize cases and closed-loop evidence | revision/output/criterion/dataset/rubric digests, evaluator ids, model and source on runs |
| 4 | met | evidence classes in reports, check rows and closed-loop bundles |
| 5 | met for F01–F11 | regression tests per finding; independent review still pending |
| 6 | **partly** | the reference workflow is executable from the docs (tested) and from an installed wheel; no independent first-time user has tried it |
| 7 | met for `install-skill` | T06 tests; there is no other update path |
| 8 | met | all profiles labeled; precedence rule in every generated surface |
| 9 | **partly** | the supported interface is the CLI (functional and error-recovery tests); the artifact got labels, `role=alert`, `aria-pressed` and cancel, but no browser keyboard, responsive or reduced-motion test was run |
| 10 | **partly** | docs and help match this revision; no release was cut, and dashboard screenshots in `docs/assets/` are prototype images (some with old branding) that are not referenced as product screenshots |

## Exclusions

- No live provider call was made; `execute-openai` was exercised only through recording transports.
- No full-history secret scan, dependency vulnerability audit, or formal accessibility certification.
- CI for this branch has not run (nothing was pushed).
- GitHub private vulnerability reporting is not yet enabled on the repository; SECURITY.md gives a fallback route until it is.
- Digests detect drift and accidental edits; they do not protect a workspace from someone who controls the machine.
