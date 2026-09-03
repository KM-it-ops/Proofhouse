from __future__ import annotations

import json
from pathlib import Path

from promptrig.compiler.cli_compiler import build_parser
from promptrig.compiler.hosted_openapi import build_openapi, dump_openapi

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "tests" / "fixtures" / "hosted-slice-v0.1" / "openapi.json"

DEFAULT_SLICE_COMMANDS = frozenset(
    {
        "validate",
        "inspect",
        "compile",
        "adapters",
        "doctor",
        "closed-loop",
        "compile-requirements",
        "evaluate-product",
        "closed-loop-bridged-008",
    }
)
OPT_IN_LIVE_COMMANDS = frozenset({"execute-openai"})


def _cli_command_names() -> set[str]:
    parser = build_parser()
    subparsers = getattr(parser, "_subparsers", None)
    if subparsers is None:
        return set()
    names: set[str] = set()
    for action in subparsers._group_actions:
        names.update(action.choices)
    return names


def test_openapi_matches_cli_and_excludes_live_from_default_slice() -> None:
    generated = build_openapi()
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == generated
    assert dump_openapi(generated) == OPENAPI_PATH.read_text(encoding="utf-8")

    cli_names = _cli_command_names()
    documented = set(generated["x-cli-commands"])
    assert documented == cli_names
    default_slice = set(generated["x-default-hosted-slice"])
    opt_in_live = set(generated["x-opt-in-live"])
    assert opt_in_live == OPT_IN_LIVE_COMMANDS
    assert default_slice == cli_names - opt_in_live
    assert default_slice.isdisjoint(opt_in_live)
    assert DEFAULT_SLICE_COMMANDS <= default_slice

    paths = generated["paths"]
    for command in DEFAULT_SLICE_COMMANDS:
        path = f"/v0/compiler/{command}"
        assert path in paths, path
        assert paths[path]["post"]["x-default-hosted-slice"] is True
    live_path = "/v0/compiler/execute-openai"
    assert live_path in paths
    assert paths[live_path]["post"]["x-default-hosted-slice"] is False
    envelope = generated["components"]["schemas"]["ResultEnvelope"]["required"]
    for field in ("contract_version", "command", "status", "data", "diagnostics"):
        assert field in envelope
