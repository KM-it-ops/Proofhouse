from __future__ import annotations

import pytest

from promptrig.compiler.canonical import (
    CanonicalizationError,
    canonical_sha256,
    canonicalize,
    parse_strict_json,
)


def test_key_ordering_is_utf16_code_unit_order():
    a = canonicalize({"b": 1, "a": 2})
    b = canonicalize({"a": 2, "b": 1})
    assert a == b == b'{"a":2,"b":1}'


def test_nested_key_ordering():
    value = {"z": {"y": 1, "x": 2}, "a": [3, 2, 1]}
    out = canonicalize(value)
    assert out == b'{"a":[3,2,1],"z":{"x":2,"y":1}}'


def test_integer_serialization_has_no_decimal_point():
    assert canonicalize(7) == b"7"
    assert canonicalize(-7) == b"-7"
    assert canonicalize(0) == b"0"


def test_float_integral_value_serializes_without_decimal():
    assert canonicalize(1.0) == b"1"


def test_negative_zero_serializes_as_zero():
    assert canonicalize(-0.0) == b"0"


def test_nan_and_infinity_rejected():
    with pytest.raises(CanonicalizationError):
        canonicalize(float("nan"))
    with pytest.raises(CanonicalizationError):
        canonicalize(float("inf"))


def test_string_escapes_control_chars_and_quote_and_backslash():
    out = canonicalize({"k": "a\"b\\c\nd\te"})
    assert out == b'{"k":"a\\"b\\\\c\\nd\\te"}'


def test_non_ascii_is_left_as_literal_utf8_not_escaped():
    out = canonicalize({"k": "café"})
    assert out.decode("utf-8") == '{"k":"café"}'


def test_duplicate_keys_rejected_before_canonicalization():
    with pytest.raises(CanonicalizationError):
        parse_strict_json('{"a": 1, "a": 2}')


def test_duplicate_keys_rejected_in_nested_object():
    with pytest.raises(CanonicalizationError):
        parse_strict_json('{"outer": {"a": 1, "a": 2}}')


def test_invalid_utf8_bytes_rejected():
    with pytest.raises(CanonicalizationError):
        parse_strict_json(b"\xff\xfe{}")


def test_lone_surrogate_escape_rejected():
    with pytest.raises(CanonicalizationError):
        parse_strict_json('{"k": "\\ud800"}')


def test_lone_surrogate_in_object_key_rejected():
    with pytest.raises(CanonicalizationError):
        parse_strict_json('{"\\ud800": 1}')


def test_valid_surrogate_pair_is_accepted():
    # U+1F600 GRINNING FACE, expressed as a UTF-16 surrogate pair escape.
    value = parse_strict_json('{"k": "\\ud83d\\ude00"}')
    assert value["k"] == "\U0001F600"
    canonicalize(value)  # must not raise


def test_no_implicit_unicode_normalization():
    # "e" + combining acute (NFD) vs precomposed "é" (NFC) must round-trip
    # distinctly -- canonicalization must not normalize them together.
    nfd = "é"
    nfc = "é"
    assert nfd != nfc
    assert canonicalize(nfd) != canonicalize(nfc)


def test_canonical_sha256_is_deterministic_across_key_order():
    h1 = canonical_sha256({"a": 1, "b": 2})
    h2 = canonical_sha256({"b": 2, "a": 1})
    assert h1 == h2
    assert len(h1) == 64


def test_canonical_sha256_changes_with_semantic_content():
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_booleans_and_null():
    assert canonicalize(True) == b"true"
    assert canonicalize(False) == b"false"
    assert canonicalize(None) == b"null"


def test_malformed_json_rejected():
    with pytest.raises(CanonicalizationError):
        parse_strict_json('{"a": }')
