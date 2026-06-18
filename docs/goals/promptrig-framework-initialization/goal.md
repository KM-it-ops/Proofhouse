# PromptRig Framework Initialization

## Objective

Initialize PromptRig as a lightweight, repo-ready Python prompt-operations framework with modular prompt assets, offline eval datasets, rubric scoring, CLI validation/reporting, tests, and a local commit on `feature/promptrig-framework`.

## Original Request

Implement the provided PromptRig initialization plan: prepare a GoalBuddy board, initialize Git in the current folder, create or select `feature/promptrig-framework`, scaffold the required files from the provided bundle, validate and test, commit locally, and do not push.

## Intake Summary

- Input shape: `existing_plan`
- Audience: developer/operators who need a professional prompt architecture, audit, rewrite, agentic design, and evaluation toolkit.
- Authority: `approved`
- Proof type: `test`
- Completion proof: required files exist, datasets validate, CLI report generation works, tests pass or failures are explained, Git branch/status are understood, and a local commit exists without pushing.
- Goal oracle: `python -m pytest`, direct CLI validation/report commands, file existence checks, and Git status/log evidence.
- Likely misfire: creating a board or copying files without proving the scaffold works, or treating the non-Git starting folder as if branch workflow had already been satisfied.
- Blind spots considered: current folder initially has no `.git`, plain `node` is unavailable, existing starter artifacts must be preserved, and provider/API integration must remain out of scope.
- Existing plan facts: use `promptrig_source_bundle.zip` as the starter scaffold; preserve root starter artifacts; initialize Git here; use bundled Codex Node for GoalBuddy checks when plain `node` is unavailable; do not push.

## Goal Oracle

The oracle for this goal is:

`A final Judge/PM audit maps the local commit, required file tree, dataset validation, CLI report generation, pytest or fallback validation, and clean no-push status back to the original PromptRig initialization request.`

The PM must keep comparing task receipts to this oracle. Planning, discovery, a passing tiny slice, or a clean-looking board is not enough. The goal finishes only when a final Judge/PM audit maps receipts and verification back to this oracle and records `full_outcome_complete: true`.

## Goal Kind

`existing_plan`

## Current Tranche

Complete the full local initialization tranche: establish the GoalBuddy board, initialize Git/branch workflow, apply the PromptRig scaffold, verify CLI/tests/datasets, commit locally, and record any deviations.

## Non-Negotiable Constraints

- Inspect before overwriting existing files.
- Preserve existing root starter artifacts unless replacement is clearly intentional.
- Keep the framework lightweight and standard-library-only at runtime.
- Do not add provider APIs, secrets, credentials, account-specific data, or push to a remote.
- Keep cybersecurity and automation content defensive, authorized, educational, privacy-preserving, and compliance-oriented.
- Missing-context labels in prompt assets must be exactly `UNKNOWN`, `NOT SPECIFIED`, and `NOT FOUND IN PROVIDED MATERIAL`.
- Final response must include branch used, files created/updated, tests and validation run, results, blockers/deviations, and recommended next command.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after planning, discovery, or Judge selection if a safe Worker task can be activated.

Do not stop because pytest is unavailable. Run direct Python validation and record pytest as a blocker/deviation.

## Slice Sizing

Use the largest safe useful slice: after the Scout/Judge baseline, one Worker should initialize Git, apply the scaffold, run verification, and commit unless a stop condition occurs.

## Canonical Board

Machine truth lives at:

`docs/goals/promptrig-framework-initialization/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/promptrig-framework-initialization/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Work only on the active board task.
4. Assign Scout, Judge, Worker, or PM according to the task.
5. Write a compact task receipt.
6. Update the board.
7. Continue safe local work until final audit proves the owner outcome.
