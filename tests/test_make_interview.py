"""Make interviews the owner first: which tool or model, the questions, a say-back to confirm, then a result made for it."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from proofhouse import cli, hosts, live, live_cli, make, make_checks
from proofhouse import make_interview as mi

QUESTIONS = json.dumps([
    {"group": "Basics", "questions": [
        {"id": "audience", "text": "Who will use it?", "type": "single_select", "options": ["Just me", "My team"]},
        {"id": "team_size", "text": "How big is the team?", "type": "text",
         "dependsOn": {"questionId": "audience", "values": ["My team"]}},
        {"id": "must", "text": "What must it always do?", "type": "text"},
    ]},
])


class Owner:
    """A model that answers by what each call asks for, and keeps where each call went."""

    def __init__(self, scores: list[int] | None = None, kind: str = "skill") -> None:
        self.scores = list(scores or [9])
        self.kind = kind
        self.calls: list[str] = []
        self.where: list[str] = []
        self.seen: dict[str, str] = {}

    def __call__(self, request: live.Request) -> live.Response:
        body = json.loads(request.body_bytes)
        text = " ".join(m["content"] for m in body["messages"])
        if text.startswith("Someone wants a"):
            role, content = "what is", json.dumps({"sort": "tool", "id": "quillcode", "name": "QuillCode"})
        elif text.startswith("Proofhouse installs agents"):
            role, content = "host", json.dumps({
                "what_it_is": "A coding tool.", "name": "QuillCode",
                "rule": {"user": "~/.quill/RULES.md", "format": "md-block"},
                "guides": {"rule": "QuillCode reads RULES.md: short imperative bullets, no frontmatter."},
                "sources": ["https://quill.example/docs/rules"]})
        elif text.startswith("Proofhouse is about to write"):
            role, content = "guide", json.dumps({"name": "Mystery Model", "guide": "Keep it short and literal.",
                                                 "sources": ["https://mystery.example/docs"]})
        elif text.startswith("You are an expert prompt engineer. You generate"):
            role, content = "questions", QUESTIONS
        elif text.startswith("You are about to write a"):
            role = "say back"
            content = f"- What it is: understood {len([c for c in self.calls if c == 'say back']) + 1}"
        elif text.startswith(("You write excellent prompts", "You write agent skills", "You write subagents",
                              "Write a standing Markdown instruction")):
            role, content = "write", self._artifact()
        elif text.startswith("Write one realistic task"):
            role, content = "task", "Refund order 42."
        elif text.startswith("Write one realistic input"):
            role, content = "test input", "A customer asks for a refund."
        elif text.startswith("You judge AI work"):
            role, content = "judge", json.dumps({"score": self.scores.pop(0), "missing": [], "fix": "none"})
        elif text.startswith("Improve the"):
            role, content = "revise", self._artifact()
        else:
            role, content = "try", "I followed it: refund sent."
        self.calls.append(role)
        self.where.append(request.url)
        self.seen[role] = text
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    def _artifact(self) -> str:
        if self.kind == "rule":
            return json.dumps({"name": "refund-rules", "content": "# Refunds\n- Always confirm the order number."})
        if self.kind == "agent":
            return "---\nname: refund-agent\ndescription: Use for refunds.\n---\nHandle refunds."
        if self.kind == "prompt":
            return "You are a refund helper."
        return "---\nname: refund-helper\ndescription: Use when a customer asks for a refund.\n---\nSteps."


class Answers:
    """An interviewer that answers from code, like the owner typing."""

    def __init__(self, target: str, answers: dict[str, str], replies: list[bool | str]) -> None:
        self.for_target, self.given, self.replies = target, answers, list(replies)
        self.shown: list[str] = []

    def target(self) -> str | None:
        return self.for_target

    def answers(self, questions: list[mi.Question]) -> dict[str, str] | None:
        return {q.id: self.given.get(q.id, "") for q in questions}

    def confirm(self, understood: str, corrections: list[str]) -> bool | str | None:
        self.shown.append(understood)
        return self.replies.pop(0)


# --- reading the questions -------------------------------------------------------------------------

def test_questions_are_read_from_groups_fences_and_flat_lists() -> None:
    grouped = mi.parse_questions(f"Here you go:\n```json\n{QUESTIONS}\n```")
    assert [q.id for q in grouped] == ["audience", "team_size", "must"]
    assert grouped[0].group == "Basics" and grouped[0].options == ("Just me", "My team")
    assert grouped[1].depends_on == ("audience", ("My team",))
    flat = mi.parse_questions(json.dumps([{"id": "same", "question": "Same?"}, {"id": "same", "question": "Other?"}]))
    assert [q.id for q in flat] == ["same", "other"] and flat[0].type == "text"  # a reused id takes the words
    # options without a choice type, or a choice type without options, are plain text questions
    assert mi.parse_questions(json.dumps([{"text": "Pick", "type": "single_select", "options": []}]))[0].type == "text"


def test_every_question_gets_its_own_id_even_when_the_model_copies_one() -> None:
    texts = ["Objective", "Video purpose", "Video length", "Video duration", "Target audience", "Video resolution",
             "Style"]
    reply = json.dumps([{"id": "short_snake_case", "text": t} for t in texts])
    ids = [q.id for q in mi.parse_questions(reply)]
    assert ids == ["objective", "video_purpose", "video_length", "video_duration", "target_audience",
                   "video_resolution", "style"]
    # the same id three times over, on questions whose words would also clash, still gives three ids
    clash = json.dumps([{"id": "pick", "text": "Pick one"}, {"id": "pick", "text": "pick"}, {"id": "pick", "text": "Pick!"}])
    assert len({q.id for q in mi.parse_questions(clash)}) == len(mi.parse_questions(clash))


def test_a_question_asked_twice_is_asked_once() -> None:
    reply = json.dumps([
        {"id": "purpose", "text": "What is the main purpose of this video?", "type": "single_select",
         "options": ["Teaser", "Tutorial"]},
        {"id": "purpose_value", "text": "What is the main purpose of this video? (select one)", "type": "single_select",
         "options": ["Teaser", "Tutorial"]},
        {"id": "length", "text": "How long should the video be?"},
        {"id": "length_value", "text": "how long should the video be (length)"},
        {"id": "teaser_tone", "text": "What tone should the teaser have?", "dependsOn": {"questionId": "purpose_value",
                                                                                      "values": ["Teaser"]}},
    ])
    questions = mi.parse_questions(reply)
    assert [q.id for q in questions] == ["purpose", "length", "teaser_tone"]
    assert questions[2].depends_on == ("purpose", ("Teaser",))  # a follow-up of the repeat hangs off the first


@pytest.mark.parametrize("reply", [None, "", "no json here", "[]", json.dumps([{"text": ""}]), '{"other": 1}'])
def test_a_reply_with_no_questions_is_refused(reply: str | None) -> None:
    with pytest.raises(ValueError):
        mi.parse_questions(reply)


def test_too_many_questions_are_cut() -> None:
    many = json.dumps([{"text": f"Question {n}?"} for n in range(mi.MAX_QUESTIONS + 5)])
    assert len(mi.parse_questions(many)) == mi.MAX_QUESTIONS


def test_a_question_about_what_the_command_already_set_is_dropped_even_when_the_model_asks_it() -> None:
    # what a small free model asked although --seconds 10 --formats 16x9 were set
    reply = json.dumps([
        {"id": "hype_film_goal", "text": "Is the goal to hype the tool or the client?", "type": "single_select",
         "options": ["Hype the tool", "Hype the client"]},
        {"id": "film_length", "text": "Is the film a specific length?", "type": "single_select",
         "options": ["No changes", "Yes, 10 seconds"]},
        {"id": "film_format", "text": "What is the video format?", "type": "single_select", "options": ["Video format"]},
        {"id": "aspect", "text": "Should it be vertical or horizontal?", "type": "text"},
        {"id": "how_long", "text": "How long should it run?", "type": "text"},
        {"id": "film_tone", "text": "What tone should the film have?", "type": "text"},
        {"id": "film_content", "text": "Should the film contain content from the model?", "type": "text",
         "dependsOn": {"questionId": "film_length", "values": ["Yes, 10 seconds"]}},
    ])
    given = "- length: 10 seconds\n- shapes to deliver: 16x9 (wide 16:9)"
    kept = mi.not_given(mi.parse_questions(reply), given)
    assert [q.id for q in kept] == ["hype_film_goal", "film_tone", "film_content"]
    assert kept[2].depends_on is None  # its parent is decided, so it is simply asked
    # only what was set is dropped: with no length set, the length questions stay
    shapes_only = mi.not_given(mi.parse_questions(reply), "- shapes to deliver: 16x9 (wide 16:9)")
    assert [q.id for q in shapes_only] == ["hype_film_goal", "film_length", "how_long", "film_tone", "film_content"]
    assert mi.not_given(mi.parse_questions(reply), "") == mi.parse_questions(reply)


def test_a_question_about_the_shape_in_plain_words_is_dropped_when_the_command_set_the_shapes() -> None:
    # what llama3.2 asked on 2026-11-04 although --formats 16x9 was set
    reply = json.dumps([
        {"id": "should_the_video_be_wide_tall_or_square", "text": "Should the video be wide, tall, or square?",
         "type": "text"},
        {"id": "screen", "text": "Widescreen or phone screen?", "type": "text"},
        {"id": "ratio", "text": "Is 16:9 or 9:16 better?", "type": "text"},
        {"id": "logo", "text": "Should the logo sit in a square badge?", "type": "text"},  # not about the film's shape
        {"id": "tone", "text": "What tone should the video convey?", "type": "text"},
    ])
    kept = mi.not_given(mi.parse_questions(reply), "- shapes to deliver: 16x9 (wide 16:9)")
    assert [q.id for q in kept] == ["logo", "tone"]


def test_a_follow_up_is_asked_only_when_its_parent_answer_calls_for_it() -> None:
    team = mi.parse_questions(QUESTIONS)[1]
    assert not mi.applies(team, {})
    assert not mi.applies(team, {"audience": mi.NOT_ANSWERED})
    assert not mi.applies(team, {"audience": "Just me"})
    assert mi.applies(team, {"audience": "Just me, my team"})


# --- the whole interview, then the make ------------------------------------------------------------

def test_a_skill_for_claude_code_asks_says_back_takes_a_correction_and_is_written_for_claude(tmp_path: Path) -> None:
    model = Owner([9])
    owner = Answers("Claude Code", {"audience": "My team", "team_size": "5", "must": "check the order"},
                    ["it is for refunds over $50 only", True])
    made = make.make("a skill for handling refunds", provider_id="ollama", model="m", kind="skill",
                     out_dir=tmp_path / "o", transport=model, interviewer=owner)
    assert made.best_version == 1
    assert model.calls[:4] == ["questions", "say back", "say back", "write"]
    assert owner.shown == ["- What it is: understood 1", "- What it is: understood 2"]
    brief = model.seen["write"]
    assert "This skill is for Claude Code" in brief
    assert "- Who will use it?: My team" in brief and "- How big is the team?: 5" in brief
    assert "refunds over $50 only" in brief and "understood 2" in brief
    assert "SKILL.md starts on its first line with YAML frontmatter" in brief  # Claude's own guide
    assert "refunds over $50 only" in model.seen["judge"]  # judged against the brief, not the bare request
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview"]["target"]["id"] == "claude" and record["interview"]["confirmed"] is True
    assert (tmp_path / "o" / "interview.json").is_file()


def test_a_question_whose_parent_does_not_call_for_it_is_left_out_of_the_brief(tmp_path: Path) -> None:
    model = Owner([9])
    owner = Answers("Claude Code", {"audience": "Just me", "team_size": "5", "must": ""}, [True])
    made = make.make("x", provider_id="ollama", model="m", kind="agent", out_dir=tmp_path / "o",
                     transport=model, interviewer=owner)
    assert made.interview.entries == [("Who will use it?", "Just me")]
    assert "How big is the team" not in model.seen["write"]
    assert "Claude reads the description to decide when to hand work to the subagent" in model.seen["write"]


def test_a_rule_for_cursor_comes_out_as_an_mdc_file_with_frontmatter(tmp_path: Path) -> None:
    model = Owner([9], kind="rule")
    made = make.make("a rule for refunds", provider_id="ollama", model="m", kind="rule", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("cursor", {"must": "confirm"}, [True]))
    assert made.best_version == 1
    assert sorted(p.name for p in (tmp_path / "o").glob("refund-rules.*")) == ["refund-rules.mdc"]
    text = (tmp_path / "o" / "refund-rules.mdc").read_text(encoding="utf-8")
    assert text.startswith("---\ndescription: refund-rules\nalwaysApply: true\n---\n# Refunds")
    assert "A Cursor project rule is one .mdc file" in model.seen["write"]
    checks = json.loads((tmp_path / "o" / "v1" / "checks.json").read_text(encoding="utf-8"))
    assert {c.get("host") for c in checks if c.get("host")} == {"cursor"}


def test_a_rule_for_codex_goes_into_agents_md(tmp_path: Path) -> None:
    model = Owner([9], kind="rule")
    make.make("a rule for refunds", provider_id="ollama", model="m", kind="rule", out_dir=tmp_path / "o",
              transport=model, interviewer=Answers("Codex", {}, [True]))
    assert (tmp_path / "o" / "refund-rules.md").is_file()
    assert "Codex reads AGENTS.md" in model.seen["write"]


def test_an_unknown_tool_is_researched_and_learned_not_refused(tmp_path: Path) -> None:
    model = Owner([9], kind="rule")
    made = make.make("a rule for refunds", provider_id="ollama", model="m", kind="rule", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("QuillCode", {"must": "confirm"}, [True]))
    assert made.best_version == 1
    assert model.calls[:3] == ["what is", "host", "questions"]
    learned = hosts.all_hosts()["quillcode"]
    assert learned["learned_by"] == "ollama/m"
    assert made.interview.target.learned_by == "ollama/m"
    assert "(named by the model, not checked)" in made.interview.target.guide_source
    assert "QuillCode reads RULES.md" in model.seen["write"]


def test_an_unknown_model_gets_a_researched_guide_kept_for_next_time(tmp_path: Path) -> None:
    model = Owner([9], kind="prompt")
    make.make("a prompt for refunds", provider_id="ollama", model="m", out_dir=tmp_path / "o", transport=model,
              interviewer=Answers("mystery-model-9", {}, [True]))
    assert "Keep it short and literal." in model.seen["write"]
    again = Owner([9], kind="prompt")
    make.make("a prompt for refunds", provider_id="ollama", model="m", out_dir=tmp_path / "p", transport=again,
              interviewer=Answers("mystery-model-9", {}, [True]))
    assert "guide" not in again.calls and "what is" not in again.calls  # learned once, read from the guides folder


def test_a_known_model_uses_its_notes() -> None:
    target = mi.find_target("claude-opus-5-5", "prompt", lambda *a, **k: pytest.fail("no research for a known model"),
                            learned_by="x")
    assert target.sort == "model" and target.guide


# --- answers from a file: pause, fill in, go on ----------------------------------------------------

def test_with_no_answers_yet_make_pauses_and_goes_on_from_the_answers_file(tmp_path: Path) -> None:
    folder = tmp_path / "o"
    first = Owner([9])
    made = make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=folder,
                     transport=first, interviewer=mi.FileInterviewer(None, "Claude Code"))
    assert made.stopped == "waiting for your answers" and made.best_version is None
    assert first.calls == ["questions"]
    assert not (folder / "record.json").exists()
    questions = (folder / "questions.md").read_text(encoding="utf-8")
    assert "**audience**: Who will use it?" in questions and "Made for: Claude Code" in questions
    answers = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    assert answers["answers"] == {"audience": "", "team_size": "", "must": ""} and answers["for"] == "Claude Code"

    answers["answers"]["must"] = "check the order"
    (folder / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    second = Owner([9])
    made = make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=folder,
                     transport=second, interviewer=mi.FileInterviewer(folder / "answers.json"))
    assert made.stopped == "waiting for your answers"
    assert second.calls == ["say back"]  # the questions are not asked again
    assert "understood 1" in (folder / "understood.md").read_text(encoding="utf-8")

    answers = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    assert answers["answers"]["must"] == "check the order"  # what the owner wrote is kept
    answers["confirmed"] = True
    (folder / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    third = Owner([9])
    made = make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=folder,
                     transport=third, interviewer=mi.FileInterviewer(folder / "answers.json"))
    assert made.best_version == 1 and third.calls[0] == "write"
    record = json.loads((folder / "record.json").read_text(encoding="utf-8"))
    assert len(record["calls"]) == 1 + 1 + len(third.calls)  # every call of every run is kept


def test_a_paused_folder_is_not_reused_for_another_request(tmp_path: Path) -> None:
    folder = tmp_path / "o"
    make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=folder,
              transport=Owner(), interviewer=mi.FileInterviewer(None, "Claude Code"))
    with pytest.raises(make.MakeError, match="another request"):
        make.make("something else", provider_id="ollama", model="m", kind="skill", out_dir=folder,
                  transport=Owner(), interviewer=mi.FileInterviewer(None, "Claude Code"))


def test_without_a_tool_named_the_make_asks_for_one_first(tmp_path: Path) -> None:
    model = Owner()
    made = make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
                     transport=model, interviewer=mi.FileInterviewer(None))
    assert made.stopped == "waiting for your answers" and model.calls == []
    assert "Which AI tool or model is this for?" in (tmp_path / "o" / "questions.md").read_text(encoding="utf-8")


def test_a_broken_answers_file_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "answers.json"
    bad.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(mi.InterviewError):
        mi.FileInterviewer(bad)


# --- answers typed in the terminal ------------------------------------------------------------------

def test_the_terminal_asks_each_question_and_turns_option_numbers_into_words(tmp_path: Path) -> None:
    typed = iter(["Claude Code", "2", "4", "", "make it for refunds only", "yes"])
    shown = io.StringIO()
    model = Owner([9])
    made = make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
                     transport=model, interviewer=mi.TerminalInterviewer(lambda: next(typed), shown.write))
    assert made.best_version == 1
    assert made.interview.entries == [("Who will use it?", "My team"), ("How big is the team?", "4")]
    assert made.interview.corrections == ["make it for refunds only"]
    out = shown.getvalue()
    assert "Which AI tool or model is this for?" in out and "  2) My team" in out
    assert "Here is what I understood:\n- What it is: understood 1" in out


def test_after_three_corrections_the_last_say_back_is_still_shown_before_anything_is_made(tmp_path: Path) -> None:
    # 108: this used to confirm on its own after the third correction, without showing the say-back it produced.
    owner = Answers("Claude Code", {}, ["a", "b", "c", True])
    made = make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
                     transport=Owner([9]), interviewer=owner)
    assert made.interview.corrections == ["a", "b", "c"] and made.best_version == 1
    assert len(owner.shown) == 4 and owner.shown[-1].endswith("understood 4")


# --- trying it on the tool --------------------------------------------------------------------------

def test_a_skill_is_tried_on_the_tools_own_agent_bridge(tmp_path: Path) -> None:
    assert cli.main(["providers", "add", "agent-claude", "--base-url", "http://127.0.0.1:11801/v1"]) == 0
    model = Owner([9])
    made = make.make("a skill for refunds", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("Claude Code", {}, [True]))
    assert made.tried_on == "agent-claude/default" and made.tried_on_note is None
    tried = model.calls.index("try")
    assert "127.0.0.1:11801" in model.where[tried]
    assert all("127.0.0.1:11801" not in url for n, url in enumerate(model.where) if n != tried)
    assert "TRIED ON CLAUDE CODE WITH THIS TASK:\nRefund order 42." in model.seen["judge"]
    assert "WHAT IT DID:\nI followed it: refund sent." in model.seen["judge"]
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["tried_on"] == "agent-claude/default"


def test_try_on_names_any_provider_and_a_failure_there_does_not_stop_the_make(tmp_path: Path) -> None:
    assert cli.main(["providers", "add", "my-box", "--base-url", "http://localhost:9999/v1"]) == 0
    model = Owner([9], kind="prompt")

    def flaky(request: live.Request) -> live.Response:
        if "localhost:9999" in request.url:
            return live.Response(500, {"error": {"message": "down"}})
        return model(request)

    made = make.make("a prompt for refunds", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                     transport=flaky, interviewer=Answers("Claude Code", {}, [True]), try_on="my-box/qwen")
    assert made.best_version == 1 and made.tried_on == "my-box/qwen"
    assert made.tried_on_note is not None and made.tried_on_note.startswith("could not try it on my-box/qwen")


def test_an_unknown_try_on_provider_is_refused(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError, match="no provider named"):
        make.make("x", provider_id="ollama", model="m", out_dir=tmp_path / "o", transport=Owner(), try_on="nope/x")


# --- without an interviewer nothing changes --------------------------------------------------------

def test_without_an_interviewer_the_make_runs_as_before(tmp_path: Path) -> None:
    model = Owner([9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model)
    assert model.calls == ["write", "judge"]
    assert not (tmp_path / "o" / "interview.json").exists()


# --- the command line -------------------------------------------------------------------------------

def test_the_command_pauses_with_for_and_tells_you_how_to_go_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                              capsys: pytest.CaptureFixture[str]) -> None:
    model = Owner()
    monkeypatch.setattr(live, "_default_transport", model, raising=False)
    real = make.make
    monkeypatch.setattr(make, "make", lambda *a, **k: real(*a, **{**k, "transport": model}))
    code = cli.main(["make", "a skill for refunds", "--kind", "skill", "--provider", "ollama", "--model", "m",
                     "--for", "Claude Code", "--out", str(tmp_path / "o")])
    out = capsys.readouterr().out
    assert code == live_cli.EXIT_WAITING and "waiting for your answers" in out
    assert f"--answers {tmp_path / 'o' / 'answers.json'}" in out


# --- the tool list ----------------------------------------------------------------------------------

def test_rule_files_take_the_ending_each_tool_wants() -> None:
    assert make_checks.rule_suffix("cursor") == ".mdc"
    assert make_checks.rule_suffix("claude") == ".md"
    assert make_checks.rule_suffix(None) == ".md" and make_checks.rule_suffix("no-such-tool") == ".md"


def test_every_shipped_guide_names_its_sources() -> None:
    for host_id in ("claude", "cursor", "codex"):
        host = hosts.all_hosts()[host_id]
        assert host["guides"] and all(s.startswith("https://") for s in host["guide_sources"])


def test_the_command_names_the_rule_file_not_the_question_sheet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                capsys: pytest.CaptureFixture[str]) -> None:
    model = Owner([9], kind="rule")
    real = make.make
    monkeypatch.setattr(make, "make", lambda *a, **k: real(*a, **{**k, "transport": model}))
    folder = tmp_path / "o"
    base = ["make", "a rule for refunds", "--kind", "rule", "--provider", "ollama", "--model", "m"]
    assert cli.main([*base, "--for", "Cursor", "--out", str(folder)]) == live_cli.EXIT_WAITING
    answers = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    answers["answers"]["must"], answers["confirmed"] = "confirm the order", True
    (folder / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    capsys.readouterr()
    assert cli.main([*base, "--answers", str(folder / "answers.json")]) == 0
    out = capsys.readouterr().out
    assert "made for Cursor" in out
    assert f"rule file: {folder / 'refund-rules.mdc'}" in out
    assert f"install rule {folder / 'refund-rules.mdc'} --into cursor --project" in out


def test_the_try_on_task_carries_what_it_works_on(tmp_path: Path) -> None:
    assert cli.main(["providers", "add", "agent-claude", "--base-url", "http://127.0.0.1:11801/v1"]) == 0
    model = Owner([9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model,
              interviewer=Answers("Claude Code", {}, [True]))
    assert "paste any file, diff, log or page it works on" in model.seen["task"]


def test_a_tool_without_its_shell_is_tried_as_a_trial_and_the_skill_is_not_tuned_to_it(tmp_path: Path) -> None:
    assert cli.main(["providers", "add", "agent-claude", "--base-url", "http://127.0.0.1:11801/v1"]) == 0
    model = Owner([5, 9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model,
              interviewer=Answers("Claude Code", {}, [True]))
    assert model.seen["try"].endswith("take what is pasted above as its output. Where the skill says to run "
                                      "something or make a change, say in one line what you would do, then carry "
                                      "on to the end the way the skill says. Do not talk about this trial, this "
                                      "session or its folder.)")
    assert "do not mark it down for commands it could not run" in model.seen["judge"]
    assert "do not ask the skill to handle pasted input or a missing repository" in model.seen["judge"]
    assert "Do not add anything about the trial run" in model.seen["revise"]


def test_without_a_trial_the_judge_and_revise_get_no_trial_note(tmp_path: Path) -> None:
    model = Owner([5, 9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model)
    assert "could not run" not in model.seen["judge"] and "trial run" not in model.seen["revise"]



def test_a_text_make_can_be_judged_by_another_model(tmp_path: Path) -> None:
    assert cli.main(["providers", "add", "my-judge", "--base-url", "http://localhost:8081/v1"]) == 0
    model = Owner([9], kind="prompt")
    made = make.make("a prompt for refunds", provider_id="ollama", model="m", out_dir=tmp_path / "o",
                     transport=model, interviewer=Answers("Claude Code", {}, [True]), judge="my-judge/qwen")
    assert made.best_version == 1 and made.judged_by == "my-judge/qwen"
    judged = [n for n, role in enumerate(model.calls) if role == "judge"]
    assert judged and all("localhost:8081" in model.where[n] for n in judged)
    assert all("localhost:8081" not in url for n, url in enumerate(model.where) if n not in judged)
    assert json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))["judge"] == "my-judge/qwen"
    with pytest.raises(make.MakeError, match="spending limit"):
        make.make("x", provider_id="ollama", model="m", out_dir=tmp_path / "p", transport=Owner(), judge="openai/gpt-x")


# --- 108: ranked questions, blanks become stated choices, nothing confirmed unseen, no quiet fallbacks ---

def test_must_know_questions_are_marked_and_come_first_with_follow_ups_after_their_parent() -> None:
    found = mi.parse_questions(json.dumps([
        {"id": "tone", "text": "What tone?", "need": "nice"},
        {"id": "audience", "text": "Who is it for?", "need": "must", "type": "single_select", "options": ["Me", "Team"]},
        {"id": "size", "text": "How big is the team?", "need": "nice", "dependsOn": {"questionId": "audience", "values": ["Team"]}},
        {"id": "limit", "text": "Any hard limit?", "priority": "required"},
        {"id": "plain", "text": "Anything else?"},
    ]))
    assert [q.must for q in found] == [False, True, False, True, False]
    assert [q.id for q in mi.ranked(found)] == ["audience", "size", "limit", "tone", "plain"]
    assert mi.Question.from_dict(found[1].to_dict()).must is True


def test_must_know_questions_are_marked_on_the_sheet_and_in_the_terminal() -> None:
    iv = mi.Interview("x", "skill", mi.find_target("Claude Code", "skill", lambda *a, **k: None, learned_by="x"),
                      [mi.Question("goal", "What for?", "text", must=True), mi.Question("tone", "What tone?", "text")])
    sheet = mi.questions_markdown(iv)
    assert "1. **goal** (must know): What for?" in sheet and "2. **tone**: What tone?" in sheet
    assert "decide_for_me" in sheet
    shown = io.StringIO()
    typed = iter(["a", ""])
    mi.TerminalInterviewer(lambda: next(typed), shown.write).answers(iv.questions)
    assert "What for? [must know]" in shown.getvalue() and "What tone? [must know]" not in shown.getvalue()


def test_a_blank_answer_is_left_to_proofhouse_and_the_say_back_states_the_choice(tmp_path: Path) -> None:
    model = Owner([9])
    made = make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o", transport=model,
                     interviewer=Answers("Claude Code", {"audience": "Just me", "must": ""}, [True]))
    assert made.interview.left == ["What must it always do?"]  # the follow-up that did not apply is not listed
    assert "LEFT TO PROOFHOUSE" in model.seen["write"] and "- What must it always do?" in model.seen["write"]
    assert "What I chose for you" in model.seen["say back"]
    record = json.loads((tmp_path / "o" / "record.json").read_text(encoding="utf-8"))
    assert record["interview"]["left"] == ["What must it always do?"]

    full = Owner([9])
    make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "p", transport=full,
              interviewer=Answers("Claude Code", {"audience": "Just me", "must": "check"}, [True]))
    assert "What I chose for you" not in full.seen["say back"] and "LEFT TO PROOFHOUSE" not in full.seen["write"]


def test_an_answers_file_with_nothing_filled_in_pauses_and_says_why_unless_told_to_decide(tmp_path: Path) -> None:
    folder = tmp_path / "o"
    args = dict(provider_id="ollama", model="m", kind="skill", out_dir=folder)
    make.make("a skill", transport=Owner(), interviewer=mi.FileInterviewer(None, "Claude Code"), **args)
    again = Owner()
    made = make.make("a skill", transport=again, interviewer=mi.FileInterviewer(folder / "answers.json"), **args)
    assert made.stopped == "waiting for your answers" and again.calls == []
    assert "decide_for_me" in made.waiting_note
    assert "decide_for_me" in (folder / "questions.md").read_text(encoding="utf-8")

    answers = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    assert answers["decide_for_me"] is False
    answers["decide_for_me"] = True
    (folder / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    third = Owner()
    made = make.make("a skill", transport=third, interviewer=mi.FileInterviewer(folder / "answers.json"), **args)
    assert third.calls == ["say back"] and "What I chose for you" in third.seen["say back"]
    assert made.interview.left == ["Who will use it?", "What must it always do?"]


def test_a_correction_in_the_answers_file_is_never_confirmed_before_the_owner_sees_the_new_say_back(tmp_path: Path) -> None:
    folder = tmp_path / "o"
    args = dict(provider_id="ollama", model="m", kind="skill", out_dir=folder)
    make.make("a skill", transport=Owner(), interviewer=mi.FileInterviewer(None, "Claude Code"), **args)
    answers = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    answers["answers"]["must"] = "check"
    answers.update(confirmed=True, correction="refunds only")  # confirmed and corrected in one go
    (folder / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    model = Owner([9])
    made = make.make("a skill", transport=model, interviewer=mi.FileInterviewer(folder / "answers.json"), **args)
    assert made.stopped == "waiting for your answers" and model.calls == ["say back", "say back"]
    assert json.loads((folder / "answers.json").read_text(encoding="utf-8"))["confirmed"] is False


def test_general_notes_are_never_used_quietly() -> None:
    target = mi._general("Zed", "zed", "Zed", "tool")
    iv = mi.Interview("x", "skill", target, [mi.Question("goal", "What for?", "text")])
    told: list[str] = []

    class Source(Answers):
        def tell(self, note: str) -> None:
            told.append(note)

    mi.run(iv, Source("Zed", {"goal": "g"}, [True]), lambda *a, **k: "- ok", preset="balanced", learned_by="x")
    assert any("general notes" in note and "Zed" in note for note in iv.notes) and told == iv.notes


def test_stock_questions_are_never_used_quietly() -> None:
    iv = mi.Interview("x", "skill", mi.find_target("Claude Code", "skill", lambda *a, **k: None, learned_by="x"))
    shown = io.StringIO()
    typed = iter(["refunds", "", "", "", "", ""])
    source = mi.TerminalInterviewer(lambda: next(typed), shown.write, "Claude Code")
    mi.run(iv, source, lambda role, *a, **k: "I would rather not." if role == "questions" else "- ok",
           preset="balanced", learned_by="x")
    assert iv.questions_from == "fallback" and [q.must for q in iv.questions[:3]] == [True, True, True]
    assert any("stock questions" in note for note in iv.notes) and "stock questions" in shown.getvalue()
    assert mi.Interview.from_dict(iv.to_dict()).notes == iv.notes
