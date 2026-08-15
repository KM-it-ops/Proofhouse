# MISSION-013 Plain-Language Headless M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certify a **headless, offline, deterministic** plain-language intake (M1) that parses a constrained prose grammar into `structured_minimal_v0` records, then runs the existing MISSION-012 closed loop — no models, no Simple Mode UI.

**Architecture:** Add `plain_language.py` as a producing stage only. It emits a structured requirements document. Existing `validate_structured_requirements` / `requirements_to_ir` / `run_closed_loop` remain the semantic owners (RC-001, RC-003). Fail closed on any line outside the grammar. Profile `plain_language_v0` is intake-only; IR mapping still uses structured_minimal_v0.

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler closed-loop`, architecture docs under `architecture/mission-011-certification/` and `architecture/OWNER_ACCEPTANCE_RECORDS/`.

## Global Constraints

- Baseline: `9e5028d` (MISSION-012 HEAD, stacked on unmerged PR #19). Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree: `C:/AI/projects/PromptRig/.worktrees/mission-013-plain-language-m1` on `feature/mission-013-plain-language-m1`. Do not edit `main` or the MISSION-012 worktree.
- Offline default: `network_allowed=false`, no credentials, no live providers, **no model calls** (M2 is MISSION-014, out of scope).
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. New intake profile: `plain_language_v0` only.
- Repair budgets remain `{0,1,2}`; repair must not weaken `accepted_objectives` or `security_constraints` (`EVR-SEC-0001`).
- Simple Mode UI-only semantics stay forbidden (`authoring_mode=simple_ui_only` / `profile=simple_mode_ui`). M3 is not this mission.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no benchmark claims.
- M1 is **constrained prose**, not freeform NLP. Extra or ambiguous lines → parse error, never a guessed requirement.
- Canonical evaluation still does not interpret ordinary language (RC-005). The parser is a producer; 008 validation remains on structured records.
- Maturity promotion: update map + evidence + tests in the same change that claims promotion. OAR-007 is **Ready for owner acceptance** until Boss says Accepted.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run pytest` when available.
- After any subagent role exceeds 10 uses, pause and propose a hardened specialist.

### Constrained grammar (normative for this mission)

A `plain_language_v0` `text` field must match this document (UTF-8, `\n` or `\r\n`). Blank lines ignored. No `#` comments.

```
Project: <name>          # optional, one line
Goal: <nonempty goal>    # required, exactly one
Requirements:            # required header
1. <statement>           # required, consecutive integers starting at 1
2. <statement>
Constraints:             # optional header
- <constraint>           # zero or more; only if Constraints: present
```

Labels are case-sensitive. Requirement IDs assigned as `REQ-PL-001`, `REQ-PL-002`, … in listed order (stable for identical text). Parse failure diagnostic prefix: `PL-PARSE-`.

---

### Task 1: M1 contract + schedule honesty

**Files:**
- Create: `architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md`
- Modify: `architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md`
- Modify: `tests/compiler/test_mission_011_certification.py` (keep Simple Mode rejection; add schedule M1-in-progress assertion)
- Create: `tests/compiler/test_mission_013_schedule.py`

**Interfaces:**
- Consumes: MISSION-011 schedule hard rule; Boss authorization 2026-08-14
- Produces: grammar file; schedule line for M1 = authorized / in progress (not done until Task 6)

- [ ] **Step 1: Write failing schedule test**

```python
from pathlib import Path

def test_m1_schedule_authorized_not_ui() -> None:
    text = Path("architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md").read_text(encoding="utf-8")
    assert "MUST NOT be the first or only semantic implementation" in text
    assert "plain_language_v0" in text
    assert "MISSION-013" in text
    assert "Simple Mode UI" in text or "M3" in text
    grammar = Path("architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md")
    assert grammar.is_file()
    g = grammar.read_text(encoding="utf-8")
    assert "Goal:" in g and "Requirements:" in g
    assert "no model" in g.lower() or "deterministic" in g.lower()
```

