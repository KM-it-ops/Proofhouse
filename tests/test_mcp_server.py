"""`proofhouse mcp`: the make, driven as tools from an AI app's chat, with the interview intact."""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from proofhouse import agent_server, demo_make, live, mcp_server
from proofhouse.mcp_server import ToolError, Tools


def _tools(tmp_path: Path, **kwargs) -> tuple[Tools, demo_make.Recorded, dict]:
    data = demo_make.recording()
    model = demo_make.Recorded(data)
    return Tools(base=tmp_path, transport=model, wait=60.0, **kwargs), model, data


def _start(tools: Tools, data: dict, **extra) -> dict:
    return tools.make_start({"request": data["request"], "kind": data["kind"], "provider": "ollama",
                             "model": demo_make.MODEL, **extra})


def _answers(report: dict) -> dict:
    return {q["id"]: (q["options"][0] if q.get("options") else "whatever reads best") for q in report["questions"]}


def test_a_make_goes_through_every_stage_and_nothing_is_made_before_the_say_back_is_confirmed(tmp_path):
    tools, model, data = _tools(tmp_path)

    first = _start(tools, data)
    assert first["stage"] == "which_tool" and first["question"]
    make = first["make"]
    assert model.calls == []  # no model call before it is known which tool it is for

    asked = tools.make_answer({"make": make, "for": data["for"]})
    assert asked["stage"] == "questions" and asked["questions"]
    assert all({"id", "question", "must_know"} <= set(q) for q in asked["questions"])
    musts = [q["must_know"] for q in asked["questions"]]
    assert musts == sorted(musts, reverse=True)  # must-know ones first

    said = tools.make_answer({"make": make, "answers": _answers(asked), "confirmed": True})
    assert said["stage"] == "say_back" and said["say_back"]
    assert json.loads((Path(make) / "answers.json").read_text(encoding="utf-8"))["confirmed"] is False
    assert "write" not in model.calls and not (Path(make) / "record.json").exists()

    again = tools.make_confirm({"make": make, "correction": "Skip merge commits."})
    assert again["stage"] == "say_back" and again["corrections_so_far"] == ["Skip merge commits."]
    assert "write" not in model.calls

    done = tools.make_confirm({"make": make, "confirmed": True})
    assert done["stage"] == "done" and done["best_version"]
    assert done["asked_for"] and done["summary"] and done["made_for"] == data["for"]
    assert "write" in model.calls and "judge" in model.calls
    assert (Path(make) / "record.json").is_file()


def test_the_say_back_cannot_be_confirmed_before_it_exists_and_answers_cannot_be_given_after(tmp_path):
    tools, _, data = _tools(tmp_path)
    make = _start(tools, data, **{"for": data["for"]})
    assert make["stage"] == "questions"
    with pytest.raises(ToolError, match="no say-back"):
        tools.make_confirm({"make": make["make"], "confirmed": True})
    tools.make_answer({"make": make["make"], "answers": _answers(make)})
    with pytest.raises(ToolError, match="make_confirm"):
        tools.make_answer({"make": make["make"], "answers": {"x": "y"}})
    with pytest.raises(ToolError, match="confirmed true"):
        tools.make_confirm({"make": make["make"]})


def test_deciding_everything_for_the_person_still_shows_a_say_back(tmp_path):
    tools, model, data = _tools(tmp_path)
    make = _start(tools, data, **{"for": data["for"]})
    said = tools.make_answer({"make": make["make"], "decide_for_me": True})
    assert said["stage"] == "say_back" and "write" not in model.calls


def test_a_make_can_be_picked_up_by_a_new_server(tmp_path):
    tools, _, data = _tools(tmp_path)
    make = _start(tools, data, **{"for": data["for"]})
    tools.make_answer({"make": make["make"], "answers": _answers(make)})

    later, _, _ = _tools(tmp_path)
    assert later.make_status({"make": make["make"]})["stage"] == "say_back"
    assert later.make_confirm({"make": make["make"], "confirmed": True})["stage"] == "done"

    after, _, _ = _tools(tmp_path)
    status = after.make_status({"make": make["make"]})
    assert status["stage"] == "done" and status["best_version"]
    listed = after.make_list({})["makes"]
    assert [m["state"] for m in listed] == ["done"] and listed[0]["from_chat"] is True


def test_a_step_that_takes_long_says_still_working_and_status_picks_it_up(tmp_path):
    tools, model, data = _tools(tmp_path)
    tools.wait = 0.0
    make = _start(tools, data, **{"for": data["for"]})
    if make["stage"] == "working":
        with pytest.raises(ToolError, match="still working"):
            tools.make_answer({"make": make["make"], "answers": {}})
    tools.wait = 60.0
    assert tools.make_status({"make": make["make"]})["stage"] == "questions"


def test_plain_words_when_the_request_is_wrong(tmp_path):
    tools, _, data = _tools(tmp_path)
    with pytest.raises(ToolError, match="request"):
        tools.make_start({})
    with pytest.raises(ToolError, match="command line"):
        tools.make_start({"request": "a film", "kind": "video", "provider": "ollama", "model": "m"})
    with pytest.raises(ToolError, match="name a model"):
        tools.make_start({"request": "x", "provider": "ollama"})
    with pytest.raises(ToolError, match="not a make started from chat"):
        tools.make_status({"make": str(tmp_path / "nothing")})
    none_here = Tools(base=tmp_path, which=lambda name: None)
    with pytest.raises(ToolError, match="proofhouse connect"):
        none_here.make_start({"request": "x"})


