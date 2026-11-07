"""Motion graphics for films: springs, typing rhythm, and animated layers drawn over any picture.

A scene is data: a size, a frame rate, a length in seconds, a base (a living background, a video, an
image, a flat colour or nothing) and a list of layers. Layers are placed in 1920-wide design pixels,
so one scene draws at any size, and every time inside a layer counts from that layer's own ``at``.

The built-in renderer draws each frame with Pillow and pipes it to FFmpeg. Other renderers (Remotion,
Hyperframes, Blender or anything that reads a scene file) are lines of data in
``data/motion_renderers.json``; fonts are data in ``data/motion_fonts.json``.

The timing rules follow the readme-hype cut (videos/readme-hype/studio/timeline.ts), which sets the
minimum quality: springs simulated frame by frame, and typing that never runs on a metronome.
"""

from __future__ import annotations

import functools
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
FONTS_FILE = DATA / "motion_fonts.json"
RENDERERS_FILE = DATA / "motion_renderers.json"


class MotionError(ValueError):
    """A scene or a render was refused; the message says why in plain words."""


THEME = {
    "accent": "#3ddc84",
    "mint": "#c8f5d8",
    "dim": "#6f9a7e",
    "soft": "#9cc7ab",
    "ink": "#070b09",
    "panel": "#0c1510",
    "line": "#1d3528",
    "glow": "#0f5c43",
    "deep": "#0a2a1f",
    "white": "#f4fff8",
}

SPRINGS = {
    "pop": {"mass": 0.7, "stiffness": 170.0, "damping": 14.0},
    "panel": {"mass": 0.9, "stiffness": 80.0, "damping": 17.0},
    "pill": {"mass": 0.8, "stiffness": 150.0, "damping": 15.0},
}
EXIT_SECONDS = 0.35
_SPRING_CAP = 4.0

KINDS = ("title", "label", "chips", "cards", "panel", "counter", "callout", "cursor", "lower_third",
         "terminal", "video", "image", "wipe", "link")
BASES = ("living", "video", "image", "color", "none")
ENTERS = ("none", "fade", "rise", "drop", "left", "right", "pop", "pop-rise", "zoom")
FRAMES = ("window", "phone", "plain", "none")
WIPE_MODES = ("through", "cover", "reveal")
WIPE_DIRECTIONS = ("right", "left", "down", "up")

_REQUIRED = {
    "title": ("text",), "label": ("text",), "chips": ("items",), "cards": ("items",), "panel": ("rows",),
    "counter": ("to",), "callout": ("box",), "cursor": ("moves",), "lower_third": ("title",),
    "terminal": ("timeline",), "video": ("file",), "image": ("file",), "link": ("from", "to"), "wipe": (),
}
_ENTER = {
    "title": "words", "label": "left", "lower_third": "left", "chips": "pop-rise", "cards": "rise",
    "panel": "rise", "counter": "rise", "terminal": "rise", "video": "rise", "image": "rise",
    "callout": "pop", "cursor": "none", "wipe": "none", "link": "none",
}
_SPRING = {"title": "pop", "callout": "pop", "chips": "pill"}
_NUMBERS = ("at", "until", "size", "stagger", "duration", "depth", "spotlight", "shadow", "width", "x", "y",
            "leading", "cps", "speed", "start", "dim", "push", "bend", "decimals", "columns", "pad", "radius",
            "tracking", "text_scale")


# --- timing -----------------------------------------------------------------------------------------

def hash01(n: float) -> float:
    """A repeatable pseudo-random number in [0, 1) for a given input."""
    x = math.sin(n * 127.1 + 311.7) * 43758.5453
    return x - math.floor(x)


def char_times(text: str, cps: float, seed: float = 0) -> list[float]:
    """Seconds at which each character lands, plus the end time. Uneven on purpose."""
    out: list[float] = []
    t = 0.0
    for i, ch in enumerate(text):
        out.append(t)
        gap = (1.0 / cps) * (0.5 + hash01(i * 7.3 + seed))
        if ch == " ":
            gap *= 1.25
        if ch in ",.":
            gap += 0.1
        t += gap
    out.append(t)
    return out


def typed_count(times: list[float], local: float) -> int:
    """How many characters are on screen ``local`` seconds after typing started."""
    n = 0
    for i in range(len(times) - 1):
        if local >= times[i]:
            n = i + 1
        else:
            break
    return n


def spring(t: float, *, fps: float = 30, mass: float = 1.0, stiffness: float = 100.0, damping: float = 10.0) -> float:
    """Spring from 0 to 1, ``t`` seconds after release; simulated per frame like Remotion's spring()."""
    if t <= 0:
        return 0.0
    steps = int(t * fps * 4)
    dt = 1.0 / (fps * 4)
    x, v = 0.0, 0.0
    for _ in range(steps):
        a = (-stiffness * (x - 1.0) - damping * v) / mass
        v += a * dt
        x += v * dt
    return x


def ease_in_out(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 0.5 - 0.5 * math.cos(math.pi * p)


def ease_out(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1.0 - (1.0 - p) ** 3


@functools.lru_cache(maxsize=32)
def _spring_table(mass: float, stiffness: float, damping: float, fps: float) -> list[float]:
    """The same simulation as spring(), kept once per spring so a frame is a table lookup."""
    dt = 1.0 / (fps * 4)
    x, v = 0.0, 0.0
    table = [0.0]
    for _ in range(int(_SPRING_CAP * fps * 4)):
        a = (-stiffness * (x - 1.0) - damping * v) / mass
        v += a * dt
        x += v * dt
        table.append(x)
    return table


def _spring_at(local: float, cfg: dict, fps: float) -> float:
    if local <= 0:
        return 0.0
    table = _spring_table(float(cfg["mass"]), float(cfg["stiffness"]), float(cfg["damping"]), float(fps))
    i = int(local * fps * 4)
    return table[i] if i < len(table) else 1.0


def _spring_of(layer: dict, kind: str) -> dict:
    sp = layer.get("spring")
    if sp is None:
        return SPRINGS[_SPRING.get(kind, "panel")]
    if isinstance(sp, str):
        return SPRINGS[sp]
    return {**SPRINGS["panel"], **sp}


def _enter(style: str, s: float, local: float) -> tuple[float, float, float, float]:
    """How an entering element sits: design-pixel shift, scale and opacity for spring progress ``s``."""
    op = _clamp(1.3 * s)
    k = 1.0 - s
    if style == "rise":
        return 0.0, 48 * k, 0.97 + 0.03 * s, op
    if style == "drop":
        return 0.0, -48 * k, 0.97 + 0.03 * s, op
    if style == "left":
        return -80 * k, 0.0, 1.0, op
    if style == "right":
        return 80 * k, 0.0, 1.0, op
    if style == "pop":
        return 0.0, 0.0, 0.6 + 0.4 * s, op
    if style == "pop-rise":
        return 0.0, 28 * k, 0.86 + 0.14 * s, op
    if style == "zoom":
        return 0.0, 0.0, 1.2 - 0.2 * s, op
    if style == "fade":
        return 0.0, 0.0, 1.0, ease_out(local / 0.45)
    return 0.0, 0.0, 1.0, 1.0


def _drift(st: _State, layer: dict, t: float) -> float:
    """A slow sideways push across the scene, deeper layers moving more (parallax)."""
    depth = layer.get("depth", 0)
    return -depth * 30 * (t / st.seconds - 0.5) * st.u if depth else 0.0


def _motion(st: _State, layer: dict, kind: str, t: float, local: float, fade: float) -> tuple[float, float, float, float]:
    s = _spring_at(local, _spring_of(layer, kind), st.fps)
    dx, dy, sc, op = _enter(layer.get("enter", _ENTER[kind]), s, local)
    return dx * st.u + _drift(st, layer, t), dy * st.u, sc, op * fade


def _life(layer: dict, t: float) -> tuple[float, float] | None:
    """Seconds since the layer started and how far it has faded out, or None when it is not on screen."""
    at = layer.get("at", 0.0)
    if t < at:
        return None
    until = layer.get("until")
    if until is None:
        return t - at, 1.0
    if t >= until:
        return None
    span = min(EXIT_SECONDS, (until - at) / 3)
    return t - at, ease_in_out((until - t) / span)


def counter_value(layer: dict, t: float) -> int | float:
    """The number a counter layer shows at scene time ``t``."""
    start, end = layer.get("from", 0), layer["to"]
    decimals = int(layer.get("decimals", 0))
    local = t - layer.get("at", 0)
    if local <= 0:
        value = start
    else:
        p = local / layer.get("duration", 1.2)
        value = end if p >= 1 else start + (end - start) * ease_out(p)
    value = round(value, decimals)
    return int(value) if decimals == 0 else value


def _counter_text(layer: dict, value: float) -> str:
    d = int(layer.get("decimals", 0))
    number = f"{value:,.{d}f}" if layer.get("grouping", True) else f"{value:.{d}f}"
    return f"{layer.get('prefix', '')}{number}{layer.get('suffix', '')}"


# --- small helpers ----------------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _pil() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
    except ImportError as exc:
        raise MotionError("motion graphics need the video extra: uv tool install 'proofhouse[video]'") from exc
    return Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def rgb(color: Any) -> tuple[int, int, int]:
    """A colour as three 0-255 numbers, from a theme name, #rgb, #rrggbb(aa) or a list of numbers."""
    if isinstance(color, str):
        value = THEME.get(color, color)
        if re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value):
            h = value[1:]
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    elif (isinstance(color, (list, tuple)) and len(color) in (3, 4)
          and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in color)):
        return int(color[0]), int(color[1]), int(color[2])
    raise MotionError(f"{color!r} is not a colour; use #rrggbb or one of: {', '.join(THEME)}")


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


_PLAIN_NUMBER = re.compile(r"-?(\d+\.?\d*|\.\d+)")


def _read_number(v: Any) -> Any:
    """A plain number written as text ("500", " -2.5 ") as that number; anything else unchanged."""
    if isinstance(v, str) and _PLAIN_NUMBER.fullmatch(v.strip()):
        text = v.strip()
        return float(text) if "." in text else int(text)
    return v


def _px(v: float) -> float:
    """Font and stroke sizes rounded to a quarter pixel, so drawn sprites can be reused."""
    return max(1.0, round(v * 4) / 4)


