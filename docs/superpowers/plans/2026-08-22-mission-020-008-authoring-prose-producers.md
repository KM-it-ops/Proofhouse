# MISSION-020 Authoring-Prose Producers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dispatch `{profile: plain_language_v0, text}` on `compile_requirements_input` through the existing MISSION-013 parser, lower mechanically into canonical MISSION-008 artifacts, and evaluate with `compile_requirements` — without freeform NLP, without a sixth envelope mode, without implementing OQ policies, and without claiming CERTIFIED or full Phase 4B exit.

**Architecture:** Third compose branch in `compile_requirements_input`: exact-key `plain_language_v0` text envelope → parse → `produce_plain_language_requirements` → `compile_requirements`. Goal maps `direct` to `/objective/goal`; numbered and constraint records get `unresolved` mappings. Parse errors return `BLOCKED` + `PL-PARSE-*`. Envelope producers and closed-loop stay unchanged. One rule engine.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

**Baseline:** local `main` @ `af40a53` (OAR-013 Accepted; OQ-008-001–010 policy only). **Branch / worktree (execution time only):** `feature/mission-020-authoring-prose-producers` in `C:/AI/projects/PromptRig/.worktrees/mission-020-authoring-prose-producers`. Spec: `docs/superpowers/specs/2026-08-22-mission-020-008-authoring-prose-producers-design.md`. Do not edit the `main` checkout during SDD.

## Global Constraints

- Baseline: `af40a53`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- M3 / Simple Mode UI forbidden.
- Reuse `parse_plain_language_v0`. Do not add a new grammar or freeform NLP interpreter.
- Do not add `authoring_mode=plain_language` or any sixth envelope mode. Synthesized `intent_input.authoring_mode` is `simple` (schema enum only).
- RCD-008-009 / PRS language disposition remains **DEFERRED**.
- Do **not** implement OQ-008-001 through OQ-008-010 in the engine or this lowerer.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler.
- Exactly one rule-engine implementation (`evaluate_contract_rules`).
- No new schema file, dependency, or `produce-requirements` / `produce-plain-language` CLI command.
- Prose compile payload keys are exactly `{profile, text}`. Extra keys are not this dispatcher.
- Goal mapping is `direct` → `/objective/goal`. Numbered and constraint mappings are `unresolved` with no `target_pointer`. Do not guess IR leaves. Valid grammar therefore yields `BLOCKED` / `RQC-BLK-0001`, never invented `SUCCESS`.
- Parse failures return `BLOCKED` + `PL-PARSE-*` from compose; do not emit those codes as 008 artifact diagnostics.
- Keep envelope digest `promptrig-mission-017-producer`. Plain producer digest is `sha256(b"promptrig-mission-020-plain-producer")`.
- OAR-014 is **Ready** until Boss says Accepted. OAR-013/012/011/010 Accepted. OAR-009 Ready.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run python -m pytest`. Do not commit `uv.lock`.

## File structure

- Create: `src/promptrig/compiler/requirements_plain_produce.py`
- Modify: `src/promptrig/compiler/requirements_contract.py` — third dispatch in `compile_requirements_input`
- Modify: `src/promptrig/compiler/api.py` — lazy-export `produce_plain_language_requirements`
- Modify: `src/promptrig/compiler/cli_compiler.py` — help names `plain_language_v0` text envelope
- Modify: `tests/compiler/test_mission_017_produce.py` — exact help string
- Modify: `tests/compiler/test_mission_019_produce.py` — exact help string
- Create: `tests/compiler/test_mission_020_schedule.py`, `tests/compiler/test_mission_020_produce.py`
- Create: `architecture/mission-020-certification/README.md`, `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-014.md`, `MISSION_020_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`, `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (non-authorization closing sentence only)

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-020-certification/README.md`
- Create: `tests/compiler/test_mission_020_schedule.py`

**Interfaces:**
- Consumes: OAR-013 Accepted; OAR-009 Ready; OQs owner-resolved policy only; PRS language DEFERRED
- Produces: certification README; schedule test

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_020_schedule.py`:

