"""A film as a row of beats: each beat speaks a few phrases over one picture, then hands over to the next.

The voice sets the clock. Every phrase is spoken and measured first, and a beat lasts as long as its words plus a
breath, never less than a short floor, so no line is cut off and no picture waits on silence. Joins between beats are
picked from the story (a wipe into real footage, a zoom back out of it, whips for high energy, dissolves to settle),
timed in whole frames, and never cross a spoken line. Real product footage is the proof, not the film: it may fill
a third of the running time at most, and the rest is generated pictures and motion graphics.

A capture (a still screenshot) or a recording (a screen video with its ``recording.json`` of keys, clicks and pointer
moves) sits in a window frame over a generated background, and the recorded pointer is redrawn on top so it lines up.
This module plans and builds commands; ``studio`` runs them and checks the result.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from . import make_checks, motion, sound

LEAD = 0.25  # seconds from a beat's picture settling to its first word
GAP = 0.18  # between phrases in one beat
BREATH = 0.4  # after a beat's last word, before the next join
MIN_BEAT = 1.5  # a beat with no words, and the floor for any beat
REAL_SHARE = 1 / 3  # real product footage may fill this much of a film at most
FPS = 30
RAMP = 0.25  # music and sounds slide down this long before a line and back up after it
MUSIC_UNDER_VOICE = 0.749  # -12 dB under speech
SOUNDS_UNDER_VOICE = 0.37  # about -4 dB under speech

BASE_KINDS = ("video", "image", "capture", "recording", "living", "color")
REAL_KINDS = ("capture", "recording")
CUTS = ("auto", "cut", "dissolve", "whip", "zoom", "wipe", "flash")
ENERGIES = ("low", "mid", "high")
# Words the engine adds by itself to keep a still picture lively (see ``liven``). "auto" only fills a beat the
# script left without layers of its own; "fill" also fills the quiet stretches between a beat's own layers (the
# films a model writes); "off" adds nothing. Set for the whole film, or per beat.
EXTRAS = ("auto", "fill", "off")
JOIN_SECONDS = {"cut": 0.0, "dissolve": 0.5, "whip": 0.35, "zoom": 0.45, "flash": 0.3, "wipe": 0.7}
XFADE = {"dissolve": "fade", "zoom": "zoomin", "flash": "fadewhite", "whip": "slideleft"}
# How far a window or phone frame sits outside its picture, in design pixels (left, top, right, bottom).
INSETS = {"none": (0, 0, 0, 0), "plain": (0, 0, 0, 0), "window": (2, 44, 2, 2), "phone": (12, 12, 12, 12)}

_ANCHOR = re.compile(r"(start|end|phrase\s+(\d+)(\s+end)?)\s*(?:([+-])\s*(\d+(?:\.\d+)?))?")
_FOOTAGE_KEYS = ("title", "scroll", "focus", "push", "dim", "spring", "start")


class StoryboardError(ValueError):
    """A storyboard that cannot be planned, with the beat it is about."""


@dataclass
class Phrase:
    text: str
    file: Path | None = None
    seconds: float = 0.0
    start: float = 0.0  # film time the phrase begins


@dataclass
class Beat:
    number: int
    phrases: list[Phrase]
    base: dict
    layers: list[dict] = field(default_factory=list)
    sounds: list[dict] = field(default_factory=list)
    cut: str = "auto"  # the join into this beat
    energy: str = "mid"
    real: bool = False
    hold: float | None = None
    meta: dict | None = None
    extras: str = "auto"  # see EXTRAS
    fps: float = FPS
    start_f: int = 0  # film frame where this beat's clip begins
    frames: int = 0  # length of its clip
    into_f: int = 0  # frames the join into it takes before the picture settles
    overlap_f: int = 0  # frames it is blended with the clip before
    cover_f: int = 0  # frames at its end a wipe covers it
    own_f: int = 0  # from clip start to the handover

    @property
    def start(self) -> float:
        return self.start_f / self.fps

    @property
    def seconds(self) -> float:
        return self.frames / self.fps

    @property
    def into(self) -> float:
        return self.into_f / self.fps

    @property
    def overlap(self) -> float:
        return self.overlap_f / self.fps

    @property
    def cover(self) -> float:
        return self.cover_f / self.fps

    @property
    def own(self) -> float:
        return self.own_f / self.fps

    @property
    def span(self) -> float:
        """How much film time the beat moves the clock on."""
        return (self.own_f + self.cover_f) / self.fps


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


_PLAIN_SECONDS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?)?")


def _seconds(v: Any) -> float | None:
    """A time given as plain seconds: a number, or text such as "2", "2.5" or "2s" that models often write."""
    if _number(v):
        return float(v)
    m = _PLAIN_SECONDS.fullmatch(v.strip()) if isinstance(v, str) else None
    return float(m.group(1)) if m else None


def split_phrases(text: str) -> list[str]:
    """Break narration into spoken phrases after each . ! ? or …"""
    return [p for p in re.split(r"(?<=[.!?…])\s+", text.strip()) if p]


# --- reading a storyboard ---------------------------------------------------------------------------

def _inside(root: Path, name: Any, where: str) -> Path:
    """A file named relative to the storyboard's folder, which must stay inside it and not pass through a link."""
    if not isinstance(name, str) or not name or not make_checks.safe_name(name):
        raise StoryboardError(f"{where}: {name!r} must be a plain file name inside the folder")
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise StoryboardError(f"{where}: {name!r} passes through a link; use the real file")
    path = path.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise StoryboardError(f"{where}: {name!r} is not a file in the folder")
    return path


