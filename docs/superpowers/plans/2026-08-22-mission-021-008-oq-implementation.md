# MISSION-021 OQ-008-001/002/006 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement owner-resolved OQ-008-001, OQ-008-002, and OQ-008-006 in the existing sole `evaluate_contract_rules` engine and file-envelope producer — without a second engine, without inventing IR leaves, and without claiming CERTIFIED or full Phase 4B exit.

**Architecture:** Producer file-digest gate stays fail-closed but is named as implemented OQ-008-001 (not “unanswered”). Engine Class 6f/6j skip BLOCKED when every remaining gap is `priority=optional`, and Class 7 returns PARTIAL with evidence. Class 8 SUCCESS may carry emitted advisory codes whose registry `semantic` is exactly `false`. `RQC-SRC-0005` stays semantic PARTIAL.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`.

## Global Constraints

- Baseline: `ca888a8`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only during SDD: `C:/AI/projects/PromptRig/.worktrees/mission-021-oq-implementation` on `feature/mission-021-oq-implementation`. Do not edit the `main` checkout.
- Spec: `docs/superpowers/specs/2026-08-22-mission-021-008-oq-implementation-design.md`.
- Offline certified path: `network_allowed=false`, no credentials, no live providers.
- Repair budgets `{0,1,2}`; `EVR-SEC-0001` unchanged.
- M3 / Simple Mode UI forbidden. No freeform NLP. No PRS language/grammar.
- Do **not** implement OQ-008-003, 004, 005, 007, 008, 009, or 010.
- Do **not** map MISSION-020 numbered/constraint records to IR. Valid constrained prose stays `BLOCKED` / `RQC-BLK-0001`.
- Exactly one rule-engine implementation (`evaluate_contract_rules`).
- Never hash missing file bytes. Never invent digests for ephemeral sources.
- Security/privacy Class 5 fail-closed is unchanged even if `priority=optional`.
- Registry: missing `semantic` means `true`. `RQC-SRC-0005` stays PARTIAL.
- OAR-015 is **Ready** until Boss says Accepted. OAR-009 through OAR-014 Accepted.
- Do **not** claim full Phase 4B exit, CERTIFIED compiler, or full MISSION-008 production compiler.
- Commit after each task; do not push unless Boss asks. Never push `origin/main`.
- Prefer `uv run python -m pytest`. Do not commit `uv.lock`.

## File structure

- Create: `architecture/mission-021-certification/README.md`
- Create: `tests/compiler/test_mission_021_schedule.py`
- Create: `tests/compiler/test_mission_021_oq.py`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-015.md`
- Create: `MISSION_021_REPORT.md`
- Modify: `src/promptrig/compiler/requirements_produce.py` (OQ-008-001 wording)
- Modify: `src/promptrig/compiler/requirements_contract.py` (6f/6j/Class 7/Class 8; module docstring)
- Modify: `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json`
- Modify: `src/promptrig/compiler/schemas/requirements_diagnostic_registry.json` (byte-identical twin)
- Modify: `architecture/requirements-compiler-contract-v0.1/validate_contract.py`
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (closing non-authorization sentence)
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`

---

### Task 1: Honesty / schedule

**Files:**
- Create: `architecture/mission-021-certification/README.md`
- Create: `tests/compiler/test_mission_021_schedule.py`

**Interfaces:**
- Consumes: OAR-009 through OAR-014 Accepted; OQ-008-001/002/006 authorized for this campaign only
- Produces: certification README; schedule test

- [ ] **Step 1: Write the failing test**

Create `tests/compiler/test_mission_021_schedule.py`:

```python
from pathlib import Path


