"""`proofhouse-compiler models list|show|remember|forget` through cli_compiler.main()."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import cli as optimize_cli
from proofhouse.optimize import registry


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    return tmp_path


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


def test_local_commands_and_exit_codes_match_compiler() -> None:
    assert optimize_cli.LOCAL_COMMANDS == frozenset({"optimize", "models", "install-skill"})
    assert optimize_cli.LOCAL_COMMANDS <= cli_compiler.COMPILER_COMMANDS
    assert "models" in cli_compiler.COMPILER_COMMANDS
    assert optimize_cli.EXIT_SUCCESS == cli_compiler.EXIT_SUCCESS == 0
    assert optimize_cli.EXIT_USAGE_ERROR == cli_compiler.EXIT_USAGE_ERROR == 2
    assert optimize_cli.EXIT_CHECK_FAILED == cli_compiler.EXIT_VALIDATION_FAILURE == 3
    assert optimize_cli.EXIT_ENVIRONMENT_FAILURE == cli_compiler.EXIT_ENVIRONMENT_FAILURE == 7


def test_models_list_json_has_eighteen_builtin(capsys) -> None:
    code, out, err = _run(["models", "list", "--json"], capsys)
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "models list"
    assert payload["status"] == "success"
    data = payload["data"]
    assert set(data) == {"builtin", "cached", "stale_after_days"}
    assert len(data["builtin"]) == 18
    assert data["cached"] == []
    assert data["stale_after_days"] == 90
    assert data["builtin"][0]["canonical_id"] == "claude-fable-5-1"
    assert data["builtin"][0]["source"] == "builtin"
    assert data["builtin"][-1]["canonical_id"] == "other"


def test_models_list_human_header_and_rows(capsys, tmp_path: Path) -> None:
    notes = tmp_path / "zeta.md"
    notes.write_text("Zeta notes\n", encoding="utf-8")
    assert _run(["models", "remember", "Zeta 9", "--notes-file", str(notes), "--verified-at", "2026-09-20"], capsys)[0] == 0
    code, out, err = _run(["models", "list"], capsys)
    assert code == 0 and err == ""
    lines = out.splitlines()
    assert lines[0] == "models: 18 builtin, 1 cached (registry v1.3, stale after 90 days)"
    assert lines[1] == f"  {'claude-fable-5-1':<20} {'Claude Fable 5.1':<20} {'Anthropic':<10} {'current':<8} reviewed 2026-09-03 unverified"
    assert lines[18] == f"  {'other':<20} {'Other':<20} {'-':<10} {'generic':<8} reviewed - unverified"
    assert lines[19] == f"  {'zeta-9':<20} {'Zeta 9':<20} {'-':<10} {'cached':<8} reviewed 2026-09-20 unverified"
    assert len(lines) == 20
    assert "STALE" not in out


def test_models_show_json_builtin_alias(capsys) -> None:
    code, out, err = _run(["models", "show", "GPT-5.6 Sol", "--json"], capsys)
    assert code == 0 and err == ""
    payload = _json(out)
    assert payload["command"] == "models show"
    assert payload["status"] == "success"
    data = payload["data"]
    assert data["canonical_id"] == "gpt-5-6-sol"
    assert data["entered_name"] == "GPT-5.6 Sol"
    assert data["source"] == "builtin"
    assert data["verified_at"] == "2026-09-03"
    assert data["stale"] is False
    assert data["provider"] == "OpenAI"
    assert data["sources"] == []


def test_models_show_unknown_is_fallback_with_warning(capsys) -> None:
    code, out, err = _run(["models", "show", "Zeta 9"], capsys)
    assert code == 0
    assert err == 'warning: no notes for "Zeta 9"; using the generic profile (source=fallback)\n'
    lines = out.splitlines()
    assert lines[0] == "model: Zeta 9"
    assert lines[1] == "  entered: Zeta 9"
    assert lines[2] == "  canonical_id: zeta-9"
    assert lines[3] == "  provider: -  tier: generic"
    assert lines[4] == "  source: fallback  verified_at: -  stale: no"
    assert lines[5] == "  sources: none recorded"
    assert lines[6] == "  evidence: unverified"
    assert lines[7].startswith("  notes: No verified vendor-specific behavior available.")

    code, out, err = _run(["models", "show", "Zeta 9", "--json"], capsys)
    assert code == 0
    assert "source=fallback" in err
    payload = _json(out)
    assert payload["status"] == "warning"
    assert payload["data"]["source"] == "fallback"


def test_models_remember_show_forget_roundtrip(capsys, tmp_path: Path) -> None:
    notes = tmp_path / "zeta.md"
    notes.write_text("Zeta 9 prefers numbered constraints.\n", encoding="utf-8")
    code, out, err = _run(
        ["models", "remember", "Zeta 9", "--notes-file", str(notes), "--source-url", "https://example.invalid/doc"],
        capsys,
    )
    assert code == 0 and err == ""
    expected_path = tmp_path / "model-notes" / "zeta-9.json"
    assert out == f"remembered: zeta-9 -> {expected_path}\n"
    assert expected_path.is_file()

    code, out, err = _run(["models", "show", "Zeta 9", "--json"], capsys)
    assert code == 0 and err == ""
    data = _json(out)["data"]
    assert data["source"] == "cached"
    assert data["sources"] == ["https://example.invalid/doc"]
    assert data["notes"] == "Zeta 9 prefers numbered constraints."
    assert data["provenance"] == "notes file zeta.md"
    assert data["verified_at"] == registry.today().isoformat()

    code, out, err = _run(["models", "show", "zeta-9"], capsys)
    assert code == 0 and err == ""
    assert "  source: cached  verified_at: " in out
    assert "  sources: https://example.invalid/doc" in out

    code, out, err = _run(["models", "forget", "Zeta 9"], capsys)
    assert code == 0 and err == ""
    assert out == "forgot: zeta-9\n"
    assert not expected_path.exists()

    code, out, err = _run(["models", "forget", "Zeta 9", "--json"], capsys)
    assert code == 2
    assert out == ""
    assert err == 'error: nothing cached for "Zeta 9"\n'


def test_models_remember_usage_errors(capsys, tmp_path: Path) -> None:
    code, out, err = _run(["models", "remember", "Zeta 9", "--notes-file", str(tmp_path / "missing.md")], capsys)
    assert code == 2 and out == ""
    assert err.startswith("error: notes file not found: ")

    empty = tmp_path / "empty.md"
    empty.write_text("   \n", encoding="utf-8")
    code, out, err = _run(["models", "remember", "Zeta 9", "--notes-file", str(empty)], capsys)
    assert code == 2 and err.startswith("error: notes file is empty: ")

    notes = tmp_path / "zeta.md"
    notes.write_text("ok", encoding="utf-8")
    code, out, err = _run(["models", "remember", "Zeta 9", "--notes-file", str(notes), "--verified-at", "21/09/2026"], capsys)
    assert code == 2 and err == "error: --verified-at must be YYYY-MM-DD\n"

    code, out, err = _run(["models", "show", "!!!"], capsys)
    assert code == 2 and err.startswith("error: ")
    assert not (tmp_path / "model-notes").exists()


def test_models_show_human_first_line(capsys) -> None:
    code, out, err = _run(["models", "show", "opus 5"], capsys)
    assert code == 0 and err == ""
    lines = out.splitlines()
    assert lines[0] == "model: Claude Opus 5"
    assert lines[1] == "  entered: opus 5"
    assert lines[2] == "  canonical_id: claude-opus-5"
    assert lines[3] == "  provider: Anthropic  tier: current"
    assert lines[4] == "  source: builtin  verified_at: 2026-09-03  stale: no"
    assert lines[5] == "  sources: none recorded"
    assert lines[6] == "  evidence: unverified"
    assert lines[7].startswith("  notes: ")


def test_models_show_stale_warning_from_injected_today(capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "today", lambda: date(2027, 1, 1))
    age = (date(2027, 1, 1) - date(2026, 9, 3)).days
    code, out, err = _run(["models", "show", "Sonnet 5"], capsys)
    assert code == 0
    assert err == (
        f"warning: notes for Claude Sonnet 5 were last reviewed 2026-09-03 ({age} days ago; threshold 90); "
        "re-check pricing, context, and settings against vendor docs\n"
    )
    assert "  source: builtin  verified_at: 2026-09-03  stale: yes" in out

    code, out, err = _run(["models", "list"], capsys)
    assert code == 0
    assert out.splitlines()[4].endswith("reviewed 2026-09-03 unverified  STALE")
    assert out.splitlines()[18].endswith("reviewed - unverified")

    code, out, err = _run(["models", "show", "Sonnet 5", "--json"], capsys)
    payload = _json(out)
    assert payload["status"] == "warning"
    assert payload["data"]["stale"] is True
    assert payload["data"]["age_days"] == age


def test_models_help_is_ascii_and_lists_subcommands(capsys) -> None:
    code, out, err = _run(["models", "--help"], capsys)
    assert code == 0
    (out + err).encode("ascii")
    for name in ("list", "show", "remember", "forget"):
        assert name in out
    code, out, err = _run(["models"], capsys)
    assert code == 2
