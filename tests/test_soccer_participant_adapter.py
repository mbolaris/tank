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
        self.tank_id = f"tank_{fish_id}"
        self.energy = energy
        self.max_energy = max_energy
        self.energy_log: list[tuple[float, str]] = []

    def modify_energy(self, amount: float, source: str = "unknown") -> float:
        self.energy += amount
        self.energy_log.append((amount, source))
        return amount


def test_finalize_rewards_resolves_wrapped_participant_by_stable_identity():
    fish_left = _EnergyFish(1, energy=50.0, max_energy=100.0)
    fish_right = _EnergyFish(2, energy=60.0, max_energy=100.0)

    left = SoccerParticipant(
        participant_id="left_1",
        team="left",
        fish_id=fish_left.fish_id,
        tank_id=fish_left.tank_id,
        energy=fish_left.energy,
        max_energy=fish_left.max_energy,
    )
    right = SoccerParticipant(
        participant_id="right_1",
        team="right",
        fish_id=fish_right.fish_id,
        tank_id=fish_right.tank_id,
        energy=fish_right.energy,
        max_energy=fish_right.max_energy,
    )

    setup = create_soccer_match_from_participants([left, right], duration_frames=1, seed=123)
    match = setup.match

    match.winner_team = "left"

    finalize_soccer_match(
        match,
        seed=setup.seed,
        reward_mode="refill_to_max",
        source_resolver={
            (fish_left.fish_id, fish_left.tank_id): fish_left,
            (fish_right.fish_id, fish_right.tank_id): fish_right,
        },
    )

    assert match.player_map["left_1"] is not fish_left
    assert match.player_map["right_1"] is not fish_right
    assert fish_left.energy == 100.0
    assert fish_right.energy == 60.0

    # Retried full-time handling must not apply the settlement twice.
    finalize_soccer_match(
        match,
        seed=setup.seed,
        reward_mode="refill_to_max",
        source_resolver={
            (fish_left.fish_id, fish_left.tank_id): fish_left,
            (fish_right.fish_id, fish_right.tank_id): fish_right,
        },
    )
    assert fish_left.energy == 100.0
    assert fish_right.energy == 60.0
