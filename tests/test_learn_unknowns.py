"""Unknown platforms, hosts, deploy targets, media and training services are researched and learned, never refused."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from proofhouse import addons, app_platforms, cli, deploy, learn, learn_catalog, live, make, media, spend, train
from proofhouse.optimize import install_skill

WEB = {"index.html": "<!doctype html><html><body><h1>App</h1></body></html>"}


def _gate(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    real = spend.send_within_ceiling

    def spy(*args, **kwargs):
        body = args[0] if isinstance(args[0], dict) else json.loads(args[0])
        seen.append(body["messages"][0]["content"][:40])
        return real(*args, **kwargs)

    monkeypatch.setattr(spend, "send_within_ceiling", spy)
    return seen


PLATFORM = {
    "what_it_is": "Gadget OS wraps web apps in a tiny native shell.",
    "name": "Gadget OS",
    "shell": "Gadget shell",
    "write": "Write setup.json with a name field for Gadget OS.",
    "checks": {"files": ["setup.json"], "json": {"setup.json": ["name"]}, "site": False},
    "build": {"tool": "python", "install": "install python", "command": [], "output": ""},
    "host_os": ["windows", "macos", "linux"],
    "sources": ["https://example.org/gadget-os"],
}

HOST = {
    "what_it_is": "Acme IDE is a coding environment with a skills folder.",
    "name": "Acme IDE",
    "skills_folder": ".acme",
    "start_hint": "a new Acme IDE session",
    "rule": {"user": "~/.acme/AGENTS.md", "format": "md-block"},
    "sources": ["https://example.org/acme-ide"],
}

DEPLOY = {
    "what_it_is": "MyHost publishes static sites with a small CLI.",
    "name": "MyHost",
    "tool": "myhost",
    "install": "pip install myhost",
    "command": [sys.executable, "-c", "print('{folder}')"],
    "sources": ["https://example.org/myhost"],
}

MEDIA = {
    "what_it_is": "Acme Images generates pictures from prompts.",
    "name": "Acme Images",
    "kinds": ["image"],
    "base_url": "https://api.acme.example/v1",
    "key_env": "ACME_IMAGE_KEY",
    "auth": "bearer",
    "unit": "image",
    "submit": {"path": "/images", "body": {"prompt": "{prompt}", "model": "{model}"}},
    "result": {"asset": ["url"]},
    "sources": ["https://example.org/acme-images"],
}

TRAIN = {
    "what_it_is": "Local tune runs a short command on this machine.",
    "name": "Local tune",
    "command": [sys.executable, "-c", "print('train')"],
    "sources": ["https://example.org/local-tune"],
}


class ResearchModel:
    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers
        self.sent: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        self.sent.append(text)
        for prefix, answer in self.answers.items():
            if text.startswith(prefix):
                payload = answer if isinstance(answer, str) else json.dumps(answer)
                return live.Response(200, {"choices": [{"message": {"content": payload}}],
                                           "usage": {"prompt_tokens": 3, "completion_tokens": 3}})
        if text.startswith("You judge AI work"):
            return live.Response(200, {"choices": [{"message": {"content": json.dumps({"score": 9, "missing": [], "fix": ""})}}],
                                       "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        if text.startswith("Build the "):
            return live.Response(200, {"choices": [{"message": {"content": json.dumps({"files": {"setup.json": '{"name":"x"}'}})}}],
                                       "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        raise AssertionError(text[:120])


def test_unknown_platform_is_researched_then_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate(monkeypatch)
    model = ResearchModel({"Proofhouse wraps working apps": json.dumps(PLATFORM)})
    result = make.make("an app", provider_id="ollama", model="m", kind="app", platforms=["gadget-os"],
                       out_dir=tmp_path / "out", transport=model)
    assert result.stopped != "rounds used up" or result.best_version
    assert gate[0].startswith("Proofhouse wraps working apps")
    assert "gadget-os" in app_platforms.all_platforms()
    pack = json.loads(learn.pack_path().read_text(encoding="utf-8"))
    assert any(p["id"] == "gadget-os" for p in pack["app_platforms"])
    again = ResearchModel({"Proofhouse wraps working apps": json.dumps(PLATFORM)})
    second = make.make("another app", provider_id="ollama", model="m", kind="app", platforms=["gadget-os"],
                       out_dir=tmp_path / "again", transport=again)
    assert not any(s.startswith("Proofhouse wraps working apps") for s in again.sent)


def test_bad_platform_name_is_refused(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError, match="plain platform name"):
        make.make("x", provider_id="ollama", model="m", kind="app", platforms=["../x"], out_dir=tmp_path / "o")


def test_unknown_host_is_learned_for_skill_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: demo\n---\n", encoding="utf-8")
    model = ResearchModel({"Proofhouse installs agents, rules and skills": json.dumps(HOST)})

    def ask(prompt: str) -> str:
        body = json.dumps({"messages": [{"role": "user", "content": prompt}]})
        reply = model(live.Request("http://x", {}, {}, body.encode()))
        return reply.payload["choices"][0]["message"]["content"]  # type: ignore[index]

    install_skill.install(host="acme-ide", bundle=skill, home=tmp_path / "ph", ask=ask)
    assert model.sent[0].startswith("Proofhouse installs agents, rules and skills")
    assert "acme-ide" in learn_catalog.skill_hosts()


def test_unknown_deploy_target_is_learned_on_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate(monkeypatch)
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    model = ResearchModel({"Proofhouse deploys finished sites": json.dumps(DEPLOY)})
    research = learn_catalog.Research("ollama", "m", transport=model)
    done = deploy.deploy(site, "myhost", dry_run=True, research=research)
    assert gate[0].startswith("Proofhouse deploys finished sites") and done.status == "dry run"
    assert "myhost" in deploy.all_targets()
    assert learn_catalog.learned_raw("deploy_targets", "myhost")


def test_unapproved_learned_deploy_refuses_before_running(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    keyed = {**DEPLOY, "key_env": "MYHOST_TOKEN"}
    learn_catalog._save_section("deploy_targets", {**keyed, "id": "myhost", **learn_catalog._meta(keyed, learned_by="x/y"),
                                                   "approved": False}, "id")
    with pytest.raises(deploy.DeployError, match="approve learned myhost"):
        deploy.deploy(site, "myhost", allow_commands=True)
    assert cli.main(["addons", "approve", "learned", "myhost"]) == 0
    assert deploy.deploy(site, "myhost", dry_run=True, allow_commands=True).status == "dry run"


def test_unknown_media_service_is_learned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate(monkeypatch)
    model = ResearchModel({"Proofhouse generates images, video, speech and music": json.dumps(MEDIA)})
    research = learn_catalog.Research("ollama", "m", transport=model)
    result = media.generate("image", "acme-images", "m", prompt="a cat", out=tmp_path / "out", max_cost_usd="1",
                            research=research, transport=lambda req: media.MediaResponse(200, content=b"x"))
    assert model.sent[0].startswith("Proofhouse generates images, video, speech and music")
    assert result.status == "refused" and "approve learned acme-images" in (result.message or "")
    assert media.find("acme-images") is not None


def test_unknown_training_service_is_learned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _gate(monkeypatch)
    data = tmp_path / "data.jsonl"
    line = json.dumps({"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]})
    data.write_text("\n".join([line] * 12) + "\n", encoding="utf-8")
    model = ResearchModel({"Proofhouse trains models through online APIs or local": json.dumps(TRAIN)})
    research = learn_catalog.Research("ollama", "m", transport=model)
    result = train.start("local-tune", "base", data, research=research, allow_commands=True, out_dir=tmp_path / "train-out")
    assert model.sent[0].startswith("Proofhouse trains models through online APIs or local")
    assert train.find("local-tune") is not None
    assert result.status in ("success", "error")
