"""Base class for evolving poker betting strategies."""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from core.poker.betting.actions import BettingAction


@dataclass
class PokerStrategyAlgorithm:
    """Base class for evolving poker betting strategies."""

    strategy_id: str = ""
    parameters: Dict[str, float] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random, repr=False)

    def decide_action(
        self,
        hand_strength: float,  # 0.0-1.0 normalized
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> Tuple[BettingAction, float]:
        """Make betting decision based on evolved parameters."""
        raise NotImplementedError

    def mutate_parameters(
        self,
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.2,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Mutate parameters for evolution.

        Args:
            mutation_rate: Probability of mutating each parameter
            mutation_strength: Standard deviation of Gaussian mutation
            rng: Random number generator (uses self._rng if not provided)
        """
        rng = rng if rng is not None else self.rng
        for param_key in self.parameters:
            if rng.random() < mutation_rate:
                mutation = rng.gauss(0, mutation_strength)
                self.parameters[param_key] += mutation
                # Clamp to valid ranges
                if "threshold" in param_key or "frequency" in param_key:
                    self.parameters[param_key] = max(0.0, min(1.0, self.parameters[param_key]))
                elif "multiplier" in param_key or "sizing" in param_key:
                    self.parameters[param_key] = max(0.1, min(3.0, self.parameters[param_key]))

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None) -> "PokerStrategyAlgorithm":
        """Create random instance using optional RNG for determinism."""
        raise NotImplementedError("PokerStrategyAlgorithm.random_instance must be implemented")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PokerStrategyAlgorithm":
        """Deserialize strategy from dictionary."""
        from core.poker.strategy.implementations.factory import (
            BASELINE_STRATEGIES,
            get_all_poker_strategies,
            get_random_poker_strategy,
        )

        strategy_id = data.get("strategy_id")
        if not isinstance(strategy_id, str) or not strategy_id:
            return get_random_poker_strategy(rng=random.Random(0))

        parameters: Dict[str, float] = {}
        parameters_data = data.get("parameters", {})
        if isinstance(parameters_data, dict):
            for key, value in parameters_data.items():
                try:
                    parameters[str(key)] = float(value)
                except (TypeError, ValueError):
                    continue

        strategy_map: Dict[str, type[PokerStrategyAlgorithm]] = {}
        for strategy_cls in [*get_all_poker_strategies(), *BASELINE_STRATEGIES]:
            try:
                instance = strategy_cls(rng=random.Random(0))
            except Exception:
                continue
            if instance.strategy_id:
                strategy_map[instance.strategy_id] = strategy_cls

        strategy_cls = strategy_map.get(strategy_id)
        if strategy_cls is None:
            return get_random_poker_strategy(rng=random.Random(0))

        instance = strategy_cls(rng=random.Random(0))
        instance.parameters = parameters
        return instance

    @property
    def _rng(self) -> random.Random:
        return self.rng

    @_rng.setter
    def _rng(self, value: random.Random) -> None:
        self.rng = value
