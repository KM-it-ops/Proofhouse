# MISSION-017 File/API Envelope Producers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file/api envelope producers that emit canonical MISSION-008 artifact mappings and evaluate them with the existing `compile_requirements` engine — without answering open OQs, without simple/developer/prs/prose, without M3/live/IR v0.2, and without claiming CERTIFIED or full Phase 4B exit.

**Architecture:** `produce_requirements(envelope)` assembles canonical artifacts. `compile_requirements_input` dispatches: `requirements_document` present → 016 path; else produce then compile. One rule engine (`evaluate_contract_rules`). No new schema file, no new CLI subcommand, no new dependency.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

**Baseline:** local `main` @ `62a7e1b`. **Branch / worktree (execution time only):** `feature/mission-017-008-file-api-producers` in `C:/AI/projects/PromptRig/.worktrees/mission-017-008-file-api-producers`. Spec: `docs/superpowers/specs/2026-08-21-mission-017-008-file-api-producers-design.md`. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `62a7e1b`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers, no provider SDK/HTTP client.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Do not add profiles.
- Repair budgets remain `{0,1,2}`; `EVR-SEC-0001` unchanged.
- Simple Mode UI-only semantics stay forbidden. M3 is not this mission.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no DFR-003 live-provider path.
- Do **not** resolve OQ-008-001 through OQ-008-009. Unknown answers stay `BLOCKED` / `PARTIAL` / gap evidence.
- Do **not** claim full Roadmap Phase 4B exit. Do **not** graduate Requirements compiler from `PARTIAL`. Do **not** claim a full MISSION-008 production compiler.
- Exactly one rule-engine implementation: do not copy RC-065; do not extend `context_from_artifacts` with text matching; do not stuff `artifacts.diagnostics` to force reason codes.
- `compile_requirements` still requires `requirements_document` for the canonical path.
- Production CLI must never expose `force_*` / test hooks. No new `produce-requirements` command.
- Ponytail-full: no new envelope schema file, no new dependency, fewest files, reuse 008 record shapes.
- OAR-011 is **Ready** until Boss says Accepted. OAR-010 stays Accepted. OAR-009 stays Ready.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest` or `.venv/Scripts/python -m pytest`.
- Do not commit `uv.lock`.

## File structure

- Create: `src/promptrig/compiler/requirements_produce.py` — envelope → artifacts
- Modify: `src/promptrig/compiler/requirements_contract.py` — add `compile_requirements_input`
- Modify: `src/promptrig/compiler/api.py` — lazy-export `produce_requirements`, `compile_requirements_input`
- Modify: `src/promptrig/compiler/cli_compiler.py` — `compile-requirements` calls compose
- Create: `tests/compiler/test_mission_017_schedule.py`, `tests/compiler/test_mission_017_produce.py`
- Create: `architecture/mission-017-certification/README.md`, `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-011.md`, `MISSION_017_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-017-certification/README.md`
- Create: `tests/compiler/test_mission_017_schedule.py`

**Interfaces:**
- Consumes: OAR-010 Accepted; OAR-009 Ready; OQ-008-001–009 still open
- Produces: certification README; schedule test that fails until the README exists

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_mission_017_not_full_008_not_m3_oqs_open() -> None:
    note = Path("architecture/mission-017-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "produce_requirements" in lower
    assert "file" in lower and "api" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "freeform" in lower
    assert "oq-008-001" in lower
    assert "oar-011" in lower
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

Run: `uv run python -m pytest tests/compiler/test_mission_017_schedule.py -v`

Expected: FAIL (`README.md` missing)

- [ ] **Step 3: Write the README**

```markdown
# MISSION-008 File/API Envelope Producers (MISSION-017)

**Status:** OAR-011 Ready for owner acceptance. OAR-010 remains Accepted. OAR-009 remains Ready (not Accepted).
**Baseline:** local `main` @ `62a7e1b`.
**Scope:** `produce_requirements` turns file/api envelopes into canonical MISSION-008 artifact mappings. `compile_requirements` remains the sole rule engine via `compile_requirements_input`. Existing M0/M1/M2 closed-loop profiles unchanged.

