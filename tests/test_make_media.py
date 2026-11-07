"""Media makes ask first too: a video, image, voice or music piece is interviewed, made, checked, judged, improved and delivered."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from proofhouse import cli, live, live_cli, make, make_media, studio
from proofhouse import make_interview as mi
from proofhouse.optimize import cli as optimize_cli

from test_learn_unknowns import MEDIA
from test_make_interview import QUESTIONS, Answers

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg not installed")

# Stand-ins for a local image maker and a local voice: read the words on stdin, write a real file with FFmpeg.
PAINTER = (
    "import subprocess, sys\n"
    "sys.stdin.read()\n"
    "subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=640x480', '-frames:v', '1', sys.argv[1]], check=True)\n"
)
SPEAKER = (
    "import subprocess, sys\n"
    "sys.stdin.read()\n"
    "subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', sys.argv[1]], check=True)\n"
)


@pytest.fixture(autouse=True)
def _no_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(optimize_cli, "_stdin_is_terminal", lambda: False)


def _add(tmp_path: Path, entry: dict) -> None:
    path = tmp_path / f"{entry['id']}.json"
    path.write_text(json.dumps(entry), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(path)]) == 0


@pytest.fixture
def programs(tmp_path: Path) -> None:
    """Two programs on this machine, added as data: a painter (image) and a speaker (speech). Both cost nothing."""
    for name, script, kind, ext in (("my-painter", PAINTER, "image", "png"), ("my-voice", SPEAKER, "speech", "wav")):
        path = tmp_path / f"{name}.py"
        path.write_text(script, encoding="utf-8")
        _add(tmp_path, {"id": name, "name": name.replace("-", " ").title(), "kinds": [kind], "unit": "request",
                        "run": {"command": [sys.executable, str(path), "{out}"], "stdin": "{prompt}", "ext": ext}})


class Director:
    """A text model for media makes: answers by what each call asks for, and keeps every prompt it saw."""

    def __init__(self, scores: list[int] | None = None, shapes: list[str] | None = None, blind: bool = False) -> None:
        self.scores = list(scores or [9])
        self.shapes = shapes
        self.blind = blind  # a model that cannot take pictures
        self.calls: list[str] = []
        self.seen: dict[str, list[str]] = {}
        self.pictures: list[str] = []
        self.json_mode: dict[str, list[bool]] = {}  # per role: was the reply asked for as JSON

    def __call__(self, request: live.Request) -> live.Response:
        body = json.loads(request.body_bytes)
        words, pictures = [], []
        for m in body["messages"]:
            if isinstance(m["content"], str):
                words.append(m["content"])
                continue
            for part in m["content"]:
                if part["type"] == "text":
                    words.append(part["text"])
                else:
                    pictures.append(part["image_url"]["url"])
        text = " ".join(words)
        if pictures and self.blind:
            self.calls.append("refused picture")
            return live.Response(400, {"error": {"message": "this model does not take pictures"}})
        self.pictures += pictures
        if text.startswith("You are an expert prompt engineer. You generate"):
            role, content = "questions", QUESTIONS
        elif text.startswith("You are about to"):
            role, content = "say back", "- What it is: a short piece, understood"
        elif text.startswith("You plan a"):
            role = "plan"
            n = self.calls.count("plan") + 1
            plan = {"prompt": f"plan {n}: a fox in a red scarf at dawn", "voice": "warm", "seconds": 2}
            if self.shapes is not None:
                plan["shapes"] = self.shapes
            content = json.dumps(plan)
        elif text.startswith("You judge media"):
            n = self.calls.count("judge") + 1
            role, content = "judge", json.dumps({"score": self.scores.pop(0), "missing": [f"gap {n}"], "fix": f"fix number {n}"})
        elif text.startswith("Proofhouse generates images"):
            role, content = "research", json.dumps({**MEDIA, "sources": ["https://api.acme.example/docs"]})
        else:
            role, content = "other", "{}"
        self.calls.append(role)
        self.seen.setdefault(role, []).append(text)
        self.json_mode.setdefault(role, []).append(body.get("response_format") == {"type": "json_object"})
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 10, "completion_tokens": 5}})


def _route(monkeypatch: pytest.MonkeyPatch, model: Director) -> None:
    real = make_media.make_media
    monkeypatch.setattr(make_media, "make_media", lambda *a, **k: real(*a, **{**k, "transport": model}))


def _record(folder: Path) -> dict:
    return json.loads((folder / "record.json").read_text(encoding="utf-8"))


# --- every media kind asks first ---------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["image", "voice", "music", "video"])
def test_a_media_make_with_no_terminal_pauses_and_asks_which_service_makes_it(
        kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    model = Director()
    _route(monkeypatch, model)
    folder = tmp_path / "o"
    code = cli.main(["make", "a fox at dawn", "--kind", kind, "--provider", "ollama", "--model", "m", "--out", str(folder)])
    out = capsys.readouterr().out
    assert code == live_cli.EXIT_WAITING
    assert "waiting for your answers" in out and f"--answers {folder / 'answers.json'}" in out
    assert model.calls == []  # nothing made blind, not even the questions before the service is known
    asked = (folder / "questions.md").read_text(encoding="utf-8")
    assert "Which service" in asked
    if kind == "image":
        assert "openai-images" in asked  # examples come from the media list
    assert not (folder / "record.json").exists() and not (folder / "v1").exists()


def test_the_target_question_names_services_from_the_media_list_not_from_code(tmp_path: Path, programs: None) -> None:
    question = mi.target_question("voice")
    assert "my-voice" in question and "elevenlabs" in question
    assert "my-painter" not in question  # a painter cannot make a voice
    assert "my-painter" in mi.target_question("image") and "my-voice" in mi.target_question("video")


def test_the_questions_cover_what_a_media_piece_needs_and_the_say_back_says_where_it_will_be_shown(
        tmp_path: Path, programs: None) -> None:
    model = Director()
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter", {"must": "a red scarf"}, [None]), transport=model)
    assert made.waiting is not None and made.stopped == "waiting for your answers"
    system = model.seen["questions"][0]
    for need in ("what it is for", "who will", "how long", "look", "voice", "music", "where it will be shown", "shapes"):
        assert need in system, need
    assert "Where it will be shown" in model.seen["say back"][0]
    iv = made.interview
    assert iv.target.sort == "media" and iv.target.id.startswith("image=my-painter")




def test_the_services_that_make_a_piece_are_never_taken_for_what_it_is_about(tmp_path: Path, programs: None) -> None:
    model = Director()
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter", {"must": "a red scarf"}, [None]), transport=model)
    asked = model.seen["questions"][0]
    assert "for My Painter" not in asked  # the questions are about the fox, not the painter
    assert "My Painter is only the tool that makes it" in asked and "never name it in a question" in asked
    assert "leave My Painter out" in model.seen["say back"][0]
    brief = made.interview.brief()
    # the writers and the judge are told what the tools make, never their names, so a name is never drawn
    assert "My Painter" not in brief and "my-painter" not in brief
    assert "MADE WITH: the tools the owner chose (only the tools that make it; the piece is not about them" in brief
    assert "image: makes image" in brief
    assert "MADE FOR" not in brief and "WHAT IS KNOWN ABOUT" not in brief
    assert "Made with: My Painter" in mi.questions_markdown(made.interview)
# --- the target: the media list, your own programs, and services learned on the spot -------------------

def test_a_video_target_is_split_into_roles_by_what_each_service_makes(tmp_path: Path, programs: None) -> None:
    target = mi.find_target("my-painter, my-voice and openai-speech/tts-1", "video", lambda *a: None, learned_by="x")
    roles = make_media.roles(target)
    assert roles["visuals"] == {"provider": "my-painter", "model": "local", "kind": "image"}
    assert roles["voice"] == {"provider": "my-voice", "model": "local"}  # the first voice named wins; the second has no role
    named = mi.find_target("voice: openai-speech/tts-1, my-painter", "video", lambda *a: None, learned_by="x")
    assert make_media.roles(named)["voice"] == {"provider": "openai-speech", "model": "tts-1"}


def test_a_piece_that_cannot_make_the_kind_or_names_no_model_is_refused_plainly(tmp_path: Path, programs: None) -> None:
    with pytest.raises(mi.InterviewError, match="speech, not image"):
        mi.find_target("my-voice", "image", lambda *a: None, learned_by="x")
    with pytest.raises(mi.InterviewError, match="openai-images/"):
        mi.find_target("openai-images", "image", lambda *a: None, learned_by="x")  # a web service needs its model named


def test_an_unknown_service_is_learned_by_the_model_then_waits_for_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                           capsys: pytest.CaptureFixture[str]) -> None:
    model = Director()
    _route(monkeypatch, model)
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"for": "acme-images/fast"}), encoding="utf-8")
    code = cli.main(["make", "a fox at dawn", "--kind", "image", "--provider", "ollama", "--model", "m",
                     "--answers", str(ahead), "--max-cost-usd", "1", "--out", str(tmp_path / "o")])
    err = capsys.readouterr().err
    assert model.calls == ["research"]  # learned, not refused as unknown; nothing else asked or made
    assert code != live_cli.EXIT_OK and "not approved yet" in err and "proofhouse addons approve learned acme-images" in err
    assert not (tmp_path / "o" / "v1").exists()


def test_a_paid_or_learned_service_needs_a_spending_limit_and_a_local_program_does_not(tmp_path: Path, programs: None) -> None:
    with pytest.raises(make.MakeError, match="spending limit"):
        make_media.make_media("a fox", kind="image", provider_id="ollama", model="m", out_dir=tmp_path / "paid",
                              interviewer=Answers("openai-images/gpt-image-1", {}, [True]), transport=Director())
    assert not (tmp_path / "paid" / "v1").exists()


# --- make, check, judge, improve, keep versions, deliver -----------------------------------------------

@needs_ffmpeg
def test_an_image_is_made_by_your_own_program_checked_judged_improved_and_delivered_in_the_shapes_asked_for(
        tmp_path: Path, programs: None) -> None:
    model = Director(scores=[5, 9], shapes=["16x9", "1x1"])
    folder = tmp_path / "o"
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter", {"must": "a red scarf"}, [True]), transport=model, rounds=3)
    assert made.stopped == "reached the target" and made.best_version == 2 and made.best_score == 9
    assert model.calls.count("plan") == 2 and model.calls.count("judge") == 2
    assert "fix number 1" in model.seen["plan"][1] and "fix number 1" not in model.seen["plan"][0]  # the plan changes
    assert "a red scarf" in model.seen["plan"][0]  # the interview's answers reach the plan
    assert "image size" in model.seen["judge"][0]  # the judge sees the file checks
    assert len(model.pictures) == 2 and all(p.startswith("data:image/jpeg;base64,") for p in model.pictures)
    assert "the picture itself, made smaller" in model.seen["judge"][0]  # and is told what the picture is
    for n in (1, 2):
        assert (folder / f"v{n}" / "plan.json").is_file()
        assert any(p.suffix == ".png" for p in (folder / f"v{n}").iterdir())
    record = _record(folder)
    assert record["interview_from"] == "caller" and record["kind"] == "image"
    assert record["roles"] == {"image": {"provider": "my-painter", "model": "local"}}
    assert [v["version"] for v in record["versions"]] == [1, 2]
    assert record["versions"][0]["plan"]["prompt"].startswith("plan 1") and record["versions"][1]["plan"]["prompt"].startswith("plan 2")
    assert all(c["ok"] for v in record["versions"] for c in v["checks"])
    for n, version in enumerate(record["versions"], 1):
        assert version["judged_on"]["picture"] == f"v{n}/judge-sheet.jpg" and version["judged_on"]["words_only_because"] is None
        assert (folder / version["judged_on"]["picture"]).is_file()
    assert "smaller copy of the picture for every version" in record["judging"] and "not_judged" not in record
    assert record["spent_usd"] == "0" and record["best_version"] == 2
    assert set(record["delivered"]) == {"16x9", "1x1"} and set(made.delivered) == {"16x9", "1x1"}
    for shape, (w, h) in (("16x9", (1920, 1080)), ("1x1", (1080, 1080))):
        seen = studio.probe(folder / record["delivered"][shape])
        assert (seen["width"], seen["height"]) == (w, h)


@needs_ffmpeg
def test_a_voice_is_checked_for_sound_and_delivered_as_the_file_types_asked_for(tmp_path: Path, programs: None,
                                                                                monkeypatch: pytest.MonkeyPatch,
                                                                                capsys: pytest.CaptureFixture[str]) -> None:
    model = Director(scores=[9])
    _route(monkeypatch, model)
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"for": "my-voice", "answers": {"must": "calm"}, "confirmed": True}), encoding="utf-8")
    folder = tmp_path / "o"
    code = cli.main(["make", "a welcome line", "--kind", "voice", "--provider", "ollama", "--model", "m",
                     "--answers", str(ahead), "--formats", "mp3,wav", "--out", str(folder)])
    out = capsys.readouterr().out
    assert code == live_cli.EXIT_OK, out
    record = _record(folder)
    assert record["interview_from"] == "answers file" and record["interview_preset"] == "balanced"
    assert {c["check"] for c in record["versions"][0]["checks"]} >= {"has sound", "length"}
    assert "SOUND, MEASURED" in model.seen["judge"][0] and "LUFS" in model.seen["judge"][0]  # it reads the sound, measured
    sound = record["versions"][0]["judged_on"]["sound"]
    assert 1.5 < sound["seconds"] < 2.5 and sound["silent_share"] < 0.2 and sound["loudness_lufs"] < 0
    assert record["versions"][0]["judged_on"]["picture"] is None and not model.pictures
    assert "cannot hear" in record["judging"]
    assert set(record["delivered"]) == {"mp3", "wav"}  # --formats wins over the plan
    for path in record["delivered"].values():
        seen = studio.probe(folder / path)
        assert seen["audio"] and seen["seconds"] > 1
        assert path in out.replace("\\", "/") or str(folder / path) in out


@needs_ffmpeg
def test_a_model_that_cannot_take_a_picture_judges_from_the_words_and_the_record_says_why(tmp_path: Path,
                                                                                      programs: None) -> None:
    model = Director(scores=[9], blind=True)
    folder = tmp_path / "o"
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter", {}, [True]), transport=model, rounds=2)
    assert made.best_score == 9 and model.calls.count("refused picture") == 1 and model.calls.count("judge") == 1
    assert model.seen["judge"][0].startswith("You judge media") and "cannot see the picture" in model.seen["judge"][0]
    judged = _record(folder)["versions"][0]["judged_on"]
    assert judged["picture"] is None and "could not take the picture" in judged["words_only_because"]
    assert "this model does not take pictures" in judged["words_only_because"]
    assert "never saw the picture" in _record(folder)["judging"]


@needs_ffmpeg
def test_a_model_that_refused_a_picture_is_not_sent_one_again_in_later_rounds(tmp_path: Path, programs: None) -> None:
    model = Director(scores=[5, 6], blind=True)
    folder = tmp_path / "o"
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter", {}, [True]), transport=model, rounds=2)
    assert len(made.rounds) == 2 and model.calls.count("judge") == 2
    assert model.calls.count("refused picture") == 1  # it said once that it cannot see: that is not asked again
    for version in _record(folder)["versions"]:
        assert "could not take the picture" in version["judged_on"]["words_only_because"]


@needs_ffmpeg
def test_the_plan_and_the_judge_are_asked_for_json_and_a_plan_with_no_prompt_is_asked_for_again(
        tmp_path: Path, programs: None) -> None:
    class Forgetful(Director):
        def __call__(self, request: live.Request) -> live.Response:
            reply = super().__call__(request)
            if self.calls[-1] == "plan" and self.calls.count("plan") == 2:  # round 2's plan leaves the prompt out
                reply.payload["choices"][0]["message"]["content"] = json.dumps({"seconds": 2, "shapes": ["1x1"]})
            return reply

    model = Forgetful(scores=[5, 6])
    folder = tmp_path / "o"
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter", {}, [True]), transport=model, rounds=2)
    assert len(made.rounds) == 2 and made.stopped == "rounds used up", made.stopped
    assert model.calls.count("plan") == 3 and '"prompt"' in model.seen["plan"][2]  # told what was missing
    assert all(model.json_mode["plan"]) and all(model.json_mode["judge"])
    assert [c.role for c in made.calls].count("plan fix") == 1


def test_a_plan_that_stays_without_a_prompt_stops_and_keeps_the_reply(tmp_path: Path, programs: None) -> None:
    class Empty(Director):
        def __call__(self, request: live.Request) -> live.Response:
            reply = super().__call__(request)
            if self.calls[-1] == "plan":
                reply.payload["choices"][0]["message"]["content"] = "I cannot plan that."
            return reply

    folder = tmp_path / "o"
    made = make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter", {}, [True]), transport=Empty(), rounds=2)
    assert "no plan" in made.stopped and "plan-reply.txt" in made.stopped, made.stopped
    assert (folder / "plan-reply.txt").read_text(encoding="utf-8") == "I cannot plan that."


@needs_ffmpeg
def test_the_judge_is_told_what_it_saw_is_its_own_claim(tmp_path: Path, programs: None) -> None:
    class Seeing(Director):
        def __call__(self, request: live.Request) -> live.Response:
            reply = super().__call__(request)
            if self.calls[-1] == "judge":
                content = json.loads(reply.payload["choices"][0]["message"]["content"])
                reply.payload["choices"][0]["message"]["content"] = json.dumps({"saw": "a test pattern, no fox", **content})
            return reply

    folder = tmp_path / "o"
    make_media.make_media("a fox at dawn", kind="image", provider_id="ollama", model="m", out_dir=folder,
                          interviewer=Answers("my-painter", {}, [True]), transport=Seeing(scores=[9]), rounds=1)
    record = _record(folder)
    assert record["versions"][0]["judged_on"]["saw"] == "a test pattern, no fox"
    assert "its own claim" in record["judging"]


@needs_ffmpeg
def test_a_file_that_fails_its_check_is_never_delivered(tmp_path: Path) -> None:
    broken = tmp_path / "blank.py"
    broken.write_text("import sys\nsys.stdin.read()\nopen(sys.argv[1], 'wb').write(b'not a picture')\n", encoding="utf-8")
    _add(tmp_path, {"id": "blank", "kinds": ["image"], "run": {"command": [sys.executable, str(broken), "{out}"],
                                                               "stdin": "{prompt}", "ext": "png"}})
    model = Director(scores=[10, 10])
    made = make_media.make_media("a fox", kind="image", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("blank", {}, [True]), transport=model, rounds=2)
    assert made.best_version is None and not made.delivered
    assert made.stopped == "rounds used up"
    record = _record(tmp_path / "o")
    assert any(not c["ok"] for c in record["versions"][0]["checks"]) and record["delivered"] == {}


# --- video goes through the studio, not a second engine ------------------------------------------------

def _fake_produce(seen: list[dict]):
    def produce(brief: str, **kwargs):
        seen.append({"brief": brief, **kwargs})
        out = kwargs["out_dir"]
        out.mkdir(parents=True, exist_ok=False)
        renders = {}
        for name in kwargs["formats"]:
            (out / f"film-{name}.mp4").write_bytes(b"film")
            renders[name] = str(out / f"film-{name}.mp4")
        return studio.Production(out, title="Fox", renders=renders,
                                 checks=[{"ok": True, "render": n, "check": "plays", "detail": ""} for n in renders])
    return produce


def test_a_video_is_planned_rendered_by_the_studio_improved_and_kept_by_version(tmp_path: Path, programs: None,
                                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    model = Director(scores=[4, 9], shapes=["9x16"])
    folder = tmp_path / "o"
    made = make_media.make_media("a hype video for a fox cafe", kind="video", provider_id="ollama", model="m", out_dir=folder,
                                 interviewer=Answers("my-painter, my-voice", {"must": "under a minute"}, [True]),
                                 transport=model, rounds=3)
    assert len(seen) == 2 and made.best_version == 2
    first, second = seen
    assert first["out_dir"] == folder / "v1" and second["out_dir"] == folder / "v2"
    assert first["visual_provider"] == "my-painter" and first["voice_provider"] == "my-voice"
    assert first["formats"] == ("9x16",)
    assert "under a minute" in first["brief"] and "plan 1" in first["brief"]
    assert "fix number 1" in second["brief"] and "fix number 1" not in first["brief"]  # changing the plan re-renders
    assert first["text_transport"] is model
    record = _record(folder)
    assert record["roles"]["visuals"]["provider"] == "my-painter" and record["roles"]["voice"]["provider"] == "my-voice"
    assert set(record["delivered"]) == {"9x16"}
    # the fake films are not films: no picture could be taken, so the judge read the words, and the record says why
    assert all(v["judged_on"]["words_only_because"] == "no picture could be taken from the file" for v in record["versions"])
    assert "never saw the picture" in record["judging"] and "cannot hear" in record["judging"]


def test_the_video_flags_answer_which_services_make_it(tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    model = Director()
    _route(monkeypatch, model)
    folder = tmp_path / "o"
    base = ["make", "a fox film", "--kind", "video", "--provider", "ollama", "--model", "m", "--out", str(folder),
            "--visual-provider", "my-painter", "--visual-model", "local", "--voice-provider", "my-voice"]
    assert cli.main(base + ["--seconds", "12", "--formats", "16x9"]) == live_cli.EXIT_WAITING  # the services are known
    assert model.calls == ["questions"]
    again = capsys.readouterr().out.split("then run: ", 1)[1]
    assert "--seconds 12" in again and "--formats 16x9" in again  # the run it asks for again keeps what was chosen
    assert "--visual-provider my-painter --visual-model local --voice-provider my-voice" in again  # and the services
    interview = json.loads((folder / "interview.json").read_text(encoding="utf-8"))
    assert interview["target"]["sort"] == "media"
    assert seen == []
    # what the command already set is told to the interviewer as decided, so it is never asked again
    asked = model.seen["questions"][0]
    assert "already set these on the command" in asked
    assert "12 seconds" in asked and "16x9 (wide 16:9)" in asked
    assert "12 seconds" in interview["given"] and "16x9" in interview["given"]  # and kept with the paused interview


def test_an_answers_file_without_a_for_line_still_takes_the_services_the_flags_name(
        tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studio, "produce", _fake_produce([]))
    model = Director()
    _route(monkeypatch, model)
    ahead = tmp_path / "ahead.json"
    ahead.write_text(json.dumps({"answers": {"style": "bold"}}), encoding="utf-8")  # no "for" in the file
    folder = tmp_path / "o"
    assert cli.main(["make", "a fox film", "--kind", "video", "--provider", "ollama", "--model", "m",
                     "--out", str(folder), "--answers", str(ahead),
                     "--visual-provider", "my-painter", "--visual-model", "local"]) == live_cli.EXIT_WAITING
    assert model.calls == ["questions"]  # the services were known, so it went on to the questions
    interview = json.loads((folder / "interview.json").read_text(encoding="utf-8"))
    assert interview["target"]["sort"] == "media"
    assert "Which service makes it" not in (folder / "questions.md").read_text(encoding="utf-8")
    # a "for" written in the answers file still wins over the flags: the unknown flag service is never looked up
    ahead.write_text(json.dumps({"for": "visuals: my-painter/local", "answers": {"style": "bold"}}), encoding="utf-8")
    model.calls.clear()
    assert cli.main(["make", "a fox film", "--kind", "video", "--provider", "ollama", "--model", "m",
                     "--out", str(tmp_path / "o2"), "--answers", str(ahead),
                     "--visual-provider", "nobody-knows", "--visual-model", "x"]) == live_cli.EXIT_WAITING
    assert model.calls == ["questions"]


def test_image_voice_and_music_are_not_text_kinds_and_cannot_be_taken_by_an_add_on() -> None:
    from proofhouse import addons, learn

    for kind in ("image", "voice", "music", "video"):
        assert kind in learn.OWN_ENGINE and kind in addons._RESERVED_KINDS
        with pytest.raises(make.MakeError, match="its own engine"):
            make.make("a fox", provider_id="ollama", model="m", kind=kind)


@needs_ffmpeg
def test_a_media_kind_added_as_data_is_made_like_the_built_in_kind_it_names(tmp_path: Path, programs: None) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "addon.json").write_text(json.dumps({
        "schema": "proofhouse.addon/v1", "name": "posters",
        "make_kinds": [{"kind": "poster", "media": "image",
                        "write": "Plan a poster: one bold picture, a short headline, readable from across a room."}],
    }), encoding="utf-8")
    assert cli.main(["addons", "install", str(pack)]) == 0
    assert "poster" in make_media.media_kinds()
    model = Director(scores=[9])
    made = make_media.make_media("a cafe poster", kind="poster", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter", {}, [True]), transport=model)
    assert made.best_version == 1 and made.delivered
    assert "readable from across a room" in model.seen["plan"][0]


# --- a film or a delivery that is only partly made is not passed off as made -----------------------------

def _partial_produce(stopped: str):
    def produce(brief: str, **kwargs):
        out = kwargs["out_dir"]
        out.mkdir(parents=True, exist_ok=False)
        first = kwargs["formats"][0]
        (out / f"film-{first}.mp4").write_bytes(b"film")
        return studio.Production(out, title="Fox", renders={first: str(out / f"film-{first}.mp4")}, stopped=stopped,
                                 checks=[{"ok": True, "render": first, "check": "plays", "detail": ""}])
    return produce


def test_a_film_missing_a_shape_it_was_asked_for_fails_its_checks_and_is_not_delivered(
        tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studio, "produce", _partial_produce("the 9x16 render failed"))
    made = make_media.make_media("a fox film", kind="video", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter, my-voice", {}, [True]), transport=Director(scores=[10]),
                                 rounds=1, shapes=["16x9", "9x16"])
    assert made.best_version is None and made.delivered == {}
    checks = _record(tmp_path / "o")["versions"][0]["checks"]
    assert any(not c["ok"] and "9x16" in c["detail"] for c in checks)


def test_a_studio_that_hits_the_spending_limit_stops_the_make(tmp_path: Path, programs: None,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studio, "produce", _partial_produce("spending limit reached"))
    model = Director(scores=[3, 3, 3])
    made = make_media.make_media("a fox film", kind="video", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter, my-voice", {}, [True]), transport=model, rounds=3,
                                 shapes=["16x9", "9x16"])
    assert made.stopped == "spending limit reached"
    assert model.calls.count("plan") == 1  # no more paid planning once the limit is hit
    assert (tmp_path / "o" / "v1" / "plan.json").is_file()


@needs_ffmpeg
def test_a_shape_that_could_not_be_delivered_is_named(tmp_path: Path, programs: None,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    real = studio.convert
    monkeypatch.setattr(studio, "convert", lambda args: False if "9x16" in str(args[-1]) else real(args))
    made = make_media.make_media("a fox", kind="image", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter", {}, [True]), transport=Director(scores=[9]),
                                 shapes=["16x9", "9x16"])
    assert set(made.delivered or {}) == {"16x9"} and made.undelivered == ["9x16"]
    assert _record(tmp_path / "o")["undelivered"] == ["9x16"]


@pytest.mark.parametrize("missing, code", [([], live_cli.EXIT_OK), (["9x16"], live_cli.EXIT_REFUSED)])
def test_the_command_says_plainly_when_the_judge_gave_no_score_or_a_shape_is_missing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], missing: list[str],
        code: int) -> None:
    finished = make.MakeResult(tmp_path / "o", "image", "rounds used up", 1, None, Decimal(0),
                               delivered={"16x9": "delivered/image-16x9.png"}, undelivered=missing)
    monkeypatch.setattr(make_media, "make_media", lambda *a, **k: finished)
    assert cli.main(["make", "a fox", "--kind", "image", "--provider", "ollama", "--model", "m", "--for", "my-painter",
                     "--out", str(tmp_path / "o")]) == code
    out = capsys.readouterr().out
    assert "None/10" not in out and "not judged" in out
    if missing:
        assert "not delivered: 9x16" in out


# --- a launch's video part asks first like every other part ------------------------------------------------

class LaunchDirector(Director):
    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You plan product launches"):
            self.calls.append("launch plan")
            content = json.dumps({"name": "Brew", "parts": [{"kind": "video", "brief": "a hype video for the cold brew"}]})
            return live.Response(200, {"choices": [{"message": {"content": content}}],
                                       "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        return super().__call__(request)


def test_a_launch_video_part_is_interviewed_and_made_through_the_media_loop(tmp_path: Path, programs: None,
                                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import launch

    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    folder = tmp_path / "l"
    result = launch.run_launch("launch our cold brew", provider_id="ollama", model="m", out_dir=folder,
                               transport=LaunchDirector(scores=[9, 9]),
                               interviewer=Answers("", {"must": "say launch day is Friday"}, [True]),
                               part_interviewer=lambda part, where: Answers("my-painter, my-voice", {"must": "show ice"}, [True]))
    assert [p.status for p in result.parts] == ["made"], result.parts
    assert seen and seen[0]["out_dir"] == folder / "01-video" / "v1"
    assert "show ice" in seen[0]["brief"] and "say launch day is Friday" in seen[0]["brief"]
    assert _record(folder / "01-video")["delivered"]


def test_a_launch_video_part_with_no_answers_yet_pauses_for_them(tmp_path: Path, programs: None,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import launch

    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    folder = tmp_path / "l"
    result = launch.run_launch("launch our cold brew", provider_id="ollama", model="m", out_dir=folder,
                               transport=LaunchDirector(), interviewer=Answers("", {}, [True]),
                               part_interviewer=lambda part, where: mi.FileInterviewer(None, "my-painter, my-voice"))
    assert [p.status for p in result.parts] == ["waiting"] and seen == []
    assert folder / "01-video" / "answers.json" in result.waiting


def test_a_launch_that_answers_from_files_names_the_video_services_from_its_flags(tmp_path: Path, programs: None) -> None:
    from proofhouse import launch

    where = tmp_path / "01-video"
    asking = launch._asker(mi.FileInterviewer(None), None, launch.Part("video", "a film"), where, 1,
                           make_media.video_target({"visual_provider": "my-painter", "visual_model": "local",
                                                    "voice_provider": "my-voice"}))
    assert isinstance(asking, mi.FileInterviewer) and asking.for_target == "visuals: my-painter/local, voice: my-voice"


def test_a_film_with_no_voice_or_music_service_gets_the_free_ones_and_the_record_says_so(
        tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import local_voice

    monkeypatch.setattr(local_voice, "available", lambda: True)
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    made = make_media.make_media("a fox film", kind="video", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                                 interviewer=Answers("my-painter", {"must": "short"}, [True]), transport=Director())
    assert made.delivered
    assert seen[0]["voice_provider"] == "local-voice" and seen[0]["music_provider"] == "local-music"
    record = _record(tmp_path / "o")
    assert record["roles"]["voice"]["provider"] == "local-voice" and record["roles"]["music"]["provider"] == "local-music"
    assert set(record["stood_in"]) == {"voice", "music"} and "no voice service" in record["stood_in"]["voice"]


def test_a_named_voice_or_a_music_file_is_never_replaced(tmp_path: Path, programs: None,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import local_voice

    monkeypatch.setattr(local_voice, "available", lambda: True)
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    song = tmp_path / "song.wav"
    song.write_bytes(b"RIFF")
    make_media.make_media("a fox film", kind="video", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                          interviewer=Answers("my-painter, my-voice", {"must": "short"}, [True]), transport=Director(),
                          video={"music_file": song})
    assert seen[0]["voice_provider"] == "my-voice" and seen[0]["music_provider"] is None
    assert _record(tmp_path / "o")["stood_in"] == {}


def test_with_no_speech_engine_here_the_voice_gap_stays_open(tmp_path: Path, programs: None,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import local_voice

    monkeypatch.setattr(local_voice, "available", lambda: False)
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    make_media.make_media("a fox film", kind="video", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                          interviewer=Answers("my-painter", {"must": "short"}, [True]), transport=Director())
    assert seen[0]["voice_provider"] is None and seen[0]["music_provider"] == "local-music"


def test_a_saved_script_builds_the_first_version_and_later_rounds_rewrite_from_the_notes(
        tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    saved = {"title": "Fox", "beats": [{"say": "Foxes brew.", "base": {"prompt": "a fox at a cafe"}}]}
    make_media.make_media("a hype video for a fox cafe", kind="video", provider_id="ollama", model="m",
                          out_dir=tmp_path / "o", interviewer=Answers("my-painter, my-voice", {}, [True]),
                          transport=Director(scores=[4, 9], shapes=["9x16"]), rounds=3, video={"script": saved})
    assert len(seen) == 2
    assert seen[0]["script"] == saved and "script" not in seen[1]


def test_make_reads_a_saved_script_file_and_refuses_one_that_is_not_a_script(
        tmp_path: Path, programs: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[dict] = []
    monkeypatch.setattr(studio, "produce", _fake_produce(seen))
    _route(monkeypatch, Director())
    base = ["make", "a fox film", "--kind", "video", "--provider", "ollama", "--model", "m",
            "--visual-provider", "my-painter", "--visual-model", "local"]
    listed = tmp_path / "list.json"
    listed.write_text("[1, 2]", encoding="utf-8")
    assert cli.main(base + ["--out", str(tmp_path / "a"), "--script", str(listed)]) != 0
    assert "is not a JSON object" in capsys.readouterr().err
    assert cli.main(base + ["--out", str(tmp_path / "b"), "--script", str(tmp_path / "missing.json")]) != 0
    assert "cannot read the saved script" in capsys.readouterr().err
    good = tmp_path / "script-written.json"
    good.write_text(json.dumps({"title": "Fox", "beats": []}), encoding="utf-8")
    assert cli.main(base + ["--out", str(tmp_path / "c"), "--script", str(good)]) == live_cli.EXIT_WAITING
    assert f"--script {good}" in capsys.readouterr().out  # the run it asks for again keeps the saved script
