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
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
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
