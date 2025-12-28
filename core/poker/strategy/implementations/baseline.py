"""Baseline poker strategies (AlwaysFold, Random)."""

import random
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


@dataclass
class AlwaysFoldStrategy(PokerStrategyAlgorithm):
    """Baseline strategy: always folds to any bet, only checks if allowed."""

    def __init__(self, rng: Optional[random.Random] = None):
        super().__init__(strategy_id="always_fold", parameters={}, _rng=rng or random.Random())

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None) -> "AlwaysFoldStrategy":
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple[BettingAction, float]:
        call_amount = opponent_bet - current_bet
        if call_amount > 0:
            return (BettingAction.FOLD, 0.0)
        return (BettingAction.CHECK, 0.0)


@dataclass
class RandomStrategy(PokerStrategyAlgorithm):
    """Baseline strategy: completely random legal moves."""

    def __init__(self, rng: Optional[random.Random] = None):
        parameters = {
            "fold_prob": 0.33,
            "call_prob": 0.33,
            # Remaining probability = raise
            "min_raise_fraction": 0.3,
            "max_raise_fraction": 1.0,
        }
        super().__init__(strategy_id="random", parameters=parameters, _rng=rng or random.Random())

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple[BettingAction, float]:
        fold_prob = self.parameters.get("fold_prob", 0.33)
        call_prob = self.parameters.get("call_prob", 0.33)
        min_raise_frac = self.parameters.get("min_raise_fraction", 0.3)
        max_raise_frac = self.parameters.get("max_raise_fraction", 1.0)

        roll = self._rng.random()
        call_amount = max(0, opponent_bet - current_bet)

        if roll < fold_prob:
            # Want to fold
            if call_amount > 0:
                return (BettingAction.FOLD, 0.0)
            # Can't fold when no bet - check instead
            return (BettingAction.CHECK, 0.0)

        elif roll < fold_prob + call_prob:
            # Want to call/check
            if call_amount <= 0:
                return (BettingAction.CHECK, 0.0)
            if call_amount > player_energy:
                return (BettingAction.FOLD, 0.0)
            return (BettingAction.CALL, call_amount)

        else:
            # Want to raise
            raise_fraction = self._rng.uniform(min_raise_frac, max_raise_frac)
            raise_amount = pot * raise_fraction
            raise_amount = min(raise_amount, player_energy - call_amount)

            if raise_amount < 10:  # Minimum meaningful raise
                if call_amount <= 0:
                    return (BettingAction.CHECK, 0.0)
                if call_amount <= player_energy:
                    return (BettingAction.CALL, call_amount)
                return (BettingAction.FOLD, 0.0)

            return (BettingAction.RAISE, raise_amount)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None) -> "RandomStrategy":
        """Create instance (parameters are fixed for baseline)."""
        return cls(rng=rng)
