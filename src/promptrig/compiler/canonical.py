"""RFC 8785-style canonical JSON (JCS) and SHA-256 hashing.

Binding per OAR-001-04: UTF-8, RFC 8785-style JSON Canonicalization Scheme,
SHA-256, duplicate-key rejection, no implicit Unicode normalization, and
rejection of invalid Unicode / lone surrogates. Canonicalization failures
are diagnostics, never silent repairs (Compiler Invariant #6, #9).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when input cannot be parsed or serialized under this profile."""

    def __init__(self, reason: str, json_pointer: str = ""):
        self.reason = reason
        self.json_pointer = json_pointer
        super().__init__(f"{reason} at {json_pointer or '<root>'}")


def _has_lone_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CanonicalizationError(f"duplicate key {key!r} rejected before canonicalization")
        seen[key] = value
    return seen


def _walk_reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        if _has_lone_surrogate(value):
            raise CanonicalizationError("string contains an invalid lone surrogate code point")
    elif isinstance(value, dict):
        for k, v in value.items():
            if _has_lone_surrogate(k):
                raise CanonicalizationError("object key contains an invalid lone surrogate code point")
            _walk_reject_surrogates(v)
    elif isinstance(value, list):
        for item in value:
            _walk_reject_surrogates(item)


def parse_strict_json(raw: bytes | str) -> Any:
    """Parse JSON with duplicate-key and lone-surrogate rejection.

    Structural rejection happens during parsing, before any canonicalization
    is attempted, per the PromptRig canonical-JSON profile.
    """
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise CanonicalizationError(f"input is not valid UTF-8: {exc}") from exc
    else:
        text = raw

    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except CanonicalizationError:
        raise
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(f"input is not valid JSON: {exc}") from exc

    _walk_reject_surrogates(value)
    return value


def canonicalize(value: Any) -> bytes:
    """Serialize an already-parsed JSON value to RFC 8785-style canonical bytes.

    The value must already be free of duplicate keys and lone surrogates
    (see parse_strict_json). No implicit Unicode normalization is performed
    on string content; strings are emitted exactly as given.
    """
    return _encode(value).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """SHA-256 over the RFC 8785-style canonical bytes of value, as lowercase hex."""
    return hashlib.sha256(canonicalize(value)).hexdigest()


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        if _has_lone_surrogate(value):
            raise CanonicalizationError("string contains an invalid lone surrogate code point")
        return _encode_string(value)
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise CanonicalizationError("integer is outside the I-JSON binary64 safe-integer domain")
        return str(value)
    if isinstance(value, float):
        return _encode_number(value)
    if isinstance(value, dict):
        for k in value:
            if _has_lone_surrogate(k):
                raise CanonicalizationError("object key contains an invalid lone surrogate code point")
        items = sorted(value.items(), key=lambda kv: kv[0].encode("utf-16-be", "surrogatepass"))
        body = ",".join(f"{_encode_string(k)}:{_encode(v)}" for k, v in items)
        return "{" + body + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    raise CanonicalizationError(f"unsupported value type for canonical JSON: {type(value).__name__}")


def _encode_string(s: str) -> str:
    # json.dumps(ensure_ascii=False) escapes the mandatory control/quote/backslash
    # characters and leaves all other Unicode as literal UTF-8, matching the
    # RFC 8785 string-escaping requirements for this profile.
    return json.dumps(s, ensure_ascii=False)


def _encode_number(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        raise CanonicalizationError("NaN and Infinity are not representable in canonical JSON")
    if value == 0.0:
        # ECMAScript Number::toString(-0) is "0"; JCS follows ECMAScript ToString.
        return "0"
    if value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    rendered = repr(value).lower()
    magnitude = abs(value)
    if 1e-6 <= magnitude < 1e21:
        if "e" in rendered:
            coefficient, exponent = rendered.split("e", 1)
            exponent_value = int(exponent)
            digits = coefficient.lstrip("-").replace(".", "")
            decimal_index = 1 + exponent_value
            if decimal_index <= 0:
                fixed = "0." + "0" * (-decimal_index) + digits
            elif decimal_index >= len(digits):
                fixed = digits + "0" * (decimal_index - len(digits))
            else:
                fixed = digits[:decimal_index] + "." + digits[decimal_index:]
            return ("-" if value < 0 else "") + fixed
        return rendered
    if "e" not in rendered:
        return rendered
    coefficient, exponent = rendered.split("e", 1)
    return f"{coefficient}e{'+' if int(exponent) >= 0 else '-'}{abs(int(exponent))}"
