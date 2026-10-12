"""The spend gate: the one place a request that can cost money is checked before it is sent.

Before anything is sent, the spine works out the most the request could cost
and refuses when that worst case is over the caller's ceiling, or when no worst
case can be made (fail closed). Parts never make this decision.

- **Price table**: data shipped in the package (``data/price_table.json``), with
  a version. Each entry names the provider, the exact model id, the input and
  output price in US dollars per million tokens, the official page the price
  was read from, and the date it was read. A model with no entry has no price,
  and a request to it is refused. Nothing outside the package can replace the
  table, and no setting or environment variable switches the check off.
- **Estimate**: input tokens are bounded by the UTF-8 bytes of the request body
  exactly as sent, plus a fixed margin (``COUNTING_RULE``); output tokens by the
  output-token ceiling the call already requires. Money is exact ``Decimal``:
  an amount that would need rounding is refused, never rounded.
- **Gate**: ``send_within_ceiling`` is the only way a sender is called. It makes
  the request bytes, works out the worst case from them, and calls ``send``
  with exactly those bytes only when the worst case is at or under the ceiling.
  A refusal carries a ``PHC-COST-*`` code and a one-line message, and sends nothing.
- **After a call**: token counts the provider reports are measured; the dollar
  figure worked out from them at table prices is estimated, never measured (the
  table can be stale, and Proofhouse never sees the bill). A figure nobody knows
  is ``unknown``, never ``0``. Reported tokens above the gate's bound are
  reported (``PHC-COST-0004``), never hidden.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, DecimalException, Inexact, InvalidOperation, Overflow, Rounded, localcontext
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .compiler.canonical import CanonicalizationError, parse_strict_json

PRICE_TABLE_SCHEMA = "proofhouse.price_table/v1"
PRICE_TABLE_PATH = Path(__file__).resolve().parent / "data" / "price_table.json"

_TABLE_KEYS = frozenset({"schema", "price_table_version", "currency", "entries"})
_ENTRY_KEYS = (
    "provider",
    "model",
    "input_usd_per_million_tokens",
    "output_usd_per_million_tokens",
    "applies_up_to_input_tokens",
    "service_tier",
    "source_url",
    "read_on",
)
# Plain decimal only: no sign, exponent, NaN, Infinity, spaces or separators.
_PRICE = re.compile(r"[0-9]+(\.[0-9]+)?")
_VERSION = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})\.([1-9][0-9]*)")
# Prices hold for the provider's standard processing; other tiers are priced differently.
_SERVICE_TIERS = frozenset({"default"})

# A margin for the markers and rewritten tool text the provider adds around a request; it does not
# publish that format. Chosen here, not a figure the provider gives.
INPUT_TOKEN_MARGIN = 1024
COUNTING_RULE = (
    "input tokens <= UTF-8 bytes of the request body as sent + 1024, assuming at most one token per byte; "
    "output tokens <= the request's output cap, assuming it caps every billed output token, reasoning included"
)
# The request fields the estimate covers, per provider. Any other field (more choices, another
# processing tier, ...) could change what is billed, so a request carrying one is refused.
_REQUEST_FIELDS = {
    "openai": frozenset({"model", "messages", "max_completion_tokens", "tools", "response_format"}),
    "openai-compatible": frozenset({"model", "messages", "max_tokens", "tools", "response_format"}),
}
_OUTPUT_CAP_FIELD = {"openai": "max_completion_tokens", "openai-compatible": "max_tokens"}
SOURCE_TABLE = "price table"
SOURCE_DECLARED = "declared by you"
SOURCE_LOCAL = "on this machine: no charge"
# Inside the request, only text the byte count covers: plain-string messages, function tools, and
# text output formats. Images, audio and other parts are billed far above their bytes, so they are refused.
_MESSAGE_ROLES = frozenset({"system", "developer", "user", "assistant"})
_OUTPUT_FORMATS = frozenset({"text", "json_object", "json_schema"})
# A ceiling from 0.000000000001 up to (not including) 10000000000000 dollars; anything else is refused.
_CEILING_EXPONENTS = range(-12, 13)
ENFORCEMENT = "refused_pre_send_when_worst_case_over_ceiling"
_TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)
# Enough digits for any real request; anything that needs more is refused, not rounded.
_MONEY_PRECISION = 60


class SpendRefused(Exception):
    """Nothing was sent. Carries a registered ``PHC-COST-*`` code and a one-line reason."""

    def __init__(self, code: str, detail: str) -> None:
        from .optimize.case_codes import CODES

        if code not in CODES:
            raise ValueError(f"unregistered diagnostic code: {code}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class PriceTableError(ValueError):
    """The price table is missing or broken; no price in it can be trusted."""


@dataclass(frozen=True, slots=True)
class PriceEntry:
    provider: str
    model: str
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal
    applies_up_to_input_tokens: int | None
    service_tier: str
    source_url: str
    read_on: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_usd_per_million_tokens": str(self.input_usd_per_million_tokens),
            "output_usd_per_million_tokens": str(self.output_usd_per_million_tokens),
            "applies_up_to_input_tokens": self.applies_up_to_input_tokens,
            "service_tier": self.service_tier,
            "source_url": self.source_url,
            "read_on": self.read_on,
        }


@dataclass(frozen=True, slots=True)
class PriceTable:
    version: str
    entries: tuple[PriceEntry, ...]

    def find(self, provider: str, model: str) -> PriceEntry | None:
        """The entry for exactly this provider and model id; no alias, prefix or case folding."""
        return next((e for e in self.entries if e.provider == provider and e.model == model), None)


def _iso_date(value: object, what: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise PriceTableError(f"{what} must be a YYYY-MM-DD date")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise PriceTableError(f"{what} {value!r} is not a real date") from None
    return value


def _price(value: object, what: str) -> Decimal:
    if not isinstance(value, str) or not _PRICE.fullmatch(value):
        raise PriceTableError(f"{what} must be a plain decimal string such as \"1.25\"")
    amount = Decimal(value)
    if amount <= 0:
        raise PriceTableError(f"{what} must be above zero")
    return amount


def _name(value: object, what: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PriceTableError(f"{what} must be a non-empty string without surrounding spaces")
    return value


def _entry(raw: object, index: int) -> PriceEntry:
    where = f"entry {index}"
    if not isinstance(raw, dict) or set(raw) != set(_ENTRY_KEYS):
        raise PriceTableError(f"{where} must have exactly {', '.join(_ENTRY_KEYS)}")
    limit = raw["applies_up_to_input_tokens"]
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise PriceTableError(f"{where} applies_up_to_input_tokens must be a positive integer or null")
    if raw["service_tier"] not in _SERVICE_TIERS:
        raise PriceTableError(f"{where} service_tier must be one of {', '.join(sorted(_SERVICE_TIERS))}")
    source = raw["source_url"]
    parsed = urlparse(source) if isinstance(source, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.hostname or any(c.isspace() for c in source):
        raise PriceTableError(f"{where} source_url must be an https address")
    return PriceEntry(
        provider=_name(raw["provider"], f"{where} provider"),
        model=_name(raw["model"], f"{where} model"),
        input_usd_per_million_tokens=_price(raw["input_usd_per_million_tokens"], f"{where} input price"),
        output_usd_per_million_tokens=_price(raw["output_usd_per_million_tokens"], f"{where} output price"),
        applies_up_to_input_tokens=limit,
        service_tier=raw["service_tier"],
        source_url=source,
        read_on=_iso_date(raw["read_on"], f"{where} read_on"),
    )


def parse_price_table(raw: bytes | str) -> PriceTable:
    """Parse and check a whole table. Any broken part refuses all of it (fail closed)."""
    try:
        data = parse_strict_json(raw)
    except CanonicalizationError as exc:
        raise PriceTableError(f"price table is unreadable: {exc}") from None
    if not isinstance(data, dict) or set(data) != _TABLE_KEYS:
        raise PriceTableError(f"price table must have exactly {', '.join(sorted(_TABLE_KEYS))}")
    if data["schema"] != PRICE_TABLE_SCHEMA:
        raise PriceTableError(f"price table schema must be {PRICE_TABLE_SCHEMA}")
    if data["currency"] != "USD":
        raise PriceTableError("price table currency must be USD")
    version = data["price_table_version"]
    match = _VERSION.fullmatch(version) if isinstance(version, str) else None
    if match is None:
        raise PriceTableError("price_table_version must look like YYYY-MM-DD.N")
    _iso_date(match.group(1), "price_table_version date")
    if not isinstance(data["entries"], list):
        raise PriceTableError("price table entries must be a list")
    entries = tuple(_entry(raw_entry, i) for i, raw_entry in enumerate(data["entries"], start=1))
    keys = [(e.provider, e.model) for e in entries]
    if len(set(keys)) != len(keys):
        raise PriceTableError("price table lists a provider and model more than once")
    return PriceTable(version=version, entries=entries)


def load_price_table() -> PriceTable:
    """The table shipped in the package. There is deliberately no other place to read prices from."""
    try:
        raw = PRICE_TABLE_PATH.read_bytes()
    except OSError as exc:
        raise PriceTableError(f"price table cannot be read: {type(exc).__name__}") from None
    return parse_price_table(raw)


def request_body_bytes(body: Mapping[str, Any]) -> bytes:
    """The exact bytes that will be sent. The estimate counts these, and only these are sent."""
    try:
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:  # UnicodeEncodeError is a ValueError
        raise SpendRefused("PHC-COST-0003", f"the request body cannot be sent as exact bytes ({type(exc).__name__})") from None


def input_tokens_bound(body: bytes) -> int:
    """Worst-case input tokens for these bytes (``COUNTING_RULE``)."""
    return len(body) + INPUT_TOKEN_MARGIN


def _count(value: object, what: str) -> int:
    if type(value) is not int or value < 0:
        raise SpendRefused("PHC-COST-0003", f"{what} must be a non-negative whole number")
    return value


def worst_case_usd(entry: PriceEntry, input_tokens: int, output_tokens: int) -> Decimal:
    """Input bound x input price + output bound x output price, per million tokens, exactly."""
    tokens_in = _count(input_tokens, "input tokens")
    tokens_out = _count(output_tokens, "output tokens")
    with localcontext() as ctx:
        ctx.prec = _MONEY_PRECISION
        for signal in (Inexact, Rounded, Overflow, InvalidOperation):
            ctx.traps[signal] = True
        try:
            return (
                Decimal(tokens_in) * entry.input_usd_per_million_tokens
                + Decimal(tokens_out) * entry.output_usd_per_million_tokens
            ) / _TOKENS_PER_PRICE_UNIT
        except DecimalException:
            raise SpendRefused("PHC-COST-0003", "the worst-case amount cannot be worked out exactly") from None


def _price_note(source: str, version: str, entry: PriceEntry) -> str:
    if source == SOURCE_TABLE:
        return f"prices {version}, read {entry.read_on}"
    if source == SOURCE_DECLARED:
        return f"price declared by you{' on ' + entry.read_on if entry.read_on else ''}"
    return source


def _usd_text(amount: Decimal) -> str:
    return format(amount, "f")


def _ceiling(value: object) -> Decimal:
    try:
        amount = Decimal(value.strip()) if isinstance(value, str) else None
    except DecimalException:
        amount = None
    if amount is None or not amount.is_finite() or amount <= 0 or amount.adjusted() not in _CEILING_EXPONENTS:
        raise SpendRefused("PHC-COST-0003", "the ceiling must be a decimal from 0.000000000001 to under 10000000000000")
    return amount


def _provider(provider: str) -> Any:
    """The provider's profile (shipped or yours); its shape says what the request may hold."""
    from . import providers

    try:
        profile = providers.find(provider)
    except providers.ProviderError as exc:
        raise SpendRefused("PHC-COST-0003", f"providers file: {exc}") from None
    if profile is None:
        raise SpendRefused("PHC-COST-0003", f"no request shape is known for provider {provider!r}")
    return profile