- [ ] **Step 2: Run test — expect FAIL (grammar missing)**

Run: `uv run pytest tests/compiler/test_mission_013_schedule.py -v`

- [ ] **Step 3: Write grammar + update schedule**

Schedule M1 bullet becomes: authorized MISSION-013; headless `plain_language_v0` constrained prose; emits structured_minimal_v0; M2/M3 still future. Keep M0 done. Keep Simple Mode UI forbidden.

Grammar file states the exact grammar above, fail-closed rules, ID assignment, and non-claims (not freeform NLP, not 008 full compiler, not M2).

- [ ] **Step 4: Run test — expect PASS**

Run: `uv run pytest tests/compiler/test_mission_013_schedule.py tests/compiler/test_mission_011_certification.py::test_simple_ui_only_profile_rejected tests/compiler/test_mission_011_certification.py::test_plain_language_schedule_exists -v`

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md tests/compiler/test_mission_013_schedule.py docs/superpowers/plans/2026-08-14-mission-013-plain-language-m1.md
git commit -m "docs: authorize MISSION-013 plain_language_v0 constrained grammar"
```

---

### Task 2: Deterministic parser module

**Files:**
- Create: `src/promptrig/compiler/plain_language.py`
- Create: `tests/compiler/test_plain_language.py`
- Create: `tests/compiler/fixtures/plain_language_minimal.txt`

**Interfaces:**
- Consumes: grammar from Task 1
- Produces:

```python
class PlainLanguageParseError(ValueError):
    def __init__(self, code: str, message: str) -> None: ...

def parse_plain_language_v0(text: str, *, project_name: str | None = None) -> dict: ...
# returns structured_minimal_v0 dict with contract_version "0.1.0", network_allowed False
```

- [ ] **Step 1: Write failing tests**

Fixture `plain_language_minimal.txt`:

```
Project: incident-desk
Goal: Summarize incidents without inventing facts.
Requirements:
1. Label missing context as UNKNOWN.
Constraints:
- No credential exfiltration.
```

```python
from pathlib import Path
import pytest
from promptrig.compiler.plain_language import parse_plain_language_v0, PlainLanguageParseError

FIXTURE = Path(__file__).parent / "fixtures" / "plain_language_minimal.txt"

def test_parse_minimal() -> None:
    doc = parse_plain_language_v0(FIXTURE.read_text(encoding="utf-8"))
    assert doc["profile"] == "structured_minimal_v0"
    assert doc["intake_profile"] == "plain_language_v0"
    assert doc["project_name"] == "incident-desk"
    assert doc["objective"]["goal"] == "Summarize incidents without inventing facts."
    assert doc["requirements"][0]["id"] == "REQ-PL-001"
    assert doc["requirements"][0]["statement"] == "Label missing context as UNKNOWN."
    assert "No credential exfiltration." in doc["behavior"]["constraints"]
    assert doc["network_allowed"] is False

def test_reject_freeform() -> None:
    with pytest.raises(PlainLanguageParseError) as ei:
        parse_plain_language_v0("Please build a helpful assistant that does stuff.")
    assert str(ei.value).startswith("PL-PARSE-")

def test_reject_gap_in_numbering() -> None:
    text = "Goal: G\nRequirements:\n1. A\n3. B\n"
    with pytest.raises(PlainLanguageParseError):
        parse_plain_language_v0(text)

def test_reject_hash_comment() -> None:
    with pytest.raises(PlainLanguageParseError):
        parse_plain_language_v0("Goal: G\n# sneaky\nRequirements:\n1. A\n")
