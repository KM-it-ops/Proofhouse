"""CLI for host mode: check, record, render video."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import host
EXIT_OK = 0
EXIT_USAGE = 2


def _fail(message: str) -> int:
    import sys

    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def _parse_score(value: str) -> int:
    try:
        number = float(value)
    except ValueError:
        raise SystemExit(EXIT_USAGE)
    if number != int(number) or not 0 <= number <= 10:
        raise SystemExit(EXIT_USAGE)
    return int(number)


def _cmd_check(args: argparse.Namespace) -> int:
    code = host.run_check(args.kind, args.path, allow_commands=args.allow_commands, as_json=args.json)
    if code == 0:
        return EXIT_OK
    if code == 2:
        return EXIT_USAGE
    return 1


def _cmd_record(args: argparse.Namespace) -> int:
    score: int | None = _parse_score(args.score) if args.score is not None else None
    judge_name: str | None = args.judge
    judge_score: int | None = _parse_score(args.judge_score) if args.judge_score is not None else None
    if (judge_name is None) != (judge_score is None):
        return _fail("--judge and --judge-score must be used together")
    if judge_name is not None and host.agent_base(judge_name) == host.agent_base(args.agent):
        return _fail("judge must be a different agent from the one that wrote this version")
    code = host.run_record(
        args.kind,
        args.path,
        out=args.out,
        request=args.request,
        agent=args.agent,
        score=score,
        judge=judge_name,
        judge_score=judge_score,
        judge_note=args.judge_note,
        allow_commands=args.allow_commands,
        as_json=args.json,
    )
    if code == 0:
        return EXIT_OK
    if code == 2:
        return EXIT_USAGE
    return 1


def _cmd_render_video(args: argparse.Namespace) -> int:
    formats = tuple(part.strip() for part in args.formats.split(",") if part.strip())
    if not formats:
        return _fail("name at least one format")
    code = host.run_render_video(args.folder, formats=formats, size_scale=args.size_scale)
    return EXIT_OK if code == 0 else EXIT_USAGE


def add_host_commands(subparsers: argparse._SubParsersAction) -> None:
    p_check = subparsers.add_parser(
        "check",
        help="Check model-written work offline (site, mcp, hook, rule, skill, agent).",
    )
    p_check.add_argument("kind", choices=host.CHECK_KINDS)
    p_check.add_argument("path", type=Path)
    p_check.add_argument("--json", action="store_true", help="Emit JSON rows.")
    p_check.add_argument(
        "--allow-commands",
        action="store_true",
        help="Start MCP or hook commands to check them (model-written code with your rights).",
    )
    p_check.set_defaults(func=_cmd_check)

    p_record = subparsers.add_parser(
        "record",
        help="Save a version, run checks, and deliver the best passing version.",
    )
    p_record.add_argument("kind", choices=host.RECORD_KINDS)
    p_record.add_argument("path", type=Path)
    p_record.add_argument("--out", required=True, type=Path)
    p_record.add_argument("--request", required=True, help="What you asked the agent to make.")
    p_record.add_argument("--agent", required=True, help="Name of the agent that wrote this version.")
    p_record.add_argument("--score", default=None, help="Agent's 0-10 score for this version.")
    p_record.add_argument("--judge", default=None, help="Name of a different agent that scored this version.")
    p_record.add_argument("--judge-score", default=None, help="That judge's 0-10 score for this version.")
    p_record.add_argument("--judge-note", default=None, help="One short sentence from the judge.")
    p_record.add_argument("--allow-commands", action="store_true")
    p_record.add_argument("--json", action="store_true")
    p_record.set_defaults(func=_cmd_record)

    p_render = subparsers.add_parser("render", help="Assemble finished videos from your own shot files.")
    render_sub = p_render.add_subparsers(dest="render_command", required=True)
    p_video = render_sub.add_parser("video", help="Render script.json into MP4 files with FFmpeg.")
    p_video.add_argument("folder", type=Path)
    p_video.add_argument("--formats", default="16x9,9x16,1x1", help="Comma-separated aspect ratios.")
    p_video.add_argument("--size-scale", type=float, default=1.0, help="Scale frame size (for tests or drafts).")
    p_video.set_defaults(func=_cmd_render_video)
