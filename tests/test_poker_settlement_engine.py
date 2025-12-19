import math


def _make_fish(fish_id: int):
    from core.algorithms import GreedyFoodSeeker
    from core.entities import Fish
    from core.genetics import Genome
    from core.movement_strategy import AlgorithmicMovement

    genome = Genome.random(use_algorithm=True)
    genome.behavioral.behavior_algorithm.value = GreedyFoodSeeker()

    return Fish(
        environment=None,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100 + fish_id * 10,
        y=100 + fish_id * 10,
        speed=2.0,
        genome=genome,
        generation=1,
        fish_id=fish_id,
        ecosystem=None,
    )


def test_settlement_two_player_house_cut_conservation():
    from core.fish_poker import PokerInteraction

    fish1 = _make_fish(1)
    fish2 = _make_fish(2)
    fish1.energy = fish1.max_energy * 0.5
    fish2.energy = fish2.max_energy * 0.5

    poker = PokerInteraction(fish1, fish2)
    before_total = fish1.energy + fish2.energy

    settlement = poker._settle_poker_energy(requested_bets=[2.0, 2.0], winner_idx=0)

    assert settlement.bets_paid == [2.0, 2.0]
    assert settlement.total_pot == 4.0

    expected_house_cut = PokerInteraction.calculate_house_cut(fish1.size, 2.0)
    assert math.isclose(settlement.house_cut, expected_house_cut, rel_tol=0, abs_tol=1e-9)

    after_total = fish1.energy + fish2.energy
    assert math.isclose(after_total, before_total - settlement.house_cut, rel_tol=0, abs_tol=1e-6)


def test_settlement_uses_actual_bets_paid_when_energy_insufficient():
    from core.fish_poker import PokerInteraction

    fish1 = _make_fish(1)
    fish2 = _make_fish(2)
    fish1.energy = 3.0
    fish2.energy = 50.0

    poker = PokerInteraction(fish1, fish2)
    settlement = poker._settle_poker_energy(requested_bets=[10.0, 10.0], winner_idx=1)

    assert math.isclose(settlement.bets_paid[0], 3.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(settlement.bets_paid[1], 10.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(settlement.total_pot, 13.0, rel_tol=0, abs_tol=1e-9)


def test_settlement_multiplayer_tie_splits_pot_no_house_cut():
    from core.fish_poker import PokerInteraction

    fish = [_make_fish(i) for i in range(1, 4)]
    for f in fish:
        f.energy = f.max_energy * 0.5

    poker = PokerInteraction(*fish)
    before_total = sum(f.energy for f in fish)

    settlement = poker._settle_poker_energy(
        requested_bets=[2.0, 2.0, 2.0],
        winner_idx=None,
        tied_indices=[0, 1],
    )

    assert math.isclose(settlement.house_cut, 0.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(settlement.total_pot, 6.0, rel_tol=0, abs_tol=1e-9)

    after_total = sum(f.energy for f in fish)
    assert math.isclose(after_total, before_total, rel_tol=0, abs_tol=1e-6)
    assert settlement.net_deltas[2] < 0
    assert settlement.net_deltas[0] > 0
    assert settlement.net_deltas[1] > 0
