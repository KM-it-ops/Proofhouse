"""Turn real command output and web pages into PNG frames for the video studio."""

from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import sitecheck

_REDACTED = "[hidden]"


def private_text() -> tuple[str, ...]:
    """The home folder (in every spelling) and the user name, longest first, so a frame never shows them."""
    home = Path.home()
    found = {str(home), home.as_posix(), str(home).replace("\\", "\\\\")}
    if len(home.name) >= 3:
        found.add(home.name)
    return tuple(sorted(found, key=len, reverse=True))


def _shown_places() -> list[tuple[str, str]]:
    """Folders this machine's output may name, longest first, each with what a viewer sees instead: the Proofhouse
    folder as ~/.proofhouse (where it is by default), the temp folder as nothing (only the file name stays), and the
    home folder as ~."""
    places = []
    own = os.environ.get("PROOFHOUSE_HOME")
    if own:
        places.append((own, "~/.proofhouse"))
    places += [(tempfile.gettempdir(), ""), (str(Path.home()), "~")]
    return sorted(((p.rstrip("\\/"), shown) for p, shown in places if len(p.rstrip("\\/")) > 3),
                  key=lambda item: len(item[0]), reverse=True)


_PATH_TAIL = r"(?:[\\/]+[^\s'\"<>|()\[\]{},;]*)?(?![\w.-])"


def clean_paths(text: str) -> str:
    """``text`` with every path inside this machine's private folders shown as a viewer would expect: a settings file
    under ~/.proofhouse, a home file under ~, a temp file by its name alone, so no frame shows a folder of this
    machine."""
    flags = re.IGNORECASE if os.name == "nt" else 0
    for real, shown in _shown_places():
        spellings = {real, real.replace("\\", "/"), real.replace("/", "\\"), real.replace("\\", "\\\\")}
        for spelling in sorted(spellings, key=len, reverse=True):
            def swap(found: re.Match[str], size: int = len(spelling), shown: str = shown) -> str:
                tail = re.sub(r"[\\/]+", "/", found.group(0)[size:])
                if shown:
                    return shown + tail
                return tail.rstrip("/").rsplit("/", 1)[-1] or "temp"
            text = re.sub(re.escape(spelling) + _PATH_TAIL, swap, text, flags=flags)
    return text


class CaptureError(Exception):
    """A capture could not be made; the message says why."""


