# MISSION-016 MISSION-008 Production Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Graduate the MISSION-008 contract-rule engine from test-only `validate_contract.py` into `promptrig.compiler` so canonical 008 artifact sets compile to `{SUCCESS, PARTIAL, BLOCKED, REFUSED, INVALID_OUTPUT}` on the public library/CLI path — without answering open OQs, without freeform NLP, without M3/live/IR v0.2, and without claiming full Phase 4B exit.

**Architecture:** One shared rule engine. Move `evaluate_contract_rules` / `context_from_artifacts` / `derive_canonical_outcome` and their helpers into `src/promptrig/compiler/requirements_contract.py`. Architecture `validate_contract.py` becomes an import/re-export plus the test-only package harness (`context_from_fixture`, schema/fixture validators). Public API is `compile_requirements`. CLI is `promptrig-compiler compile-requirements`. Existing M0/M1/M2 `closed-loop` profiles stay byte-stable; a canonical 008 payload on `closed-loop` is BLOCKED with `EVR-RQC-0001` (use `compile-requirements`). Compact `cases.json` oracle stays test-only.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`, vendored `requirements_diagnostic_registry.json`.

**Baseline:** local `main` @ `942a62d`. **Branch / worktree (execution time only):** `feature/mission-016-008-production-engine` in `C:/AI/projects/PromptRig/.worktrees/mission-016-008-production-engine`. Do not recreate the deleted 015 feature branch. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `942a62d`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers, no provider SDK/HTTP client.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Intake `plain_language_v0` remains M1. Fake suggester remains `fake-suggester-v0` sidecar. Do not add profiles. Do not map model proposals to IR.
- Repair budgets remain `{0,1,2}`; `EVR-SEC-0001` unchanged.
- Simple Mode UI-only semantics stay forbidden. M3 is not this mission.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no DFR-003 live-provider path.
- Do **not** resolve OQ-008-001 through OQ-008-009. Unknown answers stay `BLOCKED` / `PARTIAL` / gap evidence. Do not invent owner policy (coalescing, advisory-on-SUCCESS, PRS, continuation state, reasoning IR).
- Do **not** claim full Roadmap Phase 4B exit. Do **not** graduate Requirements compiler from `PARTIAL`. Do **not** claim a full MISSION-008 production compiler (no authoring-prose interpreter; canonical records only). Do **not** write comparative/benchmark performance claims (REJ-005).
- Exactly one rule-engine implementation: `promptrig.compiler.requirements_contract.evaluate_contract_rules` is the function object `validate_contract.evaluate_contract_rules` re-exports. Do not copy the precedence matrix.
- Compact semantic-oracle `fixtures/cases.json` remains a test-only projection. Production `compile_requirements` consumes canonical artifact mappings only (`requirements_document` required).
- Production CLI must never expose `force_*` / test hooks.
- OAR-010 is **Ready for owner acceptance** until Boss says Accepted. OAR-006/007/008 stay Accepted. OAR-009 stays Ready until Boss Accepts it separately — this mission does not Accept 009.
- Maturity promotion: update map + evidence + tests in the same change that claims the production engine. Requirements compiler stays `PARTIAL`.
- Ambition-gap C4 (IR v0.2 planning) is **not** this mission.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest` or `.venv/Scripts/python -m pytest`.
- After any subagent role exceeds 10 uses, pause and propose a hardened specialist.
- Do not commit `uv.lock`.

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-016-certification/README.md`
- Create: `tests/compiler/test_mission_016_schedule.py`

**Interfaces:**
- Consumes: OAR-006/007/008 Accepted; OAR-009 Ready; 008 `OPEN_QUESTIONS.md` still open for OQ-008-001–009
- Produces: mission-016 certification README that names canonical-engine scope and explicit non-claims; schedule test that fails until the README exists

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_mission_016_not_full_008_not_m3_oqs_open() -> None:
    note = Path("architecture/mission-016-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "compile_requirements" in lower or "compile-requirements" in lower
    assert "canonical" in lower
    assert "shared" in lower and "engine" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "partial" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "freeform" in lower
    assert "oq-008-001" in lower
    assert "oar-010" in lower
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_schedule.py -v`

Expected: FAIL because `architecture/mission-016-certification/README.md` does not exist.

