"""Mode-aware world registry for backend runtime.

This module bridges core mode packs with backend snapshot builders.
It creates worlds via core WorldRegistry and pairs them with snapshot builders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from core.modes.interfaces import ModePack
from core.modes.petri import create_petri_mode_pack
from core.modes.tank import create_tank_mode_pack
from core.worlds.registry import WorldRegistry

if TYPE_CHECKING:
    from backend.snapshots.interfaces import SnapshotBuilder
    from core.worlds.interfaces import MultiAgentWorldBackend

logger = logging.getLogger(__name__)


@dataclass
class WorldMetadata:
    """Metadata for a registered mode pack."""

    mode_id: str
    world_type: str
    view_mode: str
    display_name: str
    supports_persistence: bool = True
    supports_actions: bool = False


SnapshotBuilderFactory = Callable[[], "SnapshotBuilder"]

_MODE_PACKS: Dict[str, ModePack] = {}
_SNAPSHOT_BUILDERS: Dict[str, SnapshotBuilderFactory] = {}


def register_mode_pack(
    mode_pack: ModePack,
    snapshot_builder_factory: SnapshotBuilderFactory,
) -> None:
    """Register a mode pack with its snapshot builder factory."""
    if mode_pack.mode_id in _MODE_PACKS:
        logger.warning("Overwriting mode pack '%s' in backend registry", mode_pack.mode_id)

    mode_pack.snapshot_builder_factory = snapshot_builder_factory
    _MODE_PACKS[mode_pack.mode_id] = mode_pack
    _SNAPSHOT_BUILDERS[mode_pack.mode_id] = snapshot_builder_factory

    # Ensure core registry uses the same mode pack definition.
    WorldRegistry.register_mode_pack(mode_pack)
    logger.info("Registered mode pack '%s' for world_type '%s'", mode_pack.mode_id, mode_pack.world_type)


def create_world(
    mode_id: str,
    *,
    seed: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
    headless: bool = True,
    **kwargs: Any,
) -> Tuple[MultiAgentWorldBackend, SnapshotBuilder]:
    """Create a world instance and its snapshot builder.

    Args:
        mode_id: The mode to create (e.g., "tank")
        seed: Optional random seed for deterministic behavior
        config: Optional config dict (normalized by the mode pack)
        headless: Whether to run in headless mode (default True for backend)
        **kwargs: Additional config overrides
    """
    mode_pack = _MODE_PACKS.get(mode_id) or WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        available = list(WorldRegistry.list_mode_packs().keys())
        raise ValueError(f"Unknown mode '{mode_id}'. Available modes: {available}")

    combined: Dict[str, Any] = {}
    if config:
        combined.update(config)
    combined.update(kwargs)
    combined.setdefault("headless", headless)

    world = WorldRegistry.create_world(mode_pack.mode_id, seed=seed, config=combined)
    world.reset(seed=seed, config=combined)

    builder_factory = _SNAPSHOT_BUILDERS.get(mode_pack.mode_id)
    if builder_factory is None:
        raise ValueError(f"No snapshot builder registered for mode '{mode_pack.mode_id}'")
    snapshot_builder = builder_factory()

    return world, snapshot_builder


# Capability metadata per mode
_MODE_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    "tank": {"supports_persistence": True, "supports_actions": False},
    "petri": {"supports_persistence": True, "supports_actions": False},
    "soccer": {"supports_persistence": False, "supports_actions": True},
}


def get_world_metadata(mode_id: str) -> Optional[WorldMetadata]:
    """Get metadata for a registered mode pack."""
    mode_pack = _MODE_PACKS.get(mode_id) or WorldRegistry.get_mode_pack(mode_id)
    if mode_pack is None:
        return None
    caps = _MODE_CAPABILITIES.get(mode_id, {})
    return WorldMetadata(
        mode_id=mode_pack.mode_id,
        world_type=mode_pack.world_type,
        view_mode=mode_pack.default_view_mode,
        display_name=mode_pack.display_name,
        supports_persistence=caps.get("supports_persistence", True),
        supports_actions=caps.get("supports_actions", False),
    )


def get_all_world_metadata() -> list[WorldMetadata]:
    """Get metadata for all registered mode packs."""
    result: list[WorldMetadata] = []
    all_packs = dict(WorldRegistry.list_mode_packs())
    all_packs.update(_MODE_PACKS)
    for mode_id in all_packs:
        meta = get_world_metadata(mode_id)
        if meta is not None:
            result.append(meta)
    return result


def get_registered_world_types() -> list[str]:
    """Get list of registered mode ids (legacy compatibility)."""
    if _MODE_PACKS:
        return list(_MODE_PACKS.keys())
    return list(WorldRegistry.list_mode_packs().keys())


# =============================================================================
# Tank Mode Registration
# =============================================================================


def _register_tank_mode() -> None:
    from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder

    register_mode_pack(
        create_tank_mode_pack(snapshot_builder_factory=TankSnapshotBuilder),
        TankSnapshotBuilder,
    )


_register_tank_mode()


def _register_petri_mode() -> None:
    from backend.snapshots.petri_snapshot_builder import PetriSnapshotBuilder

    register_mode_pack(
        create_petri_mode_pack(snapshot_builder_factory=PetriSnapshotBuilder),
        PetriSnapshotBuilder,
    )


_register_petri_mode()


def _register_soccer_mode() -> None:
    from backend.snapshots.soccer_snapshot_builder import SoccerSnapshotBuilder
    from core.modes.soccer import create_soccer_mode_pack

    register_mode_pack(
        create_soccer_mode_pack(snapshot_builder_factory=SoccerSnapshotBuilder),
        SoccerSnapshotBuilder,
    )


_register_soccer_mode()
