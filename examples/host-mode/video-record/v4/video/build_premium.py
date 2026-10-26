"""Build final-premium.mp4: the Tidewatch film with a finished look, a narrated script that explains the app, and a voice that is paced like speech.

Run (in this order, from this folder):
  uv run --no-sync --with kokoro-onnx --with soundfile python build_voice.py <Kokoro model folder>   # voice.wav, plan.json
  uv run --no-sync --with numpy python build_music.py                                               # music.wav, same length
  ffmpeg -i voice.wav -c:a aac -b:a 128k voice.m4a ; ffmpeg -i music.wav -c:a aac -b:a 128k music.m4a
  uv run --no-sync python build_premium.py
Needs the promo's generated clips and app frames (see build_shots.py), plus captions.srt. It writes the shot clips to work/
(not tracked) and the film to final-premium.mp4. The old final.mp4 is left alone.

How it works:
  * plan.json (from build_voice.py) holds each shot's length, so every shot is exactly as long as the passage spoken over it;
  * the phone footage is retimed to the words (APP below): stretches where the app moves play at normal speed, stretches where
    it stands still are held or skipped, so the screen shows each thing as the voice says it and nothing is slowed down;
  * shots dissolve into each other (0.6 s, centred on the cut);
  * every shot drifts: a slow push-in, and a slow sideways slide behind the phone;
  * the phone sits on a soft shadow and glides across before a dissolve instead of ghosting;
  * one colour grade, a soft vignette and fine film grain over the whole film;
  * captions in Segoe UI with a fade and a short rise, beside the phone on the phone shots, under the picture on the others;
  * the voice gets a high-pass, a touch of presence and a light compressor, and the music ducks under it;
  * the film fades in from black and out to black; 1920x1080, slower and cleaner encode.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from build_shots import FPS, H, SOURCE, SPLASH_DONE, W

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
OUT = HERE / "final-premium.mp4"

PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
SECONDS = [s["seconds"] for s in PLAN["shots"]]
TOTAL = PLAN["total"]

DISSOLVE = 0.6  # seconds, centred on the cut
HEAD = TAIL = DISSOLVE / 2
PHONE_H = 820
PHONE_SRC_H = 900  # the app frame is scaled to this once, then everything is scaled together
PAD = 110  # room around the phone for its shadow
SHADOW_DROP = 26
PHONE_Y = 455  # phone centre, pixels from the top
BLUR = 26
FONT = "Segoe UI Semibold"
FONTS_DIR = "C\\\\:/Windows/Fonts"
SHORE_SECONDS = 9.8  # a shot that needs more than this much shore clip plays it forwards then backwards (it is blurred behind the phone)

# (name, seconds, clip, clip start, backdrop, phone); the phone is (centre as a fraction of the width, how the footage runs)
SHOTS = [
    ("shot-01.mp4", SECONDS[0], "shore.mp4", 0.0, "none", None),
    ("shot-02.mp4", SECONDS[1], "shore.mp4", 1.0, "full", (0.50, "app")),
    ("shot-03.mp4", SECONDS[2], "shore.mp4", 0.5, "full", (0.66, "app")),
    ("shot-04.mp4", SECONDS[3], "shore.mp4", 1.5, "full", (0.66, "app")),
    ("shot-05.mp4", SECONDS[4], "shore.mp4", 1.0, "full", (0.66, "app")),
    ("shot-06.mp4", SECONDS[5], "dinghy.mp4", 0.0, "none", None),
    ("shot-07.mp4", SECONDS[6], "dinghy.mp4", SECONDS[5], "ramp", (0.50, "end")),
]
# slow slide of the backdrop behind each phone shot: from, to (fraction of the spare width)
PAN = {"shot-02.mp4": (0.35, 0.65), "shot-03.mp4": (0.7, 0.3), "shot-04.mp4": (0.3, 0.7), "shot-05.mp4": (0.7, 0.3), "shot-07.mp4": (0.5, 0.5)}
# phone glides sideways just before a dissolve, so it lands where the next shot's phone already is
GLIDE_TO = {"shot-02.mp4": 0.66}

# App recording time (seconds) at each moment of a phone shot: (seconds into the shot, seconds into the recording).
# Between two points the footage runs straight; a repeated time is a jump over a stretch where the screen does not change.
# Where the app changes in the recording: splash done 1.9, list in 2.07-2.47, chart in 3.63-5.03, signal lost 8.67,
# Offline badge 9.17-9.37, data pack 10.40-10.90, price sheet 12.53-13.57, Unlock tapped 15.33-15.73.
APP = {
    "shot-02.mp4": [(0, 0), (1.9, 1.9), (2.2, 1.9), (2.8, 2.5)],  # splash while "Tidewatch keeps that answer", the list as "your favorite spots" starts
    "shot-03.mp4": [(0, 3.5), (0.5, 3.5), (2.1, 5.1), (6.9, 5.1), (8.4, 6.6)],  # the chart opens as "next high water" is said; the marker and the list arrive with their words
    "shot-04.mp4": [(0, 8.5), (0.83, 8.5), (1.73, 9.4), (3.5, 9.4), (3.5, 10.3), (4.4, 11.2)],  # signal lost on "lose your signal", Offline badge on "nothing changes", data pack on "tide data"
    "shot-05.mp4": [(0, 12.4), (0.3, 12.4), (1.5, 13.6), (3.2, 13.6), (3.2, 15.2), (3.8, 15.8)],  # price sheet opens with "four ninety-nine", Unlock is tapped on "you pay once"
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def app_time(keys: list[tuple[float, float]], t: float) -> float:
    if t < keys[0][0]:
        return keys[0][1]
    i = max(n for n, (kt, _) in enumerate(keys) if kt <= t)
    kt, ka = keys[i]
    if i + 1 < len(keys) and keys[i + 1][0] > kt:
        nt, na = keys[i + 1]
        return ka + (na - ka) * (t - kt) / (nt - kt)
    return ka


def app_frames(name: str, head: float, dur: float) -> Path:
    """A frame list for ffmpeg's concat reader: one recorded app frame per output frame, chosen by APP."""
    frames = SOURCE / "app" / "frames"
    last = len(list(frames.glob("f*.png"))) - 1
    lines = []
    for i in range(round(dur * FPS)):
        a = app_time(APP[name], i / FPS - head)
        lines.append(f"file '{(frames / f'f{min(max(round(a * FPS), 0), last):05d}.png').as_posix()}'")
        lines.append(f"duration {1 / FPS:.6f}")
    lines.append(lines[-2])
    out = WORK / f"{name}.frames.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def shot(index: int, spec: tuple) -> Path:
    name, seconds, clip, start, blur, phone = spec
    head = HEAD if index > 0 else 0.0
    tail = TAIL if index < len(SHOTS) - 1 else 0.0
    dur = head + seconds + tail
    out = WORK / name
    source = SOURCE / "gen" / clip
    if not source.is_file():
        sys.exit(f"missing {source}; the film reuses the promo's generated clips")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start)]

    pre, src = "", "[0:v]"
    if clip == "shore.mp4" and start + dur > SHORE_SECONDS:
        seg = dur / 2 + 0.1
        cmd += ["-t", f"{seg + 0.2:.3f}"]
        pre = (f"[0:v]trim=duration={seg:.3f},setpts=PTS-STARTPTS,fps={FPS},split[pa][pb];"
               f"[pb]reverse,setpts=PTS-STARTPTS[pr];[pa][pr]concat=n=2:v=1:a=0[src];")
        src = "[src]"
    cmd += ["-i", str(source)]

    fit = f"setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    if phone is None:
        zoom = f"(1+0.07*t/{dur})"
        # the crop reads the picture size once, so the centre is worked out from the live zoom instead
        crop = f"crop={W}:{H}:x='{W}*({zoom}-1)/2':y='{H}*({zoom}-1)/2'"
        finish = ",unsharp=5:5:0.5:5:5:0"
    else:
        p0, p1 = PAN[name]
        zoom = f"(1.06+0.06*t/{dur})"
        finish = ""
        if blur == "ramp":
            # carries on from the framing the shot before ends on, so the dissolve between them does not double the picture
            prev_dur = SECONDS[index - 1] + HEAD + TAIL
            zoom = f"({1 + 0.07 * SECONDS[index - 1] / prev_dur:.4f}+{0.07 / prev_dur:.5f}*t)"
            finish = ",unsharp=5:5:0.5:5:5:0"
            crop = f"crop={W}:{H}:x='{W}*({zoom}-1)/2':y='{H}*({zoom}-1)/2'"
        else:
            crop = f"crop={W}:{H}:x='(iw-{W})*({p0}+({p1}-{p0})*t/{dur})':y='(ih-{H})/2'"
    move = f"scale=w='trunc({W}*{zoom}/2)*2':h=-2:eval=frame,{crop}"
    base = f"{src}{fit},{move}{finish},trim=duration={dur},setpts=PTS-STARTPTS"

    if phone is None:
        graph = f"{pre}{base},format=yuv420p[v]"
    else:
        cx, mode = phone
        frames = SOURCE / "app" / "frames"
        if mode == "end":
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", str(frames / f"f{SPLASH_DONE:05d}.png")]
            app = "[1:v]format=rgba"
        else:
            cmd += ["-f", "concat", "-safe", "0", "-i", str(app_frames(name, head, dur))]
            app = f"[1:v]fps={FPS},format=rgba"
        soft = f"gblur=sigma={BLUR},eq=brightness=-0.14:saturation=1.05"
        if blur == "ramp":
            bg = (
                f"{base},split[sharp][blurin];[blurin]{soft}[blurred];"
                f"[sharp][blurred]blend=all_expr='A*(1-min(T/1.4,1))+B*min(T/1.4,1)'[bg]"
            )
            fade = ",fade=t=in:st=0.3:d=0.9:alpha=1"
        else:
            bg = f"{pre}{base},{soft}[bg]"
            fade = ""
        k = f"({PHONE_H}/{PHONE_SRC_H}*(1+0.04*t/{dur}))"
        card = (
            f"{app},scale=-2:{PHONE_SRC_H},split[pa][pb];"
            f"[pa]pad=iw+{2 * PAD}:ih+{2 * PAD}:{PAD}:{PAD}:color=black@0[pc];"
            f"[pb]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.7,"
            f"pad=iw+{2 * PAD}:ih+{2 * PAD}:{PAD}:{PAD + SHADOW_DROP}:color=black@0,gblur=sigma=30[sh];"
            f"[sh][pc]overlay=0:0:format=auto,format=rgba{fade},"
            f"scale=w='trunc(iw*{k}/2)*2':h='trunc(ih*{k}/2)*2':eval=frame[ph]"
        )
        px = f"{cx}"
        if name in GLIDE_TO:
            g0 = dur - DISSOLVE - 0.8  # finishes as the dissolve starts
            u = f"clip((t-{g0})/0.8,0,1)"
            px = f"({cx}+({GLIDE_TO[name]}-{cx})*{u}*{u}*(3-2*{u}))"
        graph = (
            f"{bg};{card};"
            f"[bg][ph]overlay=x='main_w*{px}-overlay_w/2':y='{PHONE_Y}-overlay_h/2':eval=frame:shortest=1,format=yuv420p[v]"
        )
    cmd += ["-filter_complex", graph, "-map", "[v]", "-t", str(dur), "-r", str(FPS), "-an",
            "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", str(out)]
    run(cmd)
    print(f"built {name} ({dur:.1f}s)")
    return out


