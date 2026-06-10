"""Poker outcome recording for the ecosystem.

Translates poker outcome value objects into PokerStatsManager updates and
energy ledger entries. Extracted from core/ecosystem.py; EcosystemManager
keeps thin delegating facades, and energy recording goes back through the
manager so monkeypatched manager methods are honored.
"""

from typing import TYPE_CHECKING

from core.ecosystem_stats import (
    MixedPokerOutcomeRecord,
    PlantPokerOutcomeRecord,
    PokerOutcomeRecord,
)

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager


class PokerOutcomeRecorder:
    """Records poker game outcomes into poker stats and energy ledgers."""

    def __init__(self, manager: "EcosystemManager") -> None:
        self._manager = manager

    def record_poker_outcome_record(self, record: PokerOutcomeRecord) -> None:
        """Record a poker game outcome from a value object."""
        from typing import cast

        from core.mixed_poker.types import MixedPokerResult
        from core.poker.core import PokerHand

        winner_hand = cast(PokerHand, record.winner_hand)
        loser_hand = cast(PokerHand, record.loser_hand)
        result = cast(MixedPokerResult | None, record.result)
        self._manager.poker_manager.record_poker_outcome(
            record.winner_id,
            record.loser_id,
            record.winner_algo_id,
            record.loser_algo_id,
            record.amount,
            winner_hand,
            loser_hand,
            record.house_cut,
            result,
            record.player1_algo_id,
            record.player2_algo_id,
        )

    def record_plant_poker_game_record(self, record: PlantPokerOutcomeRecord) -> None:
        """Record a plant poker outcome from a value object."""
        self._manager.poker_manager.record_plant_poker_game(
            record.fish_id,
            record.plant_id,
            record.fish_won,
            record.energy_transferred,
            record.fish_hand_rank,
            record.plant_hand_rank,
            record.won_by_fold,
        )
        net_amount = record.energy_transferred if record.fish_won else -record.energy_transferred
        self._manager.record_plant_poker_energy_gain(net_amount)

    def record_mixed_poker_energy_transfer(
        self,
        energy_to_fish: float,
        is_plant_game: bool = True,
        winner_type: str = "",
    ) -> None:
        """Record energy transfer from a mixed poker game.

        Args:
            energy_to_fish: Net energy transferred to fish
            is_plant_game: Whether this game involved plants
            winner_type: "fish" or "plant" - who won the game
        """
        self._manager.poker_manager.record_mixed_poker_energy_transfer(
            energy_to_fish, winner_type=winner_type, is_plant_game=is_plant_game
        )
        self._manager.record_plant_poker_energy_gain(energy_to_fish)

    def record_mixed_poker_outcome_record(self, record: MixedPokerOutcomeRecord) -> None:
        """Record mixed poker outcome with correct per-economy house cut attribution."""
        self._manager.poker_manager.record_mixed_poker_energy_transfer(
            record.fish_delta,
            winner_type=record.winner_type,
            is_plant_game=True,
        )

        winner_is_fish = record.winner_type == "fish"
        house_cut = float(record.house_cut or 0.0)

        if record.fish_delta > 0:
            gross = record.fish_delta + (house_cut if winner_is_fish else 0.0)
            self._manager.record_energy_gain("poker_plant", gross)
            if winner_is_fish and house_cut > 0:
                self._manager.record_energy_burn("poker_house_cut", house_cut)
        elif record.fish_delta < 0:
            self._manager.record_energy_burn("poker_plant_loss", -record.fish_delta)

        if (not winner_is_fish) and house_cut > 0:
            self._manager.record_plant_energy_gain("poker", house_cut)
            self._manager.record_plant_energy_burn("poker_house_cut", house_cut)

    def record_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-fish poker."""
        self._manager.record_energy_gain("poker_fish", amount)

    def record_plant_poker_energy_gain(self, amount: float) -> None:
        """Track net energy fish gained from fish-vs-plant poker."""
        if amount >= 0:
            self._manager.record_energy_gain("poker_plant", amount)
        else:
            self._manager.record_energy_burn("poker_plant_loss", -amount)

    def record_auto_eval_energy_gain(self, amount: float) -> None:
        """Track energy awarded through auto-evaluation benchmarks."""
        self._manager.record_energy_gain("auto_eval", amount)
