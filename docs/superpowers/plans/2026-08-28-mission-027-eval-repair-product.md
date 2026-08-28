# MISSION-027 Evaluation/Repair Product Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use PromptRig SDD (`promptrig-sdd-implementer` + `promptrig-sdd-task-reviewer`). Superpowers SDD only if that pair is unavailable. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rubric/dataset, baseline comparison, scoring aggregation, and a production regression gate beside the existing fake-adapter oracle. Do not promote the requirements compiler to CERTIFIED. Do not claim the new product surface is CERTIFIED.

**Architecture:** Additive library modules. Keep `evaluate_deterministic` unchanged. Closed-loop default stays oracle-only. JSON fixtures (no PyYAML). Rebase onto local `main` after MISSION-026 Ready lands if 026 already merged; otherwise start from the plan-commit HEAD and do not edit `architecture/mission-026-certification/` pack files.

**Tech stack:** Python 3.11+, pytest via `uv run --with pytest python -m pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-28-mission-027-eval-repair-product-design.md`
- Contract: `architecture/evaluation-repair-contract-v0.1/` (PROPOSED). Implement engines; do not flip the contract README to certified.
- Isolated worktree only: `C:/AI/projects/PromptRig/.worktrees/mission-027-eval-repair-product` on `feature/mission-027-eval-repair-product`. Do not edit the `main` checkout.
- Offline: `network_allowed=false`, no credentials, no live providers, no model judges.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- **M3 forbidden.** No freeform NLP. No IR v0.2. Do not unlock OQ-008-004/007/008/009.
- Do not change `evaluate_deterministic` behavior. Do not promote legacy `evals/` to Compiler Core.
- No new CLI command this mission.
- Do not edit `architecture/mission-026-certification/` pack files.
- Evaluation/Repair oracle slice stays CERTIFIED. New product surface is not CERTIFIED.
- Requirements compiler stays PARTIAL.
- OAR-021 is **Ready** until Boss Accepts. OAR-009 through OAR-020 must not be rewritten (OAR-020 may still be Ready on sibling).
- Prefer `uv run --with pytest python -m pytest`. Do not commit `uv.lock`. Never push `origin/main`.
- Windows: no `bash`. Write briefs with the editor.

## File structure

- Create: `src/promptrig/compiler/eval_dataset.py`
- Create: `src/promptrig/compiler/eval_rubric.py`
- Create: `src/promptrig/compiler/eval_aggregate.py`
- Create: `src/promptrig/compiler/eval_product.py`
- Create: `tests/compiler/fixtures/mission_027/cases.jsonl`
- Create: `tests/compiler/fixtures/mission_027/rubric.json`
- Create: `tests/compiler/test_eval_dataset.py`
- Create: `tests/compiler/test_eval_rubric.py`
- Create: `tests/compiler/test_eval_aggregate.py`
- Create: `tests/compiler/test_eval_product.py`
- Create: `tests/compiler/test_mission_027_schedule.py`
- Modify: `src/promptrig/compiler/closed_loop.py` (`ClosedLoopOptions.product_eval` default None/off)
- Modify: `src/promptrig/compiler/api.py` (lazy export `evaluate_product`, `ProductEvaluationResult`)
- Create: `architecture/mission-027-certification/README.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md`
- Create: `MISSION_027_REPORT.md`
- Modify: orientation, maturity map Evaluation/Repair rows (oracle CERTIFIED; product not CERTIFIED), OPEN_QUESTIONS last paragraph, deferred bullets, root README append
- Test: existing `tests/compiler/test_evaluation_engine.py`, `test_mission_012_certification.py` stay green

---

### Task 1: Dataset loader

**Files:**
- Create: `src/promptrig/compiler/eval_dataset.py`
- Create: `tests/compiler/fixtures/mission_027/cases.jsonl`
- Test: `tests/compiler/test_eval_dataset.py`

**Interfaces:**
- Consumes: nothing from later tasks
- Produces: `DatasetCase(case_id: str, req_ids: tuple[str, ...], observations: dict[str, bool | float | str])`; `load_dataset(path: Path) -> tuple[DatasetCase, ...]`

- [ ] **Step 1: Write fixtures and failing tests**

Create `tests/compiler/fixtures/mission_027/cases.jsonl`:

