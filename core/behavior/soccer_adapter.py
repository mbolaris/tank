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
    self_speed: float | None = None,
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
        self_speed=(
            max(0.0, float(self_speed))
            if self_speed is not None
            else max(0.0, (self_velocity[0] ** 2 + self_velocity[1] ** 2) ** 0.5)
        ),
        energy_ratio=max(0.0, min(1.0, energy_ratio)),
    )


def evaluate_soccer_pursuit(
    module: object,
    *,
    target_vector: Vector,
    target_velocity: Vector,
    self_velocity: Vector,
    self_speed: float,
    energy_ratio: float = 1.0,
) -> Vector | None:
    """Evaluate a pursuit graph for a soccer target and return its vector.

    Kept at the domain adapter boundary so the code-policy sandbox receives
    only numeric observations, never a mutable graph object.
    """
    compile_cached = getattr(module, "compile_cached", None)
    if not callable(compile_cached):
        return None
    observation = TargetObservation(
        target_vector=target_vector,
        target_velocity=target_velocity,
        target_exists=True,
        threat_vector=(0.0, 0.0),
        self_velocity=self_velocity,
        self_speed=max(0.0, float(self_speed)),
        energy_ratio=max(0.0, min(1.0, energy_ratio)),
    )
    output = compile_cached().evaluate(observation.to_values())
    if not isinstance(output, tuple) or len(output) != 2:
        return None
    return float(output[0]), float(output[1])


__all__ = ["build_soccer_target_observation", "evaluate_soccer_pursuit"]