def _declared_price(profile: Any, model: str) -> PriceEntry | None:
    """A price you declared in your providers file. Zero is allowed only for a provider on this machine."""
    from . import providers

    for raw in providers.load_user()["prices"]:
        if not isinstance(raw, dict) or raw.get("provider") != profile.id or raw.get("model") != model:
            continue
        amounts = []
        for key in ("input_usd_per_million_tokens", "output_usd_per_million_tokens"):
            value = raw.get(key)
            if not isinstance(value, str) or not _PRICE.fullmatch(value):
                raise SpendRefused("PHC-COST-0003", f"your declared price for {model!r} has a bad {key}")
            amount = Decimal(value)
            if amount <= 0 and not (amount == 0 and profile.local):
                raise SpendRefused("PHC-COST-0003", f"your declared price for {model!r} must be above zero")
            amounts.append(amount)
        return PriceEntry(profile.id, model, amounts[0], amounts[1], None, "default", "", str(raw.get("declared_on", "")))
    return None


def _price_for(table: PriceTable, profile: Any, model: str) -> tuple[PriceEntry, str] | None:
    """The shipped table first (yours cannot change it), then your declared price, then $0 on this machine."""
    entry = table.find(profile.id, model)
    if entry is not None:
        return entry, SOURCE_TABLE
    try:
        declared = _declared_price(profile, model)
    except ValueError as exc:  # a broken providers file
        raise SpendRefused("PHC-COST-0003", f"providers file: {exc}") from None
    if declared is not None:
        return declared, SOURCE_DECLARED
    if profile.local:
        return PriceEntry(profile.id, model, Decimal(0), Decimal(0), None, "default", "", ""), SOURCE_LOCAL
    return None


