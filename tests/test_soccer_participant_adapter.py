"""Tests for soccer participant adaptation behavior."""

from __future__ import annotations

from core.minigames.soccer.evaluator import (
    create_soccer_match_from_participants,
    finalize_soccer_match,
)
from core.minigames.soccer.participant import SoccerParticipant


class _EnergyFish:
    def __init__(self, fish_id: int, *, energy: float, max_energy: float) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.max_energy = max_energy
        self.energy_log: list[tuple[float, str]] = []

    def modify_energy(self, amount: float, source: str = "unknown") -> float:
        self.energy += amount
        self.energy_log.append((amount, source))
        return amount


def test_finalize_rewards_target_source_entity_when_participant_wrapped():
    fish_left = _EnergyFish(1, energy=50.0, max_energy=100.0)
    fish_right = _EnergyFish(2, energy=60.0, max_energy=100.0)

    left = SoccerParticipant(participant_id="left_1", team="left", source_entity=fish_left)
    right = SoccerParticipant(participant_id="right_1", team="right", source_entity=fish_right)

    setup = create_soccer_match_from_participants([left, right], duration_frames=1, seed=123)
    match = setup.match

    match.winner_team = "left"

    finalize_soccer_match(match, seed=setup.seed, reward_mode="refill_to_max")

    assert match.player_map["left_1"] is fish_left
    assert match.player_map["right_1"] is fish_right
    assert fish_left.energy == 100.0
    assert fish_right.energy == 60.0