def test_a_model_failure_is_reported_not_left_as_still_working(tmp_path):
    def down(request: live.Request) -> live.Response:
        return live.Response(500, {"error": {"message": "down"}})

    tools = Tools(base=tmp_path, transport=down, wait=60.0)
    out = tools.make_start({"request": "a skill", "kind": "skill", "provider": "ollama", "model": "m",
                            "for": "Claude Code"})
    assert out["stage"] == "failed" and not out["best_version"]
    assert "500" in out["stopped"] and "Nothing usable" in out["next"]
    again = Tools(base=tmp_path, transport=down, wait=60.0).make_status({"make": out["make"]})
    assert again["stage"] == "failed"


def _talk(tools: Tools, *messages: dict | str) -> list[dict]:
    lines = "".join((m if isinstance(m, str) else json.dumps(m)) + "\n" for m in messages)
    out = io.StringIO()
    assert mcp_server.serve(tools, io.StringIO(lines), out) == 0
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_the_protocol_lists_the_tools_and_runs_a_call(tmp_path):
    tools, _, data = _tools(tmp_path)
    replies = _talk(
        tools,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "make_start", "arguments": {
            "request": data["request"], "kind": "skill", "provider": "ollama", "model": demo_make.MODEL,
            "for": data["for"]}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "make_confirm", "arguments": {
            "make": "nowhere"}}},
        "this is not json",
        {"jsonrpc": "2.0", "id": 5, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "rm_rf"}},
    )
    assert [r.get("id") for r in replies] == [1, 2, 3, 4, None, 5, 6]  # the notification gets no reply
    assert replies[0]["result"]["protocolVersion"] == "2025-06-18"
    assert replies[0]["result"]["serverInfo"]["name"] == "proofhouse"
    names = [t["name"] for t in replies[1]["result"]["tools"]]
    assert names == ["make_start", "make_answer", "make_confirm", "make_status", "make_list"]
    assert all(t["inputSchema"]["type"] == "object" and t["description"] for t in replies[1]["result"]["tools"])
    started = json.loads(replies[2]["result"]["content"][0]["text"])
    assert replies[2]["result"]["isError"] is False and started["stage"] == "questions"
    assert replies[3]["result"]["isError"] is True
    assert replies[4]["error"]["code"] == -32700
    assert replies[5]["error"]["code"] == -32601
    assert replies[6]["error"]["code"] == -32602


def test_an_older_app_gets_the_version_it_asked_for_and_an_unknown_one_gets_the_newest(tmp_path):
    tools, _, _ = _tools(tmp_path)
    old, odd = _talk(
        tools,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
        {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
    assert old["result"]["protocolVersion"] == "2024-11-05"
    assert odd["result"]["protocolVersion"] == mcp_server.PROTOCOLS[0]


def test_a_call_to_an_agent_address_runs_the_agent_here_and_other_addresses_go_out_as_usual():
    name, entry = next(iter(agent_server.load_agents().items()))
    ran: list[tuple[list[str], str]] = []

    def runner(argv: list[str], prompt: str, timeout: float) -> str:
        ran.append((argv, prompt))
        return "written by the agent"

    elsewhere: list[str] = []

    def otherwise(request: live.Request) -> live.Response:
        elsewhere.append(request.url)
        return live.Response(200, {})

    send = mcp_server.agent_transport(runner=runner, otherwise=otherwise)
    body = json.dumps({"model": "default", "messages": [{"role": "user", "content": "write it"}]}).encode()
    reply = send(live.Request(f"http://127.0.0.1:{entry['port']}/v1/chat/completions", {}, json.loads(body), body))
    assert reply.status_code == 200
    assert reply.payload["choices"][0]["message"]["content"] == "written by the agent"
    assert ran and "write it" in ran[0][1] and elsewhere == []

    send(live.Request("https://api.example.com/v1/chat/completions", {}, json.loads(body), body))
    assert elsewhere == ["https://api.example.com/v1/chat/completions"]

    def broken(argv: list[str], prompt: str, timeout: float) -> str:
        raise agent_server.AgentError(f"{name} is not logged in")

    failed = mcp_server.agent_transport(runner=broken, otherwise=otherwise)(
        live.Request(f"http://127.0.0.1:{entry['port']}/v1/chat/completions", {}, json.loads(body), body))
    assert failed.status_code == 502 and "not logged in" in failed.payload["error"]["message"]


def test_an_agent_given_its_prompt_in_a_file_does_not_inherit_this_process_input(monkeypatch):
    seen: dict = {}

    class FakeProcess:  # the agent is started with Popen so a run that times out can be stopped with its children
        returncode = 0

        def __init__(self, argv, **kwargs):
            seen.update(kwargs)

        def communicate(self, given=None, timeout=None):
            seen["given"] = given
            return "ok", ""

    monkeypatch.setattr(agent_server.shutil, "which", lambda name: name)
    monkeypatch.setattr(agent_server.subprocess, "Popen", FakeProcess)
    assert agent_server.run_agent(["tool", "--file", "{prompt_file}"], "hello", 5.0) == "ok"
    assert seen.get("stdin") == subprocess.DEVNULL and seen["given"] is None
    seen.clear()
    assert agent_server.run_agent(["tool"], "hello", 5.0) == "ok"
    assert seen.get("stdin") == subprocess.PIPE and seen["given"] == "hello"