def test_mission_021_implements_oq_001_002_006_not_full_008_not_m3() -> None:
    note = Path("architecture/mission-021-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "oq-008-001" in lower
    assert "oq-008-002" in lower
    assert "oq-008-006" in lower
    assert "partial" in lower
    assert "not full" in lower
    assert "mission-008" in lower or "008" in text
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "not freeform" in lower or "no freeform" in lower
    assert "oar-015" in lower
    assert "blocked" in lower
    assert "rqc-blk-0001" in lower
    assert "phase 4b" in lower
    oq = Path("architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md").read_text(
        encoding="utf-8"
    )
    assert "OQ-008-003" in oq
    maturity = Path("architecture/strategy/CAPABILITY_MATURITY_MAP.md").read_text(encoding="utf-8")
    assert "| Requirements compiler | `PARTIAL`" in maturity
    disposition = Path(
        "architecture/requirements-compiler-contract-v0.1/PRS_DISPOSITION.md"
    ).read_text(encoding="utf-8")
    assert "DEFERRED" in disposition
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/compiler/test_mission_021_schedule.py -v`

Expected: FAIL because `architecture/mission-021-certification/README.md` does not exist.

- [ ] **Step 3: Write the certification README**

Create `architecture/mission-021-certification/README.md`:

```markdown
# MISSION-008 OQ-008-001/002/006 Implementation (MISSION-021)

**Status:** OAR-015 Ready for owner acceptance. OAR-014 through OAR-009 remain Accepted.
**Baseline:** local `main` @ `ca888a8`.
**Scope:** Implement owner-resolved OQ-008-001 (file digest when stable bytes exist), OQ-008-002 (optional unresolved meaning → PARTIAL with evidence), and OQ-008-006 (SUCCESS may carry advisory non-semantic diagnostics) in the existing `evaluate_contract_rules` engine and file-envelope producer.

This is Campaign COMPILER remaining 008 policy implementation. Not a full production compiler.

## What this mission certifies (narrow)

- OQ-008-001: file sources without `sha256` and without `fragment_digest` remain fail-closed; the OQN text names the implemented policy (not “unanswered”).
- OQ-008-002: optional accepted unmapped meaning and optional `no_ir_representation` become PARTIAL with evidence; required gaps stay BLOCKED (`RQC-BLK-0001`).
- OQ-008-006: SUCCESS may include emitted advisory codes with registry `semantic: false` (`RQC-ADV-0001`). `RQC-SRC-0005` remains PARTIAL.
- Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`); numbered/constraint mappings stay unresolved.

## Non-claims

- Not full MISSION-008 production compiler (OQ-008-003 through OQ-008-005 and OQ-008-007 through OQ-008-010 remain unimplemented).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- PRS **language** (grammar, parser, CONTRACT_CANDIDATE) remains DEFERRED per `PRS_DISPOSITION.md`.
- Requirements compiler maturity remains PARTIAL.
- OAR-015 Ready (not Accepted). OAR-014 through OAR-009 Accepted.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/compiler/test_mission_021_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add tests/compiler/test_mission_021_schedule.py architecture/mission-021-certification/README.md
git commit -m "test: add MISSION-021 honesty schedule for OQ-008-001/002/006"
```

---

### Task 2: OQ-008-001 file digest policy wording

**Files:**
- Modify: `src/promptrig/compiler/requirements_produce.py`
- Create: `tests/compiler/test_mission_021_oq.py` (001 tests only in this task)
- Test: `tests/compiler/test_mission_017_produce.py` (must still pass; it only requires `OQ-008-001` in OQN text)

**Interfaces:**
- Consumes: existing file-envelope digest gate
- Produces: implemented-policy OQN text; same BLOCKED / INVALID_OUTPUT outcomes

- [ ] **Step 1: Write the failing tests**

Append to `tests/compiler/test_mission_021_oq.py`:

```python
from __future__ import annotations

from promptrig.compiler.requirements_contract import compile_requirements_input
from promptrig.compiler.requirements_produce import produce_requirements


def _intent(*, mode: str, input_id: str) -> dict:
    return {
        "contract_version": "0.1.0-draft",
        "input_id": input_id,
        "authoring_mode": mode,
        "intent": "Compile from an envelope.",
        "authoritative_inputs": [f"{mode}:envelope"],
        "non_authoritative_inputs": [],
    }


def _source(*, kind: str, source_id: str, **extra: object) -> dict:
    record = {
        "id": source_id,
        "kind": kind,
        "lifecycle": "current",
        "authority_claim": "Envelope supplied the objective.",
        "location": {"uri": f"{kind}://021", "json_pointer": "/claims/0"},
    }
    record.update(extra)
    return record


def _claim(*, req_id: str, source_id: str, **extra: object) -> dict:
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


def test_oq_008_001_file_without_digest_is_blocked_not_unanswered() -> None:
    envelope = {
        "intent_input": _intent(mode="file", input_id="INP-021-001"),
        "sources": [_source(kind="file", source_id="SRC-021-001")],
        "claims": [_claim(req_id="REQ-021-001", source_id="SRC-021-001")],
    }
    artifacts = produce_requirements(envelope)
    questions = artifacts["requirements_document"]["open_questions"]
    assert questions
    text = questions[0]["text"]
    assert "OQ-008-001" in text
    assert "unanswered" not in text.lower()
    claim = next(
        item
        for item in artifacts["requirements_document"]["requirements"]
        if item["id"] == "REQ-021-001"
    )
    assert claim["acceptance_state"] == "unresolved"
    result = compile_requirements_input(envelope)
    assert result.status == "BLOCKED"
    assert result.reason_codes == ("RQC-AMB-0001",)


def test_oq_008_001_fragment_without_digest_stays_invalid() -> None:
    envelope = {
        "intent_input": _intent(mode="file", input_id="INP-021-002"),
        "sources": [
            _source(kind="file", source_id="SRC-021-002", fragment="Compile from an envelope.")
        ],
        "claims": [_claim(req_id="REQ-021-002", source_id="SRC-021-002")],
    }
    assert produce_requirements(envelope) == {}
    result = compile_requirements_input(envelope)
    assert result.status == "INVALID_OUTPUT"
    assert "RQC-SCH-0001" in result.reason_codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py::test_oq_008_001_file_without_digest_is_blocked_not_unanswered -v`

Expected: FAIL because OQN text still contains `unanswered`.

- [ ] **Step 3: Change only the OQN text**

In `src/promptrig/compiler/requirements_produce.py`, replace the open-question `text` value with:

`OQ-008-001: file source with stable bytes missing digest; fail closed.`

Do not change the demotion logic, kinds checked, or status codes. Do not hash missing bytes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py tests/compiler/test_mission_017_produce.py::test_digest_ambiguity_records_oq_008_001 -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_produce.py tests/compiler/test_mission_021_oq.py
git commit -m "feat: name OQ-008-001 file digest fail-closed as implemented policy"
```

---

### Task 3: OQ-008-002 optional unresolved meaning is PARTIAL

**Files:**
- Modify: `src/promptrig/compiler/requirements_contract.py` (`evaluate_contract_rules` Class 6f, 6j, Class 7)
- Modify: `tests/compiler/test_mission_021_oq.py` (add 002 tests)

**Interfaces:**
- Consumes: `evaluate_contract_rules`, `compile_requirements_input`, developer envelopes
- Produces: optional unmapped / optional `no_ir_representation` → PARTIAL; required gaps still BLOCKED

- [ ] **Step 1: Write the failing tests**

Append to `tests/compiler/test_mission_021_oq.py`:

```python
def test_optional_accepted_unmapped_is_partial_not_blocked() -> None:
    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-021-010"),
        "sources": [_source(kind="developer_config", source_id="SRC-021-010")],
        "claims": [
            _claim(req_id="REQ-021-010", source_id="SRC-021-010"),
            _claim(
                req_id="REQ-021-011",
                source_id="SRC-021-010",
                type="behavior",
                priority="optional",
                statement="Optional unmapped meaning.",
            ),
        ],
        "mappings": [
            {
                "id": "MAP-021-010",
                "requirement_id": "REQ-021-010",
                "outcome": "direct",
                "target_pointer": "/objective/goal",
                "authority_ref": {"kind": "source", "ref": "SRC-021-010"},
                "validation_ref": "VAL-PROD-001",
            },
            {
                "id": "MAP-021-011",
                "requirement_id": "REQ-021-011",
                "outcome": "unresolved",
                "authority_ref": {"kind": "source", "ref": "SRC-021-010"},
                "validation_ref": "VAL-PROD-001",
            },
        ],
    }
    result = compile_requirements_input(envelope)
    assert result.status == "PARTIAL"
    assert "RQC-AMB-0001" in result.reason_codes
    assert "RQC-BLK-0001" not in result.reason_codes


