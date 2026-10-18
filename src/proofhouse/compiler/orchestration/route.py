"""Artifact-class router. Upstream of IR. No network.

``route()`` is the goal picker's built-in rules: it picks the kind of thing to
make with no model and no key. It answers with a ``proofhouse make`` kind
wherever one fits, and with an older class only where make has no kind yet.
A goal that could fairly be two kinds also carries one short question for a
person and the kinds that answer it; ``artifact_class`` is then the pick to use
when nobody can be asked.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

ArtifactClass = Literal[
    # Kinds that ``proofhouse make`` makes.
    "prompt",
    "skill",
    "agent",
    "site",
    "app",
    "copy",
    "rule",
    "mcp",
    "hook",
    "video",
    "launch",
    # Classes with no make kind yet.
    "loop",
    "workflow",
    "tool",
    "API",
    "harness",
    "plain_code",
    # Consumption-governor exits.
    "nothing_new",
    "one_prompt",
]

MAKE_KINDS: tuple[ArtifactClass, ...] = (
    "prompt", "skill", "agent", "site", "app", "copy", "rule", "mcp", "hook", "video", "launch",
)
OTHER_CLASSES: tuple[ArtifactClass, ...] = ("loop", "workflow", "tool", "API", "harness", "plain_code")
_ALLOWED: tuple[ArtifactClass, ...] = MAKE_KINDS + OTHER_CLASSES + ("nothing_new", "one_prompt")
# Older class names, still accepted wherever a class is named.
LEGACY_NAMES: dict[str, ArtifactClass] = {"subagent": "agent", "MCP": "mcp", "media": "video"}

# Ask when the leader is ahead by this many points or fewer.
_CLOSE = 2
# A product signal at least this strong is a named thing to make, and earns the object bonus.
_CLEAR_PRODUCT = 4
_OBJECT_BONUS = 2

# Plain words for one question template. The safer pick is described first.
_PLAIN: dict[str, str] = {
    "prompt": "kept instructions for a model",
    "one_prompt": "one answer right now",
    "skill": "know-how an agent loads",
    "agent": "a specialist subagent",
    "site": "a website people visit",
    "app": "an app people use",
    "copy": "words to publish",
    "rule": "rules a coding tool always follows",
    "mcp": "access to a system for AI tools",
    "hook": "a reaction to a coding-tool event",
    "video": "a finished video",
    "launch": "several parts made together",
    "loop": "a job that repeats on its own",
    "workflow": "fixed steps in order",
    "tool": "one function a model calls",
    "API": "a service programs call",
    "harness": "state kept across runs",
    "plain_code": "ordinary code with no model",
}
# Earlier is safer when two scores tie.
_SAFER: tuple[str, ...] = (
    "prompt", "skill", "rule", "loop", "workflow", "tool", "hook", "app", "site", "mcp", "agent",
    "harness", "plain_code", "copy", "API", "video", "launch", "one_prompt",
)
_WHY: dict[str, str] = {
    "prompt": "default: one prompt program for one provider",
    "skill": "know-how an agent loads when a task needs it",
    "agent": "a specialist with its own instructions and tools",
    "site": "dispatch to ship-walk as website-build module",
    "app": "an application people use with its own screens",
    "copy": "words to publish for people to read",
    "rule": "standing instructions a coding tool always follows",
    "mcp": "gives ai tools access to an outside system",
    "hook": "runs when an event happens in a coding tool",
    "video": "non-reproducible lane; outside sealed deterministic core",
    "launch": "several parts made together from one goal",
    "loop": "runs on its own without an operator present, on a schedule or until done",
    "workflow": "fixed steps run in order",
    "tool": "one function a model can call",
    "API": "a service other programs call over the network",
    "harness": "keeps state across runs",
    "plain_code": "ordinary code with no model in it",
    "one_prompt": "consumption governor: a single prompt suffices",
    "nothing_new": "consumption governor: no new artifact",
}

# Verbs whose object is the thing to make, not the thing it reads.
_MAKE = re.compile(
    r"\b(?:make|build|write|create|design|generate|draft|produce|develop|ship|set up|give me|need|prepare|compose)\b"
)
_BOUNDARY = re.compile(
    r"\b(?:that|which|whose|while|when|until|whenever|before|after|once|if|so|because|with|from|into|for|by)\b"
)
# "with" stays: it usually adds a part of the thing ("with a voice-over"), not what it reads.
_PREP = re.compile(r"\b(?:for|about|from|of|into|on|in|over|across|through)\s+(?:\w+\s+){0,4}$")
_INSTRUMENT = re.compile(
    r"\s+(?:\w+\s+){0,2}?(?:scraper|crawler|spider|parser|converter|importer|exporter|checker|monitor|"
    r"fetcher|extractor|uploader|downloader)\b"
)
_SECRET_AFTER = re.compile(r"\s*(?:key|keys|token|tokens|secret|secrets)\b")
_CALLER_AFTER = re.compile(r"(?:'s|\s+can call)\b")
_JUDGMENT = re.compile(
    r"\b(?:translat\w*|summar(?:i[sz]\w*)|draft\w*|rewrit\w*|classif\w*|review\w*|research\w*|analy[sz]\w*)\b"
)
_ACTION = re.compile(
    r"\b(research\w*|compar\w*|summar(?:i[sz]\w*)|draft\w*|review|analy[sz]\w*|gather\w*|collect\w*|"
    r"document\w*|translat\w*|classif\w*|design\w*|test\w*|deploy\w*|fix\w*|check\w*|open|send\w*|pull\w*|"
    r"build\w*|creat(?:e|es|ed|ing)|writ\w*|generat\w*|answer\w*|updat\w*|email\w*|find\w*|merg\w*|"
    r"publish\w*|notif\w*|archiv\w*)\b"
)
_LANGUAGES = (
    "french", "spanish", "german", "japanese", "chinese", "arabic", "portuguese", "italian", "korean",
    "dutch", "polish", "swedish", "norwegian", "danish", "finnish", "greek", "hebrew", "hindi",
    "turkish", "russian", "ukrainian", "vietnamese", "thai", "indonesian", "malay", "czech",
    "romanian", "hungarian",
)
# A vague request names no artifact: help, "something", a bare assistant, or a short "automate".
_VAGUE = re.compile(
    r"\b(?:help me|help us|something that|something to|something people|into something|"
    r"an assistant|a helper|a chatbot|a way to)\b|^\s*automate\b"
)

# kind, weight, role, patterns. A group fires once. "product" is the thing to make.
_GROUPS: tuple[tuple[str, int, str, tuple[re.Pattern[str], ...]], ...] = (
    # Instructions a model is meant to keep and follow.
    ("prompt", 6, "product", (
        re.compile(r"\b(?:system prompt|prompt template|my prompt|our prompt|the prompt|a prompt|this prompt|prompts)\b"),
    )),
    # A bare kind-name is weak: it often names the runner, not the thing to make.
    ("skill", 1, "product", (re.compile(r"\bskills?\b"),)),
    ("agent", 1, "product", (re.compile(r"\bagents?\b"),)),
    # Know-how loaded for a task: a playbook, checklist, or reusable procedure.
    ("skill", 5, "product", (
        re.compile(r"\b(?:playbook|checklist|runbook|know-how|how-to|best practices|reusable procedure)\b"),
    )),
    ("skill", 4, "behavior", (
        re.compile(r"\b(?:reusable|across projects|across repos|load when|when a task needs)\b"),
    )),
    ("skill", 2, "behavior", (re.compile(r"\b(?:teach|teaches|teaching)\b"),)),
    # "Assistant" names no single kind: know-how, a specialist, or a product people open.
    ("skill", 3, "product", (re.compile(r"\b(?:an assistant|a helper|a chatbot)\b"),)),
    ("agent", 3, "product", (re.compile(r"\b(?:an assistant|a helper|a chatbot)\b"),)),
    ("app", 3, "product", (re.compile(r"\b(?:an assistant|a helper|a chatbot)\b"),)),
    # A specialist another tool hands work to.
    ("agent", 5, "product", (
        re.compile(
            r"\b(?:subagent|code reviewer|reviewer agent|review agent|isolated context|its own tools)\b"
            r"|\bparallel(?: \w+){0,3} workers\b|\breviewer\b"
        ),
    )),
    # A place people visit in a browser.
    ("site", 6, "product", (
        re.compile(
            r"\b(?:website|web site|landing page|home ?page|marketing site|brochure site|"
            r"splash page|web ?page|pitch site)\b|\bsite\b"
        ),
    )),
    # An application people use to do work, with screens or saved data.
    ("app", 5, "product", (
        re.compile(
            r"\b(?:dashboard|admin panel|portal|web ?app|mobile app|desktop app|saas|internal tool)\b"
            r"|\b(?:an|the) application\b|\ban app\b"
            r"|\b(?:users|customers|staff|employees) can (?:create|save|upload|log in|sign in|manage|edit|book|approve|track)\b"
        ),
    )),
    # Words meant to be published: a post, an email, a listing, an announcement.
    ("copy", 6, "product", (
        re.compile(
            r"\b(?:blog post|linkedin post|social post|newsletter|press release|product description|"
            r"ad copy|sales copy|caption|tagline|slogan|announcement|welcome email|marketing email|"
            r"launch email|cold email|sales email|(?:product|job|store) listing)\b"
            r"|\b(?:an|the|our|a) email\b(?!\s+(?:me|us)\b)"
            r"|\bemail (?:to|for) (?:our |my )?(?:customers|users|subscribers|clients|guests)\b"
        ),
    )),
    # Standing instructions a coding tool applies on its own.
    ("rule", 6, "product", (
        re.compile(
            r"\b(?:commit message|commit convention|coding standard|style guide|house style|code style|"
            r"coding convention|naming convention|conventions|contributing guide|changelog rules?)\b"
            r"|\balways (?:follow|follows|apply|applies|use|uses)\b|\bstanding instructions\b|\brules\b"
        ),
    )),
    # A server that lets AI tools reach a system. Named outright, so it outranks side details.
    ("mcp", 9, "product", (re.compile(r"\bmcp(?: server)?\b|\bmodel context protocol\b"),)),
    # Ongoing access: several operations, or connecting a coding agent to a system.
    ("mcp", 6, "behavior", (
        re.compile(
            r"\bread and (?:update|write|edit|delete|create)\b"
            r"|\bconnect\b.{0,60}\b(?:database|postgres|mysql|mongo|warehouse|jira|slack|salesforce|notion|sharepoint|system)\b"
            r"|\b(?:give|let) (?:my |our |the )?(?:agents|claude|cursor)\b.{0,40}\b(?:access|read|query)\b"
            r"|\b(?:server|connector)\b.{0,40}\b(?:cursor|claude|codex|agents|ai tools)\b"
        ),
    )),
    # Fires on an event inside a coding tool, and can stop that event.
    ("hook", 7, "behavior", (
        re.compile(
            r"\b(?:pre|post)-(?:commit|push|merge|checkout)\b|\b(?:commit|push) hook\b|\bgit hook\b"
            r"|\b(?:block|prevent|reject|stop|refuse)\b.{0,40}\b(?:commit|push|merge)\b"
            r"|\b(?:commit|push|merge)\b.{0,40}\b(?:block|reject|refuse|prevent)\b"
            r"|\bbefore (?:each |every |a |any )?(?:commit|push|merge)\b"
            r"|\b(?:when|after)\b.{0,40}\b(?:finishes|completes|ends|is done)\b"
            r"|\b(?:run|install|add|set up) (?:a |the )?hook\b"
            r"|\b(?:on|when i|when we) (?:commit|push)\b"
        ),
    )),
    # Might be an event reaction, or just a condition a watcher reports.
    ("hook", 2, "behavior", (
        re.compile(
            r"\b(?:tells|tell|pings|ping|messages|message|alerts|alert|notifies|notify) (?:me|us|the \w+|our \w+) when\b"
            r"|\bwhen something\b"
            r"|\bwhen\b.{0,50}\b(?:happens|drifts|jumps|fails|spikes|drops|changes)\b"
        ),
    )),
    # A finished video: footage or a clip, voice, and the edit.
    ("video", 6, "product", (
        re.compile(
            r"\b(?:video|footage|voice-over|voiceover|voice over|explainer|reel|short clip|product clip|video clip)\b"
            r"|\b\d+[ -]seconds? (?:clip|spot|film)\b"
        ),
    )),
    # A still picture goes to the same media lane, but weakly: it names the thing only when nothing else does,
    # and only as the last word of the thing ("an image search tool" is a tool).
    ("video", 2, "product", (
        re.compile(
            r"(?<!docker )(?<!container )(?<!disk )(?<!base )\b(?:images?|thumbnails?|illustrations?|artwork)\b"
            r"(?=\s*(?:$|[.,;:!?)]|(?:of|for|with|that|which|showing|in|on|about|from|and|to)\b))"
        ),
    )),
    # On a clock, or every weekday, with nobody starting it.
    ("loop", 5, "behavior", (
        re.compile(
            r"\b(?:every|each) (?:weekday |week )?(?:morning|night|evening|day|week|hour|weekday|monday|"
            r"tuesday|wednesday|thursday|friday|saturday|sunday)\b"
            r"|\b(?:daily|weekly|nightly|hourly|weekdays)\b|\bevery weekday\b"
            r"|\bonce a (?:day|week|month|morning)\b|\bevery other (?:day|week)\b|\bon a schedule\b|\bcron\b"
        ),
    )),
    # Keep going until a condition, a budget, or a stop.
    ("loop", 6, "behavior", (
        re.compile(
            r"\bkeep \w+ing\b.{0,80}\buntil\b|\brepeat\b.{0,40}\buntil\b|\buntil (?:it|they|the queue|the tests)\b"
            r"|\bstop at \$\d|\b(?:budget|spend|cost) (?:cap|limit|ceiling)\b"
        ),
    )),
    # Nobody is at the keyboard: away, unattended, or running on its own.
    ("loop", 4, "behavior", (
        re.compile(
            r"\bwhile\b.{0,24}\baway\b|\b(?:i am|i'm) away\b|\bwhen (?:i am|i'm) away\b"
            r"|\b(?:go|goes|going|gone|went|is|are|be|step|steps|stepped) away\b"
            r"|\baway from (?:my |the )?(?:keyboard|desk|computer|laptop)\b"
            r"|\bunattended\b|\bnobody watching\b|\bon its own\b|\bwithout (?:me|an operator)\b"
            r"|\bin the background\b"
        ),
    )),
    # Watching or polling, as opposed to a single pass.
    ("loop", 4, "behavior", (
        re.compile(r"\b(?:keep checking|keep watching|polling|watches|watch(?:ing)?|monitors|monitoring|notices)\b"),
    )),
    # "Automate X" can be a repeating job, a pipeline, or a script.
    ("loop", 2, "behavior", (re.compile(r"\bautomate\b"),)),
    ("workflow", 2, "behavior", (re.compile(r"\bautomate\b"),)),
    ("plain_code", 2, "behavior", (re.compile(r"\bautomate\b"),)),
    # The same model step over a set: each file, each row, or several languages.
    ("workflow", 4, "behavior", (
        re.compile(
            r"\bfor every (?!morning|night|evening|day|week|hour|weekday|monday|tuesday|wednesday|"
            r"thursday|friday|saturday|sunday)\w+"
            r"|\bfor each \w+|\b(?:every|each|all the) (?:files|images|photos|rows|records|pages|strings|"
            r"items|documents|emails|tickets)\b|\bper (?:language|locale|file|row|image|page|customer)\b"
        ),
    )),
    # One action a model can call. A command-line program is not this.
    ("tool", 6, "product", (
        re.compile(
            r"\b(?:a |one )?(?:function|callable)\b.{0,50}\b(?:call|calls|invoke|invokes)\b|\bcallable\b"
            r"|\b(?:agent|model)s? can call\b|\bone action\b|\bexternal system\b"
        ),
    )),
    # Reaching an outside system with credentials it holds.
    ("tool", 4, "behavior", (
        re.compile(
            r"\b(?:connect\w*|call\w*|reach\w*|access\w*|talk\w* to|authenticat\w*|query\w*|fetch\w*)\b.{0,40}"
            r"\b(?:credentials?|api keys?|tokens?)\b"
            r"|\b(?:credentials?|api keys?|tokens?)\b.{0,30}\bto (?:call|reach|access|connect|query|fetch|talk)\b"
        ),
    )),
    # Another program calls it over the network.
    ("API", 6, "product", (
        re.compile(
            r"\b(?:endpoint|rest api|http api|web api|graphql)\b"
            r"|\b(?:an|the|our) api\b(?!\s+(?:key|keys|token|tokens|secret))"
            r"|\b(?:my |our |the )?(?:app|service|program|backend) can call\b"
        ),
    )),
    # Memory that is still there on the next run.
    ("harness", 8, "behavior", (
        re.compile(
            r"\b(?:between|across) (?:sessions|runs|restarts|conversations)\b"
            r"|\bstate (?:must |should |has to |will )?survive\b"
            r"|\bmust survive\b.{0,30}\b(?:restarts?|reboots?|crash(?:es)?|failures?|runs?|sessions?)\b"
            r"|\b(?:persistent (?:memory|state|notes)|what it learned|left off)\b"
            r"|\b(?:remember\w*|learned|learnt|memory|persist\w*)\b.{0,80}\b(?:session|sessions|run|runs|restart)\b"
        ),
    )),
    # Said outright: no model, deterministic, ordinary code.
    ("plain_code", 8, "behavior", (
        re.compile(
            r"\b(?:deterministic|no llm|no model|without a model|without ai|no ai|plain code)\b"
        ),
    )),
    # A model writing or judging, when nothing else names the artifact.
    ("prompt", 2, "behavior", (re.compile(r"\b(?:translat\w*|summar(?:i[sz]\w*)|rewrit\w*|classif\w*|rephras\w*)\b"),)),
)


@dataclass(frozen=True)
class RouteRequest:
    objective: str
    constraints: dict[str, Any]


@dataclass(frozen=True)
class RouteDecision:
    # An ArtifactClass, an add-on make kind, or a new kind named in the request (learned when first made).
    artifact_class: str
    rationale: str
    ship_walk: bool
    # Only for a goal that could fairly be two kinds: one short question, and the kinds that answer it.
    question: str | None = None
    options: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["options"] = list(self.options)
        return data


def _text(request: RouteRequest) -> str:
    parts = [request.objective]
    for key, value in request.constraints.items():
        if key == "ir":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts).lower().replace("\u2019", "'")


def _forced_class(request: RouteRequest) -> ArtifactClass | None:
    """The kind the request names. A name Proofhouse does not know yet is still that kind: it is learned, not swapped."""
    forced = request.constraints.get("artifact_class")
    if not isinstance(forced, str):
        return None
    forced = LEGACY_NAMES.get(forced, forced)
    if forced in _ALLOWED:
        return forced
    from ...learn import kind_name

    named = kind_name(forced)
    return LEGACY_NAMES.get(named, named) if named is not None else None


def _new_kind_reason(kind: str) -> str:
    from ... import addons

    try:
        entry = addons.make_kinds().get(kind)
    except Exception:  # noqa: BLE001 -- a broken add-on never stops a pick
        entry = None
    if entry is not None:
        return f"constraint artifact_class={kind} (a kind from add-on {entry['addon']})"
    return (f"constraint artifact_class={kind}: a kind Proofhouse has not made before; your model researches and "
            f"learns it the first time it is made (proofhouse make --kind {kind})")


def _object_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Spans that name the thing to make: after a creation verb, or the opening noun."""
    bounds = [match.start() for match in _BOUNDARY.finditer(text)]
    spans: list[tuple[int, int]] = []
    for match in _MAKE.finditer(text):
        end = _cut(text, bounds, match.end())
        spans.append((match.end(), end))
    opening = re.match(r"^(?:please\s+)?(?:a|an|the)\s+", text)
    if opening:
        spans.append((0, _cut(text, bounds, opening.end())))
    return tuple(sorted(spans))


