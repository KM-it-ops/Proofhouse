"""Write a generated website to disk safely and check it like a visitor would.

Checks, all local:
- every HTML file parses, has a title, a language and a mobile viewport;
- every link and file the pages point to inside the site exists;
- every image has alt text;
- with a Chrome or Chromium on this machine (or ``PROOFHOUSE_BROWSER``): the
  home page is opened headless, screenshots are taken at desktop and phone
  width, and any JavaScript error is reported.

Paths in a generated site are checked before anything is written: relative,
no ``..``, at most 60 files and 3 MB, so a model cannot write outside the folder.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

MAX_FILES = 60
MAX_BYTES = 3_000_000
_SAFE_PATH = re.compile(r"[A-Za-z0-9._/-]+")
_BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "msedge")


class SiteError(ValueError):
    """The generated site cannot be written as given."""


def write_site(files: dict[str, str], folder: Path) -> list[str]:
    if not isinstance(files, dict) or not files:
        raise SiteError("the site has no files")
    if len(files) > MAX_FILES:
        raise SiteError(f"the site has more than {MAX_FILES} files")
    if sum(len(str(text).encode("utf-8")) for text in files.values()) > MAX_BYTES:
        raise SiteError("the site is larger than 3 MB")
    names = []
    for name in files:
        path = PurePosixPath(str(name))
        if not _SAFE_PATH.fullmatch(str(name)) or path.is_absolute() or ".." in path.parts or str(name).startswith("."):
            raise SiteError(f"unsafe file name in the site: {name!r}")
        names.append(str(path))
    if "index.html" not in names:
        raise SiteError("the site has no index.html")
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(text), encoding="utf-8")
    return sorted(names)


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self.title = ""
        self.lang = False
        self.viewport = False
        self.images_without_alt = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v or "" for k, v in attrs}
        if tag == "html" and values.get("lang"):
            self.lang = True
        if tag == "meta" and values.get("name", "").lower() == "viewport":
            self.viewport = True
        if tag == "title":
            self._in_title = True
        if tag == "img" and not values.get("alt", "").strip():
            self.images_without_alt += 1
        for key in ("href", "src"):
            if values.get(key):
                self.refs.append(values[key])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _internal(ref: str) -> str | None:
    parsed = urlparse(ref)
    if parsed.scheme or ref.startswith(("#", "//", "mailto:", "tel:", "data:", "javascript:")):
        return None
    path = unquote(parsed.path)
    return path or None


def find_browser() -> str | None:
    chosen = os.environ.get("PROOFHOUSE_BROWSER")
    if chosen:
        return chosen if Path(chosen).is_file() else None
    on_path = next((found for name in _BROWSERS if (found := shutil.which(name))), None)
    return on_path or next((str(path) for path in _install_folders() if path.is_file()), None)


def _install_folders() -> list[Path]:
    """Where Chrome and Edge install themselves when they are not on PATH."""
    found = [Path(os.environ[var]) / vendor / app / "Application" / exe
             for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA") if var in os.environ
             for vendor, app, exe in (("Microsoft", "Edge", "msedge.exe"), ("Google", "Chrome", "chrome.exe"))]
    found += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
              Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
              Path("/Applications/Chromium.app/Contents/MacOS/Chromium")]
    return found


def _open(command: list[str], timeout: int) -> subprocess.CompletedProcess[str] | str:
    """Run the headless browser; a launch that hangs is tried once more, then reported (never raised)."""
    for _ in range(2):
        try:
            return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            continue
        except OSError as exc:
            return f"the browser could not start ({type(exc).__name__})"
    return f"the browser did not finish in {timeout} s, twice"


def check_site(folder: Path, shots: Path | None = None, timeout: int = 30, browser: bool = True) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    pages = sorted(folder.rglob("*.html"))
    broken: list[str] = []
    for page in pages:
        parser = _Page()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            checks.append({"check": f"{page.name} reads", "ok": False, "detail": type(exc).__name__})
            continue
        name = page.relative_to(folder).as_posix()
        checks.append({"check": f"{name} has a title", "ok": bool(parser.title.strip()), "detail": parser.title.strip()[:60]})
        checks.append({"check": f"{name} declares its language", "ok": parser.lang, "detail": ""})
        checks.append({"check": f"{name} works on phones (viewport)", "ok": parser.viewport, "detail": ""})
        checks.append({"check": f"{name} images have alt text", "ok": parser.images_without_alt == 0,
                       "detail": f"{parser.images_without_alt} without alt"})
        for ref in parser.refs:
            local = _internal(ref)
            if local is None:
                continue
            target = (folder / local.lstrip("/")) if local.startswith("/") else (page.parent / local)
            if local.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append(f"{name} -> {ref}")
    checks.append({"check": "every internal link and file exists", "ok": not broken, "detail": "; ".join(broken[:10])})
    if not browser:
        checks.append({"check": "opened in a browser", "ok": None, "detail": "not measured: pass --allow-commands to open the site in a browser"})
        return checks
    browser_path = find_browser()
    if browser_path is None:
        checks.append({"check": "opened in a browser", "ok": None, "detail": "not measured: no Chrome or Chromium found"})
        return checks
    url = (folder / "index.html").resolve().as_uri()
    errors: list[str] = []
    stuck: list[str] = []
    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
    for label, size in (("desktop", "1440,900"), ("phone", "390,844")):
        command = [browser_path, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={size}",
                   "--enable-logging=stderr", "--v=0"]
        # headless Chrome and Edge only exit after a screenshot or a DOM dump; without one they wait forever
        command.append(f"--screenshot={shots / f'{label}.png'}" if shots is not None else "--dump-dom")
        run = _open(command + [url], timeout)
        if isinstance(run, str):
            stuck.append(f"{label}: {run}")
            continue
        errors += [line for line in run.stderr.splitlines() if "Uncaught" in line or "SyntaxError" in line]
    if len(stuck) == 2:
        checks.append({"check": "opened in a browser", "ok": None, "detail": "not measured: " + "; ".join(stuck)})
        return checks
    if errors:
        detail = "; ".join(errors[:3])[:300]
        if stuck:
            detail = (detail + f" (not measured on {'; '.join(stuck)})").strip()
        js_ok = False
    elif stuck:
        detail = "not measured: " + "; ".join(stuck)
        js_ok = None
    else:
        detail = ""
        js_ok = True
    checks.append({"check": "no JavaScript errors in the browser", "ok": js_ok, "detail": detail.strip()})
    if shots is not None:
        made = all((shots / f"{label}.png").is_file() for label in ("desktop", "phone"))
        checks.append({"check": "screenshots at desktop and phone width", "ok": made, "detail": str(shots)})
    return checks
