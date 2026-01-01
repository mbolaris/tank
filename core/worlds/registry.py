"""World registry for creating multi-agent world backends.

This module provides a central registry for instantiating different world types
and associating them with high-level mode packs.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Callable

from core.modes.interfaces import ModeConfig, ModePack, ModePackDefinition
from core.modes.petri import create_petri_mode_pack
from core.modes.tank import create_tank_mode_pack
from core.worlds.interfaces import MultiAgentWorldBackend

logger = logging.getLogger(__name__)

# Factory receives seed + config overrides and returns a world backend.
WorldFactory = Callable[..., MultiAgentWorldBackend]

_WORLD_FACTORIES: dict[str, WorldFactory] = {}
_MODE_PACKS: dict[str, ModePack] = {}


def _identity_config(config: ModeConfig) -> ModeConfig:
    return dict(config)


class WorldRegistry:
    """Registry for mode packs and their world backend factories."""

    @staticmethod
    def register_mode_pack(mode_pack: ModePack) -> None:
        """Register a mode pack definition."""
        if mode_pack.mode_id in _MODE_PACKS:
            logger.warning("Overwriting mode pack '%s'", mode_pack.mode_id)
        _MODE_PACKS[mode_pack.mode_id] = mode_pack

    @staticmethod
    def register_world_type(
        world_type: str,
        factory: WorldFactory,
        *,
        mode_pack: ModePack | None = None,
        default_view_mode: str = "side",
        display_name: str | None = None,
    ) -> None:
        """Register a world backend factory and its default mode pack."""
        if world_type in _WORLD_FACTORIES:
            logger.warning("Overwriting world factory '%s'", world_type)

        _WORLD_FACTORIES[world_type] = factory

        if mode_pack is None:
            mode_pack = ModePackDefinition(
                mode_id=world_type,
                world_type=world_type,
                default_view_mode=default_view_mode,
                display_name=display_name or world_type.title(),
                normalizer=_identity_config,
            )

        WorldRegistry.register_mode_pack(mode_pack)

    @staticmethod
    def create_world(
        mode_id: str,
        *,
        seed: int | None = None,
        config: ModeConfig | None = None,
        **kwargs,
    ) -> MultiAgentWorldBackend:
        """Create a world backend for the given mode.

        Args:
            mode_id: Mode identifier (e.g., "tank", "petri", "soccer")
            seed: Optional random seed
            config: Optional config dict (normalized by the mode pack)
            **kwargs: Config overrides (merged into config)
        """
        mode_pack = _MODE_PACKS.get(mode_id)
        if mode_pack is None:
            raise ValueError(
                f"Unknown mode '{mode_id}'. Available modes: {list(_MODE_PACKS.keys())}"
            )

        combined_config: ModeConfig = {}
        if config:
            combined_config.update(config)
        if kwargs:
            combined_config.update(kwargs)

        normalized = mode_pack.configure(combined_config)

        factory = _WORLD_FACTORIES.get(mode_pack.world_type)
        if factory is None:
            raise NotImplementedError(f"World type '{mode_pack.world_type}' not yet implemented.")

        return factory(seed=seed, **normalized)

    @staticmethod
    def get_mode_pack(mode_id: str) -> ModePack | None:
        """Return a registered mode pack by id."""
        return _MODE_PACKS.get(mode_id)

    @staticmethod
    def list_mode_packs() -> dict[str, ModePack]:
        """Return all registered mode packs."""
        return dict(_MODE_PACKS)

    @staticmethod
    def list_modes() -> dict[str, str]:
        """List all available modes and their status."""
        statuses: dict[str, str] = {}
        for mode_id, mode_pack in _MODE_PACKS.items():
            status = (
                "implemented" if mode_pack.world_type in _WORLD_FACTORIES else "not_implemented"
            )
            statuses[mode_id] = status
        return statuses

    @staticmethod
    def list_world_types() -> dict[str, str]:
        """List world types (legacy compatibility)."""
        statuses: dict[str, str] = {}
        for mode_pack in _MODE_PACKS.values():
            status = (
                "implemented" if mode_pack.world_type in _WORLD_FACTORIES else "not_implemented"
            )
            if status == "implemented" or mode_pack.world_type not in statuses:
                statuses[mode_pack.world_type] = status
        return statuses


# =============================================================================
# Built-in mode pack registrations
# =============================================================================


def _register_builtin_modes() -> None:
    from core.worlds.petri.backend import PetriWorldBackendAdapter
    from core.worlds.tank.backend import TankWorldBackendAdapter

    # Implemented tank mode
    WorldRegistry.register_world_type(
        world_type="tank",
        factory=lambda **kwargs: TankWorldBackendAdapter(**kwargs),
        mode_pack=create_tank_mode_pack(),
        default_view_mode="side",
        display_name="Fish Tank",
    )

    # Implemented petri mode (reuses tank backend)
    WorldRegistry.register_world_type(
        world_type="petri",
        factory=lambda **kwargs: PetriWorldBackendAdapter(**kwargs),
        mode_pack=create_petri_mode_pack(),
    )

    core_dir = Path(__file__).resolve().parents[1]
    modes_dir = core_dir / "modes"
    soccer_mode_pack_factory = None
    if (modes_dir / "soccer.py").exists():
        soccer_mode_module = importlib.import_module("core.modes.soccer")
        soccer_mode_pack_factory = getattr(soccer_mode_module, "create_soccer_mode_pack", None)

    if soccer_mode_pack_factory is not None:
        soccer_mode_pack = soccer_mode_pack_factory()
    else:
        soccer_mode_pack = ModePackDefinition(
            mode_id="soccer",
            world_type="soccer",
            default_view_mode="topdown",
            display_name="Soccer Pitch",
            normalizer=_identity_config,
            supports_persistence=False,
            supports_actions=True,
            supports_websocket=False,
            supports_transfer=False,
            has_fish=False,
        )
    soccer_backend: type[MultiAgentWorldBackend] | None = None
    worlds_dir = Path(__file__).parent
    if (worlds_dir / "soccer" / "backend.py").exists():
        soccer_module = importlib.import_module("core.worlds.soccer.backend")
        soccer_backend = getattr(soccer_module, "SoccerWorldBackendAdapter", None)

    if soccer_backend is not None:
        WorldRegistry.register_world_type(
            world_type="soccer",
            factory=lambda **kwargs: soccer_backend(**kwargs),
            mode_pack=soccer_mode_pack,
            default_view_mode="topdown",
            display_name="Soccer Pitch",
        )
    else:
        WorldRegistry.register_mode_pack(soccer_mode_pack)

    soccer_training_mode_pack_factory = None
    if (modes_dir / "soccer_training.py").exists():
        soccer_training_module = importlib.import_module("core.modes.soccer_training")
        soccer_training_mode_pack_factory = getattr(
            soccer_training_module, "create_soccer_training_mode_pack", None
        )

    if soccer_training_mode_pack_factory is not None:
        soccer_training_mode_pack = soccer_training_mode_pack_factory()
    else:
        soccer_training_mode_pack = ModePackDefinition(
            mode_id="soccer_training",
            world_type="soccer_training",
            default_view_mode="topdown",
            display_name="Soccer Training",
            normalizer=_identity_config,
            supports_persistence=False,
            supports_actions=True,
            supports_websocket=False,
            supports_transfer=False,
            has_fish=False,
        )

    soccer_training_backend: type[MultiAgentWorldBackend] | None = None
    if (worlds_dir / "soccer_training" / "world.py").exists():
        soccer_training_module = importlib.import_module("core.worlds.soccer_training.world")
        soccer_training_backend = getattr(
            soccer_training_module, "SoccerTrainingWorldBackendAdapter", None
        )

    if soccer_training_backend is not None:
        WorldRegistry.register_world_type(
            world_type="soccer_training",
            factory=lambda **kwargs: soccer_training_backend(**kwargs),
            mode_pack=soccer_training_mode_pack,
            default_view_mode="topdown",
            display_name="Soccer Training",
        )
    else:
        WorldRegistry.register_mode_pack(soccer_training_mode_pack)


_register_builtin_modes()