def card_html(
    command: str,
    output: str,
    *,
    redact: tuple[str, ...] = (),
    max_lines: int = 28,
    title: str = "",
) -> str:
    """Self-contained dark terminal page sized for a full HD screenshot."""
    cmd, text = clean_paths(command), clean_paths(output)
    for secret in redact:
        if secret:
            cmd, text = cmd.replace(secret, _REDACTED), text.replace(secret, _REDACTED)
    cmd = html.escape(cmd)
    lines = text.splitlines()
    if len(lines) > max_lines:
        extra = len(lines) - max_lines
        body = "\n".join(lines[:max_lines]) + f"\n... {extra} more lines"
    else:
        body = text
    body = html.escape(body)
    heading = html.escape(title) if title else "Terminal"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: 100%; height: 100%; background: #0d1117; }}
  body {{
    display: flex; align-items: center; justify-content: center;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    padding: 48px;
  }}
  .window {{
    width: 100%; max-width: 1680px; background: #161b22;
    border-radius: 14px; border: 1px solid #30363d;
    box-shadow: 0 24px 80px rgba(0,0,0,0.55); overflow: hidden;
  }}
  .bar {{
    display: flex; align-items: center; gap: 8px; padding: 14px 18px;
    background: #21262d; border-bottom: 1px solid #30363d;
    font-size: 15px; color: #8b949e; letter-spacing: 0.02em;
  }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  .dot.r {{ background: #ff5f57; }}
  .dot.y {{ background: #febc2e; }}
  .dot.g {{ background: #28c840; }}
  .title {{ margin-left: 8px; flex: 1; }}
  .body {{ padding: 36px 40px 44px; color: #e6edf3; font-size: 26px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }}
  .prompt {{ color: #7ee787; margin-bottom: 20px; }}
  .prompt span {{ color: #79c0ff; }}
</style>
</head>
<body>
<div class="window">
  <div class="bar">
    <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
    <span class="title">{heading}</span>
  </div>
  <div class="body"><div class="prompt">$ <span>{cmd}</span></div>{body}</div>
</div>
</body>
</html>
"""


def run_command(argv: list[str], *, cwd: Path, timeout: int = 60) -> str:
    """Run a program (never a shell); merged stdout and stderr as text."""
    try:
        done = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CaptureError(f"{' '.join(argv)!r} did not finish in {timeout} s") from exc
    except OSError as exc:
        raise CaptureError(f"{' '.join(argv)!r} could not start") from exc
    out = (done.stdout or "") + (done.stderr or "")
    if done.returncode != 0:
        out = out.rstrip("\n") + f"\n[exit {done.returncode}]"
    return out


def screenshot_command(browser: str, url: str, size: tuple[int, int], out: Path) -> list[str]:
    w, h = size
    return [
        browser,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={w},{h}",
        f"--screenshot={out}",
        url,
    ]


def _take_screenshot(url: str, size: tuple[int, int], out: Path, timeout: int = 30) -> Path:
    browser = sitecheck.find_browser()
    if browser is None:
        raise CaptureError("no Chrome or Chromium found; install Google Chrome or Microsoft Edge")
    out.parent.mkdir(parents=True, exist_ok=True)
    command = screenshot_command(browser, url, size, out)
    run = sitecheck._open(command, timeout)
    if isinstance(run, str):
        raise CaptureError(f"Chrome screenshot failed: {run}")
    if run.returncode != 0:
        raise CaptureError(f"Chrome exited with code {run.returncode} while taking a screenshot")
    if not out.is_file():
        raise CaptureError("Chrome did not write a screenshot PNG")
    return out.resolve()


def render_card(
    command: str,
    output: str,
    out_png: Path,
    *,
    size: tuple[int, int] = (1920, 1080),
    redact: tuple[str, ...] = (),
    title: str = "",
) -> Path:
    html_path = out_png.with_suffix(".html")
    try:
        html_path.write_text(
            card_html(command, output, redact=redact, title=title),
            encoding="utf-8",
        )
        return _take_screenshot(html_path.resolve().as_uri(), size, out_png)
    finally:
        html_path.unlink(missing_ok=True)


def render_page(
    url: str,
    out_png: Path,
    *,
    size: tuple[int, int] = (1920, 1080),
    full_page: bool = False,
    scale: float = 1.0,
    timeout: int = 30,
) -> Path:
    """Screenshot a page. ``full_page`` keeps everything down to the bottom; ``scale`` sharpens phone shots."""
    if not full_page and scale == 1.0:
        return _take_screenshot(url, size, out_png)
    sync_playwright = playwright()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            try:
                page = browser.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=scale)
                page.goto(url, wait_until="load", timeout=timeout * 1000)
                page.wait_for_timeout(300)
                page.screenshot(path=str(out_png), full_page=full_page, timeout=timeout * 1000)
            finally:
                browser.close()
    except CaptureError:
        raise
    except Exception as exc:  # Playwright raises its own error types; report them plainly
        raise CaptureError(f"the page screenshot failed: {exc}".splitlines()[0]) from exc
    if not out_png.is_file():
        raise CaptureError("the browser did not write a screenshot PNG")
    return out_png.resolve()


def playwright():  # noqa: ANN201 - returns Playwright's sync entry point, an optional extra
    """Playwright's sync entry point, or a plain error saying how to install it."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureError(
            "recording and full-page capture need the record extra: uv tool install 'proofhouse[record]'"
        ) from exc
    return sync_playwright


def launch_browser(p):  # noqa: ANN001, ANN201 - Playwright objects
    """Start the Chrome or Edge already installed here, headless; nothing is downloaded."""
    browser = sitecheck.find_browser()
    if browser is None:
        raise CaptureError("no Chrome or Chromium found; install Google Chrome or Microsoft Edge")
    # a browser that never starts must not hang the recording; scrollbars would show in every frame
    return p.chromium.launch(executable_path=browser, headless=True, timeout=15000, args=["--hide-scrollbars"])
