"""Agents that run on their own: act, check, repeat; or watch and act. One spending limit; every round recorded."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, live, loop

PY = f'"{sys.executable}"'
CHECK = f'{PY} -c "import calc; assert calc.add(2, 2) == 4"'


class Agent:
    """A scripted model: hands back one planned round per call and keeps what it was shown."""

    def __init__(self, *rounds: dict) -> None:
        self.rounds = list(rounds)
        self.seen: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        self.seen.append(json.loads(request.body_bytes)["messages"][-1]["content"])
        plan = self.rounds.pop(0) if self.rounds else {"actions": [], "summary": "waiting"}
        return live.Response(200, {"choices": [{"message": {"content": "Plan:\n" + json.dumps(plan)}}],
                                   "usage": {"prompt_tokens": 400, "completion_tokens": 100}})


@pytest.fixture
def project(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    (work / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    return work


def test_the_agent_works_until_the_check_passes_and_every_round_is_kept(tmp_path: Path, project: Path) -> None:
    agent = Agent(
        {"thinking": "look first", "actions": [{"read": "calc.py"}], "summary": "read calc.py"},
        {"actions": [{"write": "calc.py", "text": "def add(a, b):\n    return a + b\n"}], "summary": "fixed add"},
    )
    made = loop.run_loop("make the check pass", provider_id="ollama", model="llama3", workdir=project, check=CHECK,
                         out_dir=tmp_path / "rec", transport=agent)
    assert made.stopped == "check passed" and made.done and made.calls == 2
    assert "return a - b" in agent.seen[1] and "CHECK COMMAND RIGHT NOW: exit 1" in agent.seen[0]
    lines = [json.loads(line) for line in (tmp_path / "rec" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [line["summary"] for line in lines] == ["read calc.py", "fixed add"] and lines[1]["check"]["exit"] == 0
    record = json.loads((tmp_path / "rec" / "loop.json").read_text(encoding="utf-8"))
    assert record["done"] is True and record["calls"] == 2 and record["commands_allowed"] is False
    assert record["proofhouse_version"] == proofhouse.__version__


def test_nothing_is_sent_when_the_check_already_passes(tmp_path: Path, project: Path) -> None:
    (project / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    agent = Agent()
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=project, check=CHECK, out_dir=tmp_path / "r", transport=agent)
    assert made.stopped == "check passed" and made.calls == 0 and agent.seen == []


def test_commands_need_your_permission_and_keys_never_leave(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-very-secret-value")
    monkeypatch.setenv("GH_TOKEN", "ghp-other-secret-value")
    echo = {"actions": [{"run": f'{PY} -c "import os; print(os.environ.get(\'GROQ_API_KEY\', \'NOT-SET\')); print(os.environ.get(\'GH_TOKEN\', \'NOT-SET\'))"'}],
            "summary": "ran it"}
    off = Agent(echo, {"done": True, "summary": "ok"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, out_dir=tmp_path / "a", transport=off)
    assert "running commands is switched off" in off.seen[1]
    first = json.loads((tmp_path / "a" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first["actions"][0]["ok"] is False and "switched off" in first["actions"][0]["result"]

    on = Agent(echo, {"done": True, "summary": "ok"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, allow_commands=True, out_dir=tmp_path / "b", transport=on)
    first = json.loads((tmp_path / "b" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()[0])
    # the agent's own command never even sees the keys: its environment holds no secret-named variable
    assert first["actions"][0]["ok"] is True and first["actions"][0]["result"].count("NOT-SET") == 2
    for secret in ("gsk-very-secret-value", "ghp-other-secret-value"):
        assert all(secret not in seen for seen in on.seen)
        assert secret not in (tmp_path / "b" / "rounds.jsonl").read_text(encoding="utf-8")


def test_check_output_is_scrubbed_of_secret_named_values_before_it_goes_anywhere(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GH_TOKEN", "ghp-check-secret-value")
    check = f'{PY} -c "import os; print(os.environ[\'GH_TOKEN\']); raise SystemExit(1)"'
    agent = Agent({"actions": [], "done": True, "summary": "ok"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, check=check, max_rounds=2, out_dir=tmp_path / "r", transport=agent)
    assert "[redacted]" in agent.seen[0]  # the check's output reached the model only scrubbed
    assert all("ghp-check-secret-value" not in seen for seen in agent.seen)
    assert "ghp-check-secret-value" not in (tmp_path / "r" / "rounds.jsonl").read_text(encoding="utf-8")


def test_a_passing_check_stops_the_loop_even_with_a_watch(tmp_path: Path, project: Path) -> None:
    agent = Agent()
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=project, check=f'{PY} -c "print(1)"',
                         watch=f'{PY} -c "print(1)"', every=60, out_dir=tmp_path / "r", transport=agent)
    assert made.stopped == "check passed" and made.done and made.calls == 0 and agent.seen == []


def test_the_agent_saying_done_stops_the_loop_with_a_watch_and_no_check(tmp_path: Path, project: Path) -> None:
    agent = Agent({"actions": [], "done": True, "summary": "all set"})
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=project, watch=f'{PY} -c "print(1)"',
                         every=60, out_dir=tmp_path / "r", transport=agent)
    assert made.stopped == "the agent says it is done: all set" and made.done and made.calls == 1


def test_the_agent_cannot_write_outside_its_folder(tmp_path: Path, project: Path) -> None:
    agent = Agent({"actions": [{"write": "../escape.txt", "text": "x"}, {"read": "/etc/hostname"}], "done": True, "summary": "tried"})
    loop.run_loop("x", provider_id="ollama", model="m", workdir=project, out_dir=tmp_path / "r", transport=agent)
    first = json.loads((tmp_path / "r" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [a["ok"] for a in first["actions"]] == [False, False]
    assert not (tmp_path / "escape.txt").exists()


def test_without_a_check_the_agent_says_when_it_is_done(tmp_path: Path, project: Path) -> None:
    agent = Agent({"actions": [{"write": "notes/plan.md", "text": "# Plan\n"}], "summary": "wrote the plan"},
                  {"actions": [], "done": True, "summary": "all set"})
    made = loop.run_loop("write a plan", provider_id="ollama", model="m", workdir=project, out_dir=tmp_path / "r", transport=agent)
    assert made.stopped == "the agent says it is done: all set" and made.done
    assert (project / "notes" / "plan.md").read_text(encoding="utf-8") == "# Plan\n"
    assert "notes/plan.md" in agent.seen[1]  # the folder listing shows its own work


def test_a_watch_sends_only_when_something_changed(tmp_path: Path, project: Path) -> None:
    (project / "status.txt").write_text("green", encoding="utf-8")
    now = [0.0]
    naps: list[float] = []

    def sleep(seconds: float) -> None:
        naps.append(seconds)
        now[0] += seconds
        if len(naps) == 3:
            (project / "status.txt").write_text("red", encoding="utf-8")

    agent = Agent()
    made = loop.run_loop("tell me when the status turns red", provider_id="ollama", model="m", workdir=project,
                         watch=f'{PY} -c "print(open(\'status.txt\').read())"', every=60, max_seconds=300,
                         out_dir=tmp_path / "r", transport=agent, sleep=sleep, clock=lambda: now[0])
    assert made.stopped == "time limit reached"
    assert [s.sent for s in made.steps] == [True, False, False, True, False] and made.calls == 2
    assert "green" in agent.seen[0] and "red" in agent.seen[1] and naps == [60] * 5


def test_one_spending_limit_covers_the_whole_loop(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert cli.main(["providers", "price", "groq", "m", "--input", "1000", "--output", "1000"]) == 0
    made = loop.run_loop("x", provider_id="groq", model="m", workdir=project, check=CHECK, max_rounds=50, max_cost_usd="5",
                         max_output_tokens=512, out_dir=tmp_path / "r", transport=Agent())
    assert made.stopped == "spending limit reached" and 0 < made.calls < 50
    assert made.spent_usd <= Decimal("5")


def test_ctrl_c_stops_cleanly_and_keeps_the_record(tmp_path: Path, project: Path) -> None:
    def interrupted(request: live.Request) -> live.Response:
        raise KeyboardInterrupt

    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=project, out_dir=tmp_path / "r", transport=interrupted)
    assert made.stopped == "stopped by you"
    assert json.loads((tmp_path / "r" / "loop.json").read_text(encoding="utf-8"))["stopped"] == "stopped by you"


def test_bad_starts_are_refused(tmp_path: Path, project: Path) -> None:
    with pytest.raises(loop.LoopError):
        loop.run_loop("x", provider_id="openai", model="m", workdir=project, out_dir=tmp_path / "a")
    with pytest.raises(loop.LoopError):
        loop.run_loop("x", provider_id="ollama", model="m", workdir=project, watch="true", out_dir=tmp_path / "b")
    with pytest.raises(loop.LoopError):
        loop.run_loop("x", provider_id="ollama", model="m", workdir=tmp_path / "missing", out_dir=tmp_path / "c")
    assert cli.main(["loop", "x", "--provider", "ollama", "--model", "m", "--in", str(project), "--watch", "true"]) == 2


def test_the_command_runs_the_loop(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    agent = Agent({"actions": [{"write": "calc.py", "text": "def add(a, b):\n    return a + b\n"}], "summary": "fixed"})
    monkeypatch.setattr(live, "_httpx_post", agent)
    code = cli.main(["loop", "make the check pass", "--provider", "ollama", "--model", "llama3", "--in", str(project),
                     "--check", CHECK, "--out", str(tmp_path / "rec"), "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["stopped"] == "check passed"


TESTS_CHECK = f"{PY} tests/check_calc.py"


@pytest.fixture
def guarded(project: Path) -> Path:
    (project / "tests").mkdir()
    (project / "tests" / "check_calc.py").write_text("import sys\nsys.path.insert(0, '.')\nimport calc\nassert calc.add(2, 2) == 4\n",
                                                     encoding="utf-8")
    return project


def test_a_protected_file_cannot_be_written_so_the_check_cannot_be_passed_by_editing_it(tmp_path: Path, guarded: Path) -> None:
    before = (guarded / "tests" / "check_calc.py").read_bytes()
    agent = Agent({"actions": [{"write": "tests/check_calc.py", "text": "pass\n"}, {"write": "TESTS\\check_calc.py", "text": "pass\n"}],
                   "summary": "made the test easy"})
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=guarded, check=TESTS_CHECK, protect=["tests/*"],
                         max_rounds=2, out_dir=tmp_path / "r", transport=agent)
    assert not made.done and (guarded / "tests" / "check_calc.py").read_bytes() == before
    actions = made.steps[0].actions
    assert [a["ok"] for a in actions] == [False, False] and all("protected" in a["result"] for a in actions)
    assert "PROTECTED" in agent.seen[0] and "tests/*" in agent.seen[0]
    assert json.loads((tmp_path / "r" / "loop.json").read_text(encoding="utf-8"))["protect"] == ["tests/*"]


@pytest.mark.parametrize("code, word", [
    ("open('tests/check_calc.py', 'w').write('pass')", "changed"),
    ("open('tests/conftest.py', 'w').write('raise SystemExit(0)')", "new"),
    ("import os; os.remove('tests/check_calc.py'); open('tests/check_calc.py.bak', 'w').write('')", "removed"),
])
def test_a_command_that_changes_a_protected_file_stops_the_loop_and_is_not_a_pass(tmp_path: Path, guarded: Path, code: str, word: str) -> None:
    agent = Agent({"actions": [{"run": f'{PY} -c "{code}"'},
                               {"write": "calc.py", "text": "def add(a, b):\n    return a + b\n"}], "summary": "sneaky"})
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=guarded, check=TESTS_CHECK, protect=["tests"],
                         allow_commands=True, out_dir=tmp_path / "r", transport=agent)
    assert not made.done and made.calls == 1
    assert "protected file" in made.stopped and "tests/" in made.stopped and word in made.stopped
    line = json.loads((tmp_path / "r" / "rounds.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert line["check"] is None and line["protected_changed"]


def test_work_outside_the_protected_files_still_passes_the_check(tmp_path: Path, guarded: Path) -> None:
    agent = Agent({"actions": [{"write": "calc.py", "text": "def add(a, b):\n    return a + b\n"}], "summary": "fixed"})
    made = loop.run_loop("x", provider_id="ollama", model="m", workdir=guarded, check=TESTS_CHECK, protect=["tests/*"],
                         out_dir=tmp_path / "r", transport=agent)
    assert made.done and made.stopped == "check passed"
    with pytest.raises(loop.LoopError):
        loop.run_loop("x", provider_id="ollama", model="m", workdir=guarded, protect=[" "], out_dir=tmp_path / "s", transport=agent)


def test_a_check_with_nothing_protected_is_said_once_on_the_command_line(tmp_path: Path, guarded: Path, monkeypatch, capsys) -> None:
    fixed = {"actions": [{"write": "calc.py", "text": "def add(a, b):\n    return a + b\n"}], "summary": "fixed"}
    base = ["loop", "x", "--provider", "ollama", "--model", "m", "--in", str(guarded), "--check", TESTS_CHECK]
    monkeypatch.setattr(live, "_httpx_post", Agent(fixed))
    assert cli.main([*base, "--out", str(tmp_path / "a")]) == 0
    err = capsys.readouterr().err
    assert err.count("--protect") == 1 and "the agent can change the files your check reads" in err
    (guarded / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    monkeypatch.setattr(live, "_httpx_post", Agent(fixed))
    assert cli.main([*base, "--protect", "tests/*", "--protect", "*.cfg", "--out", str(tmp_path / "b")]) == 0
    assert "--protect" not in capsys.readouterr().err
    assert json.loads((tmp_path / "b" / "loop.json").read_text(encoding="utf-8"))["protect"] == ["tests/*", "*.cfg"]


def test_a_command_that_runs_too_long_is_stopped_with_everything_it_started(tmp_path: Path, project: Path) -> None:
    import time

    late = project / "late.txt"
    child = f"import time; time.sleep(3); open(r'{late}', 'w').write('still running')"
    (project / "slow.py").write_text(
        f"import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', {child!r}])\ntime.sleep(30)\n", encoding="utf-8")
    outcome = loop._shell(f"{PY} slow.py", project, 1, [])
    assert outcome["exit"] is None and "stopped after 1 seconds" in outcome["output"]
    time.sleep(4)
    assert not late.exists()
