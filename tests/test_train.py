"""Training on your data: clean examples, any fine-tuning service as a template, your own machine, one spending limit."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, train


def _pairs(path: Path, count: int) -> Path:
    path.write_text("".join(json.dumps({"input": f"question {i}", "output": f"answer {i}"}) + "\n" for i in range(count)), encoding="utf-8")
    return path


def test_examples_become_training_and_check_files(tmp_path: Path) -> None:
    source = _pairs(tmp_path / "pairs.jsonl", 20)
    with source.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"input": "question 0", "output": "answer 0"}) + "\n")  # a duplicate is dropped
    summary = train.build_dataset(source, tmp_path / "data", system="You are Brew support.")
    assert (summary["examples"], summary["train"], summary["valid"]) == (20, 18, 2) and summary["warnings"] == []
    first = json.loads((tmp_path / "data" / "train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first == {"messages": [{"role": "system", "content": "You are Brew support."},
                                  {"role": "user", "content": "question 0"}, {"role": "assistant", "content": "answer 0"}]}


@pytest.mark.parametrize("count", [10, 19])
def test_a_small_set_still_holds_out_a_row_to_check(tmp_path: Path, count: int) -> None:
    summary = train.build_dataset(_pairs(tmp_path / "pairs.jsonl", count), tmp_path / "data")
    assert summary["valid"] == 1 and summary["train"] == count - 1
    assert len((tmp_path / "data" / "valid.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_no_hold_out_when_asked_for_none_or_the_set_is_too_small(tmp_path: Path) -> None:
    assert train.build_dataset(_pairs(tmp_path / "a.jsonl", 20), tmp_path / "a", valid_share=0)["valid"] == 0
    assert train.build_dataset(_pairs(tmp_path / "b.jsonl", 3), tmp_path / "b")["valid"] == 0


def test_csv_works_and_bad_examples_are_named(tmp_path: Path) -> None:
    (tmp_path / "p.csv").write_text("input,output\nhi,hello\nbye,goodbye\n", encoding="utf-8")
    summary = train.build_dataset(tmp_path / "p.csv", tmp_path / "d")
    assert summary["train"] == 2 and "at least 10" in summary["warnings"][0]
    (tmp_path / "bad.jsonl").write_text(json.dumps({"messages": [{"role": "user", "content": "x"}]}) + "\n", encoding="utf-8")
    with pytest.raises(train.TrainError, match="example 1"):
        train.build_dataset(tmp_path / "bad.jsonl", tmp_path / "e")


class Service:
    """A stand-in fine-tuning service: records uploads, the job request and status reads."""

    def __init__(self, states: list[dict]) -> None:
        self.uploads: list[tuple[str, dict, str]] = []
        self.jobs: list[train.TrainRequest] = []
        self.reads: list[str] = []
        self.states = states

    def upload(self, url, headers, fields, file_field, file_name, content):
        self.uploads.append((url, fields, file_name))
        return train.TrainResponse(200, {"id": f"file-{len(self.uploads)}"})

    def create(self, request: train.TrainRequest) -> train.TrainResponse:
        self.jobs.append(request)
        return train.TrainResponse(200, {"id": "ftjob-1", "status": "validating_files"})

    def get(self, url, headers):
        self.reads.append(url)
        return train.TrainResponse(200, self.states.pop(0))


@pytest.fixture
def data(tmp_path: Path) -> Path:
    train.build_dataset(_pairs(tmp_path / "pairs.jsonl", 30), tmp_path / "data")
    return tmp_path / "data"


def test_a_job_is_uploaded_started_waited_for_and_ready_to_use(tmp_path: Path, data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-train-secret")
    assert cli.main(["train", "price", "openai", "base-model", "--usd-per-million", "25"]) == 0
    svc = Service([{"status": "running"}, {"status": "succeeded", "fine_tuned_model": "ft:base-model:brew:1"}])
    result = train.start("openai", "base-model", data, epochs=3, max_cost_usd="1", out_dir=tmp_path / "rec",
                         transport=svc.create, upload=svc.upload, get=svc.get, poll_every=0)
    assert result.status == "success" and result.trained_model == "ft:base-model:brew:1"
    assert result.use == 'proofhouse run --provider openai --model ft:base-model:brew:1 --prompt "..."'
    assert [u[0] for u in svc.uploads] == ["https://api.openai.com/v1/files"] * 2 and svc.uploads[0][1] == {"purpose": "fine-tune"}
    (job,) = svc.jobs
    body = json.loads(job.body_bytes)
    assert job.url == "https://api.openai.com/v1/fine_tuning/jobs"
    assert body == {"model": "base-model", "training_file": "file-1", "validation_file": "file-2",
                    "method": {"type": "supervised", "supervised": {"hyperparameters": {"n_epochs": 3}}}}  # no suffix given: none sent
    size = (data / "train.jsonl").stat().st_size + (data / "valid.jsonl").stat().st_size
    assert Decimal(result.admission["worst_case_usd"]) == Decimal(size) * 3 * 25 / 1_000_000
    assert svc.reads == ["https://api.openai.com/v1/fine_tuning/jobs/ftjob-1"] * 2
    assert "sk-train-secret" not in (tmp_path / "rec" / "train.json").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "rec" / "train.json").read_text(encoding="utf-8"))["proofhouse_version"] == proofhouse.__version__


def test_over_the_limit_or_without_a_price_nothing_is_uploaded(tmp_path: Path, data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOGETHER_API_KEY", "tg-secret")
    svc = Service([])
    no_price = train.start("together", "m", data, max_cost_usd="1", out_dir=tmp_path / "a",
                           transport=svc.create, upload=svc.upload, get=svc.get)
    assert no_price.code == "PHC-COST-0002" and "nothing was uploaded" in no_price.message
    assert cli.main(["train", "price", "together", "*", "--usd-per-million", "1000"]) == 0
    over = train.start("together", "m", data, epochs=10, max_cost_usd="0.01", out_dir=tmp_path / "b",
                       transport=svc.create, upload=svc.upload, get=svc.get)
    assert over.code == "PHC-COST-0001" and svc.uploads == [] and svc.jobs == []
    assert train.start("openai", "m", data, out_dir=tmp_path / "c").code in ("PHC-RUN-0002", "PHC-RUN-0003")


def test_without_waiting_the_job_is_started_and_its_status_can_be_read(tmp_path: Path, data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOGETHER_API_KEY", "tg-secret")
    assert cli.main(["train", "price", "together", "m", "--usd-per-million", "3"]) == 0
    svc = Service([{"status": "completed", "output_name": "me/m-brew"}])
    started = train.start("together", "m", data, suffix="brew", max_cost_usd="1", wait=False, out_dir=tmp_path / "r",
                          transport=svc.create, upload=svc.upload, get=svc.get)
    assert started.status == "started" and started.job_id == "ftjob-1" and svc.reads == []
    assert json.loads(svc.jobs[0].body_bytes)["suffix"] == "brew" and json.loads(svc.jobs[0].body_bytes)["lora"] is True
    done = train.status("together", "ftjob-1", get=svc.get)
    assert done.status == "success" and done.trained_model == "me/m-brew" and "--provider together" in done.use


def test_a_service_must_put_the_epochs_in_the_job_so_the_cost_has_a_limit() -> None:
    bad = {"id": "x", "base_url": "https://api.x.ai", "upload": {"path": "/f", "id": "id"},
           "create": {"path": "/jobs", "body": {"model": "{model}", "training_file": "{file_id}"}},
           "status": {"path": "/jobs/{job_id}", "field": "status", "done": ["ok"]}}
    with pytest.raises(train.TrainError, match="epochs"):
        train._parse(bad, "yours")


def test_training_on_this_machine_runs_your_command_and_costs_nothing(tmp_path: Path, data: Path) -> None:
    script = tmp_path / "fake_lora.py"
    script.write_text("import sys, pathlib\nargs = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
                      "lines = pathlib.Path(args['--data']).read_text().splitlines()\n"
                      "out = pathlib.Path(args['--out']); out.mkdir()\n"
                      "(out / 'adapter.txt').write_text(f\"{len(lines)} examples x {args['--epochs']} epochs\")\n", encoding="utf-8")
    template = {"id": "my-lora", "command": [sys.executable, str(script), "--data", "{train}", "--epochs", "{epochs}", "--out", "{out}"],
                "use_hint": "serve {out} with your server"}
    (tmp_path / "t.json").write_text(json.dumps(template), encoding="utf-8")
    assert cli.main(["train", "add", "--from", str(tmp_path / "t.json")]) == 0
    result = train.start("my-lora", "llama-3-8b", data, epochs=2, out_dir=tmp_path / "run")
    assert result.status == "success", result.message
    assert (Path(result.trained_model) / "adapter.txt").read_text(encoding="utf-8") == "27 examples x 2 epochs"
    assert result.admission["price"]["source"] == "on this machine: no charge" and result.use.startswith("serve ")


def test_the_commands(tmp_path: Path, capsys) -> None:
    _pairs(tmp_path / "p.jsonl", 12)
    assert cli.main(["train", "data", str(tmp_path / "p.jsonl"), "--out", str(tmp_path / "d")]) == 0
    assert cli.main(["train", "services"]) == 0
    out = capsys.readouterr().out
    assert "12 examples" in out and "openai" in out and "mlx-lm" in out and "this machine" in out
    assert cli.main(["train", "price", "openai", "m", "--usd-per-million", "zero"]) == 2


def test_the_gate_itself_refuses_a_job_over_the_ceiling(data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import spend

    assert cli.main(["train", "price", "openai", "m", "--usd-per-million", "1000"]) == 0
    sent: list[str] = []
    gated = spend.send_training_within_ceiling(
        train.find("openai"), "m", {"file_id": "f", "epochs": 5, "data_files": [str(data / "train.jsonl")]},
        ceiling_usd="0.001", send=lambda url, body: sent.append(url),
    )
    assert gated.admission.code == "PHC-COST-0001" and sent == []
    admitted = spend.send_training_within_ceiling(
        train.find("openai"), "m", {"file_id": "f", "epochs": 5, "data_files": [str(data / "train.jsonl")]},
        ceiling_usd="100", send=lambda url, body: sent.append(url),
    )
    assert admitted.admission.decision == "admitted" and sent == ["https://api.openai.com/v1/fine_tuning/jobs"]


@pytest.mark.parametrize("epochs", [0, 51, -1, 2.0, "3", True, None])
def test_epochs_outside_1_to_50_are_refused_before_any_request(data: Path, epochs: object) -> None:
    params = {"file_id": "f", "epochs": epochs, "data_files": [str(data / "train.jsonl")]}
    with pytest.raises(train.TrainError, match="1 to 50"):
        train.build_job_request(train.find("openai"), "m", params)


@pytest.mark.parametrize("epochs", [1, 50])
def test_epochs_at_the_edges_are_accepted(data: Path, epochs: int) -> None:
    params = {"file_id": "f", "epochs": epochs, "data_files": [str(data / "train.jsonl")]}
    assert train.build_job_request(train.find("openai"), "m", params)[2] == epochs


@pytest.mark.parametrize("model", ["@evil.example", ".evil.example", ":1@evil.example"])
def test_a_model_name_cannot_move_the_job_to_another_host(data: Path, model: str) -> None:
    service = train._parse({"id": "x", "base_url": "https://api.x.ai", "upload": {"path": "/f", "id": "id"},
                            "create": {"path": "{model}/jobs", "body": {"model": "{model}", "n": "{epochs}"}},
                            "status": {"path": "/jobs/{job_id}", "field": "status", "done": ["ok"]}}, "yours")
    params = {"file_id": "f", "epochs": 3, "data_files": [str(data / "train.jsonl")]}
    with pytest.raises(train.TrainError, match="leaves the service's host"):
        train.build_job_request(service, model, params)
