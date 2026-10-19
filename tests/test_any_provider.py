"""Any provider, any model: providers are data, every run goes through the spend gate, keys never leak."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proofhouse import cli, live, providers, spend


class Recorder:
    def __init__(self, status: int = 200, payload: dict | None = None, boom: Exception | None = None) -> None:
        self.calls: list[live.Request] = []
        self.status = status
        self.payload = payload if payload is not None else {
            "choices": [{"message": {"role": "assistant", "content": "hello back"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        }
        self.boom = boom

    def __call__(self, request: live.Request) -> Any:
        self.calls.append(request)
        if self.boom:
            raise self.boom
        return live.Response(self.status, self.payload)


def front(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli.main(argv, prog="proofhouse")
    out = capsys.readouterr()
    return code, out.out, out.err


# --- providers are data ------------------------------------------------------------------------


def test_common_cloud_and_local_providers_ship() -> None:
    found = providers.all_providers()
    for pid in ("openai", "anthropic", "google", "mistral", "groq", "together", "fireworks", "openrouter", "deepseek", "xai"):
        assert found[pid].base_url.startswith("https://") and not found[pid].local and found[pid].key_env
    for pid in ("ollama", "lmstudio", "vllm", "llamacpp"):
        assert found[pid].local and found[pid].key_env is None
    assert found["openai"].shape == "openai" and found["anthropic"].shape == "openai-compatible"


@pytest.mark.parametrize(
    "url",
    ["http://api.example.com/v1", "https://user:pw@api.example.com/v1", "https://api.example.com/v1?x=1", "ftp://h/v1", "", "https:///v1"],
)
def test_unsafe_addresses_are_refused(url: str) -> None:
    with pytest.raises(providers.ProviderError):
        providers.parse_provider({"id": "x", "base_url": url}, "yours")


def test_plain_http_is_only_for_this_machine() -> None:
    for host in ("localhost", "127.0.0.1", "[::1]"):
        assert providers.parse_provider({"id": "x", "base_url": f"http://{host}:9000/v1"}, "yours").local


@pytest.mark.parametrize("ignores", ["tools@1", [1], ["tools"], ["Tools@1"], ["tools@0"], [None]])
def test_a_bad_ignores_list_is_refused(ignores: object) -> None:
    """f939f95-F3: what a provider ignores decides what is refused, so a malformed list must not load."""
    with pytest.raises(providers.ProviderError, match="ignores"):
        providers.parse_provider({"id": "x", "base_url": "https://api.example.com/v1", "ignores": ignores}, "yours")


def test_an_unknown_provider_is_one_command_away(capsys) -> None:
    code, out, _ = front(["providers", "add", "brandnew", "--base-url", "https://api.brandnew.ai/v1", "--key-env", "BRANDNEW_KEY"], capsys)
    assert code == 0 and "brandnew" in out
    found = providers.find("brandnew")
    assert found is not None and found.origin == "yours" and found.chat_url == "https://api.brandnew.ai/v1/chat/completions"
    code, out, _ = front(["providers", "list", "--json"], capsys)
    assert "brandnew" in {row["id"] for row in json.loads(out)["providers"]}
    assert front(["providers", "remove", "brandnew"], capsys)[0] == 0
    assert providers.find("brandnew") is None


def test_a_broken_providers_file_is_refused_whole(capsys) -> None:
    providers.user_path().parent.mkdir(parents=True, exist_ok=True)
    providers.user_path().write_text('{"schema": "wrong"}', encoding="utf-8")
    with pytest.raises(providers.ProviderError):
        providers.all_providers()
    result = live.run_prompt("openai", "m", prompt="hi", max_cost_usd="1", transport=Recorder())
    assert result.code == "PHC-RUN-0001"


# --- running on any provider -----------------------------------------------------------------


def _declare(provider: str, model: str, price_in: str = "1", price_out: str = "2") -> None:
    assert cli.main(["providers", "price", provider, model, "--input", price_in, "--output", price_out]) == 0


def test_a_cloud_run_goes_through_the_gate_and_records_cost(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-secret-mistral")
    _declare("mistral", "mistral-large", "2", "6")
    capsys.readouterr()
    rec = Recorder()
    result = live.run_prompt("mistral", "mistral-large", prompt="Be brief.", input_text="hi", max_cost_usd="1", transport=rec)
    assert result.status == "success" and result.output_text == "hello back"
    (request,) = rec.calls
    assert request.url == "https://api.mistral.ai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-secret-mistral"
    body = json.loads(request.body_bytes)
    assert body == {"model": "mistral-large", "messages": [
        {"role": "system", "content": "Be brief."}, {"role": "user", "content": "hi"}], "max_tokens": 1024}
    assert result.admission["price"]["source"] == "declared by you"
    assert result.cost["usd"] == str((Decimal(12) * 2 + Decimal(3) * 6) / Decimal(1_000_000))
    assert result.cost["basis"]["usd"] == "estimated"
    assert "sk-secret-mistral" not in json.dumps(result.to_dict())


def test_openai_uses_its_own_output_cap_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    _declare("openai", "gpt-x")
    rec = Recorder()
    assert live.run_prompt("openai", "gpt-x", prompt="hi", max_cost_usd="1", transport=rec).status == "success"
    assert "max_completion_tokens" in json.loads(rec.calls[0].body_bytes)


def test_a_model_on_this_machine_runs_free_with_no_key_and_no_limit() -> None:
    rec = Recorder()
    result = live.run_prompt("ollama", "llama3", prompt="hi", transport=rec)
    assert result.status == "success" and len(rec.calls) == 1
    assert "Authorization" not in rec.calls[0].headers
    assert result.admission["price"]["source"] == "on this machine: no charge"
    assert Decimal(result.cost["usd"]) == 0 and result.cost["basis"]["usd"] == "estimated"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"provider_id": "nope"}, "PHC-RUN-0001"),
        ({"model": " "}, "PHC-RUN-0002"),
        ({"prompt": " "}, "PHC-RUN-0002"),
        ({"max_cost_usd": None}, "PHC-RUN-0002"),
    ],
)
def test_runs_that_cannot_start_send_nothing(monkeypatch: pytest.MonkeyPatch, kwargs: dict, code: str) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    _declare("groq", "llama-x")
    rec = Recorder()
    args = {"provider_id": "groq", "model": "llama-x", "prompt": "hi", "max_cost_usd": "1", "transport": rec, **kwargs}
    provider_id = args.pop("provider_id")
    model = args.pop("model")
    assert live.run_prompt(provider_id, model, **args).code == code
    assert rec.calls == []


def test_a_missing_key_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    _declare("xai", "grok-x")
    rec = Recorder()
    result = live.run_prompt("xai", "grok-x", prompt="hi", max_cost_usd="1", transport=rec)
    assert result.code == "PHC-RUN-0003" and "XAI_API_KEY" in result.message and rec.calls == []


def test_a_paid_model_with_no_price_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    rec = Recorder()
    result = live.run_prompt("deepseek", "deepseek-chat", prompt="hi", max_cost_usd="1", transport=rec)
    assert result.code == "PHC-COST-0002" and rec.calls == []


def test_a_zero_price_is_refused_for_a_paid_provider(capsys) -> None:
    assert cli.main(["providers", "price", "together", "m", "--input", "0", "--output", "0"]) == 2
    assert cli.main(["providers", "price", "ollama", "m", "--input", "0", "--output", "0"]) == 0


def test_the_spending_limit_still_refuses_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOGETHER_API_KEY", "k")
    _declare("together", "big", "1000", "1000")
    rec = Recorder()
    result = live.run_prompt("together", "big", prompt="hi", max_cost_usd="0.01", transport=rec)
    assert result.code == "PHC-COST-0001" and rec.calls == []


def test_provider_errors_and_send_failures_are_reported_without_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "sk-fw-secret")
    _declare("fireworks", "m")
    failed = live.run_prompt("fireworks", "m", prompt="hi", max_cost_usd="1",
                             transport=Recorder(401, {"error": {"message": "bad key sk-fw-secret"}}))
    assert failed.code == "PHC-RUN-0006" and "HTTP 401" in failed.message
    assert "sk-fw-secret" not in json.dumps(failed.to_dict())
    boom = Recorder(boom=RuntimeError("sk-fw-secret"))
    broken = live.run_prompt("fireworks", "m", prompt="hi", max_cost_usd="1", transport=boom)
    assert broken.code == "PHC-RUN-0005" and len(boom.calls) == 1
    assert "sk-fw-secret" not in json.dumps(broken.to_dict())


def test_the_bytes_sent_are_the_bytes_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder()
    result = live.run_prompt("lmstudio", "qwen", prompt="é 🙂", transport=rec)
    assert result.admission["input_tokens_bound"] == len(rec.calls[0].body_bytes) + spend.INPUT_TOKEN_MARGIN


def test_cli_run_prints_the_output_and_a_cost_line(capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "_httpx_post", lambda request: live.Response(200, Recorder().payload))
    code, out, err = front(["run", "--provider", "ollama", "--model", "llama3", "--prompt", "hi"], capsys)
    assert code == 0 and out == "hello back\n"
    assert "[ollama llama3] tokens in 12, out 3" in err and "(estimated)" in err
    code, out, _ = front(["run", "--provider", "groq", "--model", "x", "--prompt", "hi"], capsys)
    assert code == 7 and out.startswith("PHC-RUN-0003")


def test_cli_run_reads_prompt_and_input_files(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[live.Request] = []
    monkeypatch.setattr(live, "_httpx_post", lambda request: (seen.append(request), live.Response(200, Recorder().payload))[1])
    (tmp_path / "p.txt").write_text("system words", encoding="utf-8")
    (tmp_path / "i.txt").write_text("user words", encoding="utf-8")
    code, _, _ = front(["run", "--provider", "vllm", "--model", "m", "--prompt-file", str(tmp_path / "p.txt"),
                        "--input-file", str(tmp_path / "i.txt"), "--json"], capsys)
    assert code == 0
    messages = json.loads(seen[0].body_bytes)["messages"]
    assert messages == [{"role": "system", "content": "system words"}, {"role": "user", "content": "user words"}]


def test_one_run_reads_your_providers_file_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # The run and the spend gate share one read, so the price is judged for the entry the request goes to.
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-secret-mistral")
    _declare("mistral", "mistral-large", "2", "6")
    reads: list[Path] = []
    real = providers._read
    monkeypatch.setattr(providers, "_read", lambda path: reads.append(path) or real(path))
    result = live.run_prompt("mistral", "mistral-large", prompt="hi", max_cost_usd="1", transport=Recorder())
    assert result.status == "success" and result.admission["price"]["source"] == "declared by you"
    assert reads.count(providers.user_path()) == 1
