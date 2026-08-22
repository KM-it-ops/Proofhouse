# MISSION-018 Simple/Developer Envelope Producers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend MISSION-017 `produce_requirements` so simple and developer authoring envelopes assemble canonical MISSION-008 artifact mappings and evaluate via the existing `compile_requirements` engine — without `prs`/prose, without answering OQs, without M3/live/IR v0.2, and without claiming CERTIFIED or full Phase 4B exit.

**Architecture:** Same producer + compose path as 017. Widen allowed `authoring_mode` and per-mode source kinds. One rule engine. No new schema, CLI subcommand, or dependency.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

**Baseline:** local `main` @ `afcf9f8` (OAR-011 Accepted). **Branch / worktree (execution time only):** `feature/mission-018-simple-developer-producers` in `C:/AI/projects/PromptRig/.worktrees/mission-018-simple-developer-producers`. Spec: `docs/superpowers/specs/2026-08-21-mission-018-008-simple-developer-producers-design.md`. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `afcf9f8`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers, no provider SDK/HTTP client.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Do not add profiles.
- Repair budgets remain `{0,1,2}`; `EVR-SEC-0001` unchanged.
- Simple Mode UI-only semantics stay forbidden. M3 is not this mission. `authoring_mode=simple` here means the **008 envelope mode**, not M3 UI.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no DFR-003 live-provider path.
- Do **not** resolve OQ-008-001 through OQ-008-009.
- Do **not** claim full Roadmap Phase 4B exit. Do **not** graduate Requirements compiler from `PARTIAL`. Do **not** claim a full MISSION-008 production compiler.
- Exactly one rule-engine implementation: do not copy RC-065; do not extend `context_from_artifacts` with text matching; do not stuff `artifacts.diagnostics` to force reason codes.
- Production CLI must never expose `force_*` / test hooks. No new `produce-requirements` command.
- Ponytail-full: no new schema file, no new dependency, fewest files.
- OAR-012 is **Ready** until Boss says Accepted. OAR-011/OAR-010 stay Accepted. OAR-009 stays Ready.
- Keep existing producer validation digest (`promptrig-mission-017-producer`) unless a test explicitly requires a change.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest` or `.venv/Scripts/python -m pytest`.
- Do not commit `uv.lock`.
- Do not add `prs` producers.

## File structure

- Modify: `src/promptrig/compiler/requirements_produce.py` — allow simple/developer modes + kinds
- Modify: `src/promptrig/compiler/cli_compiler.py` — help names simple/developer
- Modify: `tests/compiler/test_mission_017_produce.py` — `prs`-only rejection for unsupported modes
- Create: `tests/compiler/test_mission_018_schedule.py`, `tests/compiler/test_mission_018_produce.py`
- Create: `architecture/mission-018-certification/README.md`, `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-012.md`, `MISSION_018_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-018-certification/README.md`
- Create: `tests/compiler/test_mission_018_schedule.py`

**Interfaces:**
- Consumes: OAR-011 Accepted; OAR-009 Ready; OQs open
- Produces: certification README; schedule test

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_018_schedule.py`:

```python
from pathlib import Path


def test_mission_018_not_full_008_not_m3_oqs_open() -> None:
    note = Path("architecture/mission-018-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "produce_requirements" in lower
    assert "simple" in lower and "developer" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "freeform" in lower
    assert "oq-008-001" in lower
    assert "oar-012" in lower
    assert "prs" in lower
    assert "phase 4b" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    for qid in (
        "OQ-008-001",
        "OQ-008-002",
        "OQ-008-003",
        "OQ-008-004",
        "OQ-008-005",
        "OQ-008-006",
        "OQ-008-007",
        "OQ-008-008",
        "OQ-008-009",
    ):
        assert qid in oq
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/compiler/test_mission_018_schedule.py -v`

Expected: FAIL (missing README)

- [ ] **Step 3: Write certification README**

Create `architecture/mission-018-certification/README.md` naming: `produce_requirements`, simple, developer, canonical, PARTIAL, not full 008, not M3 / Simple Mode UI, no live, freeform, OQ-008-001, OAR-012, prs still unauthorized, Phase 4B, file/api remain from 017.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/compiler/test_mission_018_schedule.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-018-certification/README.md tests/compiler/test_mission_018_schedule.py
git commit -m "test: add MISSION-018 honesty schedule for simple/developer producers"
```

---

### Task 2: Producer + produce tests

**Files:**
- Modify: `src/promptrig/compiler/requirements_produce.py`
- Modify: `tests/compiler/test_mission_017_produce.py`
- Create: `tests/compiler/test_mission_018_produce.py`

**Interfaces:**
- Consumes: 017 producer algorithm
- Produces: simple/developer modes; `prs` still rejected

- [ ] **Step 1: Write the failing tests**

In `test_mission_017_produce.py`, change `test_simple_developer_prs_are_invalid_output` to reject **only** `prs` (rename to `test_prs_is_invalid_output`).

Create `tests/compiler/test_mission_018_produce.py` reusing helpers pattern from 017 (`_intent`, `_source`, `_claim`, compose via `compile_requirements_input`):

```python
def test_simple_envelope_produces_ordinary_language_sources() -> None:
    # authoring_mode=simple, kind=ordinary_language → document present; compose not INVALID_OUTPUT from trust boundary
    ...


def test_developer_envelope_produces_developer_config_sources() -> None:
    # authoring_mode=developer, kind=developer_config
    ...


def test_prs_still_invalid_output() -> None:
    ...


