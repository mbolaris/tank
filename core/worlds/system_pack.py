"""Interfaces for multi-agent world system packs.

SystemPacks encapsulate the wiring, system registration, and entity seeding
logic for specific world modes (Tank, Petri, Soccer, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine
    from core.simulation.phase_hooks import PhaseHooks
    from core.simulation.pipeline import EnginePipeline
    from core.worlds.identity import EntityIdentityProvider


@runtime_checkable
class EnvironmentLike(Protocol):
    """Protocol for environment-like objects.

    This allows different world modes to provide their own environment
    implementations as long as they satisfy the basic interface needed by the engine.
    """

    def update_agent_position(self, agent: Any) -> None: ...
    def update_detection_modifier(self) -> None: ...


class SystemPack(Protocol):
    """Protocol for world mode setup packs.

    A SystemPack is responsible for:
    1. Building the environment
    2. Registering systems in the correct order
    3. Seeding initial entities
    4. Optionally providing a custom pipeline
    5. Providing an identity provider for delta tracking
    6. Providing phase hooks for mode-specific entity handling
    """

    @property
    def mode_id(self) -> str:
        """The unique identifier for this mode (e.g., 'tank')."""
        ...

    def build_environment(self, engine: SimulationEngine) -> EnvironmentLike:
        """Create and return the environment for this mode."""
        ...

    def register_systems(self, engine: SimulationEngine) -> None:
        """Register all required systems in the engine's system registry."""
        ...

    def register_contracts(self, engine: SimulationEngine) -> None:
        """Register action/observation translators for this world mode."""
        ...

    def seed_entities(self, engine: SimulationEngine) -> None:
        """Create and add initial entities to the simulation."""
        ...

    def get_metadata(self) -> dict[str, Any]:
        """Return mode-specific metadata for snapshots."""
        ...

    def build_core_systems(self, engine: SimulationEngine) -> dict[str, Any]:
        """Build and return core systems for the engine.

        The engine will wire these systems into its historical attributes
        for backward compatibility.
        """
        ...

    def get_pipeline(self) -> EnginePipeline | None:
        """Return custom pipeline or None for default.

        If None is returned, the engine will use default_pipeline().
        Override this to provide a custom update loop for your mode.
        """
        ...

    def get_identity_provider(self) -> EntityIdentityProvider | None:
        """Return the identity provider for this mode.

        The identity provider is used by the engine to obtain stable
        entity identities for delta tracking (spawns, removals, energy changes).

        Return None to fall back to default behavior (class name + id()).
        """
        ...

    def get_phase_hooks(self) -> "PhaseHooks | None":
        """Return phase hooks for mode-specific entity handling.

        Phase hooks allow modes to customize how entities are handled during
        specific phases (spawn decisions, death handling, lifecycle cleanup, etc.)
        without modifying engine code.

        Return None to use default no-op hooks.
        """
        ...