- [ ] **Step 3: Write README**

Create `architecture/mission-016-certification/README.md` with this body (phrases required by the test):

```markdown
# MISSION-008 Production Engine Package (MISSION-016)

**Status:** In progress — OAR-010 Ready for owner acceptance after Tasks 1–6 (not Accepted in this task).
**Baseline:** local `main` @ `942a62d` (MISSION-015 residual evidence on local main; OAR-009 Ready, not Accepted).
**Scope:** Shared contract-rule engine in `promptrig.compiler` for canonical MISSION-008 artifact sets. Public `compile_requirements` / `promptrig-compiler compile-requirements`. Existing M0/M1/M2 closed-loop profiles unchanged.

## What this mission certifies (narrow)

- One shared engine: `evaluate_contract_rules` lives in `promptrig.compiler.requirements_contract` and is re-exported by the architecture package harness.
- Canonical artifact sets (`requirements_document` plus mappings/diagnostics) compile to `SUCCESS` / `PARTIAL` / `BLOCKED` / `REFUSED` / `INVALID_OUTPUT`.
- Compact `cases.json` remains a test-only projection. This is not an authoring-prose interpreter.

## Non-claims

- Not full MISSION-008 production compiler (no freeform NLP; no Simple/Developer/API/file authoring parser beyond canonical records).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- OQ-008-001 through OQ-008-009 remain open; this mission does not invent owner answers.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
- OAR-010 Ready for owner acceptance (not Accepted in this package until Boss accepts).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-016-certification/README.md tests/compiler/test_mission_016_schedule.py
git commit -m "docs: authorize MISSION-016 shared 008 production engine"
```

---

### Task 2: Shared engine in `promptrig.compiler`

**Files:**
- Create: `src/promptrig/compiler/requirements_contract.py`
- Create: `src/promptrig/compiler/schemas/requirements_diagnostic_registry.json` (byte-identical copy of `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json`)
- Modify: `src/promptrig/compiler/paths.py` (add `REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH`)
- Modify: `architecture/requirements-compiler-contract-v0.1/validate_contract.py` (delete moved symbols; import/re-export them)
- Modify: `tests/compiler/test_contract_schema_drift.py` (vendored RQC registry must match architecture source)
- Create: `tests/compiler/test_mission_016_engine.py`

**Interfaces:**
- Consumes: existing functions in `validate_contract.py` (cut-paste, no precedence-matrix rewrite)
- Produces:

```python
REQUIREMENTS_CONTRACT_VERSION: str  # "0.1.0-draft"
STATUS_VALUES: set[str]  # {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}

def load_vendored_requirements_registry() -> dict[str, dict[str, Any]]: ...
def context_from_artifacts(artifacts: Mapping[str, Any]) -> dict[str, Any]: ...
def evaluate_contract_rules(context: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]: ...
def derive_canonical_outcome(artifacts: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, list[str]]: ...

@dataclass(frozen=True, slots=True)
class RequirementsCompileResult:
    status: str
    reason_codes: tuple[str, ...]
    contract_version: str
    command: str = "compile-requirements"

def compile_requirements(
    artifacts: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult: ...
```

Move these symbols **without behavior change** from `validate_contract.py` into `requirements_contract.py` (keep private helper names): `_records`, `_identities`, `find_duplicate_identities`, `_unique`, `_model_originated`, `structured_owner_user_conflict`, `_authoritative_source`, `resolve_policy`, `_evidence_resolves`, `_scope_covers`, `_authority_satisfied`, `subject_authorized`, `prohibition_applies`, `default_authorized`, `authority_backed`, `classify_ir_pointer`, `build_ir_pointer_index`, `_resolve_ir_node`, `_default_ir_pointer_index`, `context_from_artifacts`, `evaluate_contract_rules`, `derive_canonical_outcome`, plus constants `ACCEPTED_PERMITTED_AUTHORITY`, `_EMITTING_OUTCOMES`, `CANONICAL_NAMESPACES`, `JSON_POINTER`, `STATUS_VALUES`.