```jsonl
{"case_id": "EVC-001", "req_ids": ["REQ-EVAL-001"], "observations": {"compile_ok": true, "security_ok": true}}
{"case_id": "EVC-002", "req_ids": ["REQ-EVAL-001"], "observations": {"compile_ok": false, "security_ok": true}}
```

Create `tests/compiler/test_eval_dataset.py`:

```python
from pathlib import Path

import pytest

from promptrig.compiler.eval_dataset import load_dataset


FIXTURE = Path("tests/compiler/fixtures/mission_027/cases.jsonl")


def test_load_dataset_req_ids() -> None:
    cases = load_dataset(FIXTURE)
    assert len(cases) == 2
    assert cases[0].case_id == "EVC-001"
    assert cases[0].req_ids == ("REQ-EVAL-001",)
    assert cases[0].observations["compile_ok"] is True


def test_load_dataset_rejects_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_dataset(p)


def test_load_dataset_rejects_bad_req_id(tmp_path: Path) -> None:
    p = tmp_path / "bad.jsonl"
    p.write_text(
        '{"case_id": "EVC-X", "req_ids": ["NOPE"], "observations": {}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="REQ-"):
        load_dataset(p)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_dataset.py -v`

Expected: FAIL import of `promptrig.compiler.eval_dataset`.

- [ ] **Step 3: Implement loader**

Create `src/promptrig/compiler/eval_dataset.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetCase:
    case_id: str
    req_ids: tuple[str, ...]
    observations: dict[str, bool | float | str]


def load_dataset(path: Path) -> tuple[DatasetCase, ...]:
    cases: list[DatasetCase] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        req_ids = tuple(raw["req_ids"])
        if not req_ids or not all(isinstance(r, str) and r.startswith("REQ-") for r in req_ids):
            raise ValueError(f"line {line_no}: req_ids must be non-empty REQ-*")
        cases.append(
            DatasetCase(
                case_id=str(raw["case_id"]),
                req_ids=req_ids,
                observations=dict(raw["observations"]),
            )
        )
    if not cases:
        raise ValueError("dataset empty")
    return tuple(cases)
```

- [ ] **Step 4: Re-run tests**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add compiler JSONL evaluation dataset loader
```

---

### Task 2: Rubric scorer

**Files:**
- Create: `src/promptrig/compiler/eval_rubric.py`
- Create: `tests/compiler/fixtures/mission_027/rubric.json`
- Test: `tests/compiler/test_eval_rubric.py`

**Interfaces:**
- Consumes: `DatasetCase` from Task 1
- Produces: `Rubric`; `load_rubric(path: Path) -> Rubric`; `score_case(rubric: Rubric, case: DatasetCase) -> dict[str, float | None]` (None = missing observation / evaluator error)

- [ ] **Step 1: Write fixture and failing tests**

Create `tests/compiler/fixtures/mission_027/rubric.json`:

```json
{
  "rubric_id": "evr-product-v1",
  "version": "0.1.0",
  "criteria": [
    {"criterion_id": "compile", "field": "compile_ok", "expected": true},
    {"criterion_id": "security", "field": "security_ok", "expected": true}
  ]
}
```

Create `tests/compiler/test_eval_rubric.py`:

```python
from pathlib import Path

from promptrig.compiler.eval_dataset import DatasetCase, load_dataset
from promptrig.compiler.eval_rubric import load_rubric, score_case


CASES = Path("tests/compiler/fixtures/mission_027/cases.jsonl")
RUBRIC = Path("tests/compiler/fixtures/mission_027/rubric.json")


def test_score_pass_and_fail_cases() -> None:
    rubric = load_rubric(RUBRIC)
    cases = load_dataset(CASES)
    pass_scores = score_case(rubric, cases[0])
    assert pass_scores == {"compile": 1.0, "security": 1.0}
    fail_scores = score_case(rubric, cases[1])
    assert fail_scores["compile"] == 0.0
    assert fail_scores["security"] == 1.0