def _phrases(row: dict, root: Path, where: str) -> list[Phrase]:
    if "say" in row and "phrases" in row:
        raise StoryboardError(f"{where}: give say or phrases, not both")
    if "say" in row:
        if not isinstance(row["say"], str):
            raise StoryboardError(f"{where}: say must be text")
        return [Phrase(p) for p in split_phrases(row["say"])]
    items = row.get("phrases", [])
    if not isinstance(items, list):
        raise StoryboardError(f"{where}: phrases must be a list")
    out = []
    for j, item in enumerate(items, start=1):
        if isinstance(item, str):
            item = {"text": item}
        if not (isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip()):
            raise StoryboardError(f"{where}: phrase {j} needs its words as text")
        file = _inside(root, item["file"], f"{where}: phrase {j}") if "file" in item else None
        out.append(Phrase(item["text"].strip(), file))
    return out


def _check_when(value: Any, phrases: int, where: str) -> None:
    seconds = _seconds(value)
    if seconds is not None:
        if seconds < 0:
            raise StoryboardError(f"{where}: a time must be 0 or later")
        return
    m = _ANCHOR.fullmatch(value.strip()) if isinstance(value, str) else None
    if m is None:
        raise StoryboardError(f"{where}: a time is a number of seconds, or start, end, 'phrase N' or 'phrase N end', "
                              f"with an optional + or - seconds")
    if m.group(2) and not 1 <= int(m.group(2)) <= phrases:
        raise StoryboardError(f"{where}: there is no phrase {m.group(2)} in this beat")


def _recording_meta(base: dict, root: Path, where: str) -> dict | None:
    if "meta" in base:
        path = _inside(root, base["meta"], where)
    else:
        path = Path(base["file"]).with_suffix(".json")
        if not path.is_file():
            return None
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StoryboardError(f"{where}: cannot read the recording notes {path.name}: {exc}") from exc
    size = meta.get("size") if isinstance(meta, dict) else None
    if not (isinstance(size, list) and len(size) == 2 and all(_number(v) and v > 0 for v in size)):
        raise StoryboardError(f"{where}: the recording notes {path.name} need a size [width, height]")
    for name, need in (("keys", ("t",)), ("clicks", ("t", "x", "y")), ("moves", ("t", "x", "y"))):
        marks = meta.get(name, [])
        if not (isinstance(marks, list) and all(isinstance(m, dict) and all(_number(m.get(k)) for k in need)
                                                for m in marks)):
            raise StoryboardError(f"{where}: the recording notes {path.name} have a bad {name} list")
    if any(b["t"] < a["t"] for a, b in zip(meta.get("moves", []), meta.get("moves", [])[1:])):
        raise StoryboardError(f"{where}: the pointer moves in {path.name} are not in time order")
    return meta


def _base(row: dict, root: Path, where: str) -> dict:
    base = row.get("base", {"kind": "living"})
    if not isinstance(base, dict):
        raise StoryboardError(f"{where}: base must be an object with a kind")
    base = dict(base)
    kind = base.setdefault("kind", "living")
    if kind not in BASE_KINDS:
        raise StoryboardError(f"{where}: base kind must be one of: {', '.join(BASE_KINDS)}")
    if kind in ("video", "image", "capture", "recording"):
        if "file" not in base:
            raise StoryboardError(f"{where}: a {kind} base needs a file")
        base["file"] = str(_inside(root, base["file"], where))
    for key in ("start", "speed"):
        if key in base and not (_number(base[key]) and base[key] >= 0 and (key == "start" or base[key] > 0)):
            raise StoryboardError(f"{where}: base {key} must be a number above 0")
    if kind in REAL_KINDS:
        behind = base.get("behind", {"kind": "living"})
        if not (isinstance(behind, dict) and behind.get("kind", "living") in ("living", "color", "video", "image")):
            raise StoryboardError(f"{where}: behind must be a living, color, video or image background")
        behind = dict(behind)
        if "file" in behind:
            behind["file"] = str(_inside(root, behind["file"], f"{where}: behind"))
        base["behind"] = behind
        frame = base.get("frame", "window")
        if frame not in INSETS:
            raise StoryboardError(f"{where}: frame must be one of: {', '.join(INSETS)}")
        if base.get("fit", "frame") not in ("frame", "fill"):
            raise StoryboardError(f"{where}: fit must be frame or fill")
        view = base.get("view", [16, 10])
        if not (isinstance(view, list) and len(view) == 2 and all(_number(v) and v > 0 for v in view)):
            raise StoryboardError(f"{where}: view must be [width, height], like [16, 10]")
    return base


def _extras(value: Any, where: str) -> str:
    if value not in EXTRAS:
        raise StoryboardError(f"{where}: extras must be one of: {', '.join(EXTRAS)}")
    return value


