import random

import pytest

from core.mixed_poker.interaction import MixedPokerInteraction
from core.poker.betting.actions import BettingAction


class _AllInStrategy:
    def decide_action(
        self,
        *,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng=None,
    ):
        if player_energy <= 0:
            return BettingAction.CHECK, 0.0
        return BettingAction.RAISE, float(player_energy)


class _DummyFish:
    """Minimal fish-like player that dies irreversibly at energy <= 0.

    This mirrors the real fish behavior (death state is not reversed by later gains),
    which is what makes mid-hand energy deductions problematic.
    """

    def __init__(self, fish_id: int, *, energy: float) -> None:
        self.fish_id = int(fish_id)
        self.energy = float(energy)
        self.max_energy = 9999.0
        self.size = 1.0
        self.genome = object()
        self.poker_cooldown = 0
        self._dead = False
        self._strategy = _AllInStrategy()

    def get_poker_id(self) -> int:
        return self.fish_id

    def get_poker_aggression(self) -> float:
        return 0.5

    def get_poker_strategy(self):
        return self._strategy

    def modify_energy(self, amount: float) -> None:
        self.energy = max(0.0, self.energy + float(amount))
        if self.energy <= 0:
            self._dead = True

    def is_dead(self) -> bool:
        return self._dead


def test_poker_winner_not_killed_mid_hand_settlement():
    f1 = _DummyFish(1, energy=20.0)
    f2 = _DummyFish(2, energy=20.0)

    poker = MixedPokerInteraction([f1, f2], rng=random.Random(0))
    assert poker.play_poker()
    assert poker.result is not None

    # Both players should shove their full stacks, producing a deterministic pot.
    assert poker.result.total_pot == pytest.approx(40.0)

    if poker.result.is_tie:
        winner_ids = set(poker.result.tied_player_ids)
    else:
        winner_ids = {poker.result.winner_id}

    for fish in (f1, f2):
        if fish.get_poker_id() in winner_ids:
            assert not fish.is_dead(), "Winning players should not die mid-hand"
        else:
            assert fish.is_dead()
