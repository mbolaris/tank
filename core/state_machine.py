"""State machine abstractions for explicit state management.

This module provides tools for creating explicit state machines where:
- All valid states are enumerated
- Valid transitions are defined explicitly
- Invalid transitions are caught immediately (fail-fast)
- State history can be tracked for debugging

Why State Machines?
-------------------
Before (implicit state):
    class Fish:
        def __init__(self):
            self.age = 0
            self.life_stage = LifeStage.BABY

        def update(self):
            self.age += 1
            # Bug: nothing prevents ELDER -> BABY transition!
            if self.age < 100:
                self.life_stage = LifeStage.BABY

After (explicit state machine):
    class Fish:
        def __init__(self):
            self._lifecycle = LifecycleStateMachine()

        def update(self):
            result = self._lifecycle.try_transition(LifeStage.JUVENILE)
            if result.is_err():
                # Invalid transition caught immediately!
                logger.warning(f"Invalid transition: {result.error}")

Benefits:
- Invalid states are impossible (type system enforces valid values)
- Invalid transitions are caught immediately with clear error messages
- State history aids debugging
- Self-documenting: transitions show valid flows

Usage:
------
    # Define states as an Enum
    class DoorState(Enum):
        OPEN = "open"
        CLOSED = "closed"
        LOCKED = "locked"

    # Define valid transitions
    transitions = {
        DoorState.OPEN: [DoorState.CLOSED],
        DoorState.CLOSED: [DoorState.OPEN, DoorState.LOCKED],
        DoorState.LOCKED: [DoorState.CLOSED],
    }

    # Create state machine
    door = StateMachine(DoorState.CLOSED, transitions)

    # Transition
    door.transition(DoorState.OPEN)  # OK
    door.transition(DoorState.LOCKED)  # Raises! Can't go OPEN -> LOCKED
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Generic, List, TypeVar

from core.result import Err, Ok, Result

# Type variable for state enum types
S = TypeVar("S", bound=Enum)


@dataclass
class StateTransition(Generic[S]):
    """Record of a state transition for debugging.

    Attributes:
        from_state: The state before transition
        to_state: The state after transition
        frame: The simulation frame when transition occurred
        reason: Optional description of why transition happened
    """

    from_state: S
    to_state: S
    frame: int
    reason: str = ""


class StateMachine(Generic[S]):
    """A generic state machine with explicit transition validation.

    This class enforces that only valid state transitions can occur.
    Invalid transitions are caught immediately with clear error messages.

    Example:
        class LightState(Enum):
            OFF = auto()
            ON = auto()
            DIMMED = auto()

        transitions = {
            LightState.OFF: [LightState.ON],
            LightState.ON: [LightState.OFF, LightState.DIMMED],
            LightState.DIMMED: [LightState.ON, LightState.OFF],
        }

        light = StateMachine(LightState.OFF, transitions)
        light.transition(LightState.ON)  # OK
        print(light.state)  # LightState.ON
    """

    def __init__(
        self,
        initial_state: S,
        valid_transitions: Dict[S, List[S]],
        track_history: bool = False,
        max_history: int = 100,
    ) -> None:
        """Initialize the state machine.

        Args:
            initial_state: The starting state
            valid_transitions: Map of state -> list of valid target states
            track_history: Whether to record transition history
            max_history: Maximum number of transitions to keep in history
        """
        self._state = initial_state
        self._transitions = valid_transitions
        self._track_history = track_history
        self._max_history = max_history
        self._history: List[StateTransition[S]] = []
        self._current_frame = 0

        # Validate that initial state is in the transition map
        if initial_state not in valid_transitions:
            raise ValueError(
                f"Initial state {initial_state} not in valid_transitions. "
                f"Valid states: {list(valid_transitions.keys())}"
            )

    @property
    def state(self) -> S:
        """Get the current state."""
        return self._state

    @property
    def history(self) -> List[StateTransition[S]]:
        """Get transition history (empty if tracking disabled)."""
        return self._history.copy()

    def can_transition(self, target: S) -> bool:
        """Check if transition to target state is valid.

        Args:
            target: The desired target state

        Returns:
            True if transition is valid, False otherwise
        """
        valid_targets = self._transitions.get(self._state, [])
        return target in valid_targets

    def try_transition(self, target: S, frame: int = 0, reason: str = "") -> Result[S, str]:
        """Attempt to transition to a new state.

        Returns Ok(new_state) if successful, Err(message) if invalid.

        Args:
            target: The desired target state
            frame: The current simulation frame (for history)
            reason: Why this transition is happening (for debugging)

        Returns:
            Result containing new state on success, error message on failure
        """
        if not self.can_transition(target):
            valid_targets = self._transitions.get(self._state, [])
            return Err(
                f"Invalid transition: {self._state.name} -> {target.name}. "
                f"Valid targets from {self._state.name}: {[t.name for t in valid_targets]}"
            )

        old_state = self._state
        self._state = target

        if self._track_history:
            self._record_transition(old_state, target, frame, reason)

        return Ok(target)

    def transition(self, target: S, frame: int = 0, reason: str = "") -> S:
        """Transition to a new state, raising on invalid transition.

        Use this when an invalid transition is a programming error that
        should never happen. Use try_transition() when the transition
        might legitimately fail.

        Args:
            target: The desired target state
            frame: The current simulation frame (for history)
            reason: Why this transition is happening (for debugging)

        Returns:
            The new state

        Raises:
            ValueError: If the transition is invalid
        """
        result = self.try_transition(target, frame, reason)
        if result.is_err():
            raise ValueError(result.error)
        return result.unwrap()

    def force_state(self, state: S, frame: int = 0, reason: str = "forced") -> None:
        """Force a state change without validation.

        Use sparingly! This bypasses transition rules and should only be
        used for special cases like loading saved state or testing.

        Args:
            state: The state to force
            frame: The current simulation frame
            reason: Why this force is happening
        """
        old_state = self._state
        self._state = state

        if self._track_history:
            self._record_transition(old_state, state, frame, f"[FORCED] {reason}")

    def _record_transition(self, from_state: S, to_state: S, frame: int, reason: str) -> None:
        """Record a transition in history."""
        self._history.append(
            StateTransition(
                from_state=from_state,
                to_state=to_state,
                frame=frame,
                reason=reason,
            )
        )

        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_valid_transitions(self) -> List[S]:
        """Get list of valid target states from current state."""
        return list(self._transitions.get(self._state, []))

    def __repr__(self) -> str:
        return f"StateMachine(state={self._state.name})"


# ============================================================================
# Fish Lifecycle State Machine
# ============================================================================


class LifeStage(Enum):
    """Life stages for fish entities.

    This enum represents the distinct life stages a fish goes through.
    Each stage affects metabolism, reproduction ability, and behavior.

    Note: Values are strings for backward compatibility with existing code.
    """

    BABY = "baby"  # Just born, cannot reproduce
    JUVENILE = "juvenile"  # Growing, cannot reproduce
    ADULT = "adult"  # Prime of life, can reproduce
    ELDER = "elder"  # Final stage before natural death


# Valid life stage transitions (fish can only progress forward)
# Note: Death is handled separately via is_dead() check, not as a state transition
LIFE_STAGE_TRANSITIONS: Dict[LifeStage, List[LifeStage]] = {
    LifeStage.BABY: [LifeStage.JUVENILE],
    LifeStage.JUVENILE: [LifeStage.ADULT],
    LifeStage.ADULT: [LifeStage.ELDER],
    LifeStage.ELDER: [],  # Terminal living state (death handled separately)
}


def create_lifecycle_state_machine(track_history: bool = False) -> StateMachine[LifeStage]:
    """Create a state machine for fish lifecycle management.

    Args:
        track_history: Whether to track transition history (useful for debugging)

    Returns:
        A StateMachine configured for fish lifecycle stages
    """
    return StateMachine(
        initial_state=LifeStage.BABY,
        valid_transitions=LIFE_STAGE_TRANSITIONS,
        track_history=track_history,
    )


# ============================================================================
# Entity State Machine (for general entity lifecycle)
# ============================================================================


class EntityState(Enum):
    """General entity lifecycle states.

    These states apply to any entity (fish, plant, food) and represent
    their lifecycle from creation to removal.
    """

    INITIALIZING = auto()  # Being created
    ACTIVE = auto()  # Normal operation
    DYING = auto()  # In process of dying (e.g., playing death animation)
    DEAD = auto()  # Ready for removal
    REMOVED = auto()  # Removed from simulation


ENTITY_STATE_TRANSITIONS: Dict[EntityState, List[EntityState]] = {
    EntityState.INITIALIZING: [EntityState.ACTIVE, EntityState.DEAD],
    EntityState.ACTIVE: [EntityState.DYING, EntityState.DEAD, EntityState.REMOVED],
    EntityState.DYING: [EntityState.DEAD],
    EntityState.DEAD: [EntityState.REMOVED],
    EntityState.REMOVED: [],  # Terminal state
}


def create_entity_state_machine(track_history: bool = False) -> StateMachine[EntityState]:
    """Create a state machine for general entity lifecycle.

    Args:
        track_history: Whether to track transition history

    Returns:
        A StateMachine configured for entity lifecycle states
    """
    return StateMachine(
        initial_state=EntityState.INITIALIZING,
        valid_transitions=ENTITY_STATE_TRANSITIONS,
        track_history=track_history,
    )


# ============================================================================
# Poker Game State Machine
# ============================================================================


class PokerGameState(Enum):
    """States for a poker game in progress."""

    WAITING_FOR_PLAYERS = auto()  # Game not yet started
    DEALING = auto()  # Dealing cards
    PREFLOP = auto()  # Before community cards
    FLOP = auto()  # First 3 community cards
    TURN = auto()  # 4th community card
    RIVER = auto()  # 5th community card
    SHOWDOWN = auto()  # Comparing hands
    COMPLETE = auto()  # Game finished


POKER_GAME_TRANSITIONS: Dict[PokerGameState, List[PokerGameState]] = {
    PokerGameState.WAITING_FOR_PLAYERS: [PokerGameState.DEALING],
    PokerGameState.DEALING: [PokerGameState.PREFLOP],
    PokerGameState.PREFLOP: [PokerGameState.FLOP, PokerGameState.SHOWDOWN],
    PokerGameState.FLOP: [PokerGameState.TURN, PokerGameState.SHOWDOWN],
    PokerGameState.TURN: [PokerGameState.RIVER, PokerGameState.SHOWDOWN],
    PokerGameState.RIVER: [PokerGameState.SHOWDOWN],
    PokerGameState.SHOWDOWN: [PokerGameState.COMPLETE],
    PokerGameState.COMPLETE: [],  # Terminal state
}


def create_poker_state_machine(track_history: bool = True) -> StateMachine[PokerGameState]:
    """Create a state machine for poker game flow.

    Args:
        track_history: Whether to track transition history (default True for debugging)

    Returns:
        A StateMachine configured for poker game states
    """
    return StateMachine(
        initial_state=PokerGameState.WAITING_FOR_PLAYERS,
        valid_transitions=POKER_GAME_TRANSITIONS,
        track_history=track_history,
    )
