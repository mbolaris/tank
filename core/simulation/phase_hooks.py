"""Phase hooks for mode-specific behavior in the engine update loop.

This module defines the PhaseHooks protocol that allows different world modes
to customize entity handling during specific phases without modifying engine code.

Design Notes:
- PhaseHooks is a Protocol with default implementations (no-ops)
- Packs return their hooks via get_phase_hooks()
- The engine calls hooks at specific points in phase methods
- Tank provides TankPhaseHooks with Fish/Plant/Food logic
- Soccer will provide SoccerPhaseHooks with Player/Ball/Goal logic
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine


@dataclass
class SpawnDecision:
    """Result of evaluating whether a spawned entity should be added.
    
    Attributes:
        should_add: Whether to add the entity to the simulation
        entity: The entity to add (may be modified by the hook)
        reason: Optional reason for the decision (for debugging)
    """
    should_add: bool
    entity: Any
    reason: str = ""


@runtime_checkable
class PhaseHooks(Protocol):
    """Protocol for mode-specific phase behavior.
    
    Hooks are called by the engine at specific points in the update loop.
    Modes can override these to customize entity handling without touching
    engine code.
    
    All methods have default no-op implementations to allow partial overrides.
    """

    def on_entity_spawned(
        self,
        engine: "SimulationEngine",
        spawned_entity: Any,
        parent_entity: Any,
    ) -> SpawnDecision:
        """Called when entity.update() returns spawned entities.
        
        Args:
            engine: The simulation engine
            spawned_entity: The newly spawned entity
            parent_entity: The entity that spawned it
            
        Returns:
            SpawnDecision indicating whether to add the entity
        """
        ...

    def on_entity_died(
        self,
        engine: "SimulationEngine",
        entity: Any,
    ) -> bool:
        """Called when entity.is_dead() returns True.
        
        The hook should handle mode-specific death logic (death animations,
        score updates, etc.) and return whether the entity should be queued
        for removal.
        
        Args:
            engine: The simulation engine
            entity: The entity that died
            
        Returns:
            True if entity should be added to removal list, False otherwise
        """
        ...

    def on_lifecycle_cleanup(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Called during lifecycle phase for mode-specific cleanup.
        
        Use this for things like food expiry checks, death animation cleanup,
        goal reset logic, etc.
        
        Args:
            engine: The simulation engine
        """
        ...

    def on_reproduction_complete(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Called at end of reproduction phase for stats recording.
        
        Use this for population stats, energy snapshots, etc.
        
        Args:
            engine: The simulation engine
        """
        ...

    def on_frame_end(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Called at end of frame for mode-specific cleanup.
        
        Use this for benchmarks, periodic cleanup, etc.
        
        Args:
            engine: The simulation engine
        """
        ...


class NoOpPhaseHooks:
    """Default no-op implementation of PhaseHooks.
    
    Used when a pack doesn't provide custom hooks.
    """

    def on_entity_spawned(
        self,
        engine: "SimulationEngine",
        spawned_entity: Any,
        parent_entity: Any,
    ) -> SpawnDecision:
        """Default: accept all spawns."""
        return SpawnDecision(should_add=True, entity=spawned_entity)

    def on_entity_died(
        self,
        engine: "SimulationEngine",
        entity: Any,
    ) -> bool:
        """Default: queue entity for removal."""
        return True

    def on_lifecycle_cleanup(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Default: no cleanup."""
        pass

    def on_reproduction_complete(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Default: no stats recording."""
        pass

    def on_frame_end(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Default: no frame-end processing."""
        pass
