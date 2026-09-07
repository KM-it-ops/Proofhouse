"""Generate an OpenAPI 3 document from the headless compiler CLI.

The hosted slice is a wrapper. Canonical meaning stays in the library/CLI.
This module does not start an HTTP server and does not pick Q2.
"""

from __future__ import annotations

import json
from typing import Any

from .cli_compiler import build_parser

OPENAPI_VERSION = "3.0.3"
OPT_IN_LIVE_COMMANDS = frozenset({"execute-openai"})
ENVELOPE_FIELDS = ("contract_version", "command", "status", "data", "diagnostics")


def _subparsers(parser: Any) -> dict[str, Any]:
    names: dict[str, Any] = {}
    subparsers = getattr(parser, "_subparsers", None)
    if subparsers is None:
        return names
    for action in subparsers._group_actions:
        names.update(action.choices)
    return names


def _argument_schema(action: Any) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    if action.type is int:
        schema = {"type": "integer"}
    elif action.type is float:
        schema = {"type": "number"}
    if getattr(action, "choices", None):
        schema["enum"] = list(action.choices)
    if action.help:
        schema["description"] = action.help
    return schema


def _command_request_schema(subparser: Any) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for action in subparser._actions:
        option_strings = tuple(action.option_strings)
        if action.dest in {"help", "func"}:
            continue
        if option_strings == ("-h", "--help") or option_strings == ("--help",):
            continue
        name = action.dest.replace("_", "-")
        if option_strings:
            flag = option_strings[-1].lstrip("-")
            name = flag
        if getattr(action, "const", None) is True or action.nargs == 0:
            properties[name] = {"type": "boolean", "description": action.help or ""}
            continue
        properties[name] = _argument_schema(action)
        if action.required or not option_strings:
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "additionalProperties": False, "properties": properties}
    if required:
        schema["required"] = required
    return schema


def build_openapi() -> dict[str, Any]:
    parser = build_parser()
    commands = _subparsers(parser)
    cli_names = sorted(commands)
    opt_in_live = sorted(name for name in cli_names if name in OPT_IN_LIVE_COMMANDS)
    default_slice = sorted(name for name in cli_names if name not in OPT_IN_LIVE_COMMANDS)
    paths: dict[str, Any] = {}
    for name, subparser in sorted(commands.items()):
        in_default = name not in OPT_IN_LIVE_COMMANDS
        paths[f"/v0/compiler/{name}"] = {
            "post": {
                "operationId": name.replace("-", "_"),
                "summary": (
                    getattr(subparser, "description", None)
                    or getattr(subparser, "help", None)
                    or name
                ).strip(),
                "tags": ["default-hosted-slice" if in_default else "opt-in-live"],
                "x-default-hosted-slice": in_default,
                "x-cli-command": name,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": _command_request_schema(subparser),
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Compiler JSON envelope. Transport metadata may be stripped for library/CLI parity.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ResultEnvelope"}
                            }
                        },
                    }
                },
            }
        }
    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": "Proofhouse hosted-slice compiler transport",
            "version": "0.1.0-draft",
            "description": (
                "Generated from proofhouse-compiler CLI. Not a hosted implementation. "
                "Q2 is unpicked. execute-openai is opt-in live and is not on the default hosted path. "
                "UI must not own semantics."
            ),
        },
        "x-cli-commands": cli_names,
        "x-default-hosted-slice": default_slice,
        "x-opt-in-live": opt_in_live,
        "x-q2-ratified": False,
        "paths": paths,
        "components": {
            "schemas": {
                "ResultEnvelope": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(ENVELOPE_FIELDS),
                    "properties": {
                        "contract_version": {"type": "string"},
                        "command": {"type": "string"},
                        "status": {"type": "string"},
                        "data": {"type": "object"},
                        "diagnostics": {"type": "array", "items": {"type": "object"}},
                    },
                }
            }
        },
    }


def dump_openapi(document: dict[str, Any] | None = None) -> str:
    payload = document if document is not None else build_openapi()
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_openapi(path: str) -> str:
    text = dump_openapi()
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return text