def _beat(number: int, row: Any, root: Path, extras: str = "auto") -> Beat:
    where = f"beat {number}"
    if not isinstance(row, dict):
        raise StoryboardError(f"{where} must be an object")
    phrases = _phrases(row, root, where)
    base = _base(row, root, where)
    layers = row.get("layers", [])
    if not (isinstance(layers, list) and all(isinstance(lay, dict) for lay in layers)):
        raise StoryboardError(f"{where}: layers must be a list of objects")
    layers = [dict(lay) for lay in layers]
    for i, lay in enumerate(layers, start=1):
        if "file" in lay:
            lay["file"] = str(_inside(root, lay["file"], f"{where}: layer {i}"))
        for key in ("at", "until"):
            if key in lay:
                _check_when(lay[key], len(phrases), f"{where}: layer {i} {key}")
    sounds = row.get("sounds", [])
    if not (isinstance(sounds, list) and all(isinstance(s, dict) and s.get("kind") in sound.KINDS for s in sounds)):
        raise StoryboardError(f"{where}: sounds must be a list of {{at, kind}}, kind one of: {', '.join(sound.KINDS)}")
    for s in sounds:
        _check_when(s.get("at", 0), len(phrases), f"{where}: sound")
    cut, energy = row.get("cut", "auto"), row.get("energy", "mid")
    if cut not in CUTS:
        raise StoryboardError(f"{where}: cut must be one of: {', '.join(CUTS)}")
    if energy not in ENERGIES:
        raise StoryboardError(f"{where}: energy must be low, mid or high")
    real = row.get("real", base["kind"] in REAL_KINDS)
    if not isinstance(real, bool):
        raise StoryboardError(f"{where}: real must be true or false")
    hold = row.get("hold")
    if hold is not None and not (_number(hold) and hold > 0):
        raise StoryboardError(f"{where}: hold must be a number of seconds above 0")
    meta = None
    if base["kind"] == "recording":
        meta = _recording_meta(base, root, where)
        if hold is None:
            length = (meta or {}).get("seconds") or motion._duration(base["file"])
            if not length:
                raise StoryboardError(f"{where}: cannot read how long the recording is")
            hold = max(MIN_BEAT, (length - base.get("start", 0.0)) / base.get("speed", 1.0))
    extras = _extras(row.get("extras", extras), where)
    return Beat(number, phrases, base, layers, [dict(s) for s in sounds], cut, energy, real, hold, meta, extras)


def parse(data: Any, folder: Path) -> list[Beat]:
    """Read a storyboard: a list of beats, or {"beats": [...]}, with files named inside ``folder``. A storyboard
    object may set ``extras`` for every beat (see ``EXTRAS``); a beat's own ``extras`` wins."""
    rows = data.get("beats") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        raise StoryboardError("a storyboard needs a list of beats")
    extras = _extras(data.get("extras", "auto"), "the storyboard") if isinstance(data, dict) else "auto"
    root = Path(folder).resolve()
    return [_beat(i, row, root, extras) for i, row in enumerate(rows, start=1)]


# --- the clock ---------------------------------------------------------------------------------------

def voice(beats: list[Beat], speak: Callable[[str, str], Path],
          measure: Callable[[Path], float | None] = motion._duration) -> None:
    """Speak every phrase that has no file yet, then measure each one. ``speak(text, name)`` returns the file."""
    for beat in beats:
        for j, phrase in enumerate(beat.phrases, start=1):
            if phrase.file is None:
                phrase.file = Path(speak(phrase.text, f"beat{beat.number:02d}-{j:02d}"))
            seconds = measure(phrase.file)
            if not seconds or seconds <= 0:
                raise StoryboardError(f"beat {beat.number}: phrase {j}: {phrase.file.name} has no sound in it")
            phrase.seconds = float(seconds)


def plan_cuts(beats: list[Beat]) -> None:
    """Choose every join left on auto: a wipe into real footage, a zoom out of it, whips for high energy,
    dissolves to settle and to end, zooms in between, never the same move twice running."""
    for k, beat in enumerate(beats):
        if k == 0:
            beat.cut = "cut"
            continue
        if beat.cut != "auto":
            continue
        before, last = beats[k - 1], beats[k - 1].cut if k > 1 else None
        if beat.real and not before.real:
            beat.cut = "wipe"
        elif before.real and not beat.real:
            beat.cut = "zoom"
        elif beat.energy == "high":
            beat.cut = "cut" if last == "whip" else "whip"
        elif beat.energy == "low" or k == len(beats) - 1:
            beat.cut = "dissolve"
        else:
            beat.cut = "dissolve" if last == "zoom" else "zoom"


