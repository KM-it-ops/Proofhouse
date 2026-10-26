"""Makes voice.wav and music.wav for the Tidewatch video with no key and no paid call.

The voice is the Windows built-in speech engine. The music is a soft chord pad that FFmpeg
synthesises. Run it from this folder: python generate_sound.py
"""

import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
total = sum(int(shot["seconds"]) for shot in script["shots"])

speech = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$s.Rate = 0; "
    "$s.SetOutputToWaveFile($env:VOICE_OUT); "
    "$s.Speak($env:VOICE_TEXT); "
    "$s.Dispose()"
)
subprocess.run(
    ["powershell", "-NoProfile", "-Command", speech],
    check=True,
    env={**os.environ, "VOICE_OUT": str(HERE / "voice.wav"), "VOICE_TEXT": script["voiceover"]},
)

chord = [110.0, 164.81, 220.0, 277.18]
expr = "+".join(f"0.05*sin(2*PI*{f}*t)*(0.6+0.4*sin(2*PI*0.15*t))" for f in chord)
subprocess.run(
    [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={total}",
        "-af", f"afade=t=in:d=2,afade=t=out:st={total - 2}:d=2",
        str(HERE / "music.wav"),
    ],
    check=True,
)
print("voice.wav and music.wav written", file=sys.stderr)