This is Campaign COMPILER remaining 008 producers. Historical ambition-gap P2 “MISSION-017 platform SPECs” is not this mission.

## What this mission certifies (narrow)

- File and api authoring envelopes (structured claims/sources, not prose) assemble canonical records.
- Public `produce_requirements` / `compile_requirements_input`; CLI `compile-requirements` dispatches on payload shape.
- Compact `cases.json` remains test-only. This is not an authoring-prose interpreter.

## Non-claims

- Not full MISSION-008 production compiler (no freeform NLP; no Simple/Developer/PRS producers).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- OQ-008-001 through OQ-008-009 remain open; this mission does not invent owner answers.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
- OAR-011 Ready, not Accepted. OAR-009 remains Ready (not Accepted).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/compiler/test_mission_017_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/compiler/test_mission_017_schedule.py architecture/mission-017-certification/README.md
git commit -m "docs: authorize MISSION-017 file/api envelope producers"
```

---

### Task 2: Producer

**Files:**
- Create: `src/promptrig/compiler/requirements_produce.py`
- Test: `tests/compiler/test_mission_017_produce.py`

- [ ] **Step 1: Write failing tests**

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


def _intent(*, mode: str, input_id: str = "INP-017-001") -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str = "SRC-017-001", **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://017", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str = "REQ-017-001", source_id: str = "SRC-017-001", **extra: object) -> dict:
    record = {
        "id": req_id,
        "type": "objective",
        "statement": "Compile from an envelope.",
        "priority": "required",
        "acceptance_state": "accepted",
        "authority_basis": "directly_stated",
        "source_refs": [source_id],
        "acceptance_criteria": ["Engine owns status."],
        "consequential": False,
    }
    record.update(extra)
    return record


def _file_envelope(**extra: object) -> dict:
    envelope = {
        "intent_input": _intent(mode="file"),
        "sources": [_source(kind="file")],
        "claims": [_claim()],
    }
    envelope.update(extra)
    return envelope


def _api_envelope() -> dict:
    return {
        "intent_input": _intent(mode="api", input_id="INP-017-API"),
        "sources": [_source(kind="api_request", source_id="SRC-017-API")],
        "claims": [_claim(req_id="REQ-017-API", source_id="SRC-017-API")],
    }


def test_canonical_payload_matches_direct_compile() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements, compile_requirements_input

    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    assert compile_requirements_input(artifacts).to_dict() == compile_requirements(artifacts).to_dict()


def test_file_envelope_sources_are_file_kind() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input
    from promptrig.compiler.requirements_produce import produce_requirements

    artifacts = produce_requirements(_file_envelope())
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "file"
    result = compile_requirements_input(_file_envelope())
    assert result.command == "compile-requirements"
    assert result.status in {"SUCCESS", "PARTIAL", "BLOCKED", "REFUSED", "INVALID_OUTPUT"}


def test_api_envelope_sources_are_api_request_kind() -> None:
    from promptrig.compiler.requirements_produce import produce_requirements

    artifacts = produce_requirements(_api_envelope())
    assert artifacts["requirements_document"]["sources"][0]["kind"] == "api_request"


def test_simple_developer_prs_are_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    for mode in ("simple", "developer", "prs"):
        envelope = _file_envelope()
        envelope["intent_input"]["authoring_mode"] = mode
        result = compile_requirements_input(envelope)
        assert result.status == "INVALID_OUTPUT"
        assert "RQC-SCH-0001" in result.reason_codes


def test_unknown_top_level_field_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope(prose="not allowed")
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_unknown_contract_version_is_invalid_output() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["intent_input"]["contract_version"] = "9.9.9"
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_file_imports_unsupported_and_path_not_opened(tmp_path: Path) -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input
    from promptrig.compiler.requirements_produce import produce_requirements

    missing = tmp_path / "does-not-exist-017.txt"
    envelope = _file_envelope(imports=[str(missing)])
    artifacts = produce_requirements(envelope)
    statements = [r["statement"] for r in artifacts["requirements_document"]["requirements"]]
    assert str(missing) in statements
    assert any(r["acceptance_state"] == "unsupported" for r in artifacts["requirements_document"]["requirements"])
    result = compile_requirements_input(envelope)
    assert result.status == "BLOCKED"
    assert "RQC-UNS-0001" in result.reason_codes
    assert not missing.exists()


def test_duplicate_source_ids_are_engine_rqc_src_0001() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["sources"] = [_source(kind="file"), _source(kind="file")]
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SRC-0001" in result.reason_codes


def test_model_self_accept_is_not_success() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["claims"] = [_claim(authority_basis="model_suggested")]
    result = compile_requirements_input(envelope)
    assert result.status != "SUCCESS"
    assert "RQC-MDL-0001" in result.reason_codes


def test_digest_ambiguity_records_oq_008_001() -> None:
    from promptrig.compiler.requirements_produce import produce_requirements
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    envelope["sources"] = [_source(kind="file", fragment="Compile from an envelope.")]
    artifacts = produce_requirements(envelope)
    questions = artifacts["requirements_document"]["open_questions"]
    assert any("OQ-008-001" in q.get("text", "") for q in questions)
    claim = next(r for r in artifacts["requirements_document"]["requirements"] if r["id"] == "REQ-017-001")
    assert claim["acceptance_state"] == "unresolved"
    result = compile_requirements_input(envelope)
    assert result.status != "SUCCESS"


def test_harness_still_shares_evaluate_contract_rules() -> None:
    import importlib.util
    from types import ModuleType

    from promptrig.compiler import requirements_contract as rc

    path = ROOT / "architecture" / "requirements-compiler-contract-v0.1" / "validate_contract.py"
    spec = importlib.util.spec_from_file_location("mission008_contract_validator", path)
    assert spec and spec.loader
    module = ModuleType("mission008_contract_validator")
    spec.loader.exec_module(module)
    assert module.evaluate_contract_rules is rc.evaluate_contract_rules
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py -v`

