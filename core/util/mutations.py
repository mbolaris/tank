"""Helpers for routing entity mutations through the engine."""

from typing import Any, Dict, Optional


def request_spawn(
    entity: Any,
    *,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Request a spawn via the engine-backed mutation queue."""
    environment = getattr(entity, "environment", None)
    if environment is None:
        return False
    requester = getattr(environment, "_spawn_requester", None)
    if requester is not None:
        return bool(requester(entity, reason=reason, metadata=metadata))
    fallback = getattr(environment, "request_spawn", None)
    if callable(fallback):
        try:
            return bool(fallback(entity, reason=reason, metadata=metadata))
        except TypeError:
            return bool(fallback(entity, reason=reason))
    return False


def request_remove(
    entity: Any,
    *,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Request a removal via the engine-backed mutation queue."""
    environment = getattr(entity, "environment", None)
    if environment is None:
        return False
    requester = getattr(environment, "_remove_requester", None)
    if requester is not None:
        return bool(requester(entity, reason=reason, metadata=metadata))
    fallback = getattr(environment, "request_remove", None)
    if callable(fallback):
        try:
            return bool(fallback(entity, reason=reason, metadata=metadata))
        except TypeError:
            return bool(fallback(entity, reason=reason))
    return False