```

- [ ] **Step 2: Run — expect FAIL (module missing)**

Run: `uv run pytest tests/compiler/test_plain_language.py -v`

- [ ] **Step 3: Implement parser**

Line-oriented state machine: `start` → optional Project → Goal → Requirements header → numbered items → optional Constraints. Any other non-blank line raises `PlainLanguageParseError("PL-PARSE-0001", ...)`. Missing Goal or empty requirements: `PL-PARSE-0002`. Numbering gaps: `PL-PARSE-0003`. Default `project_name` `plain-language-m1` if omitted. Map constraints into `behavior.constraints`; default instructions `["Follow requirements exactly."]`.

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run pytest tests/compiler/test_plain_language.py -v`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/plain_language.py tests/compiler/test_plain_language.py tests/compiler/fixtures/plain_language_minimal.txt
git commit -m "feat: parse plain_language_v0 constrained prose into structured_minimal_v0"
```

---

### Task 3: Wire closed loop intake

**Files:**
- Modify: `src/promptrig/compiler/closed_loop.py` (`closed_loop_from_json` / `run_closed_loop` entry)
- Modify: `tests/compiler/test_closed_loop.py` or add `tests/compiler/test_plain_language_closed_loop.py`

**Interfaces:**
- Consumes: `parse_plain_language_v0`; existing `run_closed_loop`
- Produces: JSON envelope with `"profile": "plain_language_v0"` and `"text"` is accepted by `closed_loop_from_json`; result evidence includes `intake_profile` = `plain_language_v0`. Structured profiles unchanged.

JSON intake shape:

```json
{
  "profile": "plain_language_v0",
  "contract_version": "0.1.0",
  "network_allowed": false,
  "repair_budget": 1,
  "text": "<grammar document>"
}
```

If `profile` is structured_*, keep current path. If `plain_language_v0`, parse `text` then `run_closed_loop` on the structured doc. Parse errors → `BLOCKED` with diagnostic `PL-PARSE-*`. `network_allowed: true` still blocks `EVR-NET-0001` before parse. `authoring_mode: simple_ui_only` still rejected.

- [ ] **Step 1: Write failing closed-loop tests**

```python
from pathlib import Path
from promptrig.compiler.closed_loop import ClosedLoopOptions, closed_loop_from_json

def test_plain_language_closed_loop_pass() -> None:
    text = (Path(__file__).parent / "fixtures" / "plain_language_minimal.txt").read_text(encoding="utf-8")
    raw = json.dumps({
        "profile": "plain_language_v0",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "repair_budget": 1,
        "text": text,
    }).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions(repair_budget=1))
    assert result.status == "PASS"
    assert result.evidence_bundle["intake_profile"] == "plain_language_v0"
    assert "REQ-PL-001" in result.evidence_bundle["requirement_ids"]
```

Also assert existing structured fixture still PASSes (regression).

- [ ] **Step 2: Run — expect FAIL (intake unknown / no intake_profile)**

- [ ] **Step 3: Implement dispatch in `closed_loop_from_json`; thread `intake_profile` through `build_evidence_bundle` (add optional key, default omit or `structured` for old path)**

Keep `prototype_id` alias. Do not change loop_id unless adding a sibling field is cleaner — prefer `intake_profile` only.

- [ ] **Step 4: Run `uv run pytest tests/compiler/test_plain_language_closed_loop.py tests/compiler/test_closed_loop.py tests/compiler/test_evidence_bundle.py -v` — PASS**

- [ ] **Step 5: Commit**

```powershell
git commit -m "feat: accept plain_language_v0 JSON intake on closed-loop path"
```

---

### Task 4: Library/CLI parity + public export

**Files:**
- Modify: `src/promptrig/compiler/api.py` (PEP 562 export `parse_plain_language_v0` if tests import from api; otherwise export via closed_loop_from_json only — prefer exporting parse function next to closed-loop names)
- Modify: `src/promptrig/compiler/cli_compiler.py` help text for closed-loop input (JSON structured **or** plain_language_v0 envelope)
- Create: `tests/compiler/test_plain_language_parity.py`
- Create: `tests/compiler/fixtures/external_consumer_plain_language.py`

**Interfaces:**
- Library `closed_loop_from_json` and CLI `closed-loop --json` agree on `status`, `ir_sha256`, `evaluation.status`, `loop_id`, `intake_profile` for the same fixture bytes.

- [ ] **Step 1: Failing parity + consumer smoke tests** (mirror Task 5 of MISSION-012; import only `promptrig.compiler.api`)

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement exports (lazy `__getattr__` set membership, do not re-introduce eager closed_loop cycle) + CLI help**

- [ ] **Step 4: Run `uv run pytest tests/compiler/test_plain_language_parity.py tests/compiler/test_closed_loop_parity.py tests/compiler/test_mission_012_certification.py -v` — PASS**

- [ ] **Step 5: Commit**

```powershell
git commit -m "test: certify plain-language library/CLI parity and consumer smoke"
```

---

### Task 5: Certification tests + Simple Mode still forbidden

**Files:**
- Create: `tests/compiler/test_mission_013_certification.py`
- Modify: `tests/compiler/test_mission_011_certification.py` only if needed to keep Simple Mode rejection

**Interfaces:**
- Produces: subprocess smoke; assertion that freeform prose never becomes IR; assertion no `openai`/`anthropic` import in `plain_language.py`

- [ ] **Step 1: Write tests**

```python
def test_plain_language_module_has_no_provider_imports() -> None:
    src = Path("src/promptrig/compiler/plain_language.py").read_text(encoding="utf-8")
    for needle in ("openai", "anthropic", "google.generativeai", "httpx", "requests"):
        assert needle not in src.lower()

