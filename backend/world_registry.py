"""World registry for creating world instances by type.

This module provides a factory registry pattern for creating world instances.
Each world type (tank, petri, soccer) registers a factory function that
creates the world and its associated snapshot builder.

Usage:
    from backend.world_registry import create_world, get_world_metadata

    # Create a tank world with its snapshot builder
    world, snapshot_builder = create_world("tank", seed=42)

    # Get metadata about a world type
    metadata = get_world_metadata("tank")
    print(metadata["view_mode"])  # "side"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.interfaces import WorldBackend
    from backend.snapshots.interfaces import SnapshotBuilder

logger = logging.getLogger(__name__)


@dataclass
class WorldMetadata:
    """Metadata for a registered world type."""

    world_type: str
    view_mode: str  # "side", "top", etc.
    display_name: str


# Type for world factory functions
# Factory receives kwargs and returns (world, snapshot_builder)
WorldFactory = Callable[..., Tuple["WorldBackend", "SnapshotBuilder"]]

# Registry storage
_WORLD_FACTORIES: Dict[str, WorldFactory] = {}
_WORLD_METADATA: Dict[str, WorldMetadata] = {}


def register_world(
    world_type: str,
    factory: WorldFactory,
    view_mode: str = "side",
    display_name: Optional[str] = None,
) -> None:
    """Register a world type with its factory function.

    Args:
        world_type: Unique identifier for the world type (e.g., "tank", "petri")
        factory: Factory function that creates (world, snapshot_builder) tuple
        view_mode: Default view mode for the frontend ("side", "top", etc.)
        display_name: Human-readable name for the world type
    """
    if world_type in _WORLD_FACTORIES:
        logger.warning(f"Overwriting existing world factory for '{world_type}'")

    _WORLD_FACTORIES[world_type] = factory
    _WORLD_METADATA[world_type] = WorldMetadata(
        world_type=world_type,
        view_mode=view_mode,
        display_name=display_name or world_type.title(),
    )
    logger.info(f"Registered world type '{world_type}' with view_mode='{view_mode}'")


def create_world(world_type: str, **kwargs: Any) -> Tuple["WorldBackend", "SnapshotBuilder"]:
    """Create a world instance and its snapshot builder.

    Args:
        world_type: The type of world to create
        **kwargs: Arguments passed to the world factory (seed, config, etc.)

    Returns:
        Tuple of (world, snapshot_builder)

    Raises:
        ValueError: If world_type is not registered
    """
    if world_type not in _WORLD_FACTORIES:
        available = list(_WORLD_FACTORIES.keys())
        raise ValueError(
            f"Unknown world type '{world_type}'. Available types: {available}"
        )

    factory = _WORLD_FACTORIES[world_type]
    return factory(**kwargs)


def get_world_metadata(world_type: str) -> Optional[WorldMetadata]:
    """Get metadata for a registered world type.

    Args:
        world_type: The type of world

    Returns:
        WorldMetadata if registered, None otherwise
    """
    return _WORLD_METADATA.get(world_type)


def get_registered_world_types() -> list[str]:
    """Get list of all registered world types."""
    return list(_WORLD_FACTORIES.keys())


# =============================================================================
# Tank World Registration
# =============================================================================


def _create_tank_world(
    seed: Optional[int] = None,
    headless: bool = True,
    **kwargs: Any,
) -> Tuple["WorldBackend", "SnapshotBuilder"]:
    """Factory function for creating tank world instances.

    Args:
        seed: Optional random seed for deterministic behavior
        headless: Whether to run in headless mode (default True for backend)
        **kwargs: Additional configuration options

    Returns:
        Tuple of (TankWorld, TankSnapshotBuilder)
    """
    from core.tank_world import TankWorld, TankWorldConfig
    from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder

    config = TankWorldConfig(headless=headless)
    world = TankWorld(config=config, seed=seed)
    world.setup()

    snapshot_builder = TankSnapshotBuilder()

    return world, snapshot_builder


# Register tank world on module import
register_world(
    world_type="tank",
    factory=_create_tank_world,
    view_mode="side",
    display_name="Fish Tank",
)