def scrim() -> Path:
    """One soft dark gradient: left edge (for captions beside the phone) and bottom (for captions under the picture)."""
    out = WORK / "scrim.png"
    alpha = "255*max(0.5*pow(clip(1-X/1050,0,1),1.6),0.6*pow(clip((Y-690)/390,0,1),1.6))"
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H},format=rgba,geq=r=0:g=0:b=0:a='{alpha}'",
         "-frames:v", "1", str(out)])
    return out


def ts(value: str) -> str:
    h, m, rest = value.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{ms[:2]}"


# Captions beside the phone (the phone shots that carry the explaining); the rest sit under the picture
LEFT = set(range(6, 18))


def captions() -> Path:
    blocks = re.split(r"\n\s*\n", (HERE / "captions.srt").read_text(encoding="utf-8").strip())
    events = []
    for i, block in enumerate(blocks):
        lines = block.splitlines()
        a, b = (ts(x.strip()) for x in lines[1].split("-->"))
        if i in LEFT:
            # a line that starts with $ is the price, set large
            body = "\\N".join(("{\\fs130}" + x + "{\\fs58}") if x.startswith("$") else x for x in lines[2:])
            tag = "\\an4\\fs58\\move(150,{y2},150,{y1},0,420)".format(y1=PHONE_Y, y2=PHONE_Y + 18)
        else:
            body = " ".join(lines[2:])
            tag = "\\an2\\move(960,{y2},960,{y1},0,420)".format(y1=H - 70, y2=H - 52)
        events.append(f"Dialogue: 0,{a},{b},Cap,,0,0,0,,{{{tag}\\fad(380,320)}}{body}")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,{FONT},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,1.2,0,1,0,3,2,150,150,70,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    out = WORK / "captions.ass"
    out.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out