def test_missing_observation_is_none() -> None:
    rubric = load_rubric(RUBRIC)
    case = DatasetCase("EVC-Z", ("REQ-EVAL-001",), {})
    scores = score_case(rubric, case)
    assert scores["compile"] is None
    assert scores["security"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_rubric.py -v`

Expected: FAIL import of `eval_rubric`.

- [ ] **Step 3: Implement rubric**

Create `src/promptrig/compiler/eval_rubric.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .eval_dataset import DatasetCase


@dataclass(frozen=True)
class RubricCriterion:
    criterion_id: str
    field: str
    expected: bool | float | str


@dataclass(frozen=True)
class Rubric:
    rubric_id: str
    version: str
    criteria: tuple[RubricCriterion, ...]


def load_rubric(path: Path) -> Rubric:
    raw = json.loads(path.read_text(encoding="utf-8"))
    criteria = tuple(
        RubricCriterion(
            criterion_id=str(item["criterion_id"]),
            field=str(item["field"]),
            expected=item["expected"],
        )
        for item in raw["criteria"]
    )
    if not criteria:
        raise ValueError("rubric has no criteria")
    return Rubric(str(raw["rubric_id"]), str(raw["version"]), criteria)


def score_case(rubric: Rubric, case: DatasetCase) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for criterion in rubric.criteria:
        if criterion.field not in case.observations:
            out[criterion.criterion_id] = None
            continue
        out[criterion.criterion_id] = (
            1.0 if case.observations[criterion.field] == criterion.expected else 0.0
        )
    return out
```

- [ ] **Step 4: Re-run tests**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add deterministic JSON rubric scorer
```

---

### Task 3: Scoring aggregation

**Files:**
- Create: `src/promptrig/compiler/eval_aggregate.py`
- Test: `tests/compiler/test_eval_aggregate.py`

**Interfaces:**
- Consumes: score dicts from Task 2
- Produces: `Aggregation` literal; `aggregate_scores(scores: dict[str, float | None], method: Aggregation) -> tuple[float | None, tuple[str, ...]]` — None primary + `EVR-SCR-0001` when any value is None

- [ ] **Step 1: Write failing tests**

Create `tests/compiler/test_eval_aggregate.py`:

```python
from promptrig.compiler.eval_aggregate import aggregate_scores


def test_any_fail_and_all_pass() -> None:
    primary, codes = aggregate_scores({"a": 1.0, "b": 0.0}, "any_fail")
    assert primary == 0.0
    assert codes == ()
    primary, codes = aggregate_scores({"a": 1.0, "b": 1.0}, "all_pass")
    assert primary == 1.0
    primary, codes = aggregate_scores({"a": 1.0, "b": 0.0}, "all_pass")
    assert primary == 0.0


def test_min_max_mean() -> None:
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "min")[0] == 0.0
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "max")[0] == 1.0
    assert aggregate_scores({"a": 0.0, "b": 1.0}, "mean")[0] == 0.5


def test_none_score_is_evr_scr_0001() -> None:
    primary, codes = aggregate_scores({"a": 1.0, "b": None}, "min")
    assert primary is None
    assert "EVR-SCR-0001" in codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_aggregate.py -v`

Expected: FAIL import.

- [ ] **Step 3: Implement aggregation**

Create `src/promptrig/compiler/eval_aggregate.py`:

```python
from __future__ import annotations

from typing import Literal

Aggregation = Literal["min", "max", "mean", "any_fail", "all_pass"]


def aggregate_scores(
    scores: dict[str, float | None], method: Aggregation
) -> tuple[float | None, tuple[str, ...]]:
    if any(value is None for value in scores.values()):
        return None, ("EVR-SCR-0001",)
    values = list(scores.values())
    assert values
    if method == "min":
        return min(values), ()
    if method == "max":
        return max(values), ()
    if method == "mean":
        return sum(values) / len(values), ()
    if method == "any_fail":
        return (0.0 if any(v < 1.0 for v in values) else 1.0), ()
    if method == "all_pass":
        return (1.0 if all(v >= 1.0 for v in values) else 0.0), ()
    raise ValueError(f"unknown aggregation: {method}")
```

- [ ] **Step 4: Re-run tests**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add evaluation score aggregation with EVR-SCR-0001
```

---

### Task 4: Product evaluator (oracle + baseline + regression)

**Files:**
- Create: `src/promptrig/compiler/eval_product.py`
- Modify: `src/promptrig/compiler/api.py` (lazy export)
- Test: `tests/compiler/test_eval_product.py`

**Interfaces:**
- Consumes: `evaluate_deterministic`; Tasks 1–3
- Produces: `ProductEvalRequest`; `ProductEvaluationResult`; `evaluate_product(request: ProductEvalRequest) -> ProductEvaluationResult`
  - `evaluator_id = "evr-product-v1"`; `evaluator_version = "0.1.0"`
  - Oracle runs first via `evaluate_deterministic` (do not copy its logic)
  - Missing/stale baseline when `baseline_required=True`: `BLOCKED` + `EVR-BSL-0001` or `EVR-BSL-0002`
  - Candidate primary < baseline primary: status `REGRESSION`
  - `failed_attempts` empty on first-pass; never drop codes
  - `req_ids` union from dataset cases

- [ ] **Step 1: Write failing tests**

Create `tests/compiler/test_eval_product.py`:

```python
from pathlib import Path

from promptrig.compiler.eval_product import ProductEvalRequest, evaluate_product


CASES = Path("tests/compiler/fixtures/mission_027/cases.jsonl")
RUBRIC = Path("tests/compiler/fixtures/mission_027/rubric.json")


def _req(**overrides: object) -> ProductEvalRequest:
    base = dict(
        baseline_digest="sha256:base",
        candidate_digest="sha256:cand",
        dataset_path=CASES,
        rubric_path=RUBRIC,
        aggregation="any_fail",
        baseline_required=True,
        baseline_primary=1.0,
        network_used=False,
        compile_ok=True,
        security_ok=True,
        baseline_stale=False,
    )
    base.update(overrides)
    return ProductEvalRequest(**base)  # type: ignore[arg-type]


def test_network_still_blocks() -> None:
    result = evaluate_product(_req(network_used=True))
    assert result.status == "BLOCKED"
    assert "EVR-NET-0001" in result.diagnostic_codes


def test_missing_baseline_blocks() -> None:
    result = evaluate_product(_req(baseline_digest=None))
    assert result.status == "BLOCKED"
    assert "EVR-BSL-0001" in result.diagnostic_codes


def test_stale_baseline_blocks() -> None:
    result = evaluate_product(_req(baseline_stale=True))
    assert result.status == "BLOCKED"
    assert "EVR-BSL-0002" in result.diagnostic_codes


def test_regression_when_worse_than_baseline() -> None:
    result = evaluate_product(_req(baseline_primary=1.0))
    # fixture case EVC-002 fails compile_ok; any_fail primary is 0.0
    assert result.status == "REGRESSION"
    assert result.scores["primary"] == 0.0
    assert "REQ-EVAL-001" in result.req_ids
    assert result.failed_attempts == ()


def test_error_score_does_not_pass(tmp_path: Path) -> None:
    cases = tmp_path / "one.jsonl"
    cases.write_text(
        '{"case_id": "EVC-Z", "req_ids": ["REQ-EVAL-001"], "observations": {}}\n',
        encoding="utf-8",
    )
    result = evaluate_product(_req(dataset_path=cases, baseline_required=False))
    assert result.status == "ERROR"
    assert "EVR-SCR-0001" in result.diagnostic_codes
    assert result.scores["primary"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_product.py -v`

Expected: FAIL import.

- [ ] **Step 3: Implement product evaluator**

Create `src/promptrig/compiler/eval_product.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .eval_aggregate import Aggregation, aggregate_scores
from .eval_dataset import load_dataset
from .eval_rubric import load_rubric, score_case
from .evaluation import EvaluationRequest, evaluate_deterministic

PRODUCT_EVALUATOR_ID = "evr-product-v1"
PRODUCT_EVALUATOR_VERSION = "0.1.0"


@dataclass(frozen=True)
class ProductEvalRequest:
    baseline_digest: str | None
    candidate_digest: str
    dataset_path: Path
    rubric_path: Path
    aggregation: Aggregation
    baseline_required: bool
    baseline_primary: float | None
    network_used: bool
    compile_ok: bool
    security_ok: bool
    baseline_stale: bool = False


@dataclass(frozen=True)
class ProductEvaluationResult:
    status: str
    diagnostic_codes: tuple[str, ...]
    scores: dict[str, float | None]
    evaluator_id: str
    evaluator_version: str
    authoritative: bool
    aggregation: str
    failed_attempts: tuple[dict[str, object], ...]
    req_ids: tuple[str, ...]


def evaluate_product(request: ProductEvalRequest) -> ProductEvaluationResult:
    oracle = evaluate_deterministic(
        EvaluationRequest(
            baseline_digest=request.baseline_digest,
            candidate_digest=request.candidate_digest,
            compile_ok=request.compile_ok,
            security_ok=request.security_ok,
            network_used=request.network_used,
            baseline_required=request.baseline_required,
        )
    )
    if oracle.status != "PASS":
        return ProductEvaluationResult(
            status=oracle.status,
            diagnostic_codes=oracle.diagnostic_codes,
            scores=dict(oracle.scores),
            evaluator_id=oracle.evaluator_id,
            evaluator_version=oracle.evaluator_version,
            authoritative=oracle.authoritative,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=(),
        )
    if request.baseline_stale:
        return ProductEvaluationResult(
            status="BLOCKED",
            diagnostic_codes=("EVR-BSL-0002",),
            scores={"primary": None},
            evaluator_id=PRODUCT_EVALUATOR_ID,
            evaluator_version=PRODUCT_EVALUATOR_VERSION,
            authoritative=True,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=(),
        )

    cases = load_dataset(request.dataset_path)
    rubric = load_rubric(request.rubric_path)
    merged: dict[str, float | None] = {}
    req_ids: list[str] = []
    for case in cases:
        req_ids.extend(case.req_ids)
        for key, value in score_case(rubric, case).items():
            slot = f"{case.case_id}:{key}"
            merged[slot] = value

    primary, codes = aggregate_scores(merged, request.aggregation)
    if "EVR-SCR-0001" in codes:
        return ProductEvaluationResult(
            status="ERROR",
            diagnostic_codes=codes,
            scores={"primary": None},
            evaluator_id=PRODUCT_EVALUATOR_ID,
            evaluator_version=PRODUCT_EVALUATOR_VERSION,
            authoritative=True,
            aggregation=request.aggregation,
            failed_attempts=(),
            req_ids=tuple(dict.fromkeys(req_ids)),
        )

    status = "PASS" if primary == 1.0 else "FAIL"
    if (
        request.baseline_required
        and request.baseline_primary is not None
        and primary is not None
        and primary < request.baseline_primary
    ):
        status = "REGRESSION"

    return ProductEvaluationResult(
        status=status,
        diagnostic_codes=codes,
        scores={"primary": primary},
        evaluator_id=PRODUCT_EVALUATOR_ID,
        evaluator_version=PRODUCT_EVALUATOR_VERSION,
        authoritative=True,
        aggregation=request.aggregation,
        failed_attempts=(),
        req_ids=tuple(dict.fromkeys(req_ids)),
    )
```

In `api.py`, add `"evaluate_product"` and `"ProductEvaluationResult"` to a new `_PRODUCT_EVAL_EXPORTS` frozenset unioned into `_LAZY_EXPORTS`, and resolve them from `eval_product`.

- [ ] **Step 4: Re-run product tests plus oracle regression**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_product.py tests/compiler/test_evaluation_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add product evaluation path with baseline regression gate
```

---

### Task 5: Closed-loop hook (default off)

**Files:**
- Modify: `src/promptrig/compiler/closed_loop.py`
- Test: append to `tests/compiler/test_eval_product.py`

**Interfaces:**
- Consumes: `evaluate_product`
- Produces: `ClosedLoopOptions.product_eval: ProductEvalRequest | None = None`. When None, loop behavior identical to today. When set, after oracle PASS, run `evaluate_product` and if status is `REGRESSION`/`FAIL`/`ERROR`/`BLOCKED`, set `ClosedLoopResult.status` to that product status (do not change repair budget rules). Do not instantiate test hooks from this path.

- [ ] **Step 1: Write failing test**

Append to `tests/compiler/test_eval_product.py`:

```python
import json

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop
from promptrig.compiler.eval_product import ProductEvalRequest


def _closed_loop_doc() -> dict:
    fixture = Path("tests/compiler/fixtures/closed_loop_requirements_minimal.json")
    return json.loads(fixture.read_text(encoding="utf-8"))


def test_closed_loop_default_ignores_product() -> None:
    result = run_closed_loop(_closed_loop_doc(), ClosedLoopOptions())
    assert result.status == "PASS"


def test_closed_loop_product_regression_surface() -> None:
    product = ProductEvalRequest(
        baseline_digest="sha256:base",
        candidate_digest="sha256:cand",
        dataset_path=CASES,
        rubric_path=RUBRIC,
        aggregation="any_fail",
        baseline_required=True,
        baseline_primary=1.0,
        network_used=False,
        compile_ok=True,
        security_ok=True,
    )
    result = run_closed_loop(_closed_loop_doc(), ClosedLoopOptions(product_eval=product))
    assert result.status == "REGRESSION"
```

- [ ] **Step 2: Run the new tests (RED)**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_product.py::test_closed_loop_product_regression_surface -v`

Expected: FAIL (`ClosedLoopOptions` has no `product_eval`).

- [ ] **Step 3: Wire options**

Add to `ClosedLoopOptions`:

```python
product_eval: ProductEvalRequest | None = None
```

Import `ProductEvalRequest`, `evaluate_product` in `closed_loop.py`. After the existing `evaluate_deterministic` call, if `options.product_eval is not None` and oracle status is `PASS`, call `evaluate_product` with `options.product_eval` (use the live `candidate_digest` from this attempt when replacing the request’s candidate_digest via a copy if needed). If product status is not `PASS`, set the loop result status to the product status when finishing that attempt (do not repair on REGRESSION unless oracle also failed — oracle still owns repair). Keep `repair_budget` and `EVR-SEC-0001` unchanged.

Default `product_eval=None` so `test_mission_012_certification.py` stays green.

- [ ] **Step 4: Run product + 012 tests**

Run: `uv run --with pytest python -m pytest tests/compiler/test_eval_product.py tests/compiler/test_evaluation_engine.py tests/compiler/test_mission_012_certification.py tests/compiler/test_closed_loop.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add opt-in closed-loop product evaluation hook
```

---

### Task 6: Honesty / OAR-021 Ready

**Files:**
- Create: `architecture/mission-027-certification/README.md`
- Create: `tests/compiler/test_mission_027_schedule.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md`
- Create: `MISSION_027_REPORT.md`
- Modify: `architecture/strategy/PROJECT_ORIENTATION.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Evaluation and Repair rows: oracle CERTIFIED; product surface not CERTIFIED. Requirements compiler stays PARTIAL.)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` last paragraph
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` (product bar no longer “missing”; still not CERTIFIED product surface; 026 wording untouched except sibling note if that file is shared)
- Modify: root `README.md` append only
- Do not edit `architecture/mission-026-certification/`

**Interfaces:**
- Consumes: Tasks 1–5
- Produces: OAR-021 Ready; honesty schedule

- [ ] **Step 1: Write failing schedule test**

Create `tests/compiler/test_mission_027_schedule.py`:

```python
from pathlib import Path


def test_mission_027_product_bar_not_certified_compiler() -> None:
    note = Path("architecture/mission-027-certification/README.md")
    assert note.is_file()
    lower = note.read_text(encoding="utf-8").lower()
    for token in (
        "partial",
        "oar-021",
        "evaluate_deterministic",
        "rubric",
        "dataset",
        "regression",
        "oq-008-004",
        "oq-008-007",
        "oq-008-008",
        "oq-008-009",
    ):
        assert token in lower, token
    assert "not certified" in lower or "not certif" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "evr-sec-0001" in lower or "network_allowed" in lower
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    assert "| Evaluation | `CERTIFIED`" in maturity
    oar = Path("architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md")
    assert oar.is_file()
    status = next(
        line for line in oar.read_text(encoding="utf-8").splitlines() if line.lower().startswith("**status:**")
    )
    assert "ready" in status.lower()
    assert "accepted" not in status.lower()
```

- [ ] **Step 2: Run test (RED), then write README and OAR**

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_027_schedule.py -v`

Expected: FAIL (README missing).

Create `architecture/mission-027-certification/README.md`:

```markdown
# MISSION-027 Evaluation/Repair Product Bar

**Status:** OAR-021 Ready (not Accepted).
**Baseline:** Campaign COMPILER remaining work after MISSION-025 / OAR-019 Accepted. Sibling of MISSION-026.
**Scope:** Additive rubric/dataset engine, baseline comparison, scoring aggregation, and production regression gate. Fake-adapter only. No new CLI.

This mission does not promote the requirements compiler.

## What this mission records (narrow)

- **OAR-021 Ready (not Accepted).**
- Requirements compiler stays **PARTIAL**. **Not CERTIFIED**. Not full MISSION-008. Not full Roadmap **Phase 4B** exit.
- `evaluate_deterministic` oracle slice stays **CERTIFIED**. The new product surface (rubric, dataset, aggregation, regression) is implemented and **not CERTIFIED**.
- **OQ-008-004** / **OQ-008-007** / **OQ-008-008** / **OQ-008-009** remain locked-not-built.
- `EVR-SEC-0001` and `network_allowed=false` unchanged. Repair budgets `{0,1,2}`.
- Do not rewrite the MISSION-026 pack.

## Non-claims

- Not CERTIFIED requirements compiler. Not CERTIFIED product evaluation surface.
- Not **M3** / **Simple Mode** UI.
- **Not a live** provider path. **Not freeform** NLP. No IR v0.2.
```

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md`:

```markdown
# OAR-021 — MISSION-027 Evaluation/Repair Product Bar

**Status:** Ready (not Accepted).

**Certified if accepted:** rubric/dataset engine, baseline comparison, scoring aggregation, and production regression gate are implemented beside `evaluate_deterministic` without promoting the requirements compiler to CERTIFIED and without certifying the new product surface. Fake-adapter deterministic oracle stays the CERTIFIED evaluation/repair slice. No new CLI. OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, alias-group implementation, IR v0.2, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, CERTIFIED requirements compiler, CERTIFIED evaluation/repair product surface, benchmarks/claims, hosted product surfaces, MissionRig, enterprise SAST. Do not drop `-draft`. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-020 remain historical snapshots (do not rewrite).
```

- [ ] **Step 3: Current-state docs**

`PROJECT_ORIENTATION.md`: add `Job 027 ........... in    (eval/repair product bar; OAR-021 Ready; not CERTIFIED)`. Last Accepted job stays 025 / OAR-019 (026 Ready is not Accepted). Compiler PARTIAL.

`CAPABILITY_MATURITY_MAP.md`: keep Evaluation `CERTIFIED` for the oracle; add MISSION-027 product surface implemented, not CERTIFIED. Keep Repair `CERTIFIED` for instruction-append; note regression gate exists on the product path, not CERTIFIED. Requirements compiler stays `PARTIAL`.

`OPEN_QUESTIONS.md` last paragraph: add MISSION-027 product bar (OAR-021 Ready). Keep locked OQs and M3 / CERTIFIED compiler / Phase 4B unauthorized.

`DEFERRED_AND_REJECTED_WORK.md`: the OAR-006 bullet must no longer say the engines are “still unauthorized.” Say they are implemented (OAR-021 Ready) and the product surface is not CERTIFIED / not Phase 4B exit. Keep 026 pack independence wording (not 4B-exit certification).

Root `README.md`: append a MISSION-027 bullet only.

- [ ] **Step 4: MISSION_027_REPORT.md** plus honesty suite

Run: `uv run --with pytest python -m pytest tests/compiler/test_mission_027_schedule.py tests/compiler/test_eval_dataset.py tests/compiler/test_eval_rubric.py tests/compiler/test_eval_aggregate.py tests/compiler/test_eval_product.py tests/compiler/test_evaluation_engine.py tests/compiler/test_mission_012_certification.py tests/compiler/test_mission_025_schedule.py tests/compiler/test_mission_026_schedule.py -v`

`test_mission_026_schedule.py` may be missing if 026 is not on this branch. If the file is absent, skip it. If present, it must pass and 026 pack files must be unmodified.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
docs: add OAR-021 Ready and MISSION-027 product-bar honesty
```

---

## Execution notes

- Worktree: `C:/AI/projects/PromptRig/.worktrees/mission-027-eval-repair-product`
- Branch: `feature/mission-027-eval-repair-product`
- Rebase onto local `main` after 026 Ready lands, then continue.
- After Task 6: stop for Boss Accept of OAR-021. Do not push `origin/main`.
- Spec coverage: dataset → Task 1; rubric → Task 2; aggregation → Task 3; baseline/regression orchestrator → Task 4; closed-loop hook → Task 5; honesty/OAR → Task 6; no new CLI; oracle unchanged.
