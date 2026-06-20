"""Update phase definitions for explicit execution ordering.

This module defines the phases of a simulation update tick. The phases give the
engine a single, ordered vocabulary for "what happens when" during a frame.

Why Explicit Phases?
--------------------
Before (implicit ordering):
    def update(self):
        self.time_system.update(self.frame)
        self.handle_collisions()  # before or after entities?
        for entity in entities:
            entity.update()
        self.handle_reproduction()  # before or after deaths?
        self.spawn_food()

After (explicit, named phases):
    def update(self):
        self._phase_frame_start()
        self._phase_time_update()
        self._phase_environment()
        ...                        # one ordered, named method per phase

Benefits:
- Execution order is explicit and documented
- Easy to add new systems to the correct phase
- Debugging: "what phase are we in?"
- Testing: phases can be reasoned about in isolation
- Self-documenting code

How phases are executed
-----------------------
``SimulationEngine`` drives the loop with explicit, named ``_phase_*`` methods
(see ``core/simulation/phase_executor.py``). ``UpdatePhase`` is the shared
vocabulary those methods, the pipeline, and debugging tools agree on; systems
annotate the phase they belong to with :func:`runs_in_phase` for documentation
and introspection.

Usage:
------
    @runs_in_phase(UpdatePhase.COLLISION)
    class CollisionSystem(BaseSystem):
        def _do_update(self, frame: int) -> SystemResult:
            ...
"""

from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING

# Explicit public API
__all__ = [
    "UpdatePhase",
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
PHASE_DESCRIPTIONS: dict[UpdatePhase, str] = {
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


# ============================================================================
# Phase Annotations
# ============================================================================


def runs_in_phase(phase: UpdatePhase) -> Callable:
    """Decorator to declare which phase a system runs in.

    The annotation documents intent and enables introspection via
    :func:`get_system_phase`; the engine's explicit ``_phase_*`` methods own
    the actual ordering.

    Example:
        @runs_in_phase(UpdatePhase.COLLISION)
        class CollisionSystem(BaseSystem):
            def _do_update(self, frame: int) -> SystemResult:
                return SystemResult.empty()
    """

    def decorator(cls):
        cls._phase = phase
        return cls

    return decorator


def get_system_phase(system: "BaseSystem") -> UpdatePhase | None:
    """Get the phase a system is declared to run in."""
    phase = getattr(system, "_phase", None)
    return phase if isinstance(phase, UpdatePhase) else None