def _bare(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


@functools.lru_cache(maxsize=256)
def _opacity_lut(level: int) -> list[int]:
    return [v * level // 255 for v in range(256)]


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MotionError(f"{Path(path).name} could not be read as JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MotionError(f"{Path(path).name} must hold a JSON object")
    return data


# --- fonts ------------------------------------------------------------------------------------------

def _platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    return "darwin" if sys.platform == "darwin" else "linux"


@functools.lru_cache(maxsize=1)
def _font_table() -> dict:
    """The shipped font table, with the user's own motion_fonts.json (in the Proofhouse home) tried first."""
    from . import providers

    table = _read_json(FONTS_FILE)
    user = providers.proofhouse_home() / "motion_fonts.json"
    if user.is_file():
        mine = _read_json(user)
        roles = dict(table.get("roles", {}))
        for role, entries in mine.get("roles", {}).items():
            roles[role] = list(entries) + list(roles.get(role, []))
        folders = dict(table.get("folders", {}))
        for plat, dirs in mine.get("folders", {}).items():
            folders[plat] = list(dirs) + list(folders.get(plat, []))
        table = {**table, "roles": roles, "folders": folders}
    return table


@functools.lru_cache(maxsize=1)
def _font_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for folder in _font_table().get("folders", {}).get(_platform(), []):
        root = Path(os.path.expanduser(os.path.expandvars(folder)))
        if not root.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                index.setdefault(name.lower(), os.path.join(dirpath, name))
    return index


@functools.lru_cache(maxsize=256)
def font(role: str, size: float) -> Any:
    """The first installed font for a role (display, ui, ui_bold, mono ...), at ``size`` pixels."""
    ImageFont = _pil()[4]
    roles = _font_table().get("roles", {})
    if role not in roles:
        raise MotionError(f"unknown font role {role!r}; known roles: {', '.join(roles)}")
    size = max(1.0, float(size))
    fallback = None
    for entry in roles[role]:
        spec = {"file": entry} if isinstance(entry, str) else entry
        if not isinstance(spec, dict) or not isinstance(spec.get("file"), str):
            continue
        given = Path(os.path.expanduser(os.path.expandvars(spec["file"])))
        path = str(given) if given.is_absolute() else _font_index().get(spec["file"].lower())
        if not path or not os.path.isfile(path):
            continue
        try:
            f = ImageFont.truetype(path, size, index=int(spec.get("index", 0)))
        except OSError:
            continue
        if spec.get("variation"):
            try:
                f.set_variation_by_name(spec["variation"])
            except (ValueError, OSError):
                fallback = fallback or f
                continue
        return f
    return fallback or ImageFont.load_default(size)


def _text_width(f: Any, text: str, tracking: float = 0.0) -> float:
    return f.getlength(text) + tracking * max(0, len(text) - 1)


@functools.lru_cache(maxsize=512)
def _cap(role: str, px: float) -> float:
    """Height of a capital letter above the baseline."""
    return -font(role, px).getbbox("H", anchor="ls")[1]


@functools.lru_cache(maxsize=4096)
def _text_sprite(text: str, role: str, px: float, color: tuple, tracking: float = 0.0,
                 halo: float = 0.0) -> tuple[Any, int, int]:
    """Text drawn once on a transparent sprite; returns it with the baseline-left origin inside it."""
    Image, _, ImageDraw, ImageFilter, _ = _pil()
    f = font(role, px)
    left, top, right, bottom = f.getbbox(text or " ", anchor="ls")
    right = max(right, left + math.ceil(_text_width(f, text, tracking)))
    blur = max(1.5, 0.12 * px) if halo else 0.0
    pad = max(2, int(px) // 8) + math.ceil(2.5 * blur)
    width, height = int(right - left) + 2 * pad, int(bottom - top) + 2 * pad
    ox, oy = pad - int(left), pad - int(top)
    img = Image.new("RGBA", (width, height), color + (0,))
    draw = ImageDraw.Draw(img)
    if tracking:
        x = float(ox)
        for ch in text:
            draw.text((x, oy), ch, font=f, fill=color + (255,), anchor="ls")
            x += f.getlength(ch) + tracking
    else:
        draw.text((ox, oy), text, font=f, fill=color + (255,), anchor="ls")
    if halo:
        shade = img.getchannel("A").filter(ImageFilter.GaussianBlur(blur))
        shade = shade.point([min(255, int(v * halo)) for v in range(256)])
        under = Image.new("RGBA", img.size, rgb("ink") + (0,))
        under.putalpha(shade)
        under.alpha_composite(img)
        img = under
    return img, ox, oy


def _wrap(text: str, f: Any, max_w: float, tracking: float = 0.0) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            trial = cur + " " + w
            if _text_width(f, trial, tracking) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _lines(img: Any, x: float, y: float, text: str, role: str, px: float, color: tuple, max_w: float,
           leading: float, tracking: float = 0.0) -> float:
    """Wrapped text whose first capital starts at ``y``; returns the last baseline."""
    f = font(role, px)
    base = y + _cap(role, px)
    rows = _wrap(text, f, max_w, tracking)
    for k, row in enumerate(rows):
        spr, ox, oy = _text_sprite(row, role, px, color, tracking)
        _compose(img, spr, x, base + k * px * leading, ox, oy)
    return base + (len(rows) - 1) * px * leading


# --- drawing primitives -----------------------------------------------------------------------------

def _compose(dest: Any, sprite: Any, x: float, y: float, ax: float = 0.0, ay: float = 0.0, scale: float = 1.0,
             opacity: float = 1.0, smooth: bool = False) -> None:
    """Lay ``sprite`` on ``dest`` with its point (ax, ay) at (x, y), scaled about that point."""
    if opacity <= 0.003 or scale <= 0.01:
        return
    Image = _pil()[0]
    sw, sh = sprite.size
    if abs(scale - 1.0) < 0.002 and not smooth:
        left, top = round(x - ax), round(y - ay)
        part = sprite
    else:
        left, top = math.floor(x - ax * scale), math.floor(y - ay * scale)
        right, bottom = math.ceil(x + (sw - ax) * scale), math.ceil(y + (sh - ay) * scale)
        if right <= left or bottom <= top:
            return
        part = sprite.transform(
            (right - left, bottom - top), Image.Transform.AFFINE,
            (1 / scale, 0, (left - x) / scale + ax, 0, 1 / scale, (top - y) / scale + ay),
            resample=Image.Resampling.BILINEAR,
        )
    W, H = dest.size
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(W, left + part.width), min(H, top + part.height)
    if x1 <= x0 or y1 <= y0:
        return
    if (x0, y0, x1, y1) != (left, top, left + part.width, top + part.height):
        part = part.crop((x0 - left, y0 - top, x1 - left, y1 - top))
    if opacity < 0.997:
        if part is sprite:
            part = part.copy()
        part.putalpha(part.getchannel("A").point(_opacity_lut(round(opacity * 255))))
    dest.alpha_composite(part, (x0, y0))


def _place(dest: Any, sprite: Any, ox: float, oy: float, px: float, py: float, cx: float, cy: float,
           dx: float, dy: float, scale: float, op: float) -> None:
    """Put the sprite's point (ox, oy) at (px, py), scaled about (cx, cy) and shifted by (dx, dy)."""
    _compose(dest, sprite, cx + (px - cx) * scale + dx, cy + (py - cy) * scale + dy, ox, oy, scale, op)


@functools.lru_cache(maxsize=512)
def _shape(w: float, h: float, radius: float, fill: tuple, outline: tuple | None = None,
           stroke: float = 0.0) -> Any:
    """A rounded rectangle drawn three times larger and shrunk, so its edges are smooth."""
    Image, _, ImageDraw, _, _ = _pil()
    W, H, S = max(1, round(w)), max(1, round(h)), 3
    big = Image.new("RGBA", (W * S, H * S), (outline or fill)[:3] + (0,))
    r = min(radius, W / 2, H / 2) * S
    width = max(1, round(stroke * S)) if outline else 0
    ImageDraw.Draw(big).rounded_rectangle((0, 0, W * S - 1, H * S - 1), radius=r, fill=fill, outline=outline,
                                          width=width)
    return big.resize((W, H), Image.Resampling.LANCZOS)


@functools.lru_cache(maxsize=256)
def _glow(w: float, h: float, radius: float, color: tuple, blur: float, strength: float) -> tuple[Any, int]:
    """A soft glow or shadow the size of a w x h box, with a margin ``m`` around it."""
    Image, _, ImageDraw, ImageFilter, _ = _pil()
    w, h = max(1, round(w)), max(1, round(h))
    m = int(3 * blur) + 1
    mask = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(mask).rounded_rectangle((m, m, m + w - 1, m + h - 1), radius=min(radius, w / 2, h / 2),
                                           fill=round(255 * strength))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    img = Image.new("RGBA", mask.size, color + (0,))
    img.putalpha(mask)
    return img, m


@functools.lru_cache(maxsize=64)
def _round_mask(w: int, h: int, radius: float, top: bool = True) -> Any:
    Image, _, ImageDraw, _, _ = _pil()
    S = 3
    big = Image.new("L", (w * S, h * S), 0)
    corners = None if top else (False, False, True, True)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=max(0.0, radius) * S, fill=255,
                                          corners=corners)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def _box(layer: dict, default: tuple | None, u: float) -> tuple[float, float, float, float]:
    x, y, w, h = layer.get("box", default)
    return x * u, y * u, w * u, h * u


def _cover(img: Any, size: tuple[int, int], zoom: float = 1.0, focus: Any = (0.5, 0.5)) -> Any:
    """Fill ``size`` with the picture, cropping the overflow around ``focus`` (0-1 across and down)."""
    Image = _pil()[0]
    W, H = size
    iw, ih = img.size
    scale = max(W / iw, H / ih) * zoom
    vw, vh = W / scale, H / scale
    fx, fy = focus
    x0 = _clamp(fx * iw - vw / 2, 0, max(0.0, iw - vw))
    y0 = _clamp(fy * ih - vh / 2, 0, max(0.0, ih - vh))
    return img.resize((W, H), Image.Resampling.BICUBIC, box=(x0, y0, x0 + vw, y0 + vh))


def _dim(img: Any, level: float) -> Any:
    Image = _pil()[0]
    shade = Image.new(img.mode, img.size, rgb("ink") + ((255,) if img.mode == "RGBA" else ()))
    return Image.blend(img, shade, _clamp(level))


def _opaque(img: Any, color: tuple) -> Any:
    Image = _pil()[0]
    if img.mode != "RGBA":
        return img.convert("RGB")
    bg = Image.new("RGBA", img.size, color + (255,))
    bg.alpha_composite(img)
    return bg.convert("RGB")


# --- cached pieces ----------------------------------------------------------------------------------

@functools.lru_cache(maxsize=256)
def _chip(text: str, px: float, hot: bool, u: float) -> tuple[Any, int, int, int]:
    f = font("ui_bold", px)
    tw = f.getlength(text)
    w, h = round(tw + 1.9 * px), round(2 * px)
    glow, m = _glow(w, h, h / 2, rgb("accent") if hot else rgb("glow"), max(1.5, 0.5 * px), 0.55 if hot else 0.35)
    img = glow.copy()
    if hot:
        body, tone = _shape(w, h, h / 2, rgb("accent") + (255,)), rgb("ink")
    else:
        body = _shape(w, h, h / 2, rgb("panel") + (235,), rgb("line") + (255,), max(1.0, 2 * u))
        tone = rgb("soft")
    img.alpha_composite(body, (m, m))
    spr, ox, oy = _text_sprite(text, "ui_bold", px, tone)
    _compose(img, spr, m + (w - tw) / 2, m + h / 2 + _cap("ui_bold", px) / 2, ox, oy)
    return img, m, w, h


@functools.lru_cache(maxsize=64)
def _card(w: int, h: int, tag: str, title: str, body: str, hot: bool, u: float) -> tuple[Any, int]:
    r = 18 * u
    edge = rgb("accent") if hot else rgb("line")
    glow, m = _glow(w, h, r, rgb("accent") if hot else rgb("glow"), max(2.0, 24 * u), 0.5 if hot else 0.35)
    img = glow.copy()
    img.alpha_composite(_shape(w, h, r, rgb("panel") + (248,), edge + (255,), max(1.0, 2 * u)), (m, m))
    pad = 30 * u
    x, y, inner = m + pad, m + pad, w - 2 * pad
    if tag:
        y = _lines(img, x, y, tag.upper(), "mono", _px(18 * u), rgb("accent"), inner, 1.3, _px(2 * u)) + 22 * u
    if title:
        y = _lines(img, x, y, title, "ui_bold", _px(40 * u), rgb("mint"), inner, 1.15) + 24 * u
    if body:
        _lines(img, x, y, body, "ui", _px(24 * u), rgb("soft"), inner, 1.35)
    return img, m


@functools.lru_cache(maxsize=32)
def _panel_chrome(w: int, h: int, title: str, u: float) -> tuple[Any, int, int]:
    r = 22 * u
    glow, m = _glow(w, h, r, rgb("glow"), max(2.0, 30 * u), 0.45)
    img = glow.copy()
    img.alpha_composite(_shape(w, h, r, rgb("panel") + (250,), rgb("line") + (255,), max(1.0, 2 * u)), (m, m))
    head = round(96 * u)
    d = max(3, round(12 * u))
    for i, tone in enumerate(("dim", "dim", "accent")):
        _compose(img, _shape(d, d, d / 2, rgb(tone) + (255,)), m + 30 * u + i * 22 * u, m + head / 2, 0, d / 2)
    if title:
        tpx = _px(30 * u)
        spr, ox, oy = _text_sprite(title, "ui_bold", tpx, rgb("mint"))
        _compose(img, spr, m + 30 * u + 66 * u + 14 * u, m + head / 2 + _cap("ui_bold", tpx) / 2, ox, oy)
    _compose(img, _shape(w, max(1, round(2 * u)), 0, rgb("line") + (255,)), m, m + head)
    return img, m, head


@functools.lru_cache(maxsize=16)
def _tick(d: int) -> Any:
    Image, _, ImageDraw, _, _ = _pil()
    S = 4
    D = d * S
    big = Image.new("RGBA", (D, D), rgb("accent") + (0,))
    draw = ImageDraw.Draw(big)
    draw.ellipse((0, 0, D - 1, D - 1), fill=rgb("accent") + (255,))
    points = [(px * D, py * D) for px, py in ((0.28, 0.52), (0.44, 0.68), (0.73, 0.36))]
    draw.line(points, fill=rgb("ink") + (255,), width=max(1, round(0.11 * D)), joint="curve")
    return big.resize((d, d), Image.Resampling.LANCZOS)


@functools.lru_cache(maxsize=32)
def _plate(title: str, subtitle: str, u: float) -> tuple[Any, int, int, int]:
    """A lower-third name plate: dark glass, an accent bar, a title and an optional subtitle."""
    tpx, spx = _px(40 * u), _px(26 * u)
    tw = font("ui_bold", tpx).getlength(title)
    sw = font("ui", spx).getlength(subtitle) if subtitle else 0.0
    pad, bar, inset = 26 * u, 6 * u, 18 * u
    text_x = inset + bar + 22 * u
    w = round(text_x + max(tw, sw) + pad + 8 * u)
    h = round(2 * pad + _cap("ui_bold", tpx) + (spx * 1.55 if subtitle else 0))
    r = 14 * u
    glow, m = _glow(w, h, r, rgb("ink"), max(2.0, 24 * u), 0.6)
    img = glow.copy()
    img.alpha_composite(_shape(w, h, r, rgb("panel") + (240,)), (m, m))
    img.alpha_composite(_shape(max(1, round(bar)), max(1, round(h - 2 * inset)), bar / 2, rgb("accent") + (255,)),
                        (round(m + inset), round(m + inset)))
    base = m + pad + _cap("ui_bold", tpx)
    spr, ox, oy = _text_sprite(title, "ui_bold", tpx, rgb("mint"))
    _compose(img, spr, m + text_x, base, ox, oy)
    if subtitle:
        spr, ox, oy = _text_sprite(subtitle, "ui", spx, rgb("soft"))
        _compose(img, spr, m + text_x, base + spx * 1.55, ox, oy)
    return img, m, w, h


_ARROW = ((0, 0), (0, 24.5), (5.6, 19.4), (9.6, 28.6), (13.4, 27.0), (9.5, 18.0), (17.2, 18.0))


@functools.lru_cache(maxsize=16)
def _pointer(height: int) -> tuple[Any, int]:
    """A mouse pointer with a soft shadow; its tip sits at (m, m) in the sprite."""
    Image, _, ImageDraw, ImageFilter, _ = _pil()
    S = 4
    s = height / 28.6
    m = int(0.5 * height) + 2
    W, H = math.ceil(17.2 * s) + 2 * m, height + 2 * m
    big = Image.new("RGBA", (W * S, H * S), (250, 252, 250, 0))
    points = [((m + x * s) * S, (m + y * s) * S) for x, y in _ARROW]
    ImageDraw.Draw(big).polygon(points, fill=(250, 252, 250, 255), outline=rgb("ink") + (255,),
                                width=max(1, round(1.4 * s * S)))
    arrow = big.resize((W, H), Image.Resampling.LANCZOS)
    shade = arrow.getchannel("A").filter(ImageFilter.GaussianBlur(max(1.0, 0.08 * height)))
    shadow = Image.new("RGBA", (W, H), rgb("ink") + (0,))
    shadow.putalpha(shade.point([int(v * 0.45) for v in range(256)]))
    off = max(1, round(0.07 * height))
    shadow = shadow.crop((-off, -off, W - off, H - off))
    shadow.alpha_composite(arrow)
    return shadow, m


@functools.lru_cache(maxsize=512)
def _ripple(r: float, fill_a: int, ring_a: int, width: float, tone: tuple) -> Any:
    """A click ripple; its centre is the middle of the sprite."""
    Image, _, ImageDraw, _, _ = _pil()
    S = 3
    D = math.ceil(2 * r + 2 * width + 4)
    big = Image.new("RGBA", (D * S, D * S), tone + (0,))
    c, R = D * S / 2, r * S
    ImageDraw.Draw(big).ellipse((c - R, c - R, c + R, c + R), fill=tone + (fill_a,), outline=tone + (ring_a,),
                                width=max(1, round(width * S)))
    return big.resize((D, D), Image.Resampling.LANCZOS)


@functools.lru_cache(maxsize=256)
def _link_sprite(ax: float, ay: float, bx: float, by: float, bend: float, width: float, tone: tuple,
                 steps: int) -> tuple[Any, int, int]:
    """The first ``steps`` of 64 pieces of a curve from a to b; returns it with its top-left corner."""
    Image, _, ImageDraw, _, _ = _pil()
    S = 3
    dx = bx - ax
    c1, c2 = (ax + dx * bend, ay), (bx - dx * bend, by)
    points = []
    for i in range(steps + 1):
        q = i / 64
        p = 1 - q
        points.append((p ** 3 * ax + 3 * p * p * q * c1[0] + 3 * p * q * q * c2[0] + q ** 3 * bx,
                       p ** 3 * ay + 3 * p * p * q * c1[1] + 3 * p * q * q * c2[1] + q ** 3 * by))
    pad = width * 2 + 2
    left, top = math.floor(min(x for x, _ in points) - pad), math.floor(min(y for _, y in points) - pad)
    right, bottom = math.ceil(max(x for x, _ in points) + pad), math.ceil(max(y for _, y in points) + pad)
    big = Image.new("RGBA", ((right - left) * S, (bottom - top) * S), tone + (0,))
    ImageDraw.Draw(big).line([((x - left) * S, (y - top) * S) for x, y in points], fill=tone + (255,),
                             width=max(1, round(width * S)), joint="curve")
    return big.resize((right - left, bottom - top), Image.Resampling.LANCZOS), left, top


@functools.lru_cache(maxsize=16)
def _hole(W: int, H: int, x: int, y: int, w: int, h: int, r: int) -> Any:
    """A full-frame mask, 255 everywhere except a rounded box (the part a callout keeps bright)."""
    Image, _, ImageDraw, _, _ = _pil()
    S = 3
    mask = Image.new("L", (W, H), 255)
    patch = Image.new("L", ((w + 4) * S, (h + 4) * S), 255)
    ImageDraw.Draw(patch).rounded_rectangle((2 * S, 2 * S, (w + 2) * S - 1, (h + 2) * S - 1), radius=r * S, fill=0)
    mask.paste(patch.resize((w + 4, h + 4), Image.Resampling.LANCZOS), (x - 2, y - 2))
    return mask


@functools.lru_cache(maxsize=32)
def _frame(kind: str, w: int, h: int, u: float, title: str = "") -> tuple[Any, int, tuple, float, bool, Any]:
    """What a picture sits in: a window, a phone, a plain shadowed card or nothing.

    Returns the canvas, its margin, the picture's rectangle inside it, the picture's corner radius,
    whether the picture's top corners are rounded, and an overlay drawn over the picture (or None).
    """
    Image = _pil()[0]
    if kind == "none":
        return Image.new("RGBA", (w, h), (0, 0, 0, 0)), 0, (0, 0, w, h), 0.0, True, None
    if kind == "plain":
        r = 14 * u
        glow, m = _glow(w, h, r, rgb("ink"), max(2.0, 28 * u), 0.75)
        return glow, m, (m, m, w, h), r, True, None
    if kind == "window":
        r = 16 * u
        glow, m = _glow(w, h, r, rgb("ink"), max(2.0, 28 * u), 0.75)
        canvas = glow.copy()
        canvas.alpha_composite(_shape(w, h, r, rgb("panel") + (255,)), (m, m))
        bar = round(44 * u)
        d = max(3, round(12 * u))
        for i, tone in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            _compose(canvas, _shape(d, d, d / 2, rgb(tone) + (255,)), m + 20 * u + i * 20 * u, m + bar / 2, 0, d / 2)
        if title:
            tpx = _px(16 * u)
            spr, ox, oy = _text_sprite(title, "mono", tpx, rgb("dim"))
            tw = font("mono", tpx).getlength(title)
            _compose(canvas, spr, m + (w - tw) / 2, m + bar / 2 + _cap("mono", tpx) / 2, ox, oy)
        s = max(1, round(1.5 * u))
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        overlay.alpha_composite(_shape(w, h, r, rgb("line") + (0,), rgb("line") + (255,), max(1.0, 1.5 * u)), (m, m))
        return canvas, m, (m + s, m + bar, w - 2 * s, h - bar - s), max(0.0, r - s), False, overlay
    r = 54 * u  # phone
    bezel = max(2, round(12 * u))
    glow, m = _glow(w, h, r, rgb("ink"), max(2.0, 28 * u), 0.75)
    canvas = glow.copy()
    canvas.alpha_composite(_shape(w, h, r, (14, 18, 16, 255), rgb("line") + (255,), max(1.0, 2 * u)), (m, m))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    iw, ih = max(2, round(120 * u)), max(2, round(34 * u))
    overlay.alpha_composite(_shape(iw, ih, ih / 2, (0, 0, 0, 255)), (round(m + w / 2 - iw / 2), round(m + bezel + 14 * u)))
    return canvas, m, (m + bezel, m + bezel, w - 2 * bezel, h - 2 * bezel), max(0.0, r - bezel), True, overlay


# --- living background ------------------------------------------------------------------------------

_BLOBS = (
    ("glow", 0.85, 1.0, (0.30, 0.38), 0.11, 0.0),
    ("accent", 0.28, 0.62, (0.74, 0.60), 0.13, 2.1),
    ("deep", 0.70, 1.15, (0.56, 0.18), 0.12, 4.2),
)


@functools.lru_cache(maxsize=32)
def _blob(tone: str, strength: float, d: int) -> Any:
    Image = _pil()[0]
    mask = Image.radial_gradient("L").point([round(((255 - v) / 255) ** 2 * strength * 255) for v in range(256)])
    img = Image.new("RGBA", (256, 256), rgb(tone) + (255,))
    img.putalpha(mask)
    return img.resize((d, d), Image.Resampling.BICUBIC)


@functools.lru_cache(maxsize=8)
def _vignette(sw: int, sh: int) -> Any:
    Image = _pil()[0]
    g = Image.radial_gradient("L").resize((sw, sh), Image.Resampling.BICUBIC)
    g = g.point([round(255 * (1 - 0.55 * (v / 255) ** 2)) for v in range(256)])
    return Image.merge("RGB", (g, g, g))


@functools.lru_cache(maxsize=4)
def _grain(W: int, H: int, i: int) -> Any:
    Image = _pil()[0]
    data = random.Random(1000 + i).randbytes(W * H)
    g = Image.frombytes("L", (W, H), data).point([128 + (v * 15 // 256) - 7 for v in range(256)])
    return Image.merge("RGB", (g, g, g))


@functools.lru_cache(maxsize=4)
def _grid(W: int, H: int, u: float) -> Any:
    Image, _, ImageDraw, _, _ = _pil()
    img = Image.new("RGBA", (W, H), rgb("line") + (0,))
    draw = ImageDraw.Draw(img)
    step = max(4, round(80 * u))
    tone = rgb("line") + (70,)
    for x in range(0, W, step):
        draw.line((x, 0, x, H), fill=tone, width=1)
    for y in range(0, H, step):
        draw.line((0, y, W, y), fill=tone, width=1)
    return img


# --- terminal text ----------------------------------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


def _clean(text: str) -> str:
    """Terminal output as it would look: colour codes gone, carriage returns overwriting the line."""
    lines = []
    for line in _ANSI.sub("", text).split("\n"):
        line = line.rstrip("\r")
        if "\r" in line:
            line = line.rsplit("\r", 1)[1]
        lines.append(line.expandtabs(4))
    return "\n".join(lines)


def _keys(tl: dict) -> list[float]:
    keys = tl.get("keys")
    if keys is not None:
        return list(keys)
    return [0.3 + k for k in char_times(tl["command"], 14)[:-1]]


def terminal_state(tl: dict, t: float) -> tuple[str, str]:
    """The command typed so far and the output shown so far, ``t`` seconds into a terminal timeline."""
    n = sum(1 for k in _keys(tl) if k <= t)
    out = "".join(o["text"] for o in tl.get("output", []) if o["at"] <= t)
    return tl["command"][:n], out


def _wrap_segments(segs: list[tuple[str, tuple]], cols: int) -> list[list[tuple[str, tuple]]]:
    rows: list[list[tuple[str, tuple]]] = []
    cur: list[tuple[str, tuple]] = []
    n = 0
    for text, tone in segs:
        while text:
            if n >= cols:
                rows.append(cur)
                cur, n = [], 0
            piece, text = text[:cols - n], text[cols - n:]
            cur.append((piece, tone))
            n += len(piece)
    rows.append(cur)
    return rows


# --- layer drawers ----------------------------------------------------------------------------------

def _draw_title(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    px = _px(layer.get("size", 96) * u)
    role = layer.get("font", "display")
    f = font(role, px)
    color = rgb(layer.get("color", "mint"))
    accent = rgb(layer.get("accent_color", "accent"))
    hot = {_bare(w) for w in layer.get("accent", [])}
    halo = float(layer.get("shadow", 0.55))
    lines = _wrap(layer["text"], f, layer.get("width", 1600) * u)
    lead = px * layer.get("leading", 1.12)
    cap = _cap(role, px)
    cx, cy = layer.get("x", 960) * u, layer.get("y", st.dh / 2) * u
    align = layer.get("align", "center")
    first = cy - ((len(lines) - 1) * lead - cap) / 2
    space = f.getlength(" ")
    words: list[tuple[str, float, float, float, int]] = []
    off = 0
    for li, line in enumerate(lines):
        parts = line.split(" ")
        widths = [f.getlength(p) for p in parts]
        total = sum(widths) + space * (len(parts) - 1)
        x = cx - total / 2 if align == "center" else cx if align == "left" else cx - total
        y = first + li * lead
        for p, w in zip(parts, widths):
            words.append((p, x, y, w, off))
            x += w + space
            off += len(p) + 1

    def tone(word: str) -> tuple:
        return accent if _bare(word) in hot else color

    style = layer.get("enter", "words")
    drift = _drift(st, layer, t)
    if style == "words":
        cfg = _spring_of(layer, "title")
        stagger = layer.get("stagger", 0.07)
        for i, (word, x, y, w, _off) in enumerate(words):
            s = _spring_at(local - i * stagger, cfg, st.fps)
            if s <= 0 or not word:
                continue
            spr, ox, oy = _text_sprite(word, role, px, tone(word), 0.0, halo)
            yy = y + 0.4 * px * (1 - s)
            _place(dest, spr, ox, oy, x, yy, x + w / 2, yy - cap / 2, drift, 0.0, 0.92 + 0.08 * s,
                   _clamp(1.3 * s) * fade)
        return
    if style == "type":
        times = char_times("\n".join(lines), layer.get("cps", 16), seed=index)
        shown = typed_count(times, local)
        caret = None
        for word, x, y, _w, off in words:
            n = shown - off
            if 0 <= n <= len(word):
                caret = (x + f.getlength(word[:n]), y)
            if n > 0 and word:
                spr, ox, oy = _text_sprite(word[:n], role, px, tone(word), 0.0, halo)
                _compose(dest, spr, x + drift, y, ox, oy, 1.0, fade)
        typing = local < times[-1]
        if caret and (typing or (layer.get("caret", True) and int(local * 2) % 2 == 0)):
            bar = _shape(max(2, round(0.08 * px)), round(1.15 * cap), 0, accent + (255,))
            _compose(dest, bar, caret[0] + 0.06 * px + drift, caret[1] - 1.075 * cap, 0, 0, 1.0, fade)
        return
    dx, dy, sc, op = _motion(st, layer, "title", t, local, fade)
    for word, x, y, _w, _off in words:
        if word:
            spr, ox, oy = _text_sprite(word, role, px, tone(word), 0.0, halo)
            _place(dest, spr, ox, oy, x, y, cx, cy, dx, dy, sc, op)


def _draw_label(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    role = layer.get("font", "mono")
    px = _px(layer.get("size", 22) * u)
    text = layer["text"].upper() if layer.get("upper", True) else layer["text"]
    track = _px(layer.get("tracking", 4) * u)
    spr, ox, oy = _text_sprite(text, role, px, rgb(layer.get("color", "accent")), track, float(layer.get("shadow", 0.5)))
    w = _text_width(font(role, px), text, track)
    cx, cy = layer.get("x", 960) * u, layer.get("y", 160) * u
    align = layer.get("align", "center")
    x = cx - w / 2 if align == "center" else cx if align == "left" else cx - w
    dx, dy, sc, op = _motion(st, layer, "label", t, local, fade)
    _place(dest, spr, ox, oy, x, cy + _cap(role, px) / 2, cx, cy, dx, dy, sc, op)


def _draw_chips(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    px = _px(layer.get("size", 34) * u)
    marked = {_bare(h) for h in layer.get("highlight", [])}
    chips = []
    for item in layer["items"]:
        text = item if isinstance(item, str) else str(item.get("text", ""))
        hot = _bare(text) in marked or (isinstance(item, dict) and bool(item.get("hot")))
        chips.append(_chip(text, px, hot, u))
    gap, row_gap = 0.55 * px, 0.6 * px
    max_w = layer.get("width", 1640) * u
    rows: list[tuple[list[int], float]] = []
    cur: list[int] = []
    cur_w = 0.0
    for i, (_img, _m, w, _h) in enumerate(chips):
        wider = w if not cur else cur_w + gap + w
        if cur and wider > max_w:
            rows.append((cur, cur_w))
            cur, cur_w = [i], float(w)
        else:
            cur.append(i)
            cur_w = wider
    if cur:
        rows.append((cur, cur_w))
    h = chips[0][3]
    cx, cy = layer.get("x", 960) * u, layer.get("y", st.dh / 2) * u
    top = cy - (len(rows) * h + (len(rows) - 1) * row_gap) / 2
    style = layer.get("enter", _ENTER["chips"])
    cfg = _spring_of(layer, "chips")
    stagger = layer.get("stagger", 0.08)
    drift = _drift(st, layer, t)
    for r, (members, row_w) in enumerate(rows):
        x = cx - row_w / 2
        y = top + r * (h + row_gap)
        for i in members:
            img, m, w, hh = chips[i]
            cl = local - i * stagger
            s = _spring_at(cl, cfg, st.fps)
            if s > 0:
                dx, dy, sc, op = _enter(style, s, cl)
                mx, my = x + w / 2, y + hh / 2
                _place(dest, img, m + w / 2, m + hh / 2, mx, my, mx, my, dx * u + drift, dy * u, sc, op * fade)
            x += w + gap


def _text_scale(layer: dict) -> float:
    """How much bigger than usual a layer draws its words (a vertical film asks for bigger ones)."""
    return float(layer.get("text_scale", 1.0))


def _draw_cards(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    bx, by, bw, bh = _box(layer, (160, 330, 1600, 420), u)
    items = [{"title": it} if isinstance(it, str) else it for it in layer["items"]]
    n = len(items)
    cols = max(1, int(min(layer.get("columns", 4), n)))
    rows = math.ceil(n / cols)
    gap = 32 * u
    cw, ch = round((bw - gap * (cols - 1)) / cols), round((bh - gap * (rows - 1)) / rows)
    style = layer.get("enter", _ENTER["cards"])
    cfg = _spring_of(layer, "cards")
    stagger = layer.get("stagger", 0.1)
    drift = _drift(st, layer, t)
    for i, item in enumerate(items):
        r, c = divmod(i, cols)
        cl = local - i * stagger
        s = _spring_at(cl, cfg, st.fps)
        if s <= 0:
            continue
        in_row = cols if r < rows - 1 else n - cols * (rows - 1)
        x = bx + (bw - (in_row * cw + (in_row - 1) * gap)) / 2 + c * (cw + gap)
        y = by + r * (ch + gap)
        img, m = _card(cw, ch, str(item.get("tag", "")), str(item.get("title", "")), str(item.get("body", "")),
                       bool(item.get("hot")), u * _text_scale(layer))
        dx, dy, sc, op = _enter(style, s, cl)
        mx, my = x + cw / 2, y + ch / 2
        _place(dest, img, m + cw / 2, m + ch / 2, mx, my, mx, my, dx * u + drift, dy * u, sc, op * fade)


def _draw_panel(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    x, y, w, h = _box(layer, (560, 190, 800, 700), u)
    w, h = round(w), round(h)
    u *= _text_scale(layer)  # the words, rows and chrome inside the box
    chrome, m, head = _panel_chrome(w, h, str(layer.get("title", "")), u)
    canvas = chrome.copy()
    cfg = _spring_of(layer, "panel")
    tick = round(30 * u)
    tpx, vpx = _px(26 * u), _px(24 * u)
    x0 = m + 34 * u
    rows = [{"text": r} if isinstance(r, str) else r for r in layer["rows"]]
    for i, row in enumerate(rows):
        rl = local - (0.3 + 0.14 * i)
        s = _spring_at(rl, cfg, st.fps)
        if s <= 0:
            continue
        op = _clamp(1.3 * s)
        top = m + head + 18 * u + i * 66 * u + 22 * u * (1 - s)
        mid = top + 33 * u
        if row.get("tick", True):
            ts = _spring_at(rl - 0.25, SPRINGS["pop"], st.fps)
            if ts > 0:
                spr = _tick(max(4, tick))
                _compose(canvas, spr, x0 + tick / 2, mid, spr.width / 2, spr.height / 2, ts, op)
        spr, ox, oy = _text_sprite(str(row.get("text", "")), "ui", tpx, rgb("mint"))
        _compose(canvas, spr, x0 + tick + 18 * u, mid + _cap("ui", tpx) / 2, ox, oy, 1.0, op)
        if row.get("value") not in (None, ""):
            value = str(row["value"])
            spr, ox, oy = _text_sprite(value, "mono", vpx, rgb("soft"))
            vw = font("mono", vpx).getlength(value)
            _compose(canvas, spr, m + w - 34 * u - vw, mid + _cap("mono", vpx) / 2, ox, oy, 1.0, op)
        if i < len(rows) - 1:
            _compose(canvas, _shape(w - 68 * u, max(1, round(2 * u)), 0, rgb("line") + (255,)), x0, top + 66 * u,
                     0, 0, 1.0, op)
    prog = layer.get("progress")
    if isinstance(prog, dict):
        a = prog.get("at", 0.6)
        b = prog.get("until", a + 1.2)
        p = ease_in_out((local - a) / (b - a) if b > a else 1.0) * prog.get("value", 1.0)
        bw, bh = round(w - 68 * u), max(2, round(10 * u))
        py = m + h - 54 * u
        _compose(canvas, _shape(bw, bh, bh / 2, rgb("line") + (255,)), x0, py)
        if p > 0:
            _compose(canvas, _shape(max(bh, round(bw * p)), bh, bh / 2, rgb("accent") + (255,)), x0, py)
        if prog.get("label"):
            lpx = _px(22 * u)
            spr, ox, oy = _text_sprite(str(prog["label"]), "ui", lpx, rgb("soft"))
            _compose(canvas, spr, x0, py - 14 * u, ox, oy)
            pct = f"{round(p * 100)}%"
            spr, ox, oy = _text_sprite(pct, "mono", lpx, rgb("accent"))
            _compose(canvas, spr, x0 + bw - font("mono", lpx).getlength(pct), py - 14 * u, ox, oy)
    dx, dy, sc, op = _motion(st, layer, "panel", t, local, fade)
    mx, my = x + w / 2, y + h / 2
    _place(dest, canvas, m + w / 2, m + h / 2, mx, my, mx, my, dx, dy, sc, op)


def _draw_counter(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    role = layer.get("font", "display")
    px = _px(layer.get("size", 160) * u)
    f = font(role, px)
    text = _counter_text(layer, counter_value(layer, t))
    final_w = f.getlength(_counter_text(layer, layer["to"]))
    cx, cy = layer.get("x", 960) * u, layer.get("y", st.dh / 2) * u
    base = cy + _cap(role, px) / 2
    dx, dy, sc, op = _motion(st, layer, "counter", t, local, fade)
    spr, ox, oy = _text_sprite(text, role, px, rgb(layer.get("color", "mint")), 0.0, float(layer.get("shadow", 0.4)))
    _place(dest, spr, ox, oy, cx + final_w / 2 - f.getlength(text), base, cx, cy, dx, dy, sc, op)
    if layer.get("label"):
        lpx = _px(30 * u)
        label = str(layer["label"])
        spr, ox, oy = _text_sprite(label, "ui", lpx, rgb("soft"))
        lw = font("ui", lpx).getlength(label)
        _place(dest, spr, ox, oy, cx - lw / 2, base + 0.5 * px + _cap("ui", lpx), cx, cy, dx, dy, sc, op)


def _draw_callout(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    Image = _pil()[0]
    u = st.u
    pad = layer.get("pad", 10)
    x, y, w, h = _box(layer, None, u)
    if layer.get("map"):  # the box is in recorded page pixels; place it where the recording sits
        to_px = _mapper(layer, u)
        bx, by, bw, bh = layer["box"]
        (x, y), (x1, y1) = to_px(bx, by), to_px(bx + bw, by + bh)
        w, h = x1 - x, y1 - y
    x, y, w, h = x - pad * u, y - pad * u, w + 2 * pad * u, h + 2 * pad * u
    r = layer.get("radius", 16) * u
    accent = rgb(layer.get("accent_color", "accent"))
    level = layer.get("spotlight", 0.55) * fade * ease_out(local / 0.4)
    if level > 0.003:
        hole = _hole(st.W, st.H, round(x), round(y), max(1, round(w)), max(1, round(h)), round(r))
        shade = Image.new("RGBA", (st.W, st.H), rgb("ink") + (255,))
        shade.putalpha(hole.point(_opacity_lut(round(level * 255))))
        dest.alpha_composite(shade)
    s = _spring_at(local, _spring_of(layer, "callout"), st.fps)
    if s > 0:
        ring = _shape(round(w), round(h), r, accent + (0,), accent + (255,), 3.5 * u)
        _compose(dest, ring, x + w / 2, y + h / 2, ring.width / 2, ring.height / 2, 1.06 - 0.06 * s,
                 _clamp(1.3 * s) * fade)
    if layer.get("label"):
        cl = local - 0.12
        ls = _spring_at(cl, SPRINGS["pill"], st.fps)
        if ls > 0:
            lu = u * _text_scale(layer)
            img, m, cw, ch = _chip(str(layer["label"]), _px(26 * lu), True, lu)
            ly = y - 12 * u - ch if y / u >= 80 else y + h + 12 * u
            dx, dy, sc, op = _enter("pop-rise", ls, cl)
            mx, my = x + cw / 2, ly + ch / 2
            _place(dest, img, m + cw / 2, m + ch / 2, mx, my, mx, my, dx * u, dy * u, sc, op * fade)


def _mapper(layer: dict, u: float) -> Any:
    """Turns recorded page pixels into frame pixels: through ``map`` when given, else design pixels."""
    mp = layer.get("map")
    if not mp:
        return lambda x, y: (x * u, y * u)
    (sw, sh), (bx, by, bw, bh) = mp["size"], mp["box"]
    return lambda x, y: ((bx + x * bw / sw) * u, (by + y * bh / sh) * u)


def _path_at(moves: list[dict], t: float) -> tuple[float, float]:
    if t <= moves[0]["t"]:
        return moves[0]["x"], moves[0]["y"]
    for a, b in zip(moves, moves[1:]):
        if t < b["t"]:
            span = b["t"] - a["t"]
            p = (t - a["t"]) / span if span > 0 else 1.0
            if span >= 0.25:
                p = ease_in_out(p)  # a long glide eases in and out; recorded steps stay as they were
            return a["x"] + (b["x"] - a["x"]) * p, a["y"] + (b["y"] - a["y"]) * p
    return moves[-1]["x"], moves[-1]["y"]


def _draw_cursor(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    to_px = _mapper(layer, u)
    tone = rgb(layer.get("color", "accent"))
    press = 1.0
    for click in layer.get("clicks", []):
        dt = local - click["t"]
        if 0 <= dt < 0.6:
            p = dt / 0.6
            r = round(max(4 * u, 70 * u * ease_out(p)) * 2) / 2
            spr = _ripple(r, int(60 * (1 - p)) // 4 * 4, int(230 * (1 - p)) // 4 * 4, _px(3 * u), tone)
            cx, cy = to_px(click["x"], click["y"])
            _compose(dest, spr, cx, cy, spr.width / 2, spr.height / 2, 1.0, fade)
        if 0 <= dt < 0.18:
            press = 0.85 + 0.15 * ease_out(dt / 0.18)
    x, y = to_px(*_path_at(layer["moves"], local))
    spr, m = _pointer(max(8, round(layer.get("size", 36) * u)))
    _compose(dest, spr, x, y, m, m, press, fade)


def _draw_lower_third(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    img, m, _w, h = _plate(str(layer["title"]), str(layer.get("subtitle", "")), u * _text_scale(layer))
    x, y = layer.get("x", 120) * u, layer.get("y", st.dh - 200) * u
    dx, dy, sc, op = _motion(st, layer, "lower_third", t, local, fade)
    _place(dest, img, m, m, x, y, x, y + h / 2, dx, dy, sc, op)


def _draw_terminal(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    Image, _, ImageDraw, _, _ = _pil()
    u = st.u
    x, y, w, h = _box(layer, (210, 140, 1500, 800), u)
    w, h = round(w), round(h)
    u *= _text_scale(layer)  # the window chrome and the typed text
    tl = layer["timeline"]
    typed, out = terminal_state(tl, local)
    keys = _keys(tl)
    enter = tl.get("enter", (keys[-1] if keys else 0.3) + 0.25)
    outs = tl.get("output", [])
    last_out = max((o["at"] for o in outs), default=None)
    done = local >= enter and local >= (last_out + 0.35 if last_out is not None else enter + 0.2)
    blink = int(local * 2) % 2 == 0
    if not keys or local < keys[0]:
        caret = blink
    elif local < enter:
        caret = True
    else:
        caret = blink if done else False
    title = str(layer.get("title", "Terminal"))
    key = ("term", index, len(typed), len(out), caret, done, w, h)
    hit = st.cache.get(key)
    if hit is None:
        if len(st.cache) > 48:
            st.cache.clear()
        frame_img, m, (rx, ry, rw, rh), radius, top_round, overlay = _frame("window", w, h, u, title)
        content = Image.new("RGBA", (rw, rh), (8, 17, 12, 255))
        draw = ImageDraw.Draw(content)
        tpx = _px(28 * u)
        f = font("mono", tpx)
        cap = _cap("mono", tpx)
        line_h = 1.45 * tpx
        pad = 34 * u
        char_w = f.getlength("M") or tpx * 0.6
        cols = max(8, int((rw - 2 * pad) // char_w))
        max_rows = max(1, int((rh - 2 * pad) // line_h))
        accent, mint, soft = rgb("accent"), rgb("mint"), rgb("soft")
        logical = [[("$ ", accent), (typed, mint)]]
        if local >= enter:
            body = _clean(out).split("\n")
            if body and body[-1] == "":
                body = body[:-1]
            logical += [[(b, soft)] for b in body]
            if done:
                logical.append([("$ ", accent)])
        rows = [row for segs in logical for row in _wrap_segments(segs, cols)][-max_rows:]
        for k, row in enumerate(rows):
            base = pad + cap + k * line_h
            cx = pad
            for piece, tone in row:
                draw.text((cx, base), piece, font=f, fill=tone + (255,), anchor="ls")
                cx += f.getlength(piece)
            if caret and k == len(rows) - 1:
                draw.rectangle((cx + 0.1 * char_w, base - cap - 0.12 * cap, cx + 0.9 * char_w, base + 0.18 * cap),
                               fill=accent + (220,))
        canvas = frame_img.copy()
        canvas.paste(content, (rx, ry), _round_mask(rw, rh, radius, top_round))
        if overlay is not None:
            canvas.alpha_composite(overlay)
        hit = st.cache[key] = (canvas, m)
    canvas, m = hit
    dx, dy, sc, op = _motion(st, layer, "terminal", t, local, fade)
    mx, my = x + w / 2, y + h / 2
    _place(dest, canvas, m + w / 2, m + h / 2, mx, my, mx, my, dx, dy, sc, op)


def _draw_media(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    u = st.u
    x, y, w, h = _box(layer, (160, 90, 1600, 900), u)
    w, h = round(w), round(h)
    kind = layer.get("frame", "window")
    frame_img, m, (rx, ry, rw, rh), radius, top_round, overlay = _frame(kind, w, h, u, str(layer.get("title", "")))
    span = layer.get("until", st.seconds) - layer.get("at", 0)
    if layer["kind"] == "video":
        start = layer.get("start", 0)
        speed = layer.get("speed")
        if speed is None:
            dur = _duration(layer["file"])
            speed = _clamp((dur - start) / span, 0.5, 1.0) if dur and span > 0 else 1.0
        content = st.video(index, layer["file"], (rw, rh), start, speed).frame(round(local * st.fps))
        if layer.get("push"):
            content = _cover(content, (rw, rh), 1 + layer["push"] * _clamp(local / span))
    else:
        img = st.image(layer["file"])
        scroll = layer.get("scroll")
        iw, ih = img.size
        view = rh / (rw / iw)
        if isinstance(scroll, dict) and ih - view > 0:
            a, b = scroll.get("at", 0.0), scroll.get("until", span)
            p = ease_in_out((local - a) / (b - a)) if b > a else 1.0
            f0, f1 = scroll.get("from", 0.0), scroll.get("to", 1.0)
            off = (ih - view) * (f0 + (f1 - f0) * p)
            content = img.resize((rw, rh), _pil()[0].Resampling.BICUBIC, box=(0, off, iw, off + view))
        else:
            content = _cover(img, (rw, rh), 1 + layer.get("push", 0.03) * _clamp(local / span) if span > 0 else 1.0,
                             layer.get("focus", (0.5, 0.5)))
    if layer.get("dim"):
        content = _dim(content, layer["dim"])
    canvas = frame_img.copy()
    if kind == "none" and content.mode == "RGBA":
        canvas.alpha_composite(content, (rx, ry))
    else:
        canvas.paste(_opaque(content, rgb("ink")), (rx, ry), _round_mask(rw, rh, radius, top_round))
    if overlay is not None:
        canvas.alpha_composite(overlay)
    dx, dy, sc, op = _motion(st, layer, layer["kind"], t, local, fade)
    mx, my = x + w / 2, y + h / 2
    _place(dest, canvas, m + w / 2, m + h / 2, mx, my, mx, my, dx, dy, sc, op)


def _draw_wipe(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    """A graphic wipe: an ink panel with an accent edge sweeping across the frame."""
    dur = layer.get("duration", 0.7)
    mode = layer.get("mode", "through")
    direction = layer.get("direction", "right")
    across = direction in ("right", "left")
    L = st.W if across else st.H
    band = 0.14 * L
    full = L + band
    if mode == "through":
        head = ease_in_out(local / (dur / 2)) * full
        tail = ease_in_out((local - dur / 2) / (dur / 2)) * full
    elif mode == "cover":
        head, tail = ease_in_out(local / dur) * full, 0.0
    else:
        head, tail = full, ease_in_out(local / dur) * full
    spans = (((tail, head - band), rgb(layer.get("color", "ink"))),
             ((max(tail, head - band), head), rgb(layer.get("accent_color", "accent"))))
    for (a, b), tone in spans:
        a, b = round(_clamp(a, 0, L)), round(_clamp(b, 0, L))
        if b <= a:
            continue
        if direction in ("left", "up"):
            a, b = L - b, L - a
        box = (a, 0, b, st.H) if across else (0, a, st.W, b)
        dest.paste(tone + (255,), box)


def _draw_link(st: _State, layer: dict, dest: Any, t: float, local: float, fade: float, index: int) -> None:
    """A curved line drawing itself from one point to another, with a dot at each end."""
    u = st.u
    dur = layer.get("duration", 0.7)
    tone = rgb(layer.get("color", "accent"))
    ax, ay = layer["from"][0] * u, layer["from"][1] * u
    bx, by = layer["to"][0] * u, layer["to"][1] * u
    steps = round(ease_in_out(local / dur) * 64)
    if steps > 0:
        img, left, top = _link_sprite(round(ax, 1), round(ay, 1), round(bx, 1), round(by, 1),
                                      float(layer.get("bend", 0.5)), _px(max(1.0, layer.get("width", 4) * u)), tone,
                                      steps)
        _compose(dest, img, left, top, 0, 0, 1.0, fade)
    d = max(3, round(14 * u))
    dot = _shape(d, d, d / 2, tone + (255,))
    for start, (px, py) in ((0.0, (ax, ay)), (dur, (bx, by))):
        s = _spring_at(local - start, SPRINGS["pop"], st.fps)
        if s > 0:
            _compose(dest, dot, px, py, d / 2, d / 2, s, fade)


_DRAW = {
    "title": _draw_title, "label": _draw_label, "chips": _draw_chips, "cards": _draw_cards, "panel": _draw_panel,
    "counter": _draw_counter, "callout": _draw_callout, "cursor": _draw_cursor, "lower_third": _draw_lower_third,
    "terminal": _draw_terminal, "video": _draw_media, "image": _draw_media, "wipe": _draw_wipe, "link": _draw_link,
}


# --- video sources ----------------------------------------------------------------------------------

@functools.lru_cache(maxsize=64)
def _duration(path: str) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        run = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True, timeout=60, check=False)
        return float(run.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _video_size(path: str) -> tuple[int, int] | None:
    try:
        done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=width,height", "-of", "csv=p=0", str(path)],
                              capture_output=True, text=True, timeout=30)
        w, h = done.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


class _VideoSource:
    """Frames of a clip, read in order from one FFmpeg process, scaled and cropped to fill ``size``."""

    def __init__(self, path: str, size: tuple[int, int], fps: float, start: float = 0.0, speed: float = 1.0) -> None:
        self.path, self.size, self.fps, self.start, self.speed = str(path), tuple(size), fps, start, speed
        self.proc: subprocess.Popen | None = None
        self.next = 0
        self.last_n = -1
        self.last: Any = None
        self.ended = False

    def _open(self, n: int) -> None:
        self.close()
        W, H = self.size
        at = self.start + n / self.fps * self.speed
        vf = (f"setpts=(PTS-STARTPTS)/{self.speed:g},fps={self.fps:g},"
              f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=rgb24")
        self.proc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{at:.3f}", "-i", self.path, "-an", "-vf", vf,
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self.next, self.ended = n, False

    def frame(self, n: int) -> Any:
        Image = _pil()[0]
        n = max(0, n)
        if n == self.last_n and self.last is not None:
            return self.last
        if self.ended and n > self.last_n and self.last is not None:
            return self.last
        if self.proc is None or n < self.next or n > self.next + 2 * self.fps:
            self._open(n)
        W, H = self.size
        need = W * H * 3
        img = None
        assert self.proc is not None and self.proc.stdout is not None
        while self.next <= n:
            buf = self.proc.stdout.read(need)
            if len(buf) < need:
                self.ended = True
                break
            if self.next == n:
                img = Image.frombytes("RGB", (W, H), buf)
            self.next += 1
        if img is None:
            img = self.last if self.last is not None else self._fallback()
        self.last, self.last_n = img, n
        return img

    def _fallback(self) -> Any:
        """The clip's last frame when nothing could be read where asked, or a dark frame."""
        Image = _pil()[0]
        W, H = self.size
        dur = _duration(self.path)
        if dur:
            try:
                run = subprocess.run(
                    ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{max(0.0, dur - 0.2):.3f}", "-i", self.path, "-an",
                     "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                     "format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                    capture_output=True, timeout=60, check=False)
                if len(run.stdout) >= W * H * 3:
                    return Image.frombytes("RGB", (W, H), run.stdout[:W * H * 3])
            except (OSError, subprocess.TimeoutExpired):
                pass
        return Image.new("RGB", (W, H), rgb("ink"))

    def close(self) -> None:
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.kill()
            if self.proc.stdout is not None:
                self.proc.stdout.close()
            self.proc.wait()
            self.proc = None


# --- scenes -----------------------------------------------------------------------------------------

class _State:
    """One scene being drawn: its size, open clips, loaded pictures and reusable pieces."""

    def __init__(self, scene: dict) -> None:
        self.W, self.H = scene["size"]
        self.u = self.W / 1920
        self.dh = 1920 * self.H / self.W
        self.fps = scene["fps"]
        self.seconds = scene["seconds"]
        self.base = scene["base"]
        self.layers = scene["layers"]
        self.videos: dict[Any, _VideoSource] = {}
        self.images: dict[str, Any] = {}
        self.cache: dict[tuple, Any] = {}

    def video(self, key: Any, path: str, size: tuple[int, int], start: float, speed: float) -> _VideoSource:
        src = self.videos.get(key)
        if src is None or src.size != tuple(size) or src.path != str(path):
            if src is not None:
                src.close()
            src = self.videos[key] = _VideoSource(path, tuple(size), self.fps, start, speed)
        return src

    def image(self, path: str) -> Any:
        img = self.images.get(path)
        if img is None:
            Image = _pil()[0]
            with Image.open(path) as im:
                im.load()
                clear = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
                img = im.convert("RGBA" if clear else "RGB")
            self.images[path] = img
        return img

    def _living(self, t: float) -> Any:
        Image, ImageChops, _, _, _ = _pil()
        b = self.base
        sw = 192
        sh = max(2, round(192 * self.H / self.W))
        small = Image.new("RGBA", (sw, sh), rgb(b.get("color", "ink")) + (255,))
        pace, seed = b.get("speed", 1.0), b.get("seed", 0)
        for tone, strength, size, (hx, hy), speed, phase in _BLOBS:
            d = max(2, round(size * sw))
            a = t * pace * speed * 3 + phase + seed
            x = sw * (hx + 0.16 * math.sin(a))
            y = sh * (hy + 0.2 * math.cos(0.83 * a + 1.3))
            _compose(small, _blob(tone, strength, d), x, y, d / 2, d / 2, smooth=True)
        pic = ImageChops.multiply(small.convert("RGB"), _vignette(sw, sh))
        pic = pic.resize((self.W, self.H), Image.Resampling.BICUBIC)
        if b.get("grid"):
            pic = Image.alpha_composite(pic.convert("RGBA"), _grid(self.W, self.H, self.u)).convert("RGB")
        pic = ImageChops.add(pic, _grain(self.W, self.H, int(t * 12) % 4), 1.0, -128)
        return pic.convert("RGBA")

    def _base(self, t: float) -> Any:
        Image = _pil()[0]
        b = self.base
        kind = b["kind"]
        size = (self.W, self.H)
        if kind == "none":
            return Image.new("RGBA", size, (0, 0, 0, 0))
        if kind == "color":
            return Image.new("RGBA", size, rgb(b.get("color", "ink")) + (255,))
        if kind == "living":
            return self._living(t)
        if kind == "video":
            start = b.get("start", 0)
            speed = b.get("speed")
            if speed is None:
                dur = _duration(b["file"])
                speed = _clamp((dur - start) / self.seconds, 0.5, 1.0) if dur else 1.0
            pic = self.video("base", b["file"], size, start, speed).frame(round(t * self.fps))
            if b.get("push"):
                pic = _cover(pic, size, 1 + b["push"] * _clamp(t / self.seconds))
        else:
            img = _opaque(self.image(b["file"]), rgb("ink"))
            pan = b.get("pan")
            if pan:
                p = ease_in_out(t / self.seconds)
                (fx0, fy0), (fx1, fy1) = pan
                focus: Any = (fx0 + (fx1 - fx0) * p, fy0 + (fy1 - fy0) * p)
            else:
                focus = b.get("focus", (0.5, 0.5))
            pic = _cover(img, size, 1 + b.get("push", 0.06) * _clamp(t / self.seconds), focus)
        if b.get("dim"):
            pic = _dim(pic, b["dim"])
        return pic.convert("RGBA")

    def draw(self, t: float) -> Any:
        dest = self._base(t)
        for i, layer in enumerate(self.layers):
            life = _life(layer, t)
            if life is not None:
                _DRAW[layer["kind"]](self, layer, dest, t, life[0], life[1], i)
        return dest

    def close(self) -> None:
        for src in self.videos.values():
            src.close()
        self.videos.clear()


def _file(where: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MotionError(f"{where}: file must be a path")
    path = Path(value).expanduser()
    if not path.is_file():
        raise MotionError(f"{where}: file not found: {value}")
    return str(path.resolve())


def _point(v: Any) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(_number(n) for n in v)


def _check_colors(where: str, obj: dict) -> None:
    for key, value in obj.items():
        if key.endswith("color"):
            try:
                rgb(value)
            except MotionError as exc:
                raise MotionError(f"{where}: {key}: {exc}") from None


def _check_base(base: Any) -> dict:
    if not isinstance(base, dict):
        raise MotionError("base must be an object with a kind")
    kind = base.get("kind", "none")
    if kind not in BASES:
        raise MotionError(f"unknown base kind {kind!r}; known base kinds: {', '.join(BASES)}")
    out = dict(base, kind=kind)
    if kind in ("video", "image"):
        if "file" not in out:
            raise MotionError(f"a {kind} base needs a file")
        out["file"] = _file("the base", out["file"])
    for key in ("start", "speed", "dim", "push", "seed"):
        if key in out and not _number(out[key]):
            raise MotionError(f"the base: {key} must be a number")
    if "speed" in out and out["speed"] <= 0:
        raise MotionError("the base: speed must be above 0")
    _check_colors("the base", out)
    if "focus" in out and not _point(out["focus"]):
        raise MotionError("the base: focus must be two numbers from 0 to 1")
    if "pan" in out and not (isinstance(out["pan"], (list, tuple)) and len(out["pan"]) == 2
                             and all(_point(p) for p in out["pan"])):
        raise MotionError("the base: pan must be two points, like [[0.3, 0.5], [0.7, 0.5]]")
    return out


def _check_box(where: str, box: Any) -> None:
    if not (isinstance(box, (list, tuple)) and len(box) == 4 and all(_number(v) for v in box)
            and box[2] > 0 and box[3] > 0):
        raise MotionError(f"{where}: box must be [x, y, width, height] with a width and height above 0")


def _check_timeline(where: str, tl: Any) -> None:
    if not isinstance(tl, dict) or not isinstance(tl.get("command"), str):
        raise MotionError(f"{where}: timeline needs a command")
    keys = tl.get("keys")
    if keys is not None and not (isinstance(keys, list) and all(_number(k) for k in keys)):
        raise MotionError(f"{where}: timeline keys must be a list of times")
    output = tl.get("output", [])
    if not (isinstance(output, list) and all(isinstance(o, dict) and _number(o.get("at"))
                                             and isinstance(o.get("text"), str) for o in output)):
        raise MotionError(f"{where}: timeline output must be a list of {{at, text}}")
    if "enter" in tl and not _number(tl["enter"]):
        raise MotionError(f"{where}: timeline enter must be a time")


def _check_marks(where: str, name: str, marks: Any, *, sorted_times: bool, need: bool) -> None:
    if not isinstance(marks, list) or (need and not marks) or not all(
            isinstance(mk, dict) and all(_number(mk.get(k)) for k in ("t", "x", "y")) for mk in marks):
        raise MotionError(f"{where}: {name} must be a list of {{t, x, y}}")
    if sorted_times and any(b["t"] < a["t"] for a, b in zip(marks, marks[1:])):
        raise MotionError(f"{where}: {name} must be in time order")


def _check_layer(i: int, layer: Any) -> dict:
    if not isinstance(layer, dict):
        raise MotionError(f"layer {i} must be an object with a kind")
    kind = layer.get("kind")
    if kind not in KINDS:
        raise MotionError(f"layer {i} has an unknown kind {kind!r}; known kinds: {', '.join(KINDS)}")
    where = f"layer {i} ({kind})"
    out = {k: _read_number(v) if k in _NUMBERS or k in ("to", "from") else v for k, v in layer.items()}
    for field in _REQUIRED[kind]:
        if field not in out:
            raise MotionError(f"{where} needs {field!r}")
    for key in _NUMBERS:
        if key in out and not _number(out[key]):
            raise MotionError(f"{where}: {key} must be a number")
    if out.get("at", 0) < 0:
        raise MotionError(f"{where}: at must be 0 or later")
    if "until" in out and out["until"] <= out.get("at", 0):
        raise MotionError(f"{where}: until must come after at")
    if "speed" in out and out["speed"] <= 0:
        raise MotionError(f"{where}: speed must be above 0")
    if "enter" in out:
        allowed = ENTERS + (("words", "type") if kind == "title" else ())
        if out["enter"] not in allowed:
            raise MotionError(f"{where}: enter must be one of: {', '.join(allowed)}")
    if "spring" in out:
        sp = out["spring"]
        ok = sp in SPRINGS if isinstance(sp, str) else (
            isinstance(sp, dict) and bool(sp) and all(k in ("mass", "stiffness", "damping") and _number(v) and v > 0
                                                      for k, v in sp.items()))
        if not ok:
            raise MotionError(f"{where}: spring must be one of {', '.join(SPRINGS)} or {{mass, stiffness, damping}}")
    if "file" in out:
        out["file"] = _file(where, out["file"])
    if "box" in out:
        _check_box(where, out["box"])
    if "frame" in out and out["frame"] not in FRAMES:
        raise MotionError(f"{where}: frame must be one of: {', '.join(FRAMES)}")
    _check_colors(where, out)
    for key in ("text", "title", "subtitle", "label", "font"):
        if key in out and not isinstance(out[key], str):
            raise MotionError(f"{where}: {key} must be text")
    for key in ("accent", "highlight"):
        if key in out and not (isinstance(out[key], list) and all(isinstance(w, str) for w in out[key])):
            raise MotionError(f"{where}: {key} must be a list of words")
    if kind == "counter":
        for key in ("to", "from"):
            if key in out and not _number(out[key]):
                raise MotionError(f"{where}: {key} must be a number")
    if kind == "terminal":
        _check_timeline(where, out["timeline"])
    if kind == "cursor":
        _check_marks(where, "moves", out["moves"], sorted_times=True, need=True)
        if "clicks" in out:
            _check_marks(where, "clicks", out["clicks"], sorted_times=False, need=False)
    if kind in ("chips", "cards"):
        items = out["items"]
        if not (isinstance(items, list) and items and all(isinstance(it, (str, dict)) for it in items)):
            raise MotionError(f"{where}: items must be a list of text or objects")
    if kind == "panel":
        rows = out["rows"]
        if not (isinstance(rows, list) and rows and all(isinstance(r, (str, dict)) for r in rows)):
            raise MotionError(f"{where}: rows must be a list of text or objects")
    if kind == "link":
        for key in ("from", "to"):
            if not _point(out[key]):
                raise MotionError(f"{where}: {key} must be a point [x, y]")
    if "map" in out:
        mp = out["map"]
        if not (isinstance(mp, dict) and _point(mp.get("size")) and min(mp["size"]) > 0):
            raise MotionError(f"{where}: map needs the recorded size [width, height] and a box")
        _check_box(where, mp.get("box"))
    if "scroll" in out:
        sc = out["scroll"]
        if not (isinstance(sc, dict) and all(_number(v) for v in sc.values())):
            raise MotionError(f"{where}: scroll must be an object of numbers: at, until, from, to")
    if kind == "wipe":
        if out.get("mode", "through") not in WIPE_MODES:
            raise MotionError(f"{where}: mode must be one of: {', '.join(WIPE_MODES)}")
        if out.get("direction", "right") not in WIPE_DIRECTIONS:
            raise MotionError(f"{where}: direction must be one of: {', '.join(WIPE_DIRECTIONS)}")
    return out


def check_scene(scene: Any) -> dict:
    """A checked copy of a scene, with defaults filled in and file paths made absolute."""
    if not isinstance(scene, dict):
        raise MotionError("a scene must be an object with size, fps, seconds and layers")
    out = dict(scene)
    size = out.get("size", [1920, 1080])
    if not (isinstance(size, (list, tuple)) and len(size) == 2 and all(
            isinstance(v, int) and not isinstance(v, bool) and v >= 16 and v % 2 == 0 for v in size)):
        raise MotionError("size must be two even whole numbers of at least 16, like [1920, 1080]")
    out["size"] = [int(size[0]), int(size[1])]
    fps = out.get("fps", 30)
    if not _number(fps) or not 0 < fps <= 120:
        raise MotionError("fps must be a number above 0 and at most 120")
    out["fps"] = fps
    seconds = out.get("seconds")
    if not _number(seconds) or seconds <= 0:
        raise MotionError("seconds must be a number above 0")
    out["base"] = _check_base(out.get("base") or {"kind": "none"})
    layers = out.get("layers", [])
    if not isinstance(layers, list):
        raise MotionError("layers must be a list")
    out["layers"] = [_check_layer(i, layer) for i, layer in enumerate(layers)]
    return out


def frame(scene: dict, t: float) -> Any:
    """One frame of a scene at ``t`` seconds, as a Pillow RGBA image."""
    scene = check_scene(scene)
    _pil()
    st = _State(scene)
    try:
        return st.draw(t)
    finally:
        st.close()


_WHOOSH_ENTERS = ("left", "right", "rise", "drop", "zoom")


def events(scene: dict) -> list[tuple[float, str]]:
    """The moments in a scene that deserve a sound, as (seconds, kind), in time order.

    Typed characters tick, cursor clicks click, items that spring in pop, a title lands with a hit, and a wipe,
    a lower third or a picture sliding in whooshes. The kinds are the ones the sound kit makes.
    """
    scene = check_scene(scene)
    out: list[tuple[float, str]] = []
    for index, layer in enumerate(scene["layers"]):
        if layer.get("quiet"):
            continue
        kind = layer["kind"]
        at = layer.get("at", 0.0)
        enter = layer.get("enter", _ENTER[kind])
        if kind == "title":
            if enter == "type":
                text = layer["text"]
                times = char_times(text, layer.get("cps", 16), seed=index)[:-1]
                out += [(at + k, "tick") for k, ch in zip(times, text) if not ch.isspace()]
            else:
                out.append((at, "hit"))
        elif kind in ("chips", "cards"):
            stagger = layer.get("stagger", 0.08 if kind == "chips" else 0.1)
            out += [(at + i * stagger, "pop") for i in range(len(layer["items"]))]
        elif kind in ("label", "callout", "panel"):
            out.append((at, "pop"))
        elif kind == "counter":
            out.append((at + layer.get("duration", 1.2), "pop"))
        elif kind == "cursor":
            out += [(at + c["t"], "click") for c in layer.get("clicks", [])]
        elif kind == "terminal":
            tl = layer["timeline"]
            out += [(at + k, "tick") for k in _keys(tl)]
            out += [(at + o["at"], "pop") for o in tl.get("output", []) if o["text"].strip()]
        elif kind in ("wipe", "lower_third") or (kind in ("video", "image") and enter in _WHOOSH_ENTERS):
            out.append((at, "whoosh"))
        elif kind == "link":
            out.append((at, "tick"))
    return sorted((round(t, 3), k) for t, k in out if 0 <= t < scene["seconds"])


# --- rendering --------------------------------------------------------------------------------------

def _last_line(err: Any) -> str:
    err.seek(0)
    lines = err.read().decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "no message"


def render(scene: dict, out: Path, *, renderer: str = "builtin", table: Path | None = None,
           timeout: float | None = None) -> Path:
    """Render a scene to a video file. A scene with no base becomes a see-through .mov overlay."""
    scene = check_scene(scene)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if renderer != "builtin":
        return _render_outside(scene, out, renderer, table, timeout)
    if shutil.which("ffmpeg") is None:
        raise MotionError("FFmpeg is not installed; install it and make sure ffmpeg is on PATH")
    _pil()
    W, H = scene["size"]
    fps = scene["fps"]
    clear = scene["base"]["kind"] == "none"
    if clear and out.suffix.lower() != ".mov":
        raise MotionError("a scene with no base is see-through; write it to a .mov file, or give it a base")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba" if clear else "rgb24",
           "-s", f"{W}x{H}", "-framerate", f"{fps:g}", "-i", "-"]
    if clear:
        cmd += ["-c:v", "png", "-pix_fmt", "rgba"]
    else:
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264",
                "-preset", "medium", "-crf", "17", "-colorspace", "bt709", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-movflags", "+faststart"]
    cmd.append(str(out))
    frames = max(1, round(scene["seconds"] * fps))
    deadline = time.monotonic() + timeout if timeout else None
    st = _State(scene)
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
        assert proc.stdin is not None
        try:
            for i in range(frames):
                if deadline is not None and time.monotonic() > deadline:
                    raise MotionError(f"the motion render took longer than {timeout:g} s and was stopped")
                img = st.draw(i / fps)
                proc.stdin.write((img if clear else img.convert("RGB")).tobytes())
            proc.stdin.close()
            wait = max(1.0, deadline - time.monotonic()) if deadline is not None else None
            code = proc.wait(timeout=wait)
        except subprocess.TimeoutExpired as exc:
            raise MotionError(f"FFmpeg did not finish {out.name} in time") from exc
        except OSError as exc:  # a broken pipe means FFmpeg stopped early
            raise MotionError(f"FFmpeg stopped while writing {out.name}: {_last_line(err)}") from exc
        finally:
            st.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if not proc.stdin.closed:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
        if code != 0:
            raise MotionError(f"FFmpeg could not write {out.name}: {_last_line(err)}")
    return out.resolve()


def render_all(jobs: list[tuple[dict, Path]], workers: int = 1) -> list[Path]:
    """Render several scenes and return their files in the order given. Scenes do not depend on each other, so with
    ``workers`` above 1 they are drawn in separate processes (drawing is the slow part and uses one core each).
    The first scene that fails stops the rest and its own error comes back."""
    if workers <= 1 or len(jobs) <= 1:
        return [render(scene, out) for scene, out in jobs]
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures.process import BrokenProcessPool

    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
        futures = [pool.submit(render, scene, out) for scene, out in jobs]
        try:
            return [f.result() for f in futures]
        except BrokenProcessPool:
            raise MotionError("a drawing process stopped without an error, most likely out of memory; "
                              "draw the beats one at a time instead") from None
        except BaseException:
            for f in futures:
                f.cancel()
            raise


def renderers(table: Path | None = None) -> list[dict]:
    """Every renderer: the shipped table, then the user's motion_renderers.json, then ``table``."""
    from . import providers

    entries = list(_read_json(RENDERERS_FILE).get("renderers", []))
    user = providers.proofhouse_home() / "motion_renderers.json"
    if user.is_file():
        entries += _read_json(user).get("renderers", [])
    if table is not None:
        path = Path(table)
        if not path.is_file():
            raise MotionError(f"renderer table not found: {path}")
        entries += _read_json(path).get("renderers", [])
    merged: dict[str, dict] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            merged[entry["id"]] = entry
    return list(merged.values())


_PLACEHOLDER = re.compile(r"\{(scene|out|width|height|fps|seconds)\}")


def _render_outside(scene: dict, out: Path, renderer: str, table: Path | None, timeout: float | None) -> Path:
    known = {entry["id"]: entry for entry in renderers(table)}
    entry = known.get(renderer)
    if entry is None:
        raise MotionError(f"unknown renderer {renderer!r}; known renderers: {', '.join(known)}")
    command = entry.get("command")
    if not (isinstance(command, list) and command and all(isinstance(c, str) for c in command)):
        raise MotionError(f"renderer {renderer!r} needs a command as a list of words, never a shell string")
    scene_file = out.with_name(out.stem + ".scene.json")
    scene_file.write_text(json.dumps(scene, indent=2), encoding="utf-8")
    W, H = scene["size"]
    values = {"scene": str(scene_file), "out": str(out), "width": str(W), "height": str(H),
              "fps": f"{scene['fps']:g}", "seconds": f"{scene['seconds']:g}"}
    argv = [_PLACEHOLDER.sub(lambda mt: values[mt.group(1)], part) for part in command]
    limit = timeout or entry.get("timeout") or 1800
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=limit, check=False)
    except subprocess.TimeoutExpired as exc:
        raise MotionError(f"renderer {renderer!r} did not finish in {limit} s") from exc
    except OSError as exc:
        raise MotionError(f"renderer {renderer!r} could not start: {exc}") from exc
    if done.returncode != 0:
        tail = (done.stderr or done.stdout or "").strip().splitlines()
        raise MotionError(f"renderer {renderer!r} failed (exit {done.returncode}): {tail[-1] if tail else 'no message'}")
    if not out.is_file():
        raise MotionError(f"renderer {renderer!r} finished but wrote no {out.name}")
    return out.resolve()