def _check_request(body: Mapping[str, Any], *, shape: str, model: str, output_bound: int) -> None:
    """The model and output cap are read from the bytes being counted; the caller's word is not taken."""
    fields = _REQUEST_FIELDS.get(shape)
    if fields is None:
        raise SpendRefused("PHC-COST-0003", f"no request shape {shape!r} is known")
    extra = sorted(str(key) for key in body if key not in fields)
    if extra:
        raise SpendRefused("PHC-COST-0003", f"the request has fields the estimate does not cover: {', '.join(extra)}")
    if body.get("model") != model:
        raise SpendRefused("PHC-COST-0003", "the request names a different model from the one priced")
    cap = body.get(_OUTPUT_CAP_FIELD[shape])
    if type(cap) is not int or cap != output_bound:
        raise SpendRefused("PHC-COST-0003", f"the request's output cap is not the output bound {output_bound}")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise SpendRefused("PHC-COST-0003", "the request's messages must be a non-empty list")
    for message in messages:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] not in _MESSAGE_ROLES
            or not isinstance(message["content"], str)
        ):
            raise SpendRefused("PHC-COST-0003", "a message is not plain text the estimate covers")
    tools = body.get("tools", [])
    if not isinstance(tools, list) or any(not isinstance(tool, dict) or tool.get("type") != "function" for tool in tools):
        raise SpendRefused("PHC-COST-0003", "a tool is not a function definition the estimate covers")
    if "response_format" in body:
        output_format = body["response_format"]
        if not isinstance(output_format, dict) or output_format.get("type") not in _OUTPUT_FORMATS:
            raise SpendRefused("PHC-COST-0003", "the output format is not one the estimate covers")


