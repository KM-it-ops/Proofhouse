# MISSION-014 Model-Assisted Headless M2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certify a **headless, offline, opt-in** M2 suggestion sidecar (`fake-suggester-v0`) that emits unaccepted `model_suggested` proposals and cannot become canonical IR — no live providers, no Simple Mode UI.

**Architecture:** Add `model_suggest.py` as a producing sidecar only. `build_fake_model_proposal` emits a `proposed` / `model_suggested` record (`REQ-MS-001`) derived from `objective.goal`. Existing `validate_structured_requirements` / `requirements_to_ir` / `run_closed_loop` remain the semantic owners. Proposals never enter `doc["requirements"]` and never appear in IR `requirement_ids`. An always-on MAS gate rejects `accepted` + `model_suggested`. Default `enable_model_suggestions=False` keeps 012/013 evidence byte-compatible (no `model_proposal` / `suggestion_profile` keys).

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler closed-loop`, architecture docs under `architecture/mission-011-certification/`, `architecture/mission-014-certification/`, and `architecture/OWNER_ACCEPTANCE_RECORDS/`.

## Global Constraints

- Baseline: `9e1afc9` (`main`, merge of PR #20). Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree: `C:/AI/projects/PromptRig/.worktrees/mission-014-model-assisted-m2` on `feature/mission-014-model-assisted-m2`. Do not edit `main` or leftover 012/013 husk directories.
- Offline default: `network_allowed=false`, no credentials, no live providers, **no provider SDK or HTTP client** in the suggester. Fake/scripted only (`fake-suggester-v0`). RC-074 still forbids model calls in MISSION-008; this mission is MISSION-014 and is not a live model.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Intake `plain_language_v0` remains M1. Do not extend structured requirement objects with new required fields.
- Repair budgets remain `{0,1,2}`; repair must not weaken `accepted_objectives` or `security_constraints` (`EVR-SEC-0001`).
- Simple Mode UI-only semantics stay forbidden (`authoring_mode=simple_ui_only` / `profile=simple_mode_ui`). M3 is not this mission.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no benchmark claims; no DFR-003 live-provider path.
- Proposals are **sidecar evidence only**. They must not be mapped by `requirements_to_ir`. IR `requirement_ids` with suggestions on must equal the suggestion-off run for the same structured doc.
- Gate diagnostics use prefix `MAS-GATE-` / `MAS-PARSE-` only — do not reuse `PL-PARSE-` or `EVR-`.
- Production CLI must never expose `force_*` / test hooks; quarantine behind `ClosedLoopTestHooks`.
- Maturity promotion: update map + evidence + tests in the same change that claims promotion. OAR-008 is **Ready for owner acceptance** until Boss says Accepted. Requirements compiler stays `PARTIAL`. OAR-006 and OAR-007 stay Accepted.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run pytest` when available.
- After any subagent role exceeds 10 uses, pause and propose a hardened specialist.
- Do not commit `uv.lock`.

### Fake suggester contract (normative for this mission)

Producer identity: `fake-suggester-v0` / version `0.1.0`. Suggestion profile key: `fake_suggester_v0`.

`build_fake_model_proposal(doc: dict[str, Any]) -> dict[str, Any]` returns a dict with at least:

```
id: "MAS-PROP-001"
producer_id: "fake-suggester-v0"
producer_version: "0.1.0"
acceptance_state: "proposed"
authority_basis: "model_suggested"
input_digest: "sha256:" + hex digest of canonicalize(doc)
proposed_records: ["REQ-MS-001"]
proposed_requirements: [{
  id: "REQ-MS-001",
  statement: "Consider documenting assumption: " + doc["objective"]["goal"],
  acceptance_state: "proposed",
  authority_basis: "model_suggested",
}]
output_digest: "sha256:" + hex digest of canonicalize(proposal without output_digest)
```

Same input bytes → identical proposal (including digests). The suggester must not mutate `doc`, `security_constraints`, or accepted objectives.

