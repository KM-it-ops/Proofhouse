"""Pictures that cost nothing, made on this machine.

The shipped ``local-images`` entry in the media list runs ``python -m proofhouse.local_images --model local --size
1792x1024 --out shot.png`` with the prompt on stdin. Two engines:

- ``diffusers``: a real image model run on this machine, when the ``local-images`` extra is installed
  (``pip install 'proofhouse[local-images]'``). The model ``local`` means Stable Diffusion Turbo
  (``stabilityai/sd-turbo``); any other model is a diffusers model id, fetched once from Hugging Face. It uses the
  graphics card when there is one and runs on the processor otherwise, slower but free. Each model's own licence
  applies to what it makes.
- ``floor``: generated art from the prompt's colour and mood words (light, glow, soft shapes, flowing lines), with no
  words drawn on it. It needs only Pillow.

``local`` picks the model when it is installed and the floor otherwise; ``PROOFHOUSE_IMAGE_ENGINE`` or the model
``floor`` or ``diffusers`` picks one by name. A paid image service makes richer pictures; this is the floor, not the
ceiling.
"""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import importlib.util
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

ENGINES = ("diffusers", "floor")
DEFAULT_MODEL = "stabilityai/sd-turbo"
_AUTO = ("", "local", "auto")
_WORK_EDGE = 512  # the floor paints soft shapes at this size, then scales up; nothing in it needs more detail

# colour words: hue in degrees, saturation and brightness from 0 to 1
_COLOURS: dict[str, tuple[float, float, float]] = {
    "red": (0, .85, .85), "crimson": (348, .85, .7), "scarlet": (5, .9, .85), "coral": (12, .65, .95),
    "orange": (28, .9, .95), "peach": (25, .45, .97), "amber": (38, .9, .95), "gold": (45, .8, .95),
    "golden": (45, .8, .95), "yellow": (55, .85, .97), "lime": (90, .8, .9), "green": (130, .7, .75),
    "emerald": (145, .8, .7), "mint": (150, .4, .9), "teal": (175, .75, .65), "turquoise": (172, .7, .85),
    "cyan": (186, .85, .95), "aqua": (186, .7, .95), "azure": (205, .7, .95), "blue": (215, .8, .85),
    "cobalt": (220, .85, .7), "navy": (225, .8, .35), "indigo": (245, .75, .55), "violet": (270, .65, .85),
    "purple": (280, .7, .7), "lavender": (270, .35, .95), "magenta": (305, .85, .9), "pink": (330, .55, .95),
    "rose": (340, .6, .9), "brown": (25, .6, .4), "white": (0, 0, .96), "silver": (210, .06, .78),
    "grey": (210, .05, .55), "gray": (210, .05, .55), "black": (0, 0, .07),
}
# the hues a mood suggests when the prompt names no colour
_MOODS: tuple[tuple[frozenset[str], tuple[float, ...]], ...] = (
    (frozenset({"neon", "cyber", "cyberpunk", "hype", "energetic", "futuristic", "tech", "electric", "synthwave",
                "digital", "launch"}), (300, 190, 260)),
    (frozenset({"dark", "tense", "noir", "ominous", "night", "mysterious", "moody", "midnight", "space"}), (228, 262, 200)),
    (frozenset({"warm", "hopeful", "sunrise", "sunset", "cozy", "golden", "fire", "autumn", "desert"}), (30, 12, 45)),
    (frozenset({"calm", "ambient", "ocean", "sea", "peaceful", "serene", "water", "sky", "winter"}), (190, 208, 165)),
    (frozenset({"nature", "forest", "garden", "spring", "leaf", "jungle", "grass"}), (125, 90, 150)),
)
_VIVID = {"neon", "vibrant", "vivid", "bold", "hype", "energetic", "electric", "saturated", "bright", "punchy"}
_SOFT = {"calm", "pastel", "soft", "muted", "gentle", "faded", "dreamy", "subtle", "minimal"}
_DARK = {"dark", "night", "noir", "midnight", "moody", "shadow", "shadows", "ominous", "space", "deep"}
_LIGHT = {"bright", "light", "airy", "pastel", "sunny", "white", "clean", "morning"}
_FLOW = {"flow", "flowing", "wave", "waves", "motion", "speed", "fast", "energy", "dynamic", "stream", "ribbons", "swirl"}
_STARS = {"stars", "starry", "space", "galaxy", "night", "cosmic", "sparkle", "sparkles", "city", "lights"}
_HORIZON = {"sunrise", "sunset", "horizon", "dawn", "dusk", "landscape", "ocean", "sea", "desert"}