def test_wrong_kind_for_simple_is_schema_invalid() -> None:
    # simple + kind=file → INVALID_OUTPUT + RQC-SCH-0001
    ...


def test_imports_rejected_on_simple() -> None:
    # imports present on simple → {}
    ...
```

Also assert file/api minimal envelopes still work (one smoke each) or rely on 017 suite in Step 4.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_018_produce.py tests/compiler/test_mission_017_produce.py::test_prs_is_invalid_output -q`

Expected: FAIL on new assertions / missing rename until implemented

- [ ] **Step 3: Implement producer changes**

In `requirements_produce.py`:

```python
MODE_SOURCE_KINDS = {
    "file": frozenset({"file", "decision", "contract"}),
    "api": frozenset({"api_request", "decision", "contract"}),
    "simple": frozenset({"ordinary_language", "decision", "contract"}),
    "developer": frozenset({"developer_config", "decision", "contract"}),
}
# mode not in MODE_SOURCE_KINDS → return {}
# imports: only when mode == "file"
```

Keep digest and assembly logic unchanged.

- [ ] **Step 4: Run focused tests**

Run: `uv run python -m pytest tests/compiler/test_mission_018_produce.py tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_016_engine.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_produce.py tests/compiler/test_mission_018_produce.py tests/compiler/test_mission_017_produce.py
git commit -m "feat: produce simple and developer envelopes into canonical 008 artifacts"
```

---

### Task 3: CLI help + OAR-012 Ready + honesty docs

**Files:**
- Modify: `src/promptrig/compiler/cli_compiler.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-012.md`
- Create: `MISSION_018_REPORT.md`
- Modify: `architecture/mission-018-certification/README.md` (status Ready line if needed)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`
- Modify: `README.md`
- Modify: `tests/compiler/test_mission_018_produce.py` (CLI help assertion)

**Interfaces:**
- Consumes: producer from Task 2
- Produces: OAR-012 Ready; docs; CLI help

- [ ] **Step 1: Write failing CLI help test**

Append to `test_mission_018_produce.py`:

```python
def test_compile_requirements_input_help_names_simple_developer() -> None:
    from promptrig.compiler.cli_compiler import build_parser

    parser = build_parser()
    req = None
    for action in parser._subparsers._group_actions:
        req = action.choices.get("compile-requirements")
        if req is not None:
            break
    assert req is not None
    help_text = " ".join(filter(None, [req.description, getattr(req, "help", None)]))
    # also check positional input help
    input_helps = []
    for action in req._actions:
        if getattr(action, "dest", None) == "input" or "input" in str(getattr(action, "option_strings", [])):
            input_helps.append(action.help or "")
    blob = (help_text + " " + " ".join(input_helps)).lower()
    assert "simple" in blob and "developer" in blob
```

Adapt to match how 017 help test locates the positional (see `test_compile_requirements_input_help_names_envelope` in `test_mission_017_produce.py`).

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m pytest tests/compiler/test_mission_018_produce.py::test_compile_requirements_input_help_names_simple_developer -q`

Expected: FAIL

- [ ] **Step 3: Update CLI help strings** to name file/api/simple/developer envelopes.

- [ ] **Step 4: Write OAR-012 Ready**

```markdown
# OAR-012 — MISSION-018 Simple/Developer Envelope Producers

**Status:** Ready for owner acceptance.

**Certified if accepted:** simple and developer envelope producers in `promptrig.compiler.requirements_produce` (`produce_requirements`) assemble canonical MISSION-008 artifact mappings alongside file/api; `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch envelope vs canonical payload; `evaluate_contract_rules` remains the sole RC-065 implementation. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`. OQ-008-001 through OQ-008-009 remain open (fail closed; no invented owner answers). Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, prs/authoring-prose producers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, resolving OQ-008-001 through OQ-008-009. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 remains Ready (not Accepted by this record). OAR-010 and OAR-011 remain Accepted.
```

- [ ] **Step 5: Maturity / deferred / README / MISSION_018_REPORT.md**

- Maturity: append MISSION-018 simple/developer + OAR-012 Ready; stay `PARTIAL`; limitations drop “still not simple/developer” but keep prs/prose/OQs/full 008.
- Deferred: update 017 bullet — simple/developer landed; remaining `prs`/prose; OQs; no full 008; no M3.
- README Status: one MISSION-018 sentence after 017; OAR-012 Ready.
- Report from HEAD evidence; do not Accept OAR-012.

- [ ] **Step 6: Run suite**

Run: `uv run python -m pytest tests/compiler tests/evaluation tests/requirements -q`

Expected: all PASS

- [ ] **Step 7: Commit**

```powershell
git add src/promptrig/compiler/cli_compiler.py architecture/OWNER_ACCEPTANCE_RECORDS/OAR-012.md MISSION_018_REPORT.md architecture/mission-018-certification/README.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md tests/compiler/test_mission_018_produce.py
git commit -m "docs: MISSION-018 report and OAR-012 draft for simple/developer producers"
```

---

## Spec coverage check

- simple/developer → canonical artifacts: Task 2
- file/api unchanged: Task 2 suite
- `prs` rejected: Tasks 2–3
- One engine / no new schema / no new CLI command: Tasks 2–3
- Honesty / PARTIAL / OQs / OAR-012 Ready / no M3: Tasks 1, 3

## Pre-flight (plan vs review rubric)

- No empty tests; each assertion checks a named behavior.
- No second rule engine; producer only assembles records.
- 017 rejection test update is intentional (simple/developer move to 018).