Always-on gate (`validate_model_boundary`): if any `doc["requirements"]` item is a dict with `acceptance_state == "accepted"` and `authority_basis == "model_suggested"`, return `["MAS-GATE-0001"]`. If a proposal dict has `acceptance_state == "accepted"`, return `["MAS-GATE-0001"]`. If a proposal or proposed requirement has `authority_basis == "owner_decision"` (invented owner authority), return `["MAS-GATE-0002"]`. Test-only hooks (never CLI):

- `force_self_accept_proposal` → `MAS-GATE-0001`
- `force_invent_owner_decision` → `MAS-GATE-0002`
- `force_weaken_security_via_suggestion` → `MAS-GATE-0003`

Gate failure status is `INVALID_OUTPUT` with those diagnostics; empty evidence bundle.

---

### Task 1: M2 contract + schedule honesty

**Files:**
- Create: `architecture/mission-014-certification/FAKE_SUGGESTER.md`
- Modify: `architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md`
- Create: `tests/compiler/test_mission_014_schedule.py`

**Interfaces:**
- Consumes: MISSION-011 schedule hard rule; OAR-007 M1 done; Boss authorization for MISSION-014 fake-offline slice
- Produces: fake-suggester note; schedule line for M2 = authorized / in progress (not done until Task 6)

- [ ] **Step 1: Write failing schedule test**

```python
from pathlib import Path


def test_m2_schedule_authorized_not_live_not_ui() -> None:
    text = Path("architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md").read_text(
        encoding="utf-8"
    )
    assert "MUST NOT be the first or only semantic implementation" in text
    assert "MISSION-014" in text
    assert "fake-suggester-v0" in text
    assert "Simple Mode UI" in text or "M3" in text
    note = Path("architecture/mission-014-certification/FAKE_SUGGESTER.md")
    assert note.is_file()
    body = note.read_text(encoding="utf-8")
    assert "fake-suggester-v0" in body
    assert "not a live" in body.lower() or "no live" in body.lower()
    assert "proposed" in body.lower()
    assert "model_suggested" in body
```

- [ ] **Step 2: Run test — expect FAIL (note missing / schedule still says M2 future)**

Run: `uv run pytest tests/compiler/test_mission_014_schedule.py -v`

- [ ] **Step 3: Write FAKE_SUGGESTER.md + update schedule**

Schedule M2 bullet becomes: authorized MISSION-014 in progress; optional headless `fake-suggester-v0` suggestion sidecar; proposals unaccepted; cannot bypass deterministic validation / authority / evidence; not a live provider; M3 still future. Keep M0 done. Keep M1 as implemented (OAR-007). Keep Simple Mode UI forbidden until M3.

`FAKE_SUGGESTER.md` states: producer `fake-suggester-v0` / `0.1.0`; sidecar only; `REQ-MS-001`; `acceptance_state=proposed`; `authority_basis=model_suggested`; never mapped to IR; not a live model; not M3; not freeform NLP; not full MISSION-008.

- [ ] **Step 4: Run test — expect PASS**

Run: `uv run pytest tests/compiler/test_mission_014_schedule.py tests/compiler/test_mission_013_schedule.py tests/compiler/test_mission_011_certification.py::test_plain_language_schedule_exists tests/compiler/test_mission_011_certification.py::test_simple_ui_only_profile_rejected -v`

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-014-certification/FAKE_SUGGESTER.md architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md tests/compiler/test_mission_014_schedule.py docs/superpowers/plans/2026-08-15-mission-014-model-assisted-m2.md
git commit -m "docs: authorize MISSION-014 fake-suggester-v0 M2 sidecar"
```

---

### Task 2: Deterministic fake suggester module

**Files:**
- Create: `src/promptrig/compiler/model_suggest.py`
- Create: `tests/compiler/test_model_suggest.py`

**Interfaces:**
- Consumes: fake suggester contract from Task 1; `promptrig.compiler.canonical.canonicalize`
- Produces:

```python
FAKE_SUGGESTER_ID = "fake-suggester-v0"
FAKE_SUGGESTER_VERSION = "0.1.0"
SUGGESTION_PROFILE = "fake_suggester_v0"
PROPOSED_REQUIREMENT_ID = "REQ-MS-001"