def _cut(text: str, bounds: list[int], start: int) -> int:
    index = bisect_left(bounds, start)
    return bounds[index] if index < len(bounds) else min(len(text), start + 80)


def _inside(spans: tuple[tuple[int, int], ...], index: int) -> bool:
    # Span ends never fall as starts rise, so only the last span starting at or before index can hold it.
    position = bisect_right(spans, index, key=lambda span: span[0])
    return position > 0 and spans[position - 1][1] > index


def _blocked(kind: str, role: str, text: str, match: re.Match[str], spans: tuple[tuple[int, int], ...]) -> bool:
    """A hit that names what the thing reads, or a caller, is not the thing to make."""
    if _INSTRUMENT.match(text, match.end()):
        return True
    if kind == "API" and _SECRET_AFTER.match(text, match.end()):
        return True
    if kind == "app" and _CALLER_AFTER.match(text, match.end()):
        return True
    if role == "product" and spans and not _inside(spans, match.start()) and _PREP.search(text[max(0, match.start() - 40):match.start()]):
        return True
    return False


def _group_points(
    patterns: tuple[re.Pattern[str], ...], text: str, kind: str, role: str, weight: int,
    spans: tuple[tuple[int, int], ...],
) -> int:
    best = 0
    for pattern in patterns:
        for match in pattern.finditer(text):
            if _blocked(kind, role, text, match, spans):
                continue
            bonus = _OBJECT_BONUS if role == "product" and weight >= _CLEAR_PRODUCT and _inside(spans, match.start()) else 0
            best = max(best, weight + bonus)
    return best