def test_simple_ui_still_rejected_on_plain_envelope() -> None:
    raw = json.dumps({
        "profile": "plain_language_v0",
        "authoring_mode": "simple_ui_only",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "text": "Goal: G\nRequirements:\n1. A\n",
    }).encode()
    result = closed_loop_from_json(raw, ClosedLoopOptions())
    assert result.status == "BLOCKED"
    assert any("Simple Mode" in d for d in result.diagnostics)
```

- [ ] **Step 2–4: RED/GREEN, run with 011 Simple Mode test**

- [ ] **Step 5: Commit**

```powershell
git commit -m "test: certify MISSION-013 M1 non-claims and Simple Mode rejection"
```

---

### Task 6: Report, OAR-007 draft, maturity (not Accepted)

**Files:**
- Create: `MISSION_013_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-007.md` (Ready for owner acceptance)
- Create: `architecture/mission-013-certification/README.md`
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (Requirements compiler still `PARTIAL`; cite M1 constrained prose + tests; non-claim freeform/M2/UI)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` (plain-language M1 no longer “unauthorized”; remaining: freeform NLP, M2, M3, full 008)
- Modify: `README.md` Status (honest M1 constrained prose; still no live/UI/models)
- Modify: schedule M1 to “implemented, awaiting OAR-007”

**Interfaces:**
- Do **not** mark OAR-007 Accepted. Do **not** set Requirements compiler to `CERTIFIED`.

- [ ] **Step 1: Write docs from HEAD evidence**
- [ ] **Step 2: Run `uv run pytest tests/compiler tests/evaluation -v` — all PASS**
- [ ] **Step 3: Commit**

```powershell
git commit -m "docs: MISSION-013 report and OAR-007 draft for plain-language M1"
```

---

## Spec Coverage Check

| Source | Tasks |
|---|---|
| Schedule M1 headless before UI | 1, 5, 6 |
| Constrained prose grammar (Boss choice) | 1, 2 |
| Emit structured records then 008/012 path | 3 |
| No models / RC-003 / RC-074 | 2, 5 |
| Library/CLI parity | 4 |
| Simple Mode UI still forbidden | 5 |
| Honesty / OAR draft | 6 |
| M2, M3, live, IR v0.2 | Out of scope |

## Worktree / stacking

- Branch: `feature/mission-013-plain-language-m1`
- Worktree: `.worktrees/mission-013-plain-language-m1`
- Stacked on MISSION-012 `9e5028d` (PR #19). Rebase onto `main` only after #19 merges; no force-push unless Boss asks.
- Do not nest worktrees. Do not commit `uv.lock`.
