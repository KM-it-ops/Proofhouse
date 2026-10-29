"""The agent bridge: a logged-in coding agent (Claude Code, Codex, Grok) answers as an OpenAI-format provider on this machine."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from proofhouse import agent_server, live, providers


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


def _post(base: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        base + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
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
    _, base = served("codex", runner)
    status, payload = _post(
        base, {"model": "any-model", "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Say hi."}]}
    )
    assert status == 200
    assert payload["choices"][0]["message"] == {"role": "assistant", "content": "the answer"}
    prompt = runner.calls[0][1]
    assert "Be brief." in prompt and "Say hi." in prompt


def test_a_failing_agent_gives_a_plain_502_not_a_fake_answer(served) -> None:
    _, base = served("grok", FakeRunner(fail="grok is not signed in"))
    status, payload = _post(base, {"model": "m", "messages": [{"role": "user", "content": "x"}]})
    assert status == 502
    assert "not signed in" in payload["error"]["message"]


def test_server_listens_on_this_machine_only(served) -> None:
    server, _ = served("claude", FakeRunner())
    assert server.server_address[0] == "127.0.0.1"


def test_model_name_is_passed_to_the_agent_when_its_command_takes_one(served) -> None:
    runner = FakeRunner()
    _, base = served("claude", runner)
    _post(base, {"model": "claude-sonnet-5-5", "messages": [{"role": "user", "content": "x"}]})
    assert "claude-sonnet-5-5" in runner.calls[0][0]


def test_proofhouse_run_prompt_works_through_the_bridge_with_no_key_and_no_price(
    served, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    _, base = served("codex", FakeRunner("a made thing"))
    providers.save_user(
        {"schema": providers.PROVIDERS_SCHEMA, "providers": [{"id": "bridge-test", "base_url": base}], "prices": [],
         "media_prices": [], "training_prices": []}
    )
    result = live.run_prompt("bridge-test", "codex", prompt="Make a thing.")
    assert result.status == "success", result.message
    assert result.output_text == "a made thing"
