"""(De)serialization codec for ComposablePokerStrategy.

Encodes a strategy to a plain dict for storage/transmission and decodes it
back. Encoding includes only the well-visited CFR info sets (filtered via
``CFRInheritance.filter_inheritable``), which is what makes the learned
state Lamarckian-inheritable across save/load boundaries.
"""

from typing import TYPE_CHECKING, Any

from core.poker.strategy.composable.cfr_inheritance import CFRInheritance
from core.poker.strategy.composable.definitions import (
    BettingStyle,
    BluffingApproach,
    HandSelection,
    PositionAwareness,
    ShowdownTendency,
)
from core.util import coerce_enum

if TYPE_CHECKING:
    from core.poker.strategy.composable.strategy import ComposablePokerStrategy


class PokerStrategyCodec:
    """Serializes ComposablePokerStrategy instances to/from dicts."""

    @staticmethod
    def encode(strategy: "ComposablePokerStrategy") -> dict[str, Any]:
        """Serialize a strategy to a dictionary for storage/transmission."""
        # Only include well-visited info sets in serialization
        (
            inheritable_regret,
            inheritable_strategy_sum,
            inheritable_visit_count,
        ) = CFRInheritance.filter_inheritable(
            strategy.regret, strategy.strategy_sum, strategy.visit_count
        )

        return {
            "type": "ComposablePokerStrategy",
            "strategy_id": strategy.strategy_id,
            "hand_selection": int(strategy.hand_selection),
            "betting_style": int(strategy.betting_style),
            "bluffing_approach": int(strategy.bluffing_approach),
            "position_awareness": int(strategy.position_awareness),
            "showdown_tendency": int(strategy.showdown_tendency),
            "parameters": dict(strategy.parameters),
            "learning_rate": strategy.learning_rate,
            # CFR learned state (Lamarckian-inheritable)
            "regret": inheritable_regret,
            "strategy_sum": inheritable_strategy_sum,
            "visit_count": inheritable_visit_count,
        }

    @staticmethod
    def decode(
        data: dict[str, Any],
        strategy_cls: "type[ComposablePokerStrategy] | None" = None,
    ) -> "ComposablePokerStrategy":
        """Deserialize a strategy from a dictionary."""
        if strategy_cls is None:
            from core.poker.strategy.composable.strategy import ComposablePokerStrategy

            strategy_cls = ComposablePokerStrategy

        return strategy_cls(
            strategy_id=data.get("strategy_id", "composable"),
            hand_selection=coerce_enum(HandSelection, data.get("hand_selection", 2)),
            betting_style=coerce_enum(BettingStyle, data.get("betting_style", 1)),
            bluffing_approach=coerce_enum(BluffingApproach, data.get("bluffing_approach", 1)),
            position_awareness=coerce_enum(PositionAwareness, data.get("position_awareness", 1)),
            showdown_tendency=coerce_enum(ShowdownTendency, data.get("showdown_tendency", 1)),
            parameters=data.get("parameters", {}),
            learning_rate=data.get("learning_rate", 1.0),
            regret=data.get("regret", {}),
            strategy_sum=data.get("strategy_sum", {}),
            visit_count=data.get("visit_count", {}),
        )
