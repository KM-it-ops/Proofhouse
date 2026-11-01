"""Real recordings for films: a terminal command as it runs, and a web app as it is used.

A terminal recording keeps when each line of output really arrived, so the film can type the command
at a human pace and then show the output with its real rhythm. An app recording drives the Chrome or
Edge already installed here, keeps every frame the page paints, and notes where the cursor went and
clicked so the motion layer can draw the pointer and the sound layer can add the clicks.
"""

from __future__ import annotations

import codecs
import json
import math
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import capture, motion
from .capture import CaptureError

STEP_KINDS = ("click", "hover", "type", "press", "scroll", "wait")
_MAX_WAIT_STEP = 30.0


@dataclass(frozen=True)
class Chunk:
    """A piece of output and the seconds after start when it arrived."""

    at: float
    text: str


def _hide(text: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, capture._REDACTED)
    return text


def record_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 60,
    redact: tuple[str, ...] = (),
) -> list[Chunk]:
    """Run a program (never a shell) and keep each line of its output with the time it arrived.

    Output is cut into lines before it is kept, so a secret that arrives in two pieces is still
    hidden. The home folder and user name are always hidden.
    """
    if isinstance(argv, str) or not argv or not all(isinstance(a, str) for a in argv):
        raise CaptureError("a recorded command is a list of words, never a shell line")
    secrets = tuple(sorted({*redact, *capture.private_text()}, key=len, reverse=True))
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            list(argv),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            env=env,
        )
    except OSError as exc:
        raise CaptureError(f"{' '.join(argv)!r} could not start") from exc

    chunks: list[Chunk] = []
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    pending = ""

    def keep(text: str, at: float) -> None:
        nonlocal pending
        pending += text
        while True:
            cut = max(pending.rfind("\n"), pending.rfind("\r"))
            if cut < 0:
                return
            ready, pending = pending[: cut + 1], pending[cut + 1 :]
            chunks.append(Chunk(at, _hide(ready, secrets)))

    def read() -> None:
        assert proc.stdout is not None
        while True:
            data = proc.stdout.read(65536)
            if not data:
                break
            keep(decoder.decode(data), time.monotonic() - start)
        keep(decoder.decode(b"", final=True), time.monotonic() - start)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.wait()
        reader.join(timeout=2)
        raise CaptureError(f"{' '.join(argv)!r} did not finish in {timeout} s") from exc
    reader.join(timeout=5)
    end = time.monotonic() - start
    if pending:
        chunks.append(Chunk(end, _hide(pending, secrets)))
    if code != 0:
        lead = "" if not chunks or chunks[-1].text.endswith(("\n", "\r")) else "\n"
        chunks.append(Chunk(end, f"{lead}[exit {code}]\n"))
    return chunks


