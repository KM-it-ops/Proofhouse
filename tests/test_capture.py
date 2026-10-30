"""Real captures as video shots: command output and pages become frames, and the script writer works from a fact sheet."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from proofhouse import capture, sitecheck, studio

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