```python
from pathlib import Path


def test_mission_020_constrained_prose_not_full_008_not_m3_oqs_policy_only() -> None:
    note = Path("architecture/mission-020-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "plain_language_v0" in lower
    assert "compile_requirements" in lower or "compile-requirements" in lower
    assert "canonical" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "constrained" in lower
    assert "oq-008-001" in lower
    assert "oar-014" in lower
    assert "policy" in lower
    assert "phase 4b" in lower
    assert "blocked" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "RESOLVED" in oq
    assert "authorize no production implementation" in oq.lower() or "policy only" in oq.lower()
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/compiler/test_mission_020_schedule.py -v`

Expected: FAIL because `architecture/mission-020-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-020-certification/README.md`:

```markdown
# MISSION-008 Authoring-Prose Producers (MISSION-020)

**Status:** OAR-014 Ready for owner acceptance. OAR-013, OAR-012, OAR-011, and OAR-010 remain Accepted. OAR-009 remains Ready (not Accepted).
**Baseline:** local `main` @ `af40a53`.
**Scope:** Dispatch exact-key `plain_language_v0` text envelopes on `compile_requirements_input` / `promptrig-compiler compile-requirements` through existing `parse_plain_language_v0`, lower into canonical MISSION-008 artifacts via `produce_plain_language_requirements`, and evaluate with `compile_requirements`. File/api/simple/developer/prs envelope producers remain unchanged. Closed-loop `plain_language_v0` intake remains unchanged.

This is Campaign COMPILER remaining 008 authoring-prose producers. Constrained interpreter, not another envelope.

## What this mission certifies (narrow)

- Constrained `plain_language_v0` `{profile, text}` payloads assemble canonical records.
- Public `produce_plain_language_requirements` / `compile_requirements_input`; CLI `compile-requirements` dispatches canonical vs prose vs envelope.
- Goal maps `direct` to `/objective/goal`; numbered and constraint records are `unresolved` mappings. Valid grammar is BLOCKED (`RQC-BLK-0001`), not invented SUCCESS.
- Parse failures are BLOCKED with `PL-PARSE-*`. Extra keys are not this dispatcher.
- Compact `cases.json` remains test-only. This does not interpret compact `input.intent` strings.

## Non-claims

- Not full MISSION-008 production compiler (OQ-008-001 through OQ-008-010 remain owner-resolved policy only; not implemented).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion. Constrained `plain_language_v0` only.
- PRS **language** (grammar, parser, CONTRACT_CANDIDATE) remains DEFERRED per `PRS_DISPOSITION.md`.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
- OAR-014 Ready (not Accepted). OAR-013, OAR-012, OAR-011, and OAR-010 Accepted. OAR-009 remains Ready (not Accepted).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/compiler/test_mission_020_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/compiler/test_mission_020_schedule.py architecture/mission-020-certification/README.md
git commit -m "test: add MISSION-020 honesty schedule for authoring-prose producers"
```

---

### Task 2: Plain-language lowerer + compose dispatch

**Files:**
- Create: `src/promptrig/compiler/requirements_plain_produce.py`
- Modify: `src/promptrig/compiler/requirements_contract.py` (`compile_requirements_input` only)
- Modify: `src/promptrig/compiler/api.py`
- Create: `tests/compiler/test_mission_020_produce.py`

**Interfaces:**
- Consumes: `parse_plain_language_v0`, `PlainLanguageParseError`, `REQUIREMENTS_CONTRACT_VERSION`, `compile_requirements`
- Produces: `is_plain_language_compile_payload(payload: object) -> bool`; `produce_plain_language_requirements(text: str) -> dict[str, Any]` (raises `PlainLanguageParseError`); compose returns `RequirementsCompileResult`

- [ ] **Step 1: Write the failing tests**

Create `tests/compiler/test_mission_020_produce.py`:

