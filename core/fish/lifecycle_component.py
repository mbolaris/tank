"""Lifecycle management component for fish.

This module provides the LifecycleComponent class which handles all lifecycle-related
functionality for fish, including aging, life stage transitions, and size changes.
Separating lifecycle logic into its own component improves code organization and testability.
"""

from typing import TYPE_CHECKING
from core.constants import (
    LIFE_STAGE_BABY_MAX,
    LIFE_STAGE_JUVENILE_MAX,
    LIFE_STAGE_YOUNG_ADULT_MAX,
    LIFE_STAGE_ADULT_MAX,
    LIFE_STAGE_MATURE_MAX,
    FISH_BABY_SIZE,
    FISH_ADULT_SIZE
)

if TYPE_CHECKING:
    from core.entities import LifeStage


class LifecycleComponent:
    """Manages fish lifecycle, including aging and life stage transitions.

    This component encapsulates all lifecycle-related logic for a fish, including:
    - Age tracking and incrementing
    - Life stage transitions based on age
    - Size calculations based on life stage
    - Maximum age/lifespan management

    Attributes:
        age: Current age in frames
        max_age: Maximum lifespan in frames
        life_stage: Current life stage (BABY, JUVENILE, ADULT, ELDER)
        size: Current visual size multiplier
    """

    def __init__(self, max_age: int):
        """Initialize the lifecycle component.

        Args:
            max_age: Maximum lifespan in frames (affected by genetics)
        """
        self.age: int = 0
        self.max_age: int = max_age

        # Import here to avoid circular dependency
        from core.entities import LifeStage
        self.life_stage: 'LifeStage' = LifeStage.BABY
        self.size: float = FISH_BABY_SIZE

    def increment_age(self) -> None:
        """Increment age by one frame and update life stage."""
        self.age += 1
        self.update_life_stage()

    def update_life_stage(self) -> None:
        """Update life stage and size based on current age."""
        from core.entities import LifeStage

        if self.age < LIFE_STAGE_BABY_MAX:
            self.life_stage = LifeStage.BABY
            # Grow from 0.5 to 1.0 as baby ages
            self.size = FISH_BABY_SIZE + (FISH_ADULT_SIZE - FISH_BABY_SIZE) * (self.age / LIFE_STAGE_BABY_MAX)
        elif self.age < LIFE_STAGE_JUVENILE_MAX:
            self.life_stage = LifeStage.JUVENILE
            self.size = FISH_ADULT_SIZE
        elif self.age < LIFE_STAGE_ADULT_MAX:
            self.life_stage = LifeStage.ADULT
            self.size = FISH_ADULT_SIZE
        else:
            self.life_stage = LifeStage.ELDER
            self.size = FISH_ADULT_SIZE

    def is_baby(self) -> bool:
        """Check if fish is in baby stage.

        Returns:
            bool: True if in BABY life stage
        """
        from core.entities import LifeStage
        return self.life_stage == LifeStage.BABY

    def is_juvenile(self) -> bool:
        """Check if fish is in juvenile stage.

        Returns:
            bool: True if in JUVENILE life stage
        """
        from core.entities import LifeStage
        return self.life_stage == LifeStage.JUVENILE

    def is_adult(self) -> bool:
        """Check if fish is in adult stage.

        Returns:
            bool: True if in ADULT life stage
        """
        from core.entities import LifeStage
        return self.life_stage == LifeStage.ADULT

    def is_elder(self) -> bool:
        """Check if fish is in elder stage.

        Returns:
            bool: True if in ELDER life stage
        """
        from core.entities import LifeStage
        return self.life_stage == LifeStage.ELDER

    def is_dying_of_old_age(self) -> bool:
        """Check if fish has reached or exceeded maximum age.

        Returns:
            bool: True if age >= max_age
        """
        return self.age >= self.max_age

    def get_age_ratio(self) -> float:
        """Get current age as a ratio of maximum age.

        This is useful for decision-making and aging-related calculations.

        Returns:
            float: Age ratio between 0.0 (newborn) and 1.0+ (at/past max age)
        """
        return self.age / self.max_age if self.max_age > 0 else 0.0

    def get_life_stage_name(self) -> str:
        """Get human-readable name of current life stage.

        Returns:
            str: Life stage name (e.g., "Baby", "Adult", "Elder")
        """
        return self.life_stage.value.capitalize()
