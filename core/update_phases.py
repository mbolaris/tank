"""Update phase definitions for explicit execution ordering.

This module defines the phases of a simulation update tick and provides
tools for organizing system execution in a predictable order.

Why Explicit Phases?
--------------------
Before (implicit ordering):
    def update(self):
        self.time_system.update(self.frame)
        self.handle_collisions()  # Wait, should this be before or after entities?
        for entity in entities:
            entity.update()
        self.handle_reproduction()  # What about deaths? Before or after?
        self.spawn_food()

After (explicit phases):
    def update(self):
        for phase in UpdatePhase:
            self._run_phase(phase)

    def _run_phase(self, phase: UpdatePhase):
        for system in self.systems_by_phase[phase]:
            system.update(self.frame)

Benefits:
- Execution order is explicit and documented
- Easy to add new systems to correct phase
- Debugging: "what phase are we in?"
- Testing: can run phases in isolation
- Self-documenting code

Note: The current SimulationEngine uses explicit phase methods instead of
PhaseRunner. PhaseRunner remains as an optional utility for tests or future
refactors.

Usage:
------
    # Systems declare which phase they run in
    class CollisionSystem(BaseSystem):
        phase = UpdatePhase.COLLISION

    # Runner executes in order
    runner = PhaseRunner()
    runner.register(collision_system)
    runner.register(time_system)
    runner.run_all(frame=1)  # Runs in phase order regardless of registration order
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

# Explicit public API
__all__ = [
    # Core types
    "UpdatePhase",
    "PhaseContext",
    "PhaseRunner",
    # Protocol
    "PhaseAware",
    # Helpers
    "PHASE_DESCRIPTIONS",
    "runs_in_phase",
    "get_system_phase",
]

if TYPE_CHECKING:
    from core.systems.base import BaseSystem


class UpdatePhase(Enum):
    """Phases of a simulation update tick.

    Systems execute in phase order. Within a phase, systems execute
    in registration order.

    The phases are:

    1. FRAME_START: Reset per-frame counters, prepare for new frame
    2. TIME_UPDATE: Advance time, update time-dependent modifiers
    3. ENVIRONMENT: Update environmental factors (light, temperature)
    4. ENTITY_THINK: Entities decide what to do (AI, behavior algorithms)
    5. ENTITY_ACT: Entities perform actions (movement, energy use)
    6. COLLISION: Detect and handle collisions
    7. INTERACTION: Handle entity interactions (eating, poker, mating)
    8. REPRODUCTION: Process reproduction and spawning
    9. LIFECYCLE: Process deaths, births, state transitions
    10. SPAWN: Spawn new entities (food, emergency fish)
    11. CLEANUP: Remove dead entities, return to pools
    12. FRAME_END: Update statistics, record snapshots
    """

    FRAME_START = auto()  # Reset counters, prepare new frame
    TIME_UPDATE = auto()  # Advance day/night cycle
    ENVIRONMENT = auto()  # Update environmental factors
    ENTITY_THINK = auto()  # AI decision making
    ENTITY_ACT = auto()  # Movement, energy consumption
    COLLISION = auto()  # Collision detection and response
    INTERACTION = auto()  # Poker, feeding, communication
    REPRODUCTION = auto()  # Mating, asexual reproduction
    LIFECYCLE = auto()  # Death processing, state transitions
    SPAWN = auto()  # Food spawning, emergency spawns
    CLEANUP = auto()  # Entity removal, pool returns
    FRAME_END = auto()  # Statistics, snapshots


# Human-readable descriptions for debugging
PHASE_DESCRIPTIONS: Dict[UpdatePhase, str] = {
    UpdatePhase.FRAME_START: "Initializing frame, resetting counters",
    UpdatePhase.TIME_UPDATE: "Advancing day/night cycle",
    UpdatePhase.ENVIRONMENT: "Updating environmental modifiers",
    UpdatePhase.ENTITY_THINK: "Entities making decisions",
    UpdatePhase.ENTITY_ACT: "Entities performing actions",
    UpdatePhase.COLLISION: "Detecting and handling collisions",
    UpdatePhase.INTERACTION: "Processing entity interactions",
    UpdatePhase.REPRODUCTION: "Handling reproduction",
    UpdatePhase.LIFECYCLE: "Processing deaths and births",
    UpdatePhase.SPAWN: "Spawning new entities",
    UpdatePhase.CLEANUP: "Removing dead entities",
    UpdatePhase.FRAME_END: "Recording statistics and snapshots",
}


@dataclass
class PhaseContext:
    """Context passed to systems during phase execution.

    This provides systems with information about the current update
    without requiring them to query global state.

    Attributes:
        frame: Current simulation frame number
        phase: Current update phase
        time_modifier: Activity modifier from time system (0.0-1.0)
        time_of_day: Current time of day (0.0-1.0, 0=midnight, 0.5=noon)
        delta_time: Time since last frame (for frame-rate independent updates)
    """

    frame: int
    phase: UpdatePhase
    time_modifier: float = 1.0
    time_of_day: float = 0.5
    delta_time: float = 1.0 / 30.0  # Assume 30 FPS default


class PhaseAware(Protocol):
    """Protocol for systems that run in specific phases."""

    @property
    def phase(self) -> UpdatePhase:
        """The phase this system runs in."""
        ...

    def update_in_phase(self, context: PhaseContext) -> None:
        """Execute the system's update for this phase."""
        ...


