"""Advanced poker strategies."""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


@dataclass
class AdaptiveStrategy(PokerStrategyAlgorithm):
    """Adapts play style based on pot size and stack depth."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            strategy_id="adaptive",
            parameters={
                "aggression_base": _rng.uniform(0.3, 0.6),
                "pot_size_adjustment": _rng.uniform(0.1, 0.3),  # More aggressive with bigger pots
                "stack_depth_factor": _rng.uniform(0.5, 1.5),
                "fold_threshold_tight": _rng.uniform(0.35, 0.50),
                "fold_threshold_loose": _rng.uniform(0.15, 0.30),
                "position_bonus": _rng.uniform(0.08, 0.18),
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
    ) -> Tuple[BettingAction, float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        # Adapt aggression based on pot size relative to stack
        pot_ratio = pot / player_energy if player_energy > 0 else 0
        adjusted_aggression = self.parameters["aggression_base"] + (
            pot_ratio * self.parameters["pot_size_adjustment"]
        )

        # Tighter in big pots, looser in small pots
        fold_threshold = (
            self.parameters["fold_threshold_tight"]
            if pot_ratio > 0.3
            else self.parameters["fold_threshold_loose"]
        )

        if position_on_button:
            hand_strength += self.parameters["position_bonus"]

        if hand_strength < fold_threshold:
            return (BettingAction.FOLD, 0.0)

        if hand_strength > 0.7 or (hand_strength > 0.5 and self._rng.random() < adjusted_aggression):
            raise_amt = pot * self._rng.uniform(0.5, 1.0) * self.parameters["stack_depth_factor"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class PositionalExploiter(PokerStrategyAlgorithm):
    """Heavily exploits positional advantage."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            strategy_id="positional_exploiter",
            parameters={
                "ip_raise_threshold": _rng.uniform(0.25, 0.40),  # Raise more in position
                "oop_fold_threshold": _rng.uniform(0.40, 0.55),  # Fold more out of position
                "ip_aggression_boost": _rng.uniform(0.20, 0.40),
                "steal_frequency": _rng.uniform(0.35, 0.55),
                "value_sizing": _rng.uniform(0.6, 1.2),
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
    ) -> Tuple[BettingAction, float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            # In position: play aggressively
            adjusted_strength = hand_strength + self.parameters["ip_aggression_boost"]

            # Steal attempt with weak-medium hands
            if call_amount == 0 and self._rng.random() < self.parameters["steal_frequency"]:
                steal_amt = pot * self._rng.uniform(0.6, 1.0)
                return (BettingAction.RAISE, min(steal_amt, player_energy * 0.3))

            if adjusted_strength > self.parameters["ip_raise_threshold"]:
                raise_amt = pot * self.parameters["value_sizing"]
                raise_amt = min(raise_amt, player_energy * 0.4)
                return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))

            return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)
        else:
            # Out of position: play tight
            if hand_strength < self.parameters["oop_fold_threshold"]:
                return (BettingAction.FOLD, 0.0)

            if hand_strength > 0.75:
                raise_amt = pot * self.parameters["value_sizing"] * 0.8
                return (BettingAction.RAISE, min(raise_amt, player_energy * 0.35))

            return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class TrapSetterStrategy(PokerStrategyAlgorithm):
    """Slowplays strong hands to trap opponents."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            strategy_id="trap_setter",
            parameters={
                "trap_threshold": _rng.uniform(0.70, 0.85),  # Slowplay above this strength
                "trap_frequency": _rng.uniform(0.50, 0.75),  # How often to trap vs value bet
                "spring_trap_threshold": _rng.uniform(0.80, 0.95),  # When to spring the trap
                "weak_fold_threshold": _rng.uniform(0.30, 0.45),
                "check_raise_frequency": _rng.uniform(0.25, 0.45),
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
    ) -> Tuple[BettingAction, float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if hand_strength < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        # Strong hand - consider trapping
        if hand_strength >= self.parameters["trap_threshold"]:
            if self._rng.random() < self.parameters["trap_frequency"]:
                # Slowplay: just call or check to disguise strength
                if call_amount > 0:
                    return (BettingAction.CALL, call_amount)
                else:
                    # Check-raise opportunity
                    if self._rng.random() < self.parameters["check_raise_frequency"]:
                        return (BettingAction.CHECK, 0.0)  # Will raise if opponent bets
                    return (BettingAction.CHECK, 0.0)
            else:
                # Value bet the monster
                if hand_strength >= self.parameters["spring_trap_threshold"]:
                    raise_amt = pot * self._rng.uniform(0.8, 1.5)
                    raise_amt = min(raise_amt, player_energy * 0.5)
                    return (BettingAction.RAISE, raise_amt)

        # Medium strength - standard play
        if hand_strength > 0.5:
            if call_amount == 0:
                return (BettingAction.RAISE, pot * 0.5)
            return (BettingAction.CALL, call_amount)

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class MathematicalStrategy(PokerStrategyAlgorithm):
    """Pure pot odds and equity-based decisions."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "__init__")
        super().__init__(
            strategy_id="mathematical",
            parameters={
                "required_equity_multiplier": _rng.uniform(1.0, 1.4),  # How much equity needed vs pot odds
                "implied_odds_factor": _rng.uniform(1.2, 2.0),
                "value_bet_threshold": _rng.uniform(0.55, 0.70),
                "bet_sizing_pot_fraction": _rng.uniform(0.5, 0.8),
                "fold_equity_threshold": _rng.uniform(0.25, 0.40),
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
    ) -> Tuple[BettingAction, float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        # Calculate pot odds
        pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 and call_amount > 0 else 0.0

        # Implied odds adjustment
        effective_pot_odds = pot_odds / self.parameters["implied_odds_factor"]

        # Required equity to call
        required_equity = effective_pot_odds * self.parameters["required_equity_multiplier"]

        if call_amount > 0:
            if hand_strength >= required_equity:
                # Profitable call
                if hand_strength >= self.parameters["value_bet_threshold"]:
                    # Value raise
                    raise_amt = pot * self.parameters["bet_sizing_pot_fraction"]
                    raise_amt = min(raise_amt, player_energy * 0.4)
                    return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))
                return (BettingAction.CALL, call_amount)
            else:
                # Consider fold equity (semi-bluff)
                if hand_strength > self.parameters["fold_equity_threshold"] and self._rng.random() < 0.25:
                    bluff_amt = pot * self.parameters["bet_sizing_pot_fraction"]
                    return (BettingAction.RAISE, min(bluff_amt, player_energy * 0.3))
                return (BettingAction.FOLD, 0.0)
        else:
            # No bet to call
            if hand_strength >= self.parameters["value_bet_threshold"]:
                bet_amt = pot * self.parameters["bet_sizing_pot_fraction"]
                return (BettingAction.RAISE, min(bet_amt, player_energy * 0.35))
            return (BettingAction.CHECK, 0.0)
