"""Regression test for the poker-benchmark fish selection.

The periodic/comprehensive poker benchmarks ranked fish by
``f.components.poker_stats.total_winnings`` - but ``AgentComponents`` has no
``poker_stats`` and ``FishPokerStats`` has no ``total_winnings``, so the sort key
was always 0 and "top fish" was just input order. The fitness now comes from
``fish.poker_stats.get_net_energy()`` (ARCHITECTURE_REVIEW item 5).
"""

from __future__ import annotations

from core.fish.poker_stats_component import FishPokerStats
from core.poker.evaluation.periodic_benchmark import _poker_net_energy


class _StubFish:
    def __init__(self, poker_stats: FishPokerStats | None) -> None:
        self.poker_stats = poker_stats


def test_net_energy_is_zero_when_unplayed():
    assert _poker_net_energy(_StubFish(None)) == 0.0


def test_net_energy_uses_won_minus_lost_minus_cuts():
    ps = FishPokerStats(total_energy_won=100.0, total_energy_lost=30.0, total_house_cuts_paid=5.0)
    assert _poker_net_energy(_StubFish(ps)) == 65.0


def test_sort_ranks_by_net_energy_not_input_order():
    weak = _StubFish(FishPokerStats(total_energy_won=10.0, total_energy_lost=8.0))  # +2
    strong = _StubFish(FishPokerStats(total_energy_won=200.0, total_energy_lost=20.0))  # +180
    unplayed = _StubFish(None)  # 0

    # Deliberately not already in fitness order.
    ordered = sorted([weak, unplayed, strong], key=_poker_net_energy, reverse=True)

    assert ordered[0] is strong
    assert ordered[-1] is unplayed
