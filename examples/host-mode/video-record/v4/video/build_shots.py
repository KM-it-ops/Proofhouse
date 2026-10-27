"""Build the seven film shot clips (shot-01.mp4 .. shot-07.mp4) with FFmpeg.

Run: uv run --no-sync python build_shots.py
The film reuses the footage made for the launch promo, so it needs, in ../launch/video/:
  gen/shore.mp4, gen/dinghy.mp4   (the two generated Gemini clips, 10 s each)
  app/frames/                     (the app screen recording from capture_app.py, 30 fps)
Only the cut is new: other parts of each clip, other phone positions, and a longer story.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "launch" / "video"
FPS = 30
W, H = 1920, 1080
PHONE_H = 770
PHONE_ASPECT = 430 / 890
BLUR = 22

# name, seconds, backdrop clip, backdrop start, blur ("none" | "full" | "ramp"),
# phone: None or (centre x as a fraction of the width, app start second or "end" for the finished splash, hold seconds)
SHOTS = [
    ("shot-01.mp4", 5, "shore.mp4", 0.0, "none", None),
    ("shot-02.mp4", 3, "shore.mp4", 5.0, "full", (0.50, 0.0, 0.0)),
    ("shot-03.mp4", 5, "shore.mp4", 2.0, "full", (0.66, 3.2, 0.0)),
    ("shot-04.mp4", 5, "shore.mp4", 1.0, "full", (0.66, 8.0, 0.6)),
    ("shot-05.mp4", 5, "shore.mp4", 3.0, "full", (0.66, 12.4, 0.8)),
    ("shot-06.mp4", 4, "dinghy.mp4", 0.0, "none", None),
    ("shot-07.mp4", 3, "dinghy.mp4", 4.0, "ramp", (0.50, "end", 0.0)),
]
SPLASH_DONE = 54  # frame at 1.8 s: wave mark and wordmark fully drawn, before the splash fades


def build(out: str, seconds: float, clip: str, start: float, blur: str, phone: tuple[float, float | str, float] | None) -> None:
    source = SOURCE / "gen" / clip
    if not source.is_file():
        sys.exit(f"missing {source}; the film reuses the promo's generated clips")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", str(source)]
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
    push = f"(1+0.06*t/{seconds})"
    move = f"scale=w='trunc({W}*{push}/2)*2':h=-2:eval=frame,crop={W}:{H}"
    base = f"[0:v]{fit},{move},trim=duration={seconds},setpts=PTS-STARTPTS"
    soft = "gblur=sigma={s},eq=brightness=-0.12:saturation=0.9".format(s=BLUR)
    if phone is None:
        graph = f"{base},format=yuv420p[v]"
    else:
        cx, app_start, hold = phone
        frames = SOURCE / "app" / "frames"
        if app_start == "end":
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(seconds), "-i", str(frames / f"f{SPLASH_DONE:05d}.png")]
            app_part = "[1:v]format=rgba"
        else:
            span = seconds - hold
            cmd += ["-framerate", str(FPS), "-start_number", str(int(app_start * FPS)), "-t", str(span), "-i", str(frames / "f%05d.png")]
            app_part = "[1:v]format=rgba" + (f",tpad=stop_mode=clone:stop_duration={hold}" if hold else "")
        if blur == "ramp":
            bg = (
                f"{base},split[sharp][blurin];[blurin]{soft}[blurred];"
                f"[sharp][blurred]blend=all_expr='A*(1-min(T/1.2,1))+B*min(T/1.2,1)'[bg]"
            )
            fade = ",fade=t=in:st=0.2:d=0.8:alpha=1"
        else:
            bg = f"{base},{soft}[bg]"
            fade = ""
        lift = f"(1+0.04*t/{seconds})"
        ph = f"trunc({PHONE_H}*{lift}/2)*2"
        pw = f"trunc({PHONE_H}*{lift}*{PHONE_ASPECT:.5f}/2)*2"
        graph = (
            f"{bg};{app_part}{fade},scale=w='{pw}':h='{ph}':eval=frame[ph];"
            f"[bg][ph]overlay=x='main_w*{cx}-overlay_w/2':y='(main_h-overlay_h)/2-110':eval=frame:shortest=1,format=yuv420p[v]"
        )
    cmd += ["-filter_complex", graph, "-map", "[v]", "-t", str(seconds), "-r", str(FPS), "-an",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", str(HERE / out)]
    subprocess.run(cmd, check=True)
    print(f"built {out} ({seconds}s)")


def main() -> None:
    for spec in SHOTS:
        build(*spec)


if __name__ == "__main__":
    main()
