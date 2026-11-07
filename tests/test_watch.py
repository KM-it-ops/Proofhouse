import json
import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import watch
from proofhouse.cli import main

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")

SRT = """1
00:00:00,200 --> 00:00:01,500
Say what you want.

2
00:00:02,200 --> 00:00:03,600
It keeps every version.

3
00:00:04,300 --> 00:00:05,600
It keeps every version again.
"""


def _film(folder: Path) -> Path:
    """Three two-second shots of plain colour with a hard cut between each, and a tone under them."""
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "video-16x9.mp4"
    colours = ["red", "blue", "white"]
    inputs = []
    for c in colours:
        inputs += ["-f", "lavfi", "-i", f"color=c={c}:s=320x180:r=30:d=2"]
    inputs += ["-f", "lavfi", "-i", "sine=frequency=440:duration=6"]
    chain = "".join(f"[{i}:v]" for i in range(3)) + "concat=n=3:v=1:a=0[v]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", chain, "-map", "[v]", "-map", "3:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    (folder / "captions.srt").write_text(SRT, encoding="utf-8")
    return out


@needs_ffmpeg
def test_a_film_s_shots_words_and_lines_said_again_are_measured(tmp_path: Path) -> None:
    film = watch.review(_film(tmp_path / "film-a"))
    assert film["name"] == "film-a" and film["shot_count"] == 3
    assert [round(c) for c in film["cuts"]] == [2, 4]
    assert [s["said"] for s in film["shots"]] == ["Say what you want.", "It keeps every version.",
                                                  "It keeps every version again."]
    assert film["words"] == 13 and film["said_again"] == [{"at": 4.3, "line": "It keeps every version again."}]
    assert film["loudness_lufs"] is not None and film["silent_share"] == 0


@needs_ffmpeg
def test_films_are_written_up_side_by_side_with_a_timeline_and_a_shot_sheet_each(tmp_path: Path) -> None:
    a = _film(tmp_path / "one")
    b = _film(tmp_path / "two" / "film")  # a folder called film is named after the folder above it
    out = tmp_path / "watch"
    assert main(["watch", str(a), str(b), "--out", str(out)]) == 0
    text = (out / "watch.md").read_text(encoding="utf-8")
    assert "| | one | two |" in text and "| Shots | 3 | 3 |" in text and "| Lines said again | 1 | 1 |" in text
    assert (out / "timeline.png").stat().st_size > 0
    assert (out / "shots-one.jpg").is_file() and (out / "shots-two.jpg").is_file()
    data = json.loads((out / "watch.json").read_text(encoding="utf-8"))
    assert [f["shot_count"] for f in data["films"]] == [3, 3]


@needs_ffmpeg
def test_a_label_and_captions_can_be_given_and_a_missing_film_is_a_plain_error(tmp_path: Path, capsys) -> None:
    a = _film(tmp_path / "x")
    srt = tmp_path / "other.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:01,000\nHello there.\n", encoding="utf-8")
    made = watch.watch([a], tmp_path / "w", captions=[srt], names=["Mine"])
    assert made["films"][0]["name"] == "Mine" and made["films"][0]["words"] == 2
    assert main(["watch", str(tmp_path / "nope.mp4"), "--out", str(tmp_path / "w2")]) == 2
    assert "no film at" in capsys.readouterr().err


def test_an_srt_file_is_read_into_timed_lines(tmp_path: Path) -> None:
    srt = tmp_path / "c.srt"
    srt.write_bytes("﻿1\r\n00:00:01,250 --> 00:00:02,000\r\nTwo\r\nlines\r\n\r\n2\r\nbad\r\n".encode("utf-8"))
    assert watch.read_srt(srt) == [(1.25, 2.0, "Two lines")]


def test_a_cut_is_the_strongest_change_nearby_and_never_a_fade_at_either_end() -> None:
    change = [0.0] * 60
    change[3], change[20], change[21], change[40], change[58] = 90, 30, 50, 10, 90
    seconds = 10.0
    assert watch.cuts(change, seconds) == [round((21 - watch.LAG / 2) / watch.FPS, 2)]
