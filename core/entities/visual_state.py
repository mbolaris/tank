"""Visual state containers for entities."""

from __future__ import annotations


from typing import Any, Dict, Optional


class FishVisualState:
    """Transient rendering-only state for fish.

    This class encapsulates all visual effects and their timers, separating
    rendering concerns from the main entity logic.
    """

    def __init__(self) -> None:
        self.poker_effect_state: Optional[Dict[str, Any]] = None
        self.poker_effect_timer: int = 0
        self.birth_effect_timer: int = 0
        self.death_effect_state: Optional[Dict[str, Any]] = None
        self.death_effect_timer: int = 0

    def update(self) -> None:
        """Update visual effects timers."""
        # Update death visual effects (countdown)
        if self.death_effect_timer > 0:
            self.death_effect_timer -= 1

        # Update poker visual effects
        if self.poker_effect_timer > 0:
            self.poker_effect_timer -= 1
            if self.poker_effect_timer <= 0:
                self.poker_effect_state = None

        # Update birth visual effects
        if self.birth_effect_timer > 0:
            self.birth_effect_timer -= 1

    def set_poker_effect(
        self,
        status: str,
        amount: float = 0.0,
        duration: int = 15,
        target_id: Optional[int] = None,
        target_type: Optional[str] = None,
    ) -> None:
        """Set a visual effect for poker status."""
        self.poker_effect_state = {
            "status": status,
            "amount": amount,
            "target_id": target_id,
            "target_type": target_type,
        }
        self.poker_effect_timer = duration

    def set_death_effect(self, cause: str, duration: int = 45) -> None:
        """Set a visual effect for death cause."""
        self.death_effect_state = {"cause": cause}
        self.death_effect_timer = duration

    def set_birth_effect(self, duration: int = 60) -> None:
        """Set a visual effect for giving birth."""
        self.birth_effect_timer = duration