Allowed mechanical edits only:
- Rename 008 `CONTRACT_VERSION` to `REQUIREMENTS_CONTRACT_VERSION = "0.1.0-draft"` in the production module. In `validate_contract.py` set `CONTRACT_VERSION = REQUIREMENTS_CONTRACT_VERSION`.
- `_default_ir_pointer_index` must read `paths.IR_SCHEMA_PATH` (vendored IR), not `architecture/compiler-contract-freeze-v0.5/...`.
- `load_vendored_requirements_registry` reads `paths.REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH`. Keep `validate_contract.load_diagnostic_registry(package: Path)` reading the architecture file (package harness).

Do **not** move `context_from_fixture` (test-only compact adapter stays in `validate_contract.py`).

- [ ] **Step 1: Write failing tests**

`tests/compiler/test_mission_016_engine.py`:

```python
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "architecture" / "requirements-compiler-contract-v0.1"
LAS = PACKAGE / "fixtures" / "linked_artifact_sets.json"


def _load_harness() -> ModuleType:
    path = PACKAGE / "validate_contract.py"
    spec = importlib.util.spec_from_file_location("mission008_contract_validator", path)
    assert spec and spec.loader
    module = ModuleType("mission008_contract_validator")
    spec.loader.exec_module(module)
    return module


def _set(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item
    raise KeyError(set_id)


def test_compile_requirements_not_importable_yet() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements  # noqa: F401


def test_positive_linked_sets_match_declared_status() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements

    expected = {
        "LAS-POS-SUCCESS-001": "SUCCESS",
        "LAS-POS-PARTIAL-001": "PARTIAL",
        "LAS-POS-BLOCKED-001": "BLOCKED",
        "LAS-POS-REFUSED-001": "REFUSED",
    }
    for set_id, status in expected.items():
        result = compile_requirements(_set(set_id)["artifacts"])
        assert result.status == status, set_id
        assert result.contract_version == "0.1.0-draft"
        assert result.command == "compile-requirements"


def test_missing_requirements_document_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements

    result = compile_requirements({"intent_input": {"contract_version": "0.1.0-draft"}})
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_harness_reexports_the_same_evaluate_contract_rules() -> None:
    from promptrig.compiler import requirements_contract as rc

    harness = _load_harness()
    assert harness.evaluate_contract_rules is rc.evaluate_contract_rules
    assert harness.context_from_artifacts is rc.context_from_artifacts
    assert harness.derive_canonical_outcome is rc.derive_canonical_outcome
```

The first test fails with `ModuleNotFoundError` until the module exists; keep it as an import smoke. After the module exists, `test_compile_requirements_not_importable_yet` still runs as an import smoke (rename is unnecessary — leave the name; it passes once the module exists).

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_engine.py -v`

Expected: FAIL (`ModuleNotFoundError: promptrig.compiler.requirements_contract`).

- [ ] **Step 3: Vendor registry + path**

Copy `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json` to `src/promptrig/compiler/schemas/requirements_diagnostic_registry.json` with identical bytes.

Append to `src/promptrig/compiler/paths.py` after `DIAGNOSTIC_REGISTRY_PATH`:

```python
REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH = _SCHEMAS_DIR / "requirements_diagnostic_registry.json"
```

Append to `tests/compiler/test_contract_schema_drift.py`:

```python
def test_vendored_requirements_diagnostic_registry_matches_source(repo_root):
    frozen = (
        repo_root
        / "architecture"
        / "requirements-compiler-contract-v0.1"
        / "requirements-diagnostic-registry.json"
    )
    assert paths.REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH.read_bytes() == frozen.read_bytes()
