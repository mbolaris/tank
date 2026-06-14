"""World registry for creating multi-agent world backends.

This module provides a central registry for instantiating different world types
and associating them with high-level mode packs.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from core.exceptions import ConfigurationError
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
            mode_id: Mode identifier (e.g., "tank", "petri")
            seed: Optional random seed
            config: Optional config dict (normalized by the mode pack)
            **kwargs: Config overrides (merged into config)
        """
        _ensure_builtin_modes()
        mode_pack = _MODE_PACKS.get(mode_id)
        if mode_pack is None:
            raise ConfigurationError(
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
        _ensure_builtin_modes()
        return _MODE_PACKS.get(mode_id)

    @staticmethod
    def list_mode_packs() -> dict[str, ModePack]:
        """Return all registered mode packs."""
        _ensure_builtin_modes()
        return dict(_MODE_PACKS)

    @staticmethod
    def list_modes() -> dict[str, str]:
        """List all available modes and their status."""
        _ensure_builtin_modes()
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
        _ensure_builtin_modes()
        statuses: dict[str, str] = {}
        for mode_pack in _MODE_PACKS.values():
            status = (
                "implemented" if mode_pack.world_type in _WORLD_FACTORIES else "not_implemented"
            )
            if status == "implemented" or mode_pack.world_type not in statuses:
                statuses[mode_pack.world_type] = status
        return statuses


# =============================================================================
# Built-in mode pack registrations (lazy)
# =============================================================================

_builtins_registered = False
_registration_lock = threading.Lock()


def _ensure_builtin_modes() -> None:
    """Register built-in mode packs on first use (thread-safe, idempotent).

    Registration is deferred (rather than run at import time) so that importing
    ``core.worlds`` does not eagerly pull in the Tank/Petri world backends,
    which depend on ``core.simulation`` and would otherwise form an import-time
    cycle. The registry's read methods call this before serving. See ADR-008.

    Double-checked locking keeps concurrent first reads (the backend drives
    simulations on worker threads) from registering twice or observing a
    half-populated registry.
    """
    global _builtins_registered
    if _builtins_registered:
        return
    with _registration_lock:
        if _builtins_registered:
            return
        _register_builtin_modes()
        _builtins_registered = True


def _register_builtin_modes() -> None:
    from core.worlds.petri.backend import PetriWorldBackendAdapter
    from core.worlds.tank.backend import TankWorldBackendAdapter

    # Implemented tank mode
    WorldRegistry.register_world_type(
        world_type="tank",
        factory=lambda **kwargs: TankWorldBackendAdapter(**kwargs),
        mode_pack=create_tank_mode_pack(),
        default_view_mode="side",
        display_name="Tank",
    )

    # Implemented petri mode (reuses tank backend)
    WorldRegistry.register_world_type(
        world_type="petri",
        factory=lambda **kwargs: PetriWorldBackendAdapter(**kwargs),
        mode_pack=create_petri_mode_pack(),
    )

    # Note: Soccer is NOT registered as a world mode.
    # It is a minigame accessible via the "start_soccer" command handler.
    # See core/minigames/soccer/ for the RCSS-Lite engine.
