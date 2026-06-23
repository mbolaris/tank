import math
import pytest

from core.ecosystem import EcosystemManager
from core.ecosystem_stats import MixedPokerOutcomeRecord
from core.worlds.contracts import EnergyDeltaRecord


def test_mixed_poker_outcome_record_tracks_house_cut():
    ecosystem = EcosystemManager()

    record = MixedPokerOutcomeRecord(
        fish_delta=5.0,
        plant_delta=-5.0,
        house_cut=2.0,
        winner_type="fish",
    )
    ecosystem.record_mixed_poker_outcome_record(record)

    assert math.isclose(
        ecosystem.energy_sources.get("poker_plant", 0.0),
        7.0,
        rel_tol=0,
        abs_tol=1e-9,
    )
    assert math.isclose(
        ecosystem.energy_burn.get("poker_house_cut", 0.0),
        2.0,
        rel_tol=0,
        abs_tol=1e-9,
    )


def test_record_fish_poker_game_increments_total():
    ecosystem = EcosystemManager()
    start = ecosystem.total_fish_poker_games
    ecosystem.record_fish_poker_game()
    ecosystem.record_fish_poker_game()
    assert ecosystem.total_fish_poker_games == start + 2


def test_poker_win_energy_delta_feeds_reported_fish_poker_source():
    ecosystem = EcosystemManager()

    ecosystem.ingest_energy_deltas(
        [EnergyDeltaRecord(entity_id="fish-1", delta=12.5, source="poker_win")]
    )

    assert math.isclose(ecosystem.energy_sources.get("poker_fish", 0.0), 12.5)
    assert ecosystem.energy_sources.get("poker", 0.0) == 0.0
    assert math.isclose(ecosystem.get_summary_stats([])["energy_from_poker"], 12.5)


def test_fish_poker_game_counter_advances_unit():
    """Verify that calling handle_poker_result on PokerSystem increments the ecosystem's
    total_fish_poker_games counter without needing a full 3000-frame simulation.
    """
    from core.worlds.registry import WorldRegistry
    from types import SimpleNamespace

    world = WorldRegistry.create_world("tank", seed=42, config={})
    world.reset(seed=42, config={})
    engine = world._engine
    eco = engine.ecosystem
    start = eco.total_fish_poker_games

    # Create a minimal PokerInteraction between two fish
    # Let's get two fish from the engine
    fish_list = list(engine._entity_manager.get_fish())
    assert len(fish_list) >= 2, "Need at least two fish to play poker"
    fish1, fish2 = fish_list[0], fish_list[1]

    # Mock the result of the PokerInteraction
    mock_result = SimpleNamespace(
        winner_id=fish1.get_poker_id(),
        loser_ids=[fish2.get_poker_id()],
        loser_id=fish2.get_poker_id(),
        is_tie=False,
        winner_hand=SimpleNamespace(description="Pair of Aces"),
        loser_hands=[SimpleNamespace(description="Two Pair")],
        energy_transferred=5.0,
        plant_count=0,
        fish_count=2,
        winner_type="fish",
        loser_types=["fish"],
        reproduction_occurred=False,
        offspring=None,
    )

    mock_poker = SimpleNamespace(
        result=mock_result,
        players=[fish1, fish2],
        fish1=fish1,
        fish2=fish2,
        hand1=mock_result.winner_hand,
        hand2=mock_result.loser_hands[0],
    )

    # Invoke handle_poker_result directly on poker_system
    engine.poker_system.handle_poker_result(mock_poker)

    assert eco.total_fish_poker_games == start + 1


@pytest.mark.slow
def test_fish_poker_game_counter_advances_in_sim():
    """Regression: fish-vs-fish poker games played but the global counter stayed
    at 0 because handle_poker_result never counted the completed game (its
    recorder, record_poker_outcome, was orphaned when poker moved to the
    multiplayer interaction). It must advance during a real seeded sim.
    """
    from core.worlds.registry import WorldRegistry

    world = WorldRegistry.create_world("tank", seed=42, config={})
    world.reset(seed=42, config={})
    eco = world._engine.ecosystem
    start = eco.total_fish_poker_games

    for _ in range(3000):
        world.step()

    # Delta (not absolute) so a persisted logs/poker_totals.json can't mask it.
    assert eco.total_fish_poker_games > start
