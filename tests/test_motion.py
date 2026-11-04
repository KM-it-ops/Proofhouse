"""The motion layer: springs, typing rhythm, the building blocks, and renderers as data."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proofhouse import motion

pytest.importorskip("PIL")
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")

SMALL = [640, 360]  # scenes are written in 1920-wide design pixels and drawn at any size


def _scene(layers: list[dict], **extra: object) -> dict:
    return {"size": SMALL, "fps": 30, "seconds": 3.0, "layers": layers, **extra}


def _alpha_sum(img) -> int:  # noqa: ANN001
    return sum(img.getchannel("A").getdata())


def _lit_box(img, threshold: int = 40) -> tuple[int, int, int, int] | None:  # noqa: ANN001
    return img.getchannel("A").point(lambda v: 255 if v > threshold else 0).getbbox()


def test_spring_settles_on_one_and_overshoots_when_loose() -> None:
    assert motion.spring(0) == 0
    assert motion.spring(3.0) == pytest.approx(1.0, abs=0.01)
    loose = [motion.spring(i / 30, damping=8, stiffness=200) for i in range(60)]
    assert max(loose) > 1.05  # a loose spring bounces past its target
    tight = [motion.spring(i / 30, damping=30, stiffness=120) for i in range(60)]
    assert max(tight) <= 1.0001


def test_typing_is_uneven_and_repeatable() -> None:
    times = motion.char_times("proofhouse providers list", 14, seed=2)
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert len(times) == len("proofhouse providers list") + 1
    assert max(gaps) > 1.5 * min(gaps)  # never a metronome
    assert times == motion.char_times("proofhouse providers list", 14, seed=2)
    assert motion.typed_count(times, -1) == 0
    assert motion.typed_count(times, times[-1] + 1) == len("proofhouse providers list")


def test_unknown_layer_kind_is_refused_plainly() -> None:
    with pytest.raises(motion.MotionError, match="kind"):
        motion.check_scene(_scene([{"kind": "hologram"}]))


def test_title_words_spring_in_one_after_another() -> None:
    scene = _scene([{"kind": "title", "text": "Say what you want", "at": 0.5, "size": 120}])
    before = motion.frame(scene, 0.4)
    assert _alpha_sum(before) == 0  # nothing before it starts, and no background: transparent
    early, late = motion.frame(scene, 0.62), motion.frame(scene, 1.6)
    assert 0 < _alpha_sum(early) < _alpha_sum(late)
    box = _lit_box(late)
    assert box is not None
    left, top, right, bottom = box
    assert abs((left + right) / 2 - 320) < 20 and abs((top + bottom) / 2 - 180) < 25  # centred by default
    r, g, b, a = late.getpixel(((left + right) // 2, (top + bottom) // 2))  # noqa: F841
    lit = [late.getpixel((x, (top + bottom) // 2)) for x in range(left, right)]
    assert any(p[3] > 200 and p[1] > 180 for p in lit)  # mint text, fully drawn


def test_title_fades_out_before_it_ends() -> None:
    scene = _scene([{"kind": "title", "text": "Gone", "at": 0.0, "until": 2.0}])
    assert _alpha_sum(motion.frame(scene, 1.9)) < _alpha_sum(motion.frame(scene, 1.4))
    assert _alpha_sum(motion.frame(scene, 2.05)) == 0


def test_chips_cascade_and_highlight_in_the_accent_colour() -> None:
    items = ["OpenAI", "Anthropic", "Google", "Ollama", "Mistral", "xAI"]
    scene = _scene([{"kind": "chips", "items": items, "at": 0.2, "stagger": 0.12, "highlight": ["Ollama"]}])
    sums = [_alpha_sum(motion.frame(scene, t)) for t in (0.25, 0.5, 0.8, 1.6)]
    assert sums == sorted(sums) and sums[0] < sums[-1]
    done = motion.frame(scene, 1.6).convert("RGB")
    accent = motion.rgb(motion.THEME["accent"])
    assert any(all(abs(c - a) < 30 for c, a in zip(done.getpixel((x, y)), accent))
               for x in range(0, 640, 3) for y in range(120, 240, 3))


def test_counter_counts_up_and_lands_on_the_number() -> None:
    layer = {"kind": "counter", "to": 92, "at": 0.5, "duration": 1.0, "suffix": "%"}
    assert motion.counter_value(layer, 0.4) == 0
    mid = motion.counter_value(layer, 1.0)
    assert 0 < mid < 92
    assert motion.counter_value(layer, 1.5) == 92
    scene = _scene([layer])
    assert _alpha_sum(motion.frame(scene, 1.0)) > 0


def test_cursor_follows_its_path_and_ripples_on_a_click() -> None:
    layer = {"kind": "cursor", "moves": [{"t": 0.0, "x": 300, "y": 300}, {"t": 1.0, "x": 1500, "y": 700}],
             "clicks": [{"t": 1.1, "x": 1500, "y": 700}]}
    scene = _scene([layer])
    start = _lit_box(motion.frame(scene, 0.0))
    assert start is not None and abs(start[0] - 100) < 8 and abs(start[1] - 100) < 8  # pointer tip at 300/3
    end = _lit_box(motion.frame(scene, 1.05))
    assert end is not None and abs(end[0] - 500) < 8
    ripple = motion.frame(scene, 1.3)
    box = _lit_box(ripple, threshold=20)
    assert box is not None and box[0] < 495 < box[2]  # the ring spreads around the click point


def test_terminal_types_the_command_then_shows_the_output() -> None:
    timeline = {"command": "proofhouse providers list", "keys": [0.2 + i * 0.05 for i in range(25)],
                "enter": 1.7, "output": [{"at": 1.9, "text": "openai\n"}, {"at": 2.2, "text": "ollama\n"}],
                "seconds": 3.0}
    typed, out = motion.terminal_state(timeline, 0.5)
    assert 0 < len(typed) < 25 and out == ""
    typed, out = motion.terminal_state(timeline, 2.0)
    assert typed == "proofhouse providers list" and out == "openai\n"
    scene = _scene([{"kind": "terminal", "timeline": timeline, "box": [160, 120, 1600, 840]}])
    assert _alpha_sum(motion.frame(scene, 2.5)) > _alpha_sum(motion.frame(scene, 0.1)) > 0


def test_text_scale_draws_the_words_inside_plates_boxes_and_labels_bigger() -> None:
    timeline = {"command": "proofhouse providers list", "keys": [0.2 + i * 0.05 for i in range(25)],
                "enter": 1.7, "output": [{"at": 1.9, "text": "openai\n"}], "seconds": 3.0}
    layers = [{"kind": "lower_third", "title": "Ada Lovelace", "subtitle": "maker"},
              {"kind": "callout", "box": [600, 400, 400, 200], "label": "Scored", "spotlight": 0},
              {"kind": "cards", "items": [{"title": "Prompts", "body": "Made and kept"}, "Media"], "columns": 2},
              {"kind": "panel", "rows": [{"text": "Prompt", "value": "ok"}, "Media"], "title": "Runs"},
              {"kind": "terminal", "timeline": timeline}]
    for layer in layers:
        bright = [sum(motion.frame(_scene([dict(layer, text_scale=s)]), 2.6).convert("L").histogram()[151:])
                  for s in (1.0, 1.5)]
        assert bright[1] > 1.6 * bright[0] > 0, layer["kind"]  # half as big again in each direction
    with pytest.raises(motion.MotionError, match="text_scale"):
        motion.check_scene(_scene([dict(layers[0], text_scale="big")]))


def test_living_background_moves_and_is_never_flat() -> None:
    scene = _scene([], base={"kind": "living"})
    a, b = motion.frame(scene, 0.0).convert("L"), motion.frame(scene, 2.0).convert("L")
    lo, hi = a.getextrema()
    assert hi - lo > 12  # not a flat colour
    from PIL import ImageChops

    assert ImageChops.difference(a, b).getbbox() is not None  # it drifts over time


def test_image_layer_scrolls_a_full_page_capture(tmp_path: Path) -> None:
    from PIL import Image

    tall = Image.new("RGB", (400, 2000), (0, 0, 200))
    tall.paste((220, 0, 0), (0, 1800, 400, 2000))  # red footer at the very bottom
    path = tmp_path / "page.png"
    tall.save(path)
    layer = {"kind": "image", "file": str(path), "box": [660, 90, 600, 900], "frame": "plain",
             "scroll": {"at": 0.2, "until": 2.0}}
    scene = _scene([layer])
    top = motion.frame(scene, 0.1).convert("RGB")
    bottom = motion.frame(scene, 2.5).convert("RGB")
    probe = (320, 300)  # inside the box, near its lower edge (box spans y 30-330 at this size)
    assert top.getpixel(probe)[2] > 150  # blue page at the top
    assert bottom.getpixel(probe)[0] > 150  # scrolled down to the red footer


def test_callout_dims_everything_except_the_box() -> None:
    scene = _scene([{"kind": "callout", "box": [600, 300, 600, 300], "label": "Scored", "spotlight": 0.6}],
                   base={"kind": "color", "color": "#ffffff"})
    img = motion.frame(scene, 1.5).convert("L")
    assert img.getpixel((300, 160)) > 220  # inside the box stays bright
    assert img.getpixel((40, 340)) < 140  # outside is dimmed


def test_callout_box_in_recorded_pixels_lands_where_the_recording_sits() -> None:
    layer = {"kind": "callout", "box": [0, 0, 480, 270], "spotlight": 0.6,
             "map": {"size": [960, 540], "box": [960, 540, 960, 540]}}  # recording fills the lower-right quarter
    img = motion.frame(_scene([layer], base={"kind": "color", "color": "#ffffff"}), 1.5).convert("L")
    assert img.getpixel((400, 225)) > 220  # the mapped box, 320-480 x 180-270 at this size, stays bright
    assert img.getpixel((60, 40)) < 140  # the same numbers read as design pixels would be here; dimmed


def test_fonts_come_from_a_data_table() -> None:
    table = json.loads(motion.FONTS_FILE.read_text(encoding="utf-8"))
    assert {"ui", "ui_bold", "display", "mono"} <= set(table["roles"])
    f = motion.font("mono", 20)
    assert f.getlength("abc") > 0


@needs_ffmpeg
def test_render_writes_a_transparent_overlay_and_an_opaque_film(tmp_path: Path) -> None:
    overlay = motion.render(_scene([{"kind": "title", "text": "Hi"}], seconds=1.0), tmp_path / "o.mov")
    film = motion.render(_scene([{"kind": "title", "text": "Hi"}], seconds=1.0, base={"kind": "living"}),
                         tmp_path / "f.mp4")
    for path, fmt in ((overlay, "rgba"), (film, "yuv420p")):
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=pix_fmt,width,height:format=duration", "-of", "json", str(path)],
                               capture_output=True, text=True, check=True)
        info = json.loads(probe.stdout)
        assert info["streams"][0]["pix_fmt"] == fmt
        assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (640, 360)
        assert float(info["format"]["duration"]) == pytest.approx(1.0, abs=0.07)


@needs_ffmpeg
def test_video_base_plays_under_the_layers(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=2",
                    "-pix_fmt", "yuv420p", str(clip)], check=True)
    scene = _scene([{"kind": "title", "text": "Over a clip", "at": 0.0}], seconds=2.0,
                   base={"kind": "video", "file": str(clip)})
    a, b = motion.frame(scene, 0.2).convert("L"), motion.frame(scene, 1.2).convert("L")
    from PIL import ImageChops

    assert ImageChops.difference(a, b).getbbox() is not None  # the clip really plays
    assert min(a.getextrema()) < 200 and a.getpixel((5, 5)) > 0


def test_an_outside_renderer_is_one_line_of_data(tmp_path: Path) -> None:
    script = tmp_path / "fake_renderer.py"
    script.write_text(
        "import json, sys\n"
        "scene = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "open(sys.argv[2], 'w').write('rendered %d layers' % len(scene['layers']))\n",
        encoding="utf-8",
    )
    table = tmp_path / "renderers.json"
    table.write_text(json.dumps({"renderers": [
        {"id": "fake", "name": "Fake", "command": [sys.executable, str(script), "{scene}", "{out}"]}]}),
        encoding="utf-8")
    out = motion.render(_scene([{"kind": "title", "text": "x"}]), tmp_path / "out.mp4", renderer="fake",
                        table=table)
    assert out.read_text() == "rendered 1 layers"
    with pytest.raises(motion.MotionError, match="renderer"):
        motion.render(_scene([]), tmp_path / "x.mp4", renderer="nope", table=table)
