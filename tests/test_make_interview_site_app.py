"""Sites, apps and launches ask first too: where it will live, the questions, a say-back, then a result made for it."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from proofhouse import cli, launch, learn_catalog, live, live_cli, make
from proofhouse import make_interview as mi

from test_make_interview import Answers, Owner

SITE = {
    "index.html": '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width">'
                  '<title>Refunds</title><link rel="stylesheet" href="styles.css"></head><body><h1>Refunds</h1>'
                  '<script src="script.js"></script></body></html>',
    "styles.css": "body{font-family:sans-serif}",
    "script.js": "document.title = document.title;",
}
PWA = {"manifest.webmanifest": json.dumps({"name": "App", "start_url": ".", "display": "standalone",
                                           "icons": [{"src": "icon.svg", "sizes": "192x192"}]}),
       "service-worker.js": "self.addEventListener('fetch', () => {});",
       "icon.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192"></svg>',
       # the page of an installable web app links its manifest and registers its worker; without these the app's own
       # checks fail, and since 108 a failed check keeps the rounds going whatever the judge scored
       "index.html": SITE["index.html"].replace("</head>", '<link rel="manifest" href="manifest.webmanifest"></head>')
                     .replace("</body>", "<script>navigator.serviceWorker.register('service-worker.js')</script></body>")}
PLAN = json.dumps({"name": "Refund launch", "parts": [
    {"kind": "site", "brief": "A landing page for the refund helper."},
    {"kind": "skill", "brief": "A skill that handles refunds."},
]})
DEPLOY = {
    "what_it_is": "MyHost publishes static sites with a small CLI.", "name": "MyHost", "tool": "myhost",
    "install": "pip install myhost", "command": [sys.executable, "-c", "print('{folder}')"],
    "sources": ["https://example.org/myhost"],
}
PLATFORM = {
    "what_it_is": "Gadget OS wraps web apps in a tiny native shell.", "name": "Gadget OS", "shell": "Gadget shell",
    "write": "Write setup.json with a name field for Gadget OS.",
    "checks": {"files": ["setup.json"], "json": {"setup.json": ["name"]}, "site": False},
    "build": {"tool": "python", "install": "install python", "command": [], "output": ""},
    "host_os": ["windows", "macos", "linux"], "sources": ["https://example.org/gadget-os"],
}
OWNER_SAYS = {"audience": "My team", "team_size": "5", "must": "check the order"}


class Builder(Owner):
    """The interview model from test_make_interview, plus a site and app builder, a launch planner and research."""

    def __init__(self, scores: list[int] | None = None, kind: str = "skill") -> None:
        super().__init__(scores or [9] * 10, kind)
        self.log: list[tuple[str, str]] = []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        own = None
        if text.startswith(("You build excellent websites", "Build a complete working shared web app")):
            own = ("write", json.dumps({"files": SITE}))
        elif text.startswith("Build the ") and "platform shell" in text:
            own = ("platform", json.dumps({"files": PWA}))
        elif text.startswith("Improve the") and ("SITE" in text or "APP" in text):
            own = ("revise", json.dumps({"files": SITE}))
        elif text.startswith("You plan product launches"):
            own = ("plan", PLAN)
        elif text.startswith("Proofhouse deploys finished sites"):
            own = ("deploy research", json.dumps(DEPLOY))
        elif text.startswith("Proofhouse wraps working apps"):
            own = ("platform research", json.dumps(PLATFORM))
        if own is None:
            reply = super().__call__(request)
            self.log.append((self.calls[-1], text))
            return reply
        role, content = own
        self.calls.append(role)
        self.seen[role] = text
        self.log.append((role, text))
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    def said(self, role: str) -> list[str]:
        return [text for r, text in self.log if r == role]


@pytest.fixture(autouse=True)
def _no_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))


def _fill(answers_file: Path, **values: object) -> None:
    data = json.loads(answers_file.read_text(encoding="utf-8"))
    data.update(values)
    answers_file.write_text(json.dumps(data), encoding="utf-8")


# --- a site ------------------------------------------------------------------------------------------

def test_a_site_asks_where_it_will_be_published_and_is_built_and_judged_for_it(tmp_path: Path) -> None:
    model = Builder()
    owner = Answers("Netlify", OWNER_SAYS, [True])
    made = make.make("a site for our refund helper", provider_id="ollama", model="m", kind="site",
                     out_dir=tmp_path / "o", transport=model, interviewer=owner)
    assert made.best_version == 1
    assert model.calls[:3] == ["questions", "say back", "write"]
    brief = model.seen["write"]
    assert "Netlify" in brief and "- How big is the team?: 5" in brief and "check the order" in brief
    assert "AI model" not in brief and "AI tool" not in brief  # a place to publish is neither
    assert "netlify deploy" in brief  # how Netlify takes a site, from the deploy list
    assert "check the order" in model.seen["judge"]  # scored against the answers, not the bare request
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview"]["target"]["id"] == "netlify"
    assert record["interview"]["target"]["sort"] == "deploy"
    assert (tmp_path / "o" / "site" / "index.html").is_file()


def test_a_place_to_publish_nobody_taught_proofhouse_is_learned_not_refused(tmp_path: Path) -> None:
    model = Builder()
    made = make.make("a site for refunds", provider_id="ollama", model="m", kind="site", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("MyHost", OWNER_SAYS, [True]))
    assert made.best_version == 1
    assert "deploy research" in model.calls
    learned = learn_catalog.learned_raw("deploy_targets", "myhost")
    assert learned is not None and learned["approved"] is False  # learned, waiting for the owner to approve it
    target = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))["interview"]["target"]
    assert target["id"] == "myhost" and target["learned_by"]


def test_a_site_pauses_with_the_places_it_can_go_and_goes_on_from_the_answers_file(tmp_path: Path) -> None:
    folder = tmp_path / "o"
    first = Builder()
    made = make.make("a site for refunds", provider_id="ollama", model="m", kind="site", out_dir=folder,
                     transport=first, interviewer=mi.FileInterviewer(None))
    assert made.stopped == "waiting for your answers" and first.calls == []
    questions = (folder / "questions.md").read_text(encoding="utf-8")
    assert "Where will the site be published?" in questions
    assert "netlify" in questions and "vercel" in questions  # read from the deploy list, not written in code
    assert "AI tool or model" not in questions

    _fill(folder / "answers.json", **{"for": "Netlify", "answers": OWNER_SAYS, "confirmed": True})
    second = Builder()
    made = make.make("a site for refunds", provider_id="ollama", model="m", kind="site", out_dir=folder,
                     transport=second, interviewer=mi.FileInterviewer(folder / "answers.json"))
    assert made.best_version == 1 and second.calls[:3] == ["questions", "say back", "write"]
    assert "check the order" in second.seen["write"]


# --- an app ------------------------------------------------------------------------------------------

def test_an_app_asks_which_platforms_and_is_built_only_for_those(tmp_path: Path) -> None:
    model = Builder()
    made = make.make("an app for refunds", provider_id="ollama", model="m", kind="app", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("pwa", OWNER_SAYS, [True]))
    assert made.best_version == 1
    assert model.calls[:3] == ["questions", "say back", "write"]
    assert "check the order" in model.seen["write"] and "check the order" in model.seen["judge"]
    assert "check the order" in model.seen["platform"]  # the platform shell is built from the answers too
    assert len(model.said("platform")) == 1  # only the platform the owner named
    assert (tmp_path / "o" / "pwa" / "manifest.webmanifest").is_file()
    assert not (tmp_path / "o" / "windows").exists()
    target = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))["interview"]["target"]
    assert target["sort"] == "platform" and target["id"] == "pwa"


def test_an_app_pauses_with_the_platforms_it_can_run_on(tmp_path: Path) -> None:
    made = make.make("an app for refunds", provider_id="ollama", model="m", kind="app", out_dir=tmp_path / "o",
                     transport=Builder(), interviewer=mi.FileInterviewer(None))
    assert made.stopped == "waiting for your answers"
    questions = (tmp_path / "o" / "questions.md").read_text(encoding="utf-8")
    assert "Which platforms should the app run on?" in questions
    assert "pwa" in questions and "android" in questions  # read from the platform list


def test_a_platform_nobody_taught_proofhouse_is_learned_then_waits_for_approval(tmp_path: Path) -> None:
    model = Builder()
    with pytest.raises(make.MakeError, match="approve learned gadget-os"):
        make.make("an app for refunds", provider_id="ollama", model="m", kind="app", out_dir=tmp_path / "o",
                  transport=model, interviewer=Answers("gadget-os", OWNER_SAYS, [True]))
    assert "platform research" in model.calls
    assert learn_catalog.learned_raw("app_platforms", "gadget-os") is not None


# --- the command line --------------------------------------------------------------------------------

def _route(monkeypatch: pytest.MonkeyPatch, model: Builder) -> None:
    real = make.make
    monkeypatch.setattr(make, "make", lambda *a, **k: real(*a, **{**k, "transport": model}))
    real_launch = launch.run_launch
    monkeypatch.setattr(launch, "run_launch", lambda *a, **k: real_launch(*a, **{**k, "transport": model}))


def test_the_command_interviews_a_site_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    _route(monkeypatch, Builder())
    code = cli.main(["make", "a site for refunds", "--kind", "site", "--provider", "ollama", "--model", "m",
                     "--for", "Netlify", "--out", str(tmp_path / "o")])
    assert code == live_cli.EXIT_WAITING and "waiting for your answers" in capsys.readouterr().out
    assert json.loads((tmp_path / "o" / "answers.json").read_text(encoding="utf-8"))["for"] == "Netlify"


def test_platforms_named_on_the_command_line_answer_which_platforms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                     capsys: pytest.CaptureFixture[str]) -> None:
    _route(monkeypatch, Builder())
    code = cli.main(["make", "an app for refunds", "--kind", "app", "--provider", "ollama", "--model", "m",
                     "--platform", "pwa", "--out", str(tmp_path / "o")])
    assert code == live_cli.EXIT_WAITING and "waiting for your answers" in capsys.readouterr().out
    assert json.loads((tmp_path / "o" / "answers.json").read_text(encoding="utf-8"))["for"] == "pwa"


# --- a launch ----------------------------------------------------------------------------------------

def test_a_launch_asks_once_for_the_whole_goal_then_only_what_each_part_needs(tmp_path: Path) -> None:
    model = Builder()
    shared = Answers("", {"audience": "My team", "must": "say launch day is Friday"}, [True])
    by_kind = {"site": Answers("Netlify", {"must": "show the refund form"}, [True]),
               "skill": Answers("Claude Code", {"must": "check the order"}, [True])}
    result = launch.run_launch("launch our refund helper", provider_id="ollama", model="m", out_dir=tmp_path / "l",
                               transport=model, interviewer=shared,
                               part_interviewer=lambda part, where: by_kind[part.kind])
    assert [p.status for p in result.parts] == ["made", "made"]
    assert model.calls.count("plan") == 1 and model.calls.count("questions") == 3  # the goal, then each part
    whole, *per_part = model.said("questions")
    assert "site" in whole and "skill" in whole  # the shared questions know which parts are planned
    assert all("say launch day is Friday" in text for text in per_part)  # parts are told what is already answered
    writes = model.said("write")
    assert len(writes) == 2 and all("say launch day is Friday" in text for text in writes)
    assert "show the refund form" in writes[0] and "check the order" in writes[1]
    saved = json.loads((tmp_path / "l" / "interview.json").read_text(encoding="utf-8"))
    assert saved["kind"] == "launch"
    site_record = json.loads((tmp_path / "l" / "01-site" / "record.json").read_text(encoding="utf-8"))
    assert site_record["interview"]["target"]["id"] == "netlify"
    assert "say launch day is Friday" in site_record["interview"]["shared"]


def test_a_launch_pauses_for_the_whole_goal_then_for_each_part_and_goes_on(tmp_path: Path) -> None:
    folder = tmp_path / "l"
    first = Builder()
    result = launch.run_launch("launch our refund helper", provider_id="ollama", model="m", out_dir=folder,
                               transport=first, interviewer=mi.FileInterviewer(None))
    assert result.stopped == "waiting for your answers"
    assert folder / "answers.json" in result.waiting and (folder / "questions.md").is_file()
    assert not (folder / "01-site").exists()  # nothing is made before the whole goal is answered

    _fill(folder / "answers.json", answers={"audience": "My team", "must": "say launch day is Friday"}, confirmed=True)
    second = Builder()
    result = launch.run_launch("launch our refund helper", provider_id="ollama", model="m", out_dir=folder,
                               transport=second, interviewer=mi.FileInterviewer(folder / "answers.json"))
    assert result.stopped == "waiting for your answers"
    assert "plan" not in second.calls  # the plan is kept, not made again
    assert folder / "01-site" / "answers.json" in result.waiting
    assert folder / "02-skill" / "answers.json" in result.waiting
    assert "Where will the site be published?" in (folder / "01-site" / "questions.md").read_text(encoding="utf-8")

    _fill(folder / "01-site" / "answers.json", **{"for": "Netlify", "answers": {"must": "show the form"}, "confirmed": True})
    _fill(folder / "02-skill" / "answers.json", **{"for": "Claude Code", "answers": {"must": "check"}, "confirmed": True})
    third = Builder()
    result = launch.run_launch("launch our refund helper", provider_id="ollama", model="m", out_dir=folder,
                               transport=third, interviewer=mi.FileInterviewer(folder / "answers.json"))
    assert result.stopped == "finished" and [p.status for p in result.parts] == ["made", "made"]
    assert all("say launch day is Friday" in text for text in third.said("write"))
    record = json.loads((folder / "launch.json").read_text(encoding="utf-8"))
    assert [p["status"] for p in record["parts"]] == ["made", "made"]


def test_a_launch_folder_paused_for_another_goal_is_not_reused(tmp_path: Path) -> None:
    folder = tmp_path / "l"
    launch.run_launch("launch our refund helper", provider_id="ollama", model="m", out_dir=folder,
                      transport=Builder(), interviewer=mi.FileInterviewer(None))
    with pytest.raises(launch.LaunchError, match="another goal"):
        launch.run_launch("something else", provider_id="ollama", model="m", out_dir=folder,
                          transport=Builder(), interviewer=mi.FileInterviewer(None))


def test_the_command_pauses_a_launch_and_names_every_answers_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                  capsys: pytest.CaptureFixture[str]) -> None:
    _route(monkeypatch, Builder())
    code = cli.main(["make", "launch our refund helper", "--kind", "launch", "--provider", "ollama", "--model", "m",
                     "--out", str(tmp_path / "l"), "--for", "unused"])
    out = capsys.readouterr().out
    assert code == live_cli.EXIT_WAITING and "waiting for your answers" in out
    assert f"--answers {tmp_path / 'l' / 'answers.json'}" in out


def test_questions_sent_for_a_launch_part_list_what_is_already_known() -> None:
    iv = mi.Interview("a site", "site", shared="WHAT THE OWNER TOLD US FOR THE WHOLE LAUNCH:\n- Must: Friday")
    assert "FOR THE WHOLE LAUNCH" in iv.brief() and "Friday" in iv.brief()
    assert mi.Interview.from_dict(iv.to_dict()).shared == iv.shared