```

- [ ] **Step 4: Create `requirements_contract.py` and rewire harness**

Create `src/promptrig/compiler/requirements_contract.py`:

1. Module docstring: production shared MISSION-008 contract-rule engine; not an authoring-prose compiler; OQs remain open.
2. Paste moved helpers/engine from `validate_contract.py`.
3. Add:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from . import paths

REQUIREMENTS_CONTRACT_VERSION = "0.1.0-draft"
STATUS_VALUES = {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}


def load_vendored_requirements_registry() -> dict[str, dict[str, Any]]:
    payload = json.loads(paths.REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH.read_text(encoding="utf-8"))
    records = payload.get("diagnostics", [])
    by_code = {record["code"]: record for record in records}
    if len(by_code) != len(records):
        raise ValueError("duplicate requirements diagnostic code")
    return by_code


def _default_ir_pointer_index() -> tuple[set[str], set[str]]:
    ir_schema = json.loads(paths.IR_SCHEMA_PATH.read_text(encoding="utf-8"))
    return build_ir_pointer_index(ir_schema)


@dataclass(frozen=True, slots=True)
class RequirementsCompileResult:
    status: str
    reason_codes: tuple[str, ...]
    contract_version: str
    command: str = "compile-requirements"

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "contract_version": self.contract_version,
            "reason_codes": list(self.reason_codes),
            "status": self.status,
        }


def compile_requirements(
    artifacts: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult:
    if not isinstance(artifacts, Mapping) or "requirements_document" not in artifacts:
        return RequirementsCompileResult(
            status="INVALID_OUTPUT",
            reason_codes=("RQC-SCH-0001",),
            contract_version=REQUIREMENTS_CONTRACT_VERSION,
        )
    loaded = registry if registry is not None else load_vendored_requirements_registry()
    status, codes = derive_canonical_outcome(dict(artifacts), loaded)
    return RequirementsCompileResult(
        status=status,
        reason_codes=tuple(codes),
        contract_version=REQUIREMENTS_CONTRACT_VERSION,
    )
```

Place `compile_requirements` **after** `derive_canonical_outcome` is defined.

In `validate_contract.py`, delete the moved function/constant bodies and add (top of file, after stdlib imports — no inline imports):

```python
from promptrig.compiler.requirements_contract import (
    ACCEPTED_PERMITTED_AUTHORITY,
    CANONICAL_NAMESPACES,
    REQUIREMENTS_CONTRACT_VERSION as CONTRACT_VERSION,
    STATUS_VALUES,
    _EMITTING_OUTCOMES,
    authority_backed,
    classify_ir_pointer,
    context_from_artifacts,
    default_authorized,
    derive_canonical_outcome,
    evaluate_contract_rules,
    find_duplicate_identities,
    prohibition_applies,
    resolve_policy,
    structured_owner_user_conflict,
    subject_authorized,
)
```

Re-export every name `validate_package` / `validate_linked_artifact_set` / `validate_case` / `_derive_outcome` still uses. If a private helper (`_records`, `_identities`, …) is still referenced in the harness, import it too. `context_from_fixture` stays defined in `validate_contract.py` and may import `_records` / `CANONICAL_NAMESPACES` / `structured_owner_user_conflict` from the production module.

Keep `load_diagnostic_registry(package: Path)` and `load_frozen_ir_schema()` in the harness (architecture files). Do not leave a second copy of `evaluate_contract_rules`.

- [ ] **Step 5: Run engine + 008 contract tests**

Run:

```
.venv/Scripts/python -m pytest tests/compiler/test_mission_016_engine.py tests/compiler/test_contract_schema_drift.py tests/requirements/test_requirements_contract.py tests/evaluation/test_evaluation_repair_contract.py -q
```

Expected: PASS (008 corpus still green through the re-export).

- [ ] **Step 6: Commit**

```powershell
git add src/promptrig/compiler/requirements_contract.py src/promptrig/compiler/schemas/requirements_diagnostic_registry.json src/promptrig/compiler/paths.py architecture/requirements-compiler-contract-v0.1/validate_contract.py tests/compiler/test_mission_016_engine.py tests/compiler/test_contract_schema_drift.py
git commit -m "feat: share MISSION-008 contract-rule engine in promptrig.compiler"
```

---

### Task 3: Library API + CLI

**Files:**
- Modify: `src/promptrig/compiler/api.py` (lazy export `compile_requirements` and `RequirementsCompileResult`)
- Modify: `src/promptrig/compiler/cli_compiler.py` (`compile-requirements` subcommand)
- Create: `tests/compiler/test_mission_016_api.py`

**Interfaces:**
- Consumes: `compile_requirements` / `RequirementsCompileResult` from Task 2
- Produces: `from promptrig.compiler.api import compile_requirements`; CLI `promptrig-compiler compile-requirements <json> [--json]`
- Exit codes: `SUCCESS` and `PARTIAL` → `0`; `INVALID_OUTPUT` → `3` (`EXIT_VALIDATION_FAILURE`); `BLOCKED` and `REFUSED` → `5` (`EXIT_COMPILATION_FAILURE`)