def test_required_accepted_unmapped_stays_blocked() -> None:
    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-021-012"),
        "sources": [_source(kind="developer_config", source_id="SRC-021-012")],
        "claims": [_claim(req_id="REQ-021-012", source_id="SRC-021-012")],
    }
    result = compile_requirements_input(envelope)
    assert result.status == "BLOCKED"
    assert "RQC-BLK-0001" in result.reason_codes


def test_optional_no_ir_representation_is_partial() -> None:
    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-021-013"),
        "sources": [_source(kind="developer_config", source_id="SRC-021-013")],
        "claims": [
            _claim(req_id="REQ-021-013", source_id="SRC-021-013"),
            _claim(
                req_id="REQ-021-014",
                source_id="SRC-021-013",
                type="behavior",
                priority="optional",
                statement="Optional IR gap.",
            ),
        ],
        "mappings": [
            {
                "id": "MAP-021-013",
                "requirement_id": "REQ-021-013",
                "outcome": "direct",
                "target_pointer": "/objective/goal",
                "authority_ref": {"kind": "source", "ref": "SRC-021-013"},
                "validation_ref": "VAL-PROD-001",
            },
            {
                "id": "MAP-021-014",
                "requirement_id": "REQ-021-014",
                "outcome": "no_ir_representation",
                "diagnostic_code": "RQC-IRG-0001",
                "gap_id": "IRG-021-014",
                "authority_ref": {"kind": "source", "ref": "SRC-021-013"},
                "validation_ref": "VAL-PROD-001",
            },
        ],
    }
    result = compile_requirements_input(envelope)
    assert result.status == "PARTIAL"
    assert "RQC-IRG-0001" in result.reason_codes
    assert "RQC-BLK-0001" not in result.reason_codes


