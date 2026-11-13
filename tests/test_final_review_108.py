"""What the last independent review of 108 found, each one kept from coming back."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from proofhouse import agent_server, capture, demo_make, loop, mcp_server, scrub, sitecheck
from proofhouse.mcp_server import ToolError, Tools

from test_loop_engine import PY, Agent


@pytest.fixture
def project(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    return work


# -- the loop's check must not be a way for the agent to read your keys ---------------------------------------
def test_the_check_does_not_see_secret_named_variables_so_the_agent_cannot_read_them_through_it(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The agent may write a file the check runs (a conftest.py, say). If the check had the keys, that file could
    save one in another form, which no scrubbing would recognise, for the agent to read in the next round."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk-very-secret-value")
    check = f'{PY} -c "import os, base64; print(base64.b64encode(os.environ.get(\'GROQ_API_KEY\', \'NOT-SET\').encode()).decode()); raise SystemExit(1)"'
    agent = Agent({"actions": [], "done": True, "summary": "ok"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, check=check, max_rounds=2,
                  out_dir=tmp_path / "r", transport=agent)
    assert "Tk9ULVNFVA==" in agent.seen[0]  # base64 of NOT-SET: the check never had the key
    assert "Z3NrLXZlcnktc2VjcmV0LXZhbHVl" not in "".join(agent.seen)


def test_a_variable_the_check_needs_can_be_kept_by_name_and_its_value_is_still_scrubbed(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "ghp-check-secret-value")
    monkeypatch.setenv("OTHER_TOKEN", "other-secret-value")
    check = f'{PY} -c "import os; print(os.environ[\'GH_TOKEN\'], os.environ.get(\'OTHER_TOKEN\', \'NOT-SET\')); raise SystemExit(1)"'
    agent = Agent({"actions": [], "done": True, "summary": "ok"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, check=check, keep_env=["gh_token"],
                  max_rounds=2, out_dir=tmp_path / "r", transport=agent)
    assert "[redacted] NOT-SET" in agent.seen[0]
    assert all("ghp-check-secret-value" not in seen for seen in agent.seen)
    assert loop.held_back(["GH_TOKEN"]).count("OTHER_TOKEN") == 1 and "GH_TOKEN" not in loop.held_back(["GH_TOKEN"])


# -- secrets that do not have a secret-sounding name ----------------------------------------------------------
def test_an_address_with_a_login_in_it_counts_as_a_secret_whatever_its_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "rediss://default:hunter2hunter2@example.upstash.io:6379")
    monkeypatch.setenv("SENTRY_DSN", "https://abc123abc123@o1.ingest.sentry.io/42")
    monkeypatch.setenv("GITHUB_PAT", "ghp-a-personal-one")
    monkeypatch.setenv("DOCS_URL", "https://example.com/docs")
    values = scrub.secret_values()
    assert "rediss://default:hunter2hunter2@example.upstash.io:6379" in values
    assert "https://abc123abc123@o1.ingest.sentry.io/42" in values and "ghp-a-personal-one" in values
    assert "https://example.com/docs" not in values
    assert scrub.is_secret("REDIS_URL", os.environ["REDIS_URL"]) and not scrub.is_secret("DOCS_URL", os.environ["DOCS_URL"])


# -- the bridge: a model name is a name, never part of a command ----------------------------------------------
@pytest.mark.parametrize("model", ["x&calc", "m | whoami", "a b", "$(id)", "m;rm", "-rf", "m^n", 'm"n', "m%PATH%"])
def test_a_model_name_with_command_characters_is_refused_before_any_agent_is_started(model: str) -> None:
    entry = {"argv": ["codex", "exec", "-"], "model_flag": ["--model", "{model}"]}
    with pytest.raises(agent_server.AgentError, match="model name"):
        agent_server.build_argv(entry, model, "codex")


@pytest.mark.parametrize("model", ["gpt-6.1-sol", "claude-fable-5-2", "org/model:tag", "llama3.3:70b", "name@2026-01-01"])
def test_ordinary_model_names_still_go_through(model: str) -> None:
    entry = {"argv": ["codex", "exec", "-"], "model_flag": ["--model", "{model}"]}
    assert agent_server.build_argv(entry, model, "codex") == ["codex", "exec", "--model", model, "-"]


@pytest.mark.skipif(os.name != "nt", reason="Windows file permissions; elsewhere the file is made with mode 600")
def test_on_windows_the_saved_token_does_not_take_its_readers_from_the_folder_it_is_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    monkeypatch.delenv(agent_server.TOKEN_ENV, raising=False)
    _, path = agent_server.bridge_token()
    listed = subprocess.run(["icacls", str(path)], capture_output=True, text=True, check=True).stdout
    assert "(I)" not in listed  # nothing inherited: only the entry Proofhouse wrote
    again, _ = agent_server.bridge_token()
    assert again == path.read_text(encoding="utf-8").strip()


# -- the chat tools ------------------------------------------------------------------------------------------
def _tools(base: Path) -> tuple[Tools, demo_make.Recorded, dict]:
    data = demo_make.recording()
    model = demo_make.Recorded(data)
    return Tools(base=base, transport=model, wait=60.0), model, data


def test_a_make_folder_outside_the_records_folder_is_refused(tmp_path: Path) -> None:
    base, planted = tmp_path / "makes", tmp_path / "elsewhere" / "make-x"
    base.mkdir()
    planted.mkdir(parents=True)
    (planted / mcp_server.SESSION_FILE).write_text(json.dumps(
        {"request": "x", "kind": "prompt", "provider": "ollama", "model": "m", "max_cost_usd": "999"}), encoding="utf-8")
    tools, model, _ = _tools(base)
    for call in (tools.make_status, tools.make_answer, tools.make_confirm):
        with pytest.raises(ToolError, match="not a make started from chat"):
            call({"make": str(planted), "confirmed": True})
    with pytest.raises(ToolError, match="not a make started from chat"):
        tools.make_status({"make": str(base / ".." / "elsewhere" / "make-x")})
    assert model.calls == [] and not (planted / "answers.json").exists()


def test_a_say_back_that_was_never_handed_over_cannot_be_confirmed(tmp_path: Path) -> None:
    tools, model, data = _tools(tmp_path)
    make = tools.make_start({"request": data["request"], "kind": data["kind"], "provider": "ollama",
                             "model": demo_make.MODEL, "for": data["for"]})
    asked = make if make["stage"] == "questions" else tools.make_status({"make": make["make"]})
    answers = {q["id"]: (q["options"][0] if q.get("options") else "whatever reads best") for q in asked["questions"]}
    said = tools.make_answer({"make": make["make"], "answers": answers})
    assert said["stage"] == "say_back"

    # a new server (the app was restarted) has handed nothing over yet: the confirm shows the say-back instead
    fresh = Tools(base=tmp_path, transport=model, wait=60.0)
    shown = fresh.make_confirm({"make": make["make"], "confirmed": True})
    assert shown["stage"] == "say_back" and shown["say_back"] and "not been shown" in shown["next"]
    assert "write" not in model.calls and not (Path(make["make"]) / "record.json").exists()

    # after a correction the say-back is a new one, and it comes back with the correction, so it can be confirmed
    changed = fresh.make_confirm({"make": make["make"], "correction": "Skip merge commits."})
    assert changed["stage"] == "say_back"
    done = fresh.make_confirm({"make": make["make"], "confirmed": True})
    assert done["stage"] == "done"


# -- the browser keeps its own safety wall --------------------------------------------------------------------
def test_the_browser_runs_with_its_sandbox_unless_you_switch_it_off_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sitecheck.NO_SANDBOX_ENV, raising=False)
    assert sitecheck.sandbox_flags() == []
    assert "--no-sandbox" not in capture.screenshot_command("chrome", "file:///x.html", (10, 10), Path("o.png"))
    monkeypatch.setenv(sitecheck.NO_SANDBOX_ENV, "1")
    assert sitecheck.sandbox_flags() == ["--no-sandbox"]
    assert "--no-sandbox" in capture.screenshot_command("chrome", "file:///x.html", (10, 10), Path("o.png"))
