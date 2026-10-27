"""unit-desk: MCP stdio server for unit conversion and date deltas."""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, datetime

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "unit-desk", "version": "1.0.0"}

LENGTH_TO_M = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
}

MASS_TO_G = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.349523125,
    "lb": 453.59237,
}

VOLUME_TO_L = {
    "ml": 0.001,
    "l": 1.0,
    "floz": 0.0295735295625,
    "cup": 0.2365882365,
    "gal": 3.785411784,
}

TEMP_UNITS = frozenset({"c", "f", "k"})

KIND_UNITS: dict[str, frozenset[str]] = {
    "length": frozenset(LENGTH_TO_M),
    "mass": frozenset(MASS_TO_G),
    "volume": frozenset(VOLUME_TO_L),
    "temperature": TEMP_UNITS,
}

TOOLS = [
    {
        "name": "convert_units",
        "description": (
            "Convert a numeric value between units within the same kind: "
            "length (mm, cm, m, km, in, ft, yd, mi), mass (g, kg, oz, lb), "
            "temperature (c, f, k), or volume (ml, l, floz, cup, gal). "
            "Cross-kind conversions return an error."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "Numeric amount to convert."},
                "from_unit": {"type": "string", "description": "Source unit symbol (case-insensitive)."},
                "to_unit": {"type": "string", "description": "Target unit symbol (case-insensitive)."},
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    },
    {
        "name": "days_between",
        "description": (
            "Return the signed whole-day count from start to end using ISO calendar dates "
            "(YYYY-MM-DD). Negative when end is earlier than start."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "description": "Start date in YYYY-MM-DD form."},
                "end": {"type": "string", "description": "End date in YYYY-MM-DD form."},
            },
            "required": ["start", "end"],
        },
    },
]

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def rpc_error(req_id: object, code: int, message: str) -> None:
    emit({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def rpc_result(req_id: object, result: object) -> None:
    emit({"jsonrpc": "2.0", "id": req_id, "result": result})


def tool_ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_err(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def round_sig(x: float, sig: int = 6) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    magnitude = math.floor(math.log10(abs(x)))
    decimals = sig - 1 - int(magnitude)
    return round(x, decimals)


def normalize_unit(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip().lower()


def unit_kind(unit: str) -> str | None:
    for kind, units in KIND_UNITS.items():
        if unit in units:
            return kind
    return None


def temp_to_c(value: float, unit: str) -> float:
    if unit == "c":
        return value
    if unit == "f":
        return (value - 32.0) * 5.0 / 9.0
    return value - 273.15


def temp_from_c(celsius: float, unit: str) -> float:
    if unit == "c":
        return celsius
    if unit == "f":
        return celsius * 9.0 / 5.0 + 32.0
    return celsius + 273.15


def require_finite_number(value: object, label: str = "value") -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def convert_units(args: dict) -> dict:
    missing = [key for key in ("value", "from_unit", "to_unit") if key not in args]
    if missing:
        return tool_err(f"Missing required fields: {', '.join(missing)}.")
    value = require_finite_number(args["value"])
    if value is None:
        return tool_err("value must be a finite number.")
    from_u = normalize_unit(args["from_unit"])
    to_u = normalize_unit(args["to_unit"])
    if from_u is None or to_u is None:
        return tool_err("from_unit and to_unit must be non-empty strings.")
    kind_f = unit_kind(from_u)
    kind_t = unit_kind(to_u)
    if kind_f is None:
        return tool_err(f"Unknown unit: {from_u}")
    if kind_t is None:
        return tool_err(f"Unknown unit: {to_u}")
    if kind_f != kind_t:
        return tool_err(f"Cannot convert {kind_f} ({from_u}) to {kind_t} ({to_u}).")
    if kind_f == "temperature":
        result = temp_from_c(temp_to_c(value, from_u), to_u)
    elif kind_f == "length":
        result = value * LENGTH_TO_M[from_u] / LENGTH_TO_M[to_u]
    elif kind_f == "mass":
        result = value * MASS_TO_G[from_u] / MASS_TO_G[to_u]
    else:
        result = value * VOLUME_TO_L[from_u] / VOLUME_TO_L[to_u]
    if not math.isfinite(result):
        return tool_err("Conversion produced a non-finite result.")
    result = round_sig(result)
    if not math.isfinite(result):
        return tool_err("Conversion produced a non-finite result.")
    return tool_ok(
        json.dumps(
            {"value": result, "from_unit": from_u, "to_unit": to_u},
            allow_nan=False,
        )
    )


def parse_iso_day(s: str) -> date | None:
    if not ISO_DATE.match(s):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_between(args: dict) -> dict:
    missing = [key for key in ("start", "end") if key not in args]
    if missing:
        return tool_err(f"Missing required fields: {', '.join(missing)}.")
    start_raw = args["start"]
    end_raw = args["end"]
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        return tool_err("start and end must be ISO date strings (YYYY-MM-DD).")
    start = parse_iso_day(start_raw.strip())
    end = parse_iso_day(end_raw.strip())
    if start is None:
        return tool_err(f"Invalid start date: {start_raw}")
    if end is None:
        return tool_err(f"Invalid end date: {end_raw}")
    delta = (end - start).days
    return tool_ok(
        json.dumps(
            {"days": delta, "start": start.isoformat(), "end": end.isoformat()},
            allow_nan=False,
        )
    )


def handle_call(params: object) -> dict:
    if not isinstance(params, dict):
        return tool_err("tools/call params must be an object.")
    name = params.get("name")
    if not isinstance(name, str):
        return tool_err("Tool name is required.")
    arguments = params.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return tool_err("arguments must be an object.")
    if name == "convert_units":
        return convert_units(arguments)
    if name == "days_between":
        return days_between(arguments)
    return tool_err(f"Unknown tool: {name}")


def dispatch(request: dict) -> None:
    method = request.get("method")
    req_id = request.get("id")
    has_id = "id" in request and request["id"] is not None

    if method == "notifications/initialized":
        return
    if not isinstance(method, str):
        if has_id:
            rpc_error(req_id, -32600, "Invalid Request")
        return

    if method == "initialize":
        if not has_id:
            return
        params = request.get("params")
        if params is not None and not isinstance(params, dict):
            rpc_error(req_id, -32602, "Invalid params")
            return
        rpc_result(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
        return

    if method == "ping":
        if has_id:
            rpc_result(req_id, {})
        return

    if method == "tools/list":
        if not has_id:
            return
        rpc_result(req_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        if not has_id:
            return
        try:
            rpc_result(req_id, handle_call(request.get("params")))
        except Exception as exc:  # noqa: BLE001 — keep server alive
            rpc_result(req_id, tool_err(f"Internal tool error: {exc}"))
        return

    if has_id:
        rpc_error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            rpc_error(None, -32700, "Parse error")
            continue
        if not isinstance(request, dict):
            rpc_error(None, -32600, "Invalid Request")
            continue
        try:
            dispatch(request)
        except Exception:
            req_id = request.get("id") if isinstance(request, dict) else None
            if isinstance(request, dict) and "id" in request and request["id"] is not None:
                rpc_error(request["id"], -32603, "Internal error")


if __name__ == "__main__":
    main()