```python
from __future__ import annotations

from pathlib import Path

from promptrig.compiler.requirements_contract import compile_requirements_input

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"


def _plain_payload(text: str | None = None) -> dict:
    return {
        "profile": "plain_language_v0",
        "text": FIXTURE.read_text(encoding="utf-8") if text is None else text,
    }


def test_valid_grammar_is_blocked_not_invalid_or_success() -> None:
    from promptrig.compiler.requirements_plain_produce import produce_plain_language_requirements

    artifacts = produce_plain_language_requirements(FIXTURE.read_text(encoding="utf-8"))
    document = artifacts["requirements_document"]
    ids = {item["id"] for item in document["requirements"]}
    assert "REQ-PL-GOAL" in ids
    assert "REQ-PL-001" in ids
    assert "REQ-PL-C001" in ids
    goal_map = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-GOAL")
    assert goal_map["outcome"] == "direct"
    assert goal_map["target_pointer"] == "/objective/goal"
    numbered = next(item for item in artifacts["mappings"] if item["requirement_id"] == "REQ-PL-001")
    assert numbered["outcome"] == "unresolved"
    assert "target_pointer" not in numbered
    result = compile_requirements_input(_plain_payload())
    assert result.status == "BLOCKED"
    assert "RQC-BLK-0001" in result.reason_codes


def test_freeform_text_is_parse_blocked() -> None:
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": "Please build a helpful assistant that does stuff."}
    )
    assert result.status == "BLOCKED"
    assert "PL-PARSE-0001" in result.reason_codes


def test_extra_keys_are_schema_invalid() -> None:
    payload = _plain_payload()
    payload["repair_budget"] = 1
    result = compile_requirements_input(payload)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes


def test_prs_envelope_still_compiles() -> None:
    envelope = {
        "intent_input": {
            "contract_version": "0.1.0-draft",
            "input_id": "INP-020-PRS",
            "authoring_mode": "prs",
            "intent": "Compile from an envelope.",
            "authoritative_inputs": ["prs:envelope"],
            "non_authoritative_inputs": [],
        },
        "sources": [
            {
                "id": "SRC-020-PRS",
                "kind": "prs",
                "lifecycle": "current",
                "authority_claim": "Envelope supplied the objective.",
                "location": {"uri": "prs://020", "json_pointer": "/claims/0"},
            }
        ],
        "claims": [
            {
                "id": "REQ-020-PRS",
                "type": "objective",
                "statement": "Compile from an envelope.",
                "priority": "required",
                "acceptance_state": "accepted",
                "authority_basis": "directly_stated",
                "source_refs": ["SRC-020-PRS"],
                "acceptance_criteria": ["Engine owns status."],
                "consequential": False,
            }
        ],
    }
    result = compile_requirements_input(envelope)
    assert result.status != "INVALID_OUTPUT"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_020_produce.py -v`

Expected: FAIL (module `requirements_plain_produce` missing and/or compose does not dispatch prose).

- [ ] **Step 3: Write the lowerer**

Create `src/promptrig/compiler/requirements_plain_produce.py` with this exact module:

