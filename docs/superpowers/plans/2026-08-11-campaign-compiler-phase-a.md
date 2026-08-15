# Campaign COMPILER Phase A — C0 + MISSION-012 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize governance honesty with OAR-005, then graduate the fake-adapter closed loop from MISSION-010 prototype semantics to a production-grade **offline headless** evaluation/repair/evidence boundary (MISSION-012), without live providers, UI, or IR v0.2.

**Architecture:** Keep `run_closed_loop` as the orchestrator. Extract deterministic evaluation and bounded repair into focused modules that implement MISSION-009 EVR semantics for the approved structured profiles. Graduate evidence-bundle identity and contract version labels from draft/prototype to accepted headless v0.1. Preserve offline/no-credential defaults. Test-only force hooks move behind an explicit `ClosedLoopTestHooks` type that production CLI never constructs.

**Tech Stack:** Python 3.11+, existing `promptrig.compiler` package, pytest, `promptrig-compiler` CLI, architecture contracts under `architecture/evaluation-repair-contract-v0.1/` and `architecture/requirements-compiler-contract-v0.1/`.

**Baseline:** `main` @ `9d7321ccf0c010ea6de83062f5ae9701c5131e42`  
**Branch / worktree:** `feature/mission-012-compiler-graduation` in `.worktrees/mission-012-compiler-graduation`  
**Authority:** Boss authorized Campaign COMPILER 2026-08-11; ask before push/merge/tag/PyPI.

## Global Constraints

- Exact baseline `9d7321c`; do not rewrite history; preserve freeze tag `v0.5-architecture-freeze` and historical review corpus.
- Offline default: `network_allowed=false`, no credentials, no live providers.
- Approved authoring profiles remain only `structured_minimal_v0` and `structured_developer_v0`.
- Repair budgets remain exactly `{0,1,2}`; repair must not weaken `accepted_objectives` or `security_constraints` (`EVR-SEC-0001`).
- Deterministic validators outrank any model judge; no model judge is required infrastructure.
- Simple Mode UI-only semantics stay forbidden (`PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md` M0-only).
- No IR v0.2 schema/code changes; no Phase 6–9 product surfaces; no benchmark claims.
- Contract package docs for 008/009 may be status-updated to reflect acceptance, but semantic fields stay compatible with existing fixtures unless a task explicitly versions them.
- Maturity map promotion rule: update map + evidence + tests in the same change set that claims promotion.
- Standing Boss rule: after any subagent role exceeds 10 uses (general, not campaign-scoped), pause and propose a specialized hardened variant before continuing that role.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run pytest` when available; otherwise `python -m pytest`.

---

### Task 1: C0 Governance Honesty Sync

**Files:**
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (requirements compiler, evaluation, repair, headless loop rows + evidence baseline)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` (blocking bullets that deny certified offline boundary)
- Modify: `architecture/strategy/AMBITION_GAP_ANALYSIS_2026-08-11.md` (already present untracked — include in commit)
- Modify: `src/promptrig/compiler/closed_loop.py` module docstring only (acknowledge OAR-005 narrow certification + MISSION-012 in progress; do not change runtime behavior yet)
- Test: `tests/compiler/test_mission_011_certification.py` (add assertion that maturity map no longer claims headless loop `NOT_STARTED`)

**Interfaces:**
- Consumes: OAR-005 text; README Status; ambition-gap analysis
- Produces: Honest `PARTIAL` / narrow-certified wording for headless loop; evaluation/repair as `PARTIAL` (prototype engines exist, not full 009 production); requirements compiler as `PARTIAL` (structured profiles only)

- [ ] **Step 1: Write the failing honesty test**

Add to `tests/compiler/test_mission_011_certification.py`:

```python
from pathlib import Path

def test_maturity_map_reflects_oar005_headless_partial() -> None:
    text = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Headless requirements/evaluation/repair loop | `NOT_STARTED`" not in text
    assert "OAR-005" in text
    assert "`PARTIAL`" in text or "`CERTIFIED`" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/compiler/test_mission_011_certification.py::test_maturity_map_reflects_oar005_headless_partial -v`  