Expected: FAIL (import errors for `produce_requirements` / `compile_requirements_input`)

- [ ] **Step 3: Implement the producer**

Create `src/promptrig/compiler/requirements_produce.py`:

```python
"""MISSION-017: file/api envelope → canonical MISSION-008 artifact mapping.

Does not evaluate RC-065. `compile_requirements` remains the sole rule engine.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

ALLOWED_ENVELOPE_KEYS = frozenset(
    {"intent_input", "sources", "claims", "mappings", "imports", "diagnostics"}
)
ALLOWED_INTENT_KEYS = frozenset(
    {
        "contract_version",
        "input_id",
        "authoring_mode",
        "intent",
        "authoritative_inputs",
        "non_authoritative_inputs",
        "source_ids",
    }
)
REQUIRED_INTENT_KEYS = frozenset(
    {
        "contract_version",
        "input_id",
        "authoring_mode",
        "intent",
        "authoritative_inputs",
        "non_authoritative_inputs",
    }
)
FILE_SOURCE_KINDS = frozenset({"file", "decision", "contract"})
API_SOURCE_KINDS = frozenset({"api_request", "decision", "contract"})
PRODUCER_VAL_DIGEST = hashlib.sha256(b"promptrig-mission-017-producer").hexdigest()
REQUIREMENTS_CONTRACT_VERSION = "0.1.0-draft"


def produce_requirements(envelope: Mapping[str, Any] | object) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        return {}
    if set(envelope) - ALLOWED_ENVELOPE_KEYS:
        return {}
    intent = envelope.get("intent_input")
    if not isinstance(intent, Mapping):
        return {}
    if set(intent) - ALLOWED_INTENT_KEYS or not REQUIRED_INTENT_KEYS <= set(intent):
        return {}
    mode = intent.get("authoring_mode")
    if mode not in {"file", "api"}:
        return {}
    if intent.get("contract_version") != REQUIREMENTS_CONTRACT_VERSION:
        return {}
    sources = envelope.get("sources")
    claims = envelope.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list) or not sources or not claims:
        return {}
    if any(not isinstance(item, Mapping) for item in sources + claims):
        return {}
    allowed_kinds = FILE_SOURCE_KINDS if mode == "file" else API_SOURCE_KINDS
    if any(source.get("kind") not in allowed_kinds for source in sources):
        return {}
    imports = envelope.get("imports")
    if imports is not None:
        if mode != "file" or not isinstance(imports, list) or not all(isinstance(item, str) for item in imports):
            return {}

    source_by_id = {source.get("id"): source for source in sources}
    produced_claims: list[dict[str, Any]] = []
    open_questions: list[dict[str, Any]] = []
    for claim in claims:
        produced = dict(claim)
        if (
            produced.get("acceptance_state") == "accepted"
            and produced.get("authority_basis") == "directly_stated"
        ):
            ambiguous = False
            for ref in produced.get("source_refs") or []:
                source = source_by_id.get(ref)
                if not isinstance(source, Mapping) or source.get("kind") != "file":
                    continue
                if source.get("fragment") and not source.get("sha256") and not source.get("fragment_digest"):
                    ambiguous = True
                    break
            if ambiguous:
                produced["acceptance_state"] = "unresolved"
                rid = str(produced.get("id") or "REQ-UNKNOWN")
                open_questions.append(
                    {
                        "id": f"OQN-{rid}",
                        "text": "OQ-008-001 unanswered: file fragment without digest; fail closed.",
                        "affected_requirement_refs": [rid],
                        "impact": "required",
                        "resolution_state": "unresolved",
                    }
                )
        produced_claims.append(produced)

    first_source_id = str(sources[0].get("id") or "")
    if imports:
        for index, path in enumerate(imports, start=1):
            produced_claims.append(
                {
                    "id": f"REQ-IMP-{index:03d}",
                    "type": "behavior",
                    "statement": path,
                    "priority": "required",
                    "acceptance_state": "unsupported",
                    "authority_basis": "unsupported",
                    "source_refs": [first_source_id],
                    "acceptance_criteria": ["Import is unsupported."],
                    "consequential": False,
                }
            )

    produced_claims.sort(key=lambda item: str(item.get("id") or ""))
    sorted_sources = sorted(sources, key=lambda item: str(item.get("id") or ""))
    input_id = str(intent["input_id"])
    document_id = "RQD-" + input_id.removeprefix("INP-")

    document: dict[str, Any] = {
        "contract_version": REQUIREMENTS_CONTRACT_VERSION,
        "document_id": document_id,
        "input_ref": input_id,
        "requirements": produced_claims,
        "sources": sorted_sources,
        "assumptions": [],
        "open_questions": open_questions,
        "conflicts": [],
        "validations": [
            {
                "id": "VAL-PROD-001",
                "validator_version": "0.1.0",
                "result": "PASS",
                "content_digest": PRODUCER_VAL_DIGEST,
            }
        ],
    }

    mappings = envelope.get("mappings")
    if not isinstance(mappings, list):
        mappings = []
        for claim in produced_claims:
            refs = claim.get("source_refs") or [first_source_id]
            rid = str(claim.get("id") or "")
            mappings.append(
                {
                    "id": f"MAP-{rid.removeprefix('REQ-')}",
                    "requirement_id": rid,
                    "outcome": "unresolved",
                    "authority_ref": {"kind": "source", "ref": str(refs[0])},
                    "validation_ref": "VAL-PROD-001",
                }
            )

    artifacts: dict[str, Any] = {
        "intent_input": dict(intent),
        "requirements_document": document,
        "mappings": mappings,
    }
    if "diagnostics" in envelope:
        artifacts["diagnostics"] = envelope["diagnostics"]
    return artifacts
```

