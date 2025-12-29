"""Base class and protocol for simulation systems.

This module defines the contract that all simulation systems should follow.
Having a consistent interface makes the codebase predictable and easier to extend.

Design Principles:
- Each system has ONE responsibility (Single Responsibility Principle)
- Systems are initialized with their dependencies (Dependency Injection)
- Systems can be enabled/disabled without code changes
- Systems may declare a phase for diagnostics and validation
- Systems report their state for debugging
- Systems return results describing what they did (for debugging/metrics)

Phase-System Mapping:
---------------------
Systems may declare which UpdatePhase they belong to. The engine uses an
explicit phase loop for execution order; the phase metadata is used for
diagnostics and validation:

    @runs_in_phase(UpdatePhase.COLLISION)
    class CollisionSystem(BaseSystem):
        ...

The simulation engine can then orchestrate systems by phase, ensuring
predictable execution order regardless of registration order.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, runtime_checkable

# Explicit public API
__all__ = [
    "SystemResult",
    "System",
    "BaseSystem",
]

if TYPE_CHECKING:
    from core.simulation import SimulationEngine
    from core.update_phases import UpdatePhase


@dataclass
class SystemResult:
    """Result of a system update cycle.

    Systems return this to describe what they did during an update.
    This makes debugging easier and enables metrics collection.

    Attributes:
        entities_affected: Number of entities that were modified
        entities_spawned: Number of new entities created
        entities_removed: Number of entities removed/killed
        events_emitted: Number of events emitted to event bus
        skipped: Whether the update was skipped (system disabled)
        details: System-specific details (e.g., {"collisions": 5, "food_eaten": 3})

    Example:
        def _do_update(self, frame: int) -> SystemResult:
            collisions = self.check_collisions()
            return SystemResult(
                entities_affected=len(collisions),
                details={"collision_count": len(collisions)}
            )
    """

    entities_affected: int = 0
    entities_spawned: int = 0
    entities_removed: int = 0
    events_emitted: int = 0
    skipped: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def skipped_result() -> "SystemResult":
        """Create a result for when system update was skipped."""
        return SystemResult(skipped=True)

    @staticmethod
    def empty() -> "SystemResult":
        """Create an empty result (nothing happened)."""
        return SystemResult()

    def __add__(self, other: "SystemResult") -> "SystemResult":
        """Combine two results (useful for aggregating across frames)."""
        if other.skipped:
            return self
        if self.skipped:
            return other

        combined_details = {**self.details}
        for key, value in other.details.items():
            if key in combined_details and isinstance(value, (int, float)):
                combined_details[key] = combined_details[key] + value
            else:
                combined_details[key] = value

        return SystemResult(
            entities_affected=self.entities_affected + other.entities_affected,
            entities_spawned=self.entities_spawned + other.entities_spawned,
            entities_removed=self.entities_removed + other.entities_removed,
            events_emitted=self.events_emitted + other.events_emitted,
            skipped=False,
            details=combined_details,
        )


@runtime_checkable
class System(Protocol):
    """Protocol defining what all systems must implement.

    Use this for type hints when you need "any system" without caring
    about the specific implementation.
    """

    @property
    def name(self) -> str:
        """Human-readable name for debugging and logging."""
        ...

    @property
    def enabled(self) -> bool:
        """Whether this system should run during updates."""
        ...

    def update(self, frame: int) -> SystemResult:
        """Perform the system's per-frame logic.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult describing what the system did
        """
        ...


class BaseSystem(ABC):
    """Abstract base class for all simulation systems.

    Provides common functionality and enforces the System protocol.
    Subclass this when creating new systems.

    Systems can optionally declare which phase they run in using the
    @runs_in_phase decorator or by setting _phase in __init__. The engine
    still controls execution order explicitly; phase metadata is informational.

    Example:
        from core.update_phases import UpdatePhase, runs_in_phase

        @runs_in_phase(UpdatePhase.ENVIRONMENT)
        class WeatherSystem(BaseSystem):
            def __init__(self, engine: SimulationEngine):
                super().__init__(engine, "Weather")
                self.current_weather = "sunny"

            def _do_update(self, frame: int) -> None:
                # Weather logic here
                pass

            def get_debug_info(self) -> Dict[str, Any]:
                return {"weather": self.current_weather}
    """

    # Class-level phase declaration (set by @runs_in_phase decorator)
    _phase: Optional["UpdatePhase"] = None

    def __init__(self, engine: "SimulationEngine", name: str) -> None:
        """Initialize the system.

        Args:
            engine: The simulation engine (provides access to entities, etc.)
            name: Human-readable name for this system
        """
        self._engine = engine
        self._name = name
        self._enabled = True
        self._update_count = 0

    @property
    def name(self) -> str:
        """Human-readable name for debugging and logging."""
        return self._name

    @property
    def enabled(self) -> bool:
        """Whether this system should run during updates."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable this system."""
        self._enabled = value

    @property
    def engine(self) -> "SimulationEngine":
        """Access to the simulation engine."""
        return self._engine

    @property
    def update_count(self) -> int:
        """Number of times update() has been called."""
        return self._update_count

    def update(self, frame: int) -> SystemResult:
        """Perform the system's per-frame logic.

        This method handles enabled checking and update counting.
        Subclasses implement _do_update() for actual logic.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult describing what the system did
        """
        if not self._enabled:
            return SystemResult.skipped_result()

        result = self._do_update(frame)
        self._update_count += 1

        # Handle legacy systems that return None
        if result is None:
            return SystemResult.empty()
        return result

    @abstractmethod
    def _do_update(self, frame: int) -> Optional[SystemResult]:
        """Implement system-specific update logic.

        This is called by update() if the system is enabled.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult describing what the system did, or None for legacy compatibility
        """
        pass

    @property
    def phase(self) -> Optional["UpdatePhase"]:
        """The update phase this system runs in.

        Systems can declare their phase using the @runs_in_phase decorator
        or by overriding this property.

        Returns:
            The UpdatePhase this system belongs to, or None if not phase-aware
        """
        return self._phase

    def get_debug_info(self) -> Dict[str, Any]:
        """Return debug information about this system's state.

        Override in subclasses to expose system-specific state.
        Useful for debugging and monitoring.

        Returns:
            Dictionary of debug information
        """
        return {
            "name": self._name,
            "enabled": self._enabled,
            "update_count": self._update_count,
            "phase": self._phase.name if self._phase else None,
        }

    def __repr__(self) -> str:
        phase_str = f", phase={self._phase.name}" if self._phase else ""
        return f"{self.__class__.__name__}(name={self._name!r}, enabled={self._enabled}{phase_str})"