def time_beats(beats: list[Beat], fps: float = FPS) -> float:
    """Lay the beats on the film clock in whole frames and return the running time in seconds.

    Each beat runs from its join settling, through its phrases, to a breath after the last word; a wipe takes half
    its time covering the beat before and half revealing this one, and a blend overlaps the two clips."""
    plan_cuts(beats)
    for beat in beats:
        beat.fps, beat.into_f, beat.overlap_f, beat.cover_f = fps, 0, 0, 0
    for before, beat in zip(beats, beats[1:]):
        d = round(JOIN_SECONDS[beat.cut] * fps)
        if beat.cut == "wipe":
            before.cover_f, beat.into_f = d // 2, d - d // 2
        elif beat.cut != "cut":
            beat.into_f = beat.overlap_f = d
    start = 0
    for k, beat in enumerate(beats):
        n = len(beat.phrases)
        talk = LEAD + sum(p.seconds for p in beat.phrases) + GAP * (n - 1) + BREATH if n else 0.0
        floor = beat.hold if beat.hold is not None else MIN_BEAT
        beat.own_f = beat.into_f + max(math.ceil(talk * fps - 1e-6), math.ceil(floor * fps - 1e-6))
        beat.start_f = start
        beat.frames = beat.own_f + beat.cover_f + (beats[k + 1].overlap_f if k + 1 < len(beats) else 0)
        t = beat.start + beat.into + LEAD
        for phrase in beat.phrases:
            phrase.start = round(t, 6)
            t += phrase.seconds + GAP
        start += beat.own_f + beat.cover_f
    return start / fps


def fill_to(beats: list[Beat], target: float, fps: float = FPS) -> float:
    """Time the beats, and when the film comes out shorter than ``target`` seconds, hold every beat a little
    longer after its words until it fills that length. A film already that long is left as it is. Real footage
    already runs its own length, so while there are other beats the extra time goes to them."""
    total = time_beats(beats, fps)
    short = target - total
    if short < 1 / fps or not beats:
        return total
    grow = [b for b in beats if not b.real] or beats
    for beat in grow:
        beat.hold = (beat.own_f - beat.into_f) / fps + short / len(grow)
    return time_beats(beats, fps)


def check_mix(beats: list[Beat], total: float) -> float:
    """The share of the film that is real product footage; more than a third is refused."""
    real = sum(b.span for b in beats if b.real)
    share = real / total if total > 0 else 0.0
    if share > REAL_SHARE + 1e-6:
        raise StoryboardError(f"real product footage fills {share:.0%} ({real:.1f} s of {total:.1f} s); keep it to a "
                              f"third or less, and make the rest generated pictures and motion graphics")
    return share


def when(beat: Beat, value: Any) -> float:
    """A beat-local time: seconds after the picture settles, or start, end, 'phrase N' or 'phrase N end' ± seconds."""
    seconds = _seconds(value)
    if seconds is not None:
        t = beat.into + seconds
    else:
        m = _ANCHOR.fullmatch(str(value).strip())
        if m is None:
            raise StoryboardError(f"beat {beat.number}: {value!r} is not a time")
        if m.group(1) == "start":
            t = 0.0
        elif m.group(1) == "end":
            t = beat.own
        else:
            phrase = beat.phrases[int(m.group(2)) - 1]
            t = phrase.start - beat.start + (phrase.seconds if m.group(3) else 0.0)
        if m.group(4):
            t += float(m.group(5)) * (1 if m.group(4) == "+" else -1)
    return round(min(max(t, 0.0), beat.seconds), 4)


# --- one beat as a motion scene ----------------------------------------------------------------------

def _aspect(beat: Beat) -> float:
    base = beat.base
    if base["kind"] == "capture" and "scroll" in base:
        w, h = base.get("view", [16, 10])
        return w / h
    if beat.meta:
        w, h = beat.meta["size"]
        return w / h
    if base["kind"] == "capture":
        from PIL import Image

        with Image.open(base["file"]) as im:
            w, h = im.size
        return w / h
    size = motion._video_size(base["file"])
    if size is None:
        raise StoryboardError(f"beat {beat.number}: cannot read the size of {Path(base['file']).name}")
    return size[0] / size[1]


def picture_box(beat: Beat, size: tuple[int, int]) -> tuple[list[float], list[float], str]:
    """Where real footage sits, in design pixels: the frame's box, the picture inside it, and the frame kind."""
    W, H = size
    tall = 1920 * H / W
    base = beat.base
    if base.get("fit") == "fill":
        return [0, 0, 1920, tall], [0, 0, 1920, tall], "none"
    frame = base.get("frame", "window")
    left, top, right, bottom = INSETS[frame]
    aspect = _aspect(beat)
    across = 0.94 if H > W else 0.86  # a vertical frame is narrow: the footage takes more of its width
    width = min(across * 1920 - left - right, (0.82 * tall - top - bottom) * aspect)
    height = width / aspect
    box_w, box_h = width + left + right, height + top + bottom
    x, y = (1920 - box_w) / 2, 0.47 * tall - box_h / 2
    box = [round(v, 2) for v in (x, y, box_w, box_h)]
    return box, [round(v, 2) for v in (x + left, y + top, width, height)], frame


def _footage(beat: Beat, size: tuple[int, int]) -> list[dict]:
    base = beat.base
    recording = base["kind"] == "recording"
    box, inner, frame = picture_box(beat, size)
    layer = {"kind": "video" if recording else "image", "file": base["file"], "box": box, "frame": frame,
             "at": beat.into, "enter": base.get("enter", "rise")}
    layer.update({k: base[k] for k in _FOOTAGE_KEYS if k in base})
    if recording:
        layer["speed"] = base.get("speed", 1.0)
    out = [layer]
    meta = beat.meta
    if recording and meta and meta.get("moves"):
        start, speed = base.get("start", 0.0), base.get("speed", 1.0)
        delay = 0.5 if layer["enter"] != "none" else 0.0

        def local(t: float) -> float:
            return (t - start) / speed - delay

        moves = [m for m in meta["moves"] if local(m["t"]) >= 0]
        earlier = [m for m in meta["moves"] if local(m["t"]) < 0]
        moves = ([dict(earlier[-1], t=0.0)] if earlier else []) + [dict(m, t=round(local(m["t"]), 4)) for m in moves]
        clicks = [dict(c, t=round(local(c["t"]), 4)) for c in meta.get("clicks", []) if local(c["t"]) >= 0]
        out.append({"kind": "cursor", "at": round(beat.into + delay, 4), "moves": moves, "clicks": clicks,
                    "map": {"size": list(meta["size"]), "box": inner}})
    return out


