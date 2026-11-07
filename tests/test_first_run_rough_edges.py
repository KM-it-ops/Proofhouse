"""Rough edges a first run hits: model chatter in saved files, placeholder paths, reused folders, no httpx, slow models."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pytest

from proofhouse import cli, launch, live, loop, make


def _reply(content: str) -> live.Response:
    return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}})


class Chatty:
    """A small model that introduces its answer instead of just giving it."""

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You judge AI work"):
            return _reply(json.dumps({"score": 9, "missing": [], "fix": ""}))
        if text.startswith("Write one realistic input"):
            return _reply("A customer wants a refund.")
        if text.startswith("You write excellent prompts") or text.startswith("Improve the"):
            return _reply("Here is the improved prompt:\n\nYou are a calm support agent. Answer refund emails warmly.")
        return _reply("Dear customer, your refund is on its way.")


@pytest.mark.parametrize("chatter", [
    "Here is the improved prompt:", "Here's the prompt:", "Sure! Here is the prompt you asked for:", "Certainly, here is the revised prompt:",
])
def test_a_saved_prompt_never_starts_with_the_models_chatter(tmp_path: Path, chatter: str) -> None:
    assert make._strip_fences(f"{chatter}\n\nYou are a calm support agent.") == "You are a calm support agent."
    assert make._strip_fences(f"{chatter}\n\n```\nYou are a calm support agent.\n```") == "You are a calm support agent."


@pytest.mark.parametrize("chatter", [
    "Here's a sample one-page checklist for closing a small cafe at night:",
    "Here is a template for a weekly update:",
    "Sure! Here are the closing steps:",
])
def test_a_learned_kind_never_starts_with_the_models_chatter(chatter: str) -> None:
    assert make._strip_fences(f"{chatter}\n\n**Closing**\n\n* Lock up") == "**Closing**\n\n* Lock up"


def test_real_text_that_only_looks_like_chatter_is_kept() -> None:
    kept = "Here is what to do when a customer writes in angry: stay calm.\nThen apologise."
    assert make._strip_fences(kept) == kept
    assert make._strip_fences("---\nname: x\ndescription: y\n---\nBody") == "---\nname: x\ndescription: y\n---\nBody"


def test_make_saves_the_prompt_without_the_chatter(tmp_path: Path) -> None:
    made = make.make("a prompt that answers refund emails", provider_id="ollama", model="llama3", rounds=2,
                     out_dir=tmp_path / "out", transport=Chatty())
    final = (made.folder / "final.md").read_text(encoding="utf-8")
    assert final.startswith("You are a calm support agent") and "Here is" not in final


def test_the_agent_instructions_use_no_placeholder_paths() -> None:
    assert "relative/path" not in loop._AGENT


def test_a_placeholder_path_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    done = loop._act({"write": "relative/path", "text": "hello"}, tmp_path, False, 5, [])
    assert done["ok"] is False and "placeholder" in done["result"]
    assert not (tmp_path / "relative").exists()
    read = loop._act({"read": "relative/path"}, tmp_path, False, 5, [])
    assert read["ok"] is False and "placeholder" in read["result"]


def test_reusing_an_output_folder_gives_a_plain_message_not_a_windows_error(tmp_path: Path, capsys) -> None:
    taken = tmp_path / "out"
    taken.mkdir()
    with pytest.raises(make.MakeError, match="already exists"):
        make.make("a prompt", provider_id="ollama", model="m", out_dir=taken, transport=Chatty())
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(loop.LoopError, match="already exists"):
        loop.run_loop("do it", provider_id="ollama", model="m", workdir=work, out_dir=taken, transport=Chatty())
    with pytest.raises(launch.LaunchError, match="already exists"):
        launch.run_launch("a launch", provider_id="ollama", model="m", out_dir=taken, transport=Chatty())
    code = cli.main(["make", "a prompt", "--provider", "ollama", "--model", "m", "--out", str(taken)])
    err = capsys.readouterr().err
    assert code != 0 and "already exists" in err and "WinError" not in err and "FileExistsError" not in err


def test_without_httpx_a_plain_install_still_reaches_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "httpx", None)  # makes `import httpx` fail, like a plain pip install
    seen: dict[str, object] = {}

    class Reply:
        status = 200

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def fake_urlopen(request, timeout=None):
        seen["url"], seen["timeout"] = request.full_url, timeout
        return Reply()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = live._httpx_post(live.Request("http://localhost:11434/v1/chat/completions", {"Content-Type": "application/json"}, {}, b"{}"))
    assert response.status_code == 200 and response.payload["choices"][0]["message"]["content"] == "hi"
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"


def test_requests_name_proofhouse_as_the_client_unless_the_provider_names_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Groq's front door answers 403 (Cloudflare 1010) to Python's default client name, so every request names Proofhouse.
    monkeypatch.setitem(sys.modules, "httpx", None)
    seen: list[str | None] = []

    class Reply:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def fake_urlopen(request, timeout=None):
        seen.append(request.get_header("User-agent"))
        return Reply()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    live._httpx_post(live.Request("https://api.groq.com/openai/v1/chat/completions", {"Content-Type": "application/json"}, {}, b"{}"))
    live._httpx_post(live.Request("https://example.test/v1", {"User-Agent": "their-client/2"}, {}, b"{}"))
    assert seen[0] is not None and seen[0].startswith("proofhouse/")
    assert seen[1] == "their-client/2"


def test_a_slow_model_gets_a_plain_message_and_a_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    def too_slow(request: live.Request) -> live.Response:
        raise TimeoutError("timed out")

    result = live.run_prompt("ollama", "llama3", prompt="hi", transport=too_slow)
    assert result.status == "error"
    assert "did not answer" in result.message and "PROOFHOUSE_TIMEOUT_SECONDS" in result.message
    assert "TimeoutError" not in result.message

    monkeypatch.delenv("PROOFHOUSE_TIMEOUT_SECONDS", raising=False)
    assert live._timeout_seconds() == 120.0
    monkeypatch.setenv("PROOFHOUSE_TIMEOUT_SECONDS", "600")
    assert live._timeout_seconds() == 600.0
    monkeypatch.setenv("PROOFHOUSE_TIMEOUT_SECONDS", "nonsense")
    assert live._timeout_seconds() == 120.0


def test_a_model_on_this_machine_is_waited_for_longer_than_one_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROOFHOUSE_TIMEOUT_SECONDS", raising=False)
    assert live._timeout_seconds("http://localhost:11434/v1/chat/completions") == 600.0  # slow on a CPU, never billed
    assert live._timeout_seconds("http://127.0.0.1:8080/v1/chat/completions") == 600.0
    assert live._timeout_seconds("https://api.example.com/v1/chat/completions") == 120.0
    monkeypatch.setenv("PROOFHOUSE_TIMEOUT_SECONDS", "45")  # the setting wins everywhere
    assert live._timeout_seconds("http://localhost:11434/v1/chat/completions") == 45.0

    monkeypatch.delenv("PROOFHOUSE_TIMEOUT_SECONDS", raising=False)

    def too_slow(request: live.Request) -> live.Response:
        raise TimeoutError("timed out")

    result = live.run_prompt("ollama", "llama3", prompt="hi", transport=too_slow)
    assert "within 600 seconds" in result.message and "for example 1200" in result.message


def test_a_launch_whose_plan_cannot_be_read_says_so_and_keeps_a_record(tmp_path: Path, capsys) -> None:
    def rambling(request: live.Request) -> live.Response:
        return _reply("I would love to help you launch! First you should think about your audience.")

    made = launch.run_launch("a launch", provider_id="ollama", model="m", out_dir=tmp_path / "L", transport=rambling)
    assert made.parts == [] and "plan" in made.stopped and "another model" in made.stopped
    record = json.loads((tmp_path / "L" / "launch.json").read_text(encoding="utf-8"))
    assert record["parts"] == [] and "plan" in record["stopped"]


def _thought_through_the_cap() -> live.Response:
    return live.Response(200, {"choices": [{"message": {"content": "", "reasoning": "Hmm, let me think..."},
                                            "finish_reason": "length"}],
                               "usage": {"prompt_tokens": 100, "completion_tokens": 2048}})


def test_a_local_model_that_thinks_through_its_cap_gets_room_to_answer() -> None:
    caps: list[int] = []

    def thinker(request: live.Request) -> live.Response:
        cap = json.loads(request.body_bytes)["max_tokens"]
        caps.append(cap)
        return _reply("the plan") if cap > 2048 else _thought_through_the_cap()

    result = live.run_prompt("ollama", "qwen3:4b", prompt="plan it", max_output_tokens=2048, transport=thinker)
    assert result.output_text == "the plan"
    assert caps == [2048, live.LOCAL_THINKING_ROOM]


def test_the_retry_happens_once_and_never_for_a_paid_model(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[int] = []

    def always_thinking(request: live.Request) -> live.Response:
        sent.append(1)
        return _thought_through_the_cap()

    live.run_prompt("ollama", "qwen3:4b", prompt="plan it", max_output_tokens=2048, transport=always_thinking)
    assert len(sent) == 2
    sent.clear()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert cli.main(["providers", "price", "openai", "gpt-x", "--input", "1", "--output", "2"]) == 0
    paid = live.run_prompt("openai", "gpt-x", prompt="plan it", max_output_tokens=2048, max_cost_usd="1",
                           transport=always_thinking)
    assert paid.status == "success"
    assert len(sent) == 1


def test_a_reply_that_stopped_at_the_cap_says_it_was_cut_off() -> None:
    def answer(finish: str):  # noqa: ANN202
        return lambda request: live.Response(200, {"choices": [{"message": {"content": '{"beats": ['},
                                                                "finish_reason": finish}]})

    cut = live.run_prompt("ollama", "m", prompt="plan it", transport=answer("length"))
    whole = live.run_prompt("ollama", "m", prompt="plan it", transport=answer("stop"))
    assert cut.status == "success" and cut.cut_off and cut.to_dict()["cut_off"] is True
    assert not whole.cut_off