- [ ] **Step 1: Write failing tests**

`tests/compiler/test_mission_016_api.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.cli_compiler import main as compiler_main

ROOT = Path(__file__).resolve().parents[2]
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def _artifacts(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item["artifacts"]
    raise KeyError(set_id)


def test_api_lazy_export_matches_engine() -> None:
    from promptrig.compiler.api import compile_requirements
    from promptrig.compiler.requirements_contract import compile_requirements as direct

    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    assert compile_requirements(artifacts).to_dict() == direct(artifacts).to_dict()


def test_cli_json_parity_with_library(tmp_path, capsys) -> None:
    from promptrig.compiler.api import compile_requirements

    artifacts = _artifacts("LAS-POS-BLOCKED-001")
    path = tmp_path / "blocked.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    code = compiler_main(["compile-requirements", str(path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    lib = compile_requirements(artifacts)
    assert payload["status"] == lib.status == "BLOCKED"
    assert payload["reason_codes"] == list(lib.reason_codes)
    assert code == 5


def test_cli_success_exit_zero(tmp_path, capsys) -> None:
    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    code = compiler_main(["compile-requirements", str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SUCCESS"
    assert code == 0
```

- [ ] **Step 2: Run — expect FAIL** (`compile-requirements` unknown)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_api.py -v`

- [ ] **Step 3: Lazy-export from `api.py`**

In `src/promptrig/compiler/api.py`, add to the lazy-export frozensets:

```python
_REQUIREMENTS_CONTRACT_EXPORTS = frozenset({"compile_requirements", "RequirementsCompileResult"})
_LAZY_EXPORTS = (
    _CLOSED_LOOP_EXPORTS
    | _PLAIN_LANGUAGE_EXPORTS
    | _MODEL_SUGGEST_EXPORTS
    | _REQUIREMENTS_CONTRACT_EXPORTS
)
```

In `__getattr__`, after the model-suggest branch:

```python
    if name in _REQUIREMENTS_CONTRACT_EXPORTS:
        from .requirements_contract import RequirementsCompileResult, compile_requirements

        return compile_requirements if name == "compile_requirements" else RequirementsCompileResult
```

Do not import `requirements_contract` at module top (closed_loop already special-cases `api`).

- [ ] **Step 4: Add CLI subcommand**

In `src/promptrig/compiler/cli_compiler.py`, add `_cmd_compile_requirements` next to `_cmd_closed_loop` (top-level import of `json` already exists):

```python
def _cmd_compile_requirements(args: argparse.Namespace) -> int:
    from .api import compile_requirements

    raw = _read_input(args.input)
    artifacts = json.loads(raw.decode("utf-8"))
    result = compile_requirements(artifacts)
    payload = result.to_dict()
    if args.json:
        sys.stdout.write(json.dumps(payload, sort_keys=True))
        sys.stdout.write("\n")
    else:
        print(f"compile-requirements: {result.status}")
        for code in result.reason_codes:
            print(f"  [{code}]")
    if result.status in {"SUCCESS", "PARTIAL"}:
        return EXIT_SUCCESS
    if result.status == "INVALID_OUTPUT":
        return EXIT_VALIDATION_FAILURE
    return EXIT_COMPILATION_FAILURE
```

In `build_parser()`, after the `closed-loop` parser:

```python
    p_req = subparsers.add_parser(
        "compile-requirements",
        help="Evaluate canonical MISSION-008 artifact JSON (not authoring prose; not closed-loop).",
    )
    p_req.add_argument("input", help="Path to canonical artifact JSON, or '-' for stdin.")
    p_req.add_argument("--json", action="store_true", help="Emit a single JSON result object.")
    p_req.set_defaults(func=_cmd_compile_requirements)
```

Do not add `--force` flags.

- [ ] **Step 5: Run — expect PASS**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_api.py tests/compiler/test_mission_016_engine.py -v`

- [ ] **Step 6: Commit**

```powershell
git add src/promptrig/compiler/api.py src/promptrig/compiler/cli_compiler.py tests/compiler/test_mission_016_api.py
git commit -m "feat: expose compile_requirements library API and CLI"
```

---

### Task 4: Closed-loop stays M0/M1/M2; 008 payload redirected

