"""A program on this machine is a media service too: one line of data, run through the spend gate at no charge."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from proofhouse import cli, media

# Stands in for Kokoro, Piper or a local image maker: reads the words on stdin, writes the file it is told to.
SPEAKER = (
    "import sys\n"
    "text = sys.stdin.read()\n"
    "open(sys.argv[2], 'w', encoding='utf-8').write(sys.argv[1] + '|' + text)\n"
)


def _add(tmp_path: Path, entry: dict) -> None:
    (tmp_path / "t.json").write_text(json.dumps(entry), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0


def _speaker(tmp_path: Path, **run: object) -> dict:
    script = tmp_path / "speak.py"
    script.write_text(SPEAKER, encoding="utf-8")
    return {"id": "my-voice", "name": "My voice", "kinds": ["speech"], "unit": "request",
            "run": {"command": [sys.executable, str(script), "{voice}", "{out}"], "stdin": "{prompt}", "ext": "txt", **run}}


def test_a_local_program_makes_the_file_and_costs_nothing(tmp_path: Path) -> None:
    _add(tmp_path, _speaker(tmp_path))
    words = 'Say "what" you want & | > it is kept'  # shell characters reach the program as plain text
    result = media.generate("speech", "my-voice", "any", prompt=words, out=tmp_path / "line1",
                            params={"voice": "af_heart"})
    assert result.status == "success", result.message
    assert result.path.endswith("line1.txt")
    assert Path(result.path).read_text(encoding="utf-8") == "af_heart|" + words
    assert result.admission["decision"] == "admitted" and result.admission["worst_case_usd"] == "0"
    assert result.admission["price"]["source"] == "on this machine: no charge" and result.admission["body_sha256"]


def test_a_program_can_hand_the_file_back_on_stdout(tmp_path: Path) -> None:
    script = tmp_path / "echo.py"
    script.write_text("import sys\nsys.stdout.buffer.write(b'RIFF' + sys.argv[1].encode())\n", encoding="utf-8")
    _add(tmp_path, {"id": "piped", "kinds": ["music"], "run": {"command": [sys.executable, str(script), "{prompt}"],
                                                              "output": "stdout", "ext": "wav"}})
    result = media.generate("music", "piped", "m", prompt="calm pad", out=tmp_path / "bed")
    assert result.status == "success", result.message
    assert Path(result.path).read_bytes() == b"RIFFcalm pad" and result.path.endswith("bed.wav")


def test_a_program_that_fails_or_is_missing_is_reported_plainly(tmp_path: Path) -> None:
    script = tmp_path / "broken.py"
    script.write_text("import sys\nsys.stderr.write('model file not found\\n')\nsys.exit(3)\n", encoding="utf-8")
    _add(tmp_path, {"id": "broken", "kinds": ["image"], "run": {"command": [sys.executable, str(script), "{out}"], "ext": "png"}})
    failed = media.generate("image", "broken", "m", prompt="a fox", out=tmp_path / "fox")
    assert failed.status == "error" and "exit code 3" in failed.message and "model file not found" in failed.message
    _add(tmp_path, {"id": "absent", "kinds": ["image"], "run": {"command": ["no-such-program-xyz", "{out}"], "ext": "png"}})
    missing = media.generate("image", "absent", "m", prompt="a fox", out=tmp_path / "fox2")
    assert missing.status == "error" and "no-such-program-xyz" in missing.message
    silent = tmp_path / "silent.py"
    silent.write_text("pass\n", encoding="utf-8")
    _add(tmp_path, {"id": "silent", "kinds": ["image"], "run": {"command": [sys.executable, str(silent), "{out}"], "ext": "png"}})
    empty = media.generate("image", "silent", "m", prompt="a fox", out=tmp_path / "fox3")
    assert empty.status == "error" and "wrote nothing" in empty.message


def test_a_program_that_runs_too_long_is_stopped(tmp_path: Path) -> None:
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    _add(tmp_path, {"id": "slow", "kinds": ["video"], "run": {"command": [sys.executable, str(script), "{out}"], "ext": "mp4",
                                                             "timeout": 1}})
    result = media.generate("video", "slow", "m", prompt="a fox", out=tmp_path / "clip")
    assert result.status == "error" and "1 s" in result.message


def test_bad_program_lines_are_refused_before_anything_runs() -> None:
    def parse(run: object, origin: str = "yours") -> media.MediaProvider:
        return media._parse({"id": "p", "kinds": ["speech"], "run": run}, origin)

    good = {"command": ["kokoro", "{out}"], "ext": "wav"}
    assert parse(good).local and parse(good).run is not None
    with pytest.raises(media.MediaError, match="list"):
        parse({"command": "kokoro --out {out}", "ext": "wav"})  # a shell string, never
    with pytest.raises(media.MediaError, match="program"):
        parse({"command": ["{prompt}", "x"], "ext": "wav"})  # the program itself is never filled in
    with pytest.raises(media.MediaError, match="ext"):
        parse({"command": ["kokoro"]})
    with pytest.raises(media.MediaError, match="output"):
        parse({"command": ["kokoro"], "ext": "wav", "output": "screen"})
    with pytest.raises(media.MediaError, match="out"):
        parse({"command": ["kokoro", "--fast"], "ext": "wav"})  # nowhere to write the file, and not on stdout
    for origin in ("learned", "add-on learned", "add-on somepack"):
        with pytest.raises(media.MediaError, match="program"):
            parse(good, origin)  # only the shipped table and your own file may run programs


def test_the_gate_builds_the_exact_command_that_runs(tmp_path: Path) -> None:
    profile = media._parse(_speaker(tmp_path), "yours")
    url, body, units = media.build_request(profile, "any", {"prompt": "hello", "voice": "af_heart", "out": "o.txt"})
    assert url == "program:my-voice" and units == 1
    assert body == {"command": [sys.executable, str(tmp_path / "speak.py"), "af_heart", "o.txt"], "stdin": "hello"}


def test_a_value_that_looks_like_an_option_never_fills_a_program_word(tmp_path: Path) -> None:
    profile = media._parse(_speaker(tmp_path), "yours")
    with pytest.raises(media.MediaError, match="option"):  # the program would read it as a switch, not a voice
        media.build_request(profile, "any", {"prompt": "hello", "voice": "--output=C:/elsewhere", "out": "o.txt"})
    _, body, _ = media.build_request(profile, "any", {"prompt": "-o C:/elsewhere", "voice": "af_heart", "out": "o.txt"})
    assert body["stdin"] == "-o C:/elsewhere"  # words on stdin are only ever words


def test_a_program_is_found_on_path_never_in_the_current_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real, here = tmp_path / "bin", tmp_path / "film"
    name = "speakprog" + (".exe" if os.name == "nt" else "")
    for folder in (real, here):
        folder.mkdir()
        (folder / name).write_bytes(b"")
        (folder / name).chmod(0o755)
    monkeypatch.chdir(here)  # a downloaded film folder with its own "speakprog" in it
    monkeypatch.setenv("PATH", str(real))
    found = media._find_program("speakprog")
    assert found is not None and os.path.normcase(found) == os.path.normcase(str(real / name))
    monkeypatch.setenv("PATH", os.pathsep.join([".", ""]))  # relative PATH entries mean the current folder too
    assert media._find_program("speakprog") is None
    assert media._find_program(str(here / name)) == str(here / name)  # a full path is taken as written
    assert media._find_program("./" + name) is None  # a relative path depends on where the command was run


def test_media_list_shows_a_program_as_local(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _add(tmp_path, _speaker(tmp_path))
    capsys.readouterr()
    assert cli.main(["media", "list", "--json"]) == 0
    rows = {r["id"]: r for r in json.loads(capsys.readouterr().out)["media_providers"]}
    assert rows["my-voice"]["local"] is True