Expected: FAIL (map still says `NOT_STARTED`)

- [ ] **Step 3: Update maturity map rows**

For these rows, set status and evidence to match OAR-005 narrow truth:

| Capability | New status | Evidence must cite |
|---|---|---|
| Requirements compiler | `PARTIAL` | OAR-005, `closed_loop.requirements_to_ir`, structured profiles only |
| Evaluation | `PARTIAL` | OAR-003 + closed-loop `_evaluate_artifact` prototype; not full production engine |
| Repair | `PARTIAL` | OAR-003 + closed-loop bounded repair prototype |
| Headless requirements/evaluation/repair loop | `PARTIAL` | OAR-004, OAR-005, CLI `closed-loop`, MISSION-011 tests |

Update the map header evidence baseline to include PRs #16–#18 / commit `9d7321c`.  
Keep explicit non-claims: fake adapter only; no live; no plain-language; not full Phase 4B exit.

- [ ] **Step 4: Update deferred registry blocking language**

In `DEFERRED_AND_REJECTED_WORK.md`, replace any bullet that says no certified/production-hardened headless boundary exists with language that a **narrow** offline structured+fake boundary is accepted under OAR-005, while full Phase 4B graduation remains MISSION-012.

- [ ] **Step 5: Soften closed_loop module docstring**

Replace prototype-only denial with:

```python
"""Headless closed-loop (fake adapter only) — OAR-005 narrow certification.

Structured profiles → IR → fake compile → evaluate → bounded repair → evidence.
No network. No live providers. MISSION-012 graduates evaluation/repair/evidence
from MISSION-010 prototype semantics toward production-grade offline headless.
"""
```

Do not rename `PROTOTYPE_ID` yet (Task 4).

- [ ] **Step 6: Run honesty test + existing 011 tests**

Run: `uv run pytest tests/compiler/test_mission_011_certification.py tests/compiler/test_closed_loop.py -v`  
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add architecture/strategy/CAPABILITY_MATURITY_MAP.md \
  architecture/strategy/DEFERRED_AND_REJECTED_WORK.md \
  architecture/strategy/AMBITION_GAP_ANALYSIS_2026-08-11.md \
  src/promptrig/compiler/closed_loop.py \
  tests/compiler/test_mission_011_certification.py \
  .gitignore docs/superpowers/plans/2026-08-11-campaign-compiler-phase-a.md
git commit -m "$(cat <<'EOF'
docs: sync maturity map with OAR-005 and launch Campaign COMPILER Phase A

EOF
)"
```

---

### Task 2: Deterministic Evaluator Module (MISSION-012)

**Files:**
- Create: `src/promptrig/compiler/evaluation.py`
- Create: `tests/compiler/test_evaluation_engine.py`
- Modify: `src/promptrig/compiler/closed_loop.py` (call new evaluator; delete inline `_evaluate_artifact` body)

**Interfaces:**
- Consumes: MISSION-009 statuses (`PASS|FAIL|ERROR|BLOCKED|UNAVAILABLE|REGRESSION|UNRESOLVED_DEFECT`); diagnostic codes `EVR-*`
- Produces:

```python
@dataclass(frozen=True)
class EvaluationRequest:
    baseline_digest: str | None
    candidate_digest: str
    compile_ok: bool
    security_ok: bool
    network_used: bool
    baseline_required: bool = False
    evaluator_id: str = "evr-det-compile-security-v1"
    evaluator_version: str = "0.1.0"

@dataclass(frozen=True)
class EvaluationResult:
    status: str
    diagnostic_codes: tuple[str, ...]
    scores: dict[str, float | None]
    evaluator_id: str
    evaluator_version: str
    authoritative: bool  # True — deterministic oracle