def _stem(word: str) -> str:
    for suffix in ("ing", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _add_structure(text: str, scores: dict[str, int], product: dict[str, int]) -> None:
    """Signals that are a count or a combination, not a single phrase."""
    verbs = {_stem(word) for word in _ACTION.findall(text)}
    if len(verbs) >= 3:
        scores["workflow"] += 5
    thens = len(re.findall(r"\bthen\b", text))
    if thens >= 2:
        scores["workflow"] += 6
    elif thens == 1:
        scores["workflow"] += 2
    if re.search(r"\b\d+ (?:languages|locales)\b", text) or sum(
        1 for name in _LANGUAGES if re.search(rf"\b{name}\b", text)
    ) >= 2:
        scores["workflow"] += 4
    # People asking a body of knowledge: an app, a site, a prompt, or a tool server.
    if re.search(r"\b(?:people|users|customers|staff|employees|students) can ask\b", text):
        scores["app"] += 4
        product["app"] += 4
    if re.search(r"\bask questions\b", text):
        scores["prompt"] += 2
    docs = re.search(r"\b(?:docs|documentation|handbook|wiki|knowledge base)\b", text)
    if docs and re.search(r"\b(?:people|users|visit|browse|ask|search|questions)\b", text):
        scores["site"] += 2
        product["site"] += 2
        scores["mcp"] += 2
    if re.search(r"\blet (?:my |our |the )?(?:an? )?agents? \w+", text) and not re.search(
        r"\bread and (?:update|write|edit|delete|create)\b", text
    ):
        scores["tool"] += 6
        product["tool"] += 6
    if not _JUDGMENT.search(text):
        if re.search(r"\bcommand-line\b|\b(?:python|bash|shell) script\b", text) or (
            re.search(r"\bscript\b", text) and re.search(r"\b(?:split|rename|convert|parse|sort|resize|compress)\b", text)
        ):
            scores["plain_code"] += 5
        if re.search(r"\bconvert\b.{0,40}\binto\b", text):
            scores["plain_code"] += 5
        if re.search(r"\brenam\w+\b(?:\s+\w+){0,6}\b(?:files|photos|images|pictures|downloads|documents)\b", text):
            scores["plain_code"] += 4
        if re.search(r"\b(?:scraper|crawler|spider)\b", text):
            scores["plain_code"] += 2
    # Several different pieces from one goal: a site and a video and the words, together.
    parts = [kind for kind in ("site", "video", "copy") if product[kind] >= _CLEAR_PRODUCT]
    if len(parts) >= 2:
        scores["launch"] = max(scores[kind] for kind in parts) + 4


def _score_kinds(text: str) -> tuple[dict[str, int], dict[str, int]]:
    spans = _object_spans(text)
    scores = {kind: 0 for kind in MAKE_KINDS + OTHER_CLASSES}
    product = {kind: 0 for kind in scores}
    for kind, weight, role, patterns in _GROUPS:
        points = _group_points(patterns, text, kind, role, weight, spans)
        scores[kind] += points
        if role == "product":
            product[kind] += points
    _add_structure(text, scores, product)
    return scores, product


def _ranked(scores: dict[str, int]) -> list[str]:
    order = {kind: index for index, kind in enumerate(_SAFER)}
    return sorted((kind for kind, score in scores.items() if score > 0), key=lambda kind: (-scores[kind], order[kind]))


def _vague(text: str, product: dict[str, int]) -> bool:
    if any(score >= _CLEAR_PRODUCT for score in product.values()):
        return False
    if _VAGUE.search(text):
        return len(text.split()) <= 12 or text.lstrip().startswith("automate") or "help me" in text or "something" in text
    return False


def _question(kinds: tuple[str, ...]) -> str:
    """One template for every close call, filled with the plain description of each kind."""
    words = [_PLAIN[kind] for kind in kinds]
    if len(words) == 2:
        text = f"Should this be {words[0]}, or {words[1]}?"
    else:
        text = "Should this be " + ", ".join(words[:-1]) + f", or {words[-1]}?"
    if len(text) <= 160:
        return text
    short = text[:159].rsplit(" ", 1)[0].rstrip(" ,;")
    return short + "?"


def _decide(kind: str, options: tuple[str, ...] = ()) -> RouteDecision:
    question = _question(options) if len(options) >= 2 else None
    return RouteDecision(kind, _WHY[kind], kind == "site", question, options if question else ())


def _choose(text: str) -> RouteDecision:
    scores, product = _score_kinds(text)
    ranked = _ranked(scores)
    vague = _vague(text, product)
    if not ranked:
        if vague:
            return _decide("prompt", ("prompt", "one_prompt"))
        return _decide("prompt")
    leader = ranked[0]
    close = tuple(kind for kind in ranked if scores[leader] - scores[kind] <= _CLOSE)[:4]
    if vague and len(ranked) >= 2:
        return _decide(ranked[0], tuple(ranked[:4]))
    if vague and scores[leader] < _CLEAR_PRODUCT:
        extra = "one_prompt" if leader == "prompt" else "prompt"
        return _decide(leader, (leader, extra))
    if len(close) >= 2:
        return _decide(close[0], close)
    return _decide(leader)


def route(request: RouteRequest) -> RouteDecision:
    """Pure discriminator. Does not read or write IR."""
    text = _text(request)
    forced = _forced_class(request)
    if forced == "nothing_new" or (forced is None and "nothing new" in text):
        return RouteDecision("nothing_new", "consumption governor: no new artifact", False)
    if forced == "one_prompt" or (forced is None and "one prompt" in text):
        return RouteDecision("one_prompt", "consumption governor: a single prompt suffices", False)
    if forced == "site":
        return RouteDecision("site", "dispatch to ship-walk as website-build module", True)
    if forced == "video":
        return RouteDecision("video", "non-reproducible lane; outside sealed deterministic core", False)
    if forced in {"hook", "loop"}:
        return RouteDecision(forced, "runs without an operator present", False)
    if forced is not None and forced not in _ALLOWED:
        return RouteDecision(forced, _new_kind_reason(forced), False)
    if forced is not None:
        return RouteDecision(forced, f"constraint artifact_class={forced}", False)
    named = request.constraints.get("artifact_class")
    if isinstance(named, str) and named.strip():
        chosen = _choose(text)
        return replace(chosen, rationale=f"artifact_class={named!r} is not a kind name; {chosen.rationale}")
    return _choose(text)
