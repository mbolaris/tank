"""Shared serialization helpers for the state payload dataclasses."""

from __future__ import annotations

import json
from typing import Any, cast

orjson: Any = None
try:  # Prefer faster serializer when available
    import orjson as _orjson

    orjson = _orjson
except ImportError:
    pass


def to_dict(dataclass_obj: Any) -> dict[str, Any]:
    """Dictionary representation for dataclasses (slots or regular)."""
    slots = getattr(dataclass_obj, "__slots__", None)
    if slots:
        return {name: getattr(dataclass_obj, name) for name in slots}
    return {
        field.name: getattr(dataclass_obj, field.name)
        for field in dataclass_obj.__dataclass_fields__.values()
    }


def serialize(data: dict[str, Any]) -> str:
    """Serialize a payload dict, preferring orjson when available."""
    if orjson:
        return cast(bytes, orjson.dumps(data)).decode("utf-8")
    return json.dumps(data, separators=(",", ":"))