def evaluate_deterministic(request: EvaluationRequest) -> EvaluationResult: ...
```

Rules (exact):
1. `network_used` → `BLOCKED` + `EVR-NET-0001`, `scores.primary=None`
2. `not compile_ok` → `FAIL` + `EVR-DET-0001`, `primary=0.0`
3. `not security_ok` → `BLOCKED` + `EVR-SEC-0001`, `primary=0.0`
4. `baseline_required and not baseline_digest` → `BLOCKED` + `EVR-BSL-0001`
5. else → `PASS`, empty codes, `primary=1.0`
6. `authoritative` always `True` for this evaluator

- [ ] **Step 1: Write failing tests in `tests/compiler/test_evaluation_engine.py`**

```python
from promptrig.compiler.evaluation import EvaluationRequest, evaluate_deterministic

def test_network_blocks() -> None:
    r = evaluate_deterministic(
        EvaluationRequest(
            baseline_digest="sha256:a",
            candidate_digest="sha256:b",
            compile_ok=True,
            security_ok=True,
            network_used=True,
        )
    )
    assert r.status == "BLOCKED"
    assert "EVR-NET-0001" in r.diagnostic_codes
    assert r.scores["primary"] is None
    assert r.authoritative is True

def test_compile_fail() -> None:
    r = evaluate_deterministic(
        EvaluationRequest("sha256:a", "sha256:b", False, True, False)
    )
    assert r.status == "FAIL"
    assert r.diagnostic_codes == ("EVR-DET-0001",)

def test_missing_baseline_when_required() -> None:
    r = evaluate_deterministic(
        EvaluationRequest(None, "sha256:b", True, True, False, baseline_required=True)
    )
    assert r.status == "BLOCKED"
    assert "EVR-BSL-0001" in r.diagnostic_codes

def test_pass() -> None:
    r = evaluate_deterministic(
        EvaluationRequest("sha256:a", "sha256:b", True, True, False)
    )
    assert r.status == "PASS"
    assert r.scores["primary"] == 1.0
```

- [ ] **Step 2: Run tests — expect FAIL (module missing)**

Run: `uv run pytest tests/compiler/test_evaluation_engine.py -v`

- [ ] **Step 3: Implement `evaluation.py` and wire `closed_loop.py`**

Implement `evaluate_deterministic` per rules above. Replace `_evaluate_artifact` usage in `run_closed_loop` with `evaluate_deterministic`, mapping `EvaluationResult` back into the evidence dict shape (`status`, `diagnostic_codes` as list, `scores`). Keep evidence keys stable for existing tests.

- [ ] **Step 4: Run new + closed-loop tests**

Run: `uv run pytest tests/compiler/test_evaluation_engine.py tests/compiler/test_closed_loop.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/promptrig/compiler/evaluation.py src/promptrig/compiler/closed_loop.py tests/compiler/test_evaluation_engine.py
git commit -m "$(cat <<'EOF'
feat: extract deterministic EVR evaluator for MISSION-012

EOF
)"
```

---

### Task 3: Bounded Repair Module + Test Hooks Quarantine

**Files:**
- Create: `src/promptrig/compiler/repair.py`
- Create: `tests/compiler/test_repair_engine.py`
- Modify: `src/promptrig/compiler/closed_loop.py`
- Modify: `tests/compiler/test_closed_loop.py` (construct `ClosedLoopTestHooks` instead of force flags on options if API changes)

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class ClosedLoopTestHooks:
    """Test-only. Production CLI must never instantiate this."""
    force_fail_first_compile: bool = False
    force_security_weaken_repair: bool = False

@dataclass(frozen=True)
class RepairPlan:
    mutation_summary: str
    allowed: bool
    diagnostic_codes: tuple[str, ...]

def plan_repair(*, attempt_index: int, weaken_security: bool) -> RepairPlan:
    if weaken_security:
        return RepairPlan(
            mutation_summary="remove_security_constraint",
            allowed=False,
            diagnostic_codes=("EVR-SEC-0001",),
        )
    return RepairPlan(
        mutation_summary="tighten_instruction_wording",
        allowed=True,
        diagnostic_codes=(),
    )

def apply_instruction_repair(ir_doc: dict, attempt_index: int) -> dict:
    """Return deep-copied IR with one appended repair instruction; immutables unchanged."""
```

