"""Immutable JSON-compatible values used at Compiler Core boundaries."""
from __future__ import annotations

from collections.abc import Mapping
import copy
from typing import Any


class FrozenDict(dict):
    """A recursively immutable ``dict`` that remains JSON-Schema compatible."""

    def __init__(self, values: Mapping[str, Any] = ()):
        dict.__init__(self, ((key, freeze_json(value)) for key, value in values.items()))

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("compiler boundary mappings are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        copied = {key: copy.deepcopy(value, memo) for key, value in self.items()}
        memo[id(self)] = copied
        return copied


class FrozenList(list):
    """A recursively immutable ``list`` that remains JSON-Schema compatible."""

    def __init__(self, values: list[Any] | tuple[Any, ...] = ()):
        list.__init__(self, (freeze_json(value) for value in values))

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("compiler boundary sequences are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> list[Any]:
        copied = [copy.deepcopy(value, memo) for value in self]
        memo[id(self)] = copied
        return copied


def freeze_json(value: Any) -> Any:
    """Return a defensive, recursively immutable copy of JSON-shaped data."""
    if isinstance(value, FrozenDict | FrozenList):
        return value
    if isinstance(value, Mapping):
        return FrozenDict(value)
    if isinstance(value, (list, tuple)):
        return FrozenList(value)
    return value