```python
"""MISSION-020: plain_language_v0 text → canonical MISSION-008 artifact mapping.

Does not evaluate RC-065. `compile_requirements` remains the sole rule engine.
Does not interpret freeform NLP. Parser failures stay PL-PARSE-*.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .plain_language import parse_plain_language_v0
from .requirements_contract import REQUIREMENTS_CONTRACT_VERSION

PLAIN_LANGUAGE_PROFILE = "plain_language_v0"
PLAIN_LANGUAGE_COMPILE_KEYS = frozenset({"profile", "text"})
PLAIN_PRODUCER_VAL_DIGEST = hashlib.sha256(b"promptrig-mission-020-plain-producer").hexdigest()


def is_plain_language_compile_payload(payload: object) -> bool:
    return (
        isinstance(payload, Mapping)
        and set(payload) == PLAIN_LANGUAGE_COMPILE_KEYS
        and payload.get("profile") == PLAIN_LANGUAGE_PROFILE
        and isinstance(payload.get("text"), str)
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source(*, source_id: str, fragment: str, pointer: str) -> dict[str, Any]:
    digest = _digest(fragment)
    return {
        "id": source_id,
        "kind": "ordinary_language",
        "lifecycle": "current",
        "authority_claim": "plain_language_v0 source fragment.",
        "location": {"uri": "plain-language://v0", "json_pointer": pointer},
        "fragment": fragment,
        "fragment_digest": digest,
    }


def _requirement(
    *,
    req_id: str,
    req_type: str,
    statement: str,
    source_id: str,
) -> dict[str, Any]:
    digest = _digest(statement)
    return {
        "id": req_id,
        "type": req_type,
        "statement": statement,
        "priority": "required",
        "acceptance_state": "accepted",
        "authority_basis": "directly_stated",
        "source_refs": [source_id],
        "acceptance_criteria": ["Statement matches preserved source fragment."],
        "consequential": False,
        "statement_digest": digest,
    }


def _mapping(
    *,
    map_id: str,
    requirement_id: str,
    source_id: str,
    outcome: str,
    target_pointer: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": map_id,
        "requirement_id": requirement_id,
        "outcome": outcome,
        "authority_ref": {"kind": "source", "ref": source_id},
        "validation_ref": "VAL-PL-001",
    }
    if target_pointer is not None:
        record["target_pointer"] = target_pointer
    return record


def produce_plain_language_requirements(text: str) -> dict[str, Any]:
    """Parse constrained prose and lower to canonical 008 artifacts.

    Raises PlainLanguageParseError on grammar failure.
    """
    parsed = parse_plain_language_v0(text)
    suffix = _digest(text)[:12].upper()
    input_id = f"INP-PL-{suffix}"
    document_id = f"RQD-PL-{suffix}"
    goal = str(parsed["objective"]["goal"])

    sources: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []

    sources.append(_source(source_id="SRC-PL-GOAL", fragment=goal, pointer="/text"))
    requirements.append(
        _requirement(
            req_id="REQ-PL-GOAL",
            req_type="objective",
            statement=goal,
            source_id="SRC-PL-GOAL",
        )
    )
    mappings.append(
        _mapping(
            map_id="MAP-PL-GOAL",
            requirement_id="REQ-PL-GOAL",
            source_id="SRC-PL-GOAL",
            outcome="direct",
            target_pointer="/objective/goal",
        )
    )

    for item in parsed["requirements"]:
        rid = str(item["id"])
        statement = str(item["statement"])
        token = rid.removeprefix("REQ-")
        src_id = f"SRC-{token}"
        sources.append(_source(source_id=src_id, fragment=statement, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="behavior", statement=statement, source_id=src_id)
        )
        mappings.append(
            _mapping(map_id=f"MAP-{token}", requirement_id=rid, source_id=src_id, outcome="unresolved")
        )

    constraints = list(parsed.get("behavior", {}).get("constraints") or [])
    for index, constraint in enumerate(constraints, start=1):
        rid = f"REQ-PL-C{index:03d}"
        src_id = f"SRC-PL-C{index:03d}"
        sources.append(_source(source_id=src_id, fragment=constraint, pointer="/text"))
        requirements.append(
            _requirement(req_id=rid, req_type="constraint", statement=constraint, source_id=src_id)
        )
        mappings.append(
            _mapping(
                map_id=f"MAP-PL-C{index:03d}",
                requirement_id=rid,
                source_id=src_id,
                outcome="unresolved",
            )
        )

    requirements.sort(key=lambda item: str(item.get("id") or ""))
    sources.sort(key=lambda item: str(item.get("id") or ""))
    mappings.sort(key=lambda item: str(item.get("id") or ""))

    document = {
        "contract_version": REQUIREMENTS_CONTRACT_VERSION,
        "document_id": document_id,
        "input_ref": input_id,
        "requirements": requirements,
        "sources": sources,
        "assumptions": [],
        "open_questions": [],
        "conflicts": [],
        "validations": [
            {
                "id": "VAL-PL-001",
                "validator_version": "0.1.0",
                "result": "PASS",
                "content_digest": PLAIN_PRODUCER_VAL_DIGEST,
            }
        ],
    }
    return {
        "intent_input": {
            "contract_version": REQUIREMENTS_CONTRACT_VERSION,
            "input_id": input_id,
            "authoring_mode": "simple",
            "intent": goal,
            "authoritative_inputs": ["user:intent"],
            "non_authoritative_inputs": [],
        },
        "requirements_document": document,
        "mappings": mappings,
    }
```

Replace `compile_requirements_input` in `src/promptrig/compiler/requirements_contract.py` with:

