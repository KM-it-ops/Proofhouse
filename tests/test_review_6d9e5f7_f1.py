"""A storyboard layer that cannot be drawn must not be recorded as a passing film."""

import json
import wave
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from proofhouse import studio


def _fake_media(kind, provider, model, *, out, **kwargs):
    """Stand in for the picture and voice services: a tiny picture, or two seconds of quiet sound."""
    if kind == "speech":
        path = out.with_suffix(".wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(8000)
            sound.writeframes(b"\x00\x00" * 16000)
    else:
        path = out.with_suffix(".png")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake image")
    return SimpleNamespace(status="success", code=None, message=None, path=str(path), cost={"usd": "0"})


def _pretend_render(out_dir, board, *, production, **kwargs):
    rendered = out_dir / "video-1x1.mp4"
    rendered.write_bytes(b"fake film")
    production.renders["1x1"] = str(rendered)
    return production


def _writer(script, cost):
    def reply(*args, **kwargs):
        return SimpleNamespace(status="success", code=None, message=None, cost=cost, cut_off=False,
                               admission={"worst_case_usd": "0.40"}, output_text=json.dumps(script))
    return reply


def _film(tmp_path, monkeypatch, script, cost, **more):
    monkeypatch.setattr(studio.live, "run_prompt", _writer(script, cost))
    monkeypatch.setattr(studio.media, "generate", _fake_media)
    monkeypatch.setattr(studio, "assemble_beats", _pretend_render)
    return studio.produce("Show Demo", provider_id="ollama", model="local", voice_provider="local-voice",
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "film", **more)


def test_an_undrawable_overlay_is_not_recorded_as_a_pass(tmp_path: Path, monkeypatch) -> None:
    script = {"title": "Demo", "beats": [{"say": "Meet Demo.", "base": {"kind": "living"}, "hold": 3,
                                          "layers": [{"kind": "image", "at": 0}]}]}

    made = _film(tmp_path, monkeypatch, script, {"usd": "0"})

    assert made.stopped != "finished" or any(not check["ok"] for check in made.checks), (made.stopped, made.checks)