def build_fake_model_proposal(doc: dict[str, Any]) -> dict[str, Any]: ...
def validate_model_boundary(
    doc: dict[str, Any],
    proposal: dict[str, Any] | None = None,
) -> list[str]: ...
```

- [ ] **Step 1: Write failing tests**

```python
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

from promptrig.compiler.model_suggest import (
    FAKE_SUGGESTER_ID,
    PROPOSED_REQUIREMENT_ID,
    build_fake_model_proposal,
    validate_model_boundary,
)

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_fake_model_proposal_is_deterministic() -> None:
    a = build_fake_model_proposal(_doc())
    b = build_fake_model_proposal(_doc())
    assert a == b
    assert a["producer_id"] == FAKE_SUGGESTER_ID
    assert a["acceptance_state"] == "proposed"
    assert a["authority_basis"] == "model_suggested"
    assert a["proposed_records"] == [PROPOSED_REQUIREMENT_ID]
    assert a["proposed_requirements"][0]["id"] == PROPOSED_REQUIREMENT_ID
    assert a["proposed_requirements"][0]["statement"].startswith("Consider documenting assumption:")
    assert a["input_digest"].startswith("sha256:")
    assert a["output_digest"].startswith("sha256:")


def test_suggester_does_not_mutate_input() -> None:
    doc = _doc()
    before = deepcopy(doc)
    build_fake_model_proposal(doc)
    assert doc == before


