"""The goal picker's model path: a model reads the goal and picks the kind of thing to make.

The overseer uses it when a model is set up. The one call goes through
``live.run_prompt`` and so through the spend gate. An answer that cannot be
used (the call was refused or failed, no JSON came back, or the kind is not on
the list) falls back to the built-in rules, and the rationale says so.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Any

from .route import _ALLOWED, LEGACY_NAMES, RouteDecision, RouteRequest

MAX_OUTPUT_TOKENS = 400

_KINDS = """prompt (instructions one model follows, kept and used again and again),
skill (know-how an agent loads when a task needs it),
agent (a specialist subagent with its own instructions and tools),
site (a website people visit),
app (a working application people use, with its own screens and data),
copy (words to publish: a post, an email, a listing, an announcement),
rule (standing instructions an AI coding tool always follows in a project),
mcp (a server that gives AI tools access to a system or its data),
hook (something that runs by itself when an event happens inside an AI coding tool),
video (a finished video: footage or images, voice, music and the edit),
launch (several parts made together from one goal, such as a site, a video and copy),
loop (a job that repeats on its own, on a schedule or until a goal is met, within limits),
workflow (fixed steps run in order, some by a model and some by code),
tool (one function an AI model can call),
API (a service other programs call over the network),
harness (the setup that runs and checks an agent over many runs and keeps its state),
plain_code (ordinary code with no model in it),
one_prompt (just answer once now; nothing worth keeping),
nothing_new (nothing needs to be made)"""

_PICK = """You decide what kind of thing to make for a goal. Choose ONE kind from this list only:
%s.
Judge by what the person needs done, not by single words in the goal.
If two kinds fit about equally well and the choice changes what gets built, also write one short question that
tells them apart, and list those kinds as options, starting with the one you would pick if you could not ask.
Otherwise leave the question empty and the options empty.
Answer with ONE JSON object and nothing else:
{"kind": "...", "reason": "one sentence on why", "question": "", "options": []}

GOAL:
%s"""


def _addon_kinds() -> dict[str, str]:
    """Make kinds that add-on packs bring, with what each makes."""
    from ... import addons

    try:
        found = addons.make_kinds()
    except Exception:  # noqa: BLE001 -- a broken pack must not stop the pick
        return {}
    return {kind: str(entry.get("subject") or kind) for kind, entry in found.items() if kind not in _ALLOWED}


def _json(text: str | None) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _kind(value: Any) -> str | None:
    return LEGACY_NAMES.get(value, value) if isinstance(value, str) else None


def _fallback(rules: RouteDecision, why: str) -> RouteDecision:
    return replace(rules, rationale=f"{rules.rationale} (built-in rules; the model's pick was not used: {why})")


def pick_with_model(
    request: RouteRequest,
    rules: RouteDecision,
    *,
    provider_id: str,
    model: str,
    max_cost_usd: str | None = None,
    transport: Any = None,
) -> RouteDecision:
    """Ask the model for the kind; ``rules`` is the built-in pick to fall back to."""
    from ... import live

    extra = _addon_kinds()
    kinds = _KINDS + "".join(f",\n{kind} (an add-on kind that makes: {what})" for kind, what in sorted(extra.items()))
    reply = live.run_prompt(
        provider_id,
        model,
        prompt=_PICK % (kinds, request.objective),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        max_cost_usd=max_cost_usd,
        transport=transport,
    )
    if reply.status != "success":
        return _fallback(rules, reply.message or reply.status)
    data = _json(reply.output_text)
    if data is None:
        return _fallback(rules, "it did not answer with the JSON asked for")
    allowed = set(_ALLOWED) | set(extra)
    kind = _kind(data.get("kind"))
    if kind not in allowed:
        return _fallback(rules, f"it answered {data.get('kind')!r}, which is not on the list")
    reason = data.get("reason")
    reason = reason.strip() if isinstance(reason, str) and reason.strip() else "it gave no reason"
    question = data.get("question")
    question = question.strip() if isinstance(question, str) and question.strip() else None
    raw_options = data.get("options") if isinstance(data.get("options"), list) else []
    options = tuple(dict.fromkeys(o for o in map(_kind, raw_options) if o in allowed))
    if kind not in options:
        options = (kind, *options)
    if question is None or len(options) < 2:
        question, options = None, ()
    return RouteDecision(kind, f"model {reply.provider}/{reply.model}: {reason}", kind == "site", question, options)
