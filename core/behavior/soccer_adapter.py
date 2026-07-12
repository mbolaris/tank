"""Soccer-facing adapter for the shared target observation contract."""

from __future__ import annotations

from core.behavior.targeting import TargetObservation, Vector


def build_soccer_target_observation(
    *,
    self_position: Vector,
    self_velocity: Vector,
    ball_position: Vector | None,
    ball_velocity: Vector = (0.0, 0.0),
    threat_vector: Vector = (0.0, 0.0),
    energy_ratio: float = 1.0,
) -> TargetObservation:
    """Adapt ball state to the same contract used by food pursuit."""
    target_exists = ball_position is not None
    target_vector = (
        (ball_position[0] - self_position[0], ball_position[1] - self_position[1])
        if ball_position is not None
        else (0.0, 0.0)
    )
    return TargetObservation(
        target_vector=target_vector,
        target_velocity=ball_velocity if target_exists else (0.0, 0.0),
        target_exists=target_exists,
        threat_vector=threat_vector,
        self_velocity=self_velocity,
        energy_ratio=max(0.0, min(1.0, energy_ratio)),
    )


__all__ = ["build_soccer_target_observation"]
