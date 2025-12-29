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
    requester = getattr(environment, "_spawn_requester", None) if environment else None
    if requester is None:
        return False
    return bool(requester(entity, reason=reason, metadata=metadata))


def request_remove(
    entity: Any,
    *,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Request a removal via the engine-backed mutation queue."""
    environment = getattr(entity, "environment", None)
    requester = getattr(environment, "_remove_requester", None) if environment else None
    if requester is None:
        return False
    return bool(requester(entity, reason=reason, metadata=metadata))
