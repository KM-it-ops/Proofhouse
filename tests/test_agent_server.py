"""The agent bridge: a logged-in coding agent (Claude Code, Codex, Grok) answers as an OpenAI-format provider on this machine."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from proofhouse import agent_server, live, providers


@pytest.fixture(autouse=True)
def bridge_token(monkeypatch):
    monkeypatch.setenv(agent_server.TOKEN_ENV, "synthetic-test-bridge-token")


class FakeRunner:
    def __init__(self, answer: str = "hello from the agent", fail: str | None = None) -> None:
        self.answer, self.fail, self.calls = answer, fail, []

    def __call__(self, argv: list[str], prompt: str, timeout: float) -> str:
        self.calls.append((argv, prompt))
        if self.fail:
            raise agent_server.AgentError(self.fail)
        return self.answer


@pytest.fixture
def served():
    started = []

    def start(agent: str, runner: FakeRunner):
        server = agent_server.make_server(agent, port=0, runner=runner)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        started.append(server)
        return server, f"http://127.0.0.1:{server.server_address[1]}/v1"

    yield start
    for server in started:
        server.shutdown()
        server.server_close()


def _post(base: str, body: dict, token: str | None = None, raw_headers: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(raw_headers or {})
    request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, json.loads(answer.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_agents_are_data_and_include_the_three_logged_in_tools() -> None:
    known = agent_server.load_agents()
    assert {"claude", "codex", "grok"} <= set(known)
    for entry in known.values():
        assert entry["argv"] and isinstance(entry["port"], int)


def test_unknown_agent_is_refused_by_name() -> None:
    with pytest.raises(agent_server.AgentError, match="nope"):
        agent_server.make_server("nope", port=0, runner=FakeRunner())


def test_chat_request_reaches_the_agent_and_the_answer_comes_back_in_openai_shape(served) -> None:
    runner = FakeRunner("the answer")
    server, base = served("codex", runner)
    status, payload = _post(
        base, {"model": "any-model", "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Say hi."}]},
        token=server.token,
    )
    assert status == 200
    assert payload["choices"][0]["message"] == {"role": "assistant", "content": "the answer"}
    prompt = runner.calls[0][1]
    assert "Be brief." in prompt and "Say hi." in prompt


def test_a_failing_agent_gives_a_plain_502_not_a_fake_answer(served) -> None:
    server, base = served("grok", FakeRunner(fail="grok is not signed in"))
    status, payload = _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=server.token)
    assert status == 502
    assert "not signed in" in payload["error"]["message"]


def test_server_listens_on_this_machine_only(served) -> None:
    server, _ = served("claude", FakeRunner())
    assert server.server_address[0] == "127.0.0.1"


def test_every_request_needs_the_token_and_a_wrong_one_runs_nothing(served) -> None:
    runner = FakeRunner()
    server, base = served("codex", runner)
    for token in (None, "wrong-token"):
        status, payload = _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=token)
        assert status == 401 and "token" in payload["error"]["message"]
    assert runner.calls == []
    status, _ = _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=server.token)
    assert status == 200 and len(runner.calls) == 1


def test_the_token_can_come_from_the_environment(served, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(agent_server.TOKEN_ENV, "env-token-123")
    server, base = served("codex", FakeRunner())
    assert server.token == "env-token-123" and server.token_file is None
    assert _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token="env-token-123")[0] == 200
    assert _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token="nope")[0] == 401


def test_with_no_token_named_one_is_saved_to_a_private_file_and_never_printed(
    served, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    monkeypatch.delenv(agent_server.TOKEN_ENV, raising=False)
    runner = FakeRunner()
    server, base = served("codex", runner)
    saved = (tmp_path / agent_server.TOKEN_FILE).read_text(encoding="utf-8").strip()
    assert len(saved) >= 32 and server.token == saved and server.token_file == tmp_path / agent_server.TOKEN_FILE
    assert _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=None)[0] == 401
    assert runner.calls == []
    assert _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=saved)[0] == 200
    # a second start reuses the same token, so a provider added once keeps working
    again, _ = served("codex", FakeRunner())
    assert again.token == saved


def test_the_start_message_names_the_token_file_and_both_shells_but_not_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    monkeypatch.delenv(agent_server.TOKEN_ENV, raising=False)

    def stop_at_once(self) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(agent_server.ThreadingHTTPServer, "serve_forever", stop_at_once)
    import argparse

    assert agent_server._cmd_agent_server(argparse.Namespace(agent="codex", port=0, timeout=5.0)) == 0
    out = capsys.readouterr().out
    saved = (tmp_path / agent_server.TOKEN_FILE).read_text(encoding="utf-8").strip()
    assert saved not in out
    assert str(tmp_path / agent_server.TOKEN_FILE) in out
    assert "PowerShell" in out and "bash" in out and agent_server.TOKEN_ENV in out


def test_the_bridge_note_names_the_real_variable_not_a_placeholder() -> None:
    _, note = agent_server.bridge_notes("agent-codex")
    assert agent_server.TOKEN_ENV in note and "{TOKEN_ENV}" not in note


def test_an_oversized_body_is_refused_before_it_is_read(served) -> None:
    runner = FakeRunner()
    server, base = served("codex", runner)
    status, payload = _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]}, token=server.token,
                            raw_headers={"Content-Length": str(agent_server.MAX_REQUEST_BYTES + 1)})
    assert status == 413
    assert runner.calls == []


def test_model_name_is_passed_to_the_agent_when_its_command_takes_one(served) -> None:
    runner = FakeRunner()
    server, base = served("claude", runner)
    _post(base, {"model": "claude-sonnet-5-5", "messages": [{"role": "user", "content": "x"}]}, token=server.token)
    assert "claude-sonnet-5-5" in runner.calls[0][0]


def test_proofhouse_run_prompt_works_through_the_bridge_with_the_token_and_no_vendor_key(
    served, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    monkeypatch.setenv(agent_server.TOKEN_ENV, "bridge-token-abc")
    server, base = served("codex", FakeRunner("a made thing"))
    assert server.token == "bridge-token-abc"
    providers.save_user(
        {"schema": providers.PROVIDERS_SCHEMA, "providers": [{"id": "bridge-test", "base_url": base, "key_env": agent_server.TOKEN_ENV}], "prices": [],
         "media_prices": [], "training_prices": []}
    )
    result = live.run_prompt("bridge-test", "codex", prompt="Make a thing.")
    assert result.status == "success", result.message
    assert result.output_text == "a made thing"


def test_a_refused_request_with_a_large_body_gets_its_answer_not_a_dropped_connection(served) -> None:
    """Refusing before the body was read used to close the connection on top of unread bytes, which Windows reports
    to the caller as an aborted connection in place of the 401."""
    runner = FakeRunner()
    _, base = served("codex", runner)
    body = {"model": "m", "messages": [{"role": "user", "content": "x" * 400_000}]}
    for _ in range(25):
        status, payload = _post(base, body, token="wrong")
        assert status == 401 and "token" in payload["error"]["message"]
    assert runner.calls == []


def test_only_so_many_requests_run_at_once_and_the_rest_are_told_to_come_back(served) -> None:
    going, release = threading.Event(), threading.Event()

    class Slow(FakeRunner):
        def __call__(self, argv: list[str], prompt: str, timeout: float) -> str:
            going.set()
            assert release.wait(20)
            return super().__call__(argv, prompt, timeout)

    runner = Slow()
    started = []

    def start():
        server = agent_server.make_server("codex", port=0, runner=runner, max_running=1)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        started.append(server)
        return server, f"http://127.0.0.1:{server.server_address[1]}/v1"

    server, base = start()
    try:
        body = {"model": "m", "messages": [{"role": "user", "content": "x"}]}
        first: list[tuple[int, dict]] = []
        thread = threading.Thread(target=lambda: first.append(_post(base, body, token=server.token)))
        thread.start()
        assert going.wait(10)
        status, payload = _post(base, body, token=server.token)
        assert status == 429 and "1" in payload["error"]["message"] and "at once" in payload["error"]["message"]
        release.set()
        thread.join(20)
        assert first and first[0][0] == 200
        assert _post(base, body, token=server.token)[0] == 200  # the place is free again
        assert len(runner.calls) == 2
    finally:
        release.set()
        server.shutdown()
        server.server_close()


def test_a_caller_that_stops_sending_is_let_go_and_runs_nothing() -> None:
    import socket

    runner = FakeRunner()
    server = agent_server.make_server("codex", port=0, runner=runner, read_timeout=0.5)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=10) as sock:
            sock.sendall((f"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer {server.token}\r\n"
                          "Content-Type: application/json\r\nContent-Length: 500\r\n\r\n{\"model\"").encode())
            answer = sock.recv(4096).decode("utf-8", "replace")
        assert answer.startswith("HTTP/1.0 408") or answer.startswith("HTTP/1.1 408")
        assert runner.calls == []
    finally:
        server.shutdown()
        server.server_close()


def test_an_agent_that_does_not_answer_in_time_is_stopped_with_everything_it_started(tmp_path: Path) -> None:
    import sys
    import time

    late = tmp_path / "late.txt"
    child = f"import time; time.sleep(3); open(r'{late}', 'w').write('still running')"
    script = tmp_path / "slow.py"
    script.write_text(f"import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', {child!r}])\ntime.sleep(30)\n",
                      encoding="utf-8")
    with pytest.raises(agent_server.AgentError, match="did not answer within 1 s"):
        agent_server.run_agent([sys.executable, str(script)], "hello", 1)
    time.sleep(4)
    assert not late.exists()
