"""Lifecycle management component for fish.

This module provides the LifecycleComponent class which handles all lifecycle-related
functionality for fish, including aging, life stage transitions, and size changes.
Separating lifecycle logic into its own component improves code organization and testability.

Architecture Notes:
- Uses StateMachine from core.state_machine for validated state transitions
- Invalid transitions (e.g., ELDER -> BABY) are caught immediately
- Transition history can be enabled for debugging
"""

import logging
from typing import TYPE_CHECKING, List, Optional

from core.constants import (
    FISH_ADULT_SIZE,
    FISH_BABY_SIZE,
    LIFE_STAGE_ADULT_MAX,
    LIFE_STAGE_BABY_MAX,
    LIFE_STAGE_JUVENILE_MAX,
)
from core.state_machine import (
    LifeStage,
    StateMachine,
    StateTransition,
    LIFE_STAGE_TRANSITIONS,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LifecycleComponent:
    """Manages fish lifecycle, including aging and life stage transitions.

    This component encapsulates all lifecycle-related logic for a fish, including:
    - Age tracking and incrementing
    - Life stage transitions based on age (with validation via StateMachine)
    - Size calculations based on life stage and genetics
    - Maximum age/lifespan management

    The StateMachine ensures only valid transitions occur:
    - BABY -> JUVENILE -> ADULT -> ELDER (forward only)
    - Invalid transitions (e.g., ELDER -> BABY) raise errors immediately

    Attributes:
        age: Current age in frames.
        max_age: Maximum lifespan in frames.
        life_stage: Current life stage (BABY, JUVENILE, ADULT, ELDER).
        size: Current visual size multiplier (combines age and genetic factors).
        genetic_size_modifier: Genetic body size trait (0.5-2.0).
    """

    __slots__ = ("age", "max_age", "genetic_size_modifier", "_state_machine", "size", "_track_history")

    def __init__(
        self,
        max_age: int,
        genetic_size_modifier: float = 1.0,
        track_history: bool = False,
    ) -> None:
        """Initialize the lifecycle component.

        Args:
            max_age: Maximum lifespan in frames (affected by genetics).
            genetic_size_modifier: Genetic body size multiplier (0.5-2.0).
            track_history: If True, track state transition history for debugging.
        """
        self.age: int = 0
        self.max_age: int = max_age
        self.genetic_size_modifier: float = genetic_size_modifier
        self._track_history: bool = track_history

        # Use StateMachine for validated state transitions
        self._state_machine: StateMachine[LifeStage] = StateMachine(
            initial_state=LifeStage.BABY,
            valid_transitions=LIFE_STAGE_TRANSITIONS,
            track_history=track_history,
        )
        self.size: float = FISH_BABY_SIZE * genetic_size_modifier

    def increment_age(self, frame: int = 0) -> None:
        """Increment age by one frame and update life stage.

        Args:
            frame: Current simulation frame (used for transition history).
        """
        self.age += 1
        self._update_life_stage(frame)

    def _update_life_stage(self, frame: int = 0) -> None:
        """Update life stage and size based on current age and genetics.

        Uses StateMachine for validated transitions. Invalid transitions
        (e.g., going backward in life stages) will log a warning.

        Args:
            frame: Current simulation frame (for transition history).
        """
        current_stage = self._state_machine.state

        # Determine target stage based on age
        if self.age < LIFE_STAGE_BABY_MAX:
            target_stage = LifeStage.BABY
            # Grow from 0.5 to 1.0 as baby ages
            base_size = FISH_BABY_SIZE + (FISH_ADULT_SIZE - FISH_BABY_SIZE) * (
                self.age / LIFE_STAGE_BABY_MAX
            )
        elif self.age < LIFE_STAGE_JUVENILE_MAX:
            target_stage = LifeStage.JUVENILE
            base_size = FISH_ADULT_SIZE
        elif self.age < LIFE_STAGE_ADULT_MAX:
            target_stage = LifeStage.ADULT
            base_size = FISH_ADULT_SIZE
        else:
            target_stage = LifeStage.ELDER
            base_size = FISH_ADULT_SIZE

        # Attempt transition if stage changed (StateMachine validates it)
        if target_stage != current_stage:
            result = self._state_machine.try_transition(
                target_stage,
                frame=frame,
                reason=f"aged to {self.age} frames",
            )
            if result.is_err():
                # Log but don't crash - this catches bugs in age calculation
                logger.warning(f"Lifecycle transition failed: {result.error}")

        # Apply genetic size modifier to get final size
        self.size = base_size * self.genetic_size_modifier

    # Legacy method name for backward compatibility
    def update_life_stage(self) -> None:
        """Update life stage (legacy method, prefer _update_life_stage)."""
        self._update_life_stage(frame=0)

    @property
    def life_stage(self) -> LifeStage:
        """Current life stage (from state machine)."""
        return self._state_machine.state

    @property
    def current_stage(self) -> LifeStage:
        """Alias for life_stage for backward compatibility."""
        return self._state_machine.state

    @current_stage.setter
    def current_stage(self, value: LifeStage) -> None:
        """Set life_stage via current_stage alias (forces transition)."""
        if value != self._state_machine.state:
            # Force the state for backward compatibility
            self._state_machine.force_state(value, reason="direct assignment")

    def is_baby(self) -> bool:
        """Check if fish is in baby stage.

        Returns:
            True if in BABY life stage.
        """
        return self._state_machine.state == LifeStage.BABY

    def is_juvenile(self) -> bool:
        """Check if fish is in juvenile stage.

        Returns:
            True if in JUVENILE life stage.
        """
        return self._state_machine.state == LifeStage.JUVENILE

    def is_adult(self) -> bool:
        """Check if fish is in adult stage.

        Returns:
            True if in ADULT life stage.
        """
        return self._state_machine.state == LifeStage.ADULT

    def is_elder(self) -> bool:
        """Check if fish is in elder stage.

        Returns:
            True if in ELDER life stage.
        """
        return self._state_machine.state == LifeStage.ELDER

    def is_dying_of_old_age(self) -> bool:
        """Check if fish has reached or exceeded maximum age.

        Returns:
            True if age >= max_age.
        """
        return self.age >= self.max_age

    def get_age_ratio(self) -> float:
        """Get current age as a ratio of maximum age.

        This is useful for decision-making and aging-related calculations.

        Returns:
            Age ratio between 0.0 (newborn) and 1.0+ (at/past max age).
        """
        return self.age / self.max_age if self.max_age > 0 else 0.0

    def get_life_stage_name(self) -> str:
        """Get human-readable name of current life stage.

        Returns:
            Life stage name (e.g., "Baby", "Adult", "Elder").
        """
        return self._state_machine.state.value.capitalize()

    def get_transition_history(self) -> List[StateTransition[LifeStage]]:
        """Get life stage transition history (if tracking enabled).

        Returns:
            List of StateTransition objects, empty if tracking disabled.
        """
        return self._state_machine.history

    def get_valid_next_stages(self) -> List[LifeStage]:
        """Get valid next life stages from current state.

        Useful for debugging and understanding lifecycle flow.

        Returns:
            List of valid next LifeStage values.
        """
        return self._state_machine.get_valid_transitions()
