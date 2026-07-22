"""RFC 8785-style canonical JSON (JCS) and SHA-256 hashing.

Binding per OAR-001-04: UTF-8, RFC 8785-style JSON Canonicalization Scheme,
SHA-256, duplicate-key rejection, no implicit Unicode normalization, and
rejection of invalid Unicode / lone surrogates. Canonicalization failures
are diagnostics, never silent repairs (Compiler Invariant #6, #9).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import rfc8785


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
    """Serialize an already-parsed JSON value to RFC 8785 canonical bytes.

    The value must already be free of duplicate keys and lone surrogates
    (see parse_strict_json). No implicit Unicode normalization is performed
    on string content; strings are emitted exactly as given.
    """
    _walk_reject_surrogates(value)
    try:
        # RFC 8785 delegates binary64 number rendering to ECMAScript.  Keep
        # this boundary on the maintained, dependency-pinned implementation
        # rather than attempting to emulate Number::toString with Python repr.
        return rfc8785.dumps(value)
    except rfc8785.CanonicalizationError as exc:
        raise CanonicalizationError(str(exc)) from exc


def canonical_sha256(value: Any) -> str:
    """SHA-256 over the RFC 8785-style canonical bytes of value, as lowercase hex."""
    return hashlib.sha256(canonicalize(value)).hexdigest()
