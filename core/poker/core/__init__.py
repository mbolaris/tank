"""
Core poker components for Texas Hold'em.

This package contains the fundamental poker building blocks: cards, hands,
and game state. It also re-exports commonly used components from other
poker subpackages for convenience.

Note: To avoid circular imports, re-exports are done via lazy imports in
the module-level __getattr__ function.
"""

from core.poker.core.cards import Card, Deck, Rank, Suit, get_card
from core.poker.core.game_state import PokerGameState
from core.poker.core.hand import HandRank, PokerHand

# Core exports (always available)
__all__ = [
    # Cards
    "Card",
    "Deck",
    "Rank",
    "Suit",
    "get_card",
    # Hands
    "HandRank",
    "PokerHand",
    # Game State
    "PokerGameState",
    # Re-exported from betting (lazy loaded)
    "BettingAction",
    "BettingRound",
    "decide_action",
    "AGGRESSION_LOW",
    "AGGRESSION_MEDIUM",
    "AGGRESSION_HIGH",
    # Re-exported from evaluation (lazy loaded)
    "evaluate_hand",
    # Re-exported from simulation (lazy loaded)
    "simulate_game",
    "simulate_multi_round_game",
    "finalize_pot",
    "resolve_bet",
]

# Lazy imports to avoid circular dependencies
_lazy_imports = {
    "BettingAction": ("core.poker.betting.actions", "BettingAction"),
    "BettingRound": ("core.poker.betting.actions", "BettingRound"),
    "decide_action": ("core.poker.betting.decision", "decide_action"),
    "AGGRESSION_LOW": ("core.poker.betting.decision", "AGGRESSION_LOW"),
    "AGGRESSION_MEDIUM": ("core.poker.betting.decision", "AGGRESSION_MEDIUM"),
    "AGGRESSION_HIGH": ("core.poker.betting.decision", "AGGRESSION_HIGH"),
    "evaluate_hand": ("core.poker.evaluation.hand_evaluator", "evaluate_hand"),
    "simulate_game": ("core.poker.simulation.engine", "simulate_game"),
    "simulate_multi_round_game": ("core.poker.simulation.engine", "simulate_multi_round_game"),
    "finalize_pot": ("core.poker.simulation.engine", "finalize_pot"),
    "resolve_bet": ("core.poker.simulation.engine", "resolve_bet"),
}


def __getattr__(name: str):
    """Lazy import handler to avoid circular imports."""
    if name in _lazy_imports:
        module_path, attr_name = _lazy_imports[name]
        import importlib
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        # Cache in module namespace for future access
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
