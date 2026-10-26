"""The shipped unit-desk MCP example answers bad input the way JSON-RPC 2.0 says, and stays up."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SERVER = Path(__file__).resolve().parent.parent / "examples" / "host-mode" / "mcp" / "server.py"
LIST = {"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": {}}


def talk(lines: list[str]) -> tuple[list[dict[str, Any]], str]:
    process = subprocess.run(
        [sys.executable, str(SERVER)], input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 0
    replies = [json.loads(line) for line in process.stdout.splitlines()]
    return replies, process.stderr


@pytest.mark.parametrize("garbage", ["not json at all", "{", '{"jsonrpc": "2.0", "id": 1,', "nul\x00l"])
def test_garbage_line_gets_a_parse_error_and_the_server_keeps_going(garbage: str) -> None:
    replies, _ = talk([garbage, json.dumps(LIST)])
    assert replies[0] == {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
    assert replies[1]["id"] == 7 and len(replies[1]["result"]["tools"]) == 2
    assert len(replies) == 2


@pytest.mark.parametrize("not_a_request", ["42", '"text"', "null", "true", "[1, 2]", "[]"])
def test_valid_json_that_is_not_an_object_gets_invalid_request(not_a_request: str) -> None:
    replies, _ = talk([not_a_request, json.dumps(LIST)])
    assert replies[0] == {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    assert replies[1]["id"] == 7 and len(replies) == 2


def test_notifications_and_blank_lines_still_get_no_reply() -> None:
    note = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    replies, _ = talk([json.dumps(note), "", "   ", json.dumps(LIST)])
    assert [reply["id"] for reply in replies] == [7]


def test_only_json_goes_to_stdout() -> None:
    replies, _ = talk(["oops", json.dumps(LIST)])
    assert all(reply["jsonrpc"] == "2.0" for reply in replies)
