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


def extract_answer(answer: str | None) -> dict[str, Any] | None:
    """The one JSON object in a research answer, or ``None`` when it is not that object."""
    match = re.search(r"\{.*\}", answer or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    return data if isinstance(data, dict) else None


def provenance(answer: dict[str, Any], *, learned_by: str, what_limit: int = 600, source_limit: int = 10) -> dict[str, Any]:
    """Where a learned entry came from. The sources are the model's own list, marked as not checked."""
    sources = answer.get("sources") if isinstance(answer.get("sources"), list) else []
    what = answer.get("what_it_is")
    text = what.strip() if isinstance(what, str) else ""
    return {
        "what_it_is": text[:what_limit],
        "sources": [s for s in sources if isinstance(s, str) and re.match(r"https?://\S+$", s) and len(s) <= 300][:source_limit],
        "sources_note": SOURCES_NOTE,
        "learned_by": learned_by,
        "learned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def ask_model(provider_id: str, model: str, prompt: str, *, max_cost_usd: str | None = None,
              max_output_tokens: int = 2048, transport: Any = None) -> str | None:
    """One research call through ``live.run_prompt``, and so through the spend gate."""
    from . import live

    reply = live.run_prompt(
        provider_id, model, prompt=prompt, input_text=None,
        max_output_tokens=max_output_tokens, max_cost_usd=max_cost_usd, transport=transport,
    )
    if reply.status != "success":
        raise LearnError(reply.message or reply.code or "the research call did not succeed")
    return reply.output_text


def parse(kind: str, answer: str | None, *, learned_by: str) -> dict[str, Any]:
    """The make-kind entry the research answer describes, or ``LearnError``."""
    data = extract_answer(answer)
    if data is None:
        raise LearnError("the model's research answer was not the JSON asked for")
    what = data.get("what_it_is")
    write = data.get("write")
    if not isinstance(what, str) or not what.strip():
        raise LearnError("the model did not say what it is")
    if not isinstance(write, str) or len(write.strip()) < 20:
        raise LearnError("the model wrote no usable instructions for making one")
    subject = data.get("subject")
    label = re.sub(r"[^A-Z0-9 ]+", " ", subject.upper()).strip()[:40] if isinstance(subject, str) else ""
    return {
        "kind": kind,
        "write": f"{write.strip()[:6000]}\n\nWhat a {kind} is: {what.strip()[:600]}",
        "subject": label or kind.upper().replace("-", " "),
        **provenance(data, learned_by=learned_by),
    }


def pack_path() -> Path:
    return addons.packs_dir() / LEARNED_PACK / "addon.json"


def _empty_pack() -> dict[str, Any]:
    return {"schema": addons.ADDON_SCHEMA, "name": LEARNED_PACK, "version": "1",
            "description": "Things Proofhouse researched the first time you asked for them"}


def _keep_aside(path: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path.replace(path.with_name(f"addon.json.unreadable-{stamp}"))


def read_pack() -> dict[str, Any]:
    """The learned pack. A file that cannot be read, or that is not a pack object, is kept aside."""
    path = pack_path()
    if not path.is_file():
        return _empty_pack()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    try:
        checked = addons._check(data, str(path), "pack")
        addons._check_entries(checked)
    except (TypeError, ValueError):
        _keep_aside(path)
        return _empty_pack()
    return data


def write_pack(raw: dict[str, Any]) -> Path:
    providers.write_atomic(pack_path(), json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    return pack_path()


def save_section(section: str, entry: dict[str, Any], id_key: str) -> Path:
    """Add or replace one entry in the learned pack. The pack is checked before it is written."""
    from . import app_platforms, deploy, hosts, media, train

    raw = read_pack()
    for key in addons.SECTIONS:
        raw.setdefault(key, [])
    entries = [item for item in raw.get(section, []) if isinstance(item, dict) and item.get(id_key) != entry[id_key]]
    raw[section] = entries + [entry]
    raw["schema"] = addons.ADDON_SCHEMA
    raw["name"] = LEARNED_PACK
    raw.setdefault("version", "1")
    raw.setdefault("description", "Things Proofhouse researched the first time you asked for them")
    addon = addons._check(raw, str(pack_path()), "pack")
    if section == "app_platforms":
        for item in addon.contents["app_platforms"]:
            app_platforms._validate_entry(item, "learned")
    if section == "hosts":
        hosts._check_hosts(addon.contents["hosts"], "learned")
    if section == "deploy_targets":
        for item in addon.contents["deploy_targets"]:
            deploy._check(item, "learned")
    if section == "media_providers":
        for item in addon.contents["media_providers"]:
            media._parse(item, "learned")
    if section == "training_services":
        for item in addon.contents["training_services"]:
            train._parse(item, "learned")
    return write_pack(raw)


def save(entry: dict[str, Any]) -> Path:
    """Add or replace one kind in the ``learned`` pack. A pack that cannot be read is kept aside, never lost."""
    return save_section("make_kinds", entry, "kind")


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

    def ask(prompt: str) -> str | None:
        return ask_model(provider_id, model, prompt, max_cost_usd=max_cost_usd,
                         max_output_tokens=max_output_tokens, transport=transport)

    return learn(kind, ask, learned_by=f"{provider_id}/{model}")