# Layers that can be placed in the footage's own pixels, and how a layout written for a wide frame is spread
# down a vertical one: positions keep their share of the height, boxes grow to use the narrow width, words get bigger.
_MAPPED = ("callout", "cursor")
_POINT_KINDS = ("title", "label", "chips", "counter", "lower_third")
_BOX_DEFAULTS = {"cards": (160, 330, 1600, 420), "panel": (560, 190, 800, 700), "terminal": (210, 140, 1500, 800),
                 "video": (160, 90, 1600, 900), "image": (160, 90, 1600, 900)}
_TEXT_SIZES = {"title": 96, "label": 22, "chips": 34, "counter": 160}
_SCALED_TEXT = ("cards", "callout", "lower_third")  # drawn at a fixed size, so they take a text_scale
TALL_TEXT = 1.5
TALL_WIDTH = 1840


def _holds_still(beat: Beat) -> bool:
    """Real footage that keeps one place on screen: not filling the frame, not a scrolling capture."""
    base = beat.base
    return (base["kind"] in REAL_KINDS and base.get("fit") != "fill"
            and not (base["kind"] == "capture" and "scroll" in base))


def _recorded_size(beat: Beat) -> list[int]:
    base = beat.base
    if beat.meta:
        return [int(v) for v in beat.meta["size"]]
    if base["kind"] == "capture":
        from PIL import Image

        with Image.open(base["file"]) as im:
            return list(im.size)
    size = motion._video_size(base["file"])
    if size is None:
        raise StoryboardError(f"beat {beat.number}: cannot read the size of {Path(base['file']).name}")
    return list(size)


def _on_footage(beat: Beat, layer: dict, i: int, size: tuple[int, int]) -> dict:
    """A callout or pointer on still footage is in the footage's own pixels unless it says ``map: frame``."""
    mp = layer.get("map")
    if mp == "frame":
        layer.pop("map")
        return layer
    if mp == "footage":
        if layer["kind"] not in _MAPPED:
            raise StoryboardError(f"beat {beat.number}: layer {i}: only a callout or cursor can be placed on the footage")
        if not _holds_still(beat):
            raise StoryboardError(f"beat {beat.number}: layer {i} asks to be placed on the footage, but this beat has "
                                  "no footage that holds still (a recording, or a capture that neither scrolls nor fills)")
    elif mp is not None or layer["kind"] not in _MAPPED or not _holds_still(beat):
        return layer
    layer["map"] = {"size": _recorded_size(beat), "box": picture_box(beat, size)[1]}
    return layer


def _tall(layer: dict, size: tuple[int, int]) -> dict:
    """Spread a layout written for a 1920 x 1080 frame down a vertical one. Wide and square frames are untouched."""
    W, H = size
    if H <= W:
        return layer
    tall = 1920 * H / W
    f = tall / 1080
    kind = layer["kind"]
    mapped = isinstance(layer.get("map"), dict)  # in the footage's own pixels: the map already places it
    if kind in _TEXT_SIZES:
        layer["size"] = layer.get("size", _TEXT_SIZES[kind]) * TALL_TEXT
    if kind in _SCALED_TEXT:
        layer["text_scale"] = layer.get("text_scale", 1) * TALL_TEXT
    if kind in _POINT_KINDS:
        if "y" in layer:
            layer["y"] = layer["y"] * f
        elif kind == "label":
            layer["y"] = 160 * f
    elif kind == "link":
        layer["from"], layer["to"] = ([p[0], p[1] * f] for p in (layer["from"], layer["to"]))
    elif kind == "cursor" and not mapped:
        for key in ("moves", "clicks"):
            if key in layer:
                layer[key] = [dict(m, y=m["y"] * f) if isinstance(m, dict) and "y" in m else m for m in layer[key]]
    elif (kind in _BOX_DEFAULTS or kind == "callout") and not mapped and (kind != "callout" or "box" in layer):
        box = layer.get("box", _BOX_DEFAULTS.get(kind))
        if not (isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)):
            return layer  # motion.check_scene says what is wrong with it
        x, y, w, h = box
        grow = min(TALL_TEXT, TALL_WIDTH / w) if w > 0 else 1.0
        if kind in ("panel", "terminal"):
            layer["text_scale"] = round(layer.get("text_scale", 1) * grow, 4)  # the words grow with the box
        cx, cy, w, h = x + w / 2, (y + h / 2) * f, w * grow, h * grow
        if kind == "cards":
            n = len(layer.get("items") or [None])
            before = max(1, int(min(layer.get("columns", 4), n)))
            layer["columns"] = min(before, 2)
            h *= math.ceil(n / layer["columns"]) / math.ceil(n / before)
            h = min(h, 0.8 * tall)
        x = min(max(cx - w / 2, 0.0), max(0.0, 1920 - w))
        y = min(max(cy - h / 2, 0.0), max(0.0, tall - h))
        layer["box"] = [round(v, 4) for v in (x, y, w, h)]
    return layer