Then add this at the end of `src/promptrig/compiler/requirements_contract.py` (after `compile_requirements`):

```python
def compile_requirements_input(
    payload: Mapping[str, Any] | object,
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult:
    from .requirements_produce import produce_requirements

    if isinstance(payload, Mapping) and "requirements_document" in payload:
        return compile_requirements(payload, registry=registry)
    return compile_requirements(produce_requirements(payload), registry=registry)
```

Keep the producer import inside `compile_requirements_input` only if a top-level import would cycle. Prefer a **top-level** import in `requirements_contract.py`:

```python
from .requirements_produce import produce_requirements
```

at the top of `requirements_contract.py` with the other imports. `requirements_produce.py` must not import `requirements_contract`.

- [ ] **Step 4: Run producer tests**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py -v`

Expected: canonical/file/api/fail-closed tests PASS. CLI parity tests are Task 3 if still failing on lazy export — if `compile_requirements_input` is importable from `requirements_contract`, Task 2 tests above should PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_produce.py src/promptrig/compiler/requirements_contract.py tests/compiler/test_mission_017_produce.py
git commit -m "feat: produce canonical 008 artifacts from file/api envelopes"
```

---

### Task 3: Public API and CLI compose

**Files:**
- Modify: `src/promptrig/compiler/api.py` (lazy exports)
- Modify: `src/promptrig/compiler/cli_compiler.py` (`_cmd_compile_requirements`, help text)
- Modify: `tests/compiler/test_mission_017_produce.py` (add CLI cases)

