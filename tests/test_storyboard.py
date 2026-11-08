"""Beats: the voice sets the clock, joins never cross a line, real footage stays under a third, and the commands
that join, voice and mix a film line up frame for frame."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import wave
from array import array
from pathlib import Path

import pytest

from proofhouse import motion, sound, storyboard
from proofhouse.storyboard import StoryboardError

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="FFmpeg not installed")
FPS = storyboard.FPS


def _tone(path: Path, seconds: float, freq: float = 440.0) -> Path:
    n = round(seconds * 24000)
    pcm = array("h", (round(9000 * math.sin(2 * math.pi * freq * i / 24000)) for i in range(n)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm.tobytes())
    return path


def _wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def _speaker(folder: Path):  # noqa: ANN202
    """A stand-in voice: 0.3 s of tone per word, written where a real voice would write its file."""
    def speak(text: str, name: str) -> Path:
        return _tone(folder / f"{name}.wav", 0.3 * len(text.split()))
    return speak


def _planned(rows: list[dict], folder: Path) -> tuple[list[storyboard.Beat], float]:
    beats = storyboard.parse(rows, folder)
    storyboard.voice(beats, _speaker(folder), _wav_seconds)
    total = storyboard.time_beats(beats)
    return beats, total


def _capture(folder: Path, name: str = "shot.png", size: tuple[int, int] = (1600, 1000)) -> str:
    from PIL import Image

    Image.new("RGB", size, (240, 240, 240)).save(folder / name)
    return name


def _recording(folder: Path) -> str:
    (folder / "rec.mp4").write_bytes(b"not decoded in these tests")
    (folder / "rec.json").write_text(json.dumps({
        "size": [1280, 800], "scale": 1, "seconds": 6.0, "keys": [{"t": 2.0}, {"t": 9.0}],
        "clicks": [{"t": 0.3, "x": 100, "y": 100}, {"t": 1.1, "x": 640, "y": 400}],
        "moves": [{"t": 0.2, "x": 100, "y": 100}, {"t": 1.0, "x": 640, "y": 400}, {"t": 3.0, "x": 900, "y": 500}],
        "scrolls": []}), encoding="utf-8")
    return "rec.mp4"


# --- reading -----------------------------------------------------------------------------------------

def test_narration_splits_into_phrases_after_each_stop() -> None:
    assert storyboard.split_phrases("  Say it. Pick a model!  Ready?  Go… now ") == [
        "Say it.", "Pick a model!", "Ready?", "Go…", "now"]
    assert storyboard.split_phrases("   ") == []


def test_a_beat_reads_say_or_phrases_and_defaults_to_a_living_background(tmp_path: Path) -> None:
    _tone(tmp_path / "line.wav", 1.0)
    beats = storyboard.parse({"beats": [{"say": "One. Two."},
                                        {"phrases": ["Three.", {"text": "Four.", "file": "line.wav"}]}]}, tmp_path)
    assert [p.text for p in beats[0].phrases] == ["One.", "Two."]
    assert beats[0].base == {"kind": "living"} and beats[0].cut == "auto" and beats[0].real is False
    assert beats[1].phrases[1].file == (tmp_path / "line.wav").resolve()
    with pytest.raises(StoryboardError, match="beat 1: give say or phrases, not both"):
        storyboard.parse([{"say": "a", "phrases": ["b"]}], tmp_path)


@pytest.mark.parametrize("row, message", [
    ({"base": {"kind": "slideshow"}}, "base kind must be one of"),
    ({"base": {"kind": "capture"}}, "a capture base needs a file"),
    ({"cut": "spin"}, "cut must be one of"),
    ({"energy": "max"}, "energy must be low, mid or high"),
    ({"hold": 0}, "hold must be a number of seconds above 0"),
    ({"sounds": [{"at": 1, "kind": "boom"}]}, "sounds must be a list"),
    ({"say": "One.", "sounds": [{"at": "phrase 2", "kind": "pop"}]}, "there is no phrase 2"),
    ({"layers": [{"kind": "label", "text": "x", "at": "soon"}]}, "a time is a number of seconds"),
])
def test_a_bad_beat_is_refused_with_its_number(tmp_path: Path, row: dict, message: str) -> None:
    with pytest.raises(StoryboardError, match=f"beat 2: .*{message}"):
        storyboard.parse([{"say": "Fine."}, row], tmp_path)


@pytest.mark.parametrize("name", ["../outside.png", "/etc/passwd", "C:/Windows/win.ini", "sub/../../x.png",
                                  ".hidden/x.png", "missing.png"])
def test_files_must_stay_inside_the_storyboard_folder(tmp_path: Path, name: str) -> None:
    folder = tmp_path / "board"
    folder.mkdir()
    _capture(tmp_path, "outside.png")
    with pytest.raises(StoryboardError, match="beat 1"):
        storyboard.parse([{"base": {"kind": "capture", "file": name}}], folder)


def test_a_file_reached_through_a_link_is_refused(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    folder = tmp_path / "board"
    folder.mkdir()
    (tmp_path / "elsewhere").mkdir()
    _capture(tmp_path / "elsewhere", "shot.png")
    try:
        os.symlink(tmp_path / "elsewhere", folder / "linked", target_is_directory=True)
    except OSError:
        pytest.skip("this machine does not allow links")
    with pytest.raises(StoryboardError, match="passes through a link"):
        storyboard.parse([{"base": {"kind": "capture", "file": "linked/shot.png"}}], folder)


def test_a_recording_reads_its_notes_and_lasts_as_long_as_it_plays(tmp_path: Path) -> None:
    beat, = storyboard.parse([{"base": {"kind": "recording", "file": _recording(tmp_path), "speed": 2.0}}], tmp_path)
    assert beat.real is True
    assert beat.meta["size"] == [1280, 800]
    assert beat.hold == pytest.approx(3.0)  # six seconds of screen played at twice the speed
    (tmp_path / "rec.json").write_text(json.dumps({"size": [1280], "moves": []}), encoding="utf-8")
    with pytest.raises(StoryboardError, match="need a size"):
        storyboard.parse([{"base": {"kind": "recording", "file": "rec.mp4"}}], tmp_path)


# --- the clock ---------------------------------------------------------------------------------------

def test_the_voice_sets_each_beats_length(tmp_path: Path) -> None:
    beats, total = _planned([{"say": "One two three. Four five."}, {"say": "Six.", "cut": "cut"}], tmp_path)
    first, second = beats
    assert [p.seconds for p in first.phrases] == pytest.approx([0.9, 0.6])
    talk = storyboard.LEAD + 0.9 + storyboard.GAP + 0.6 + storyboard.BREATH
    assert first.own_f == math.ceil(talk * FPS - 1e-6)
    assert first.phrases[0].start == pytest.approx(storyboard.LEAD)
    assert first.phrases[1].start == pytest.approx(storyboard.LEAD + 0.9 + storyboard.GAP)
    # a one-word beat is held for the floor, not rushed
    assert second.own_f == math.ceil(storyboard.MIN_BEAT * FPS)
    assert second.start_f == first.own_f
    assert total == pytest.approx((first.own_f + second.own_f) / FPS)


def test_a_phrase_with_no_sound_is_refused(tmp_path: Path) -> None:
    beats = storyboard.parse([{"say": "Hello."}], tmp_path)
    with pytest.raises(StoryboardError, match="beat 1: phrase 1: .* has no sound"):
        storyboard.voice(beats, _speaker(tmp_path), lambda path: 0.0)


def test_joins_follow_the_story_and_never_repeat_back_to_back(tmp_path: Path) -> None:
    shot = _capture(tmp_path)
    rows = [{"say": "Open."}, {"say": "Fast.", "energy": "high"}, {"say": "Faster.", "energy": "high"},
            {"say": "Steady."}, {"say": "Steady again."}, {"base": {"kind": "capture", "file": shot}},
            {"say": "Back out."}, {"say": "Calm.", "energy": "low"}, {"say": "Mine.", "cut": "flash"},
            {"say": "The end."}]
    beats, _ = _planned(rows, tmp_path)
    assert [b.cut for b in beats] == ["cut", "whip", "cut", "zoom", "dissolve", "wipe", "zoom", "dissolve",
                                      "flash", "dissolve"]


def test_no_spoken_line_crosses_a_join(tmp_path: Path) -> None:
    shot = _capture(tmp_path)
    rows = [{"say": "A long opening line with many words in it."}, {"say": "Quick.", "energy": "high"},
            {"base": {"kind": "capture", "file": shot}, "say": "Here is the real thing."},
            {"say": "And we are back. With two lines."}, {"say": "Goodbye.", "energy": "low"}]
    beats, total = _planned(rows, tmp_path)
    for before, beat in zip(beats, beats[1:]):
        handover = before.start + before.own  # where the wipe's cover or the next blend begins
        assert all(p.start + p.seconds <= handover - storyboard.BREATH + 1e-6 for p in before.phrases)
        settled = beat.start + beat.into  # the join into this beat is over
        assert all(p.start >= settled + storyboard.LEAD - 1e-6 for p in beat.phrases)
        assert beat.start_f == before.start_f + before.own_f + before.cover_f
    wipe = beats[2]
    assert wipe.cut == "wipe" and beats[1].cover_f + wipe.into_f == round(0.7 * FPS)
    assert beats[3].cut == "zoom" and beats[3].overlap_f == beats[3].into_f == round(0.45 * FPS)
    assert beats[2].frames == beats[2].own_f + beats[3].overlap_f
    assert total == pytest.approx(sum(b.own_f + b.cover_f for b in beats) / FPS)


def test_real_footage_over_a_third_is_refused(tmp_path: Path) -> None:
    shot = _capture(tmp_path)
    beats, total = _planned([{"say": "Short."}, {"base": {"kind": "capture", "file": shot}, "hold": 6}], tmp_path)
    with pytest.raises(StoryboardError, match=r"real product footage fills \d+% .* keep it to a third or less"):
        storyboard.check_mix(beats, total)
    beats, total = _planned([{"say": "A longer generated opening. With a second line to carry it."},
                             {"say": "And more generated pictures. And motion graphics."},
                             {"base": {"kind": "capture", "file": shot}, "hold": 2}], tmp_path)
    assert 0 < storyboard.check_mix(beats, total) <= 1 / 3


def test_times_can_hang_off_the_words(tmp_path: Path) -> None:
    beats, _ = _planned([{"say": "Hello."}, {"say": "One two. Three four five.", "cut": "dissolve"}], tmp_path)
    beat = beats[1]
    first, second = beat.phrases
    assert storyboard.when(beat, 0) == pytest.approx(beat.into, abs=1e-3)
    assert storyboard.when(beat, 1.0) == pytest.approx(beat.into + 1.0, abs=1e-3)
    assert storyboard.when(beat, "start") == 0
    assert storyboard.when(beat, "end") == pytest.approx(beat.own, abs=1e-3)
    assert storyboard.when(beat, "phrase 2") == pytest.approx(second.start - beat.start, abs=1e-3)
    assert storyboard.when(beat, "phrase 1 end + 0.1") == pytest.approx(
        first.start + first.seconds + 0.1 - beat.start, abs=1e-3)
    assert storyboard.when(beat, "start - 5") == 0
    assert storyboard.when(beat, 99) == pytest.approx(beat.seconds, abs=1e-3)


def test_a_time_written_as_text_seconds_means_seconds(tmp_path: Path) -> None:
    """Small models write "at": "2" or "2s"; that is two seconds, not an error."""
    beats, _ = _planned([{"say": "Hello there.", "layers": [{"kind": "label", "text": "Hi", "at": "0", "until": "0.5s"}]}],
                        tmp_path)
    beat = beats[0]
    assert storyboard.when(beat, "0.5") == pytest.approx(beat.into + 0.5, abs=1e-3)
    assert storyboard.when(beat, "0.25 s") == storyboard.when(beat, 0.25)


# --- scenes, sounds, captions ------------------------------------------------------------------------

def test_a_capture_sits_centred_in_a_window_over_a_generated_background(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    shot = _capture(tmp_path)
    beats, _ = _planned([{"say": "Intro."}, {"base": {"kind": "capture", "file": shot}, "say": "Look."}], tmp_path)
    box, inner, frame = storyboard.picture_box(beats[1], (1920, 1080))
    assert frame == "window"
    assert inner[2] / inner[3] == pytest.approx(1.6, rel=1e-3)
    assert box[0] + box[2] / 2 == pytest.approx(960)
    assert box[1] >= 0 and box[1] + box[3] <= 1080 and box[3] <= 0.82 * 1080 + 0.01
    scenes = storyboard.scenes(beats, (640, 360))
    assert scenes[1]["base"]["kind"] == "living"
    footage = scenes[1]["layers"][0]
    assert footage["kind"] == "image" and footage["at"] == pytest.approx(beats[1].into)
    # the wipe: the beat before is covered to its last frame, this one is revealed without a second whoosh
    cover = scenes[0]["layers"][-1]
    assert cover["kind"] == "wipe" and cover["mode"] == "cover"
    assert cover["at"] + cover["duration"] == pytest.approx(scenes[0]["seconds"] - 1 / FPS, abs=1e-3)
    reveal = scenes[1]["layers"][-1]
    assert reveal["mode"] == "reveal" and reveal["quiet"] is True


def test_the_recorded_pointer_is_redrawn_where_it_was_on_the_screen(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    beats, _ = _planned([{"base": {"kind": "recording", "file": _recording(tmp_path)}, "say": "Watch."}], tmp_path)
    beat = beats[0]
    _, inner, _ = storyboard.picture_box(beat, (1920, 1080))
    layers = storyboard.scenes(beats, (640, 360))[0]["layers"]
    video, cursor = layers[0], layers[1]
    assert video["kind"] == "video" and video["speed"] == 1.0
    assert cursor["map"] == {"size": [1280, 800], "box": inner}
    assert cursor["at"] == pytest.approx(beat.into + 0.5)  # it appears once the window has risen in
    assert [(m["t"], m["x"]) for m in cursor["moves"]] == [(0.0, 100), (0.5, 640), (2.5, 900)]
    assert [(c["t"], c["x"]) for c in cursor["clicks"]] == [(0.6, 640)]


def _layer(scene: dict, kind: str) -> dict:
    return next(layer for layer in scene["layers"] if layer["kind"] == kind)


def test_a_callout_on_footage_is_placed_on_the_picture_by_itself(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    shot = _capture(tmp_path)
    callout = {"kind": "callout", "box": [100, 100, 300, 80], "label": "here"}
    rows = [{"base": {"kind": "capture", "file": shot}, "say": "Look.", "layers": [callout]},
            {"base": {"kind": "capture", "file": shot}, "say": "Again.", "layers": [dict(callout, map="frame")]},
            {"base": {"kind": "recording", "file": _recording(tmp_path)}, "say": "Watch.", "layers": [callout]}]
    beats, _ = _planned(rows, tmp_path)
    scenes = storyboard.scenes(beats, (640, 360))
    # the box is in the screenshot's own pixels; the storyboard knows where the screenshot sits
    _, inner, _ = storyboard.picture_box(beats[0], (640, 360))
    assert _layer(scenes[0], "callout")["map"] == {"size": [1600, 1000], "box": inner}
    assert "map" not in _layer(scenes[1], "callout")  # "frame": the box stays in design pixels
    _, inner, _ = storyboard.picture_box(beats[2], (640, 360))
    assert _layer(scenes[2], "callout")["map"] == {"size": [1280, 800], "box": inner}  # the recording's size


def test_a_callout_stays_in_design_pixels_when_the_footage_does_not_hold_still(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    shot = _capture(tmp_path)
    callout = {"kind": "callout", "box": [100, 100, 300, 80]}
    beats, _ = _planned([{"base": {"kind": "capture", "file": shot, "fit": "fill"}, "say": "Look.", "layers": [callout]}],
                        tmp_path)
    assert "map" not in _layer(storyboard.scenes(beats, (640, 360))[0], "callout")
    for rows in ([{"base": {"kind": "capture", "file": shot, "fit": "fill"}, "say": "x", "layers": [dict(callout, map="footage")]}],
                 [{"say": "No footage.", "layers": [dict(callout, map="footage")]}]):
        beats, _ = _planned(rows, tmp_path)
        with pytest.raises(StoryboardError, match="footage"):
            storyboard.scenes(beats, (640, 360))


FILM9_BEATS = [  # layers written without a place, as the local model wrote them for film9
    [{"kind": "title", "text": "Say what you want", "at": "start"}, {"kind": "label", "text": "Pick any model", "at": "start"},
     {"kind": "chips", "items": ["cloud", "local", "open", "commercial"]}],
    [{"kind": "panel", "title": "Version History", "rows": ["Version 1", "Version 2", "Version 3"]},
     {"kind": "counter", "to": 3, "label": "versions"}, {"kind": "label", "text": "Every result saved"},
     {"kind": "chips", "items": ["image", "video", "voice", "music"]}],
    [{"kind": "lower_third", "title": "Spending Limit", "subtitle": "You set it"}, {"kind": "counter", "to": 5, "label": "calls"},
     {"kind": "chips", "items": ["cloud", "local", "open", "commercial"]}],
    [{"kind": "panel", "title": "Components", "rows": ["Prompt", "Agent", "Skill", "Rule", "MCP", "Hook"]},
     {"kind": "chips", "items": ["prompt", "agent", "skill", "rule", "server", "hook"]}, {"kind": "label", "text": "All built"}],
    [{"kind": "title", "text": "Compare", "at": "start"}, {"kind": "panel", "title": "History", "rows": ["Version 1", "Version 2"]},
     {"kind": "counter", "to": 3, "label": "versions"}],
]


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920), (1080, 1080)])
def test_layers_written_without_a_place_never_land_on_each_other(tmp_path: Path, size: tuple[int, int]) -> None:
    pytest.importorskip("PIL")
    beats, _ = _planned([{"say": "Say what you want. Pick any model.", "layers": layers} for layers in FILM9_BEATS], tmp_path)
    for k, sc in enumerate(storyboard.scenes(beats, size), start=1):
        assert motion.collisions(sc) == [], f"beat {k}: {[(sc['layers'][i]['kind'], sc['layers'][j]['kind']) for i, j in motion.collisions(sc)]}"
        for layer in sc["layers"]:
            box = motion.extent(layer, 1920 * size[1] / size[0])
            if box:
                assert 0 <= box[0] and box[2] <= 1920 and 0 <= box[1] and box[3] <= 1920 * size[1] / size[0]


def test_layers_that_say_where_they_go_stay_where_they_are(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    layers = [{"kind": "title", "text": "Hello", "y": 300}, {"kind": "chips", "items": ["a", "b"], "y": 700},
              {"kind": "panel", "rows": ["x"], "box": [100, 100, 300, 300]}]
    beats, _ = _planned([{"say": "Hello there.", "layers": layers}], tmp_path)
    sc = storyboard.scenes(beats, (1920, 1080))[0]
    assert [{k: v for k, v in layer.items() if k != "at"} for layer in sc["layers"]] == layers


def test_a_chip_row_shown_in_an_earlier_beat_is_not_shown_again(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    rows = [{"say": "One thing.", "layers": [{"kind": "chips", "items": ["Cloud", "local"]}]},
            {"say": "Two things.", "layers": [{"kind": "title", "text": "Two"}, {"kind": "chips", "items": ["cloud", " Local "]}]},
            {"say": "Three things.", "layers": [{"kind": "chips", "items": ["cloud", "open"]}]}]
    beats, _ = _planned(rows, tmp_path)
    first, second, third = storyboard.scenes(beats, (1920, 1080))
    written = lambda sc: [layer["items"] for layer in sc["layers"] if layer["kind"] == "chips" and not layer.get("quiet")]  # noqa: E731
    assert written(first) == [["Cloud", "local"]] and written(second) == [] and written(third) == [["cloud", "open"]]
    assert [layer["text"] for layer in second["layers"] if layer["kind"] == "title"] == ["Two"]
    assert beats[1].layers[1]["items"] == ["cloud", " Local "]  # the written film is not changed


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920)])
def test_words_written_without_a_place_stay_clear_of_the_captions(tmp_path: Path, size: tuple[int, int]) -> None:
    pytest.importorskip("PIL")
    layers = [{"kind": "lower_third", "title": "Spending Limit", "subtitle": "You set it"}, {"kind": "chips", "items": ["a", "b"]},
              {"kind": "panel", "rows": ["x"]}]
    beats, _ = _planned([{"say": "Every paid call goes through your limit.", "layers": layers}], tmp_path)
    sc = storyboard.scenes(beats, size)[0]
    dh = 1920 * size[1] / size[0]
    for layer in sc["layers"]:
        box = motion.extent(layer, dh)
        if box and layer["kind"] != "panel":  # a panel written at its default size may reach down; it is never moved there
            assert box[3] <= dh * (1 - motion.CAPTION_BAND) + 1, layer["kind"]
    assert motion.collisions(sc) == []
    plate = next(layer for layer in sc["layers"] if layer["kind"] == "lower_third")
    assert plate["y"] == pytest.approx(dh * motion.CAPTION_TOP, abs=0.01)


def test_a_layer_that_is_alone_keeps_its_default_place(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    beats, _ = _planned([{"say": "Hello there.", "layers": [{"kind": "title", "text": "Hello"}]}], tmp_path)
    layer = storyboard.scenes(beats, (1920, 1080))[0]["layers"][0]
    assert "x" not in layer and "y" not in layer


def test_words_that_cannot_share_the_screen_are_refused_with_the_beat_number(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    layers = [{"kind": "panel", "rows": ["x"], "box": [0, 0, 1920, 1080]}, {"kind": "panel", "rows": ["y"]}]
    beats, _ = _planned([{"say": "Hello there.", "layers": layers}], tmp_path)
    with pytest.raises(StoryboardError, match="beat 1: .*no clear place"):
        storyboard.scenes(beats, (1920, 1080))


def test_a_vertical_film_spreads_the_layout_down_the_frame_and_enlarges_the_words(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    layers = [{"kind": "title", "text": "Hello", "y": 380},
              {"kind": "label", "text": "step one"},
              {"kind": "cards", "items": ["a", "b", "c", "d"]},
              {"kind": "panel", "rows": ["x", "y"], "box": [560, 190, 800, 700]},
              {"kind": "counter", "to": 9, "size": 120},
              {"kind": "link", "from": [400, 300], "to": [1500, 800]}]
    # one layer to a beat: this test is about scaling, and words that share a beat may not share a spot
    beats, _ = _planned([{"say": "Intro.", "layers": [layer]} for layer in layers], tmp_path)
    wide = {"layers": [lay for scene in storyboard.scenes(beats, (1920, 1080)) for lay in scene["layers"]]}
    assert [{k: v for k, v in layer.items() if k not in ("at",)} for layer in wide["layers"]] == layers  # unchanged
    tall = {"layers": [lay for scene in storyboard.scenes(beats, (1080, 1920)) for lay in scene["layers"]]}
    f = (1920 * 1920 / 1080) / 1080
    title, label, cards, panel, counter, link = (_layer(tall, k) for k in ("title", "label", "cards", "panel", "counter", "link"))
    assert title["y"] == pytest.approx(380 * f) and title["size"] == pytest.approx(144)
    assert label["y"] == pytest.approx(160 * f) and label["size"] == pytest.approx(33)
    assert counter["size"] == pytest.approx(180)
    assert cards["columns"] == 2
    x, y, w, h = cards["box"]
    assert x + w / 2 == pytest.approx(960) and y + h / 2 == pytest.approx(540 * f) and w <= 1840
    assert h > 420  # two rows of cards get the room of two rows
    x, y, w, h = panel["box"]
    assert (x + w / 2, y + h / 2, w, h) == pytest.approx((960, 540 * f, 1200, 1050))
    assert link["from"] == pytest.approx([400, 300 * f]) and link["to"] == pytest.approx([1500, 800 * f])


def test_a_vertical_film_enlarges_the_words_drawn_inside_plates_boxes_and_labels(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    timeline = {"command": "proofhouse make", "keys": [0.2, 0.3], "enter": 0.6, "seconds": 2.0}
    layers = [{"kind": "lower_third", "title": "Ada"},
              {"kind": "callout", "box": [600, 300, 300, 100], "label": "here"},
              {"kind": "cards", "items": ["a", "b"]},
              {"kind": "panel", "rows": ["x"], "box": [160, 190, 1600, 700]},
              {"kind": "terminal", "timeline": timeline}]
    beats, _ = _planned([{"say": "Intro.", "layers": [layer]} for layer in layers], tmp_path)  # one to a beat: no shared spot
    wide = {"layers": [lay for scene in storyboard.scenes(beats, (1920, 1080)) for lay in scene["layers"]]}
    assert not any("text_scale" in layer for layer in wide["layers"])
    tall_scenes = storyboard.scenes(beats, (1080, 1920))
    tall = {"layers": [lay for scene in tall_scenes for lay in scene["layers"]]}
    scale = {k: _layer(tall, k)["text_scale"] for k in ("lower_third", "callout", "cards", "panel", "terminal")}
    assert scale["lower_third"] == scale["callout"] == scale["cards"] == pytest.approx(1.5)
    assert scale["panel"] == pytest.approx(1840 / 1600, abs=1e-4)  # a wide box can only grow so far, and its words with it
    assert scale["terminal"] == pytest.approx(1840 / 1500, abs=1e-4)
    assert _layer(tall, "panel")["box"][2] == pytest.approx(1840)
    for scene in tall_scenes:
        motion.check_scene(scene)


def test_vertical_footage_fills_more_of_the_width(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    beats, _ = _planned([{"base": {"kind": "capture", "file": _capture(tmp_path)}, "say": "Look."}], tmp_path)
    box, _, _ = storyboard.picture_box(beats[0], (1080, 1920))
    assert box[2] == pytest.approx(0.94 * 1920) and box[0] + box[2] / 2 == pytest.approx(960)
    assert storyboard.picture_box(beats[0], (1920, 1080))[0][2] <= 0.86 * 1920 + 0.01


def test_sounds_come_from_the_motion_the_beats_the_keys_and_the_joins(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    rows = [{"say": "Hi.", "layers": [{"kind": "title", "text": "Hello", "at": 0.2}]},
            {"say": "Fast.", "energy": "high", "sounds": [{"at": "phrase 1", "kind": "riser"}]},
            {"base": {"kind": "recording", "file": _recording(tmp_path)}}]
    beats, total = _planned(rows, tmp_path)
    events = storyboard.sound_events(beats, storyboard.scenes(beats, (640, 360)))
    assert (round(0.2, 3), "hit") in events
    assert (round(beats[1].start - 0.1, 3), "whoosh") in events  # under the whip
    assert (round(beats[1].phrases[0].start, 3), "riser") in events
    key = beats[2].start + beats[2].into + 2.0
    assert (round(key, 3), "tick") in events  # the key typed 9 s in is after the clip and is left out
    assert len([e for e in events if e[1] == "tick"]) == 1
    assert events == sorted(events) and all(0 <= t < total for t, _ in events)


def test_captions_follow_each_spoken_phrase(tmp_path: Path) -> None:
    beats, _ = _planned([{"say": "One two. Three."}], tmp_path)
    first, second = beats[0].phrases
    text = storyboard.captions(beats)
    assert text.startswith("1\n00:00:00,250 --> 00:00:00,850\nOne two.\n\n2\n")
    assert text.endswith("Three.\n")
    assert f"00:00:{second.start:06.3f}".replace(".", ",") in text


def test_music_dips_under_the_voice_and_comes_back_up() -> None:
    expr =storyboard.duck([(1.0, 2.0)], 0.75, ramp=0.25)

    def level(t: float) -> float:
        return eval(expr, {"__builtins__": {}}, {"t": t, "min": min, "max": max})  # noqa: S307 - our own numbers

    assert level(0.0) == 1 and level(3.0) == 1
    assert level(1.5) == pytest.approx(0.25)
    assert level(0.875) == pytest.approx(0.625)  # halfway down the slide in
    assert storyboard.duck([], 0.75) == "1"


def test_lines_close_together_share_one_dip(tmp_path: Path) -> None:
    beats, _ = _planned([{"say": "One. Two."}, {"say": "Three.", "cut": "cut"}], tmp_path)
    spans = storyboard.speech_spans(beats)
    a, b = beats[0].phrases
    assert spans[0] == (a.start, pytest.approx(b.start + b.seconds))  # 0.18 s apart: one dip
    assert len(spans) == 2


# --- the commands, run for real -----------------------------------------------------------------------

def _color_clip(path: Path, frames: int, color: str) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=64x36:r={FPS}",
                    "-frames:v", str(frames), "-pix_fmt", "yuv420p", str(path)], check=True, timeout=60)
    return path


def _probe(path: Path, *entries: str) -> list[str]:
    done = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries", ",".join(entries),
                           "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=60)
    return done.stdout.split()


@needs_ffmpeg
def test_joined_picture_is_exactly_as_long_as_the_planned_film(tmp_path: Path) -> None:
    shot = _capture(tmp_path)
    rows = [{"say": "One."}, {"say": "Two.", "energy": "high"}, {"base": {"kind": "capture", "file": shot}},
            {"say": "Four."}, {"say": "Five.", "cut": "flash"}, {"say": "Six.", "energy": "low"}]
    beats, total = _planned(rows, tmp_path)
    assert [b.cut for b in beats] == ["cut", "whip", "wipe", "zoom", "flash", "dissolve"]
    colors = ["red", "green", "blue", "white", "black", "yellow"]
    clips = [_color_clip(tmp_path / f"beat{b.number:02d}.mp4", b.frames, c) for b, c in zip(beats, colors)]
    out = tmp_path / "picture.mp4"
    subprocess.run(storyboard.join_command(clips, beats, out), check=True, timeout=120)
    frames, = _probe(out, "stream=nb_read_frames")
    assert int(frames) == round(total * FPS)


@needs_ffmpeg
def test_voice_and_mix_make_one_finished_film_at_the_planned_length(tmp_path: Path) -> None:
    from proofhouse import studio

    beats, total = _planned([{"say": "Hello there. This is a test."}, {"say": "Goodbye.", "cut": "dissolve"}],
                            tmp_path)
    voice = tmp_path / "voice.wav"
    subprocess.run(storyboard.voice_command(beats, total, voice), check=True, timeout=60)
    assert _wav_seconds(voice) == pytest.approx(total, abs=0.01)
    clips = [_color_clip(tmp_path / f"beat{b.number}.mp4", b.frames, "gray") for b in beats]
    picture = tmp_path / "picture.mp4"
    subprocess.run(storyboard.join_command(clips, beats, picture), check=True, timeout=60)
    music = _tone(tmp_path / "music.wav", 1.3, 220.0)  # shorter than the film: it loops
    fx = sound.mix([(0.1, "whoosh"), (1.0, "pop")], total, tmp_path / "fx.wav")
    out = tmp_path / "film.mp4"
    cmd = storyboard.mix_command(picture, voice, music, fx, total, storyboard.speech_spans(beats), out,
                                 loudness=studio.LOUDNESS)
    subprocess.run(cmd, check=True, timeout=120)
    duration, = _probe(out, "format=duration")
    assert float(duration) == pytest.approx(total, abs=0.08)
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                            str(out)], capture_output=True, text=True, timeout=60).stdout.split()
    assert sorted(kinds) == ["audio", "video"]


def test_a_storyboard_with_no_words_needs_no_voice_track(tmp_path: Path) -> None:
    beats, total = _planned([{"hold": 2}], tmp_path)
    assert storyboard.voice_command(beats, total, tmp_path / "v.wav") is None
    assert storyboard.speech_spans(beats) == []


def test_a_film_shorter_than_asked_is_filled_out_to_the_asked_length(tmp_path: Path) -> None:
    rows = [{"say": "Say what you want.", "base": {"kind": "living"}}, {"say": "Pick any model.", "base": {"kind": "living"}}]
    beats, total = _planned(rows, tmp_path)
    spans = [b.span for b in beats]
    starts = [p.start for b in beats for p in b.phrases]
    filled = storyboard.fill_to(beats, total + 4)
    assert filled == pytest.approx(total + 4, abs=1 / storyboard.FPS)
    assert all(after > before + 1.9 for after, before in zip((b.span for b in beats), spans))
    assert [p.start for b in beats for p in b.phrases][0] == starts[0]  # the first word does not move
    assert storyboard.fill_to(beats, 1.0) == pytest.approx(filled)  # never cut short to fit



def test_real_footage_runs_its_own_length_and_the_other_beats_take_the_extra_time(tmp_path: Path) -> None:
    rows = [{"say": "Say what you want.", "base": {"kind": "living"}},
            {"say": "Watch it run.", "base": {"kind": "living"}, "real": True, "hold": 2.0},
            {"say": "Pick any model.", "base": {"kind": "living"}}]
    beats, total = _planned(rows, tmp_path)
    real_span = beats[1].span
    assert storyboard.fill_to(beats, total + 4) == pytest.approx(total + 4, abs=1 / storyboard.FPS)
    assert beats[1].span == pytest.approx(real_span, abs=1 / storyboard.FPS)
    only_real = storyboard.parse([rows[1]], tmp_path)
    storyboard.voice(only_real, _speaker(tmp_path), _wav_seconds)
    alone = storyboard.time_beats(only_real)
    assert storyboard.fill_to(only_real, alone + 2) == pytest.approx(alone + 2, abs=1 / storyboard.FPS)  # nothing else to grow

# --- every second lively ---------------------------------------------------------------------------------

def _quiet(beat: storyboard.Beat, sc: dict) -> list[tuple[float, float]]:
    spans = [s for layer in sc["layers"] for s in storyboard._moving(layer, beat.seconds)]
    if beat.into:
        spans.append((0.0, beat.into))
    return storyboard.quiet_stretches(spans, 0.0, beat.own)


def test_key_words_drop_the_small_joining_words() -> None:
    assert storyboard.key_words("Say what you want, and pick any model!") == ["Say", "want", "pick", "any", "model"]
    assert storyboard.key_words("it is what it is") == ["it", "is", "what", "it", "is"]  # all small: keep them
    assert storyboard.key_words("one two three four five six seven", most=3) == ["two", "three", "four"]


def test_a_still_beat_with_long_lines_never_holds_still(tmp_path: Path) -> None:
    shot = _capture(tmp_path)
    rows = [{"base": {"kind": "capture", "file": shot},
             "say": "Proofhouse makes prompts agents skills rules servers hooks images video voice music sites apps."},
            {"base": {"kind": "living"}, "say": "Pick any model from any provider and watch it run."}]
    beats, total = _planned(rows, tmp_path)
    storyboard.fill_to(beats, total + 6)  # stretch the beats so long stretches would stand still
    for beat, sc in zip(beats, storyboard.scenes(beats, (1920, 1080))):
        assert _quiet(beat, sc) == [], f"beat {beat.number} holds still"
        titles = [layer for layer in sc["layers"] if layer["kind"] == "title"]
        assert titles and titles[0]["text"].split()[0] in ("Proofhouse", "Pick")  # its own words, not filler
        assert all(layer.get("quiet") for layer in sc["layers"] if layer["kind"] == "chips")  # fillers make no sound


def test_a_beat_that_says_nothing_borrows_the_nearest_line(tmp_path: Path) -> None:
    beats, total = _planned([{"say": "Ship launches from one goal.", "base": {"kind": "living"}},
                             {"base": {"kind": "living"}}], tmp_path)
    storyboard.fill_to(beats, total + 4)
    sc = storyboard.scenes(beats, (1920, 1080))[1]
    shown = {w for layer in sc["layers"] if layer["kind"] == "chips" for w in layer["items"]}
    assert shown and shown <= {"Ship", "launches", "goal"}
    assert _quiet(beats[1], sc) == []


def test_moving_pictures_get_nothing_added(tmp_path: Path) -> None:
    beats, _ = _planned([{"say": "Watch this for a long while now.", "base": {"kind": "living"}}], tmp_path)
    beat = beats[0]
    beat.base = {"kind": "video", "file": "clip.mp4"}
    assert storyboard.liven(beat, []) == []


def _laid_out() -> list[dict]:
    return [{"base": {"kind": "living"}, "say": "It asks what it needs. Then it says back what it understood.",
             "layers": [{"kind": "title", "text": "It asks first.", "at": "phrase 1"}]},
            {"base": {"kind": "living"}, "say": "Pick any model from any provider and watch it run."}]


def _added(sc: dict) -> list[dict]:
    return [layer for layer in sc["layers"] if layer.get("quiet") or layer.get("size") == storyboard.TITLE_SIZE]


def test_a_beat_the_script_laid_out_gets_nothing_added_and_an_empty_one_is_still_filled(tmp_path: Path) -> None:
    beats, total = _planned(_laid_out(), tmp_path)
    storyboard.fill_to(beats, total + 6)  # long quiet stretches after the title has landed
    laid, empty = storyboard.scenes(beats, (1920, 1080))
    assert [layer["kind"] for layer in laid["layers"]] == ["title"] and _added(laid) == []
    assert _added(empty) and _quiet(beats[1], empty) == []


def test_fill_also_fills_the_quiet_stretches_between_a_beats_own_layers(tmp_path: Path) -> None:
    beats, total = _planned({"extras": "fill", "beats": _laid_out()}, tmp_path)
    storyboard.fill_to(beats, total + 6)
    laid = storyboard.scenes(beats, (1920, 1080))[0]
    assert _added(laid) and _quiet(beats[0], laid) == []


def test_off_adds_nothing_anywhere_and_a_beat_may_choose_for_itself(tmp_path: Path) -> None:
    rows = _laid_out()
    beats, total = _planned({"extras": "off", "beats": rows}, tmp_path)
    storyboard.fill_to(beats, total + 6)
    assert all(_added(sc) == [] for sc in storyboard.scenes(beats, (1920, 1080)))
    beats, total = _planned({"extras": "off", "beats": [rows[0], {**rows[1], "extras": "auto"}]}, tmp_path)
    storyboard.fill_to(beats, total + 6)
    first, second = storyboard.scenes(beats, (1920, 1080))
    assert _added(first) == [] and _added(second)


def test_a_recording_gets_nothing_added(tmp_path: Path) -> None:
    beats, _ = _planned([{"say": "This one splits a bill, and it really does the math.", "base": {"kind": "living"}}],
                        tmp_path)
    beats[0].base = {"kind": "recording", "file": "app.mp4"}
    assert storyboard.liven(beats[0], []) == []


def test_an_unknown_extras_setting_is_refused(tmp_path: Path) -> None:
    with pytest.raises(storyboard.StoryboardError, match="extras must be one of"):
        storyboard.parse({"extras": "lots", "beats": [{"base": {"kind": "living"}}]}, tmp_path)
    with pytest.raises(storyboard.StoryboardError, match="beat 1: extras"):
        storyboard.parse([{"base": {"kind": "living"}, "extras": True}], tmp_path)
