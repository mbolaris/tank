from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.config.simulation_config import SimulationConfig, SoccerConfig
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime
from core.minigames.soccer.rewards import apply_soccer_entry_fees
from core.simulation.engine import SimulationEngine


class DummyFish:
    def __init__(self, fish_id: int, energy: float, max_energy: float) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.max_energy = max_energy
        self.genome = None

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        if amount >= 0:
            applied = min(amount, self.max_energy - self.energy)
        else:
            applied = max(amount, -self.energy)
        self.energy += applied
        return applied


class DummyWorld:
    def __init__(self, fish: list[DummyFish]) -> None:
        self._fish = fish
        self.genome_code_pool = None

    def get_fish_list(self) -> list[DummyFish]:
        return list(self._fish)


def test_soccer_league_emits_rewards(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_create_match(participants, **kwargs):
        entry_fee_energy = float(kwargs.get("entry_fee_energy", 0.0))
        entry_fees = apply_soccer_entry_fees(participants, entry_fee_energy)

        team_size = len(participants) // 2
        left_team = participants[:team_size]
        right_team = participants[team_size:]

        player_map = {}
        for idx, entity in enumerate(left_team, 1):
            player_map[f"left_{idx}"] = entity
        for idx, entity in enumerate(right_team, 1):
            player_map[f"right_{idx}"] = entity

        teams = {
            "left": [entity.fish_id for entity in left_team],
            "right": [entity.fish_id for entity in right_team],
        }

        match_id = kwargs.get("match_id") or "soccer_test_match"

        class FakeMatch:
            def __init__(self, match_id, player_map, teams):
                self.match_id = match_id
                self.player_map = player_map
                self._teams = teams
                self.game_over = False
                self.current_frame = 0
                self.winner_team = "left"

            def step(self, num_steps: int = 1):
                self.current_frame += num_steps
                self.game_over = True
                return self.get_state()

            def get_state(self):
                return {
                    "winner_team": "left",
                    "score": {"left": 1, "right": 0},
                    "frame": self.current_frame,
                    "message": "Left wins",
                    "last_goal": None,
                    "teams": self._teams,
                }

        match = FakeMatch(match_id, player_map, teams)

        return SimpleNamespace(
            match=match,
            seed=kwargs.get("seed"),
            match_id=match_id,
            selected_count=len(participants),
            match_counter=kwargs.get("match_counter", 0),
            selection_seed=kwargs.get("selection_seed"),
            entry_fees=entry_fees,
        )

    import core.minigames.soccer.league_runtime as league_runtime

    monkeypatch.setattr(
        league_runtime,
        "create_soccer_match_from_participants",
        fake_create_match,
    )

    config = SimulationConfig.headless_fast()
    soccer = config.soccer
    soccer.enabled = True
    soccer.match_every_frames = 1
    soccer.matches_per_tick = 1
    soccer.cycles_per_frame = 5
    soccer.duration_frames = 10
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

    for _ in range(5):
        engine.update()
        events = engine.get_recent_soccer_events(max_age_frames=1000)
        for event in events:
            if event.get("skipped"):
                continue
            if any(delta > 0 for delta in event.get("energy_deltas", {}).values()):
                energy_rewarded = True
            if any(delta > 0 for delta in event.get("repro_credit_deltas", {}).values()):
                repro_rewarded = True
        if energy_rewarded and repro_rewarded:
            break

    assert events
    assert energy_rewarded
    assert repro_rewarded


def test_league_runtime_steps_are_bounded() -> None:
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        cycles_per_frame=2,
        duration_frames=50,
        min_players=2,
        num_players=2,
        cooldown_matches=0,
    )
    runtime = SoccerLeagueRuntime(config)
    world = DummyWorld([DummyFish(1, 50.0, 100.0), DummyFish(2, 50.0, 100.0)])

    runtime.tick(world, seed_base=3, cycle=1)
    live_state = runtime.get_live_state()

    assert live_state is not None
    assert live_state["frame"] == 2
    assert live_state["game_over"] is False


def test_league_runtime_deterministic_outcomes() -> None:
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        cycles_per_frame=3,
        duration_frames=6,
        min_players=2,
        num_players=2,
        cooldown_matches=0,
        entry_fee_energy=0.0,
        reward_mode="pot_payout",
    )

    def run_once() -> dict:
        runtime = SoccerLeagueRuntime(config)
        world = DummyWorld([DummyFish(1, 50.0, 100.0), DummyFish(2, 50.0, 100.0)])
        for cycle in range(1, 5):
            runtime.tick(world, seed_base=7, cycle=cycle)
            events = runtime.drain_events()
            if events:
                outcome = events[0]
                return {
                    "winner_team": outcome.winner_team,
                    "score_left": outcome.score_left,
                    "score_right": outcome.score_right,
                    "energy_deltas": outcome.energy_deltas,
                }
        return {}

    first = run_once()
    second = run_once()

    assert first
    assert first == second