**Files:**
- Modify: `src/promptrig/compiler/closed_loop.py` (`closed_loop_from_json` only)
- Create: `tests/compiler/test_mission_016_closed_loop.py`

**Interfaces:**
- Consumes: existing `closed_loop_from_json`; Task 3 CLI is separate
- Produces: constant `REQUIREMENTS_CONTRACT_USE_COMPILE_COMMAND = "EVR-RQC-0001"`; canonical 008 JSON (`requirements_document` present, no `profile`) returns `BLOCKED` + that code and does **not** call `compile_requirements` or `requirements_to_ir`
- Existing fixtures `closed_loop_requirements_minimal.json`, `plain_language_v0`, `simple_ui_only`, `network_allowed=true` unchanged

- [ ] **Step 1: Write failing tests**

```python
from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import (
    ClosedLoopOptions,
    closed_loop_from_json,
    run_closed_loop,
)

ROOT = Path(__file__).resolve().parents[2]
MINIMAL = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def _las(set_id: str) -> dict:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    for item in payload["sets"]:
        if item["id"] == set_id:
            return item["artifacts"]
    raise KeyError(set_id)


def test_canonical_008_on_closed_loop_is_blocked_not_compiled() -> None:
    raw = json.dumps(_las("LAS-POS-SUCCESS-001")).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert "EVR-RQC-0001" in result.diagnostics
    assert result.evidence_bundle == {}


def test_structured_minimal_closed_loop_still_passes() -> None:
    result = closed_loop_from_json(MINIMAL.read_bytes(), ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"


def test_simple_mode_still_blocked() -> None:
    raw = json.dumps({"profile": "simple_mode_ui", "objective": {"goal": "x"}}).encode("utf-8")
    result = closed_loop_from_json(raw)
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in code for code in result.diagnostics)


def test_network_allowed_still_evr_net() -> None:
    result = run_closed_loop(
        json.loads(MINIMAL.read_text(encoding="utf-8")),
        ClosedLoopOptions(network_allowed=True),
    )
    assert result.status == "BLOCKED"
    assert result.diagnostics == ["EVR-NET-0001"]
```

- [ ] **Step 2: Run — expect FAIL** (SUCCESS 008 set currently BLOCKED for missing profile, but diagnostic is not `EVR-RQC-0001`)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_closed_loop.py -v`

- [ ] **Step 3: Detect canonical 008 shape**

In `src/promptrig/compiler/closed_loop.py`, next to `SIMPLE_MODE_FORBIDDEN_DIAGNOSTIC`:

```python
REQUIREMENTS_CONTRACT_USE_COMPILE_COMMAND = "EVR-RQC-0001"
```

In `closed_loop_from_json`, after the `simple_ui_only` / `simple_mode_ui` guard and **before** `profile = doc.get("profile")`:

```python
    if "requirements_document" in doc and "profile" not in doc:
        return ClosedLoopResult(
            status="BLOCKED",
            evidence_bundle={},
            diagnostics=[REQUIREMENTS_CONTRACT_USE_COMPILE_COMMAND],
        )
