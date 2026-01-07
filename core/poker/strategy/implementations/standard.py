"""Standard poker strategies (TAG, LAG, etc)."""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

from core.config.poker import (
    POKER_LAG_ENERGY_FRACTION,
    POKER_PREFLOP_MAX_ENERGY_FRACTION,
    POKER_PREFLOP_MIN_RAISE_MULTIPLIER,
)
from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


@dataclass
class TightAggressiveStrategy(PokerStrategyAlgorithm):
    """TAG: Plays few hands aggressively."""

    def __init__(self, rng: Optional[random.Random] = None):
        if rng is None:
            raise RuntimeError("TightAggressiveStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="tight_aggressive",
            parameters={
                "weak_fold_threshold": _rng.uniform(0.3, 0.5),
                "strong_raise_threshold": _rng.uniform(0.6, 0.8),
                "value_raise_multiplier": _rng.uniform(0.5, 1.0),
                "bluff_frequency": _rng.uniform(0.05, 0.15),
                "position_bonus": _rng.uniform(0.05, 0.15),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        _rng = rng or self._rng

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_bonus"]
            hand_strength = min(1.0, hand_strength)

        if hand_strength < self.parameters["weak_fold_threshold"]:
            if _rng.random() < self.parameters["bluff_frequency"]:
                bluff = min(pot * 0.5, player_energy * 0.2)
                return (BettingAction.RAISE, bluff)
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["strong_raise_threshold"]:
            raise_amt = pot * self.parameters["value_raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            raise_amt = max(raise_amt, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER)
            return (BettingAction.RAISE, raise_amt)

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class LooseAggressiveStrategy(PokerStrategyAlgorithm):
    """LAG: Plays many hands aggressively."""

    def __init__(self, rng: Optional[random.Random] = None):
        if rng is None:
            raise RuntimeError("LooseAggressiveStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="loose_aggressive",
            parameters={
                "weak_fold_threshold": _rng.uniform(0.15, 0.30),
                "raise_threshold": _rng.uniform(0.4, 0.6),
                "raise_multiplier": _rng.uniform(0.7, 1.5),
                "bluff_frequency": _rng.uniform(0.25, 0.45),
                "position_aggression": _rng.uniform(0.1, 0.25),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        _rng = rng or self._rng

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_aggression"]

        if call_amount == 0 and hand_strength > 0.2:
            raise_amt = pot * self.parameters["raise_multiplier"]
            return (BettingAction.RAISE, min(raise_amt, player_energy * POKER_LAG_ENERGY_FRACTION))

        if hand_strength < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        if _rng.random() < self.parameters["bluff_frequency"]:
            bluff = pot * _rng.uniform(0.5, 1.2)
            return (
                BettingAction.RAISE,
                min(bluff, player_energy * POKER_PREFLOP_MAX_ENERGY_FRACTION),
            )

        if hand_strength >= self.parameters["raise_threshold"]:
            raise_amt = pot * self.parameters["raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            return (
                BettingAction.RAISE,
                max(raise_amt, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER),
            )

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class TightPassiveStrategy(PokerStrategyAlgorithm):
    """Rock: Plays few hands, rarely raises."""

    def __init__(self, rng: Optional[random.Random] = None):
        # Inline RNG check
        if rng is None:
            raise RuntimeError("TightPassiveStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="tight_passive",
            parameters={
                "weak_fold_threshold": _rng.uniform(0.4, 0.6),
                "raise_threshold": _rng.uniform(0.75, 0.90),
                "call_threshold": _rng.uniform(0.35, 0.55),
                "raise_multiplier": _rng.uniform(0.3, 0.6),
                "bluff_frequency": _rng.uniform(0.01, 0.05),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if hand_strength < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["raise_threshold"]:
            raise_amt = pot * self.parameters["raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.25)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.3))

        if hand_strength >= self.parameters["call_threshold"]:
            if call_amount == 0:
                return (BettingAction.CHECK, 0.0)
            pot_odds = call_amount / (pot + call_amount) if pot > 0 else 1.0
            if hand_strength > pot_odds * 1.5:
                return (BettingAction.CALL, call_amount)

        return (BettingAction.CHECK, 0.0) if call_amount == 0 else (BettingAction.FOLD, 0.0)


@dataclass
class BalancedStrategy(PokerStrategyAlgorithm):
    """Balanced/GTO-inspired strategy."""

    def __init__(self, rng: Optional[random.Random] = None):
        if rng is None:
            raise RuntimeError("BalancedStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="balanced",
            parameters={
                "weak_fold_threshold": _rng.uniform(0.25, 0.40),
                "medium_threshold": _rng.uniform(0.45, 0.60),
                "strong_threshold": _rng.uniform(0.70, 0.85),
                "value_raise_multiplier": _rng.uniform(0.5, 0.9),
                "bluff_multiplier": _rng.uniform(0.4, 0.8),
                "bluff_frequency": _rng.uniform(0.15, 0.30),
                "position_bonus": _rng.uniform(0.08, 0.18),
                "pot_odds_factor": _rng.uniform(1.2, 1.8),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        _rng = rng or self._rng

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_bonus"]
            hand_strength = min(1.0, hand_strength)

        pot_odds = call_amount / (pot + call_amount) if pot > 0 and call_amount > 0 else 0.0

        if hand_strength < self.parameters["weak_fold_threshold"]:
            if pot_odds > 0 and hand_strength > pot_odds * self.parameters["pot_odds_factor"]:
                return (
                    (BettingAction.CALL, call_amount)
                    if call_amount > 0
                    else (BettingAction.CHECK, 0.0)
                )
            if _rng.random() < self.parameters["bluff_frequency"] * 0.5:
                bluff = pot * self.parameters["bluff_multiplier"]
                return (BettingAction.RAISE, min(bluff, player_energy * 0.25))
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["strong_threshold"]:
            raise_amt = pot * self.parameters["value_raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.40)
            return (
                BettingAction.RAISE,
                max(raise_amt, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER),
            )

        if hand_strength >= self.parameters["medium_threshold"]:
            if _rng.random() < 0.4:
                raise_amt = pot * self.parameters["value_raise_multiplier"] * 0.7
                raise_amt = min(raise_amt, player_energy * POKER_PREFLOP_MAX_ENERGY_FRACTION)
                return (BettingAction.RAISE, max(raise_amt, call_amount * 1.3))
            return (
                (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)
            )

        if call_amount == 0:
            return (BettingAction.CHECK, 0.0)
        if (
            call_amount < pot * 0.3
            and hand_strength > pot_odds * self.parameters["pot_odds_factor"]
        ):
            return (BettingAction.CALL, call_amount)
        return (BettingAction.FOLD, 0.0)


@dataclass
class ManiacStrategy(PokerStrategyAlgorithm):
    """Ultra-aggressive strategy."""

    def __init__(self, rng: Optional[random.Random] = None):
        if rng is None:
            raise RuntimeError("ManiacStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="maniac",
            parameters={
                "min_hand_to_play": _rng.uniform(0.05, 0.20),
                "raise_frequency": _rng.uniform(0.60, 0.85),
                "raise_sizing": _rng.uniform(1.0, 2.5),
                "bluff_frequency": _rng.uniform(0.40, 0.65),
                "all_in_threshold": _rng.uniform(0.75, 0.95),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        _rng = rng or self._rng

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if hand_strength < self.parameters["min_hand_to_play"]:
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["all_in_threshold"] and _rng.random() < 0.3:
            return (BettingAction.RAISE, player_energy * 0.9)

        if _rng.random() < self.parameters["raise_frequency"]:
            raise_amt = pot * self.parameters["raise_sizing"]
            raise_amt = min(raise_amt, player_energy * 0.5)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 2.0))

        if call_amount == 0:
            if _rng.random() < 0.5:
                return (BettingAction.RAISE, pot * 0.5)
            return (BettingAction.CHECK, 0.0)
        return (BettingAction.CALL, call_amount)


@dataclass
class LoosePassiveStrategy(PokerStrategyAlgorithm):
    """Calling station: plays many hands passively."""

    def __init__(self, rng: Optional[random.Random] = None):
        # Inline RNG check
        if rng is None:
            raise RuntimeError("LoosePassiveStrategy: RNG is None")
        _rng = rng
        super().__init__(
            strategy_id="loose_passive",
            parameters={
                "weak_fold_threshold": _rng.uniform(0.10, 0.25),
                "raise_threshold": _rng.uniform(0.80, 0.95),
                "call_threshold": _rng.uniform(0.15, 0.30),
                "raise_multiplier": _rng.uniform(0.25, 0.50),
                "pot_odds_sensitivity": _rng.uniform(0.5, 1.5),
            },
            _rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        pot_odds = call_amount / (pot + call_amount) if pot > 0 and call_amount > 0 else 0.0
        adjusted = hand_strength + (1.0 - pot_odds) * self.parameters["pot_odds_sensitivity"] * 0.1

        if adjusted < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["raise_threshold"]:
            raise_amt = pot * self.parameters["raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.20)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.2))

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)