def test_module_has_no_provider_or_http_imports() -> None:
    src = Path("src/promptrig/compiler/model_suggest.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()


def test_validate_model_boundary_rejects_self_accept() -> None:
    doc = _doc()
    doc["requirements"][0]["acceptance_state"] = "accepted"
    doc["requirements"][0]["authority_basis"] = "model_suggested"
    errors = validate_model_boundary(doc)
    assert "MAS-GATE-0001" in errors


def test_validate_model_boundary_rejects_self_accepting_proposal() -> None:
    proposal = build_fake_model_proposal(_doc())
    proposal["acceptance_state"] = "accepted"
    errors = validate_model_boundary(_doc(), proposal)
    assert "MAS-GATE-0001" in errors


def test_validate_model_boundary_rejects_invented_owner_decision() -> None:
    proposal = build_fake_model_proposal(_doc())
    proposal["authority_basis"] = "owner_decision"
    errors = validate_model_boundary(_doc(), proposal)
    assert "MAS-GATE-0002" in errors
```

- [ ] **Step 2: Run — expect FAIL (module missing)**

Run: `uv run pytest tests/compiler/test_model_suggest.py -v`

- [ ] **Step 3: Implement `model_suggest.py`**

Use `canonical.canonicalize` for digests. Compute `output_digest` from the proposal dict **without** the `output_digest` key, then set the key. `validate_model_boundary` returns a list of `MAS-GATE-*` codes (stable order, no duplicates). Do not import closed_loop (avoid cycles).

- [ ] **Step 4: Run — expect PASS**

Run: `uv run pytest tests/compiler/test_model_suggest.py -v`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/model_suggest.py tests/compiler/test_model_suggest.py
git commit -m "feat: add deterministic fake-suggester-v0 proposal sidecar"
```

---

### Task 3: Gate + closed-loop opt-in wiring

**Files:**
- Modify: `src/promptrig/compiler/repair.py` (`ClosedLoopTestHooks` — add three bool fields default False)
- Modify: `src/promptrig/compiler/closed_loop.py` (`ClosedLoopOptions.enable_model_suggestions: bool = False`; `ClosedLoopResult.model_proposal`; always-on gate; opt-in suggester before `requirements_to_ir`; thread proposal into evidence)
- Modify: `src/promptrig/compiler/evidence.py` (`build_evidence_bundle` optional `model_proposal` / `suggestion_profile`; omit keys when None)
- Create: `tests/compiler/test_model_suggest_closed_loop.py`

**Interfaces:**
- Consumes: `build_fake_model_proposal`, `validate_model_boundary`, `SUGGESTION_PROFILE`
- Produces: opt-in closed-loop path; default-off has no `model_proposal` / `suggestion_profile` keys; IR ids unchanged when on

`ClosedLoopTestHooks` becomes:

```python
@dataclass(frozen=True)
class ClosedLoopTestHooks:
    force_fail_first_compile: bool = False
    force_security_weaken_repair: bool = False
    force_self_accept_proposal: bool = False
    force_invent_owner_decision: bool = False
    force_weaken_security_via_suggestion: bool = False
```

In `run_closed_loop`, after network/budget checks and **before** `requirements_to_ir`:

1. If hooks `force_self_accept_proposal` / `force_invent_owner_decision` / `force_weaken_security_via_suggestion`, return `INVALID_OUTPUT` with the matching `MAS-GATE-0001` / `0002` / `0003` (empty evidence).
2. Run `validate_model_boundary(requirements_doc)` (always on). On errors: `INVALID_OUTPUT`.
3. If `options.enable_model_suggestions`: `proposal = build_fake_model_proposal(requirements_doc)`; run `validate_model_boundary(requirements_doc, proposal)`; on errors `INVALID_OUTPUT`; else keep `proposal` for the result/evidence. Do not append proposal records onto `requirements_doc["requirements"]`.
4. Then existing `requirements_to_ir` / compile / eval / repair.

`closed_loop_from_json`: if `doc.get("enable_model_suggestions") is True`, treat as enabled (OR with `options.enable_model_suggestions`).

`build_evidence_bundle(..., model_proposal: dict | None = None, suggestion_profile: str | None = None)`: if `model_proposal is not None`, set `bundle["model_proposal"] = model_proposal` and `bundle["suggestion_profile"] = suggestion_profile or "fake_suggester_v0"`.

- [ ] **Step 1: Write failing closed-loop tests**

```python
from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop, closed_loop_from_json
from promptrig.compiler.repair import ClosedLoopTestHooks

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_default_off_has_no_model_proposal_key() -> None:
    off = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    assert off.status == "PASS"
    assert "model_proposal" not in off.evidence_bundle
    assert "suggestion_profile" not in off.evidence_bundle
    assert off.model_proposal is None


def test_suggestions_on_sidecar_does_not_change_ir_ids() -> None:
    off = run_closed_loop(_doc(), ClosedLoopOptions(repair_budget=1))
    on = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
    )
    assert on.status == "PASS"
    assert on.evidence_bundle["requirement_ids"] == off.evidence_bundle["requirement_ids"]
    assert on.evidence_bundle["ir_sha256"] == off.evidence_bundle["ir_sha256"]
    assert on.evidence_bundle["suggestion_profile"] == "fake_suggester_v0"
    assert on.evidence_bundle["model_proposal"]["proposed_records"] == ["REQ-MS-001"]
    assert "REQ-MS-001" not in on.evidence_bundle["requirement_ids"]


def test_self_accept_in_requirements_is_invalid_output_when_off() -> None:
    doc = _doc()
    doc["requirements"][0]["acceptance_state"] = "accepted"
    doc["requirements"][0]["authority_basis"] = "model_suggested"
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0001" in result.diagnostics


def test_hook_self_accept_proposal() -> None:
    result = run_closed_loop(
        _doc(),
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_self_accept_proposal=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0001" in result.diagnostics


def test_json_enable_flag_turns_sidecar_on() -> None:
    raw = json.dumps({**_doc(), "enable_model_suggestions": True}).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["suggestion_profile"] == "fake_suggester_v0"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/compiler/test_model_suggest_closed_loop.py -v`

- [ ] **Step 3: Implement wiring as specified. Keep `prototype_id` alias. Do not change `loop_id`.**

- [ ] **Step 4: Run with regression**

Run: `uv run pytest tests/compiler/test_model_suggest_closed_loop.py tests/compiler/test_closed_loop.py tests/compiler/test_evidence_bundle.py tests/compiler/test_plain_language_closed_loop.py -v`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/repair.py src/promptrig/compiler/closed_loop.py src/promptrig/compiler/evidence.py tests/compiler/test_model_suggest_closed_loop.py
git commit -m "feat: opt-in fake suggestion sidecar on closed-loop path"
```

---

### Task 4: Library/CLI parity + public export

**Files:**
- Modify: `src/promptrig/compiler/api.py` (PEP 562 lazy export `build_fake_model_proposal`; do not re-introduce eager closed_loop cycle)
- Modify: `src/promptrig/compiler/cli_compiler.py` (`--enable-model-suggestions` on `closed-loop` only, `store_true`, default off; pass into `ClosedLoopOptions`; help text mentions optional M2 sidecar)
- Create: `tests/compiler/test_model_suggest_parity.py`
- Create: `tests/compiler/fixtures/external_consumer_model_suggest.py`

**Interfaces:**
- Library `closed_loop_from_json` + `ClosedLoopOptions(enable_model_suggestions=True)` and CLI `closed-loop --json --enable-model-suggestions` agree on `status`, `ir_sha256`, `evaluation.status`, `loop_id`, `suggestion_profile`, and `model_proposal.output_digest` for the same fixture bytes.
- Public `promptrig.compiler.api.build_fake_model_proposal` is callable.

- [ ] **Step 1: Write failing parity + consumer smoke tests**

```python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json
from promptrig.compiler.cli_compiler import main as compiler_main

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"
EXTERNAL_CONSUMER = Path(__file__).parent / "fixtures" / "external_consumer_model_suggest.py"


def test_model_suggest_public_api_exports() -> None:
    from promptrig.compiler import api

    assert callable(api.build_fake_model_proposal)
    assert callable(api.closed_loop_from_json)


def _parity_fields_from_result(result) -> dict[str, str]:
    evidence = result.evidence_bundle
    proposal = evidence["model_proposal"]
    return {
        "status": result.status,
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_output_digest": proposal["output_digest"],
    }


def _parity_fields_from_cli(payload: dict) -> dict[str, str]:
    evidence = payload["evidence_bundle"]
    proposal = evidence["model_proposal"]
    return {
        "status": payload["status"],
        "ir_sha256": evidence["ir_sha256"],
        "evaluation_status": evidence["evaluation"]["status"],
        "loop_id": evidence["loop_id"],
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_output_digest": proposal["output_digest"],
    }


@pytest.mark.parametrize("repair_budget", [0, 1, 2])
def test_library_cli_model_suggest_deep_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    repair_budget: int,
) -> None:
    fixture_bytes = FIXTURE.read_bytes()
    library = closed_loop_from_json(
        fixture_bytes,
        ClosedLoopOptions(repair_budget=repair_budget, enable_model_suggestions=True),
    )
    req_path = tmp_path / "req.json"
    req_path.write_bytes(fixture_bytes)
    code = compiler_main(
        [
            "closed-loop",
            str(req_path),
            "--json",
            "--repair-budget",
            str(repair_budget),
            "--enable-model-suggestions",
        ],
    )
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert _parity_fields_from_cli(cli) == _parity_fields_from_result(library)


