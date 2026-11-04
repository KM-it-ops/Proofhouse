"""What the judge is shown: a contact sheet of the film (or the picture itself, made small) and the facts of its sound."""
from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import spend, studio

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg is not on this machine")


def _film(path: Path, size: str, seconds: float, tone_seconds: float | None = None) -> Path:
    args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=25:duration={seconds}"]
    if tone_seconds is not None:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={tone_seconds}", "-af", "apad", "-t", str(seconds)]
    subprocess.run(args + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _side(path: Path) -> tuple[int, int]:
    size = spend.picture_size(path.read_bytes(), "jpeg")
    assert size is not None
    return size


@needs_ffmpeg
@pytest.mark.parametrize("size", ["1920x1080", "1080x1920", "1080x1080"])
def test_a_film_becomes_one_sheet_of_twelve_moments_small_enough_to_send(tmp_path: Path, size: str) -> None:
    film = _film(tmp_path / "f.mp4", size, 6)
    sheet = studio.contact_sheet(film, tmp_path / "sheet.jpg", kind="video")
    assert sheet is not None
    width, height = _side(sheet)
    assert max(width, height) <= spend.PICTURE_MAX_SIDE and min(width, height) >= 300
    w, h = (int(v) for v in size.split("x"))
    # four across, three down, each moment keeping the film's shape
    assert abs((width / 4) / (height / 3) - w / h) < 0.05


@needs_ffmpeg
def test_a_big_picture_is_made_small_enough_to_send_and_keeps_its_shape(tmp_path: Path) -> None:
    big = tmp_path / "big.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=3000x1500:duration=1",
                    "-frames:v", "1", str(big)], check=True)
    small = studio.contact_sheet(big, tmp_path / "small.jpg", kind="image")
    assert small is not None and _side(small) == (1024, 512)


@needs_ffmpeg
def test_the_sheet_goes_out_as_an_inline_picture_the_spend_gate_accepts(tmp_path: Path) -> None:
    sheet = studio.contact_sheet(_film(tmp_path / "f.mp4", "1280x720", 3), tmp_path / "s.jpg", kind="video")
    assert sheet is not None
    url = studio.data_url(sheet)
    assert url.startswith("data:image/jpeg;base64,") and base64.b64decode(url.split(",", 1)[1]) == sheet.read_bytes()


def test_a_file_that_is_not_a_film_gives_no_sheet(tmp_path: Path) -> None:
    junk = tmp_path / "f.mp4"
    junk.write_bytes(b"film")
    assert studio.contact_sheet(junk, tmp_path / "s.jpg", kind="video") is None
    assert studio.sound_facts(junk) is None


@needs_ffmpeg
def test_the_sound_facts_say_how_loud_it_is_and_how_much_is_silent(tmp_path: Path) -> None:
    facts = studio.sound_facts(_film(tmp_path / "f.mp4", "640x360", 6, tone_seconds=4))
    assert facts is not None
    assert -30 < facts["loudness_lufs"] < -10 and -30 < facts["peak_dbfs"] <= 0
    assert facts["seconds"] == pytest.approx(6, abs=0.2)
    assert facts["silent_share"] == pytest.approx(2 / 6, abs=0.06)  # the last two seconds are silent


@needs_ffmpeg
def test_a_film_with_no_sound_has_no_sound_facts(tmp_path: Path) -> None:
    assert studio.sound_facts(_film(tmp_path / "f.mp4", "640x360", 2)) is None