def test_valid_prose_stays_blocked() -> None:
    from pathlib import Path

    fixture = Path("tests/compiler/fixtures/plain_language_minimal.txt")
    result = compile_requirements_input(
        {"profile": "plain_language_v0", "text": fixture.read_text(encoding="utf-8")}
    )
    assert result.status == "BLOCKED"
    assert "RQC-BLK-0001" in result.reason_codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py::test_optional_accepted_unmapped_is_partial_not_blocked tests/compiler/test_mission_021_oq.py::test_optional_no_ir_representation_is_partial -v`

Expected: FAIL with `BLOCKED` / `RQC-BLK-0001` instead of PARTIAL.

- [ ] **Step 3: Implement Class 6f / 6j skip and Class 7 PARTIAL**

In `evaluate_contract_rules`:

After `has_emitting_mapping` is defined, add:

```python
    def requirement_by_id(rid: str) -> Mapping[str, Any] | None:
        for requirement in requirements:
            if requirement.get("id") == rid:
                return requirement
        return None

    def is_optional_requirement(rid: str) -> bool:
        record = requirement_by_id(rid)
        return bool(record) and record.get("priority") == "optional"
```

Replace Class 6f (`no_ir_representation` always BLOCKED) with: invalid diagnostic/gap still `INVALID_OUTPUT`; if **any** `no_ir_representation` mapping’s `requirement_id` is not optional, return `BLOCKED`, `["RQC-BLK-0001", "RQC-IRG-0001"]`; otherwise do not return (fall through).

Replace Class 6j (accepted without emitting mapping always BLOCKED) with: collect those requirements; if **any** has `priority != "optional"`, return `BLOCKED`, `["RQC-BLK-0001"]`; otherwise do not return.

Extend Class 7 so that before replaced-source PARTIAL:

- If optional-only unresolved acceptance remains, keep `PARTIAL` / `RQC-AMB-0001`.
- Else if remaining `no_ir_representation` mappings exist (all optional if 6f fell through), return `PARTIAL` with `RQC-IRG-0001` (include `RQC-AMB-0001` as well if optional unresolved acceptance also remains — if the first branch already returned, include IRG on that same return when optional IR gaps also exist).
- Else if accepted optional requirements lack an emitting mapping, return `PARTIAL` / `RQC-AMB-0001`.
- Else existing replaced-source `RQC-SRC-0005` PARTIAL.

Do not change Class 5 security/privacy. Do not change 6i required unresolved BLOCKED.

Minimal Class 7 shape (preserve existing first-branch behavior, add IRG to that return when needed):

```python
    no_ir_remaining = [mapping for mapping in mappings if mapping.get("outcome") == "no_ir_representation"]
    optional_unmapped_accepted = [
        requirement
        for requirement in requirements
        if requirement.get("acceptance_state") == "accepted"
        and not has_emitting_mapping(requirement.get("id", ""))
        and requirement.get("priority") == "optional"
    ]
    if unresolved and all(requirement.get("priority") == "optional" for requirement in unresolved):
        codes = ["RQC-AMB-0001"]
        if no_ir_remaining:
            codes.append("RQC-IRG-0001")
        return "PARTIAL", sorted(set(codes))
    if no_ir_remaining:
        return "PARTIAL", ["RQC-IRG-0001"]
    if optional_unmapped_accepted:
        return "PARTIAL", ["RQC-AMB-0001"]
    if any(source.get("lifecycle") == "replaced" for source in source_list):
        return "PARTIAL", ["RQC-SRC-0005"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py tests/compiler/test_mission_016_engine.py tests/compiler/test_mission_020_produce.py::test_valid_grammar_is_blocked_not_invalid_or_success -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/requirements_contract.py tests/compiler/test_mission_021_oq.py
git commit -m "feat: treat optional unresolved IR meaning as PARTIAL with evidence"
```

---

### Task 4: OQ-008-006 advisory non-semantic SUCCESS

**Files:**
- Modify: `architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json`
- Modify: `src/promptrig/compiler/schemas/requirements_diagnostic_registry.json` (must remain byte-identical to the architecture copy)
- Modify: `src/promptrig/compiler/requirements_contract.py` (Class 8)
- Modify: `architecture/requirements-compiler-contract-v0.1/validate_contract.py`
- Modify: `tests/compiler/test_mission_021_oq.py`

**Interfaces:**
- Consumes: registry-by-code, `emitted_diagnostic_codes`, `compile_requirements`
- Produces: SUCCESS with `RQC-ADV-0001`; replaced source still PARTIAL

- [ ] **Step 1: Write the failing tests**

Append to `tests/compiler/test_mission_021_oq.py`:

```python
def test_advisory_nonsemantic_diagnostic_can_coexist_with_success() -> None:
    from promptrig.compiler.requirements_contract import compile_requirements

    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-021-020"),
        "sources": [_source(kind="developer_config", source_id="SRC-021-020")],
        "claims": [_claim(req_id="REQ-021-020", source_id="SRC-021-020")],
        "mappings": [
            {
                "id": "MAP-021-020",
                "requirement_id": "REQ-021-020",
                "outcome": "direct",
                "target_pointer": "/objective/goal",
                "authority_ref": {"kind": "source", "ref": "SRC-021-020"},
                "validation_ref": "VAL-PROD-001",
            }
        ],
        "diagnostics": [
            {
                "id": "RQDIA-021-020",
                "code": "RQC-ADV-0001",
                "severity": "warning",
                "message_key": "requirements.advisory_nonsemantic",
                "parameters": {},
                "source_refs": ["SRC-021-020"],
                "requirement_refs": ["REQ-021-020"],
            }
        ],
    }
    artifacts = produce_requirements(envelope)
    result = compile_requirements(artifacts)
    assert result.status == "SUCCESS"
    assert result.reason_codes == ("RQC-ADV-0001",)


