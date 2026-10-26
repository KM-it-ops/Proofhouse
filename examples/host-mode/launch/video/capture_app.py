"""Record the Tidewatch app screen prototype (app/index.html) as numbered PNG frames with a clear background.

Run: uv run --no-sync --with playwright python capture_app.py [fps] [seconds]
Uses the installed Chrome (no browser download). Frames are written to app/frames/f00000.png ...
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 16.6


def main() -> None:
    out = HERE / "app" / "frames"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("f*.png"):
        old.unlink()
    frames = int(SECONDS * FPS)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 430, "height": 890}, device_scale_factor=2)
        page.goto((HERE / "app" / "index.html").as_uri())
        for i in range(frames):
            page.evaluate("t => window.setT(t)", i / FPS)
            page.screenshot(path=str(out / f"f{i:05d}.png"), omit_background=True)
        browser.close()
    print(f"wrote {frames} frames to {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
