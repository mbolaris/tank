"""Run an auto-evaluation poker match and print performance metrics.

This CLI pits a set of fish poker strategies against the built-in standard
algorithm for a configurable number of hands and surfaces evaluation metrics
useful for gauging strategy strength (bb/100, showdown win rate, etc.).
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Type

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.poker.strategy.implementations import (
    BalancedStrategy,
    LooseAggressiveStrategy,
    LoosePassiveStrategy,
    ManiacStrategy,
    PokerStrategyAlgorithm,
    TightAggressiveStrategy,
    TightPassiveStrategy,
)

STRATEGY_REGISTRY: Dict[str, Type[PokerStrategyAlgorithm]] = {
    "balanced": BalancedStrategy,
    "tight_aggressive": TightAggressiveStrategy,
    "loose_aggressive": LooseAggressiveStrategy,
    "tight_passive": TightPassiveStrategy,
    "loose_passive": LoosePassiveStrategy,
    "maniac": ManiacStrategy,
}


def build_players(strategy_ids: List[str]) -> List[Dict]:
    players = []
    for idx, strategy_id in enumerate(strategy_ids, start=1):
        factory = STRATEGY_REGISTRY.get(strategy_id)
        if factory is None:
            raise SystemExit(
                f"Unknown strategy '{strategy_id}'. Choose from: {', '.join(sorted(STRATEGY_REGISTRY))}"
            )
        strategy = factory()
        players.append(
            {
                "name": f"{strategy.strategy_id}-{idx}",
                "poker_strategy": strategy,
                "species": "fish",
            }
        )
    return players


def print_summary(stats) -> None:
    print("\n=== Auto-evaluation summary ===")
    print(f"Hands played: {stats.hands_played}")
    print(f"Game over: {stats.game_over}; Winner: {stats.winner}")

    print("\nPlayer metrics:")
    headers = [
        ("Name", 22),
        ("Net Energy", 12),
        ("bb/100", 8),
        ("Win %", 8),
        ("Showdown %", 12),
        ("Showdowns", 12),
    ]
    header_line = " ".join(f"{label:<{width}}" for label, width in headers)
    print(header_line)
    print("-" * len(header_line))

    for player in stats.players:
        line = " ".join(
            [
                f"{player['name']:<22}",
                f"{player['net_energy']:+.1f}",
                f"{player.get('bb_per_100', 0.0):>8.2f}",
                f"{player.get('win_rate', 0.0):>8.1f}",
                f"{player.get('showdown_win_rate', 0.0):>12.1f}",
                f"{player.get('showdowns_won', 0)}/{player.get('showdowns_played', 0):<4}",
            ]
        )
        print(line)


def main():
    parser = argparse.ArgumentParser(description="Evaluate poker strategies vs standard algorithm")
    parser.add_argument(
        "strategies",
        nargs="*",
        default=["balanced", "tight_aggressive"],
        help="Strategy IDs to pit against the standard algorithm",
    )
    parser.add_argument("--hands", type=int, default=200, help="Number of hands to simulate")
    parser.add_argument("--small-blind", type=float, default=5.0, help="Small blind amount")
    parser.add_argument("--big-blind", type=float, default=10.0, help="Big blind amount")
    args = parser.parse_args()

    player_pool = build_players(args.strategies)
    game = AutoEvaluatePokerGame(
        game_id="cli-eval",
        player_pool=player_pool,
        max_hands=args.hands,
        small_blind=args.small_blind,
        big_blind=args.big_blind,
    )

    stats = game.run_evaluation()
    print_summary(stats)


if __name__ == "__main__":
    main()
