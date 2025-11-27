"""Unit tests for the PokerSystem helper."""

from types import SimpleNamespace

from core.poker_system import PokerSystem


class DummyEngine:
    """Minimal engine stub for PokerSystem tests."""

    def __init__(self) -> None:
        self.frame_count = 5
        self.added_entities = []

    def add_entity(self, entity):
        self.added_entities.append(entity)


class DummyOffspring:
    pass


def _base_result(**overrides):
    defaults = {
        "winner_id": -1,
        "loser_id": -1,
        "player_ids": [1, 2],
        "loser_ids": [2],
        "player_hands": [SimpleNamespace(description="Pair of Aces"), SimpleNamespace(description="Two Pair")],
        "hand1": SimpleNamespace(description="Pair of Aces"),
        "hand2": SimpleNamespace(description="Two Pair"),
        "winner_actual_gain": 0.0,
        "energy_transferred": 0.0,
        "reproduction_occurred": False,
        "offspring": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _poker(result):
    return SimpleNamespace(
        result=result,
        fish1=SimpleNamespace(fish_id=1),
        fish2=SimpleNamespace(fish_id=2),
        hand1=result.hand1,
        hand2=result.hand2,
    )


def test_add_poker_event_records_tie_message():
    engine = DummyEngine()
    system = PokerSystem(engine, max_events=10)

    tie_result = _base_result(winner_id=-1, loser_id=-1)
    poker = _poker(tie_result)

    system.add_poker_event(poker)

    event = system.poker_events[-1]
    assert event["winner_id"] == -1
    assert event["loser_id"] == -1
    assert "TIE" in event["message"]
    assert event["frame"] == engine.frame_count


def test_add_poker_event_records_win_message():
    engine = DummyEngine()
    system = PokerSystem(engine, max_events=10)

    result = _base_result(winner_id=1, loser_id=2, winner_actual_gain=12.5, energy_transferred=7.5)
    poker = _poker(result)

    system.add_poker_event(poker)

    event = system.poker_events[-1]
    assert event["winner_id"] == 1
    assert event["loser_id"] == 2
    assert "+12.5" in event["message"]
    assert event["energy_transferred"] == 7.5


def test_handle_poker_result_adds_offspring():
    engine = DummyEngine()
    system = PokerSystem(engine, max_events=10)

    offspring = DummyOffspring()
    result = _base_result(
        winner_id=1,
        loser_id=2,
        energy_transferred=3.0,
        reproduction_occurred=True,
        offspring=offspring,
    )
    poker = _poker(result)

    system.handle_poker_result(poker)

    assert offspring in engine.added_entities
    assert len(system.poker_events) == 1


def test_plant_event_adds_metadata():
    engine = DummyEngine()
    system = PokerSystem(engine, max_events=10)

    system.add_plant_poker_event(
        fish_id=3,
        plant_id=8,
        fish_won=False,
        fish_hand="Two Pair",
        plant_hand="Flush",
        energy_transferred=6.0,
    )

    event = system.poker_events[-1]
    assert event["is_plant"] is True
    assert event["plant_id"] == 8
    assert event["winner_id"] == -3