```python
def compile_requirements_input(
    payload: Mapping[str, Any] | object,
    *,
    registry: Mapping[str, Any] | None = None,
) -> RequirementsCompileResult:
    if isinstance(payload, Mapping) and "requirements_document" in payload:
        return compile_requirements(payload, registry=registry)
    from .plain_language import PlainLanguageParseError
    from .requirements_plain_produce import (
        is_plain_language_compile_payload,
        produce_plain_language_requirements,
    )
    from .requirements_produce import produce_requirements

    if is_plain_language_compile_payload(payload):
        try:
            artifacts = produce_plain_language_requirements(str(payload["text"]))
        except PlainLanguageParseError as exc:
            return RequirementsCompileResult(
                status="BLOCKED",
                reason_codes=(exc.code,),
                contract_version=REQUIREMENTS_CONTRACT_VERSION,
            )
        return compile_requirements(artifacts, registry=registry)
    return compile_requirements(produce_requirements(payload), registry=registry)
```

In `src/promptrig/compiler/api.py`, add `"produce_plain_language_requirements"` to `_REQUIREMENTS_CONTRACT_EXPORTS` and resolve it from `requirements_plain_produce`:

```python
_REQUIREMENTS_CONTRACT_EXPORTS = frozenset(
    {
        "compile_requirements",
        "RequirementsCompileResult",
        "produce_requirements",
        "compile_requirements_input",
        "produce_plain_language_requirements",
    }
)
```

Inside `__getattr__` for `_REQUIREMENTS_CONTRACT_EXPORTS`:

```python
        from . import requirements_contract
        from . import requirements_plain_produce
        from . import requirements_produce

        if name == "produce_requirements":
            return requirements_produce.produce_requirements
        if name == "produce_plain_language_requirements":
            return requirements_plain_produce.produce_plain_language_requirements
        return getattr(requirements_contract, name)
```

- [ ] **Step 4: Run**

`uv run python -m pytest tests/compiler/test_mission_020_produce.py tests/compiler/test_mission_020_schedule.py tests/compiler/test_mission_019_produce.py tests/compiler/test_mission_018_produce.py tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_016_engine.py tests/compiler/test_plain_language_closed_loop.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_plain_produce.py src/promptrig/compiler/requirements_contract.py src/promptrig/compiler/api.py tests/compiler/test_mission_020_produce.py
git commit -m "feat: produce plain_language_v0 text into canonical 008 artifacts"
```

---

### Task 3: CLI help + OAR-014 Ready + honesty docs

**Files:**
- Modify: `src/promptrig/compiler/cli_compiler.py`
- Modify: `tests/compiler/test_mission_017_produce.py`, `tests/compiler/test_mission_019_produce.py`, `tests/compiler/test_mission_020_produce.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-014.md`
- Create: `MISSION_020_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (closing non-authorization sentence only)

**Interfaces:**
- Consumes: Task 2 compose/lowerer
- Produces: CLI help naming `plain_language_v0`; OAR-014 Ready; PARTIAL maturity evidence; report

- [ ] **Step 1: Failing CLI help test**

Append to `tests/compiler/test_mission_020_produce.py`:

```python
def test_compile_requirements_input_help_names_plain_language() -> None:
    from promptrig.compiler.cli_compiler import build_parser

    parser = build_parser()
    req = None
    for action in parser._subparsers._group_actions:
        req = action.choices.get("compile-requirements")
        if req is not None:
            break
    assert req is not None
    help_text = req.format_help()
    assert "plain_language_v0" in help_text
    input_action = next(a for a in req._actions if getattr(a, "dest", None) == "input")
    assert input_action.help == (
        "Path to canonical artifact JSON, file/api/simple/developer/prs envelope, "
        "or plain_language_v0 text envelope, or '-' for stdin."
    )
```

Update the exact help assertions in `tests/compiler/test_mission_017_produce.py` and `tests/compiler/test_mission_019_produce.py` to the same `input_action.help` string. Keep asserting `file/api/simple/developer/prs` appears in `format_help()`.

- [ ] **Step 2: Update CLI help**

In `src/promptrig/compiler/cli_compiler.py` set compile-requirements `help` to:

```python
            "Evaluate canonical MISSION-008 artifact JSON, a file/api/simple/developer/prs "
            "envelope, or a plain_language_v0 text envelope (constrained prose; not freeform NLP; "
            "not closed-loop)."
