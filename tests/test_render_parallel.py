"""Beats are independent, so they can be drawn in separate processes; the film must come out the same as drawn one by one."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import motion

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")


def _scene(text: str, seconds: float = 0.6) -> dict:
    return {"size": (320, 180), "fps": 30, "seconds": seconds, "base": {"kind": "living", "seed": len(text)},
            "layers": [{"kind": "title", "text": text}]}


def _frame_hashes(path: Path) -> list[str]:
    done = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "framemd5", "-"], capture_output=True,
                          text=True, check=True, timeout=60)
    return [line.rsplit(",", 1)[-1].strip() for line in done.stdout.splitlines() if line and not line.startswith("#")]


@needs_ffmpeg
def test_beats_drawn_in_separate_processes_match_beats_drawn_one_by_one(tmp_path: Path) -> None:
    words = ["Say what you want", "Pick any model", "Get the finished film"]
    serial = [(_scene(w), tmp_path / f"s{i}.mp4") for i, w in enumerate(words)]
    parallel = [(_scene(w), tmp_path / f"p{i}.mp4") for i, w in enumerate(words)]
    one = motion.render_all(serial, workers=1)
    many = motion.render_all(parallel, workers=3)
    assert [p.name for p in many] == ["p0.mp4", "p1.mp4", "p2.mp4"]  # the order of the beats, not of who finished first
    for a, b in zip(one, many):
        assert _frame_hashes(a) == _frame_hashes(b) and len(_frame_hashes(a)) == 18


@needs_ffmpeg
def test_a_beat_that_cannot_be_drawn_stops_the_rest_with_its_own_error(tmp_path: Path) -> None:
    bad = {"size": (320, 180), "fps": 30, "seconds": 0.5, "base": {"kind": "living"}, "layers": [{"kind": "nonsense"}]}
    jobs = [(_scene("fine"), tmp_path / "a.mp4"), (bad, tmp_path / "b.mp4"), (_scene("also fine"), tmp_path / "c.mp4")]
    with pytest.raises(motion.MotionError):
        motion.render_all(jobs, workers=2)
