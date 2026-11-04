"""Real recordings for films: a terminal command as it runs, a web app as it is used, a whole page."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proofhouse import capture, recording, sitecheck

needs_browser = pytest.mark.skipif(sitecheck.find_browser() is None, reason="no Chrome or Chromium")
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")


def test_terminal_recording_keeps_the_real_rhythm(tmp_path: Path) -> None:
    code = "import time; print('first', flush=True); time.sleep(0.8); print('second', flush=True)"
    chunks = recording.record_command([sys.executable, "-c", code], cwd=tmp_path)
    text = "".join(c.text for c in chunks)
    assert "first" in text and "second" in text
    first = next(c.at for c in chunks if "first" in c.text)
    second = next(c.at for c in chunks if "second" in c.text)
    assert second - first >= 0.6


def test_terminal_recording_streams_python_programs_that_do_not_flush(tmp_path: Path) -> None:
    code = "import time; print('one'); time.sleep(0.8); print('two')"
    chunks = recording.record_command([sys.executable, "-c", code], cwd=tmp_path)
    one = next(c.at for c in chunks if "one" in c.text)
    two = next(c.at for c in chunks if "two" in c.text)
    assert two - one >= 0.6


def test_terminal_recording_hides_private_text(tmp_path: Path) -> None:
    code = "print('key is s3cret-value')"
    chunks = recording.record_command([sys.executable, "-c", code], cwd=tmp_path, redact=("s3cret-value",))
    text = "".join(c.text for c in chunks)
    assert "s3cret" not in text
    assert capture._REDACTED in text


def test_terminal_recording_never_uses_a_shell(tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError):
        recording.record_command("echo hi && echo there", cwd=tmp_path)  # type: ignore[arg-type]


def test_terminal_recording_stops_a_command_that_hangs(tmp_path: Path) -> None:
    code = "import time; print('start', flush=True); time.sleep(30)"
    with pytest.raises(capture.CaptureError, match="did not finish"):
        recording.record_command([sys.executable, "-c", code], cwd=tmp_path, timeout=1)


def test_terminal_recording_marks_a_failing_exit(tmp_path: Path) -> None:
    chunks = recording.record_command([sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path)
    assert "[exit 3]" in "".join(c.text for c in chunks)


def test_terminal_timeline_types_first_then_shortens_long_waits() -> None:
    chunks = [recording.Chunk(0.0, "a\n"), recording.Chunk(6.0, "b\n"), recording.Chunk(6.1, "c\n")]
    tl = recording.terminal_timeline("proofhouse providers list", chunks, max_wait=1.0)
    assert len(tl["keys"]) == len("proofhouse providers list")
    assert tl["keys"] == sorted(tl["keys"])
    starts = [line["at"] for line in tl["output"]]
    assert starts[0] > tl["keys"][-1]  # output appears after the command is typed
    assert starts[1] - starts[0] <= 1.0 + 1e-9  # the 6 s wait is shortened
    assert starts[2] - starts[1] == pytest.approx(0.1, abs=1e-6)  # short gaps keep their rhythm
    assert tl["seconds"] >= starts[-1]


@needs_browser
def test_full_page_capture_is_taller_than_the_window_and_keeps_the_bottom(tmp_path: Path) -> None:
    from PIL import Image

    page = tmp_path / "tall.html"
    page.write_text(
        "<html><body style='margin:0;background:#fff'>"
        "<div style='height:2400px;background:linear-gradient(#123,#456)'></div>"
        "<footer style='height:120px;background:#e01010'></footer></body></html>",
        encoding="utf-8",
    )
    out = capture.render_page(page.as_uri(), tmp_path / "tall.png", size=(800, 600), full_page=True)
    with Image.open(out) as im:
        assert im.height >= 2500
        assert im.width == 800
        r, g, b = im.convert("RGB").getpixel((400, im.height - 40))
    assert r > 180 and g < 60 and b < 60


@needs_browser
def test_full_page_capture_takes_a_phone_width_at_double_sharpness(tmp_path: Path) -> None:
    from PIL import Image

    page = tmp_path / "phone.html"
    page.write_text("<html><body style='margin:0'><div style='height:1500px;background:#0a0'></div></body></html>",
                    encoding="utf-8")
    out = capture.render_page(page.as_uri(), tmp_path / "phone.png", size=(390, 844), full_page=True, scale=2)
    with Image.open(out) as im:
        assert im.width == 780
        assert im.height >= 3000


_APP = """<html><body style='margin:0;background:#202020;font:24px sans-serif;color:#fff'>
<input id='bill' style='position:absolute;left:40px;top:40px;width:300px;height:40px'>
<button id='go' style='position:absolute;left:400px;top:300px;width:200px;height:80px'
 onclick="document.body.style.background='#00c000';document.getElementById('out').textContent=
 document.getElementById('bill').value">Split</button>
<div id='out' style='position:absolute;left:40px;top:500px'></div></body></html>"""


@needs_browser
@needs_ffmpeg
def test_app_recording_uses_the_page_and_records_where_it_clicked(tmp_path: Path) -> None:
    page = tmp_path / "app.html"
    page.write_text(_APP, encoding="utf-8")
    steps = [
        {"do": "type", "selector": "#bill", "text": "84.50"},
        {"do": "click", "selector": "#go"},
        {"do": "wait", "seconds": 0.5},
    ]
    rec = recording.record_app(page.as_uri(), steps, tmp_path / "rec", size=(960, 600))
    assert rec.video.is_file()
    meta = json.loads((tmp_path / "rec" / "recording.json").read_text(encoding="utf-8"))
    assert meta["size"] == [960, 600]
    assert len(meta["keys"]) == len("84.50")
    clicks = meta["clicks"]
    assert len(clicks) == 2  # one into the field, one on the button
    x, y = clicks[-1]["x"], clicks[-1]["y"]
    assert 400 <= x <= 600 and 300 <= y <= 380
    assert meta["moves"], "the cursor path is kept for the overlay"
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(rec.video)], capture_output=True, text=True, check=True)
    assert float(probe.stdout) >= 1.0
    last = tmp_path / "last.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.2", "-i", str(rec.video), "-frames:v", "1",
                    str(last)], check=True)
    from PIL import Image

    with Image.open(last) as im:
        r, g, b = im.convert("RGB").getpixel((900, 20))
    assert g > 150 and r < 60  # the click really ran the app


def test_app_recording_refuses_an_unknown_step(tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError, match="step"):
        recording.check_steps([{"do": "launch-missiles"}])
