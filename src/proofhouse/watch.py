"""Watch a finished film the way a viewer meets it: where the picture changes, how long each shot holds, what is said
over it and how fast, how loud it is, and which lines come back. One film or several side by side.

It writes, per run: ``watch.md`` (the side-by-side table and each film's shots), ``watch.json`` (the same, for
programs), ``timeline.png`` (every film on one time scale: shots, speech, how much moves) and one
``shots-<name>.jpg`` per film (each shot's start, middle and end frames beside the words spoken over it).
Everything is measured with FFmpeg on this machine; nothing is sent anywhere and nothing costs money.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import motion, studio

FPS = 6  # frames looked at each second
LAG = 3  # a picture change is judged against the frame half a second earlier, so cross-fades count as cuts
SMALL = (64, 36)  # the size frames are compared at
THUMB = (256, 144)  # the size frames are shown at
CUT_LEVEL = 15.0  # mean brightness difference (0-255) above which the picture has changed
EDGE = 0.6  # seconds at the start and end where a fade from or to black is not a cut
DARK = 20  # mean brightness below which a frame reads as black
REPEAT = 0.6  # share of a line's words already said earlier for it to count as said again


class WatchError(ValueError):
    pass


def _frames(path: Path) -> list[Any]:
    """Every frame at FPS, at THUMB size, as PIL images."""
    Image = motion._pil()[0]
    w, h = THUMB
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
                          f"fps={FPS},scale={w}:{h}:flags=area,setsar=1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=False)
    step = w * h * 3
    return [Image.frombytes("RGB", (w, h), run.stdout[i:i + step]) for i in range(0, len(run.stdout) - step + 1, step)]


def _change(frames: list[Any]) -> tuple[list[float], list[float]]:
    """How much the picture changes at each frame (against half a second earlier), and each frame's brightness."""
    small = [f.convert("L").resize(SMALL).tobytes() for f in frames]
    n = SMALL[0] * SMALL[1]
    change = [0.0] * len(small)
    for i in range(LAG, len(small)):
        change[i] = sum(abs(a - b) for a, b in zip(small[i], small[i - LAG])) / n
    return change, [sum(s) / n for s in small]


def cuts(change: list[float], seconds: float) -> list[float]:
    """The moments the picture changes to a new shot: the strongest change within a second either side, above
    CUT_LEVEL, away from the fade-in and fade-out."""
    found = []
    for i, level in enumerate(change):
        around = change[max(0, i - FPS + 1):i + FPS]
        at = round((i - LAG / 2) / FPS, 2)
        if level >= CUT_LEVEL and level == max(around) and EDGE < at < seconds - EDGE:
            if not found or at - found[-1] >= 0.5:
                found.append(at)
    return found


def read_srt(path: Path) -> list[tuple[float, float, str]]:
    """Each caption in an SRT file as (start, end, text)."""
    stamp = r"(\d+):(\d+):(\d+)[,.](\d+)"
    lines = []
    for block in re.split(r"\n\s*\n", re.sub(r"\r+\n?", "\n", path.read_text(encoding="utf-8-sig")).strip()):
        rows = block.strip().split("\n")
        at = next((i for i, row in enumerate(rows) if "-->" in row), None)
        m = re.match(stamp + r"\s*-->\s*" + stamp, rows[at].strip()) if at is not None else None
        if m is None:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        lines.append((start, end, " ".join(r.strip() for r in rows[at + 1:] if r.strip())))
    return lines


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def said_again(lines: list[tuple[float, float, str]]) -> list[dict[str, Any]]:
    """Lines whose words were mostly said already earlier in the film."""
    seen: set[str] = set()
    again = []
    for start, _end, text in lines:
        words = [w for w in _words(text) if len(w) > 3]
        if words and sum(w in seen for w in words) / len(words) >= REPEAT:
            again.append({"at": round(start, 2), "line": text})
        seen.update(words)
    return again


GENERIC = {"film", "films", "out", "output", "render", "renders", "final"}


def _name(path: Path) -> str:
    """A film called video-16x9.mp4 is named after its folder (or the folder above a folder called film)."""
    if not path.stem.lower().startswith("video"):
        return path.stem
    folder = path.parent
    return folder.parent.name if folder.name.lower() in GENERIC and folder.parent.name else folder.name


