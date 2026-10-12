"""T-041-01: the price table is data shipped in the package, with a version, and it fails closed.

A price is a decimal string (never a JSON number, so nothing passes through
float). Any broken entry refuses the whole table. A model matches only by its
exact id: no alias, prefix or case folding (no silent substitution).
"""
from __future__ import annotations

import copy
import json
import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from proofhouse import spend
from proofhouse.compiler.canonical import canonical_sha256

ROOT = Path(__file__).resolve().parents[1]

# Each shipped version is pinned to the digest of its canonical form, so a price
# cannot change without the version changing too.
PINNED_VERSIONS = {
    "2026-10-12.1": "b01ab521537d3bc05a528241831b163b666d7876da190620af561a03970d4642",
}

ENTRY = {
    "provider": "openai",
    "model": "model-a",
    "input_usd_per_million_tokens": "1.25",
    "output_usd_per_million_tokens": "10",
    "applies_up_to_input_tokens": None,
    "service_tier": "default",
    "source_url": "https://example.com/pricing",
    "read_on": "2026-10-12",
}
TABLE = {
    "schema": spend.PRICE_TABLE_SCHEMA,
    "price_table_version": "2026-10-12.1",
    "currency": "USD",
    "entries": [ENTRY],
}


def _table(**changes) -> dict:
    table = copy.deepcopy(TABLE)
    table.update(changes)
    return table


def _entry(**changes) -> dict:
    entry = dict(ENTRY)
    entry.update(changes)
    return _table(entries=[entry])


def test_the_shipped_table_loads_and_its_version_is_pinned_to_its_content() -> None:
    raw = spend.PRICE_TABLE_PATH.read_text(encoding="utf-8")
    table = spend.load_price_table()
    assert table.version in PINNED_VERSIONS, "a new price_table_version must be pinned here"
    assert canonical_sha256(json.loads(raw)) == PINNED_VERSIONS[table.version]


def test_the_shipped_table_has_no_entry_until_a_cited_price_is_supplied() -> None:
    # No price has been supplied and cited yet, so every live model is refused.
    assert spend.load_price_table().entries == ()


def test_the_table_ships_as_package_data() -> None:
    assert spend.PRICE_TABLE_PATH == ROOT / "src" / "proofhouse" / "data" / "price_table.json"
    package_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]["package-data"]
    assert "data/*.json" in package_data["proofhouse"]


def test_a_good_entry_parses_to_decimals() -> None:
    table = spend.parse_price_table(json.dumps(TABLE))
    (entry,) = table.entries
    assert entry.input_usd_per_million_tokens == Decimal("1.25")
    assert entry.output_usd_per_million_tokens == Decimal("10")
    assert type(entry.input_usd_per_million_tokens) is Decimal
    assert entry.to_dict() == ENTRY  # prices go back out as the same decimal strings


def test_lookup_is_by_exact_provider_and_model() -> None:
    table = spend.parse_price_table(json.dumps(_entry(model="gpt-5.6-luna")))
    assert table.find("openai", "gpt-5.6-luna") is not None
    for model in ("gpt-5.6-luna-2026-10-01", "GPT-5.6-LUNA", "gpt-5.6", " gpt-5.6-luna", "gpt-5.6-luna "):
        assert table.find("openai", model) is None, model
    assert table.find("anthropic", "gpt-5.6-luna") is None


BROKEN = [
    ("price as a JSON number", _entry(input_usd_per_million_tokens=1.25)),
    ("price as a JSON integer", _entry(output_usd_per_million_tokens=10)),
    ("zero price", _entry(input_usd_per_million_tokens="0")),
    ("zero price with decimals", _entry(output_usd_per_million_tokens="0.000")),
    ("negative price", _entry(input_usd_per_million_tokens="-1")),
    ("NaN price", _entry(input_usd_per_million_tokens="NaN")),
    ("Infinity price", _entry(output_usd_per_million_tokens="Infinity")),
    ("exponent price", _entry(input_usd_per_million_tokens="1e2")),
    ("comma price", _entry(input_usd_per_million_tokens="1,25")),
    ("blank price", _entry(input_usd_per_million_tokens=" ")),
    ("spaced price", _entry(input_usd_per_million_tokens=" 1.25")),
    ("missing key", _table(entries=[{k: v for k, v in ENTRY.items() if k != "read_on"}])),
    ("unknown key", _entry(cached_input_usd_per_million_tokens="0.1")),
    ("empty model", _entry(model="")),
    ("padded model", _entry(model=" model-a")),
    ("non-string provider", _entry(provider=1)),
    ("plain http source", _entry(source_url="http://example.com/pricing")),
    ("source without host", _entry(source_url="https:///pricing")),
    ("source with space", _entry(source_url="https://example.com/pri cing")),
    ("bad read_on", _entry(read_on="12/10/2026")),
    ("impossible read_on", _entry(read_on="2026-02-30")),
    ("other service tier", _entry(service_tier="priority")),
    ("zero input range", _entry(applies_up_to_input_tokens=0)),
    ("bool input range", _entry(applies_up_to_input_tokens=True)),
    ("float input range", _entry(applies_up_to_input_tokens=1000.0)),
    ("duplicate model", _table(entries=[ENTRY, ENTRY])),
    ("entries not a list", _table(entries={})),
    ("wrong schema", _table(schema="proofhouse.price_table/v2")),
    ("wrong currency", _table(currency="EUR")),
    ("bad version", _table(price_table_version="v1")),
    ("impossible version date", _table(price_table_version="2026-13-01.1")),
    ("unknown top-level key", _table(note="x")),
]


@pytest.mark.parametrize("label,table", BROKEN, ids=[label for label, _ in BROKEN])
def test_any_broken_entry_refuses_the_whole_table(label: str, table: dict) -> None:
    with pytest.raises(spend.PriceTableError):
        spend.parse_price_table(json.dumps(table))


@pytest.mark.parametrize(
    "raw",
    ["", "[]", "null", "{", '{"schema": "a", "schema": "b"}', b"\xff\xfe"],
    ids=["empty", "list", "null", "truncated", "duplicate-key", "not-utf8"],
)
def test_unreadable_tables_are_refused(raw) -> None:
    with pytest.raises(spend.PriceTableError):
        spend.parse_price_table(raw)


def test_a_missing_table_file_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spend, "PRICE_TABLE_PATH", tmp_path / "absent.json")
    with pytest.raises(spend.PriceTableError):
        spend.load_price_table()
