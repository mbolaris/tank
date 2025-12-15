"""Evolving poker strategy algorithms for betting decisions.

This module provides poker strategy algorithms that evolve through mutation and crossover.
Unlike BehaviorAlgorithm (which controls fish movement), these control poker betting decisions.

Each strategy has evolvable parameters that control:
- Fold/call/raise thresholds
- Bet sizing
- Bluff frequency
- Pot odds sensitivity
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from core.constants import (
    POKER_LAG_ENERGY_FRACTION,
    POKER_PREFLOP_MAX_ENERGY_FRACTION,
    POKER_PREFLOP_MIN_RAISE_MULTIPLIER,
)
from core.poker.betting.actions import BettingAction


@dataclass
class PokerStrategyAlgorithm:
    """Base class for evolving poker betting strategies."""

    strategy_id: str
    parameters: Dict[str, float] = field(default_factory=dict)

    def decide_action(
        self,
        hand_strength: float,  # 0.0-1.0 normalized
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:
        """Make betting decision based on evolved parameters."""
        raise NotImplementedError

    def mutate_parameters(
        self,
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.2,
    ) -> None:
        """Mutate parameters for evolution."""
        for param_key in self.parameters:
            if random.random() < mutation_rate:
                mutation = random.gauss(0, mutation_strength)
                self.parameters[param_key] += mutation
                # Clamp to valid ranges
                if "threshold" in param_key or "frequency" in param_key:
                    self.parameters[param_key] = max(0.0, min(1.0, self.parameters[param_key]))
                elif "multiplier" in param_key or "sizing" in param_key:
                    self.parameters[param_key] = max(0.1, min(3.0, self.parameters[param_key]))

    @classmethod
    def random_instance(cls) -> "PokerStrategyAlgorithm":
        """Create random instance."""
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PokerStrategyAlgorithm":
        """Deserialize strategy from dictionary."""
        strategy_id = data.get("strategy_id")
        parameters = data.get("parameters", {})

        # Find the correct subclass
        for strategy_cls in ALL_POKER_STRATEGIES:
            # Create a temporary instance to check ID (or check class attribute if available)
            # Since strategy_id is set in __init__, we check the class map below
            pass

        # Better approach: Map IDs to classes
        strategy_map = {
            "tight_aggressive": TightAggressiveStrategy,
            "loose_aggressive": LooseAggressiveStrategy,
            "tight_passive": TightPassiveStrategy,
            "loose_passive": LoosePassiveStrategy,
            "balanced": BalancedStrategy,
            "maniac": ManiacStrategy,
            # Advanced strategies
            "adaptive": AdaptiveStrategy,
            "positional_exploiter": PositionalExploiter,
            "trap_setter": TrapSetterStrategy,
            "mathematical": MathematicalStrategy,
            # Baseline strategies for benchmarking
            "always_fold": AlwaysFoldStrategy,
            "random": RandomStrategy,
        }

        strategy_cls = strategy_map.get(strategy_id)
        if strategy_cls:
            instance = strategy_cls()
            instance.parameters = parameters
            return instance

        # Fallback to random if unknown
        return get_random_poker_strategy()


@dataclass
class TightAggressiveStrategy(PokerStrategyAlgorithm):
    """TAG: Plays few hands aggressively."""

    def __init__(self):
        super().__init__(
            strategy_id="tight_aggressive",
            parameters={
                "weak_fold_threshold": random.uniform(0.3, 0.5),
                "strong_raise_threshold": random.uniform(0.6, 0.8),
                "value_raise_multiplier": random.uniform(0.5, 1.0),
                "bluff_frequency": random.uniform(0.05, 0.15),
                "position_bonus": random.uniform(0.05, 0.15),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_bonus"]
            hand_strength = min(1.0, hand_strength)

        if hand_strength < self.parameters["weak_fold_threshold"]:
            if random.random() < self.parameters["bluff_frequency"]:
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

    def __init__(self):
        super().__init__(
            strategy_id="loose_aggressive",
            parameters={
                "weak_fold_threshold": random.uniform(0.15, 0.30),
                "raise_threshold": random.uniform(0.4, 0.6),
                "raise_multiplier": random.uniform(0.7, 1.5),
                "bluff_frequency": random.uniform(0.25, 0.45),
                "position_aggression": random.uniform(0.1, 0.25),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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

        if random.random() < self.parameters["bluff_frequency"]:
            bluff = pot * random.uniform(0.5, 1.2)
            return (BettingAction.RAISE, min(bluff, player_energy * POKER_PREFLOP_MAX_ENERGY_FRACTION))

        if hand_strength >= self.parameters["raise_threshold"]:
            raise_amt = pot * self.parameters["raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            return (BettingAction.RAISE, max(raise_amt, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER))

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class TightPassiveStrategy(PokerStrategyAlgorithm):
    """Rock: Plays few hands, rarely raises."""

    def __init__(self):
        super().__init__(
            strategy_id="tight_passive",
            parameters={
                "weak_fold_threshold": random.uniform(0.4, 0.6),
                "raise_threshold": random.uniform(0.75, 0.90),
                "call_threshold": random.uniform(0.35, 0.55),
                "raise_multiplier": random.uniform(0.3, 0.6),
                "bluff_frequency": random.uniform(0.01, 0.05),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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

    def __init__(self):
        super().__init__(
            strategy_id="balanced",
            parameters={
                "weak_fold_threshold": random.uniform(0.25, 0.40),
                "medium_threshold": random.uniform(0.45, 0.60),
                "strong_threshold": random.uniform(0.70, 0.85),
                "value_raise_multiplier": random.uniform(0.5, 0.9),
                "bluff_multiplier": random.uniform(0.4, 0.8),
                "bluff_frequency": random.uniform(0.15, 0.30),
                "position_bonus": random.uniform(0.08, 0.18),
                "pot_odds_factor": random.uniform(1.2, 1.8),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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
            if random.random() < self.parameters["bluff_frequency"] * 0.5:
                bluff = pot * self.parameters["bluff_multiplier"]
                return (BettingAction.RAISE, min(bluff, player_energy * 0.25))
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["strong_threshold"]:
            raise_amt = pot * self.parameters["value_raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.40)
            return (BettingAction.RAISE, max(raise_amt, call_amount * POKER_PREFLOP_MIN_RAISE_MULTIPLIER))

        if hand_strength >= self.parameters["medium_threshold"]:
            if random.random() < 0.4:
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

    def __init__(self):
        super().__init__(
            strategy_id="maniac",
            parameters={
                "min_hand_to_play": random.uniform(0.05, 0.20),
                "raise_frequency": random.uniform(0.60, 0.85),
                "raise_sizing": random.uniform(1.0, 2.5),
                "bluff_frequency": random.uniform(0.40, 0.65),
                "all_in_threshold": random.uniform(0.75, 0.95),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if hand_strength < self.parameters["min_hand_to_play"]:
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["all_in_threshold"] and random.random() < 0.3:
            return (BettingAction.RAISE, player_energy * 0.9)

        if random.random() < self.parameters["raise_frequency"]:
            raise_amt = pot * self.parameters["raise_sizing"]
            raise_amt = min(raise_amt, player_energy * 0.5)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 2.0))

        if call_amount == 0:
            if random.random() < 0.5:
                return (BettingAction.RAISE, pot * 0.5)
            return (BettingAction.CHECK, 0.0)
        return (BettingAction.CALL, call_amount)


@dataclass
class LoosePassiveStrategy(PokerStrategyAlgorithm):
    """Calling station: plays many hands passively."""

    def __init__(self):
        super().__init__(
            strategy_id="loose_passive",
            parameters={
                "weak_fold_threshold": random.uniform(0.10, 0.25),
                "raise_threshold": random.uniform(0.80, 0.95),
                "call_threshold": random.uniform(0.15, 0.30),
                "raise_multiplier": random.uniform(0.25, 0.50),
                "pot_odds_sensitivity": random.uniform(0.5, 1.5),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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


# NEW STRATEGIES for more diversity

@dataclass
class AdaptiveStrategy(PokerStrategyAlgorithm):
    """Adapts play style based on pot size and stack depth."""

    def __init__(self):
        super().__init__(
            strategy_id="adaptive",
            parameters={
                "aggression_base": random.uniform(0.3, 0.6),
                "pot_size_adjustment": random.uniform(0.1, 0.3),  # More aggressive with bigger pots
                "stack_depth_factor": random.uniform(0.5, 1.5),
                "fold_threshold_tight": random.uniform(0.35, 0.50),
                "fold_threshold_loose": random.uniform(0.15, 0.30),
                "position_bonus": random.uniform(0.08, 0.18),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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

        if hand_strength > 0.7 or (hand_strength > 0.5 and random.random() < adjusted_aggression):
            raise_amt = pot * random.uniform(0.5, 1.0) * self.parameters["stack_depth_factor"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))

        return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)


@dataclass
class PositionalExploiter(PokerStrategyAlgorithm):
    """Heavily exploits positional advantage."""

    def __init__(self):
        super().__init__(
            strategy_id="positional_exploiter",
            parameters={
                "ip_raise_threshold": random.uniform(0.25, 0.40),  # Raise more in position
                "oop_fold_threshold": random.uniform(0.40, 0.55),  # Fold more out of position
                "ip_aggression_boost": random.uniform(0.20, 0.40),
                "steal_frequency": random.uniform(0.35, 0.55),
                "value_sizing": random.uniform(0.6, 1.2),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            # In position: play aggressively
            adjusted_strength = hand_strength + self.parameters["ip_aggression_boost"]

            # Steal attempt with weak-medium hands
            if call_amount == 0 and random.random() < self.parameters["steal_frequency"]:
                steal_amt = pot * random.uniform(0.6, 1.0)
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

    def __init__(self):
        super().__init__(
            strategy_id="trap_setter",
            parameters={
                "trap_threshold": random.uniform(0.70, 0.85),  # Slowplay above this strength
                "trap_frequency": random.uniform(0.50, 0.75),  # How often to trap vs value bet
                "spring_trap_threshold": random.uniform(0.80, 0.95),  # When to spring the trap
                "weak_fold_threshold": random.uniform(0.30, 0.45),
                "check_raise_frequency": random.uniform(0.25, 0.45),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if hand_strength < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        # Strong hand - consider trapping
        if hand_strength >= self.parameters["trap_threshold"]:
            if random.random() < self.parameters["trap_frequency"]:
                # Slowplay: just call or check to disguise strength
                if call_amount > 0:
                    return (BettingAction.CALL, call_amount)
                else:
                    # Check-raise opportunity
                    if random.random() < self.parameters["check_raise_frequency"]:
                        return (BettingAction.CHECK, 0.0)  # Will raise if opponent bets
                    return (BettingAction.CHECK, 0.0)
            else:
                # Value bet the monster
                if hand_strength >= self.parameters["spring_trap_threshold"]:
                    raise_amt = pot * random.uniform(0.8, 1.5)
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

    def __init__(self):
        super().__init__(
            strategy_id="mathematical",
            parameters={
                "required_equity_multiplier": random.uniform(1.0, 1.4),  # How much equity needed vs pot odds
                "implied_odds_factor": random.uniform(1.2, 2.0),
                "value_bet_threshold": random.uniform(0.55, 0.70),
                "bet_sizing_pot_fraction": random.uniform(0.5, 0.8),
                "fold_equity_threshold": random.uniform(0.25, 0.40),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple["BettingAction", float]:

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
                if hand_strength > self.parameters["fold_equity_threshold"] and random.random() < 0.25:
                    bluff_amt = pot * self.parameters["bet_sizing_pot_fraction"]
                    return (BettingAction.RAISE, min(bluff_amt, player_energy * 0.3))
                return (BettingAction.FOLD, 0.0)
        else:
            # No bet to call
            if hand_strength >= self.parameters["value_bet_threshold"]:
                bet_amt = pot * self.parameters["bet_sizing_pot_fraction"]
                return (BettingAction.RAISE, min(bet_amt, player_energy * 0.35))
            return (BettingAction.CHECK, 0.0)


# =============================================================================
# BASELINE STRATEGIES FOR BENCHMARKING
# These are fixed, non-evolving strategies used to measure skill progression
# =============================================================================


@dataclass
class AlwaysFoldStrategy(PokerStrategyAlgorithm):
    """Baseline: Folds everything except absolute premium hands.

    This is the weakest possible opponent - any competent strategy
    should achieve high bb/100 against this. Used as a sanity check
    that evolution is producing strategies that can at least beat
    the most exploitable opponent.
    """

    strategy_id: str = "always_fold"
    parameters: Dict[str, float] = field(
        default_factory=lambda: {
            "premium_threshold": 0.95,  # Only play AA, KK (~top 1% of hands)
        }
    )

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
    ) -> Tuple[BettingAction, float]:
        premium_threshold = self.parameters.get("premium_threshold", 0.95)
        call_amount = max(0, opponent_bet - current_bet)

        # Only continue with absolute premium hands
        if hand_strength >= premium_threshold:
            if call_amount <= 0:
                return (BettingAction.CHECK, 0.0)
            if call_amount <= player_energy:
                return (BettingAction.CALL, call_amount)
            return (BettingAction.FOLD, 0.0)

        # Fold everything else
        if call_amount > 0:
            return (BettingAction.FOLD, 0.0)
        return (BettingAction.CHECK, 0.0)

    @classmethod
    def random_instance(cls) -> "AlwaysFoldStrategy":
        """Create instance (parameters are fixed for baseline)."""
        return cls()


@dataclass
class RandomStrategy(PokerStrategyAlgorithm):
    """Baseline: Makes completely random decisions.

    Pure noise baseline - any learning/evolution should beat this easily.
    This provides a floor for measuring whether strategies have learned
    anything at all about poker.
    """

    strategy_id: str = "random"
    parameters: Dict[str, float] = field(
        default_factory=lambda: {
            "fold_prob": 0.33,
            "call_prob": 0.33,
            # Remaining probability = raise
            "min_raise_fraction": 0.3,
            "max_raise_fraction": 1.0,
        }
    )

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

        roll = random.random()
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
            raise_fraction = random.uniform(min_raise_frac, max_raise_frac)
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
    def random_instance(cls) -> "RandomStrategy":
        """Create instance (parameters are fixed for baseline)."""
        return cls()


# Registry of all EVOLVING strategy classes
ALL_POKER_STRATEGIES = [
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    TightPassiveStrategy,
    LoosePassiveStrategy,
    BalancedStrategy,
    ManiacStrategy,
    # Advanced strategies for more diversity
    AdaptiveStrategy,
    PositionalExploiter,
    TrapSetterStrategy,
    MathematicalStrategy,
]

# Baseline strategies for benchmarking (not included in evolution pool)
BASELINE_STRATEGIES = [
    AlwaysFoldStrategy,
    RandomStrategy,
    TightPassiveStrategy,  # "Rock" - also useful as baseline
    LoosePassiveStrategy,  # "Calling Station" - also useful as baseline
]


def get_random_poker_strategy(rng: Optional[random.Random] = None) -> PokerStrategyAlgorithm:
    """Get random poker strategy."""
    rng = rng or random
    return rng.choice(ALL_POKER_STRATEGIES).random_instance()


# Configuration flags for poker evolution tuning
POKER_EVOLUTION_CONFIG = {
    # Novelty injection rate: chance of completely random strategy
    # Lower = more exploitation of evolved strategies, Higher = more exploration
    # Set very low to preserve evolved adaptations across generations
    "novelty_injection_rate": 0.005,  # REDUCED from 0.02 to minimize genetic drift
    # Rate when parents have different strategy types
    "different_type_novelty_rate": 0.01,  # REDUCED from 0.05 to preserve winning types
    # Default mutation parameters - reduced for more stable evolution
    "default_mutation_rate": 0.08,  # REDUCED from 0.12 for stability
    "default_mutation_strength": 0.10,  # REDUCED from 0.15 for stability
    # Enable winner-biased inheritance (parent1 = winner when True)
    "winner_biased_inheritance": True,
    # Default winner weight when winner_biased_inheritance is True
    "default_winner_weight": 0.85,  # INCREASED from 0.80 - winner contributes 85%
}


def crossover_poker_strategies(
    parent1: Optional[PokerStrategyAlgorithm],
    parent2: Optional[PokerStrategyAlgorithm],
    mutation_rate: float = None,
    mutation_strength: float = None,
    winner_weight: float = None,
) -> PokerStrategyAlgorithm:
    """Crossover two poker strategies with winner-biased inheritance.

    This function creates offspring poker strategies by combining two parent
    strategies. When winner_weight is provided (or winner_biased_inheritance
    is enabled), parent1 is assumed to be the winner and contributes more
    genetic material.

    Args:
        parent1: First parent strategy (winner in winner-biased mode)
        parent2: Second parent strategy (loser in winner-biased mode)
        mutation_rate: Probability of mutating each parameter (0.0-1.0)
        mutation_strength: Standard deviation of Gaussian mutation
        winner_weight: How much parent1 (winner) contributes (0.0-1.0, default 0.8)

    Returns:
        New offspring poker strategy
    """
    cfg = POKER_EVOLUTION_CONFIG

    # Use config defaults if not provided
    if mutation_rate is None:
        mutation_rate = cfg["default_mutation_rate"]
    if mutation_strength is None:
        mutation_strength = cfg["default_mutation_strength"]
    if winner_weight is None:
        winner_weight = cfg["default_winner_weight"] if cfg["winner_biased_inheritance"] else 0.5

    # Clamp winner_weight to valid range
    winner_weight = max(0.0, min(1.0, winner_weight))

    # Novelty injection: small chance of completely random strategy
    # This maintains diversity but at a lower rate to preserve adaptations
    if random.random() < cfg["novelty_injection_rate"]:
        return get_random_poker_strategy()

    if parent1 is None and parent2 is None:
        return get_random_poker_strategy()
    elif parent1 is None:
        offspring = parent2.__class__()
        offspring.parameters = parent2.parameters.copy()
    elif parent2 is None:
        offspring = parent1.__class__()
        offspring.parameters = parent1.parameters.copy()
    else:
        same_type = type(parent1) == type(parent2)
        if same_type:
            # Same strategy type: blend parameters with winner-biased weighting
            offspring = parent1.__class__()
            for param_key in parent1.parameters:
                if param_key in parent2.parameters:
                    # Use winner-biased weighted average
                    # winner_weight determines parent1's contribution
                    offspring.parameters[param_key] = (
                        parent1.parameters[param_key] * winner_weight +
                        parent2.parameters[param_key] * (1.0 - winner_weight)
                    )
                else:
                    offspring.parameters[param_key] = parent1.parameters[param_key]
        else:
            # Different strategy types: prefer winner's type
            if random.random() < cfg["different_type_novelty_rate"]:
                # Reduced novelty injection for different types
                offspring = get_random_poker_strategy()
            elif random.random() < winner_weight:
                # Winner-biased selection: prefer winner's (parent1) strategy type
                offspring = parent1.__class__()
                offspring.parameters = parent1.parameters.copy()
            else:
                # Loser's strategy type selected
                offspring = parent2.__class__()
                offspring.parameters = parent2.parameters.copy()

    offspring.mutate_parameters(mutation_rate, mutation_strength)
    return offspring