def sound() -> Path:
    """Voice cleaned up a little (the synth is dry and a little dull), music ducked under it, brought to a normal listening level (-16 LUFS), 48 kHz."""
    out = WORK / "sound.m4a"
    voice = ("highpass=f=75,equalizer=f=3000:t=q:w=1:g=2,"
             "acompressor=threshold=0.125:ratio=2.5:attack=12:release=200:makeup=1.4,aresample=48000,asplit=2[v][key]")
    graph = (
        f"[0:a]{voice};"
        "[1:a]aresample=48000,volume=0.32[m];"
        "[m][key]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=450[duck];"
        "[v][duck]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000[a]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-i", str(HERE / "voice.m4a"), "-i", str(HERE / "music.m4a"),
         "-filter_complex", graph, "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL}", str(out)])
    return out


def film(shots: list[Path], scrim_png: Path, ass: Path, audio: Path) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for s in shots:
        cmd += ["-i", str(s)]
    cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(scrim_png), "-i", str(audio)]
    n = len(shots)
    parts = []
    last = "[0:v]"
    start = 0.0
    for i in range(1, n):
        start += SECONDS[i - 1]
        parts.append(f"{last}[{i}:v]xfade=transition=fade:duration={DISSOLVE}:offset={start - HEAD:.3f}[x{i}]")
        last = f"[x{i}]"
    grade = (
        f"{last}format=gbrp,eq=contrast=1.05:saturation=1.1:brightness=0.02:gamma=1.05,"
        "colorbalance=rs=-0.03:bs=0.05:rm=0.0:bm=0.02:rh=0.05:gh=0.01:bh=-0.05,"
        "vignette=angle=PI/3.6,format=yuv420p,noise=c0s=4:c0f=t+u"
        f"[g];[g][{n}:v]overlay=0:0:shortest=1,"
        f"subtitles={ass.name}:fontsdir={FONTS_DIR},"
        f"fade=t=in:st=0:d=0.7,fade=t=out:st={TOTAL - 0.7:.2f}:d=0.7,format=yuv420p[v]"
    )
    parts.append(grade)
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-map", f"{n + 1}:a", "-c:a", "copy",
            "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-t", f"{TOTAL}", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True, cwd=WORK)


def main() -> None:
    WORK.mkdir(exist_ok=True)
    only = sys.argv[1:]  # optional: shot numbers to rebuild, e.g. "3 4", and "film" to assemble; with none given, everything is built
    shots = [WORK / s[0] if only and str(i + 1) not in only else shot(i, s) for i, s in enumerate(SHOTS)]
    if not only or "film" in only:
        film(shots, scrim(), captions(), sound())
        print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