# --- keeping every second lively ---------------------------------------------------------------------
# A beat that leaves the picture standing still (a still image, a capture, a layer that has finished arriving)
# gets motion made from its own words: the key words of each line land one by one as they are said, and a row
# of them pops in and out over any stretch that would otherwise hold still. What a script laid out by hand is
# never covered: by default only a beat with no layers of its own is filled (see ``EXTRAS``).

LIVELY_GAP = 0.8  # the longest a beat may go with nothing new on screen; the film is measured a second at a time
MOVING = 0.45  # how long one entrance keeps the picture changing
FILL_STEP = 0.6  # the spacing of the pops in a filler row
FILL_Y = 790  # where a filler row sits in a 1080-high frame: under a centred title, over the captions
FILL_SIZE = 54  # its words, big enough to read at a glance
TITLE_SHADOW = 1.0  # the darkest halo, so the words read on a light picture too
TITLE_SIZE = 124  # bigger than a written title: these words carry the line
_SMALL_WORDS = frozenset(
    "a an and are as at be been but by can do for from has have i if in into is it its just me my no not of on "
    "one or our so than that the their them then there these this those to too up us was we were what when "
    "where which who will with you your".split())
_TEXT_KINDS = ("title", "label", "chips", "cards", "panel", "counter", "callout", "lower_third", "terminal")


def key_words(text: str, most: int = 6) -> list[str]:
    """The words of a line worth putting on screen: its first ``most`` words that are not small joining words."""
    words = [w.strip(".,;:!?\"'()[]") for w in text.split()]
    words = [w for w in words if w]
    big = [w for w in words if w.lower() not in _SMALL_WORDS]
    return (big or words)[:most]


def _moving(layer: dict, seconds: float) -> list[tuple[float, float]]:
    """When a layer changes the picture, as (from, to) in clip seconds."""
    kind, at, until = layer["kind"], float(layer.get("at", 0.0)), layer.get("until")
    enter = layer.get("enter", motion._ENTER.get(kind, "fade"))
    if kind in ("video", "cursor", "terminal") or (kind == "image" and "scroll" in layer):
        return [(at, float(until) if until is not None else seconds)]
    if kind == "wipe":
        spans = [(at, at + float(layer.get("duration", 0.6)))]
    elif kind == "counter":
        spans = [(at, at + float(layer.get("duration", 1.2)))]
    elif enter == "type":
        spans = [(at, at + len(str(layer.get("text", ""))) / float(layer.get("cps", 16)))]
    elif enter == "none":
        spans = [(at, at + 0.1)]
    else:
        if kind in ("chips", "cards"):
            n = len(layer.get("items") or [None])
        elif kind == "title" and enter == "words":
            n = len(str(layer.get("text", "")).split())
        else:
            n = 1
        stagger = float(layer.get("stagger", {"chips": 0.08, "title": 0.07}.get(kind, 0.1)))
        spans = [(at, at + stagger * max(n - 1, 0) + MOVING)]
    if until is not None:
        spans.append((float(until), float(until) + motion.EXIT_SECONDS))
    return spans


def quiet_stretches(spans: list[tuple[float, float]], start: float, end: float) -> list[tuple[float, float]]:
    """The stretches between ``start`` and ``end`` longer than ``LIVELY_GAP`` in which nothing moves."""
    out, t = [], start
    for a, b in sorted(spans):
        if a >= end:
            break
        if a - t > LIVELY_GAP:
            out.append((t, a))
        t = max(t, b)
    if end - t > LIVELY_GAP:
        out.append((t, end))
    return out


def liven(beat: Beat, layers: list[dict], words: str = "") -> list[dict]:
    """The layers to add so that this beat never holds still for longer than ``LIVELY_GAP``.

    ``layers`` are the beat's own, already timed. A beat with no words on screen of its own gets each line's key
    words as a title that builds word by word while the line is said; any stretch still left standing gets a row
    of key words that pop in one at a time and leave. ``words`` stands in for a beat that says nothing.

    Nothing is added when the beat's ``extras`` is "off", over moving pictures or a recording (they move by
    themselves), or, with "auto", to a beat that has layers of its own: the script already laid that beat out."""
    if beat.extras == "off" or beat.base["kind"] in ("video", "recording"):
        return []
    if beat.extras == "auto" and beat.layers:
        return []
    spans = [s for layer in layers for s in _moving(layer, beat.seconds)]
    if beat.into:
        spans.append((0.0, beat.into))
    added: list[dict] = []
    if not any(layer["kind"] in _TEXT_KINDS for layer in layers):
        for phrase in beat.phrases:
            shown = key_words(phrase.text)
            if not shown:
                continue
            at = round(phrase.start - beat.start, 4)
            if added:
                added[-1]["until"] = max(at, round(added[-1]["at"] + 0.1, 4))
            stagger = min(max(phrase.seconds / len(shown), 0.07), FILL_STEP)  # the words land as they are said
            added.append({"kind": "title", "text": " ".join(shown), "at": at, "stagger": round(stagger, 4),
                          "size": TITLE_SIZE, "color": "white", "shadow": TITLE_SHADOW, "accent": shown[:1]})
        spans += [s for layer in added for s in _moving(layer, beat.seconds)]
    pool = key_words(" ".join(p.text for p in beat.phrases) or words, most=4)
    if not pool:
        return added
    k = len(pool)
    for start, end in quiet_stretches(spans, 0.0, beat.own):
        rows = max(1, round((end - start) / ((k + 1) * FILL_STEP)))
        length = (end - start) / rows
        step = length / (k + 1)
        for j in range(rows):
            at = start + j * length
            added.append({"kind": "chips", "items": pool[j % k:] + pool[:j % k], "at": round(at, 4),
                          "stagger": round(step, 4), "until": round(at + k * step, 4), "y": FILL_Y, "size": FILL_SIZE, "quiet": True})
    return added