- [ ] **Step 1: Write failing CLI / lazy-export tests (append to the produce test file)**

```python
def test_api_lazy_export_produce_and_compose() -> None:
    from promptrig.compiler import api as compiler_api
    from promptrig.compiler.requirements_contract import (
        compile_requirements_input as direct_compose,
    )
    from promptrig.compiler.requirements_produce import produce_requirements as direct_produce

    artifacts = _artifacts("LAS-POS-SUCCESS-001")
    assert compiler_api.compile_requirements_input(artifacts).to_dict() == direct_compose(artifacts).to_dict()
    envelope = _file_envelope()
    assert compiler_api.produce_requirements(envelope) == direct_produce(envelope)


def test_cli_file_envelope_json_parity(tmp_path, capsys) -> None:
    from promptrig.compiler.requirements_contract import compile_requirements_input

    envelope = _file_envelope()
    path = tmp_path / "file-envelope.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    code = compiler_main(["compile-requirements", str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    lib = compile_requirements_input(envelope)
    assert payload["status"] == lib.status
    assert payload["reason_codes"] == list(lib.reason_codes)
    assert payload["command"] == "compile-requirements"
    if lib.status in {"SUCCESS", "PARTIAL"}:
        assert code == 0
    elif lib.status == "INVALID_OUTPUT":
        assert code != 0
    else:
        assert code != 0
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py::test_api_lazy_export_produce_and_compose tests/compiler/test_mission_017_produce.py::test_cli_file_envelope_json_parity -v`

Expected: FAIL (`api` has no `produce_requirements` / CLI still calls `compile_requirements` only)

- [ ] **Step 3: Wire lazy export and CLI**

In `src/promptrig/compiler/api.py` replace `_REQUIREMENTS_CONTRACT_EXPORTS` and the getattr branch:

```python
_REQUIREMENTS_CONTRACT_EXPORTS = frozenset(
    {
        "compile_requirements",
        "RequirementsCompileResult",
        "produce_requirements",
        "compile_requirements_input",
    }
)
```

Inside `__getattr__`, replace the requirements-contract branch with:

```python
    if name in _REQUIREMENTS_CONTRACT_EXPORTS:
        from . import requirements_contract
        from . import requirements_produce

        if name == "produce_requirements":
            return requirements_produce.produce_requirements
        return getattr(requirements_contract, name)
```

In `src/promptrig/compiler/cli_compiler.py`:

```python
def _cmd_compile_requirements(args: argparse.Namespace) -> int:
    from .api import compile_requirements_input

    raw = _read_input(args.input)
    payload = json.loads(raw.decode("utf-8"))
    result = compile_requirements_input(payload)
    payload_out = result.to_dict()
    if args.json:
        sys.stdout.write(json.dumps(payload_out, sort_keys=True))
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

Change the subparser help to:

```python
        help="Evaluate canonical MISSION-008 artifact JSON or a file/api envelope (not authoring prose; not closed-loop).",
```

Do not add a `produce-requirements` subcommand.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_016_api.py tests/compiler/test_mission_016_engine.py tests/compiler/test_mission_017_schedule.py -q`

