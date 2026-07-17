"""Task-neutral target observations and pursuit math for behavior graphs."""

from __future__ import annotations

import math
from dataclasses import dataclass

Vector = tuple[float, float]


@dataclass(frozen=True)
class TargetObservation:
    """Common target signals supplied by a domain adapter.

    The target may be food, a soccer ball, prey, or a waypoint.  Generic graph
    nodes use only these values and never inspect a domain entity directly.
    """

    target_vector: Vector
    target_velocity: Vector
    target_exists: bool
    threat_vector: Vector
    self_velocity: Vector
    self_speed: float
    energy_ratio: float

    @property
    def target_distance(self) -> float:
        return math.hypot(*self.target_vector)

    def to_values(self) -> dict[str, object]:
        return {
            "target_vector": self.target_vector,
            "target_velocity": self.target_velocity,
            "target_distance": self.target_distance,
            "target_exists": self.target_exists,
            "threat_vector": self.threat_vector,
            "self_velocity": self.self_velocity,
            "self_speed": self.self_speed,
            "energy_ratio": self.energy_ratio,
        }


def intercept_vector(observation: TargetObservation, speed: float) -> Vector:
    """Predict a pursuit vector using constant target/self velocities.

    The bounded first-order prediction is intentionally stable at zero speed
    and keeps the adapter-neutral primitive usable in food and soccer contexts.
    """
    if not observation.target_exists or speed <= 0.0:
        return 0.0, 0.0
    travel_time = observation.target_distance / speed
    relative_velocity = (
        observation.target_velocity[0] - observation.self_velocity[0],
        observation.target_velocity[1] - observation.self_velocity[1],
    )
    return (
        observation.target_vector[0] + relative_velocity[0] * travel_time,
        observation.target_vector[1] + relative_velocity[1] * travel_time,
    )


__all__ = ["TargetObservation", "Vector", "intercept_vector"]