@dataclass
class PhaseRunner:
    """Executes systems in their designated phases.

    The PhaseRunner organizes systems by phase and executes them in
    order. Within a phase, systems run in registration order.

    Example:
        runner = PhaseRunner()

        # Register systems (order doesn't matter - sorted by phase)
        runner.register(collision_system, UpdatePhase.COLLISION)
        runner.register(time_system, UpdatePhase.TIME_UPDATE)
        runner.register(lifecycle_system, UpdatePhase.LIFECYCLE)

        # Run all phases in order
        context = runner.run_all(frame=100)

        # Or run specific phases
        runner.run_phase(UpdatePhase.COLLISION, context)
    """

    _systems_by_phase: Dict[UpdatePhase, List["BaseSystem"]] = field(
        default_factory=lambda: {phase: [] for phase in UpdatePhase}
    )
    _debug_mode: bool = False
    _current_phase: Optional[UpdatePhase] = None
    _phase_timings: Dict[UpdatePhase, float] = field(default_factory=dict)

    def register(self, system: "BaseSystem", phase: UpdatePhase) -> None:
        """Register a system to run in a specific phase.

        Args:
            system: The system to register
            phase: The phase to run in
        """
        self._systems_by_phase[phase].append(system)

    def unregister(self, system: "BaseSystem", phase: UpdatePhase) -> bool:
        """Remove a system from a phase.

        Args:
            system: The system to remove
            phase: The phase to remove from

        Returns:
            True if system was found and removed, False otherwise
        """
        systems = self._systems_by_phase[phase]
        if system in systems:
            systems.remove(system)
            return True
        return False

    def run_all(
        self,
        frame: int,
        time_modifier: float = 1.0,
        time_of_day: float = 0.5,
    ) -> PhaseContext:
        """Run all phases in order.

        Args:
            frame: Current simulation frame
            time_modifier: Activity modifier from time system
            time_of_day: Current time of day

        Returns:
            The PhaseContext used for execution
        """
        context = PhaseContext(
            frame=frame,
            phase=UpdatePhase.FRAME_START,
            time_modifier=time_modifier,
            time_of_day=time_of_day,
        )

        for phase in UpdatePhase:
            self.run_phase(phase, context)

        return context

    def run_phase(self, phase: UpdatePhase, context: PhaseContext) -> None:
        """Run all systems registered for a specific phase.

        Args:
            phase: The phase to run
            context: The execution context
        """
        import time

        context.phase = phase
        self._current_phase = phase

        if self._debug_mode:
            start_time = time.perf_counter()

        for system in self._systems_by_phase[phase]:
            if system.enabled:
                system.update(context.frame)

        if self._debug_mode:
            elapsed = time.perf_counter() - start_time
            self._phase_timings[phase] = elapsed

        self._current_phase = None

    def run_phases(
        self,
        phases: List[UpdatePhase],
        context: PhaseContext,
    ) -> None:
        """Run a subset of phases.

        Useful for testing or when you need fine-grained control.

        Args:
            phases: List of phases to run (in order given)
            context: The execution context
        """
        for phase in phases:
            self.run_phase(phase, context)

    @property
    def current_phase(self) -> Optional[UpdatePhase]:
        """Get the currently executing phase, or None if not in update."""
        return self._current_phase

    def get_systems_in_phase(self, phase: UpdatePhase) -> List["BaseSystem"]:
        """Get all systems registered for a phase."""
        return self._systems_by_phase[phase].copy()

    def enable_debug(self, enabled: bool = True) -> None:
        """Enable debug mode (tracks timing per phase)."""
        self._debug_mode = enabled

    def get_phase_timings(self) -> Dict[UpdatePhase, float]:
        """Get timing information for each phase (requires debug mode)."""
        return self._phase_timings.copy()

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the runner."""
        return {
            "current_phase": self._current_phase.name if self._current_phase else None,
            "systems_per_phase": {
                phase.name: [s.name for s in systems]
                for phase, systems in self._systems_by_phase.items()
                if systems
            },
            "timings": (
                {
                    phase.name: f"{timing*1000:.2f}ms"
                    for phase, timing in self._phase_timings.items()
                }
                if self._debug_mode
                else {}
            ),
        }


# ============================================================================
# Phase Decorators (for future use)
# ============================================================================


def runs_in_phase(phase: UpdatePhase) -> Callable:
    """Decorator to declare which phase a system runs in.

    Example:
        @runs_in_phase(UpdatePhase.COLLISION)
        class CollisionSystem(BaseSystem):
            def _do_update(self, frame: int) -> None:
                ...
    """

    def decorator(cls):
        cls._phase = phase
        return cls

    return decorator


def get_system_phase(system: "BaseSystem") -> Optional[UpdatePhase]:
    """Get the phase a system is declared to run in."""
    return getattr(system, "_phase", None)
