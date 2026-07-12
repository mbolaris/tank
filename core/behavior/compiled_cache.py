"""Bounded cache for compiled behavior-graph plans."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar, cast

from core.behavior.nodes import NodeRegistry

_COMPILED_GRAPH_CACHE_MAXSIZE = 256
_COMPILED_GRAPH_CACHE: OrderedDict[tuple[NodeRegistry, str], object] = OrderedDict()

T = TypeVar("T")


def get_compiled_plan(registry: NodeRegistry, fingerprint: str, compiler: Callable[[], T]) -> T:
    """Return a registry-specific LRU entry, compiling only when absent."""
    key = (registry, fingerprint)
    compiled = _COMPILED_GRAPH_CACHE.pop(key, None)
    if compiled is not None:
        _COMPILED_GRAPH_CACHE[key] = compiled
        return cast(T, compiled)

    compiled = compiler()
    _COMPILED_GRAPH_CACHE[key] = compiled
    if len(_COMPILED_GRAPH_CACHE) > _COMPILED_GRAPH_CACHE_MAXSIZE:
        _COMPILED_GRAPH_CACHE.popitem(last=False)
    return compiled