def terminal_timeline(
    command_text: str,
    chunks: list[Chunk],
    *,
    max_wait: float = 1.0,
    cps: float = 16.0,
    seed: float = 3.0,
    lead: float = 0.5,
    enter: float = 0.35,
    hold: float = 1.6,
    redact: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Plan a terminal shot: the command typed at a human pace, then the real output.

    Gaps in the output longer than ``max_wait`` seconds are cut down to it; shorter gaps keep the
    rhythm the program really had.
    """
    secrets = tuple(sorted({*redact, *capture.private_text()}, key=len, reverse=True))
    text = _hide(command_text, secrets)
    typed = motion.char_times(text, cps, seed)
    keys = [round(lead + t, 4) for t in typed[:-1]]
    t = lead + typed[-1] + enter
    output = []
    last = 0.0
    for chunk in chunks:
        t += min(max(0.0, chunk.at - last), max_wait)
        last = chunk.at
        output.append({"at": round(t, 4), "text": chunk.text})
    return {"command": text, "keys": keys, "enter": round(lead + typed[-1] + enter, 4), "output": output,
            "seconds": round(t + hold, 3)}


def check_steps(steps: list[dict[str, Any]]) -> None:
    """Refuse app steps the recorder does not know, before a browser starts."""
    if not isinstance(steps, list) or not steps:
        raise CaptureError("an app recording needs at least one step")
    for n, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise CaptureError(f"step {n} is not an object")
        do = step.get("do")
        if do not in STEP_KINDS:
            raise CaptureError(f"step {n}: unknown step {do!r}; use one of {', '.join(STEP_KINDS)}")
        if do in ("click", "hover", "type") and not isinstance(step.get("selector"), str):
            raise CaptureError(f"step {n}: {do} needs a selector")
        if do == "type" and not isinstance(step.get("text"), str):
            raise CaptureError(f"step {n}: type needs text")
        if do == "press" and not isinstance(step.get("key"), str):
            raise CaptureError(f"step {n}: press needs a key, such as Enter")
        if do == "scroll" and not isinstance(step.get("y", step.get("selector")), (int, float, str)):
            raise CaptureError(f"step {n}: scroll needs y (pixels) or a selector")
        if do == "wait":
            seconds = step.get("seconds")
            if not isinstance(seconds, (int, float)) or not 0 <= seconds <= _MAX_WAIT_STEP:
                raise CaptureError(f"step {n}: wait needs seconds between 0 and {_MAX_WAIT_STEP:g}")


@dataclass(frozen=True)
class AppRecording:
    video: Path
    meta: Path
    seconds: float


class _Pointer:
    """Moves the mouse along eased paths and writes down where it went."""

    def __init__(self, page: Any, clock: Any, start: tuple[float, float]) -> None:
        self.page, self.clock = page, clock
        self.x, self.y = start
        self.moves: list[dict[str, float]] = []
        self.clicks: list[dict[str, float]] = []
        page.mouse.move(self.x, self.y)
        self._note()

    def _note(self) -> None:
        self.moves.append({"t": round(self.clock(), 4), "x": round(self.x, 1), "y": round(self.y, 1)})

    def glide(self, x: float, y: float) -> None:
        distance = math.hypot(x - self.x, y - self.y)
        steps = max(6, min(36, int(distance / 18)))
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            p = motion.ease_in_out(i / steps)
            # A slight arc, like a hand, instead of a ruler-straight line.
            bow = math.sin(math.pi * p) * min(40.0, distance * 0.08)
            self.x = x0 + (x - x0) * p
            self.y = y0 + (y - y0) * p - bow
            self.page.mouse.move(self.x, self.y)
            self._note()
            self.page.wait_for_timeout(16)

    def click(self) -> None:
        self.page.mouse.down()
        self.clicks.append({"t": round(self.clock(), 4), "x": round(self.x, 1), "y": round(self.y, 1)})
        self.page.wait_for_timeout(70)
        self.page.mouse.up()


def _centre(page: Any, selector: str) -> tuple[float, float]:
    target = page.locator(selector).first
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    if box is None:
        raise CaptureError(f"{selector!r} is not on screen")
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def record_app(
    url: str,
    steps: list[dict[str, Any]],
    out_dir: Path,
    *,
    size: tuple[int, int] = (1920, 1080),
    scale: float = 1.0,
    cps: float = 9.0,
    tail: float = 0.6,
    timeout: int = 30,
) -> AppRecording:
    """Use a web app in the installed browser, following ``steps``, and record it as a video.

    Steps are data: click, hover, type, press, scroll and wait. ``recording.json`` beside the
    video holds the frame size and when keys, clicks and pointer moves happened (no typed text).
    """
    check_steps(steps)
    if shutil.which("ffmpeg") is None:
        raise CaptureError("FFmpeg is needed to turn the recording into a video; install it and retry")
    sync_playwright = capture.playwright()
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir()
    frames: list[tuple[float, Path]] = []
    keys: list[dict[str, float]] = []
    scrolls: list[dict[str, float]] = []
    w, h = size
    t0 = time.time()

    def clock() -> float:
        return time.time() - t0

    try:
        with sync_playwright() as p:
            browser = capture.launch_browser(p)
            try:
                page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
                page.set_default_timeout(timeout * 1000)
                page.goto(url, wait_until="load", timeout=timeout * 1000)

                def on_frame(frame: Any) -> None:
                    now = time.time()
                    stamp = frame.get("timestamp")
                    at = now
                    if isinstance(stamp, (int, float)):
                        for unit in (1.0, 1000.0):  # the browser's wall-clock time, in seconds or milliseconds
                            if abs(stamp / unit - now) < 60:
                                at = stamp / unit
                                break
                    data = frame["data"]
                    path = frames_dir / f"f{len(frames):05d}.{'png' if data[:4] == b'\x89PNG' else 'jpg'}"
                    path.write_bytes(data)
                    frames.append((at - t0, path))

                t0 = time.time()
                page.screencast.start(on_frame=on_frame, quality=92,
                                      size={"width": int(w * scale), "height": int(h * scale)})
                page.wait_for_timeout(400)
                pointer = _Pointer(page, clock, (w * 0.55, h * 0.72))
                for n, step in enumerate(steps, 1):
                    try:
                        _run_step(page, pointer, step, keys, scrolls, clock, cps, seed=n)
                    except CaptureError:
                        raise
                    except Exception as exc:  # Playwright's own error types
                        raise CaptureError(f"step {n} ({step['do']}) failed: {exc}".splitlines()[0]) from exc
                page.wait_for_timeout(int(tail * 1000))
                end = clock()
                page.screencast.stop()
            finally:
                browser.close()
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(f"the app recording failed: {exc}".splitlines()[0]) from exc

    if not frames:
        raise CaptureError("the browser sent no frames to record")
    video = out_dir / "recording.mp4"
    _encode(frames, end, frames_dir, video, (int(w * scale), int(h * scale)))
    shutil.rmtree(frames_dir, ignore_errors=True)
    meta = out_dir / "recording.json"
    meta.write_text(json.dumps({"size": [w, h], "scale": scale, "seconds": round(end, 3), "keys": keys,
                                "clicks": pointer.clicks, "moves": pointer.moves, "scrolls": scrolls},
                               indent=1), encoding="utf-8")
    return AppRecording(video=video.resolve(), meta=meta.resolve(), seconds=round(end, 3))


def _run_step(page: Any, pointer: _Pointer, step: dict[str, Any], keys: list[dict[str, float]],
              scrolls: list[dict[str, float]], clock: Any, cps: float, *, seed: int) -> None:
    do = step["do"]
    if do in ("click", "hover", "type"):
        pointer.glide(*_centre(page, step["selector"]))
        if do == "hover":
            page.wait_for_timeout(250)
            return
        page.wait_for_timeout(90)
        pointer.click()
        if do == "click":
            page.wait_for_timeout(200)
            return
        page.wait_for_timeout(180)
        text = step["text"]
        times = motion.char_times(text, cps, seed * 11.0)
        for i, ch in enumerate(text):
            page.keyboard.type(ch)
            keys.append({"t": round(clock(), 4)})
            page.wait_for_timeout(max(15, int((times[i + 1] - times[i]) * 1000)))
    elif do == "press":
        page.keyboard.press(step["key"])
        keys.append({"t": round(clock(), 4)})
        page.wait_for_timeout(200)
    elif do == "scroll":
        if isinstance(step.get("y"), (int, float)):
            total = float(step["y"])
        else:
            target = page.locator(step["selector"]).first.bounding_box()
            total = 0.0 if target is None else target["y"] - page.viewport_size["height"] * 0.25
        ticks = max(8, min(40, int(abs(total) / 25)))
        done = 0.0
        scrolls.append({"t": round(clock(), 4), "dy": round(total, 1)})
        for i in range(1, ticks + 1):
            want = total * motion.ease_in_out(i / ticks)
            page.mouse.wheel(0, want - done)
            done = want
            page.wait_for_timeout(16)
        page.wait_for_timeout(250)
    elif do == "wait":
        page.wait_for_timeout(int(float(step["seconds"]) * 1000))


def _encode(frames: list[tuple[float, Path]], end: float, folder: Path, out: Path, size: tuple[int, int]) -> None:
    """Join frames at their real times into a steady 30 fps video."""
    kept: list[tuple[float, Path]] = []
    for at, path in sorted(frames, key=lambda f: f[0]):
        if kept and at - kept[-1][0] < 1e-3:
            kept[-1] = (kept[-1][0], path)  # the newer frame of two at the same moment wins
        else:
            kept.append((max(0.0, at), path))
    kept[0] = (0.0, kept[0][1])
    lines = ["ffconcat version 1.0"]
    for i, (at, path) in enumerate(kept):
        nxt = kept[i + 1][0] if i + 1 < len(kept) else max(end, at + 1 / 30)
        lines += [f"file '{path.name}'", f"duration {nxt - at:.4f}"]
    lines.append(f"file '{kept[-1][1].name}'")  # the concat reader needs the last image twice
    listing = folder / "frames.txt"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    w, h = size[0] - size[0] % 2, size[1] - size[1] % 2
    command = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
               "-vf", f"fps=30,scale={w}:{h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "16",
               "-preset", "medium", "-movflags", "+faststart", str(out)]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    if done.returncode != 0 or not out.is_file():
        raise CaptureError(f"FFmpeg could not join the recorded frames: {done.stderr.strip()[-300:]}")
