import math

from core.ecosystem import EcosystemManager
from core.ecosystem_stats import MixedPokerOutcomeRecord


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