`ClosedLoopOptions` keeps `repair_budget` and `network_allowed` only. Move force flags to optional `hooks: ClosedLoopTestHooks | None = None` on `run_closed_loop` (or on options as nested `hooks`).

- [ ] **Step 1: Write failing repair-engine tests**

```python
from promptrig.compiler.repair import plan_repair, apply_instruction_repair

def test_refuse_security_weaken() -> None:
    p = plan_repair(attempt_index=0, weaken_security=True)
    assert p.allowed is False
    assert p.diagnostic_codes == ("EVR-SEC-0001",)

def test_apply_preserves_immutables() -> None:
    ir = {
        "objective": {"success_criteria": ["a"]},
        "behavior": {"instructions": ["x"], "constraints": ["c"]},
        "requirements": [{"id": "REQ-1"}],
    }
    out = apply_instruction_repair(ir, 0)
    assert out["objective"]["success_criteria"] == ["a"]
    assert out["behavior"]["constraints"] == ["c"]
    assert [r["id"] for r in out["requirements"]] == ["REQ-1"]
    assert len(out["behavior"]["instructions"]) == 2
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement repair module; refactor closed_loop; update tests**

Ensure production path: `hooks is None` ⇒ no forced fail/weaken. Update `test_closed_loop.py` call sites to pass hooks.

- [ ] **Step 4: Add CLI guard test**

```python
def test_cli_closed_loop_has_no_force_flags(tmp_path: Path) -> None:
    # invoke compiler_main closed-loop help/args — assert argparse has no force_* flags
```

Inspect `cli_compiler.py` closed-loop subparser; do not add force flags.

- [ ] **Step 5: Run tests and commit**

```bash
git add src/promptrig/compiler/repair.py src/promptrig/compiler/closed_loop.py \
  tests/compiler/test_repair_engine.py tests/compiler/test_closed_loop.py
git commit -m "$(cat <<'EOF'
feat: extract bounded repair engine and quarantine test hooks

EOF
)"
```

---

### Task 4: Versioned Evidence Bundle Graduation

**Files:**
- Create: `src/promptrig/compiler/evidence.py`
- Create: `tests/compiler/test_evidence_bundle.py`
- Modify: `src/promptrig/compiler/closed_loop.py`
- Modify: fixtures/tests that assert `prototype_id` / contract draft versions

**Interfaces:**
- Produces:

```python
HEADLESS_LOOP_ID = "mission-012-headless-closed-loop-v0.1"
CONTRACT_008_ACCEPTED = "0.1.0"
CONTRACT_009_ACCEPTED = "0.1.0"
EVIDENCE_BUNDLE_SCHEMA = "eeb-headless-v0.1"

def build_evidence_bundle(...) -> dict[str, Any]:
    """Stable keys: bundle_id, loop_id, evidence_schema, contract_versions,
    requirement_ids, immutable_fields, adapter, ir_sha256, baseline_digest,
    evaluation, failed_attempts, unresolved_defect, network_allowed,
    network_used, repair_budget, compile_status, evaluator."""
```

Replace evidence key `prototype_id` with `loop_id` **and** keep `prototype_id` as deprecated alias equal to `loop_id` for one release (document in evidence.py docstring) so older readers do not break silently — tests must assert both during transition.

Update `validate_structured_requirements` to accept `contract_version` in `{"0.1.0-draft", "0.1.0"}` and emit `0.1.0` in new evidence `contract_versions`.

- [ ] **Step 1: Failing tests for schema identity**

```python
def test_evidence_bundle_has_graduated_ids() -> None:
    result = run_closed_loop(_doc())
    b = result.evidence_bundle
    assert b["loop_id"] == "mission-012-headless-closed-loop-v0.1"
    assert b["evidence_schema"] == "eeb-headless-v0.1"
    assert b["contract_versions"]["requirements"] == "0.1.0"
    assert b["contract_versions"]["evaluation_repair"] == "0.1.0"
    assert "evaluator" in b
    assert b["evaluator"]["id"] == "evr-det-compile-security-v1"
