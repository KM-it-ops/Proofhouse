"""One goal, many outputs: a planned launch built part by part through each engine, within one spending limit."""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, launch, live, media

SITE = {"index.html": '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width">'
                      "<title>Brew</title></head><body><h1>Brew</h1></body></html>"}
VIDEO = {"title": "Brew", "voiceover": "Coffee, faster.", "music": "lofi",
         "shots": [{"seconds": 2, "visual": "a cup", "caption": "Coffee"}, {"seconds": 2, "visual": "a phone", "caption": "faster"}]}


class Team:
    """One stand-in model playing every role a launch needs."""

    def __init__(self, plan: dict, tokens: int = 100) -> None:
        self.plan = plan
        self.tokens = tokens
        self.roles: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You plan product launches"):
            role, content = "plan", json.dumps(self.plan)
        elif text.startswith("You judge AI work"):
            role, content = "judge", json.dumps({"score": 9, "missing": [], "fix": ""})
        elif text.startswith("You build excellent websites"):
            role, content = "site", json.dumps({"files": SITE})
        elif text.startswith("You write launch and announcement copy"):
            role, content = "copy", "Brew is here. Order coffee in one tap."
        elif text.startswith("You write subagents"):
            role, content = "agent", "---\nname: brew-support\ndescription: Answers Brew customer questions.\n---\nBe helpful."
        elif text.startswith("You are a video producer"):
            role, content = "video", json.dumps(VIDEO)
        else:
            role, content = "other", "ok"
        self.roles.append(role)
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": self.tokens, "completion_tokens": self.tokens}})


PLAN = {"name": "Brew launch", "parts": [
    {"kind": "site", "brief": "A landing page for Brew, a one-tap coffee ordering app."},
    {"kind": "copy", "brief": "Launch post and email for Brew."},
    {"kind": "agent", "brief": "A support agent that answers Brew customer questions."},
    {"kind": "nonsense", "brief": "ignored"},
]}


def test_a_goal_becomes_every_planned_part_each_made_by_its_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))
    team = Team(PLAN)
    made = launch.run_launch("launch Brew, a one-tap coffee ordering app", provider_id="ollama", model="llama3",
                             out_dir=tmp_path / "l", transport=team)
    assert made.name == "Brew launch" and [p.kind for p in made.parts] == ["site", "copy", "agent"]
    assert [p.status for p in made.parts] == ["made", "made", "made"], [p.detail for p in made.parts]
    assert (tmp_path / "l" / "01-site" / "site" / "index.html").is_file()
    assert (tmp_path / "l" / "02-copy" / "final.md").read_text(encoding="utf-8").startswith("Brew is here.")
    assert (tmp_path / "l" / "03-agent" / "brew-support.md").is_file()
    assert team.roles[0] == "plan" and team.roles.count("judge") == 3
    record = json.loads((tmp_path / "l" / "launch.json").read_text(encoding="utf-8"))
    assert record["stopped"] == "finished" and len(record["parts"]) == 3
    assert record["proofhouse_version"] == proofhouse.__version__
    assert "## site: made" in (tmp_path / "l" / "README.md").read_text(encoding="utf-8")


def test_you_can_pick_the_parts(tmp_path: Path) -> None:
    seen: list[str] = []
    team = Team(PLAN)

    def spy(request: live.Request) -> live.Response:
        seen.append(" ".join(m["content"] for m in json.loads(request.body_bytes)["messages"]))
        return team(request)

    made = launch.run_launch("launch Brew", provider_id="ollama", model="m", parts=("copy",), out_dir=tmp_path / "l", transport=spy)
    assert [p.kind for p in made.parts] == ["copy"] and "Make exactly these parts, one each: copy." in seen[0]
    with pytest.raises(launch.LaunchError):
        launch.run_launch("x", provider_id="ollama", model="m", parts=("poster",), out_dir=tmp_path / "x")


def test_one_limit_covers_the_whole_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-launch-test-key")
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))
    assert cli.main(["providers", "price", "groq", "m", "--input", "100", "--output", "100"]) == 0
    made = launch.run_launch("launch Brew", provider_id="groq", model="m", max_cost_usd="0.70", out_dir=tmp_path / "l",
                             transport=Team(PLAN, tokens=1000))  # every call costs about $0.20
    assert Decimal(0) < made.spent_usd <= Decimal("0.70")
    assert made.parts[0].status != "skipped" and any(p.status in ("skipped", "not made") for p in made.parts)
    with pytest.raises(launch.LaunchError):
        launch.run_launch("x", provider_id="groq", model="m", out_dir=tmp_path / "x")


def test_a_video_part_without_a_visual_service_is_skipped_with_the_reason(tmp_path: Path) -> None:
    plan = {"name": "Brew", "parts": [{"kind": "video", "brief": "a 4-second hype video"}]}
    made = launch.run_launch("launch Brew", provider_id="ollama", model="m", out_dir=tmp_path / "l", transport=Team(plan))
    assert made.parts[0].status == "skipped" and "--visual-provider" in made.parts[0].detail


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg not installed")
def test_a_video_part_is_produced_by_the_studio(tmp_path: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x334455:s=320x180", "-frames:v", "1",
                    str(tmp_path / "f.png")], check=True)
    template = {"id": "local-images", "kinds": ["image"], "base_url": "http://localhost:7860", "auth": "none", "unit": "image",
                "submit": {"path": "/img", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"], "ext": "png"}}
    (tmp_path / "t.json").write_text(json.dumps(template), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0
    png = (tmp_path / "f.png").read_bytes()
    plan = {"name": "Brew", "parts": [{"kind": "video", "brief": "a 4-second hype video"}]}
    made = launch.run_launch(
        "launch Brew", provider_id="ollama", model="m", out_dir=tmp_path / "l", transport=Team(plan),
        video={"visual_provider": "local-images", "visual_model": "sdxl", "seconds": 4, "formats": ("1x1",), "size_scale": 0.1},
        media_transport=lambda r: media.MediaResponse(200, {"image": base64.b64encode(png).decode()}),
    )
    assert made.parts[0].status == "made", made.parts[0].detail
    assert (tmp_path / "l" / "01-video" / "studio.json").is_file()


def test_the_command_runs_a_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))
    monkeypatch.setattr(live, "_httpx_post", Team(PLAN))
    code = cli.main(["make", "launch Brew", "--kind", "launch", "--parts", "copy,agent", "--provider", "ollama", "--model", "m",
                     "--out", str(tmp_path / "l")])
    out = capsys.readouterr().out
    assert code == 0 and "copy" in out and "agent" in out and "README.md" in out
