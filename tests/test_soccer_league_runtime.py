from __future__ import annotations

from core.config.simulation_config import SimulationConfig
from core.simulation.engine import SimulationEngine


def test_soccer_league_emits_rewards() -> None:
    config = SimulationConfig.headless_fast()
    soccer = config.soccer
    soccer.enabled = True
    soccer.match_every_frames = 1
    soccer.matches_per_tick = 1
    soccer.duration_frames = 400
    soccer.num_players = 6
    soccer.min_players = 6
    soccer.cooldown_matches = 0
    soccer.entry_fee_energy = 1.0
    soccer.reward_mode = "refill_to_max"
    soccer.repro_reward_mode = "credits"
    soccer.repro_credit_award = 1.0
    soccer.repro_credit_required = 1.0
    soccer.seed_base = 0

    engine = SimulationEngine(config=config, seed=123)
    engine.setup()

    events = []
    energy_rewarded = False
    repro_rewarded = False

    engine.update()
    events = engine.get_recent_soccer_events(max_age_frames=1000)
    for event in events:
        if event.get("skipped"):
            continue
        if any(delta > 0 for delta in event.get("energy_deltas", {}).values()):
            energy_rewarded = True
        if any(delta > 0 for delta in event.get("repro_credit_deltas", {}).values()):
            repro_rewarded = True

    assert events
    assert energy_rewarded
    assert repro_rewarded