```

- [ ] **Step 2–4: Implement, migrate closed_loop, fix fixtures/tests, run suite subset, commit**

```bash
git commit -m "$(cat <<'EOF'
feat: graduate closed-loop evidence bundle to headless v0.1

EOF
)"
```

---

### Task 5: Library/CLI Deep Parity + External Consumer Smoke

**Files:**
- Modify: `src/promptrig/compiler/api.py` (export `run_closed_loop` / `closed_loop_from_json` if not already public)
- Create: `tests/compiler/test_closed_loop_parity.py`
- Create: `tests/compiler/fixtures/external_consumer_closed_loop.py` (minimal script-style import smoke used by test)
- Modify: `tests/compiler/test_mission_011_certification.py` or add `tests/compiler/test_mission_012_certification.py`

**Interfaces:**
- Library and CLI must produce equal `status`, `evidence_bundle["ir_sha256"]`, `evidence_bundle["evaluation"]["status"]`, and `evidence_bundle["loop_id"]` for the same fixture bytes and repair_budget.

- [ ] **Step 1: Write failing parity test** comparing library `closed_loop_from_json` vs CLI `closed-loop` stdout JSON (follow existing CLI test patterns in `test_closed_loop.py`).

- [ ] **Step 2: Write external-consumer smoke** that imports only public package paths and runs closed loop on fixture — fails if import path requires private modules incorrectly.

- [ ] **Step 3: Implement any API export fixes; run tests; commit**

```bash
git commit -m "$(cat <<'EOF'
test: certify closed-loop library/CLI parity and consumer smoke

EOF
)"
```

---

### Task 6: MISSION-012 Report, OAR-006 Draft, Maturity Promotion

**Files:**
- Create: `MISSION_012_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-006.md` (status: Ready for owner acceptance — do not mark Accepted until Boss says)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (promote evaluation/repair/headless loop to `IMPLEMENTED_NOT_CERTIFIED` or narrow `CERTIFIED` offline headless with explicit non-claims; cite MISSION-012 tests)
- Modify: `README.md` Status section (honest: MISSION-012 graduated offline eval/repair/evidence; still no live/UI/benchmarks)
- Create: `architecture/mission-012-certification/README.md` (scope, non-claims, evidence pointers)

**Interfaces:**
- OAR-006 must list Certified / Still unauthorized mirroring OAR-005 style.
- Do **not** claim full Roadmap Phase 4B exit if external-consumer matrix / perf ceilings are still thin — state residual gaps honestly.

- [ ] **Step 1: Write docs from actual test evidence on branch HEAD**
- [ ] **Step 2: Run full relevant suite**

Run: `uv run pytest tests/compiler tests/evaluation -v`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs: MISSION-012 report and OAR-006 draft for offline headless graduation

EOF
)"
```

---

## Spec Coverage Check

| Ambition-gap WP | Tasks |
|---|---|
| C0 governance sync | Task 1 |
| C1 4B graduation — evaluator | Task 2 |
| C1 4B graduation — repair + hooks | Task 3 |
| C1 evidence/versioning | Task 4 |
| C1 consumer/parity | Task 5 |
| C1 report/OAR/maturity | Task 6 |
| C2–C3 plain-language M1/M2 | Out of Phase A (later plan) |

## Residual honesty (must appear in Task 6)

MISSION-012 does **not** by itself unlock live providers, Simple Mode UI, IR v0.2, benchmarks, or enterprise SAST. Evaluator remains a deterministic compile/security oracle for fake-adapter artifacts — not a full rubric/dataset product engine.