def test_cli_default_omits_model_proposal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    req_path = tmp_path / "req.json"
    req_path.write_bytes(FIXTURE.read_bytes())
    code = compiler_main(["closed-loop", str(req_path), "--json", "--repair-budget", "1"])
    assert code == 0
    cli = json.loads(capsys.readouterr().out)
    assert "model_proposal" not in cli["evidence_bundle"]


def test_external_consumer_model_suggest_smoke(tmp_path: Path) -> None:
    req_path = tmp_path / "req.json"
    req_path.write_bytes(FIXTURE.read_bytes())
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(EXTERNAL_CONSUMER), str(req_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "PASS"
    assert payload["suggestion_profile"] == "fake_suggester_v0"
```

`external_consumer_model_suggest.py` must import **only** `promptrig.compiler.api` (mirror `external_consumer_plain_language.py`) and call `closed_loop_from_json` with `ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True)`.

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run pytest tests/compiler/test_model_suggest_parity.py -v`

- [ ] **Step 3: Implement lazy export + CLI flag**

In `api.py`: add `_MODEL_SUGGEST_EXPORTS = frozenset({"build_fake_model_proposal"})` to `_LAZY_EXPORTS`. In `__getattr__`, import from `.model_suggest`. Do not import `closed_loop` at module top.

In `cli_compiler.py`:

