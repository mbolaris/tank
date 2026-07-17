"""Shared target-observation contracts for food and soccer pursuit."""

from __future__ import annotations

from core.behavior.soccer_adapter import build_soccer_target_observation
from core.behavior.targeting import TargetObservation, intercept_vector


def test_interception_uses_relative_target_velocity() -> None:
    observation = TargetObservation(
        target_vector=(10.0, 0.0),
        target_velocity=(2.0, 0.0),
        target_exists=True,
        threat_vector=(0.0, 0.0),
        self_velocity=(1.0, 0.0),
        self_speed=5.0,
        energy_ratio=0.5,
    )

    assert observation.target_distance == 10.0
    assert intercept_vector(observation, speed=5.0) == (12.0, 0.0)


def test_soccer_adapter_uses_the_shared_target_contract() -> None:
    observation = build_soccer_target_observation(
        self_position=(2.0, 3.0),
        self_velocity=(1.0, 0.0),
        ball_position=(8.0, 7.0),
        ball_velocity=(0.5, -0.5),
        energy_ratio=2.0,
    )

    assert observation.target_vector == (6.0, 4.0)
    assert observation.target_velocity == (0.5, -0.5)
    assert observation.self_speed == 1.0
    assert observation.energy_ratio == 1.0
    assert observation.to_values()["target_exists"] is True


def test_missing_food_is_not_classified_as_food_pursuit_when_hungry() -> None:
    from core.behavior.tank_adapter import (
        ForagingIntentKind,
        TankBehaviorObservation,
        classify_foraging_intent,
        default_foraging_graph,
    )

    observation = TankBehaviorObservation(
        values={
            "threat_away_vector": (0.0, 0.0),
            "energy_ratio": 0.1,
            "target_exists": False,
        },
        target_label=None,
    )

    assert (
        classify_foraging_intent(observation, default_foraging_graph()) is ForagingIntentKind.SEARCH
    )
