"""Review of the five fixes for review 6d9e5f7 (3dc8b22..f94a1e9): what they broke or left half done."""

import json
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

from proofhouse import studio

FACTS = {"product": "Demo", "summary": "A tool that makes prompts.", "facts": ["Works with 4 providers."]}
BRIEF = "Make a film about Demo"


def test_everyday_one_and_single_are_not_invented_figures() -> None:
    board = [{"say": "One command does it all, in a single step.",
              "base": {"kind": "generate", "prompt": "a single lighthouse at dusk"}}]

    assert studio._invented(board, BRIEF, FACTS) == [], \
        "Plain words like 'one' and 'single' are treated as figures the facts never give."


def test_a_spelled_out_figure_above_one_is_still_caught() -> None:
    board = [{"say": "It is ten times faster.", "base": {"kind": "generate", "prompt": "twelve robots"}}]

    found = studio._invented(board, BRIEF, FACTS)

    assert (1, None, ["10"]) in found and (1, "picture", ["12"]) in found, found


def test_dropping_a_middle_sentence_keeps_later_timings_on_their_own_sentence() -> None:
    board = [
        {"say": "Meet Demo.", "base": {"kind": "living"}},
        {"say": "Demo writes prompts. It handles 500 requests a second. Teams ship faster.",
         "base": {"kind": "living"},
         "layers": [{"kind": "lower_third", "title": "Ship", "at": "phrase 3 start", "until": "phrase 2 end"}]},
        {"say": "Try Demo today.", "base": {"kind": "living"}},
    ]

    studio.settle_gaps(board, brief=BRIEF, seconds=12, facts=FACTS, footage=[], voiced=True, pictures=False)

    row = next(r for r in board if "Teams ship faster." in str(r.get("say", "")))
    assert "500" not in row["say"], row
    layer = row["layers"][0]
    assert layer["at"] == "phrase 2 start", f"the overlay timed to 'Teams ship faster.' now starts at {layer['at']}"
    assert layer["until"] == "phrase 1 end", f"the overlay that ended with the dropped line now ends at {layer['until']}"


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


def test_a_prompted_layer_on_a_footage_beat_reaches_the_film(tmp_path: Path, monkeypatch) -> None:
    facts = {**FACTS, "commands": [{"id": "version", "argv": [sys.executable, "-c", "print('demo 1.0')"],
                                    "shows": "the installed version answering"}]}
    script = {"title": "Demo", "beats": [
        {"say": "Meet Demo.", "base": {"kind": "living"}, "hold": 3},
        {"say": "Here it is.", "base": {"kind": "capture", "ref": "version"}, "hold": 3,
         "layers": [{"kind": "image", "prompt": "a calm workshop", "at": 0}]},
        {"say": "It makes prompts.", "base": {"kind": "living"}, "hold": 3},
        {"say": "Try Demo today.", "base": {"kind": "living"}, "hold": 3},
    ]}
    rendered: list[list[dict]] = []

    def writer(*args, **kwargs):
        return SimpleNamespace(status="success", code=None, message=None, cost={"usd": "0"}, cut_off=False,
                               admission={"worst_case_usd": "0"}, output_text=json.dumps(script))

    def pretend_render(out_dir, script, *, production, **kwargs):
        rendered.append(script["beats"])
        (out_dir / "video-1x1.mp4").write_bytes(b"fake film")
        production.renders["1x1"] = str(out_dir / "video-1x1.mp4")
        return production

    monkeypatch.setattr(studio.live, "run_prompt", writer)
    monkeypatch.setattr(studio.media, "generate", _fake_media)
    monkeypatch.setattr(studio.recording, "record_command", lambda argv, cwd: [])
    monkeypatch.setattr(studio.recording, "terminal_timeline", lambda display, chunks, **kw: {"seconds": 2})
    monkeypatch.setattr(studio, "assemble_beats", pretend_render)

    made = studio.produce("Show Demo", provider_id="ollama", model="local", voice_provider="local-voice",
                          visual_provider="local-images", visual_model="floor", seconds=12, formats=("1x1",),
                          out_dir=tmp_path / "film", facts=facts, allow_commands=True)

    assert made.stopped == "finished", made.stopped
    footage_beats = [row for row in rendered[0] if row.get("real")]
    assert footage_beats, (rendered[0], made.checks)
    images = [lay for lay in footage_beats[0].get("layers") or [] if lay.get("kind") == "image"]
    assert images and all("file" in lay and "prompt" not in lay for lay in images), \
        f"the footage beat goes to the film with its picture layer never attached: {images}"
