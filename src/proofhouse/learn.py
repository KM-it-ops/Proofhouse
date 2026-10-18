"""Learn a kind Proofhouse does not know yet, then make it like any other kind.

A kind is a name: ``proofhouse make --kind press-kit`` or ``artifact_class=press-kit``. When the name
is not a built-in kind and no add-on brings it, Proofhouse does not refuse it and does not swap in a
kind it knows. The model you picked researches it first: what it is, what a finished, high-quality
one contains, and the instructions a writer follows to make one. That answer is checked like an
add-on's make kind and saved in the add-on pack ``learned``
(``PROOFHOUSE_HOME/addons/learned/addon.json``), so later makes of that kind skip the research.

The research call goes through ``live.run_prompt`` and so through the spend gate, inside the same
spending limit as the rest of the command. What the model says is the model's account: the sources
it names are recorded as given and marked as not checked. Remove a learned kind with
``proofhouse addons remove learned`` (all of them) or edit the pack file.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import addons, providers

LEARNED_PACK = "learned"
SOURCES_NOTE = "named by the model that researched this kind; not checked"
# Kinds with an engine of their own: ``proofhouse make --kind video|launch`` runs them, not the writer loop.
OWN_ENGINE = frozenset({"video", "launch"})

_RESEARCH = (
    "Proofhouse makes many kinds of things for people. Someone asked it to make a {kind}, a kind it has not made "
    "before. Research what a {kind} is and what a finished, high-quality {kind} contains: its parts, format, usual "
    "length, conventions, and what people who make them for a living check before they call one done. Then write the "
    "instructions a writer model will follow to make a {kind} from any request. Reply with JSON only: "
    '{"what_it_is": "<one or two sentences>", '
    '"write": "<the writer instructions: start with \'You make\', say what a finished {kind} must include and the '
    'quality bar, and end by telling the writer to output only the finished {kind}>", '
    '"subject": "<a short label in capitals for the finished thing>", '
    '"sources": ["<web addresses of official or well-known pages that describe a {kind}, if you know any>"]}'
)


class LearnError(ValueError):
    """The research answer cannot be used to make the kind."""


def kind_name(text: str) -> str | None:
    """The kind name a person meant: ``"Press Kit"`` is ``press-kit``. ``None`` when nothing usable is left."""
    name = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return name if addons._KIND.fullmatch(name) else None


def research_prompt(kind: str) -> str:
    return _RESEARCH.replace("{kind}", kind)


def parse(kind: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    """The make-kind entry the research answer describes, or ``LearnError``."""
    match = re.search(r"\{.*\}", answer or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    write = data.get("write")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    if not isinstance(write, str) or len(write.strip()) < 20:
        raise LearnError("the model wrote no usable instructions for making one")
    subject = data.get("subject")
    label = re.sub(r"[^A-Z0-9 ]+", " ", subject.upper()).strip()[:40] if isinstance(subject, str) else ""
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    return {
        "kind": kind,
        "write": f"{write.strip()[:6000]}\n\nWhat a {kind} is: {what.strip()[:600]}",
        "subject": label or kind.upper().replace("-", " "),
        "what_it_is": what.strip()[:600],
        "sources": [s for s in sources if isinstance(s, str) and re.match(r"https?://\S+$", s) and len(s) <= 300][:10],
        "sources_note": SOURCES_NOTE,
        "learned_by": learned_by,
        "learned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def pack_path() -> Path:
    return addons.packs_dir() / LEARNED_PACK / "addon.json"


def save(entry: dict[str, Any]) -> Path:
    """Add or replace one kind in the ``learned`` pack. A pack that cannot be read is kept aside, never lost."""
    path = pack_path()
    kinds: list[dict[str, Any]] = []
    if path.is_file():
        try:
            kinds = addons._check(json.loads(path.read_text(encoding="utf-8")), str(path), "pack").contents["make_kinds"]
        except (OSError, ValueError):
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            path.replace(path.with_name(f"addon.json.unreadable-{stamp}"))
    raw = {
        "schema": addons.ADDON_SCHEMA,
        "name": LEARNED_PACK,
        "version": "1",
        "description": "Kinds Proofhouse researched and learned the first time you asked for them",
        "make_kinds": [k for k in kinds if k.get("kind") != entry["kind"]] + [entry],
    }
    addons._check(raw, str(path), "pack")  # the same check every pack passes
    providers.write_atomic(path, json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return path


def learn(kind: str, ask: Callable[[str], str | None], *, learned_by: str) -> dict[str, Any]:
    """Research ``kind`` with one call to ``ask`` (a call through the spend gate), save it, return its entry."""
    entry = parse(kind, ask(research_prompt(kind)), learned_by=learned_by)
    save(entry)
    return entry


def learn_with_model(
    kind: str,
    *,
    provider_id: str,
    model: str,
    max_cost_usd: str | None = None,
    max_output_tokens: int = 2048,
    transport: Any = None,
) -> dict[str, Any]:
    """``learn`` with one ``live.run_prompt`` call, for callers outside ``make`` (the front door)."""
    from . import live

    def ask(prompt: str) -> str | None:
        reply = live.run_prompt(
            provider_id, model, prompt=prompt, input_text=None,
            max_output_tokens=max_output_tokens, max_cost_usd=max_cost_usd, transport=transport,
        )
        if reply.status != "success":
            raise LearnError(reply.message or reply.code or "the research call did not succeed")
        return reply.output_text

    return learn(kind, ask, learned_by=f"{provider_id}/{model}")
