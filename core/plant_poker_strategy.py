"""Poker strategy adapter for fractal plants.

This module exposes a lightweight adapter that turns a PlantGenome's
poker-related traits (aggression, bluff frequency, risk tolerance)
into a BettingAction policy that implements the PokerStrategyAlgorithm
interface used throughout the fish poker code.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from core.poker.strategy.implementations import PokerStrategyAlgorithm

if TYPE_CHECKING:  # pragma: no cover
    from core.entities.plant import Plant
    from core.genetics import PlantGenome

from core.poker.betting.actions import BettingAction


class PlantPokerStrategyAdapter(PokerStrategyAlgorithm):
    """Adapts plant genome poker traits to the poker strategy interface."""

    def __init__(self, genome: PlantGenome, *, strategy_id: str = "plant_adapter") -> None:
        super().__init__(
            strategy_id=strategy_id,
            parameters={
                "aggression": genome.aggression,
                "bluff_frequency": genome.bluff_frequency,
                "risk_tolerance": genome.risk_tolerance,
            },
        )
        self._genome = genome

    @classmethod
    def from_genome(cls, genome: PlantGenome) -> PlantPokerStrategyAdapter:
        """Create a strategy adapter directly from a PlantGenome."""

        return cls(genome)

    @classmethod
    def from_plant(cls, plant: Plant) -> PlantPokerStrategyAdapter:
        """Convenience constructor that reads the genome from a plant."""

        return cls(plant.genome)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> tuple[BettingAction, float]:
        # Use provided RNG or create a fallback
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")

        call_amount = max(0.0, opponent_bet - current_bet)
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        aggression = self.parameters["aggression"]
        bluff_frequency = self.parameters["bluff_frequency"]
        risk_tolerance = self.parameters["risk_tolerance"]

        # Adjust perceived hand strength based on position and aggression
        adjusted_strength = hand_strength
        if position_on_button:
            adjusted_strength += 0.05 + aggression * 0.1
            adjusted_strength = min(1.0, adjusted_strength)

        # Dynamic thresholds derived from genome traits
        fold_threshold = max(0.05, 0.3 - (risk_tolerance - 0.5) * 0.2)
        raise_threshold = min(0.95, 0.55 + aggression * 0.35)
        call_threshold = fold_threshold + (raise_threshold - fold_threshold) * (
            0.4 + risk_tolerance * 0.4
        )

        if adjusted_strength < fold_threshold:
            # Allow occasional bluffs that leverage bluff_frequency and aggression
            if _rng.random() < bluff_frequency * (0.8 + aggression * 0.4):
                raise_amt = pot * (0.3 + aggression * 0.6)
                raise_amt = min(raise_amt, player_energy * 0.2)
                if raise_amt > 0:
                    return (BettingAction.RAISE, raise_amt)
            return (BettingAction.CHECK, 0.0) if call_amount == 0 else (BettingAction.FOLD, 0.0)

        if adjusted_strength >= raise_threshold:
            base_multiplier = 0.4 + aggression * 0.8
            raise_amt = pot * base_multiplier
            raise_amt = max(raise_amt, call_amount * (1.2 + risk_tolerance * 0.8))
            raise_amt = min(raise_amt, player_energy * 0.45)
            return (BettingAction.RAISE, raise_amt)

        if adjusted_strength >= call_threshold:
            if call_amount == 0:
                # Semi-bluff when we have initiative and aggression is high
                if _rng.random() < aggression * 0.3:
                    raise_amt = min(pot * 0.35, player_energy * 0.15)
                    if raise_amt > 0:
                        return (BettingAction.RAISE, raise_amt)
                return (BettingAction.CHECK, 0.0)
            return (BettingAction.CALL, call_amount)

        # Marginal hands: check when possible, otherwise consider pot odds before folding
        if call_amount == 0:
            return (BettingAction.CHECK, 0.0)

        # Calculate pot odds - call if the hand has enough equity
        pot_odds = call_amount / (pot + call_amount) if pot > 0 else 0.5
        # Marginal hands should call if pot odds are favorable (adjusted by risk tolerance)
        # Higher risk tolerance = more willing to call with marginal hands
        pot_odds_threshold = pot_odds - (risk_tolerance - 0.3) * 0.15
        if adjusted_strength > pot_odds_threshold and call_amount <= player_energy:
            return (BettingAction.CALL, call_amount)

        return (BettingAction.FOLD, 0.0)
