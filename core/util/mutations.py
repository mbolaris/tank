"""Helpers for routing entity mutations through the engine."""

from typing import Any


def request_spawn(
    entity: Any,
    *,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
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


def request_spawn_in(
    environment: Any,
    entity: Any,
    *,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Request a spawn via the engine-backed mutation queue.

    Use this when the entity being spawned has no environment yet
    (e.g., newly-created overflow food). The environment parameter
    is used to find the spawn requester.

    Args:
        environment: The environment/engine that owns the spawn queue
        entity: The entity to spawn
        reason: Optional reason string for logging/debugging
        metadata: Optional metadata dict

    Returns:
        True if request was queued, False otherwise
    """
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
    metadata: dict[str, Any] | None = None,
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