def scene(beat: Beat, size: tuple[int, int], following: Beat | None = None, words: str = "") -> dict:
    """The motion scene for one beat's clip, ready for ``motion.render``. ``following`` is the next beat; ``words``
    gives a beat that says nothing something to show (see ``liven``)."""
    base = dict(beat.base)
    layers: list[dict] = []
    if base["kind"] in REAL_KINDS:
        layers += _footage(beat, size)
        base = dict(base["behind"])
    else:
        for key in ("behind", "fit", "view", "frame", "meta"):
            base.pop(key, None)
        if base["kind"] == "video":
            base.setdefault("push", 0.04)
    for i, layer in enumerate(beat.layers, start=1):
        layer = _tall(_on_footage(beat, dict(layer), i, size), size)
        layer["at"] = when(beat, layer.get("at", 0))
        if "until" in layer:
            layer["until"] = when(beat, layer["until"])
            if layer["until"] <= layer["at"]:
                raise StoryboardError(f"beat {beat.number}: layer {i} ends before it starts once timed")
        layers.append(layer)
    wipes = []
    if beat.cut == "wipe" and beat.into_f:
        wipes.append({"kind": "wipe", "mode": "reveal", "at": 0.0, "duration": beat.into, "quiet": True})
    if following is not None and following.cut == "wipe" and beat.cover_f:
        dur = max(1 / beat.fps, beat.cover - 1 / beat.fps)  # full cover on the clip's last frame
        wipes.append({"kind": "wipe", "mode": "cover", "at": round(beat.seconds - beat.cover, 4),
                      "duration": round(dur, 4)})
    layers += [_tall(layer, size) for layer in liven(beat, layers + wipes, words)] + wipes
    sc = {"size": list(size), "fps": beat.fps, "seconds": beat.seconds, "base": base, "layers": layers}
    try:
        return motion.check_scene(sc)
    except motion.MotionError as exc:
        raise StoryboardError(f"beat {beat.number}: {exc}") from exc


def scenes(beats: list[Beat], size: tuple[int, int]) -> list[dict]:
    """Every beat's scene. A beat that says nothing borrows the nearest line before it (or after it) to show."""
    lines = [" ".join(p.text for p in b.phrases) for b in beats]
    out = []
    for k, b in enumerate(beats):
        near = [lines[i] for i in [*range(k - 1, -1, -1), *range(k + 1, len(beats))] if lines[i]]
        out.append(scene(b, size, beats[k + 1] if k + 1 < len(beats) else None, near[0] if near else ""))
    return out


# --- sound -------------------------------------------------------------------------------------------

def sound_events(beats: list[Beat], scenes_: list[dict]) -> list[tuple[float, str]]:
    """Every sound of the film on its clock: what moves on screen, the beats' own sounds, recorded keystrokes and
    the joins (a whoosh under a whip or zoom, a hit on a flash; a wipe's cover whooshes by itself)."""
    out: list[tuple[float, str]] = []
    for beat, sc in zip(beats, scenes_):
        out += [(beat.start + t, k) for t, k in motion.events(sc)]
        out += [(beat.start + when(beat, s.get("at", 0)), s["kind"]) for s in beat.sounds]
        if beat.base["kind"] == "recording" and beat.meta:
            start, speed = beat.base.get("start", 0.0), beat.base.get("speed", 1.0)
            for key in beat.meta.get("keys", []):
                local = beat.into + (key["t"] - start) / speed
                if beat.into <= local < beat.own:
                    out.append((beat.start + local, "tick"))
        if beat.number > 1 and beat.cut in ("whip", "zoom"):
            out.append((beat.start - 0.1, "whoosh"))
        elif beat.number > 1 and beat.cut == "flash":
            out.append((beat.start + beat.overlap / 2, "hit"))
    return sorted((round(t, 3), k) for t, k in out if t >= 0)


def speech_spans(beats: list[Beat], ramp: float = RAMP) -> list[tuple[float, float]]:
    """When the voice is speaking, with lines closer than two ramps merged so the dips do not overlap."""
    merged: list[tuple[float, float]] = []
    for a, b in sorted((p.start, p.start + p.seconds) for beat in beats for p in beat.phrases):
        if merged and a - merged[-1][1] < 2 * ramp:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def duck(spans: list[tuple[float, float]], depth: float, ramp: float = RAMP) -> str:
    """An FFmpeg volume expression that dips by ``depth`` while the voice speaks, sliding in and out over ``ramp``."""
    if not spans:
        return "1"
    terms = "+".join(f"max(0,min(1,min((t-{a - ramp:.3f})/{ramp:g},({b + ramp:.3f}-t)/{ramp:g})))" for a, b in spans)
    return f"1-{depth:g}*min(1,{terms})"


