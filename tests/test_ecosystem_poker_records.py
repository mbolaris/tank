import math

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
