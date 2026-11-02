"""Make interviews the owner first: which tool or model, the questions, a say-back to confirm, then a result made for it."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from proofhouse import cli, hosts, live, make, make_checks
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
    flat = mi.parse_questions(json.dumps([{"question": "Same?"}, {"question": "Same?"}]))
    assert [q.id for q in flat] == ["same", "same_2"] and flat[0].type == "text"
    # options without a choice type, or a choice type without options, are plain text questions
    assert mi.parse_questions(json.dumps([{"text": "Pick", "type": "single_select", "options": []}]))[0].type == "text"


@pytest.mark.parametrize("reply", [None, "", "no json here", "[]", json.dumps([{"text": ""}]), '{"other": 1}'])
def test_a_reply_with_no_questions_is_refused(reply: str | None) -> None:
    with pytest.raises(ValueError):
        mi.parse_questions(reply)


def test_too_many_questions_are_cut() -> None:
    many = json.dumps([{"text": f"Question {n}?"} for n in range(mi.MAX_QUESTIONS + 5)])
    assert len(mi.parse_questions(many)) == mi.MAX_QUESTIONS


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


def test_after_three_corrections_the_corrections_win_and_the_make_goes_on(tmp_path: Path) -> None:
    owner = Answers("Claude Code", {}, ["a", "b", "c", "never asked"])
    made = make.make("x", provider_id="ollama", model="m", kind="skill", out_dir=tmp_path / "o",
                     transport=Owner([9]), interviewer=owner)
    assert made.interview.corrections == ["a", "b", "c"] and made.best_version == 1


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
    assert code == 0 and "waiting for your answers" in out
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
    assert cli.main([*base, "--for", "Cursor", "--out", str(folder)]) == 0
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