```python
p_loop.add_argument(
    "--enable-model-suggestions",
    action="store_true",
    default=False,
    help="Opt-in MISSION-014 fake-suggester-v0 sidecar (proposals are not canonical).",
)
```

Pass `enable_model_suggestions=args.enable_model_suggestions` into `ClosedLoopOptions`. Do not add any `force_*` argparse flags.

- [ ] **Step 4: Run**

Run: `uv run pytest tests/compiler/test_model_suggest_parity.py tests/compiler/test_closed_loop_parity.py tests/compiler/test_plain_language_parity.py tests/compiler/test_mission_012_certification.py -v`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/api.py src/promptrig/compiler/cli_compiler.py tests/compiler/test_model_suggest_parity.py tests/compiler/fixtures/external_consumer_model_suggest.py
git commit -m "test: certify fake-suggester library/CLI parity and consumer smoke"
```

---

### Task 5: Certification tests + non-claims

**Files:**
- Create: `tests/compiler/test_mission_014_certification.py`

**Interfaces:**
- Produces: subprocess/CLI smoke; no provider imports in `model_suggest.py`; Simple Mode still rejected; hook security-weaken and invented authority; CLI has no `force_` strings

- [ ] **Step 1: Write tests**

```python
from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json, run_closed_loop
from promptrig.compiler.repair import ClosedLoopTestHooks

FIXTURE = Path(__file__).parent / "fixtures" / "closed_loop_requirements_minimal.json"


def test_model_suggest_module_has_no_provider_imports() -> None:
    src = Path("src/promptrig/compiler/model_suggest.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()


def test_cli_compiler_has_no_force_hooks() -> None:
    src = Path("src/promptrig/compiler/cli_compiler.py").read_text(encoding="utf-8")
    assert "force_" not in src


def test_simple_ui_still_rejected_with_suggestions_flag() -> None:
    raw = json.dumps(
        {
            "profile": "plain_language_v0",
            "authoring_mode": "simple_ui_only",
            "contract_version": "0.1.0",
            "network_allowed": False,
            "enable_model_suggestions": True,
            "text": "Goal: G\nRequirements:\n1. A\n",
        }
    ).encode()
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(enable_model_suggestions=True),
    )
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in d for d in result.diagnostics)


def test_invented_owner_decision_hook() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = run_closed_loop(
        doc,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_invent_owner_decision=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0002" in result.diagnostics


def test_security_weaken_via_suggestion_hook() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = run_closed_loop(
        doc,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=True),
        hooks=ClosedLoopTestHooks(force_weaken_security_via_suggestion=True),
    )
    assert result.status == "INVALID_OUTPUT"
    assert "MAS-GATE-0003" in result.diagnostics