class ImageError(RuntimeError):
    """No engine could make the picture."""


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _ready(engine: str) -> bool:
    if engine == "diffusers":
        return _has_module("diffusers") and _has_module("torch") and _has_module("transformers") and _has_module("PIL")
    return _has_module("PIL")


def pick(model: str = "local") -> str:
    """The engine that will paint: the one the model or PROOFHOUSE_IMAGE_ENGINE names, or the best one installed."""
    model = (model or "").strip()
    asked = model.lower() if model.lower() in ENGINES else os.environ.get("PROOFHOUSE_IMAGE_ENGINE", "").strip().lower()
    if model.lower() not in (*_AUTO, *ENGINES):
        asked = "diffusers"  # a model id is a model to run
    if asked:
        if asked not in ENGINES:
            raise ImageError(f"PROOFHOUSE_IMAGE_ENGINE must be one of {', '.join(ENGINES)}")
        if not _ready(asked):
            raise ImageError("the image model is not installed here; install it with pip install 'proofhouse[local-images]'"
                             if asked == "diffusers" else "Pillow is not installed here; install proofhouse[video]")
        return asked
    for engine in ENGINES:
        if _ready(engine):
            return engine
    raise ImageError("Pillow is not installed here; install proofhouse[video], or name an image service")


def available() -> bool:
    try:
        pick()
    except ImageError:
        return False
    return True


def parse_size(text: str) -> tuple[int, int]:
    found = re.fullmatch(r"\s*(\d{2,5})\s*[xX*]\s*(\d{2,5})\s*", text or "")
    if not found:
        raise ImageError(f"size must look like 1792x1024, not {text!r}")
    width, height = int(found[1]), int(found[2])
    if not (64 <= width <= 8192 and 64 <= height <= 8192):
        raise ImageError("size must be 64 to 8192 pixels on each side")
    return width, height


# ---- the floor: generated art from the prompt's colour and mood words ----

def _words(prompt: str) -> list[str]:
    return re.findall(r"[a-z]+", prompt.lower())