```

and the positional `input` help to:

```python
            "Path to canonical artifact JSON, file/api/simple/developer/prs envelope, "
            "or plain_language_v0 text envelope, or '-' for stdin."
```

- [ ] **Step 3: Write OAR-014 Ready** (not Accepted)

Create `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-014.md`:

```markdown
# OAR-014 — MISSION-020 Authoring-Prose Producers

**Status:** Ready for owner acceptance.

**Certified if accepted:** constrained `plain_language_v0` text envelopes (`{profile, text}`) parse via existing `parse_plain_language_v0` and lower through `produce_plain_language_requirements` into canonical MISSION-008 artifact mappings; `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch canonical vs prose vs file/api/simple/developer/prs envelope; `evaluate_contract_rules` remains the sole RC-065 implementation. Goal maps `direct` to `/objective/goal`; numbered and constraint records remain unresolved mappings, so valid grammar is BLOCKED rather than invented SUCCESS. Compact `cases.json` remains test-only. Existing M0/M1/M2 closed-loop profiles unchanged; canonical 008 payloads on `closed-loop` still return `EVR-RQC-0001`. OQ-008-001 through OQ-008-010 remain owner-resolved policy only (not implemented; engine/producer fail-closed). Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language** (grammar, parser, CONTRACT_CANDIDATE) per `PRS_DISPOSITION.md` (RCD-008-009 remains DEFERRED), full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST, implementing OQ-008-001 through OQ-008-010. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 remains Ready (not Accepted by this record). OAR-010, OAR-011, OAR-012, and OAR-013 remain Accepted.
```

Do not Accept OAR-014 in this task.

- [ ] **Step 4: Maturity / deferred / README / OPEN_QUESTIONS / report**

Requirements compiler stays **PARTIAL**. Evidence: append MISSION-020 constrained prose lowerer (`requirements_plain_produce.py`, `test_mission_020_*.py`, OAR-014 Ready). Limitations: still not full 008 compiler; OQs policy-only unimplemented; PRS language DEFERRED; prose-only input is BLOCKED not SUCCESS; no M3.

`DEFERRED_AND_REJECTED_WORK.md` Blocking bullets: authoring-prose constrained `plain_language_v0` lowerer landed (OAR-014 Ready); remaining unauthorized: OQ implementation, full 008 compiler, M3, freeform NLP.

`README.md` Status: add a MISSION-020 paragraph matching 019 style; OAR-014 Ready; still PARTIAL; still no full 008 / M3 / freeform / Phase 4B exit.

`OPEN_QUESTIONS.md` closing paragraph: drop “Authoring-prose producers” from the unauthorized list; keep M3, live providers, full 008 compiler, CERTIFIED, Phase 4B exit, and “resolutions do not authorize implementation.”

Write `MISSION_020_REPORT.md` with baseline `af40a53`; tasks 1–3; tests added; explicit non-claims matching OAR-014; HEAD left as the Task 3 commit SHA (implementer fills after commit, or a follow-up docs SHA if needed). Do not claim CERTIFIED or full Phase 4B.

- [ ] **Step 5: Suite**

`uv run python -m pytest tests/compiler tests/evaluation tests/requirements -q`

Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add src/promptrig/compiler/cli_compiler.py tests/compiler/test_mission_017_produce.py tests/compiler/test_mission_019_produce.py tests/compiler/test_mission_020_produce.py architecture/OWNER_ACCEPTANCE_RECORDS/OAR-014.md MISSION_020_REPORT.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md
git commit -m "docs: MISSION-020 report and OAR-014 draft for authoring-prose producers"
```

---

## Spec coverage check

- Exact-key `{profile, text}` dispatch: Task 2
- Parse `PL-PARSE-*` BLOCKED: Task 2
- Goal `direct` / numbered+constraint `unresolved` / BLOCKED not SUCCESS: Task 2
- Extra keys INVALID_OUTPUT: Task 2
- Envelope + closed-loop unchanged: Task 2 suite
- CLI help names `plain_language_v0`: Task 3
- Honesty / PARTIAL / OAR-014 Ready / no M3 / OQs unimplemented / no freeform: Tasks 1, 3
- No new schema / CLI subcommand / sixth envelope / OQ engine: Tasks 2–3