```

Do not import `requirements_contract` here. Do not run the 008 engine inside closed-loop.

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_closed_loop.py tests/compiler/test_closed_loop.py tests/compiler/test_mission_012_certification.py tests/compiler/test_mission_013_certification.py tests/compiler/test_mission_014_certification.py tests/compiler/test_mission_015_consumer_matrix.py -q`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/closed_loop.py tests/compiler/test_mission_016_closed_loop.py
git commit -m "fix: reject canonical 008 payloads on closed-loop with EVR-RQC-0001"
```

---

### Task 5: Certification + OQ fail-closed + consumer honesty

**Files:**
- Create: `tests/compiler/test_mission_016_certification.py`
- Create: `tests/compiler/fixtures/external_consumer_requirements_contract.py`

**Interfaces:**
- Consumes: Tasks 1–4 public API
- Produces: certification tests that lock non-claims; installed-package-style consumer that imports **only** `promptrig.compiler.api.compile_requirements` (no new CI job)

- [ ] **Step 1: Write failing tests**

`tests/compiler/fixtures/external_consumer_requirements_contract.py`:

```python
"""Installed-package consumer: import only promptrig.compiler.api public paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from promptrig.compiler.api import compile_requirements


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: external_consumer_requirements_contract.py <canonical-json>", file=sys.stderr)
        return 2
    artifacts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = compile_requirements(artifacts)
    sys.stdout.write(json.dumps(result.to_dict(), sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`tests/compiler/test_mission_016_certification.py`:

```python
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "architecture" / "mission-016-certification" / "README.md"
OQ = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "OPEN_QUESTIONS.md"
ENGINE = ROOT / "src" / "promptrig" / "compiler" / "requirements_contract.py"
CONSUMER = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_requirements_contract.py"
LAS = (
    ROOT
    / "architecture"
    / "requirements-compiler-contract-v0.1"
    / "fixtures"
    / "linked_artifact_sets.json"
)


def test_readme_and_oqs_still_honest() -> None:
    lower = README.read_text(encoding="utf-8").lower()
    assert "not full" in lower
    assert "partial" in lower
    assert "oar-010" in lower
    text = OQ.read_text(encoding="utf-8")
    for qid in [f"OQ-008-00{i}" for i in range(1, 10)]:
        assert qid in text


def test_engine_does_not_answer_open_oqs() -> None:
    source = ENGINE.read_text(encoding="utf-8")
    forbidden = (
        "coalesce",
        "prs parser",
        "spec_version\": \"0.2",
        "advisory_on_success",
        "freeform",
        "simple_mode_ui",
    )
    lower = source.lower()
    for token in forbidden:
        assert token not in lower, token


def test_single_evaluate_contract_rules_definition() -> None:
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_contract_rules"]
    assert defs == ["evaluate_contract_rules"]
    harness = (
        ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "validate_contract.py"
    ).read_text(encoding="utf-8")
    assert "def evaluate_contract_rules" not in harness
    assert "from promptrig.compiler.requirements_contract import" in harness


def test_external_consumer_uses_public_api_only() -> None:
    tree = ast.parse(CONSUMER.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    assert "promptrig.compiler.api" in imports
    assert all(not name.startswith("promptrig.compiler.") or name == "promptrig.compiler.api" for name in imports if name.startswith("promptrig"))


def test_external_consumer_success_subprocess(tmp_path) -> None:
    payload = json.loads(LAS.read_text(encoding="utf-8"))
    artifacts = next(item["artifacts"] for item in payload["sets"] if item["id"] == "LAS-POS-SUCCESS-001")
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(artifacts), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CONSUMER), str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "SUCCESS"
    assert out["command"] == "compile-requirements"
```

- [ ] **Step 2: Run — expect FAIL** until consumer fixture exists (and possibly until README phrases from Task 1 are present — those should already pass)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_certification.py -v`

- [ ] **Step 3: Add the consumer fixture** (body in Step 1). No new GitHub Actions job. Do not expand resource ceilings (REJ-005).

- [ ] **Step 4: Run certification + prior 016 tests**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_016_schedule.py tests/compiler/test_mission_016_engine.py tests/compiler/test_mission_016_api.py tests/compiler/test_mission_016_closed_loop.py tests/compiler/test_mission_016_certification.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/compiler/test_mission_016_certification.py tests/compiler/fixtures/external_consumer_requirements_contract.py
git commit -m "test: certify MISSION-016 engine honesty and public-API consumer"
```

---

### Task 6: Report, OAR-010 draft, maturity honesty

**Files:**
- Create: `MISSION_016_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-010.md` (Ready for owner acceptance — **not** Accepted)
- Modify: `architecture/mission-016-certification/README.md` (status: evidence complete, awaiting OAR-010)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Requirements compiler stays `PARTIAL`; cite 016 shared engine + `compile_requirements`; non-claim freeform/M3/live/full 008/full 4B)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` (blocking bullet: shared engine exists; remaining unauthorized: freeform, live M2, M3, full 008 authoring envelopes, full 4B exit, OQ resolutions)
- Modify: `README.md` Status (honest 016 engine; still PARTIAL; OAR-010 Ready not Accepted; OAR-009 still Ready)

**Interfaces:**
- Do **not** mark OAR-010 or OAR-009 Accepted. Do **not** set Requirements compiler to `CERTIFIED`. Do **not** claim full Phase 4B exit or full MISSION-008 production compiler.

OAR-010 draft body (Status line exactly `Ready for owner acceptance`):

```markdown
# OAR-010 — MISSION-016 MISSION-008 Production Engine

**Status:** Ready for owner acceptance.

**Certified if accepted:** shared MISSION-008 contract-rule engine in `promptrig.compiler.requirements_contract` (`evaluate_contract_rules` is the sole implementation; architecture `validate_contract.py` re-exports it). Public `compile_requirements` / `promptrig-compiler compile-requirements` evaluate canonical artifact sets to `SUCCESS` / `PARTIAL` / `BLOCKED` / `REFUSED` / `INVALID_OUTPUT`. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` return `EVR-RQC-0001`. OQ-008-001 through OQ-008-009 remain open (fail closed; no invented owner answers). Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, full MISSION-008 production requirements compiler (authoring-prose / Simple/Developer/API/file envelopes as producers), full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, resolving OQ-008-001 through OQ-008-009. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 remains Ready (not Accepted by this record).
```

`MISSION_016_REPORT.md` must include: baseline `942a62d`; tasks 1–6; tests added; explicit non-claims matching OAR-010; note that ambition-gap C4 is not this mission; note OAR-009 is still Ready.

Maturity map Requirements compiler evidence: append MISSION-016 shared engine + `compile_requirements` + `test_mission_016_*.py`. Limitations: still not full 008 production compiler; OQs open; canonical records only. Next authorized step: remains M3 per schedule **and** remaining 008 authoring envelopes / OQ decisions — do not imply M3 is unblocked by this engine.

Deferred registry blocking bullet: add that MISSION-016 lifted the 008 rule engine into production for canonical records only; remaining unauthorized list unchanged except “no production 008 engine” is no longer accurate — replace with “no full 008 authoring-envelope production compiler; OQs open.”

README Status: add a MISSION-016 sentence after the 015 sentence; keep 015/OAR-009 Ready language.

- [ ] **Step 1: Write docs from HEAD evidence**

- [ ] **Step 2: Run compiler+evaluation suite**

Run: `.venv/Scripts/python -m pytest tests/compiler tests/evaluation tests/requirements -q`

Expected: all PASS.

- [ ] **Step 3: Commit**

```powershell
git add MISSION_016_REPORT.md architecture/OWNER_ACCEPTANCE_RECORDS/OAR-010.md architecture/mission-016-certification/README.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md
git commit -m "docs: MISSION-016 report and OAR-010 draft for shared 008 engine"
```

---

## Spec Coverage Check

- Shared one engine / no second precedence matrix: Tasks 2, 5
- Canonical artifact compile statuses: Tasks 2, 3
- Public library + CLI parity: Task 3
- M0/M1/M2 closed-loop byte-stable; 008 payload redirected: Task 4
- OQ-008-001–009 remain open; fail closed: Tasks 1, 5, 6
- Compact `cases.json` stays test-only: Tasks 1–3 (production requires `requirements_document`)
- OAR-010 Ready not Accepted; compiler stays PARTIAL; no full 4B / full 008 / M3 / live / C4: Tasks 1, 6
- Installed-package-style public-API consumer without new CI job / no benchmark: Task 5

## Pre-flight (plan vs review rubric)

- Reviewer flags “full Phase 4B exit” or “CERTIFIED requirements compiler” as a defect — Tasks 1 and 6 keep residual disclosure. Governs.
- Reviewer flags a second `evaluate_contract_rules` as a defect — Task 2 re-export + Task 5 AST check. Governs.
- Moving the engine without rewriting RC-065 precedence is plan-mandated; do not “clean up” status order.
- `EVR-RQC-0001` on closed-loop rather than silently compiling 008 through `requirements_to_ir` is plan-mandated.
- OQ fail-closed (no coalescing / PRS / IR v0.2 / advisory-on-SUCCESS policy) is plan-mandated.

## Worktree / stacking

- Branch: `feature/mission-016-008-production-engine`
- Worktree: `.worktrees/mission-016-008-production-engine`
- Baseline: local `main` @ `942a62d`
- Do not recreate `feature/mission-015-phase4b-residual`. Ignore leftover `.worktrees/mission-015-phase4b-residual` husk.
- After whole-branch review: stop. No push, PR, merge, or OAR Accepted unless Boss asks.