@dataclass(frozen=True, slots=True)
class Admission:
    """What the gate decided before sending, and everything it knew when it decided."""

    decision: str  # "admitted" or "refused"
    code: str | None = None
    message: str | None = None
    ceiling_usd: str | None = None
    worst_case_usd: str | None = None
    input_tokens_bound: int | None = None
    output_tokens_bound: int | None = None
    body_sha256: str | None = None
    price: dict[str, Any] | None = None
    price_table_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enforcement": ENFORCEMENT,
            "decision": self.decision,
            "code": self.code,
            "message": self.message,
            "ceiling_usd": self.ceiling_usd,
            "worst_case_usd": self.worst_case_usd,
            "input_tokens_bound": self.input_tokens_bound,
            "counting_rule": COUNTING_RULE,
            "output_tokens_bound": self.output_tokens_bound,
            "body_sha256": self.body_sha256,
            "price": None if self.price is None else dict(self.price),
            "price_table_version": self.price_table_version,
        }


@dataclass(frozen=True, slots=True)
class Gated:
    """The gate's answer. ``response`` is what ``send`` returned, or ``None`` when nothing was sent."""

    admission: Admission
    response: Any = None
    entry: PriceEntry | None = None
    wall_nanoseconds: int | None = None


def send_within_ceiling(
    body: Mapping[str, Any],
    *,
    provider: str,
    model: str,
    max_output_tokens: int,
    ceiling_usd: str,
    send: Callable[[bytes], Any],
) -> Gated:
    """Call ``send`` once, with the exact bytes counted, only if the worst case is at or under the ceiling.

    Refuses (and never calls ``send``) when the worst case is over the ceiling,
    when the model has no price, or when no worst case can be made.
    """
    facts: dict[str, Any] = {}
    try:
        ceiling = _ceiling(ceiling_usd)
        facts["ceiling_usd"] = _usd_text(ceiling)
        sent = request_body_bytes(body)
        facts["body_sha256"] = hashlib.sha256(sent).hexdigest()
        facts["input_tokens_bound"] = bound = input_tokens_bound(sent)
        facts["output_tokens_bound"] = output_bound = _count(max_output_tokens, "the output-token ceiling")
        profile = _provider(provider)
        _check_request(body, shape=profile.shape, model=model, output_bound=output_bound)
        try:
            table = load_price_table()
        except PriceTableError as exc:
            reason = str(exc) if str(exc).startswith("price table") else f"price table {exc}"
            raise SpendRefused("PHC-COST-0003", reason) from None
        facts["price_table_version"] = table.version
        found = _price_for(table, profile, model)
        if found is None:
            raise SpendRefused(
                "PHC-COST-0002",
                f"no price for {model!r} from {provider} in price table {table.version} or your declared prices; "
                "nothing was sent",
            )
        entry, source = found
        facts["price"] = {**entry.to_dict(), "source": source}
        limit = entry.applies_up_to_input_tokens
        if limit is not None and bound > limit:
            raise SpendRefused("PHC-COST-0003", f"the input bound {bound} is above the {limit} input tokens its price applies to")
        worst = worst_case_usd(entry, bound, output_bound)
        facts["worst_case_usd"] = _usd_text(worst)
        if worst > ceiling:
            raise SpendRefused(
                "PHC-COST-0001",
                f"worst case ${facts['worst_case_usd']} is over the ceiling ${facts['ceiling_usd']} for {model!r} "
                f"({_price_note(source, table.version, entry)}); nothing was sent",
            )
    except SpendRefused as refusal:
        detail = refusal.detail
        if refusal.code == "PHC-COST-0003":
            detail = f"no worst-case cost could be made ({detail}); nothing was sent"
        return Gated(Admission(decision="refused", code=refusal.code, message=f"{refusal.code}: {detail}", **facts))
    started = time.perf_counter_ns()
    response = send(sent)
    return Gated(Admission(decision="admitted", **facts), response, entry, time.perf_counter_ns() - started)


