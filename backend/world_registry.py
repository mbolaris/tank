"""Mode-aware world registry for backend runtime.

This module bridges core mode packs with backend snapshot builders.
It creates worlds via core WorldRegistry and pairs them with snapshot builders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from core.worlds.registry import WorldRegistry

if TYPE_CHECKING:
    from backend.snapshots.interfaces import SnapshotBuilder
    from core.worlds.interfaces import MultiAgentWorldBackend

logger = logging.getLogger(__name__)


@dataclass
class WorldMetadata:
    """Metadata for a registered mode pack.

    All capability flags are read from the canonical ModePackDefinition in core.
    """

    mode_id: str
    world_type: str
    view_mode: str
    display_name: str
    supports_persistence: bool = True
    supports_actions: bool = False
    supports_websocket: bool = True
    supports_transfer: bool = False
    has_fish: bool = False


SnapshotBuilderFactory = Callable[[], "SnapshotBuilder"]

_SNAPSHOT_BUILDERS: dict[str, SnapshotBuilderFactory] = {}


def register_snapshot_builder(
    mode_id: str,
    snapshot_builder_factory: SnapshotBuilderFactory,
) -> None:
    """Register a snapshot builder factory for an existing core mode pack."""
    mode_pack = WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        available = list(WorldRegistry.list_mode_packs().keys())
        raise ValueError(f"Unknown world type '{mode_id}'. Available types: {available}")

    if (
        mode_pack.snapshot_builder_factory is not None
        and mode_pack.snapshot_builder_factory is not snapshot_builder_factory
    ):
        logger.warning("Overwriting snapshot builder for mode '%s'", mode_id)

    mode_pack.snapshot_builder_factory = snapshot_builder_factory
    _SNAPSHOT_BUILDERS[mode_id] = snapshot_builder_factory
    logger.info("Registered snapshot builder for mode '%s'", mode_id)


def create_world(
    mode_id: str,
    *,
    seed: int | None = None,
    config: dict[str, Any] | None = None,
    headless: bool = True,
    **kwargs: Any,
) -> tuple[MultiAgentWorldBackend, SnapshotBuilder]:
    """Create a world instance and its snapshot builder.

    Args:
        mode_id: The mode to create (e.g., "tank")
        seed: Optional random seed for deterministic behavior
        config: Optional config dict (normalized by the mode pack)
        headless: Whether to run in headless mode (default True for backend)
        **kwargs: Additional config overrides
    """
    mode_pack = WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        available = list(WorldRegistry.list_mode_packs().keys())
        raise ValueError(f"Unknown mode '{mode_id}'. Available modes: {available}")

    combined: dict[str, Any] = {}
    if config:
        combined.update(config)
    combined.update(kwargs)
    combined.setdefault("headless", headless)

    world = WorldRegistry.create_world(mode_pack.mode_id, seed=seed, config=combined)
    world.reset(seed=seed, config=combined)

    builder_factory = (
        _SNAPSHOT_BUILDERS.get(mode_pack.mode_id) or mode_pack.snapshot_builder_factory
    )
    if builder_factory is None:
        raise ValueError(f"No snapshot builder registered for mode '{mode_pack.mode_id}'")
    snapshot_builder = builder_factory()

    return world, snapshot_builder


def get_world_metadata(mode_id: str) -> WorldMetadata | None:
    """Get metadata for a registered mode pack.

    Capability flags are read directly from the mode pack definition,
    which is the canonical source of truth in core.modes.
    """
    mode_pack = WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        return None
    return WorldMetadata(
        mode_id=mode_pack.mode_id,
        world_type=mode_pack.world_type,
        view_mode=mode_pack.default_view_mode,
        display_name=mode_pack.display_name,
        supports_persistence=getattr(mode_pack, "supports_persistence", True),
        supports_actions=getattr(mode_pack, "supports_actions", False),
        supports_websocket=getattr(mode_pack, "supports_websocket", True),
        supports_transfer=getattr(mode_pack, "supports_transfer", False),
        has_fish=getattr(mode_pack, "has_fish", False),
    )


def get_all_world_metadata() -> list[WorldMetadata]:
    """Get metadata for all registered mode packs."""
    result: list[WorldMetadata] = []
    all_packs = WorldRegistry.list_mode_packs()
    for mode_id in all_packs:
        meta = get_world_metadata(mode_id)
        if meta is not None:
            result.append(meta)
    return result


def get_registered_world_types() -> list[str]:
    """Get list of registered mode ids (legacy compatibility)."""
    return list(WorldRegistry.list_mode_packs().keys())


# =============================================================================
# Tank Mode Registration
# =============================================================================


def _register_tank_mode() -> None:
    from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder

    register_snapshot_builder("tank", TankSnapshotBuilder)


_register_tank_mode()


def _register_petri_mode() -> None:
    from backend.snapshots.petri_snapshot_builder import PetriSnapshotBuilder

    register_snapshot_builder("petri", PetriSnapshotBuilder)


_register_petri_mode()


# Note: Soccer is NOT registered as a world mode.
# It is a minigame accessible via the "start_soccer" command handler.
# Snapshot building is handled inline by core/soccer_match.py.