def test_replaced_source_stays_partial() -> None:
    envelope = {
        "intent_input": _intent(mode="developer", input_id="INP-021-021"),
        "sources": [
            _source(kind="developer_config", source_id="SRC-021-021", lifecycle="replaced")
        ],
        "claims": [_claim(req_id="REQ-021-021", source_id="SRC-021-021")],
        "mappings": [
            {
                "id": "MAP-021-021",
                "requirement_id": "REQ-021-021",
                "outcome": "direct",
                "target_pointer": "/objective/goal",
                "authority_ref": {"kind": "source", "ref": "SRC-021-021"},
                "validation_ref": "VAL-PROD-001",
            }
        ],
    }
    result = compile_requirements_input(envelope)
    assert result.status == "PARTIAL"
    assert "RQC-SRC-0005" in result.reason_codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py::test_advisory_nonsemantic_diagnostic_can_coexist_with_success -v`

Expected: FAIL (`RQC-DIA-0001` unknown code, or SUCCESS with empty codes).

- [ ] **Step 3: Registry, Class 8, harness**

Add to **both** registry JSON files, after `RQC-SRC-0005`, the object:

```json
{"code": "RQC-ADV-0001", "severity": "warning", "class": "advisory", "semantic": false, "message_key": "requirements.advisory_nonsemantic"}
```

Keep every other diagnostic without `"semantic"` (missing means true). Copy architecture file bytes onto the vendored compiler schema path so `test_vendored_requirements_diagnostic_registry_matches_source` passes.

Replace Class 8 SUCCESS return:

```python
    if requirements and all(requirement.get("acceptance_state") == "accepted" for requirement in requirements):
        advisory_codes = []
        for code in context["emitted_diagnostic_codes"]:
            if not code:
                continue
            entry = registry.get(code) or {}
            if entry.get("class") == "advisory" and entry.get("semantic") is False:
                advisory_codes.append(code)
        return "SUCCESS", sorted(set(advisory_codes))
