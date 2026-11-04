"""A voice that costs nothing: the speech engine this machine already has speaks the words.

The shipped ``local-voice`` entry in the media list runs ``python -m proofhouse.local_voice --out line.wav --voice NAME``
with the words on stdin. It uses the first engine it finds: Kokoro (if the ``kokoro`` package is installed), Piper (if
``piper`` is on PATH and ``PIPER_MODEL`` names a voice file), macOS ``say``, Windows speech, then espeak-ng or espeak.
``PROOFHOUSE_VOICE_ENGINE`` picks one by name. The words always reach the engine on stdin, never on a command line.
A paid voice service sounds better; this is the floor, not the ceiling.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

ENGINES = ("kokoro", "piper", "say", "windows", "espeak-ng", "espeak")
TIMEOUT = 600

# Windows speech, reading the words from stdin as UTF-8 and writing 16-bit mono WAV. Nothing is pasted into the script:
# the file and the voice come in through the environment.
_WINDOWS = (
    "$ErrorActionPreference='Stop';"
    "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
    "Add-Type -AssemblyName System.Speech;"
    "$t=[Console]::In.ReadToEnd();"
    "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$want=$env:PH_VOICE_NAME;"
    "if($want){foreach($v in $s.GetInstalledVoices()){if($v.Enabled -and $v.VoiceInfo.Name -like ('*'+$want+'*'))"
    "{$s.SelectVoice($v.VoiceInfo.Name);break}}};"
    "$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050,"
    "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono);"
    "$s.SetOutputToWaveFile($env:PH_VOICE_OUT,$f);$s.Speak($t);$s.Dispose()"
)


class VoiceError(RuntimeError):
    """No engine could speak the words."""


def _program(name: str) -> str | None:
    from .media import _find_program  # PATH's full folders only, never the current folder

    return _find_program(name)


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _ready(engine: str) -> bool:
    if engine == "kokoro":
        return _has_module("kokoro")
    if engine == "piper":
        return _program("piper") is not None and bool(os.environ.get("PIPER_MODEL"))
    if engine == "windows":
        return os.name == "nt" and _program("powershell") is not None
    return _program(engine) is not None


def pick() -> str:
    """The engine that will speak: the one named in PROOFHOUSE_VOICE_ENGINE, or the first this machine has."""
    asked = os.environ.get("PROOFHOUSE_VOICE_ENGINE", "").strip().lower()
    if asked:
        if asked not in ENGINES:
            raise VoiceError(f"PROOFHOUSE_VOICE_ENGINE must be one of {', '.join(ENGINES)}")
        if not _ready(asked):
            raise VoiceError(f"the {asked} speech engine is not installed here")
        return asked
    for engine in ENGINES:
        if _ready(engine):
            return engine
    raise VoiceError("no speech engine on this machine; install Kokoro, Piper or espeak-ng, or name a voice service")


def available() -> bool:
    try:
        pick()
    except VoiceError:
        return False
    return True


def _kokoro(text: str, out: Path, voice: str) -> None:
    from array import array

    from kokoro import KPipeline  # type: ignore[import-not-found]

    name = voice if re.fullmatch(r"[a-z]{2}_[a-z]+", voice or "") else "af_heart"
    pipeline = KPipeline(lang_code=name[0])
    pcm = array("h")
    for _, _, audio in pipeline(text, voice=name):
        pcm.extend(int(max(-1.0, min(1.0, float(v))) * 32767) for v in audio)
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm.tobytes())


def _command(engine: str, out: Path, voice: str) -> tuple[list[str], dict[str, str] | None]:
    if engine == "piper":
        return [str(_program("piper")), "--model", os.environ["PIPER_MODEL"], "--output_file", str(out)], None
    if engine == "say":
        command = [str(_program("say")), "-o", str(out), "--data-format=LEI16@22050", "-f", "-"]
        return (command[:1] + ["-v", voice] + command[1:] if voice and voice != "alloy" else command), None
    if engine == "windows":
        env = {**os.environ, "PH_VOICE_OUT": str(out), "PH_VOICE_NAME": "" if voice == "alloy" else voice}
        return [str(_program("powershell")), "-NoProfile", "-NonInteractive", "-Command", _WINDOWS], env
    command = [str(_program(engine)), "-w", str(out), "--stdin"]
    if re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)*", voice or ""):
        command[1:1] = ["-v", voice]
    return command, None


def speak(text: str, out: Path, *, voice: str = "", engine: str | None = None) -> Path:
    """Speak ``text`` into a WAV file at ``out``."""
    if not text.strip():
        raise VoiceError("there are no words to speak")
    engine = engine or pick()
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    if engine == "kokoro":
        _kokoro(text, out, voice)
    else:
        command, env = _command(engine, out, voice)
        try:
            done = subprocess.run(command, input=text.encode("utf-8"), capture_output=True, timeout=TIMEOUT, check=False, env=env)
        except subprocess.TimeoutExpired:
            raise VoiceError(f"{engine} ran past {TIMEOUT} s and was stopped") from None
        except OSError as exc:
            raise VoiceError(f"{engine} could not start ({type(exc).__name__})") from None
        if done.returncode != 0:
            lines = done.stderr.decode("utf-8", "replace").strip().splitlines()
            raise VoiceError(f"{engine} stopped with exit code {done.returncode}" + (f": {lines[-1][:300]}" if lines else ""))
    if not out.is_file() or out.stat().st_size == 0:
        raise VoiceError(f"{engine} finished but wrote no sound")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m proofhouse.local_voice", description="Speak the words on stdin into a WAV file.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--voice", default="")
    args = parser.parse_args(argv)
    try:
        speak(sys.stdin.buffer.read().decode("utf-8", "replace"), args.out, voice=args.voice)
    except VoiceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