def review(path: Path, captions: Path | None = None, name: str | None = None) -> dict[str, Any]:
    """Everything measured about one film. ``captions`` defaults to a captions.srt beside it."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise WatchError("watching a film needs FFmpeg (ffmpeg and ffprobe) installed")
    path = Path(path)
    if not path.is_file():
        raise WatchError(f"no film at {path}")
    facts = studio.probe(path)
    seconds = facts["seconds"]
    frames = _frames(path)
    if not frames or seconds <= 0:
        raise WatchError(f"FFmpeg could not read the picture in {path}")
    change, light = _change(frames)
    found = cuts(change, seconds)
    captions = captions if captions is not None else path.with_name("captions.srt")
    lines = read_srt(captions) if captions and Path(captions).is_file() else []
    bounds = [0.0, *found, seconds]
    shots = []
    for n, (start, end) in enumerate(zip(bounds, bounds[1:]), 1):
        over = [t for s, e, t in lines if start <= (s + e) / 2 < end]
        words = sum(len(_words(t)) for t in over)
        shots.append({"shot": n, "start": round(start, 2), "end": round(end, 2), "seconds": round(end - start, 2),
                      "words": words, "words_per_second": round(words / (end - start), 2) if end > start else 0.0,
                      "said": " ".join(over)})
    spoken = sum(e - s for s, e, _t in lines)
    gaps = [b[0] - a[1] for a, b in zip([(0.0, 0.0, "")] + lines, lines + [(seconds, seconds, "")])]
    lengths = [s["seconds"] for s in shots]
    sound = studio.sound_facts(path) if facts.get("audio") else None
    moving = sum(c >= 3.0 for c in change[LAG:]) / max(1, len(change) - LAG)
    total_words = sum(len(_words(t)) for _s, _e, t in lines)
    return {
        "film": str(path), "name": name or _name(path),
        "seconds": round(seconds, 2), "size": [facts.get("width"), facts.get("height")],
        "shots": shots, "cuts": found,
        "shot_count": len(shots), "average_shot": round(sum(lengths) / len(lengths), 2),
        "longest_shot": max(lengths), "shortest_shot": min(lengths),
        "words": total_words, "words_per_minute": round(total_words / seconds * 60, 1) if lines else None,
        "speech_share": round(spoken / seconds, 3) if lines else None,
        "longest_without_words": round(max(gaps), 2) if lines else None,
        "said_again": said_again(lines),
        "moving_share": round(moving, 3),
        "dark_seconds": round(sum(v < DARK for v in light) / FPS, 2),
        "loudness_lufs": sound["loudness_lufs"] if sound else None,
        "silent_share": sound["silent_share"] if sound else None,
        "_frames": frames, "_change": change, "_lines": lines,
    }


def _frame_at(film: dict, t: float) -> Any:
    frames = film["_frames"]
    return frames[max(0, min(len(frames) - 1, round(t * FPS)))]


def shot_sheet(film: dict, out: Path) -> Path:
    """One row per shot: its start, middle and end frames, with its length and the words spoken over it."""
    Image, _chops, ImageDraw = motion._pil()[:3]
    tw, th = THUMB
    label, pad = 440, 8
    head, body = motion.font("ui_bold", 22), motion.font("ui", 18)
    sheet = Image.new("RGB", (label + 3 * (tw + pad) + pad, 60 + len(film["shots"]) * (th + pad)), (250, 250, 250))
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 14), f"{film['name']}  |  {film['seconds']} s, {film['shot_count']} shots, "
                         f"{film['words']} words", fill=(0, 0, 0), font=head)
    for row, shot in enumerate(film["shots"]):
        y = 60 + row * (th + pad)
        a, b = shot["start"], shot["end"]
        for col, t in enumerate((a + min(0.3, (b - a) / 4), (a + b) / 2, b - min(0.3, (b - a) / 4))):
            sheet.paste(_frame_at(film, t), (label + pad + col * (tw + pad), y))
        draw.text((pad, y + 4), f"Shot {shot['shot']}  {a:.1f}-{b:.1f} s  ({shot['seconds']:.1f} s)",
                  fill=(0, 0, 0), font=head)
        draw.text((pad, y + 34), f"{shot['words']} words, {shot['words_per_second']} a second",
                  fill=(90, 90, 90), font=body)
        text = shot["said"] or "(nothing said)"
        for i, line in enumerate(motion._wrap(text, body, label - 2 * pad)[:4]):
            draw.text((pad, y + 62 + i * 21), line, fill=(30, 30, 120), font=body)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=86)
    return out


def timeline(films: list[dict], out: Path) -> Path:
    """Every film on one time scale: a frame each second, the shots, when words are spoken, and how much moves."""
    Image, _chops, ImageDraw = motion._pil()[:3]
    longest = max(f["seconds"] for f in films)
    px = 40  # pixels per second
    left, strip = 220, (px, round(px * 9 / 16))
    width = left + round(longest * px) + 20
    band = 34 + strip[1] + 26 + 22 + 50 + 20
    img = Image.new("RGB", (width, len(films) * band + 30), "white")
    draw = ImageDraw.Draw(img)
    head, small = motion.font("ui_bold", 18), motion.font("ui", 14)
    for s in range(0, int(longest) + 1, 5):
        draw.text((left + s * px, len(films) * band + 6), f"{s}s", fill=(110, 110, 110), font=small)
    for r, film in enumerate(films):
        y = r * band
        draw.text((8, y + 8), film["name"][:22], fill=(0, 0, 0), font=head)
        draw.text((8, y + 34), f"{film['shot_count']} shots, {film['words']} words", fill=(90, 90, 90), font=small)
        y += 34
        for s in range(int(film["seconds"])):
            img.paste(_frame_at(film, s + 0.5).resize(strip), (left + s * px, y))
        y += strip[1] + 4
        for i, shot in enumerate(film["shots"]):
            x0, x1 = left + shot["start"] * px, left + shot["end"] * px
            draw.rectangle([x0, y, x1 - 2, y + 20], fill=(70, 110, 200) if i % 2 else (120, 160, 235))
            draw.text((x0 + 3, y + 2), str(shot["shot"]), fill="white", font=small)
        y += 26
        again = {a["at"] for a in film["said_again"]}
        for s, e, _t in film["_lines"]:
            draw.rectangle([left + s * px, y, left + e * px, y + 16],
                           fill=(220, 60, 60) if round(s, 2) in again else (60, 170, 90))
        y += 22
        change = film["_change"]
        top = max(max(change), CUT_LEVEL * 2)
        points = [(left + ((i - LAG / 2) / FPS) * px, y + 46 - min(46.0, c / top * 46)) for i, c in enumerate(change)]
        draw.line(points, fill=(200, 120, 20), width=2)
        draw.line([(left, y + 46 - CUT_LEVEL / top * 46), (width - 20, y + 46 - CUT_LEVEL / top * 46)],
                  fill=(230, 200, 160), width=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


ROWS = [
    ("Length", "seconds", "{} s"), ("Shots", "shot_count", "{}"), ("Average shot", "average_shot", "{} s"),
    ("Longest shot", "longest_shot", "{} s"), ("Shortest shot", "shortest_shot", "{} s"), ("Words", "words", "{}"),
    ("Words a minute", "words_per_minute", "{}"), ("Share of the film with words", "speech_share", "{:.0%}"),
    ("Longest stretch without words", "longest_without_words", "{} s"),
    ("Lines said again", "said_again", "{}"), ("Share of the film where something moves", "moving_share", "{:.0%}"),
    ("Seconds of black", "dark_seconds", "{} s"), ("Loudness", "loudness_lufs", "{} LUFS"),
    ("Share silent", "silent_share", "{:.0%}"),
]


def _cell(film: dict, key: str, form: str) -> str:
    value = film.get(key)
    if isinstance(value, list):
        value = len(value)
    return "not measured" if value is None else form.format(value)


def report(films: list[dict]) -> str:
    names = [f["name"] for f in films]
    out = ["# Films side by side", "", "| | " + " | ".join(names) + " |", "|---" * (len(films) + 1) + "|"]
    out += [f"| {label} | " + " | ".join(_cell(f, key, form) for f in films) + " |" for label, key, form in ROWS]
    out += ["", "Pictures: `timeline.png` shows every film on one time scale (a frame each second, shots in blue, "
            "words in green, a line said again in red, and how much the picture moves in orange; the pale line is "
            "where a change counts as a cut). Each `shots-<name>.jpg` puts a shot's start, middle and end frames "
            "beside the words spoken over it."]
    for film in films:
        out += ["", f"## {film['name']}", "", f"`{film['film']}`", "", "| Shot | When | Length | Words a second | Said |",
                "|---|---|---|---|---|"]
        out += [f"| {s['shot']} | {s['start']:.1f}-{s['end']:.1f} s | {s['seconds']:.1f} s | {s['words_per_second']} | "
                f"{s['said'].replace('|', '/') or '(nothing)'} |" for s in film["shots"]]
        if film["said_again"]:
            out += ["", "Said again: " + "; ".join(f"{a['at']:.1f} s '{a['line']}'" for a in film["said_again"])]
    return "\n".join(out) + "\n"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "film"


def watch(paths: list[Path], out_dir: Path, captions: list[Path | None] | None = None,
          names: list[str | None] | None = None) -> dict[str, Any]:
    """Review each film and write the side-by-side report, timeline and shot sheets into ``out_dir``."""
    if not paths:
        raise WatchError("name at least one film")
    if len(captions or []) > len(paths) or len(names or []) > len(paths):
        raise WatchError("more --captions or --name values than films")
    captions = list(captions or []) + [None] * (len(paths) - len(captions or []))
    names = list(names or []) + [None] * (len(paths) - len(names or []))
    films = [review(Path(p), c, n) for p, c, n in zip(paths, captions, names)]
    used: set[str] = set()
    for film in films:
        slug, n = _slug(film["name"]), 2
        while slug in used:
            slug, n = f"{_slug(film['name'])}-{n}", n + 1
        used.add(slug)
        film["sheet"] = str(shot_sheet(film, out_dir / f"shots-{slug}.jpg"))
    picture = timeline(films, out_dir / "timeline.png")
    (out_dir / "watch.md").write_text(report(films), encoding="utf-8")
    plain = [{k: v for k, v in f.items() if not k.startswith("_")} for f in films]
    (out_dir / "watch.json").write_text(json.dumps({"films": plain, "timeline": str(picture)}, indent=2),
                                        encoding="utf-8")
    return {"films": plain, "timeline": str(picture), "report": str(out_dir / "watch.md")}