UNKNOWN = "unknown"
COST_FIELDS = ("tokens_in", "tokens_out", "usd", "wall_seconds", "compute_seconds")
_NANOSECONDS_PER_SECOND = Decimal(1_000_000_000)


def _reported(usage: object, key: str) -> int | str:
    value = usage.get(key) if isinstance(usage, dict) else None
    return value if type(value) is int and value >= 0 else UNKNOWN


def cost_after(gated: Gated, payload: object) -> tuple[dict[str, Any], str | None]:
    """What a sent call cost, and a one-line ``PHC-COST-0004`` warning when the gate's bound did not hold.

    ``basis`` is one label per figure: provider-reported tokens and the local
    wall clock are ``measured``; ``usd`` is ``estimated``; anything else is ``unknown``.
    """
    usage = payload.get("usage") if isinstance(payload, dict) else None
    tokens_in = _reported(usage, "prompt_tokens")
    tokens_out = _reported(usage, "completion_tokens")
    usd: str = UNKNOWN
    if gated.entry is not None and isinstance(tokens_in, int) and isinstance(tokens_out, int):
        try:
            usd = _usd_text(worst_case_usd(gated.entry, tokens_in, tokens_out))
        except SpendRefused:
            usd = UNKNOWN
    wall: str = UNKNOWN
    if gated.wall_nanoseconds is not None:
        wall = _usd_text(Decimal(gated.wall_nanoseconds) / _NANOSECONDS_PER_SECOND)
    figures: dict[str, Any] = {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd": usd,
        "wall_seconds": wall,
        "compute_seconds": UNKNOWN,
    }
    labels = {"tokens_in": "measured", "tokens_out": "measured", "usd": "estimated", "wall_seconds": "measured"}
    basis = {field: UNKNOWN if figures[field] == UNKNOWN else labels.get(field, UNKNOWN) for field in COST_FIELDS}
    cost = {**figures, "basis": basis, "price_table_version": "" if usd == UNKNOWN else str(gated.admission.price_table_version)}

    admission = gated.admission
    model = (admission.price or {}).get("model", "")
    warning = None
    for kind, used, bound in (
        ("input", tokens_in, admission.input_tokens_bound),
        ("output", tokens_out, admission.output_tokens_bound),
    ):
        if isinstance(used, int) and isinstance(bound, int) and used > bound:
            warning = (
                f"PHC-COST-0004: {model!r} used {used} {kind} tokens, over the bound of {bound}; "
                "the price check did not hold for this call"
            )
            break
    return cost, warning


