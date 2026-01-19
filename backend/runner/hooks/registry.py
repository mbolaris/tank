"""World hooks registry.

This module provides a registry and factory function for getting the
appropriate hooks implementation for a world type.
"""

from typing import Callable, Dict

from backend.runner.hooks.noop_hooks import NoOpWorldHooks
from backend.runner.hooks.petri_hooks import PetriWorldHooks
from backend.runner.hooks.protocol import WorldHooks
from backend.runner.hooks.tank_hooks import TankWorldHooks

# Registry mapping world types to their hooks factory functions
_HOOKS_REGISTRY: Dict[str, Callable[[], WorldHooks]] = {
    "tank": TankWorldHooks,
    "petri": PetriWorldHooks,
}


def register_hooks(world_type: str, hooks_factory: Callable[[], WorldHooks]) -> None:
    """Register a hooks factory for a world type.

    This allows external code to register custom hooks for new world types.

    Args:
        world_type: The world type identifier (e.g., "soccer", "sandbox")
        hooks_factory: A callable that returns a WorldHooks instance
    """
    _HOOKS_REGISTRY[world_type] = hooks_factory


def unregister_hooks(world_type: str) -> bool:
    """Unregister hooks for a world type.

    Args:
        world_type: The world type identifier

    Returns:
        True if hooks were unregistered, False if world type wasn't registered
    """
    if world_type in _HOOKS_REGISTRY:
        del _HOOKS_REGISTRY[world_type]
        return True
    return False


def get_hooks_for_world(world_type: str) -> WorldHooks:
    """Factory function to get the appropriate hooks for a world type.

    Args:
        world_type: The type of world (tank, petri, etc)

    Returns:
        WorldHooks instance for the world type
    """
    hooks_factory = _HOOKS_REGISTRY.get(world_type)
    if hooks_factory is not None:
        return hooks_factory()
    # All unregistered worlds use no-op hooks
    return NoOpWorldHooks()


def get_registered_world_types() -> list[str]:
    """Get list of world types that have registered hooks.

    Returns:
        List of world type identifiers
    """
    return list(_HOOKS_REGISTRY.keys())
