import pytest
from core.sim.events import AteFood, Moved, EnergyBurned, PokerGamePlayed
from core.sim.energy_ledger import EnergyLedger, EnergyDelta


@pytest.fixture
def ledger():
    return EnergyLedger()


def test_ate_food_delta(ledger):
    event = AteFood(
        entity_id=1, food_id=101, food_type="nectar", energy_gained=50.0, algorithm_id=5, frame=10
    )
    deltas = ledger.apply(event)

    assert len(deltas) == 1
    d = deltas[0]
    assert d.entity_id == 1
    assert d.delta == 50.0
    assert d.reason == "ate_food"
    assert d.metadata["food_type"] == "nectar"


def test_moved_delta(ledger):
    event = Moved(entity_id=2, distance=10.0, energy_cost=5.0, speed=2.0, frame=10)
    deltas = ledger.apply(event)

    assert len(deltas) == 1
    d = deltas[0]
    assert d.entity_id == 2
    assert d.delta == -5.0
    assert d.reason == "movement"
    assert d.metadata["speed"] == 2.0


def test_poker_win_delta(ledger):
    event = PokerGamePlayed(
        entity_id=3,
        energy_change=100.0,
        opponent_type="fish",
        won=True,
        hand_rank="Royal Flush",
        frame=20,
    )
    deltas = ledger.apply(event)

    assert len(deltas) == 1
    d = deltas[0]
    assert d.entity_id == 3
    assert d.delta == 100.0
    assert d.reason == "poker_game"


def test_poker_loss_delta(ledger):
    event = PokerGamePlayed(
        entity_id=4, energy_change=-50.0, opponent_type="plant", won=False, frame=20
    )
    deltas = ledger.apply(event)

    assert len(deltas) == 1
    d = deltas[0]
    assert d.entity_id == 4
    assert d.delta == -50.0
