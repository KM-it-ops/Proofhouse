# MISSION-015 Phase 4B Residual Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certify remaining Phase 4B **evidence** for the already-certified offline fake-adapter closed loop: PEP 517 clean-install, an installed-package public-API consumer matrix, and explicit operational resource ceilings — without claiming full Phase 4B exit, M3, live providers, or benchmarks.

**Architecture:** No new semantic compiler path. Public consumers stay on `promptrig.compiler.api` lazy exports. Packaging proof is an isolated venv install of the repo (PEP 517) with `PYTHONPATH` stripped. Resource ceilings live in `resource_bounds.py` and are documented in `RESOURCE_BOUNDS.md` as fail-closed operational bounds (REJ-005: not comparative benchmarks).

**Tech Stack:** Python 3.11+, `promptrig.compiler`, pytest, `promptrig-compiler`, stdlib `venv` + pip, GitHub Actions.

**Baseline:** `main` @ `8fc5c43` (PR #21). **Branch / worktree:** `feature/mission-015-phase4b-residual` in `C:/AI/projects/PromptRig/.worktrees/mission-015-phase4b-residual`.

## Global Constraints

- Baseline: `8fc5c43`. Do not rewrite history; preserve `v0.5-architecture-freeze`.
- Isolated worktree only. Do not edit the `main` checkout.
- Offline certified path: `network_allowed=false`, no credentials, no live providers, no provider SDK/HTTP client.
- Approved structured profiles remain `structured_minimal_v0` and `structured_developer_v0`. Intake `plain_language_v0` remains M1. Fake suggester remains `fake-suggester-v0` sidecar. Do not add profiles or map proposals to IR.
- Repair budgets remain `{0,1,2}`; `EVR-SEC-0001` unchanged.
- Simple Mode UI-only semantics stay forbidden. M3 is not this mission.
- No IR v0.2 schema/code; no Phase 6–9 product surfaces; no DFR-003 live-provider path.
- Do **not** claim full Roadmap Phase 4B exit. Do **not** graduate Requirements compiler from `PARTIAL`. Do **not** write comparative/benchmark performance claims (REJ-005).
- Resource ceilings are operational fail-closed bounds for `closed_loop_requirements_minimal.json` + `repair_budget=1` only: `WALL_SECONDS_MAX = 5.0`, `TRACEMALLOC_PEAK_BYTES_MAX = 8388608` (8 MiB). Measured locally ~0.16s / ~153 KiB; 3× would be ~0.47s / ~459 KiB; floors are 5.0s and 8 MiB for CI variance.
- Production CLI must never expose `force_*` / test hooks.
- OAR-009 is **Ready for owner acceptance** until Boss says Accepted. OAR-006/007/008 stay Accepted.
- Maturity promotion: update map + evidence + tests in the same change that claims the residual evidence. CI job-count wording must match the workflow after Task 5 (eight jobs: six OS/Python + typescript-drift + wheel-install).
- Ambition-gap C4 (IR v0.2 planning) is **not** this mission; if launched later it needs a new ID.
- Commit after each task; do not push unless Boss asks.
- Prefer `uv run python -m pytest` or `.venv/Scripts/python -m pytest`.
- After any subagent role exceeds 10 uses, pause and propose a hardened specialist.
- Do not commit `uv.lock`.

---

### Task 1: Residual contract + honesty

**Files:**
- Create: `architecture/mission-015-certification/README.md`
- Create: `tests/compiler/test_mission_015_schedule.py`

**Interfaces:**
- Consumes: OAR-006/007/008 Accepted; remaining 4B holes named in those OARs (consumer matrix, perf/resource, clean-install)
- Produces: mission-015 certification README that names residual scope and explicit non-claims; schedule test that fails until the README exists

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_mission_015_residual_not_full_4b_not_m3() -> None:
    note = Path("architecture/mission-015-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "clean-install" in lower or "clean install" in lower
    assert "consumer matrix" in lower
    assert "resource" in lower
    assert "not full" in lower
    assert "phase 4b" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "benchmark" in lower
    assert "partial" in lower
    assert "oar-009" in lower
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_schedule.py -v`

Expected: FAIL because `architecture/mission-015-certification/README.md` does not exist.

- [ ] **Step 3: Write README**

Create `architecture/mission-015-certification/README.md` with this body (exact non-claim phrases required by the test):

```markdown
# Phase 4B Residual Evidence Package (MISSION-015)

**Status:** In progress — OAR-009 Ready for owner acceptance after Tasks 1–6 (not Accepted in this task).
**Baseline:** `main` @ `8fc5c43` (PR #21 / OAR-008 Accepted).
**Scope:** Residual packaging, installed-package consumer matrix, and operational resource bounds for the already-certified offline fake-adapter closed loop.

## What this mission certifies (narrow)

- PEP 517 `[build-system]` plus isolated-venv clean-install of the wheel/source (no `PYTHONPATH=src`).
- Installed-package consumer matrix over public `promptrig.compiler.api` for structured closed-loop, `plain_language_v0`, and opt-in `fake-suggester-v0`.
- Explicit operational resource ceilings (`RESOURCE_BOUNDS.md` / `resource_bounds.py`) — not a benchmark.

Existing PYTHONPATH smokes from MISSION-012/013/014 remain. This mission adds installed-package counterparts.

## Non-claims

- Not full Roadmap Phase 4B exit (no full MISSION-008 production compiler; no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- Resource ceilings are operational fail-closed bounds, not comparative benchmark results.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_schedule.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-015-certification/README.md tests/compiler/test_mission_015_schedule.py
git commit -m "docs: authorize MISSION-015 Phase 4B residual evidence"
```

---

### Task 2: Clean-install proof

**Files:**
- Modify: `pyproject.toml` (add `[build-system]`)
- Create: `tests/compiler/packaging_util.py`
- Create: `tests/compiler/test_mission_015_clean_install.py`

**Interfaces:**
- Consumes: Task 1 README; existing `external_consumer_closed_loop.py`; `closed_loop_requirements_minimal.json`
- Produces: `install_isolated(repo_root, venv_dir) -> Path` returning the isolated venv's Python; `clean_child_env() -> dict`

- [ ] **Step 1: Write failing tests**

`tests/compiler/packaging_util.py`:

```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def clean_child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def install_isolated(repo_root: Path, venv_dir: Path) -> Path:
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    py = venv_python(venv_dir)
    env = clean_child_env()
    upgrade = subprocess.run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    installed = subprocess.run(
        [str(py), "-m", "pip", "install", str(repo_root)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    return py
```

`tests/compiler/test_mission_015_clean_install.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from packaging_util import clean_child_env, install_isolated, venv_python

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
CONSUMER = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_closed_loop.py"


def test_pyproject_declares_pep517_build_system() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[build-system]" in text
    assert "setuptools" in text
    assert "wheel" in text


def test_isolated_venv_doctor_and_closed_loop_consumer(tmp_path: Path) -> None:
    py = install_isolated(ROOT, tmp_path / "venv")
    env = clean_child_env()
    doctor = subprocess.run(
        [str(py), "-m", "promptrig.compiler.cli_compiler", "doctor", "--json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert doctor.returncode == 0, doctor.stderr
    payload = json.loads(doctor.stdout)
    assert payload["status"] == "success"
    assert payload["command"] == "doctor"
    names = {c["name"]: c["ok"] for c in payload["data"]["checks"]}
    assert names["ir_schema"] is True
    assert names["diagnostic_registry"] is True
    assert names["offline_mode"] is True

    consumer = subprocess.run(
        [str(py), str(CONSUMER), str(FIXTURE)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert consumer.returncode == 0, consumer.stderr
    out = json.loads(consumer.stdout)
    assert out["status"] == "PASS"
    assert out["loop_id"] == "mission-012-headless-closed-loop-v0.1"
    assert out["ir_sha256"]
    assert "src" not in (env.get("PYTHONPATH") or "")
    scripts = venv_python(tmp_path / "venv")
    assert scripts.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_clean_install.py::test_pyproject_declares_pep517_build_system -v`

Expected: FAIL (`[build-system]` missing).

- [ ] **Step 3: Add build-system to pyproject.toml**

Insert at the **top** of `pyproject.toml` (before `[project]`):

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

Leave the rest of `pyproject.toml` unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_clean_install.py -v`

Expected: PASS (isolated pip install may take ~30–90s and may contact PyPI for `jsonschema` / `rfc8785` only — not a live provider).

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml tests/compiler/packaging_util.py tests/compiler/test_mission_015_clean_install.py
git commit -m "test: prove PEP 517 clean-install for compiler wheel"
```

---

### Task 3: Installed-package consumer matrix

**Files:**
- Create: `architecture/mission-015-certification/CONSUMER_MATRIX.md`
- Create: `tests/compiler/fixtures/external_consumer_matrix.py`
- Create: `tests/compiler/test_mission_015_consumer_matrix.py`
- Create: `tests/compiler/fixtures/plain_language_envelope.json` (generated in the test from `plain_language_minimal.txt` is also acceptable — prefer writing the envelope in the test)

**Interfaces:**
- Consumes: `install_isolated` / `clean_child_env` from Task 2
- Produces: matrix script that imports **only** `promptrig.compiler.api` (`ClosedLoopOptions`, `closed_loop_from_json`)

- [ ] **Step 1: Write failing tests and matrix consumer**

`tests/compiler/fixtures/external_consumer_matrix.py`:

```python
"""Installed-package consumer: import only promptrig.compiler.api public paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from promptrig.compiler.api import ClosedLoopOptions, closed_loop_from_json


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: external_consumer_matrix.py <json> [--enable-model-suggestions]",
            file=sys.stderr,
        )
        return 2
    enable = "--enable-model-suggestions" in sys.argv
    raw = Path(sys.argv[1]).read_bytes()
    result = closed_loop_from_json(
        raw,
        ClosedLoopOptions(repair_budget=1, enable_model_suggestions=enable),
    )
    evidence = result.evidence_bundle or {}
    evaluation = evidence.get("evaluation") or {}
    proposal = evidence.get("model_proposal")
    payload = {
        "status": result.status,
        "diagnostics": list(result.diagnostics),
        "ir_sha256": evidence.get("ir_sha256"),
        "evaluation_status": evaluation.get("status"),
        "loop_id": evidence.get("loop_id"),
        "intake_profile": evidence.get("intake_profile"),
        "suggestion_profile": evidence.get("suggestion_profile"),
        "proposal_acceptance": None if proposal is None else proposal.get("acceptance_state"),
        "proposal_authority": None if proposal is None else proposal.get("authority_basis"),
        "proposed_records": None if proposal is None else proposal.get("proposed_records"),
    }
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`tests/compiler/test_mission_015_consumer_matrix.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from packaging_util import clean_child_env, install_isolated

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "tests" / "compiler" / "fixtures" / "external_consumer_matrix.py"
STRUCTURED = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"
PLAIN_TXT = ROOT / "tests" / "compiler" / "fixtures" / "plain_language_minimal.txt"
CREDENTIAL_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)


def _run_matrix(py: Path, json_path: Path, *flags: str) -> dict:
    env = clean_child_env()
    for key in CREDENTIAL_KEYS:
        env.pop(key, None)
    proc = subprocess.run(
        [str(py), str(MATRIX), str(json_path), *flags],
        cwd=json_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_consumer_matrix_doc_exists() -> None:
    text = Path("architecture/mission-015-certification/CONSUMER_MATRIX.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "promptrig.compiler.api" in lower
    assert "structured" in lower
    assert "plain_language_v0" in lower
    assert "fake-suggester-v0" in lower or "fake_suggester" in lower
    assert "simple mode" in lower
    assert "network_allowed" in lower


def test_installed_consumer_matrix(tmp_path: Path) -> None:
    py = install_isolated(ROOT, tmp_path / "venv")

    structured = _run_matrix(py, STRUCTURED)
    assert structured["status"] == "PASS"
    assert structured["ir_sha256"]
    assert structured["proposal_acceptance"] is None

    plain_envelope = {
        "profile": "plain_language_v0",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "repair_budget": 1,
        "text": PLAIN_TXT.read_text(encoding="utf-8"),
    }
    plain_path = tmp_path / "plain.json"
    plain_path.write_text(json.dumps(plain_envelope), encoding="utf-8")
    plain = _run_matrix(py, plain_path)
    assert plain["status"] == "PASS"
    assert plain["intake_profile"] == "plain_language_v0"

    suggested = _run_matrix(py, STRUCTURED, "--enable-model-suggestions")
    assert suggested["status"] == "PASS"
    assert suggested["suggestion_profile"] == "fake_suggester_v0"
    assert suggested["proposal_acceptance"] == "proposed"
    assert suggested["proposal_authority"] == "model_suggested"
    assert suggested["proposed_records"] == ["REQ-MS-001"]
    assert suggested["ir_sha256"] == structured["ir_sha256"]

    blocked_ui = {
        "profile": "plain_language_v0",
        "authoring_mode": "simple_ui_only",
        "contract_version": "0.1.0",
        "network_allowed": False,
        "text": "Goal: G\nRequirements:\n1. A\n",
    }
    ui_path = tmp_path / "ui.json"
    ui_path.write_text(json.dumps(blocked_ui), encoding="utf-8")
    ui = _run_matrix(py, ui_path)
    assert ui["status"] == "BLOCKED"
    assert any("Simple Mode" in d for d in ui["diagnostics"])

    net_doc = json.loads(STRUCTURED.read_text(encoding="utf-8"))
    net_doc["network_allowed"] = True
    net_path = tmp_path / "net.json"
    net_path.write_text(json.dumps(net_doc), encoding="utf-8")
    net = _run_matrix(py, net_path)
    assert net["status"] == "BLOCKED"
    assert any("network_allowed" in d for d in net["diagnostics"])
```

- [ ] **Step 2: Run — expect FAIL** (`CONSUMER_MATRIX.md` missing)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_consumer_matrix.py::test_consumer_matrix_doc_exists -v`

- [ ] **Step 3: Write CONSUMER_MATRIX.md**

```markdown
# Installed-package consumer matrix (MISSION-015)

Consumers import **only** `promptrig.compiler.api`. They run from an isolated venv install (no `PYTHONPATH=src`).

| Case | Input | Expect |
|---|---|---|
| Structured closed-loop | `closed_loop_requirements_minimal.json` | PASS, IR digest present, no proposal |
| `plain_language_v0` | grammar text envelope | PASS, `intake_profile=plain_language_v0` |
| Opt-in `fake-suggester-v0` | structured + `--enable-model-suggestions` | PASS, proposal `acceptance_state=proposed`, `authority_basis=model_suggested`, `proposed_records=["REQ-MS-001"]`, IR digest equals suggestion-off |
| Simple Mode | `authoring_mode=simple_ui_only` | BLOCKED, Simple Mode diagnostic |
| `network_allowed` true | structured doc with `network_allowed: true` | BLOCKED, network_allowed diagnostic |
| No credentials | credential env keys stripped | same PASS as structured (no key required) |

Existing PYTHONPATH smokes in MISSION-012/013/014 are not replaced.
```

- [ ] **Step 4: Run matrix tests**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_consumer_matrix.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add architecture/mission-015-certification/CONSUMER_MATRIX.md tests/compiler/fixtures/external_consumer_matrix.py tests/compiler/test_mission_015_consumer_matrix.py
git commit -m "test: certify installed-package consumer matrix"
```

---

### Task 4: Operational resource bounds

**Files:**
- Create: `src/promptrig/compiler/resource_bounds.py`
- Create: `architecture/mission-015-certification/RESOURCE_BOUNDS.md`
- Create: `tests/compiler/test_mission_015_resource_bounds.py`

**Interfaces:**
- Consumes: `run_closed_loop` + `ClosedLoopOptions` (existing)
- Produces: `WALL_SECONDS_MAX: float = 5.0` and `TRACEMALLOC_PEAK_BYTES_MAX: int = 8388608`

- [ ] **Step 1: Write failing tests**

```python
from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop
from promptrig.compiler.resource_bounds import TRACEMALLOC_PEAK_BYTES_MAX, WALL_SECONDS_MAX

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "compiler" / "fixtures" / "closed_loop_requirements_minimal.json"


def test_resource_bounds_doc_forbids_benchmark_claims() -> None:
    text = Path("architecture/mission-015-certification/RESOURCE_BOUNDS.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "not a benchmark" in lower or "not comparative" in lower
    assert "operational" in lower
    assert "5.0" in text
    assert "8388608" in text
    assert WALL_SECONDS_MAX == 5.0
    assert TRACEMALLOC_PEAK_BYTES_MAX == 8388608


def test_closed_loop_minimal_respects_operational_ceilings() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))  # warmup
    tracemalloc.start()
    t0 = time.perf_counter()
    result = run_closed_loop(doc, ClosedLoopOptions(repair_budget=1))
    elapsed = time.perf_counter() - t0
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result.status == "PASS"
    assert elapsed < WALL_SECONDS_MAX
    assert peak < TRACEMALLOC_PEAK_BYTES_MAX
```

- [ ] **Step 2: Run — expect FAIL** (`resource_bounds` import missing)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_resource_bounds.py -v`

- [ ] **Step 3: Implement module + markdown**

`src/promptrig/compiler/resource_bounds.py`:

```python
"""Operational fail-closed ceilings for the certified fake-adapter closed loop.

These are not comparative benchmark results (REJ-005).
"""

WALL_SECONDS_MAX = 5.0
TRACEMALLOC_PEAK_BYTES_MAX = 8388608
```

`architecture/mission-015-certification/RESOURCE_BOUNDS.md`:

```markdown
# Operational resource bounds (MISSION-015)

These are fail-closed **operational** ceilings for `run_closed_loop` on
`tests/compiler/fixtures/closed_loop_requirements_minimal.json` with
`repair_budget=1`. They are **not a benchmark** and are **not comparative**
product-performance claims (REJ-005).

Canonical values (must match `src/promptrig/compiler/resource_bounds.py`):

- `WALL_SECONDS_MAX` = 5.0
- `TRACEMALLOC_PEAK_BYTES_MAX` = 8388608 (8 MiB)

Basis: local measurement ~0.16s wall / ~153 KiB tracemalloc peak; 3× would be
~0.47s / ~459 KiB. Floors of 5.0 seconds and 8 MiB absorb CI variance.

Scope: fake adapter, offline, this fixture only. Not a live-provider bound.
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_resource_bounds.py -v`

- [ ] **Step 5: Commit**

```powershell
git add src/promptrig/compiler/resource_bounds.py architecture/mission-015-certification/RESOURCE_BOUNDS.md tests/compiler/test_mission_015_resource_bounds.py
git commit -m "test: add operational closed-loop resource ceilings"
```

---

### Task 5: CI wheel-install job

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `tests/compiler/test_mission_015_ci.py`

**Interfaces:**
- Consumes: Task 2 `[build-system]`; Task 3 matrix consumer (CI may use `external_consumer_closed_loop.py` for the one smoke)
- Produces: job `wheel-install` on `ubuntu-latest` / Python 3.11

- [ ] **Step 1: Write failing CI-shape test**

```python
from pathlib import Path


def test_ci_has_ubuntu_wheel_install_job() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "wheel-install:" in text
    assert "ubuntu-latest" in text
    assert "python -m build" in text
    assert "pip install" in text
    assert "promptrig-compiler doctor --json" in text
    assert "external_consumer_closed_loop.py" in text
    assert "install -e" in text  # existing editable matrix stays
```

- [ ] **Step 2: Run — expect FAIL** (`wheel-install:` missing)

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_ci.py -v`

- [ ] **Step 3: Append job to `.github/workflows/ci.yml`**

Keep the existing `test` and `typescript-drift` jobs unchanged. Append:

```yaml
  wheel-install:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build wheel
        run: |
          python -m pip install build
          python -m build

      - name: Isolated venv install
        run: |
          python -m venv /tmp/pr-wheel
          /tmp/pr-wheel/bin/pip install dist/*.whl

      - name: Doctor on installed wheel
        run: /tmp/pr-wheel/bin/promptrig-compiler doctor --json

      - name: Installed consumer smoke
        run: |
          /tmp/pr-wheel/bin/python tests/compiler/fixtures/external_consumer_closed_loop.py tests/compiler/fixtures/closed_loop_requirements_minimal.json
```

Do not add `psutil`. Do not duplicate the 6-cell OS/Python matrix for wheels.

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/Scripts/python -m pytest tests/compiler/test_mission_015_ci.py tests/compiler/test_mission_015_schedule.py -v`

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/ci.yml tests/compiler/test_mission_015_ci.py
git commit -m "ci: add ubuntu wheel-install clean-install job"
```

---

### Task 6: Report, OAR-009 draft, maturity honesty

**Files:**
- Create: `MISSION_015_REPORT.md`
- Create: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-009.md` (Ready for owner acceptance — **not** Accepted)
- Modify: `architecture/mission-015-certification/README.md` (status: evidence complete, awaiting OAR-009)
- Modify: `architecture/mission-012-certification/README.md` non-claims (point at 015 residual; still not full 4B exit)
- Modify: `architecture/mission-013-certification/README.md` same
- Modify: `architecture/mission-014-certification/README.md` same
- Modify: `architecture/strategy/CAPABILITY_MATURITY_MAP.md` (CI eight jobs; headless loop evidence cites 015 packaging/consumer/bounds; still not full 4B exit; Requirements compiler stays `PARTIAL`)
- Modify: `architecture/strategy/DEFERRED_AND_REJECTED_WORK.md` blocking bullet (narrow residual packaging/consumer/bounds exist; remaining unauthorized: live, freeform, M3, full 008, full 4B exit)
- Modify: `README.md` Status (honest 015 residual evidence; still no live/UI/freeform/full 4B exit)

**Interfaces:**
- Do **not** mark OAR-009 Accepted. Do **not** set Requirements compiler to `CERTIFIED`. Do **not** claim full Phase 4B exit.

OAR-009 draft body (Status line exactly `Ready for owner acceptance`):

```markdown
# OAR-009 — MISSION-015 Phase 4B Residual Evidence

**Status:** Ready for owner acceptance.

**Certified if accepted:** residual evidence for the already-certified offline fake-adapter closed loop — PEP 517 `[build-system]`, isolated-venv clean-install, installed-package public-API consumer matrix (structured / `plain_language_v0` / opt-in `fake-suggester-v0`, Simple Mode and `network_allowed=true` still BLOCKED), and operational resource ceilings `WALL_SECONDS_MAX=5.0` / `TRACEMALLOC_PEAK_BYTES_MAX=8388608` (not a benchmark). Repair budgets `{0,1,2}`, `EVR-SEC-0001`, `network_allowed=false` unchanged.

**Still unauthorized without new campaign:** live model-assisted suggestion, freeform NLP, M3 / Simple Mode UI semantics, live providers, full MISSION-008 production requirements compiler, full Roadmap Phase 4B exit, benchmarks/claims, hosted product surfaces, MissionRig, IR v0.2, enterprise SAST. Requirements compiler maturity remains **PARTIAL** after this record.
```

`MISSION_015_REPORT.md` must include: baseline `8fc5c43`; tasks 1–6; tests added; explicit non-claims matching OAR-009; note that ambition-gap C4 is not this mission.

Maturity map CI row: change "Seven jobs" to "Eight jobs: six OS/Python tests plus TypeScript drift plus Ubuntu wheel-install (MISSION-015)".

Headless-loop limitations: replace "single external-consumer smoke (not full matrix); thin perf ceilings" with language that MISSION-015 added installed-package consumer matrix + operational ceilings for the fake path; still not full Phase 4B exit.

012/013/014 README non-claim line about thin perf / smoke-not-matrix: rewrite to "Full Roadmap Phase 4B exit remains unauthorized. MISSION-015 adds installed-package consumer matrix and operational resource ceilings for this offline fake path (OAR-009)."

- [ ] **Step 1: Write docs from HEAD evidence**

- [ ] **Step 2: Run compiler+evaluation suite**

Run: `.venv/Scripts/python -m pytest tests/compiler tests/evaluation -q`

Expected: all PASS (387 prior + new 015 tests).

- [ ] **Step 3: Commit**

```powershell
git add MISSION_015_REPORT.md architecture/OWNER_ACCEPTANCE_RECORDS/OAR-009.md architecture/mission-015-certification/README.md architecture/mission-012-certification/README.md architecture/mission-013-certification/README.md architecture/mission-014-certification/README.md architecture/strategy/CAPABILITY_MATURITY_MAP.md architecture/strategy/DEFERRED_AND_REJECTED_WORK.md README.md
git commit -m "docs: MISSION-015 report and OAR-009 draft for residual 4B evidence"
```

---

## Spec Coverage Check

- Clean-install / PEP 517: Tasks 2, 5
- Installed consumer matrix (structured, M1, M2 sidecar, Simple Mode, network, no credentials): Task 3
- Operational resource ceilings, not benchmarks: Task 4
- CI wheel-install job + eight-job honesty: Tasks 5, 6
- Residual-only OAR-009, compiler stays PARTIAL, no full 4B exit: Tasks 1, 6
- M3, live providers, freeform NLP, IR v0.2, C4 planning: out of scope

## Pre-flight (plan vs review rubric)

- Reviewer flags "full Phase 4B exit" as a defect — Tasks 1 and 6 keep residual disclosure. Governs.
- Resource tests labeled operational / not a benchmark — REJ-005 aligned.
- Maturity map "seven jobs" is updated in Task 6 after Task 5 adds the eighth job. Governs.

## Worktree / stacking

- Branch: `feature/mission-015-phase4b-residual`
- Worktree: `.worktrees/mission-015-phase4b-residual`
- Baseline: `main` @ `8fc5c43`
- After whole-branch review: stop. No push, PR, merge, or OAR Accepted unless Boss asks.