def captions(beats: list[Beat]) -> str:
    """Captions phrase by phrase, on the film clock, as SRT."""
    def stamp(t: float) -> str:
        ms = round(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    blocks = []
    for phrase in (p for beat in beats for p in beat.phrases):
        blocks.append(f"{len(blocks) + 1}\n{stamp(phrase.start)} --> {stamp(phrase.start + phrase.seconds)}\n"
                      f"{phrase.text}\n")
    return "\n".join(blocks)


# --- commands ----------------------------------------------------------------------------------------

def voice_command(beats: list[Beat], total: float, out: Path) -> list[str] | None:
    """One voice track: every phrase placed at its time, silence between, exactly ``total`` long."""
    phrases = [p for beat in beats for p in beat.phrases]
    if not phrases:
        return None
    cmd, parts = ["ffmpeg", "-v", "error", "-y"], []
    for i, p in enumerate(phrases):
        cmd += ["-i", str(p.file)]
        parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,adelay={round(p.start * 1000)}:all=1[p{i}]")
    n = len(phrases)
    head = "[p0]" if n == 1 else "".join(f"[p{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,"
    parts.append(f"{head}apad=whole_dur={total:.3f},atrim=0:{total:.3f}[voice]")
    return cmd + ["-filter_complex", ";".join(parts), "-map", "[voice]", "-c:a", "pcm_s16le", str(out)]


def join_command(clips: list[Path], beats: list[Beat], out: Path) -> list[str]:
    """Join the beat clips into one picture: straight cuts and wipes end to end, the rest blended over each other."""
    fps = beats[0].fps
    cmd, parts = ["ffmpeg", "-v", "error", "-y"], []
    for i, clip in enumerate(clips):
        cmd += ["-i", str(clip)]
        parts.append(f"[{i}:v]fps={fps:g},settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
    prev = "v0"
    for k in range(1, len(clips)):
        beat, label = beats[k], f"j{k}"
        if beat.cut in ("cut", "wipe"):
            parts.append(f"[{prev}][v{k}]concat=n=2:v=1:a=0,fps={fps:g},settb=AVTB[{label}]")
        else:
            offset, dur = beat.start, beat.overlap
            parts.append(f"[{prev}][v{k}]xfade=transition={XFADE[beat.cut]}:duration={dur:.4f}:offset={offset:.4f}"
                         f"[{label}]")
            if beat.cut == "whip":  # a sideways smear while the picture slides
                parts.append(f"[{label}]gblur=sigma=40:sigmaV=1:enable='between(t,{offset:.4f},{offset + dur:.4f})'"
                             f"[w{k}]")
                label = f"w{k}"
        prev = label
    return cmd + ["-filter_complex", ";".join(parts), "-map", f"[{prev}]", "-an", "-c:v", "libx264",
                  "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", str(out)]


def mix_command(picture: Path, voice_track: Path | None, music: Path | None, sounds: Path | None, total: float,
                spans: list[tuple[float, float]], out: Path, *, loudness: str, picture_filter: str = "") -> list[str]:
    """The finished film: the picture with its fades, the voice cleaned up, music and sound design dipping under
    every line, all brought to one loudness."""
    T = f"{total:.3f}"
    edge = min(0.5, total / 6)
    fit = f"aresample=48000,aformat=channel_layouts=stereo"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(picture)]
    if voice_track is not None:
        cmd += ["-i", str(voice_track)]
    else:
        cmd += ["-f", "lavfi", "-t", T, "-i", "anullsrc=r=48000:cl=mono"]
    parts = [f"[1:a]{fit},highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,"
             f"apad=whole_dur={T},atrim=0:{T}[vo]"]
    labels, index = ["[vo]"], 2
    if music is not None:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        parts.append(f"[{index}:a]{fit},atrim=0:{T},volume=0.6,volume='{duck(spans, MUSIC_UNDER_VOICE)}':eval=frame[mu]")
        labels.append("[mu]")
        index += 1
    if sounds is not None:
        cmd += ["-i", str(sounds)]
        parts.append(f"[{index}:a]{fit},volume='{duck(spans, SOUNDS_UNDER_VOICE)}':eval=frame,"
                     f"apad=whole_dur={T},atrim=0:{T}[fx]")
        labels.append("[fx]")
    mixed = labels[0] if len(labels) == 1 else "".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,"
    parts.append(f"{mixed}{loudness},afade=t=in:d={edge:.3f},afade=t=out:st={total - edge:.3f}:d={edge:.3f}[a]")
    parts.append(f"[0:v]{picture_filter + ',' if picture_filter else ''}fade=t=in:d={edge:.3f},"
                 f"fade=t=out:st={total - edge:.3f}:d={edge:.3f}[v]")
    return cmd + ["-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset",
                  "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", T,
                  "-movflags", "+faststart", str(out)]