```

In `validate_contract.py`, replace the SUCCESS + declared_reasons check:

```python
    if derived_status == "SUCCESS":
        if any(d.get("severity") == "error" for d in diagnostics):
            return "success_with_error_evidence"
        for code in declared_reasons:
            entry = registry.get(code) or {}
            if entry.get("class") != "advisory" or entry.get("semantic") is not False:
                return "success_with_error_evidence"
```

Keep the following `if derived_status != "SUCCESS" and not declared_reasons` line unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/compiler/test_mission_021_oq.py tests/compiler/test_contract_schema_drift.py::test_vendored_requirements_diagnostic_registry_matches_source tests/requirements/test_requirements_contract.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/requirements-compiler-contract-v0.1/requirements-diagnostic-registry.json src/promptrig/compiler/schemas/requirements_diagnostic_registry.json src/promptrig/compiler/requirements_contract.py architecture/requirements-compiler-contract-v0.1/validate_contract.py tests/compiler/test_mission_021_oq.py
git commit -m "feat: allow advisory non-semantic diagnostics with SUCCESS"
```

---

### Task 5: Docs, OAR-015 Ready, honesty surfaces

**Files:**
- Modify: `src/promptrig/compiler/requirements_contract.py` (module docstring: OQ-008-001/002/006 implemented this campaign; 003–005 and 007–010 unimplemented)
- Modify: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` (closing paragraph: 001/002/006 implemented in MISSION-021; remaining OQs still authorize no implementation)
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-015.md`
- Create: `MISSION_021_REPORT.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md`, `README.md`

**Interfaces:**
- Consumes: Tasks 1–4 behavior
- Produces: OAR-015 Ready (not Accepted); PARTIAL honesty

