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
    "input tokens <= UTF-8 bytes of the request body as sent + 1024; "
    "assumes the provider's tokenizer makes at most one token per byte"
)
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


def _usd_text(amount: Decimal) -> str:
    return format(amount, "f")


def _ceiling(value: object) -> Decimal:
    try:
        amount = Decimal(value.strip()) if isinstance(value, str) else None
    except DecimalException:
        amount = None
    if amount is None or not amount.is_finite() or amount <= 0:
        raise SpendRefused("PHC-COST-0003", "the ceiling is not a positive decimal")
    return amount


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
        try:
            table = load_price_table()
        except PriceTableError as exc:
            reason = str(exc) if str(exc).startswith("price table") else f"price table {exc}"
            raise SpendRefused("PHC-COST-0003", reason) from None
        facts["price_table_version"] = table.version
        entry = table.find(provider, model)
        if entry is None:
            raise SpendRefused("PHC-COST-0002", f"no price for {model!r} in price table {table.version}; nothing was sent")
        facts["price"] = entry.to_dict()
        limit = entry.applies_up_to_input_tokens
        if limit is not None and bound > limit:
            raise SpendRefused("PHC-COST-0003", f"the input bound {bound} is above the {limit} input tokens its price applies to")
        worst = worst_case_usd(entry, bound, output_bound)
        facts["worst_case_usd"] = _usd_text(worst)
        if worst > ceiling:
            raise SpendRefused(
                "PHC-COST-0001",
                f"worst case ${facts['worst_case_usd']} is over the ceiling ${facts['ceiling_usd']} for {model!r} "
                f"(prices {table.version}, read {entry.read_on}); nothing was sent",
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
