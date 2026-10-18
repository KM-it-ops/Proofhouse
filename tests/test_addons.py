"""Add-ons: providers, services, tools and make kinds from packs and packages, with no change to Proofhouse."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import addons, cli, hosts, live, make, media, providers, train

PACK = {
    "schema": "proofhouse.addon/v1",
    "name": "acme-pack",
    "version": "1.0",
    "description": "Acme's models, image service, tuning and editor",
    "providers": [{"id": "acme", "base_url": "https://api.acme.example/v1", "key_env": "ACME_API_KEY"}],
    "media_providers": [{"id": "acme-images", "kinds": ["image"], "base_url": "https://img.acme.example", "unit": "image",
                         "submit": {"path": "/gen", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"]}}],
    "training_services": [{"id": "acme-tune", "command": ["acme-tune", "--model", "{model}", "--data", "{train}"]}],
    "hosts": [{"id": "acme-editor", "name": "Acme Editor", "rule": {"format": "file", "path": "~/.acme/rules/{name}.md"}}],
    "make_kinds": [{"kind": "tweet-thread", "subject": "THREAD",
                    "write": "You write tweet threads that people finish reading. Write the thread for the request below."}],
}


class Writer:
    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You judge AI work"):
            assert "THREAD:" in text
            content = json.dumps({"score": 10, "missing": [], "fix": ""})
        else:
            assert text.startswith("You write tweet threads")
            content = "1/ Brew is here.\n2/ One tap, coffee ready."
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


def _pack(tmp_path: Path, data: dict) -> Path:
    folder = tmp_path / "pack"
    folder.mkdir(exist_ok=True)
    (folder / "addon.json").write_text(json.dumps(data), encoding="utf-8")
    return folder


def test_a_pack_adds_a_provider_a_service_a_trainer_a_tool_and_a_make_kind(tmp_path: Path) -> None:
    assert cli.main(["addons", "install", str(_pack(tmp_path, PACK))]) == 0
    assert providers.find("acme").origin == "add-on acme-pack"
    assert media.find("acme-images").origin == "add-on acme-pack"
    assert train.find("acme-tune").local
    assert "acme-editor" in hosts.all_hosts()
    made = make.make("a launch thread for Brew", provider_id="ollama", model="m", kind="tweet-thread",
                     out_dir=tmp_path / "out", transport=Writer())
    assert made.best_score == 10 and (tmp_path / "out" / "final.md").read_text(encoding="utf-8").startswith("1/ Brew is here.")
    assert cli.main(["addons", "remove", "acme-pack"]) == 0
    assert providers.find("acme") is None and "tweet-thread" not in addons.make_kinds()


def test_your_own_entry_still_wins_over_an_add_on(tmp_path: Path) -> None:
    addons.install(_pack(tmp_path, PACK))
    assert cli.main(["providers", "add", "acme", "--base-url", "https://my-proxy.example/v1"]) == 0
    assert providers.find("acme").base_url == "https://my-proxy.example/v1"


@pytest.mark.parametrize("change", [
    {"providers": [{"id": "bad", "base_url": "http://not-local.example"}]},
    {"make_kinds": [{"kind": "site", "write": "A writer prompt that is long enough."}]},
    {"name": "Not A Name"},
    {"surprise": []},
])
def test_a_bad_pack_is_refused_before_it_is_installed(tmp_path: Path, change: dict) -> None:
    with pytest.raises(addons.AddonError):
        addons.install(_pack(tmp_path, {**PACK, **change}))
    assert not addons.packs_dir().exists() or not any(addons.packs_dir().iterdir())


@pytest.mark.parametrize("kind", [*make.KINDS, "video", "launch"])
def test_an_add_on_cannot_claim_a_built_in_kind_name(tmp_path: Path, kind: str) -> None:
    with pytest.raises(addons.AddonError):
        addons.install(_pack(tmp_path, {**PACK, "make_kinds": [{"kind": kind, "write": "A writer prompt that is long enough."}]}))


class _Point:
    def __init__(self, name: str, make_it) -> None:
        self.name, self._make = name, make_it

    def load(self):
        return self._make


def test_a_python_package_add_on_is_loaded_and_a_broken_one_is_skipped(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def broken():
        raise RuntimeError("boom")

    points = [_Point("good", lambda: {"name": "good-addon", "providers": [{"id": "goodai", "base_url": "https://api.good.example/v1"}]}),
              _Point("bad", broken)]
    monkeypatch.setattr(addons, "entry_points", lambda group: points if group == "proofhouse.addons" else [])
    assert providers.find("goodai").origin == "add-on good-addon"
    assert cli.main(["addons", "list"]) == 0
    captured = capsys.readouterr()
    assert "good-addon" in captured.out and "package" in captured.out and "skipped: bad: RuntimeError: boom" in captured.err


def test_a_make_kind_nobody_added_is_researched_first_not_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown kind is learned (learn.py), never refused; the first thing sent is the research question."""
    addons.install(_pack(tmp_path, PACK))
    sent: list[str] = []

    def model(request: live.Request) -> live.Response:
        sent.append(" ".join(m["content"] for m in json.loads(request.body_bytes)["messages"]))
        return live.Response(200, {"choices": [{"message": {"content": "not JSON"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    monkeypatch.setattr(live, "_httpx_post", model)
    assert cli.main(["make", "x", "--kind", "poster", "--provider", "ollama", "--model", "m", "--out", str(tmp_path / "o")]) != 0
    assert len(sent) == 1 and sent[0].startswith("Proofhouse makes many kinds") and "make a poster" in sent[0]