- [ ] **Step 1: Update OPEN_QUESTIONS closing paragraph**

Replace the final paragraph of `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md` with:

```markdown
MISSION-021 implements OQ-008-001, OQ-008-002, and OQ-008-006 in the production engine/producer. OQ-008-003 through OQ-008-005 and OQ-008-007 through OQ-008-010 remain owner-resolved policy only and authorize no further production implementation. Freeform authoring-prose interpretation, M3 / Simple Mode UI, live providers, full MISSION-008 production compiler, CERTIFIED maturity, and full Phase 4B exit remain unauthorized. Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`).
```

Keep a `policy only` phrase in that paragraph so existing 020 schedule `policy only` assertion still holds.

- [ ] **Step 2: Write OAR-015 Ready** (not Accepted)

```markdown
# OAR-015 — MISSION-021 OQ-008-001/002/006 Implementation

**Status:** Ready for owner acceptance.

**Certified if accepted:** OQ-008-001 file-digest fail-closed is named implemented policy; OQ-008-002 optional unresolved / optional `no_ir_representation` meaning compiles PARTIAL with evidence; OQ-008-006 SUCCESS may carry advisory non-semantic `RQC-ADV-0001`; `evaluate_contract_rules` remains the sole RC-065 implementation. Required unmapped meaning and valid constrained prose remain BLOCKED (`RQC-BLK-0001`). `RQC-SRC-0005` remains PARTIAL. Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, PRS **language**, OQ-008-003 through OQ-008-005, OQ-008-007 through OQ-008-010, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST. Requirements compiler maturity remains **PARTIAL** after this record. OAR-009 through OAR-014 remain Accepted.
```

- [ ] **Step 3: Report, maturity, deferred, README**

`MISSION_021_REPORT.md` status: OAR-015 Ready for owner acceptance (not Accepted). Baseline `ca888a8`. Branch `feature/mission-021-oq-implementation`. List Tasks 1–5 commits. Residual gaps: PARTIAL; prose still BLOCKED; remaining OQs unimplemented; not CERTIFIED; not Phase 4B exit; not M3.

Maturity map Requirements compiler evidence: append MISSION-021 OQ-008-001/002/006 (`test_mission_021_*.py`; OAR-015 Ready). Limitations: still not full 008; 003–005/007–010 unimplemented; valid prose BLOCKED; no M3.

`DEFERRED_AND_REJECTED_WORK.md` Blocking: MISSION-021 implemented OQ-008-001/002/006 (OAR-015 Ready); remaining unauthorized: other OQs, full 008, M3, freeform NLP.

`README.md`: add a MISSION-021 paragraph matching 020 style; OAR-015 Ready; still PARTIAL; still no full 008 / M3 / freeform / Phase 4B exit.

Module docstring in `requirements_contract.py`: replace “OQ-008-001 through OQ-008-009 remain unresolved” with “OQ-008-001, OQ-008-002, and OQ-008-006 are implemented; OQ-008-003 through OQ-008-005 and OQ-008-007 through OQ-008-010 remain unimplemented.”

- [ ] **Step 4: Run honesty + oq tests**

Run: `uv run python -m pytest tests/compiler/test_mission_021_schedule.py tests/compiler/test_mission_021_oq.py tests/compiler/test_mission_020_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md architecture/OWNER_ACCEPTANCE_RECORDS/OAR-015.md MISSION_021_REPORT.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md src/promptrig/compiler/requirements_contract.py architecture/mission-021-certification/README.md
git commit -m "docs: MISSION-021 report and OAR-015 draft for OQ-008-001/002/006"
```

---

## Self-review

- Spec coverage: 001 wording + fail-closed, 002 optional PARTIAL, 006 SUCCESS advisory, honesty, OAR-015 Ready, prose still BLOCKED, remaining OQs unimplemented.
- No TBD/placeholder steps.
- Types: `compile_requirements_input` / `compile_requirements` / `RequirementsCompileResult.status` / `reason_codes` consistent across tasks.
