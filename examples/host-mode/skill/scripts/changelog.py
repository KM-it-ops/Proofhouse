#!/usr/bin/env python3
"""Build a Keep a Changelog release section from conventional commits."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

COMMIT_RE = re.compile(
    r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$"
)
SKIP_TYPES = frozenset({"chore", "docs", "test", "ci", "style", "build"})
SECTION_ORDER = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git_ok(repo: Path) -> bool:
    r = run_git(repo, "rev-parse", "--git-dir")
    return r.returncode == 0 and r.stdout.strip()


def has_commits(repo: Path) -> bool:
    r = run_git(repo, "rev-parse", "HEAD")
    return r.returncode == 0


def latest_tag(repo: Path) -> str | None:
    r = run_git(repo, "tag", "--sort=-v:refname")
    if r.returncode != 0:
        return None
    for line in r.stdout.splitlines():
        tag = line.strip()
        if tag:
            return tag
    return None


def resolve_since(repo: Path, since: str | None) -> str | None:
    if since:
        r = run_git(repo, "rev-parse", "--verify", since)
        if r.returncode != 0:
            eprint(f"error: unknown git ref: {since}")
            sys.exit(1)
        return since
    tag = latest_tag(repo)
    return tag


def parse_commits(repo: Path, since_ref: str | None) -> list[tuple[str, str, bool, str | None]]:
    """Return list of (type, subject, breaking, scope)."""
    log_args = ["log", "--reverse", "--format=%B%x00"]
    if since_ref:
        log_args.append(f"{since_ref}..HEAD")
    r = run_git(repo, *log_args)
    if r.returncode != 0:
        eprint(r.stderr.strip() or "error: git log failed")
        sys.exit(1)
    raw = r.stdout
    if not raw.strip():
        return []

    entries: list[tuple[str, str, bool, str | None]] = []
    for block in raw.split("\0"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        subject_line = lines[0].strip()
        body = "\n".join(lines[1:])
        footer_breaking = "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body

        m = COMMIT_RE.match(subject_line)
        if not m:
            continue
        ctype = m.group("type").lower()
        if ctype in SKIP_TYPES:
            continue
        breaking = bool(m.group("breaking")) or footer_breaking
        scope = m.group("scope")
        subject = m.group("subject").strip()
        entries.append((ctype, subject, breaking, scope))
    return entries


def section_for(ctype: str) -> str | None:
    if ctype in ("feat", "feature"):
        return "Added"
    if ctype == "fix":
        return "Fixed"
    if ctype in ("refactor", "perf", "change"):
        return "Changed"
    if ctype == "deprecate":
        return "Deprecated"
    if ctype == "remove":
        return "Removed"
    if ctype == "security":
        return "Security"
    return None


def format_item(subject: str, breaking: bool, scope: str | None) -> str:
    prefix = f"**{scope}:** " if scope else ""
    line = f"- {prefix}{subject}"
    if breaking:
        line += " **BREAKING**"
    return line


def render(version: str | None, entries: list[tuple[str, str, bool, str | None]]) -> str:
    if not entries:
        heading = f"## [{version}] - {date.today().isoformat()}" if version else "## Unreleased"
        return f"{heading}\n\n_No user-facing changes in this range._\n"

    ver = version or "Unreleased"
    if version:
        heading = f"## [{version}] - {date.today().isoformat()}"
    else:
        heading = "## Unreleased"

    buckets: dict[str, list[str]] = {s: [] for s in SECTION_ORDER}
    for ctype, subject, breaking, scope in entries:
        section = section_for(ctype)
        if section is None:
            continue
        buckets[section].append(format_item(subject, breaking, scope))

    parts = [heading, ""]
    for section in SECTION_ORDER:
        items = buckets[section]
        if not items:
            continue
        parts.append(f"### {section}")
        parts.extend(items)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a Keep a Changelog release block from conventional commits."
    )
    parser.add_argument("repo", type=Path, help="Path to a git repository")
    parser.add_argument("--since", help="Git ref to start after (default: latest tag, or all history)")
    parser.add_argument("--version", help="Version for the release heading (e.g. 1.2.3)")
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not repo.is_dir():
        eprint(f"error: not a directory: {repo}")
        return 1
    if not git_ok(repo):
        eprint(f"error: not a git repository: {repo}")
        return 1
    if not has_commits(repo):
        eprint("note: repository has no commits")
        print(render(args.version, []))
        return 0

    since_ref = resolve_since(repo, args.since)
    entries = parse_commits(repo, since_ref)
    sys.stdout.write(render(args.version, entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