def look(prompt: str) -> dict[str, Any]:
    """The palette and shapes the prompt's words call for: three colours (deep, middle, accent) and what to draw."""
    words = _words(prompt)
    seen = set(words)
    seed = int.from_bytes(hashlib.sha256(prompt.strip().lower().encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    named = [_COLOURS[w] for w in words if w in _COLOURS]
    named = list(dict.fromkeys(named))[:3]
    if named:
        hues = [h for h, _, _ in named]
    else:
        hues = next((list(h) for mood, h in _MOODS if mood & seen), [])
        if not hues:
            base = rng.uniform(0, 360)
            hues = [base, base + rng.choice((30, 40, 150, 180)), base - 30]
    while len(hues) < 3:
        hues.append(hues[0] + (35 if len(hues) == 1 else -150))
    sat = .95 if seen & _VIVID else .4 if seen & _SOFT else .75
    dark, light = bool(seen & _DARK), bool(seen & _LIGHT) and not seen & _DARK
    values = (.55, .8, 1.0) if light else (.07, .3, .9) if dark else (.16, .48, .97)

    def colour(i: int, level: int) -> tuple[int, int, int]:
        h, s, v = hues[i] % 360, (named[i][1] * sat / .75 if i < len(named) else sat), values[level]
        if i < len(named) and named[i][1] < .1:  # white, grey and black keep their own lightness
            s, v = named[i][1], named[i][2] if level == 2 else named[i][2] * values[level] / values[2]
        r, g, b = colorsys.hsv_to_rgb(h / 360, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
        return round(r * 255), round(g * 255), round(b * 255)

    # the first colour named leads as the glow; the others make the ground
    order = ((1 if len(named) > 1 else 0), (2 if len(named) > 2 else 1), 0) if named else (0, 1, 2)
    deep, middle, accent = (colour(i, level) for level, i in enumerate(order))
    return {
        "seed": seed, "deep": deep, "middle": middle, "accent": accent, "lift": .45 if dark else 1.0 if light else .85,
        "flow": 2 + (3 if seen & _FLOW else rng.randint(0, 1)), "stars": bool(seen & _STARS),
        "horizon": bool(seen & _HORIZON), "angle": rng.uniform(-35, 35) + (0 if seen & _HORIZON else rng.choice((0, 90))),
    }


def _floor(prompt: str, size: tuple[int, int], out: Path) -> None:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    width, height = size
    plan = look(prompt)
    rng = random.Random(plan["seed"])
    scale = _WORK_EDGE / max(width, height)
    sw, sh = max(16, round(width * scale)), max(16, round(height * scale))
    edge = max(sw, sh)

    side = math.ceil(math.hypot(sw, sh)) + 2  # the ground: a turned gradient from the deep colour to the middle one
    ramp = Image.linear_gradient("L").resize((side, side), Image.BICUBIC).rotate(plan["angle"], Image.BICUBIC)
    ramp = ramp.crop(((side - sw) // 2, (side - sh) // 2, (side - sw) // 2 + sw, (side - sh) // 2 + sh))
    picture = Image.composite(Image.new("RGB", (sw, sh), plan["middle"]), Image.new("RGB", (sw, sh), plan["deep"]), ramp)

    def light(colour: tuple[int, int, int], cx: float, cy: float, radius: float, strength: float) -> Image.Image:
        d = max(4, round(radius * 2))
        mask = Image.radial_gradient("L").resize((d, d), Image.BICUBIC).point(lambda v: round(((255 - v) / 255) ** 1.6 * 255 * strength))
        layer = Image.new("RGB", (sw, sh))
        layer.paste(colour, (round(cx - d / 2), round(cy - d / 2)), mask)
        return layer

    # light adds to what is under it (a screen blend), so glows glow instead of covering the ground
    cx, cy = (sw * rng.uniform(.4, .6), sh * .78) if plan["horizon"] else (sw * rng.uniform(.25, .75), sh * rng.uniform(.25, .7))
    lift = plan["lift"]
    picture = ImageChops.screen(picture, light(plan["accent"], cx, cy, edge * rng.uniform(.5, .75), .95 * lift))
    picture = ImageChops.screen(picture, light(plan["middle"], sw - cx, sh - cy, edge * rng.uniform(.3, .5), .7 * lift))

    orbs = Image.new("RGB", (sw, sh))  # soft lights, out of focus
    draw = ImageDraw.Draw(orbs)
    for _ in range(rng.randint(8, 16)):
        r = rng.uniform(.02, .1) * edge
        x, y = rng.uniform(0, sw), rng.uniform(0, sh)
        colour = rng.choice((plan["accent"], plan["middle"], tuple(min(255, c + 70) for c in plan["accent"])))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=tuple(round(c * rng.uniform(.25, .6) * lift) for c in colour))
    picture = ImageChops.screen(picture, orbs.filter(ImageFilter.GaussianBlur(edge / 60)))

    halo, core = Image.new("RGB", (sw, sh)), Image.new("RGB", (sw, sh))  # flowing lines of light across the frame
    for k in range(plan["flow"]):
        base, amp = sh * rng.uniform(.2, .85), sh * rng.uniform(.05, .18)
        freq, phase = rng.uniform(1.2, 3.2) * math.pi / sw, rng.uniform(0, math.tau)
        points = [(x, base + amp * math.sin(freq * x + phase)) for x in range(-4, sw + 5, 3)]
        colour = plan["accent"] if k % 2 == 0 else tuple(min(255, c + 90) for c in plan["middle"])
        width_px = max(1, round(sh * rng.uniform(.003, .01)))
        ImageDraw.Draw(halo).line(points, fill=tuple(round(c * .7) for c in colour), width=width_px * 6)
        ImageDraw.Draw(core).line(points, fill=tuple(min(255, c + 80) for c in colour), width=width_px)
    picture = ImageChops.screen(picture, halo.filter(ImageFilter.GaussianBlur(edge / 70)))
    picture = ImageChops.screen(picture, core.filter(ImageFilter.GaussianBlur(.6)))

    if plan["stars"]:
        specks = Image.new("RGB", (sw, sh))
        draw = ImageDraw.Draw(specks)
        for _ in range(rng.randint(40, 90)):
            x, y, r = rng.uniform(0, sw), rng.uniform(0, sh * .8), rng.uniform(.4, 1.2)
            v = rng.randint(110, 255)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(v, v, v))
        picture = ImageChops.screen(picture, specks.filter(ImageFilter.GaussianBlur(.4)))

    shade = Image.radial_gradient("L").resize((sw, sh), Image.BICUBIC).point(lambda v: round(255 - (v / 255) ** 2 * 140))
    picture = ImageChops.multiply(picture, Image.merge("RGB", (shade, shade, shade)))  # darker toward the edges

    final = picture.resize((width, height), Image.BICUBIC)
    grain = Image.frombytes("L", (width, height), rng.randbytes(width * height)).convert("RGB")  # the same each time
    Image.blend(final, grain, .03).save(out, format="PNG")


# ---- the real model ----

def _model_size(width: int, height: int, edge: int) -> tuple[int, int]:
    """The asked shape at the model's own size, each side a multiple of 64."""
    scale = edge / max(width, height)
    return max(64, round(width * scale / 64) * 64), max(64, round(height * scale / 64) * 64)


def _diffusers(prompt: str, size: tuple[int, int], out: Path, model: str) -> None:
    import torch  # type: ignore[import-not-found]
    from diffusers import AutoPipelineForText2Image  # type: ignore[import-not-found]
    from PIL import Image

    name = DEFAULT_MODEL if model.strip().lower() in (*_AUTO, *ENGINES) else model.strip()
    turbo = "turbo" in name.lower()
    if torch.cuda.is_available():
        device, dtype = "cuda", torch.float16
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device, dtype = "mps", torch.float16
    else:
        device, dtype = "cpu", torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(name, torch_dtype=dtype).to(device)
    w, h = _model_size(*size, 512 if turbo or "xl" not in name.lower() else 1024)
    made = pipe(prompt=prompt, width=w, height=h, num_inference_steps=1 if turbo else 25,
                guidance_scale=0.0 if turbo else 7.0).images[0]
    made.convert("RGB").resize(size, Image.LANCZOS).save(out, format="PNG")


def paint(prompt: str, out: Path, *, size: tuple[int, int] = (1024, 1024), model: str = "local",
          engine: str | None = None) -> Path:
    """Make a picture of ``prompt`` into a PNG file at ``out``."""
    if not prompt.strip():
        raise ImageError("there is nothing to picture")
    engine = engine or pick(model)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    if engine == "diffusers":
        _diffusers(prompt.strip(), size, out, model)
    else:
        _floor(prompt.strip(), size, out)
    if not out.is_file() or out.stat().st_size == 0:
        raise ImageError(f"{engine} finished but wrote no picture")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m proofhouse.local_images", description="Make a picture of the prompt on stdin.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--model", default="local")
    args = parser.parse_args(argv)
    try:
        paint(sys.stdin.buffer.read().decode("utf-8", "replace"), args.out, size=parse_size(args.size), model=args.model)
    except ImageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