def _media_price(profile: Any, model: str) -> tuple[Decimal, str] | None:
    """Your declared price per unit for this media service and model (``*`` matches any model), or $0 on this machine."""
    from . import providers

    try:
        declared = providers.load_user()["media_prices"]
    except ValueError as exc:
        raise SpendRefused("PHC-COST-0003", f"providers file: {exc}") from None
    for wanted in (model, "*"):
        for raw in declared:
            if isinstance(raw, dict) and raw.get("provider") == profile.id and raw.get("model") == wanted:
                value = raw.get("usd_per_unit")
                if not isinstance(value, str) or not _PRICE.fullmatch(value) or (Decimal(value) <= 0 and not profile.local):
                    raise SpendRefused("PHC-COST-0003", f"your declared price for {profile.id} {wanted} must be a decimal above zero")
                return Decimal(value), SOURCE_DECLARED
    if profile.local:
        return Decimal(0), SOURCE_LOCAL
    return None


def send_media_within_ceiling(
    profile: Any, model: str, params: Mapping[str, Any], *, ceiling_usd: str, send: Callable[[str, bytes], Any]
) -> Gated:
    """One paid media request. The gate builds it from the service's template, prices it per unit, and sends it only if
    units x price is at or under the ceiling. The caller never hands over a body or a unit count."""
    from . import media

    facts: dict[str, Any] = {}
    try:
        ceiling = _ceiling(ceiling_usd)
        facts["ceiling_usd"] = _usd_text(ceiling)
        try:
            url, body, units = media.build_request(profile, model, dict(params))
        except (media.MediaError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise SpendRefused("PHC-COST-0003", f"the request cannot be built ({exc})") from None
        sent = request_body_bytes(body)
        facts["body_sha256"] = hashlib.sha256(sent).hexdigest()
        found = _media_price(profile, model)
        if found is None:
            raise SpendRefused(
                "PHC-COST-0002",
                f"no price for {model!r} from {profile.id}; declare one with `proofhouse media price`; nothing was sent",
            )
        per_unit, source = found
        facts["price"] = {"provider": profile.id, "model": model, "unit": profile.unit, "units": str(units),
                          "usd_per_unit": str(per_unit), "source": source}
        with localcontext() as ctx:
            ctx.prec = _MONEY_PRECISION
            for signal in (Inexact, Rounded, Overflow, InvalidOperation):
                ctx.traps[signal] = True
            try:
                worst = units * per_unit
            except DecimalException:
                raise SpendRefused("PHC-COST-0003", "the worst-case amount cannot be worked out exactly") from None
        facts["worst_case_usd"] = _usd_text(worst)
        if worst > ceiling:
            raise SpendRefused(
                "PHC-COST-0001",
                f"worst case ${facts['worst_case_usd']} ({units} {profile.unit} x ${per_unit}) is over the ceiling "
                f"${facts['ceiling_usd']} for {model!r}; nothing was sent",
            )
    except SpendRefused as refusal:
        detail = refusal.detail
        if refusal.code == "PHC-COST-0003":
            detail = f"no worst-case cost could be made ({detail}); nothing was sent"
        return Gated(Admission(decision="refused", code=refusal.code, message=f"{refusal.code}: {detail}", **facts))
    started = time.perf_counter_ns()
    response = send(url, sent)
    return Gated(Admission(decision="admitted", **facts), response, None, time.perf_counter_ns() - started)


def _training_price(profile: Any, model: str) -> tuple[Decimal, str] | None:
    """Your declared price per million training tokens for this service and base model (``*`` matches any), or $0 locally."""
    from . import providers

    try:
        declared = providers.load_user()["training_prices"]
    except ValueError as exc:
        raise SpendRefused("PHC-COST-0003", f"providers file: {exc}") from None
    for wanted in (model, "*"):
        for raw in declared:
            if isinstance(raw, dict) and raw.get("provider") == profile.id and raw.get("model") == wanted:
                value = raw.get("usd_per_million_tokens")
                if not isinstance(value, str) or not _PRICE.fullmatch(value) or (Decimal(value) <= 0 and not profile.local):
                    raise SpendRefused("PHC-COST-0003", f"your declared training price for {profile.id} {wanted} must be a decimal above zero")
                return Decimal(value), SOURCE_DECLARED
    if profile.local:
        return Decimal(0), SOURCE_LOCAL
    return None


def send_training_within_ceiling(
    profile: Any, model: str, params: Mapping[str, Any], *, ceiling_usd: str, send: Callable[[str, bytes], Any]
) -> Gated:
    """One paid training job. The gate builds the job request from the service's template, bounds the tokens it can bill
    (every byte of every data file, times the epochs written into the request), prices that per million training tokens,
    and sends only if it is at or under the ceiling. The caller never hands over a body, a size or a token count."""
    from . import train

    facts: dict[str, Any] = {}
    try:
        ceiling = _ceiling(ceiling_usd)
        facts["ceiling_usd"] = _usd_text(ceiling)
        try:
            url, body, epochs, data_bytes = train.build_job_request(profile, model, dict(params))
        except (train.TrainError, OSError, KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise SpendRefused("PHC-COST-0003", f"the job request cannot be built ({exc})") from None
        sent = request_body_bytes(body)
        facts["body_sha256"] = hashlib.sha256(sent).hexdigest()
        found = _training_price(profile, model)
        if found is None:
            raise SpendRefused(
                "PHC-COST-0002",
                f"no training price for {model!r} on {profile.id}; declare one with `proofhouse train price`; nothing was sent",
            )
        per_million, source = found
        facts["price"] = {"provider": profile.id, "model": model, "unit": "1M training tokens", "usd_per_unit": str(per_million),
                          "source": source, "data_bytes": data_bytes, "epochs": epochs,
                          "bound": "training tokens <= data bytes x epochs"}
        with localcontext() as ctx:
            ctx.prec = _MONEY_PRECISION
            for signal in (Inexact, Rounded, Overflow, InvalidOperation):
                ctx.traps[signal] = True
            try:
                worst = Decimal(data_bytes) * Decimal(epochs) * per_million / Decimal(1_000_000)
            except DecimalException:
                raise SpendRefused("PHC-COST-0003", "the worst-case amount cannot be worked out exactly") from None
        facts["worst_case_usd"] = _usd_text(worst)
        if worst > ceiling:
            raise SpendRefused(
                "PHC-COST-0001",
                f"worst case ${facts['worst_case_usd']} ({data_bytes} bytes x {epochs} epochs at ${per_million} per million "
                f"training tokens) is over the ceiling ${facts['ceiling_usd']} for {model!r}; nothing was sent",
            )
    except SpendRefused as refusal:
        detail = refusal.detail
        if refusal.code == "PHC-COST-0003":
            detail = f"no worst-case cost could be made ({detail}); nothing was sent"
        return Gated(Admission(decision="refused", code=refusal.code, message=f"{refusal.code}: {detail}", **facts))
    started = time.perf_counter_ns()
    response = send(url, sent)
    return Gated(Admission(decision="admitted", **facts), response, None, time.perf_counter_ns() - started)
