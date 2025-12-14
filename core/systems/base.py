"""Base class and protocol for simulation systems.

This module defines the contract that all simulation systems should follow.
Having a consistent interface makes the codebase predictable and easier to extend.

Design Principles:
- Each system has ONE responsibility (Single Responsibility Principle)
- Systems are initialized with their dependencies (Dependency Injection)
- Systems can be enabled/disabled without code changes
- Systems report their state for debugging
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


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

    def update(self, frame: int) -> None:
        """Perform the system's per-frame logic.

        Args:
            frame: Current simulation frame number
        """
        ...


class BaseSystem(ABC):
    """Abstract base class for all simulation systems.

    Provides common functionality and enforces the System protocol.
    Subclass this when creating new systems.

    Example:
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

    def update(self, frame: int) -> None:
        """Perform the system's per-frame logic.

        This method handles enabled checking and update counting.
        Subclasses implement _do_update() for actual logic.

        Args:
            frame: Current simulation frame number
        """
        if not self._enabled:
            return

        self._do_update(frame)
        self._update_count += 1

    @abstractmethod
    def _do_update(self, frame: int) -> None:
        """Implement system-specific update logic.

        This is called by update() if the system is enabled.

        Args:
            frame: Current simulation frame number
        """
        pass

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
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r}, enabled={self._enabled})"
