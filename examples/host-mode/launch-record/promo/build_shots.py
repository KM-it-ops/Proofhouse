"""Build the six promo shot clips (shot-01.mp4 .. shot-06.mp4) with FFmpeg.

Run: uv run --no-sync python build_shots.py
Needs app/frames/ from capture_app.py. Backdrop footage is read from gen/shore.mp4 (shots 1-5) and
gen/dinghy.mp4 (shot 6); when a file is missing a stand-in moving gradient is used and the run says so.
Shots 2-5 are consecutive pieces of one continuous recording of the app screen (16 seconds, 30 fps).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
W, H = 1920, 1080
PHONE_H = 770
PHONE_ASPECT = 430 / 890

# (output, seconds, app recording start second or None for backdrop only, backdrop file, push direction)
SHOTS = [
    ("shot-01.mp4", 4, None, "shore.mp4", "in"),
    ("shot-02.mp4", 3, 0, "shore.mp4", "in"),
    ("shot-03.mp4", 5, 3, "shore.mp4", "in"),
    ("shot-04.mp4", 4, 8, "shore.mp4", "in"),
    ("shot-05.mp4", 4, 12, "shore.mp4", "in"),
    ("shot-06.mp4", 4, None, "dinghy.mp4", "out"),
]


def backdrop_input(name: str, seconds: float) -> list[str]:
    path = HERE / "gen" / name
    if path.is_file():
        return ["-stream_loop", "-1", "-i", str(path)]
    print(f"  stand-in backdrop for {name} (generated clip not present)")
    return ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0x28485c:c1=0xd9b88f:x0=0:y0=0:x1={W}:y1={H}:speed=0.03:rate={FPS}:d={seconds}"]


def build(out: str, seconds: float, app_start: float | None, backdrop: str, direction: str) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y", *backdrop_input(backdrop, seconds)]
    push = f"(1+0.07*t/{seconds})" if direction == "in" else f"(1.07-0.07*t/{seconds})"
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
    move = f"scale=w='trunc({W}*{push}/2)*2':h=-2:eval=frame,crop={W}:{H}"
    if app_start is None:
        graph = f"[0:v]{fit},{move},trim=duration={seconds},setpts=PTS-STARTPTS,format=yuv420p[v]"
    else:
        cmd += ["-framerate", str(FPS), "-start_number", str(int(app_start * FPS)), "-i", str(HERE / "app" / "frames" / "f%05d.png")]
        lift = f"(1+0.05*t/{seconds})"
        ph = f"trunc({PHONE_H}*{lift}/2)*2"
        pw = f"trunc({PHONE_H}*{lift}*{PHONE_ASPECT:.5f}/2)*2"
        graph = (
            f"[0:v]{fit},{move},gblur=sigma=26,eq=brightness=-0.14:saturation=0.85,trim=duration={seconds},setpts=PTS-STARTPTS[bg];"
            f"[1:v]format=rgba,scale=w='{pw}':h='{ph}':eval=frame[ph];"
            f"[bg][ph]overlay=x='(main_w-overlay_w)/2':y='(main_h-overlay_h)/2-120':eval=frame:shortest=1,format=yuv420p[v]"
        )
    cmd += ["-filter_complex", graph, "-map", "[v]", "-t", str(seconds), "-r", str(FPS), "-an",
            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", str(HERE / out)]
    subprocess.run(cmd, check=True)
    print(f"built {out} ({seconds}s)")


def main() -> None:
    for spec in SHOTS:
        build(*spec)


if __name__ == "__main__":
    main()
