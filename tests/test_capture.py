"""Real captures as video shots: command output and pages become frames, and the script writer works from a fact sheet."""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proofhouse import capture, cli, live, media, sitecheck, studio

FACTS = {
    "product": "Proofhouse",
    "summary": "You say what you want and pick any model; it makes it, runs it, improves it and keeps every version.",
    "facts": ["It keeps every version of what it makes.", "Providers are data: adding one is a line."],
    "commands": [{"id": "version", "argv": [sys.executable, "-c", "print('proofhouse 0.10.2')"],
                  "shows": "the installed version answering"}],
    "pages": [{"id": "compare", "url": "file:///compare.html", "shows": "two models side by side on one job"}],
}


def test_the_card_escapes_the_output_hides_private_text_and_shortens_long_output() -> None:
    page = capture.card_html("proofhouse check <site>", "<b>ok</b>\nC:\\Users\\alice\\work\n" + "\n".join(f"row {i}" for i in range(60)),
                             redact=("alice",), max_lines=10)
    assert "&lt;b&gt;ok&lt;/b&gt;" in page and "<b>ok</b>" not in page
    assert "alice" not in page
    assert "proofhouse check &lt;site&gt;" in page
    assert "more lines" in page and "row 59" not in page


def test_a_command_runs_without_a_shell_and_a_hung_one_is_reported(tmp_path: Path) -> None:
    out = capture.run_command([sys.executable, "-c", "print('a && b')"], cwd=tmp_path, timeout=20)
    assert out.strip() == "a && b"
    with pytest.raises(capture.CaptureError, match="did not finish"):
        capture.run_command([sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path, timeout=1)
    with pytest.raises(capture.CaptureError, match="could not start"):
        capture.run_command(["no-such-program-xyz"], cwd=tmp_path, timeout=5)


def test_a_failing_command_keeps_its_output_and_says_how_it_ended(tmp_path: Path) -> None:
    out = capture.run_command([sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"], cwd=tmp_path, timeout=20)
    assert "bad" in out and "exit 3" in out


def test_the_screenshot_command_asks_for_the_frame_size() -> None:
    command = capture.screenshot_command("chrome", "file:///x.html", (1920, 1080), Path("out.png"))
    assert command[0] == "chrome"
    assert "--window-size=1920,1080" in command
    assert any(part.startswith("--screenshot=") and part.endswith("out.png") for part in command)
    assert command[-1] == "file:///x.html"


def test_a_captured_still_is_shown_whole_not_zoomed_into() -> None:
    still = studio.shot_command(Path("c.png"), "still", 5, (1920, 1080), Path("o.mp4"))
    assert not any("zoompan" in part for part in still)
    assert any("pad=1920:1080" in part for part in still)
    assert any("zoompan" in part for part in studio.shot_command(Path("g.png"), "image", 5, (1920, 1080), Path("o.mp4")))


def test_without_a_browser_the_error_says_so(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sitecheck, "find_browser", lambda: None)
    with pytest.raises(capture.CaptureError, match="Chrome"):
        capture.render_card("x", "y", tmp_path / "card.png")


@pytest.mark.skipif(sitecheck.find_browser() is None, reason="no Chrome or Chromium")
def test_a_real_card_is_a_png_of_the_asked_size(tmp_path: Path) -> None:
    made = capture.render_card("proofhouse --version", "proofhouse 0.10.2", tmp_path / "card.png", size=(1280, 720))
    assert made.is_file() and sitecheck._png_width(made) == 1280


def test_a_fact_sheet_is_checked_when_it_is_loaded(tmp_path: Path) -> None:
    good = tmp_path / "facts.json"
    good.write_text(__import__("json").dumps(FACTS), encoding="utf-8")
    assert studio.load_facts(good)["product"] == "Proofhouse"
    for bad in ('{"product": "x"}', "not json", '{"product": "x", "summary": "s", "commands": [{"id": "a"}]}',
                '{"product": "x", "summary": "s", "commands": [{"id": "a", "argv": ["x"]}, {"id": "a", "argv": ["y"]}]}'):
        path = tmp_path / "bad.json"
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(studio.StudioError):
            studio.load_facts(path)


def test_the_script_prompt_carries_the_facts_and_asks_for_speech_not_slogans() -> None:
    prompt = studio.script_prompt("a launch film", 30, FACTS)
    for needle in ("Proofhouse", "version", "compare", "two models side by side", "It keeps every version", "short phrases"):
        assert needle in prompt
    assert "30" in prompt and "a launch film" in prompt
    assert studio.script_prompt("a launch film", 30) == studio._SCRIPT.format(seconds=30, brief="a launch film")


def test_capture_shots_name_a_listed_item_and_the_writer_cannot_invent_one() -> None:
    data = {"title": "t", "voiceover": "v", "music": "m", "shots": [
        {"seconds": 4, "source": "capture", "ref": "version", "caption": "It answers"},
        {"seconds": 4, "source": "generate", "visual": "a calm workshop", "caption": "Made"},
        {"seconds": 4, "source": "capture", "ref": "compare", "caption": "Side by side"},
    ]}
    _, _, _, shots = studio.plan_from(data, 12, FACTS)
    assert [s.source for s in shots] == ["capture", "generate", "capture"]
    assert [s.ref for s in shots] == ["version", None, "compare"]
    assert shots[0].visual == "the installed version answering"
    invented = {"shots": [{"seconds": 4, "source": "capture", "ref": "rm-everything", "caption": "x"}]}
    with pytest.raises(studio.StudioError, match="rm-everything"):
        studio.plan_from(invented, 4, FACTS)
    with pytest.raises(studio.StudioError):
        studio.plan_from(data, 12, None)  # capture shots with no fact sheet to take them from


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg not installed")


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@pytest.fixture
def capture_services(tmp_path: Path) -> dict[str, bytes]:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x2255aa:s=320x180", "-frames:v", "1", str(tmp_path / "frame.png"))
    templates = [
        {"id": "local-images", "kinds": ["image"], "base_url": "http://localhost:7860", "auth": "none", "unit": "image",
         "submit": {"path": "/img", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"], "ext": "png"}},
    ]
    (tmp_path / "t.json").write_text(json.dumps(templates), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0
    return {"png": (tmp_path / "frame.png").read_bytes()}


CAPTURE_SCRIPT = {
    "title": "Real and generated",
    "voiceover": "Here is the real output. Here is something made.",
    "music": "calm electronic",
    "shots": [
        {"seconds": 3, "source": "capture", "ref": "version", "caption": "Real"},
        {"seconds": 3, "source": "generate", "visual": "a calm workshop for the product", "caption": "Made"},
    ],
}


@needs_ffmpeg
def test_capture_and_generated_shots_charge_once_for_media_and_need_allow_commands(
    tmp_path: Path, capture_services: dict[str, bytes], monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(FACTS), encoding="utf-8")
    png = capture_services["png"]
    renders: list[str] = []

    def fake_card(command: str, output: str, out_png: Path, **kwargs: object) -> Path:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        _ffmpeg("-f", "lavfi", "-i", "color=c=0x333333:s=320x180", "-frames:v", "1", str(out_png))
        renders.append("card")
        return out_png

    monkeypatch.setattr(capture, "render_card", fake_card)
    media_calls: list[str] = []

    def writer(request: live.Request) -> live.Response:
        return live.Response(200, {"choices": [{"message": {"content": json.dumps(CAPTURE_SCRIPT)}}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    def post(request: media.MediaRequest) -> media.MediaResponse:
        media_calls.append(request.url)
        return media.MediaResponse(200, {"image": base64.b64encode(png).decode()})

    blocked = studio.produce(
        "film", provider_id="ollama", model="m", visual_provider="local-images", visual_model="sdxl",
        seconds=6, formats=("16x9",), out_dir=tmp_path / "blocked", facts=FACTS, allow_commands=False,
        text_transport=writer, media_transport=post,
    )
    assert "allow-commands" in blocked.stopped.lower()
    assert renders == [] and media_calls == []

    made = studio.produce(
        "film", provider_id="ollama", model="m", visual_provider="local-images", visual_model="sdxl",
        seconds=6, out_dir=tmp_path / "video", facts=FACTS, allow_commands=True,
        text_transport=writer, media_transport=post, size_scale=0.1,
    )
    assert made.stopped == "finished", made.stopped
    assert set(made.renders) == {"16x9", "9x16", "1x1"}
    assert renders == ["card"]
    assert len(media_calls) == 1


def test_the_card_hides_private_text_in_the_command_line_too() -> None:
    page = capture.card_html("proofhouse --project C:\\Users\\alice\\repo", "ok", redact=("C:\\Users\\alice",))
    assert "alice" not in page and "[hidden]" in page


def test_private_text_lists_the_home_folder_in_every_spelling_and_the_user_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("C:/Users/alice")))
    found = capture.private_text()
    assert any(part.lower().endswith("alice") and "\\\\" in part for part in found) or "C:/Users/alice" in found
    assert "alice" in found
    assert list(found) == sorted(found, key=len, reverse=True)


def test_the_video_command_hands_facts_and_allow_commands_over_once_and_needs_no_visual_service_up_front(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts_path = tmp_path / "facts.json"
    facts_path.write_text(json.dumps(FACTS), encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_produce(brief: str, **kwargs: object) -> studio.Production:
        seen.update(kwargs)
        return studio.Production(tmp_path / "out")

    monkeypatch.setattr(studio, "produce", fake_produce)
    code = cli.main(["make", "a launch film", "--kind", "video", "--provider", "ollama", "--model", "m",
                     "--facts", str(facts_path), "--allow-commands", "--out", str(tmp_path / "out")])
    assert seen, "the command never reached produce"  # it used to crash, then refuse a capture-only film for want of a visual service
    assert code == 7  # the fake made no renders
    assert seen["allow_commands"] is True
    assert seen["facts"]["product"] == "Proofhouse"  # type: ignore[index]
    assert not seen["visual_provider"]


def test_a_command_may_carry_the_line_to_show_instead_of_its_real_arguments(tmp_path: Path) -> None:
    sheet = dict(FACTS, commands=[{"id": "v", "argv": ["uv", "run", "--project", "C:\\x", "proofhouse", "--version"],
                                   "display": "proofhouse --version"}])
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(sheet), encoding="utf-8")
    assert studio.load_facts(path)["commands"][0]["display"] == "proofhouse --version"
    sheet["commands"][0]["display"] = 5
    path.write_text(json.dumps(sheet), encoding="utf-8")
    with pytest.raises(studio.StudioError, match="display"):
        studio.load_facts(path)


@needs_ffmpeg
def test_a_film_of_captures_only_needs_no_visual_service_and_other_clip_types_are_not_taken_for_pictures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clip = tmp_path / "bridge.avi"
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x225588:s=320x180:d=2", "-pix_fmt", "yuv420p", str(clip))
    card = tmp_path / "card.png"
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x333333:s=320x180", "-frames:v", "1", str(card))

    def fake_card(command: str, output: str, out_png: Path, **kwargs: object) -> Path:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(card, out_png)
        return out_png

    monkeypatch.setattr(capture, "render_card", fake_card)
    script = {"title": "t", "voiceover": "Real output.", "music": "calm",
              "shots": [{"seconds": 3, "source": "capture", "ref": "version", "caption": "Real"}]}

    def writer(request: live.Request) -> live.Response:
        return live.Response(200, {"choices": [{"message": {"content": json.dumps(script)}}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    made = studio.produce("film", provider_id="ollama", model="m", seconds=3, formats=("16x9",), out_dir=tmp_path / "v",
                          facts=FACTS, allow_commands=True, text_transport=writer, size_scale=0.1)
    assert made.stopped == "finished", made.stopped

    shots = [studio.Shot(seconds=2, visual="x", caption="", file=str(card)), studio.Shot(seconds=2, visual="x", caption="", file=str(clip))]
    (tmp_path / "mixed").mkdir()
    again = studio.assemble(tmp_path / "mixed", shots, visual_kind="mixed", formats=("16x9",), size_scale=0.1, captions=False,
                            voice_file=None, music_file=None, production=studio.Production(tmp_path / "mixed"))
    assert again.renders and not [c for c in again.checks if not c["ok"]]
