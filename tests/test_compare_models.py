"""The same job on many models at once: side by side, one spending limit, a judge's scores as advice."""
from __future__ import annotations

import json
import threading
from decimal import Decimal
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, compare, live


class Models:
    """Stand-in providers: each model answers in its own words; the judge scores the anonymous outputs."""

    def __init__(self, scores: dict[str, int] | None = None) -> None:
        self.scores = scores or {}
        self.asked: list[tuple[str, str]] = []
        self.lock = threading.Lock()

    def __call__(self, request: live.Request) -> live.Response:
        body = json.loads(request.body_bytes)
        text = " ".join(m["content"] for m in body["messages"])
        with self.lock:
            self.asked.append((request.url, body["model"]))
        if text.startswith("You judge AI outputs"):
            content = json.dumps({"scores": {k: {"score": v, "why": f"reason {k}"} for k, v in self.scores.items()}, "best": "B"})
        else:
            content = f"answer from {body['model']}"
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 50, "completion_tokens": 20}})


def test_every_model_runs_and_the_results_sit_side_by_side(tmp_path: Path) -> None:
    models = Models({"A": 6, "B": 9, "C": 4})
    made = compare.compare("Summarise the refund policy in one line.", ["ollama:llama3", "ollama:qwen2.5:7b", "lmstudio:phi"],
                           judge="ollama:judge-model", out_dir=tmp_path / "c", transport=models)
    assert [e.output for e in made.entries] == ["answer from llama3", "answer from qwen2.5:7b", "answer from phi"]
    assert [e.score for e in made.entries] == [6, 9, 4] and made.best == "ollama:qwen2.5:7b"
    assert len(models.asked) == 4  # three runs and one judge
    record = json.loads((tmp_path / "c" / "compare.json").read_text(encoding="utf-8"))
    assert record["best"] == "ollama:qwen2.5:7b" and "advice" in record["judge"]["note"]
    assert record["proofhouse_version"] == proofhouse.__version__
    page = (tmp_path / "c" / "side-by-side.html").read_text(encoding="utf-8")
    assert "answer from phi" in page and "9/10" in page
    assert len(list((tmp_path / "c" / "outputs").iterdir())) == 3


def test_the_judge_sees_only_anonymous_outputs(tmp_path: Path) -> None:
    seen: list[str] = []
    models = Models({"A": 5})

    def spy(request: live.Request) -> live.Response:
        seen.append(json.loads(request.body_bytes)["messages"][-1]["content"])
        return models(request)

    compare.compare("job", ["ollama:secret-model-name"], judge="ollama:j", out_dir=tmp_path / "c", transport=spy)
    judged = [s for s in seen if "OUTPUT A" in s]
    assert judged and "secret-model-name" not in judged[0].replace("answer from secret-model-name", "")


def test_one_limit_covers_every_call_and_the_judge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    for model in ("a", "b", "c", "j"):
        assert cli.main(["providers", "price", "groq", model, "--input", "1000", "--output", "1000"]) == 0
    made = compare.compare("job", ["groq:a", "groq:b", "groq:c"], judge="groq:j", max_cost_usd="3",
                           max_output_tokens=256, out_dir=tmp_path / "c", transport=Models({"A": 1}))
    assert made.spent_usd <= Decimal("3")
    assert all(e.status == "refused" and e.code == "PHC-COST-0001" for e in made.entries)  # each share is $0.75; worst case is more


def test_a_paid_model_needs_a_limit_and_targets_are_provider_model(tmp_path: Path) -> None:
    with pytest.raises(compare.CompareError):
        compare.compare("job", ["openai:m"], out_dir=tmp_path / "a")
    with pytest.raises(compare.CompareError):
        compare.compare("job", ["no-colon"], out_dir=tmp_path / "b")
    with pytest.raises(compare.CompareError):
        compare.compare("job", ["nowhere:m"], out_dir=tmp_path / "c")
    assert compare.parse_target("ollama:llama3:8b") == ("ollama", "llama3:8b")


def test_the_command_prints_the_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(live, "_httpx_post", Models({"A": 8, "B": 3}))
    code = cli.main(["compare", "job", "--on", "ollama:llama3", "--on", "ollama:mistral", "--judge", "ollama:j",
                     "--out", str(tmp_path / "c")])
    out = capsys.readouterr().out
    assert code == 0 and "best on this job: ollama:llama3" in out and out.index("ollama:llama3") < out.index("ollama:mistral")


def test_paid_models_run_when_each_share_covers_its_worst_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    for model in ("a", "b"):
        assert cli.main(["providers", "price", "groq", model, "--input", "0.50", "--output", "1.50"]) == 0
    made = compare.compare("job", ["groq:a", "groq:b"], max_cost_usd="0.10", max_output_tokens=256,
                           out_dir=tmp_path / "c", transport=Models())
    assert [e.status for e in made.entries] == ["success", "success"]
    assert Decimal(0) < made.spent_usd <= Decimal("0.10")
