"""A finished film has to be small enough to upload: the bitrate is worked out from the size cap, the final encode
is held to it, and a film that still comes out over is squeezed with a two-pass encode."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import storyboard

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")


def test_the_rate_leaves_room_for_the_sound_and_the_wrapper() -> None:
    cap, total = 25 * 1024 * 1024, 45.7
    rate = storyboard.video_rate(total, cap)
    picture_and_sound = (rate + storyboard.AUDIO_BPS) * total / 8
    assert picture_and_sound <= cap * 0.96
    assert rate > 3_000_000  # a 45 s film still gets a real picture rate


def test_a_longer_film_gets_a_lower_rate_and_a_tiny_cap_never_goes_to_zero() -> None:
    assert storyboard.video_rate(90, 25 * 2**20) < storyboard.video_rate(45, 25 * 2**20)
    assert storyboard.video_rate(600, 1_000_000) >= storyboard.MIN_VIDEO_BPS


def test_the_final_encode_is_held_to_the_rate_and_can_be_left_open() -> None:
    held = storyboard.mix_command(Path("p.mp4"), None, None, None, 45.0, [], Path("o.mp4"), loudness="anull")
    rate = str(storyboard.video_rate(45.0))
    assert held[held.index("-maxrate") + 1] == rate
    assert held[held.index("-bufsize") + 1] == str(2 * int(rate))
    open_ended = storyboard.mix_command(Path("p.mp4"), None, None, None, 45.0, [], Path("o.mp4"), loudness="anull",
                                        cap=None)
    assert "-maxrate" not in open_ended


def test_the_squeeze_is_two_passes_that_share_one_log_and_keep_the_sound() -> None:
    one, two = storyboard.squeeze_commands(Path("in.mp4"), 45.0, 25 * 2**20, Path("out.mp4"), Path("log"))
    assert "-pass" in one and one[one.index("-pass") + 1] == "1" and "-an" in one
    assert two[two.index("-pass") + 1] == "2" and two[two.index("-c:a") + 1] == "copy"
    assert one[one.index("-passlogfile") + 1] == two[two.index("-passlogfile") + 1] == "log"
    assert one[one.index("-b:v") + 1] == two[two.index("-b:v") + 1]


def _noisy(path: Path, seconds: int) -> Path:
    """A test pattern with moving grain at 640x360 and a tone: grain cannot be compressed, so the file is huge."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=30:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=f=440:d={seconds}", "-vf", "noise=alls=20:allf=t",
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
                   check=True, timeout=120)
    return path


@needs_ffmpeg
def test_a_film_that_comes_out_over_the_cap_is_squeezed_under_it(tmp_path: Path) -> None:
    source = _noisy(tmp_path / "noisy.mp4", 8)
    cap = 600_000
    assert source.stat().st_size > cap * 2  # the test is only fair if it starts well over
    out = tmp_path / "small.mp4"
    one, two = storyboard.squeeze_commands(source, 8.0, cap, out, tmp_path / "pass")
    for cmd in (one, two):
        subprocess.run(cmd, check=True, timeout=120, cwd=tmp_path)
    assert out.stat().st_size <= cap
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, timeout=60).stdout.split()
    assert sorted(kinds) == ["audio", "video"]


def test_the_joined_middle_step_is_fast_and_the_kept_encode_is_not() -> None:
    beats = storyboard.parse({"beats": [{"say": "One.", "show": {"type": "title", "text": "A"}},
                                        {"say": "Two.", "show": {"type": "title", "text": "B"}}]}, Path("."))
    beats[1].cut = "cut"
    join = storyboard.join_command([Path("a.mp4"), Path("b.mp4")], beats, Path("j.mp4"))
    assert join[join.index("-preset") + 1] == storyboard.JOIN_PRESET == "veryfast"
    final = storyboard.mix_command(Path("p.mp4"), None, None, None, 45.0, [], Path("o.mp4"), loudness="anull")
    assert final[final.index("-preset") + 1] == "medium"
