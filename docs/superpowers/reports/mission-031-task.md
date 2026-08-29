# MISSION-031 Task U5 — IR v0.2 planning package

**Worktree:** `C:\AI\projects\PromptRig\.worktrees\mission-031-ir-v02-planning`
**Branch:** `feature/mission-031-ir-v02-planning`
**HEAD before:** `5b4ebb8` (U4 008 SUCCESS→IR bridge)

## What you implemented

Planning package only. No production IR v0.2 schema. Frozen `PROMPTRIG_IR_V0_1.schema.json` bytes unchanged (sha256 `a274953882b5b46166d87eece761dd1b637ddc7c8061b1c2ba4b2f0cb9303ad3`). U6 not started.

- `architecture/ir-v0.2-planning/`: SPEC + semantic delta (continuation vs reasoning), OPTIONS catalog (each option has a provider-neutral owner or is explicitly rejected; vendor-shaped field without an owner is invalid), compatibility/migration draft, opaque-state threat model, TypeScript impact note (generator still v0.1 only), fixtures proving v0.1 retain-defined-behavior and unknown-version/downgrade fail-closed.
- Recommend **evidence-only continuation** for the U6 live path (artifact/evidence, not an IR field). Live in this campaign stays single-request. Reasoning stays unsupported in v0.1 (ADR-006 gap).
- ADR-007 updated as **Proposed** only (not Accepted; no schema authorization). ADR-006 status untouched.
- `architecture/mission-031-certification/README.md` and `OAR-024.md` Ready (not Accepted). OAR-021=027, 022=028, 023=030 remain sibling Ready records. Skip-cert law not undone. Compiler stays PARTIAL. Not M3. Not live. Not CERTIFIED IR v0.2.

## What you tested (commands + results)

RED (schedule test only, before planning docs):

```text
uv run --with pytest python -m pytest tests/compiler/test_mission_031_schedule.py -v
```

Result: **7 failed, 1 passed** in 0.90s. Schema-hash test passed (file already frozen). Failures: missing `architecture/mission-031-certification/README.md`, missing `architecture/ir-v0.2-planning/` SPEC/OPTIONS/fixtures.

GREEN (after docs/fixtures/OAR/ADR-007 Proposed note):

```text
uv run --with pytest python -m pytest tests/compiler/test_mission_031_schedule.py tests/compiler/test_mission_030_schedule.py tests/compiler/test_mission_028_schedule.py -v
```

Result: **10 passed** in 0.56s.

Schema untouched:

```text
git diff --exit-code -- architecture/compiler-contract-freeze-v0.5/PROMPTRIG_IR_V0_1.schema.json
```

Result: exit 0 (empty diff).

## TDD Evidence

- **RED command:** `uv run --with pytest python -m pytest tests/compiler/test_mission_031_schedule.py -v`
- **RED reason:** missing README/SPEC/OPTIONS/fixtures (FileNotFoundError / AssertionError). Frozen-schema hash test already green.
- **GREEN command:** required three-file suite above.
- **GREEN output:** 10 passed in 0.56s (8 MISSION-031 schedule tests, 1 MISSION-030, 1 MISSION-028 skip-cert).

## Files changed

- Create: `architecture/ir-v0.2-planning/README.md`
- Create: `architecture/ir-v0.2-planning/SPEC.md`
- Create: `architecture/ir-v0.2-planning/OPTIONS.json`
- Create: `architecture/ir-v0.2-planning/COMPATIBILITY_MIGRATION.md`
- Create: `architecture/ir-v0.2-planning/THREAT_MODEL.md`
- Create: `architecture/ir-v0.2-planning/TYPESCRIPT_IMPACT.md`
- Create: `architecture/ir-v0.2-planning/fixtures/v0_1_valid.json`
- Create: `architecture/ir-v0.2-planning/fixtures/unknown_version.json`
- Create: `architecture/ir-v0.2-planning/fixtures/downgrade_v0_2_shape.json`
- Create: `architecture/ir-v0.2-planning/fixtures/expected_outcomes.json`
- Create: `architecture/mission-031-certification/README.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-024.md`
- Create: `tests/compiler/test_mission_031_schedule.py`
- Modify: `architecture/adr/ADR-007-Multi-Turn-State-IR-Gap.md` (Proposed planning pointer only)
- Create: `docs/superpowers/reports/mission-031-task.md`
- Not committed: `uv.lock`
- Not modified: frozen IR schema; ADR-006; production compiler/codegen; U6 live HTTP

## Self-review findings

- Completeness: SPEC delta, options with owners, invalid field, compatibility, threat model, TypeScript note, fixtures, cert README, OAR-024 Ready, ADR-007 Proposed, schedule tests, schema hash pin.
- YAGNI: no production schema, no generator retarget, no live HTTP, no U6, no maturity-map rewrite.
- Naming: `architecture/ir-v0.2-planning/` is a new folder, not dumped into the freeze directory.
- Test honesty: v0.1 fixture validates against the frozen schema; unknown version and downgrade fail closed at `/spec_version`. Skip-cert (OAR-022) not undone. Compiler stays PARTIAL.

## Concerns / residual honesty gaps

- Q4 is still unpicked. This package recommends evidence-only for U6; it does not decide CONT-IR-FIELD vs CONT-PROHIBIT.
- OQ-008-008 / OQ-008-009 remain locked-not-built. Listing Q4 options does not implement them.
- OAR-024 is Ready, not Accepted. Not CERTIFIED IR v0.2.
