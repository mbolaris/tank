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
from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from core.poker_interaction import BettingAction, PokerHand


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
            }
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
        from core.poker_interaction import BettingAction

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
            raise_amt = max(raise_amt, call_amount * 1.5)
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
            }
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
        from core.poker_interaction import BettingAction

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_aggression"]

        if call_amount == 0 and hand_strength > 0.2:
            raise_amt = pot * self.parameters["raise_multiplier"]
            return (BettingAction.RAISE, min(raise_amt, player_energy * 0.35))

        if hand_strength < self.parameters["weak_fold_threshold"]:
            return (BettingAction.FOLD, 0.0)

        if random.random() < self.parameters["bluff_frequency"]:
            bluff = pot * random.uniform(0.5, 1.2)
            return (BettingAction.RAISE, min(bluff, player_energy * 0.3))

        if hand_strength >= self.parameters["raise_threshold"]:
            raise_amt = pot * self.parameters["raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.4)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))

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
            }
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
        from core.poker_interaction import BettingAction

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
            }
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
        from core.poker_interaction import BettingAction

        call_amount = opponent_bet - current_bet
        if call_amount > player_energy:
            return (BettingAction.FOLD, 0.0)

        if position_on_button:
            hand_strength += self.parameters["position_bonus"]
            hand_strength = min(1.0, hand_strength)

        pot_odds = call_amount / (pot + call_amount) if pot > 0 and call_amount > 0 else 0.0

        if hand_strength < self.parameters["weak_fold_threshold"]:
            if pot_odds > 0 and hand_strength > pot_odds * self.parameters["pot_odds_factor"]:
                return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)
            if random.random() < self.parameters["bluff_frequency"] * 0.5:
                bluff = pot * self.parameters["bluff_multiplier"]
                return (BettingAction.RAISE, min(bluff, player_energy * 0.25))
            return (BettingAction.FOLD, 0.0)

        if hand_strength >= self.parameters["strong_threshold"]:
            raise_amt = pot * self.parameters["value_raise_multiplier"]
            raise_amt = min(raise_amt, player_energy * 0.40)
            return (BettingAction.RAISE, max(raise_amt, call_amount * 1.5))

        if hand_strength >= self.parameters["medium_threshold"]:
            if random.random() < 0.4:
                raise_amt = pot * self.parameters["value_raise_multiplier"] * 0.7
                raise_amt = min(raise_amt, player_energy * 0.30)
                return (BettingAction.RAISE, max(raise_amt, call_amount * 1.3))
            return (BettingAction.CALL, call_amount) if call_amount > 0 else (BettingAction.CHECK, 0.0)

        if call_amount == 0:
            return (BettingAction.CHECK, 0.0)
        if call_amount < pot * 0.3 and hand_strength > pot_odds * self.parameters["pot_odds_factor"]:
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
            }
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
        from core.poker_interaction import BettingAction

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
            }
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
        from core.poker_interaction import BettingAction

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


ALL_POKER_STRATEGIES = [
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    TightPassiveStrategy,
    LoosePassiveStrategy,
    BalancedStrategy,
    ManiacStrategy,
]


def get_random_poker_strategy() -> PokerStrategyAlgorithm:
    """Get random poker strategy."""
    return random.choice(ALL_POKER_STRATEGIES).random_instance()


def crossover_poker_strategies(
    parent1: Optional[PokerStrategyAlgorithm],
    parent2: Optional[PokerStrategyAlgorithm],
    mutation_rate: float = 0.15,
    mutation_strength: float = 0.2,
) -> PokerStrategyAlgorithm:
    """Crossover two poker strategies."""
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
            offspring = parent1.__class__()
            for param_key in parent1.parameters:
                if param_key in parent2.parameters:
                    if random.random() < 0.5:
                        offspring.parameters[param_key] = (
                            parent1.parameters[param_key] + parent2.parameters[param_key]
                        ) / 2.0
                    else:
                        offspring.parameters[param_key] = (
                            parent1.parameters[param_key] if random.random() < 0.5
                            else parent2.parameters[param_key]
                        )
                else:
                    offspring.parameters[param_key] = parent1.parameters[param_key]
        else:
            chosen = parent1 if random.random() < 0.5 else parent2
            offspring = chosen.__class__()
            offspring.parameters = chosen.parameters.copy()

    offspring.mutate_parameters(mutation_rate, mutation_strength)
    return offspring