```

- [ ] **Step 2: Run — expect FAIL until Task 3 hooks exist (if Task 3 already landed, expect PASS after file exists)**

Run: `uv run pytest tests/compiler/test_mission_014_certification.py tests/compiler/test_mission_011_certification.py::test_simple_ui_only_profile_rejected tests/compiler/test_mission_013_certification.py -v`

- [ ] **Step 3: No extra production code unless a test fails because CLI still lacks a help-string mention — do not add `force_*` flags.**

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```powershell
git add tests/compiler/test_mission_014_certification.py
git commit -m "test: certify MISSION-014 M2 non-claims and MAS gates"
```

---

### Task 6: Report, OAR-008 draft, maturity (not Accepted)

**Files:**
- Create: `MISSION_014_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-008.md` (Ready for owner acceptance — **not** Accepted)
- Create: `architecture/mission-014-certification/README.md`
- Modify: `architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md` (M2 = implemented, awaiting OAR-008)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Requirements compiler still `PARTIAL`; cite M2 fake suggester + tests; non-claim live M2 / M3 / freeform / full 008)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` (offline fake M2 sidecar no longer “unauthorized”; remaining: live model-assisted, freeform NLP, M3, full 008)
- Modify: `README.md` Status (honest M2 fake sidecar; still no live/UI/freeform)

**Interfaces:**
- Do **not** mark OAR-008 Accepted. Do **not** set Requirements compiler to `CERTIFIED`. Do **not** claim live model assistance.

OAR-008 draft body (Status line exactly `Ready for owner acceptance`):

```
# OAR-008 — MISSION-014 Model-Assisted M2 (Fake Suggester Sidecar)

**Status:** Ready for owner acceptance.

**Certified if accepted:** headless offline opt-in `fake-suggester-v0` suggestion sidecar that emits unaccepted `proposed` / `model_suggested` proposals (`REQ-MS-001`) as evidence only — fake adapter closed loop unchanged, `network_allowed=false`, repair budgets `{0,1,2}`, `EVR-SEC-0001`, test hooks quarantined behind `ClosedLoopTestHooks`. MAS gate rejects self-accept (`MAS-GATE-0001`), invented owner authority (`MAS-GATE-0002`), and security-weaken injections (`MAS-GATE-0003`). Proposals are not mapped to IR.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, full external-consumer conformance matrix, performance/resource ceiling proof. Requirements compiler maturity remains **PARTIAL** after this record.
```

- [ ] **Step 1: Write docs from HEAD evidence**
- [ ] **Step 2: Run `uv run pytest tests/compiler tests/evaluation -v` — all PASS**
- [ ] **Step 3: Commit**

```powershell
git add MISSION_014_REPORT.md architecture/OWNER_ACCEPTANCE_RECORDS/OAR-008.md architecture/mission-014-certification/README.md architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md
git commit -m "docs: MISSION-014 report and OAR-008 draft for fake-suggester M2"
```

---

## Spec Coverage Check

| Source | Tasks |
|---|---|
| Schedule M2 after M1, before M3 UI | 1, 5, 6 |
| Fake/scripted suggester only (Boss slice) | 1, 2, 5 |
| Sidecar proposals; not in IR / `requirements_to_ir` | 2, 3 |
| Always-on MAS self-accept gate | 2, 3, 5 |
| Opt-in default off; 012/013 keys unchanged | 3, 4 |
| Library/CLI parity + public export | 4 |
| Simple Mode UI still forbidden; no `force_*` CLI | 5 |
| Honesty / OAR-008 draft not Accepted | 6 |
| Live providers, M3, freeform NLP, IR v0.2 | Out of scope |

## Worktree / stacking

- Branch: `feature/mission-014-model-assisted-m2`
- Worktree: `.worktrees/mission-014-model-assisted-m2`
- Baseline: `main` @ `9e1afc9` (PR #20 merged). Do not nest worktrees. Do not commit `uv.lock`.
- After whole-branch review: stop. No push, PR, merge, or OAR Accepted unless Boss asks.
