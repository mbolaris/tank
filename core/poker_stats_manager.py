import json
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from core.config.ecosystem import TOTAL_ALGORITHM_COUNT
from core.ecosystem_stats import EcosystemEvent, FishOpponentPokerStats, PokerStats

if TYPE_CHECKING:
    from core.entities import Fish
    from core.poker.core import PokerHand
    from core.poker.table import PokerResult

logger = logging.getLogger(__name__)


class PokerStatsManager:
    """Handles poker statistics aggregation and event logging."""

    def __init__(
        self,
        add_event: Callable[[EcosystemEvent], None],
        frame_provider: Callable[[], int],
    ) -> None:
        self._add_event = add_event
        self._frame_provider = frame_provider

        self.poker_stats: Dict[int, PokerStats] = {}
        self.plant_poker_stats: Dict[int, FishOpponentPokerStats] = {}
        self.total_fish_poker_games: int = 0
        self.total_plant_poker_games: int = 0
        self.total_plant_poker_energy_transferred: float = 0.0
        self._poker_save_counter: int = 0

        self._init_poker_stats()

    def cleanup_dead_fish(self, alive_fish_ids: Set[int]) -> int:
        """Remove poker stats for fish that are no longer alive.

        Args:
            alive_fish_ids: Set of IDs of currently living fish.

        Returns:
            Number of records removed.
        """
        initial_count = len(self.plant_poker_stats)
        # Keep only fish that are alive
        self.plant_poker_stats = {
            fish_id: stats
            for fish_id, stats in self.plant_poker_stats.items()
            if fish_id in alive_fish_ids
        }
        return initial_count - len(self.plant_poker_stats)

    def _poker_totals_path(self) -> str:
        os.makedirs("logs", exist_ok=True)
        return os.path.join("logs", "poker_totals.json")

    def _load_poker_totals(self) -> None:
        path = self._poker_totals_path()
        if not os.path.exists(path):
            return

        with open(path) as file:
            data = json.load(file)

        self.total_fish_poker_games = int(data.get("total_fish_poker_games", 0))
        self.total_plant_poker_games = int(data.get("total_plant_poker_games", 0))

    def _save_poker_totals(self) -> None:
        # Optimization: Only save every 100 updates to reduce file I/O
        self._poker_save_counter += 1
        if self._poker_save_counter < 100:
            return

        self._poker_save_counter = 0
        path = self._poker_totals_path()
        data = {
            "total_fish_poker_games": int(self.total_fish_poker_games),
            "total_plant_poker_games": int(self.total_plant_poker_games),
        }
        with open(path, "w") as file:
            json.dump(data, file)

    def _init_poker_stats(self) -> None:
        """Initialize poker stats for all algorithms including poker variants."""
        for i in range(TOTAL_ALGORITHM_COUNT + 5):
            self.poker_stats[i] = PokerStats(algorithm_id=i)

    def get_poker_stats_summary(self) -> Dict[str, Any]:
        """Get summary poker statistics across all algorithms."""
        total_games = sum(s.total_games for s in self.poker_stats.values())
        total_wins = sum(s.total_wins for s in self.poker_stats.values())
        total_losses = sum(s.total_losses for s in self.poker_stats.values())
        total_ties = sum(s.total_ties for s in self.poker_stats.values())
        total_energy_won = sum(s.total_energy_won for s in self.poker_stats.values())
        total_energy_lost = sum(s.total_energy_lost for s in self.poker_stats.values())
        total_house_cuts = sum(s.total_house_cuts for s in self.poker_stats.values())
        total_folds = sum(s.folds for s in self.poker_stats.values())
        total_showdowns = sum(s.showdown_count for s in self.poker_stats.values())
        total_won_at_showdown = sum(s.won_at_showdown for s in self.poker_stats.values())
        total_won_by_fold = sum(s.won_by_fold for s in self.poker_stats.values())

        best_hand_rank = max((s.best_hand_rank for s in self.poker_stats.values()), default=0)
        hand_rank_names = [
            "High Card",
            "Pair",
            "Two Pair",
            "Three of a Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four of a Kind",
            "Straight Flush",
            "Royal Flush",
        ]
        best_hand_name = hand_rank_names[best_hand_rank] if 0 <= best_hand_rank < len(hand_rank_names) else "Unknown"

        avg_fold_rate = (total_folds / total_games) if total_games > 0 else 0.0
        showdown_win_rate = (total_won_at_showdown / total_showdowns) if total_showdowns > 0 else 0.0
        net_energy = total_energy_won - total_energy_lost - total_house_cuts

        win_rate = (total_wins / total_games) if total_games > 0 else 0.0
        roi = (net_energy / total_games) if total_games > 0 else 0.0

        total_preflop_folds = sum(s.preflop_folds for s in self.poker_stats.values())
        vpip = ((total_games - total_preflop_folds) / total_games) if total_games > 0 else 0.0

        total_button_wins = sum(s.button_wins for s in self.poker_stats.values())
        total_button_games = sum(s.button_games for s in self.poker_stats.values())
        total_non_button_wins = sum(s.non_button_wins for s in self.poker_stats.values())
        total_non_button_games = sum(s.non_button_games for s in self.poker_stats.values())
        button_win_rate = (total_button_wins / total_button_games) if total_button_games > 0 else 0.0
        non_button_win_rate = (
            (total_non_button_wins / total_non_button_games) if total_non_button_games > 0 else 0.0
        )
        positional_advantage = button_win_rate - non_button_win_rate

        total_raises = sum(s.total_raises for s in self.poker_stats.values())
        total_calls = sum(s.total_calls for s in self.poker_stats.values())
        aggression_factor = (total_raises / total_calls) if total_calls > 0 else 0.0

        avg_hand_rank = sum(s.avg_hand_rank for s in self.poker_stats.values() if s.total_games > 0)
        num_active_algorithms = len([s for s in self.poker_stats.values() if s.total_games > 0])
        avg_hand_rank = avg_hand_rank / num_active_algorithms if num_active_algorithms > 0 else 0.0

        total_showdown_wins = sum(s.won_at_showdown for s in self.poker_stats.values())
        showdown_win_rate_pct = f"{(total_showdown_wins / total_showdowns):.1%}" if total_showdowns > 0 else "0.0%"

        return {
            "total_games": total_games,
            "total_fish_games": self.total_fish_poker_games,
            "total_plant_games": self.total_plant_poker_games,
            "total_plant_energy_transferred": self.total_plant_poker_energy_transferred,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_ties": total_ties,
            "total_energy_won": total_energy_won,
            "total_energy_lost": total_energy_lost,
            "net_energy": net_energy,
            "best_hand_rank": best_hand_rank,
            "best_hand_name": best_hand_name,
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate:.1%}",
            "roi": roi,
            "vpip": vpip,
            "vpip_pct": f"{vpip:.1%}",
            "bluff_success_rate": (total_won_by_fold / total_games) if total_games > 0 else 0.0,
            "bluff_success_pct": (
                f"{(total_won_by_fold / total_games):.1%}" if total_games > 0 else "0.0%"
            ),
            "button_win_rate": button_win_rate,
            "button_win_rate_pct": f"{button_win_rate:.1%}",
            "non_button_win_rate": non_button_win_rate,
            "non_button_win_rate_pct": f"{non_button_win_rate:.1%}",
            "positional_advantage": positional_advantage,
            "positional_advantage_pct": f"{positional_advantage:.1%}",
            "aggression_factor": aggression_factor,
            "avg_hand_rank": avg_hand_rank,
            "total_folds": total_folds,
            "preflop_folds": total_preflop_folds,
            "postflop_folds": sum(s.postflop_folds for s in self.poker_stats.values()),
            "showdown_win_rate": showdown_win_rate,
            "showdown_win_rate_pct": showdown_win_rate_pct,
            "avg_fold_rate": avg_fold_rate,
        }

    def get_poker_leaderboard(
        self, fish_list: List["Fish"], sort_by: str = "net_energy", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get poker leaderboard of top-performing fish."""
        if fish_list is None:
            return []

        poker_fish: List[Fish] = []
        for fish in fish_list:
            if not hasattr(fish, "poker_stats") or fish.poker_stats is None:
                from core.fish.poker_stats_component import FishPokerStats

                fish.poker_stats = FishPokerStats()

            if fish.poker_stats.total_games > 0:
                poker_fish.append(fish)

        if sort_by == "net_energy":
            poker_fish.sort(key=lambda f: f.poker_stats.get_net_energy(), reverse=True)
        elif sort_by == "wins":
            poker_fish.sort(key=lambda f: f.poker_stats.wins, reverse=True)
        elif sort_by == "win_rate":
            poker_fish.sort(key=lambda f: f.poker_stats.get_win_rate(), reverse=True)
        elif sort_by == "roi":
            poker_fish.sort(key=lambda f: f.poker_stats.get_roi(), reverse=True)
        else:
            poker_fish.sort(key=lambda f: f.poker_stats.get_net_energy(), reverse=True)

        hand_rank_names = [
            "High Card",
            "Pair",
            "Two Pair",
            "Three of a Kind",
            "Straight",
            "Flush",
            "Full House",
            "Four of a Kind",
            "Straight Flush",
            "Royal Flush",
        ]

        leaderboard = []
        for rank, fish in enumerate(poker_fish[:limit], start=1):
            stats = fish.poker_stats
            best_hand_name = (
                hand_rank_names[stats.best_hand_rank]
                if 0 <= stats.best_hand_rank < len(hand_rank_names)
                else "Unknown"
            )

            algo_name = "Unknown"
            composable = fish.genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                algo_name = composable.value.short_description

            leaderboard.append(
                {
                    "rank": rank,
                    "fish_id": fish.fish_id,
                    "generation": fish.generation,
                    "algorithm": algo_name,
                    "energy": round(fish.energy, 1),
                    "age": fish._lifecycle_component.age,
                    "total_games": stats.total_games,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "ties": stats.ties,
                    "win_rate": round(stats.get_win_rate() * 100, 1),
                    "net_energy": round(stats.get_net_energy(), 1),
                    "roi": round(stats.get_roi(), 2),
                    "current_streak": stats.current_streak,
                    "best_streak": stats.best_streak,
                    "best_hand": best_hand_name,
                    "best_hand_rank": stats.best_hand_rank,
                    "showdown_win_rate": round(stats.get_showdown_win_rate() * 100, 1),
                    "fold_rate": round(stats.get_fold_rate() * 100, 1),
                    "positional_advantage": round(stats.get_positional_advantage() * 100, 1),
                    "recent_win_rate": round(stats.get_recent_win_rate() * 100, 1),
                    "skill_trend": stats.get_skill_trend(),
                }
            )

        return leaderboard

    def record_poker_outcome(
        self,
        winner_id: int,
        loser_id: int,
        winner_algo_id: Optional[int],
        loser_algo_id: Optional[int],
        amount: float,
        winner_hand: "PokerHand",
        loser_hand: "PokerHand",
        house_cut: float = 0.0,
        result: Optional["PokerResult"] = None,
        player1_algo_id: Optional[int] = None,
        player2_algo_id: Optional[int] = None,
    ) -> None:
        """Record a poker game outcome with detailed statistics."""
        if winner_id == -1:
            self._update_tie_stats(winner_algo_id, winner_hand)
            self._update_tie_stats(loser_algo_id, loser_hand)
            return

        self._update_winner_stats(
            winner_id,
            winner_algo_id,
            amount,
            winner_hand,
            house_cut,
            result,
            player1_algo_id,
            player2_algo_id,
        )

        self._update_loser_stats(
            loser_algo_id,
            amount,
            loser_hand,
            house_cut,
            result,
            player1_algo_id,
            player2_algo_id,
        )

        self.total_fish_poker_games += 1
        try:
            self._save_poker_totals()
        except Exception as error:  # pragma: no cover - defensive logging
            logger.error(f"Failed to save poker totals: {error}", exc_info=True)

        self._log_poker_event(winner_id, loser_id, amount, winner_hand, loser_hand)

    def record_plant_poker_game(
        self,
        fish_id: int,
        plant_id: int,
        fish_won: bool,
        energy_transferred: float,
        fish_hand_rank: int,
        plant_hand_rank: int,
        won_by_fold: bool,
    ) -> None:
        """Record a poker game between a fish and a fractal plant."""
        if fish_id not in self.plant_poker_stats:
            self.plant_poker_stats[fish_id] = FishOpponentPokerStats(
                fish_id=fish_id, fish_name=f"Fish #{fish_id}"
            )

        stats = self.plant_poker_stats[fish_id]
        stats.total_games += 1

        if fish_won:
            stats.wins += 1
            stats.total_energy_won += energy_transferred
            self.total_plant_poker_energy_transferred += energy_transferred
            if won_by_fold:
                stats.wins_by_fold += 1
        else:
            stats.losses += 1
            stats.total_energy_lost += energy_transferred
            self.total_plant_poker_energy_transferred -= energy_transferred
            if won_by_fold:
                stats.losses_by_fold += 1

        stats.best_hand_rank = max(stats.best_hand_rank, fish_hand_rank)
        stats._total_hand_rank += fish_hand_rank
        stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

        self.total_plant_poker_games += 1
        try:
            self._save_poker_totals()
        except Exception as error:  # pragma: no cover - defensive logging
            logger.error(f"Failed to save poker totals: {error}", exc_info=True)

    def record_mixed_poker_energy_transfer(
        self,
        energy_to_fish: float,
        is_plant_game: bool = True,
    ) -> None:
        """Record energy transfer from a mixed poker game (fish + plants).

        Args:
            energy_to_fish: Net energy transferred to fish (positive = fish gained from plants,
                           negative = plants gained from fish)
            is_plant_game: Whether this game involved plants (for counting)
        """
        self.total_plant_poker_energy_transferred += energy_to_fish
        if is_plant_game:
            self.total_plant_poker_games += 1
            try:
                self._save_poker_totals()
            except Exception as error:  # pragma: no cover - defensive logging
                logger.error(f"Failed to save poker totals: {error}", exc_info=True)

    def _update_tie_stats(self, algo_id: Optional[int], hand: "PokerHand") -> None:
        if algo_id is not None and algo_id in self.poker_stats:
            stats = self.poker_stats[algo_id]
            stats.total_games += 1
            stats.total_ties += 1
            if hand is not None:
                stats._total_hand_rank += hand.rank_value
                stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

    def _update_winner_stats(
        self,
        winner_id: int,
        winner_algo_id: Optional[int],
        amount: float,
        winner_hand: "PokerHand",
        house_cut: float,
        result: Optional["PokerResult"],
        player1_algo_id: Optional[int],
        player2_algo_id: Optional[int],
    ) -> None:
        from core.poker.core import BettingAction

        if winner_algo_id is None or winner_algo_id not in self.poker_stats:
            return

        stats = self.poker_stats[winner_algo_id]
        stats.total_games += 1
        stats.total_wins += 1
        stats.total_energy_won += amount
        stats.total_house_cuts += house_cut / 2

        if winner_hand is not None:
            stats.best_hand_rank = max(stats.best_hand_rank, winner_hand.rank_value)
            stats._total_hand_rank += winner_hand.rank_value
            stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

        if result is None:
            return

        stats._total_pot_size += result.final_pot
        stats.avg_pot_size = stats._total_pot_size / stats.total_games

        if result.won_by_fold:
            stats.won_by_fold += 1
        else:
            stats.won_at_showdown += 1
            stats.showdown_count += 1

        winner_on_button = (
            (winner_algo_id == player1_algo_id and result.button_position == 1)
            or (winner_algo_id == player2_algo_id and result.button_position == 2)
        )

        if winner_on_button:
            stats.button_games += 1
            stats.button_wins += 1
        else:
            stats.non_button_games += 1
            stats.non_button_wins += 1

        for player, action, _ in result.betting_history:
            if (player == 1 and winner_algo_id == player1_algo_id) or (
                player == 2 and winner_algo_id == player2_algo_id
            ):
                if action == BettingAction.RAISE:
                    stats.total_raises += 1
                elif action == BettingAction.CALL:
                    stats.total_calls += 1

    def _update_loser_stats(
        self,
        loser_algo_id: Optional[int],
        amount: float,
        loser_hand: "PokerHand",
        house_cut: float,
        result: Optional["PokerResult"],
        player1_algo_id: Optional[int],
        player2_algo_id: Optional[int],
    ) -> None:
        from core.poker.core import BettingAction

        if loser_algo_id is None or loser_algo_id not in self.poker_stats:
            return

        stats = self.poker_stats[loser_algo_id]
        stats.total_games += 1
        stats.total_losses += 1
        stats.total_energy_lost += amount
        stats.total_house_cuts += house_cut / 2

        if loser_hand is not None:
            stats._total_hand_rank += loser_hand.rank_value
            stats.avg_hand_rank = stats._total_hand_rank / stats.total_games

        if result is None:
            return

        stats._total_pot_size += result.final_pot
        stats.avg_pot_size = stats._total_pot_size / stats.total_games

        loser_folded = (
            (loser_algo_id == player1_algo_id and result.player1_folded)
            or (loser_algo_id == player2_algo_id and result.player2_folded)
        )

        if loser_folded:
            stats.folds += 1
            if result.total_rounds == 0:
                stats.preflop_folds += 1
            else:
                stats.postflop_folds += 1
        else:
            stats.showdown_count += 1

        loser_on_button = (
            (loser_algo_id == player1_algo_id and result.button_position == 1)
            or (loser_algo_id == player2_algo_id and result.button_position == 2)
        )

        if loser_on_button:
            stats.button_games += 1
        else:
            stats.non_button_games += 1

        for player, action, _ in result.betting_history:
            if (player == 1 and loser_algo_id == player1_algo_id) or (
                player == 2 and loser_algo_id == player2_algo_id
            ):
                if action == BettingAction.RAISE:
                    stats.total_raises += 1
                elif action == BettingAction.CALL:
                    stats.total_calls += 1

    def _log_poker_event(
        self,
        winner_id: int,
        loser_id: int,
        amount: float,
        winner_hand: "PokerHand",
        loser_hand: "PokerHand",
    ) -> None:
        winner_desc = winner_hand.description if winner_hand is not None else "Unknown"
        loser_desc = loser_hand.description if loser_hand is not None else "Unknown"
        self._add_event(
            EcosystemEvent(
                frame=self._frame_provider(),
                event_type="poker",
                fish_id=winner_id,
                details=(
                    f"Won {amount:.1f} energy from fish {loser_id} "
                    f"({winner_desc} vs {loser_desc})"
                ),
            )
        )