Expected: all PASS (016 CLI still works because canonical payloads have `requirements_document`)

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/api.py src/promptrig/compiler/cli_compiler.py tests/compiler/test_mission_017_produce.py
git commit -m "feat: dispatch compile-requirements through file/api envelope compose"
```

---

### Task 4: Certification docs and OAR-011 Ready

**Files:**
- Create: `MISSION_017_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-011.md`
- Modify: `architecture/mission-017-certification/README.md` (status line stays Ready)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Requirements compiler stays `PARTIAL`)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`
- Modify: `README.md` Status

- [ ] **Step 1: Write OAR-011 Ready**

```markdown
# OAR-011 — MISSION-017 File/API Envelope Producers

**Status:** Ready for owner acceptance.

**Certified if accepted:** file and api envelope producers in `promptrig.compiler.requirements_produce` (`produce_requirements`) assemble canonical MISSION-008 artifact mappings; `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch envelope vs canonical payload; `evaluate_contract_rules` remains the sole RC-065 implementation. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`. OQ-008-001 through OQ-008-009 remain open (fail closed; no invented owner answers). Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, simple/developer/prs/authoring-prose producers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, resolving OQ-008-001 through OQ-008-009. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 remains Ready (not Accepted by this record). OAR-010 remains Accepted.
```

- [ ] **Step 2: Write MISSION_017_REPORT.md** from HEAD evidence (commits, test commands). Include residual gaps matching OAR-011 non-claims. Do not mark OAR-011 Accepted.

- [ ] **Step 3: Maturity / deferred / README**

Requirements compiler evidence: append MISSION-017 `produce_requirements` + `compile_requirements_input` + `test_mission_017_*.py` + OAR-011 Ready. Limitations: file/api envelope assembly only; still not simple/developer/prs/prose; OQs open; compiler stays `PARTIAL`.

Deferred blocking bullet: MISSION-017 added file/api envelope producers for canonical assembly; remaining unauthorized: simple/developer/prs/prose producers; OQs open; no full 008 compiler; no M3.

README Status: add a MISSION-017 sentence after the 016 sentence; keep 016/OAR-009 Ready language; do not unblock M3.

- [ ] **Step 4: Run compiler+evaluation+requirements suite**

Run: `uv run python -m pytest tests/compiler tests/evaluation tests/requirements -q`

Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add MISSION_017_REPORT.md architecture/OWNER_ACCEPTANCE_RECORDS/OAR-011.md architecture/mission-017-certification/README.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md
git commit -m "docs: MISSION-017 report and OAR-011 draft for file/api producers"
```

---

## Spec coverage check

- File/api envelopes → canonical artifacts: Task 2
- `compile_requirements` remains sole engine; compose dispatch: Tasks 2–3
- No new schema / no new CLI command: Tasks 2–3
- Trust-boundary `INVALID_OUTPUT` + `RQC-SCH-0001`: Task 2
- Imports → `RQC-UNS-0001`, no FS: Task 2
- Digest ambiguity → unresolved + `OQ-008-001` text, not SUCCESS: Task 2
- Duplicate IDs / model self-accept copied to engine: Task 2
- 016 canonical byte-stable: Tasks 2–3
- Honesty / PARTIAL / OQs open / OAR-011 Ready / no M3: Tasks 1, 4
- Closed-loop `EVR-RQC-0001` unchanged: do not edit `closed_loop.py`; 016 tests still run in Task 4 suite

## Pre-flight (plan vs review rubric)

- Reviewer flags “full 008 compiler” or CERTIFIED as a defect — Tasks 1 and 4 keep residual disclosure. Governs.
- Reviewer flags stuffing diagnostics to force codes — spec audit forbids it; Task 2 copies records. Governs.
- Reviewer flags `RQC-UNS-0002` on canonical path — spec requires `RQC-UNS-0001`. Governs.
- Open questions do not change RC-065; digest case also unresolves the claim. Governs.
- Do not edit `evaluate_contract_rules` / `context_from_artifacts` unless a test proves a 016 regression. Governs.

## Worktree / stacking

- Branch: `feature/mission-017-008-file-api-producers`
- Worktree: `.worktrees/mission-017-008-file-api-producers`
- Baseline: local `main` @ `62a7e1b`
- After whole-branch review: stop. No push, PR, merge, or OAR-011 Accepted unless Boss asks.
