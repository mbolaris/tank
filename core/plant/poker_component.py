"""Poker gameplay component for plants.

This module provides the PlantPokerComponent class which handles all poker-related
functionality for plants.
"""

import logging
from typing import TYPE_CHECKING, Callable, Optional

from core.config.plants import PLANT_MIN_POKER_ENERGY

if TYPE_CHECKING:
    from core.genetics import PlantGenome
    from core.world import World

logger = logging.getLogger(__name__)


class PlantPokerComponent:
    """Manages plant poker gameplay capabilities.

    This component encapsulates all poker-related logic for a plant, including:
    - Poker eligibility checks
    - Poker strategy retrieval
    - Visual effect state for poker outcomes
    - Statistics tracking

    Attributes:
        poker_cooldown: Frames until can play poker again.
        poker_wins: Count of poker games won.
        poker_losses: Count of poker games lost.
        last_button_position: Last dealer button position.
        poker_effect_state: Current visual effect state.
        poker_effect_timer: Remaining frames for effect display.
    """

    __slots__ = (
        "_get_energy",
        "_get_environment",
        "_get_genome",
        "_is_dead",
        "_plant_id",
        "last_button_position",
        "poker_cooldown",
        "poker_effect_state",
        "poker_effect_timer",
        "poker_losses",
        "poker_wins",
    )

    def __init__(
        self,
        plant_id: int,
        get_energy: Callable[[], float],
        get_genome: Callable[[], "PlantGenome"],
        get_environment: Callable[[], "World"],
        is_dead: Callable[[], bool],
    ) -> None:
        """Initialize the poker component.

        Args:
            plant_id: The plant's unique identifier.
            get_energy: Callback to get current energy.
            get_genome: Callback to get the plant's genome.
            get_environment: Callback to get the environment.
            is_dead: Callback to check if plant is dead.
        """
        self.poker_cooldown = 0
        self.poker_wins = 0
        self.poker_losses = 0
        self.last_button_position = 2
        self.poker_effect_state: Optional[dict] = None
        self.poker_effect_timer = 0
        self._get_energy = get_energy
        self._get_genome = get_genome
        self._get_environment = get_environment
        self._is_dead = is_dead
        self._plant_id = plant_id

    def update(self) -> None:
        """Update cooldown and effect timers."""
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1

        if self.poker_effect_timer > 0:
            self.poker_effect_timer -= 1
            if self.poker_effect_timer <= 0:
                self.poker_effect_state = None

    def can_play_poker(self) -> bool:
        """Check if plant can play poker.

        Returns:
            True if poker game can proceed.
        """
        if self._is_dead():
            return False
        if self._get_energy() < PLANT_MIN_POKER_ENERGY:
            return False
        if self.poker_cooldown > 0:
            return False
        return True

    def get_poker_aggression(self) -> float:
        """Get poker aggression level.

        Returns:
            Aggression value for poker decisions (0.0-1.0).
        """
        return self._get_genome().aggression

    def get_poker_strategy(self):
        """Get poker strategy for this plant.

        If this plant has a strategy_type set (baseline strategy plant),
        returns the corresponding baseline poker strategy implementation.
        Otherwise falls back to the genome-based adapter.

        Returns:
            PokerStrategyAlgorithm: Either a baseline strategy or PlantPokerStrategyAdapter.
        """
        genome = self._get_genome()

        # Check if this is a baseline strategy plant
        if genome.strategy_type is not None:
            from core.plants.plant_strategy_types import (
                PlantStrategyType,
                get_poker_strategy_for_type,
            )

            try:
                strategy_type = PlantStrategyType(genome.strategy_type)
                # Use environment RNG if available for determinism
                rng = getattr(self._get_environment(), "rng", None)
                return get_poker_strategy_for_type(strategy_type, rng=rng)
            except ValueError:
                pass  # Fall through to genome-based strategy

        # Fall back to genome-based strategy (legacy behavior)
        from core.plant_poker_strategy import PlantPokerStrategyAdapter

        return PlantPokerStrategyAdapter(genome)

    def get_poker_id(self) -> int:
        """Get stable ID for poker tracking.

        Returns:
            plant_id offset by 100000 to avoid collision with fish IDs.
        """
        return self._plant_id + 100000

    def set_poker_effect(
        self,
        status: str,
        amount: float = 0.0,
        duration: int = 15,
        target_id: Optional[int] = None,
        target_type: Optional[str] = None,
    ) -> None:
        """Set a visual effect for poker status.

        Args:
            status: 'playing', 'won', 'lost', 'tie'.
            amount: Amount won or lost (for display).
            duration: How long to show the effect in frames.
            target_id: ID of the opponent/target entity (for drawing arrows).
            target_type: Type of the opponent/target entity ('fish', 'plant').
        """
        self.poker_effect_state = {
            "status": status,
            "amount": amount,
            "target_id": target_id,
            "target_type": target_type,
        }
        self.poker_effect_timer = duration

    def record_win(self) -> None:
        """Record a poker win."""
        self.poker_wins += 1

    def record_loss(self) -> None:
        """Record a poker loss."""
        self.poker_losses += 1
