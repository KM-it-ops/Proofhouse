"""`proofhouse-compiler optimize new|compile|record|revise|status` through cli_compiler.main()."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import packets, registry
from proofhouse.optimize.case import CASE_SCHEMA

OBJECTIVE = "Summarise a security advisory for a SOC audience"
SONNET_NOTES = (
    "Fast, capable default. Concise, direct instructions; doesn't need heavy scaffolding. "
    "Good for genuine iteration."
)


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _json(out: str) -> dict:
    assert out.endswith("\n")
    payload = json.loads(out)
    assert set(payload) == {"command", "status", "data"}
    assert json.dumps(payload, sort_keys=True) + "\n" == out
    return payload


def _new(case_dir: Path, capsys, *extra: str) -> tuple[int, str, str]:
    return _run(["optimize", "new", "--case", str(case_dir), "--objective", OBJECTIVE, "--model", "Sonnet 5", *extra], capsys)


def _record(case_dir: Path, tmp_path: Path, name: str, prompt: str, capsys, *extra: str) -> tuple[int, str, str]:
    prompt_file = tmp_path / name
    prompt_file.write_text(prompt, encoding="utf-8")
    return _run(["optimize", "record", "--case", str(case_dir), "--prompt-file", str(prompt_file), *extra], capsys)


def test_new_writes_case_files_and_builtin_model(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-a"
    code, out, err = _new(case_dir, capsys)
    assert code == 0 and err == ""
    for name in ("case.json", "01-clarify.md", "answers.json"):
        assert (case_dir / name).is_file(), name
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert case["schema"] == CASE_SCHEMA == "proofhouse.optimize.case/v0"
    assert case["objective"] == OBJECTIVE
    assert case["model"]["source"] == "builtin"
    assert case["model"]["canonical_id"] == "claude-sonnet-5"
    assert case["model"]["entered_name"] == "Sonnet 5"
    assert case["preset"] == "balanced"
    assert case["loop"] is False
    assert case["stage"] == "clarify"
    assert case["revisions"] == []
    assert case["criteria"] == []
    assert (case_dir / "answers.json").read_text(encoding="utf-8") == "{}\n"
    clarify = (case_dir / "01-clarify.md").read_text(encoding="utf-8")
    assert clarify.startswith("# Proofhouse packet: clarify\n")
    assert SONNET_NOTES in clarify
    assert OBJECTIVE in clarify
    assert "{{" not in clarify

    lines = out.splitlines()
    resolved_dir = case_dir.resolve()
    assert lines[0] == f"optimize: new case {resolved_dir}"
    assert lines[1] == "  model: Claude Sonnet 5 (claude-sonnet-5) source=builtin verified_at=2026-09-03 stale=no"
    assert lines[2] == "  preset: balanced  loop: no"
    assert lines[3] == "  wrote: case.json, 01-clarify.md, answers.json"
    assert lines[4] == (
        "  next: run 01-clarify.md in your host agent, put answers in answers.json, then: "
        f"proofhouse-compiler optimize compile --case {resolved_dir}"
    )
    assert len(lines) == 5


def test_new_on_existing_dir_is_usage_error(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-b"
    assert _new(case_dir, capsys)[0] == 0
    code, out, err = _new(case_dir, capsys)
    assert code == 2 and out == ""
    assert err.startswith("error: case directory already exists: ")
    code, out, err = _run(["optimize", "new", "--case", str(tmp_path / "case-c"), "--model", "Sonnet 5"], capsys)
    assert code == 2 and out == ""


def test_compile_requires_answers_then_renders_them(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-d"
    assert _new(case_dir, capsys)[0] == 0
    code, out, err = _run(["optimize", "compile", "--case", str(case_dir)], capsys)
    assert code == 2 and out == ""
    assert err == "error: answers.json is empty; answer the clarify packet first\n"
    assert not (case_dir / "02-compile.md").exists()

    (case_dir / "answers.json").write_text(
        json.dumps({"audience": "SOC analysts", "length": "under 200 words"}), encoding="utf-8"
    )
    code, out, err = _run(["optimize", "compile", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    packet_path = (case_dir / "02-compile.md").resolve()
    lines = out.splitlines()
    assert lines[0] == f"optimize: compile packet -> {packet_path}"
    assert lines[1] == (
        "  next: run it, save the compiled prompt text, then: "
        f"proofhouse-compiler optimize record --case {case_dir.resolve()} --prompt-file <file>"
    )
    text = packet_path.read_text(encoding="utf-8")
    assert text.startswith("# Proofhouse packet: compile\n")
    assert "- audience: SOC analysts" in text
    assert "- length: under 200 words" in text
    assert SONNET_NOTES in text
    assert "{{" not in text
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert case["stage"] == "compile"

    alt = tmp_path / "alt-answers.json"
    alt.write_text(json.dumps([{"question": "Who reads it?", "answer": "the SOC lead"}]), encoding="utf-8")
    code, out, err = _run(["optimize", "compile", "--case", str(case_dir), "--answers", str(alt), "--json"], capsys)
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "optimize compile"
    assert payload["status"] == "success"
    assert "- Who reads it?: the SOC lead" in packet_path.read_text(encoding="utf-8")


def test_record_twice_creates_v1_v2_with_distinct_sha(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-e"
    assert _new(case_dir, capsys)[0] == 0
    prompt_one = "Summarise the advisory in under 200 words for SOC analysts."
    code, out, err = _record(case_dir, tmp_path, "p1.txt", prompt_one, capsys, "--rationale", "first pass")
    assert code == 0 and err == ""
    sha_one = hashlib.sha256(prompt_one.encode("utf-8")).hexdigest()
    est_one = math.ceil(len(prompt_one) / 4)
    assert out == f"optimize: recorded revision v1 ({est_one} est. tokens, sha256 {sha_one[:12]}...)\n"

    prompt_two = prompt_one + " Lead with severity and affected versions."
    code, out, err = _record(case_dir, tmp_path, "p2.txt", prompt_two, capsys, "--json")
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "optimize record"
    assert payload["data"]["revision"]["n"] == 2

    v1 = json.loads((case_dir / "revisions" / "v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((case_dir / "revisions" / "v2.json").read_text(encoding="utf-8"))
    assert set(v1) == {
        "n", "prompt", "rationale", "settings", "efficiency", "sha256", "token_estimate", "created_at", "feedback_on_previous"
    }
    assert v1["n"] == 1 and v2["n"] == 2
    assert v1["prompt"] == prompt_one and v2["prompt"] == prompt_two
    assert v1["rationale"] == "first pass" and v2["rationale"] == ""
    assert v1["sha256"] == sha_one
    assert v1["sha256"] != v2["sha256"]
    assert v1["token_estimate"] == est_one
    assert v1["feedback_on_previous"] is None

    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert [r["n"] for r in case["revisions"]] == [1, 2]
    assert case["revisions"][0]["path"] == "revisions/v1.json"
    assert case["revisions"][0]["sha256"] == sha_one
    assert set(case["revisions"][0]) == {"n", "path", "sha256", "token_estimate", "created_at", "feedback_on_previous"}


def test_revise_from_earlier_revision_quotes_that_prompt(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-f"
    assert _new(case_dir, capsys)[0] == 0
    code, out, err = _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "too long"], capsys)
    assert code == 2 and err == "error: no revisions recorded; run record first\n"

    prompt_one = "FIRST-PROMPT: summarise the advisory."
    prompt_two = "SECOND-PROMPT: summarise the advisory with severity first."
    assert _record(case_dir, tmp_path, "p1.txt", prompt_one, capsys)[0] == 0
    assert _record(case_dir, tmp_path, "p2.txt", prompt_two, capsys)[0] == 0

    code, out, err = _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "too long", "--revision", "1"], capsys)
    assert code == 0 and err == ""
    packet_path = (case_dir / "03-revise-v1.md").resolve()
    lines = out.splitlines()
    assert lines[0] == f"optimize: revise packet for v1 -> {packet_path}"
    # Revisions are append-only: resuming from v1 after two records still yields v3 next.
    assert lines[1] == "  next: run it, then record the result as v3"
    text = packet_path.read_text(encoding="utf-8")
    assert text.startswith("# Proofhouse packet: revise v1\n")
    assert prompt_one in text
    assert prompt_two not in text
    assert 'User feedback on that version: "too long"' in text
    assert f"~{math.ceil(len(prompt_one) / 4)} tokens" in text

    code, out, err = _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "shorter"], capsys)
    assert code == 0 and err == ""
    assert out.splitlines()[0] == f"optimize: revise packet for v2 -> {(case_dir / '03-revise-v2.md').resolve()}"
    assert out.splitlines()[1] == "  next: run it, then record the result as v3"
    assert prompt_two in (case_dir / "03-revise-v2.md").read_text(encoding="utf-8")

    code, out, err = _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "x", "--revision", "9"], capsys)
    assert code == 2 and err == "error: revision v9 does not exist (latest is v2)\n"

    assert _record(case_dir, tmp_path, "p3.txt", "THIRD-PROMPT", capsys)[0] == 0
    v3 = json.loads((case_dir / "revisions" / "v3.json").read_text(encoding="utf-8"))
    assert v3["feedback_on_previous"] == "shorter"
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert case["stage"] == "revise"
    assert case["revisions"][2]["feedback_on_previous"] == "shorter"


def test_user_text_with_template_markers_survives_new_compile_revise(tmp_path: Path, capsys) -> None:
    case_dir = tmp_path / "case-m"
    objective = "Draft a Jinja template that prints {{x}} and {{ user.name }}"
    code, out, err = _run(["optimize", "new", "--case", str(case_dir), "--objective", objective, "--model", "Sonnet 5"], capsys)
    assert code == 0 and err == ""
    assert objective in (case_dir / "01-clarify.md").read_text(encoding="utf-8")
    (case_dir / "answers.json").write_text(json.dumps({"engine": "use {{loop.index}} inside"}), encoding="utf-8")
    code, out, err = _run(["optimize", "compile", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    assert "- engine: use {{loop.index}} inside" in (case_dir / "02-compile.md").read_text(encoding="utf-8")
    assert _record(case_dir, tmp_path, "pm.txt", "Render {{slot}} then stop.", capsys)[0] == 0
    code, out, err = _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "keep {{x}} literal"], capsys)
    assert code == 0 and err == ""
    text = (case_dir / "03-revise-v1.md").read_text(encoding="utf-8")
    assert "Render {{slot}} then stop." in text
    assert 'User feedback on that version: "keep {{x}} literal"' in text


def test_unknown_template_key_is_usage_error_not_traceback(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = tmp_path / "case-n"
    assert _new(case_dir, capsys)[0] == 0
    (case_dir / "answers.json").write_text(json.dumps({"q": "a"}), encoding="utf-8")
    broken = json.loads(json.dumps(packets.framework()))
    broken["systemPrompts"]["compilePrompt"]["userTemplateFirstPass"] += "\n{{notAKey}}"
    monkeypatch.setattr(packets, "framework", lambda: broken)
    code, out, err = _run(["optimize", "compile", "--case", str(case_dir)], capsys)
    assert code == 2 and out == ""
    assert err == "error: unfilled placeholder {{notAKey}} in template\n"
    assert not (case_dir / "02-compile.md").exists()


def test_notes_file_is_researched_and_not_cached(tmp_path: Path, home: Path, capsys) -> None:
    notes = tmp_path / "zeta.md"
    notes.write_text("Zeta 9 prefers numbered constraints.\n", encoding="utf-8")
    case_dir = tmp_path / "case-g"
    code, out, err = _run(
        [
            "optimize", "new", "--case", str(case_dir), "--objective", OBJECTIVE, "--model", "Zeta 9",
            "--notes-file", str(notes), "--preset", "efficient", "--loop", "--json",
        ],
        capsys,
    )
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "optimize new"
    model = payload["data"]["case"]["model"]
    assert model["source"] == "researched"
    assert model["provenance"] == "notes file zeta.md"
    assert model["verified_at"] == registry.today().isoformat()
    assert model["canonical_id"] == "zeta-9"
    assert model["entered_name"] == "Zeta 9"
    assert model["notes"] == "Zeta 9 prefers numbered constraints."
    assert not (home / "model-notes").exists()
    clarify = (case_dir / "01-clarify.md").read_text(encoding="utf-8")
    assert "Zeta 9 prefers numbered constraints." in clarify
    assert "Loop & Recurrence" in clarify
    assert "Efficient (tightest possible prompt, minimum viable questions)" in clarify
    assert "source=researched" in clarify


def test_status_reports_stage_counts_and_stale_warning(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = tmp_path / "case-h"
    assert _new(case_dir, capsys)[0] == 0
    assert _record(case_dir, tmp_path, "p1.txt", "one", capsys)[0] == 0
    code, out, err = _run(["optimize", "status", "--case", str(case_dir)], capsys)
    assert code == 0 and err == ""
    assert out.splitlines() == [
        f"case: {case_dir.resolve()}",
        "  stage: clarify",
        "  model: Claude Sonnet 5 (claude-sonnet-5) source=builtin verified_at=2026-09-03 stale=no",
        "  revisions: 1",
        "  criteria: 0",
    ]

    monkeypatch.setattr(registry, "today", lambda: date(2027, 1, 1))
    age = (date(2027, 1, 1) - date(2026, 9, 3)).days
    warning = (
        f"warning: notes for Claude Sonnet 5 were verified 2026-09-03 ({age} days ago; threshold 90); "
        "re-check pricing, context, and settings against vendor docs\n"
    )
    code, out, err = _run(["optimize", "status", "--case", str(case_dir), "--json"], capsys)
    assert code == 0 and err == warning
    payload = _json(out)
    assert payload["command"] == "optimize status"
    assert payload["status"] == "warning"
    assert payload["data"]["model"]["stale"] is True
    assert payload["data"]["revisions"] == 1

    code, out, err = _new(tmp_path / "case-i", capsys)
    assert code == 0 and err == warning
    assert "stale=yes" in out

    code, out, err = _run(["optimize", "status", "--case", str(tmp_path / "nope")], capsys)
    assert code == 2 and err.startswith("error: case not found: ")


def test_optimize_help_is_ascii_and_packets_have_no_endpoints(tmp_path: Path, capsys) -> None:
    code, out, err = _run(["optimize", "--help"], capsys)
    assert code == 0
    (out + err).encode("ascii")
    for name in ("new", "compile", "record", "revise", "status"):
        assert name in out
    for name in ("new", "compile", "record", "revise", "status"):
        code, out, err = _run(["optimize", name, "--help"], capsys)
        assert code == 0
        (out + err).encode("ascii")
    code, out, err = _run(["optimize"], capsys)
    assert code == 2

    case_dir = tmp_path / "case-j"
    assert _new(case_dir, capsys)[0] == 0
    (case_dir / "answers.json").write_text('{"a": "b"}', encoding="utf-8")
    assert _run(["optimize", "compile", "--case", str(case_dir)], capsys)[0] == 0
    assert _record(case_dir, tmp_path, "p.txt", "prompt", capsys)[0] == 0
    assert _run(["optimize", "revise", "--case", str(case_dir), "--feedback", "f"], capsys)[0] == 0
    for path in case_dir.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for forbidden in ("api.anthropic", "openai.com", "api_key"):
                assert forbidden not in text, path
