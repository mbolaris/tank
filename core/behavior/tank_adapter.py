"""Tank-specific observation adapter for the reusable behavior graph substrate.

The adapter is the only graph layer allowed to inspect a Fish or Environment.
Nodes receive a plain mapping of scalar, vector, and boolean observations, so
the same steering modules can later be fed by a soccer or navigation adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from core.algorithms.composable.food_selection import select_food_target
from core.behavior.graph import BehaviorGraph
from core.behavior.standard_nodes import register_standard_nodes
from core.behavior.targeting import TargetObservation
from core.entities import Crab, Fish

_SOCIAL_RADIUS = 120.0


@dataclass(frozen=True)
class TankBehaviorObservation:
    """Pure, serializable signals that graph nodes may consume."""

    values: Mapping[str, object]
    target_label: str | None


def build_tank_behavior_observation(fish: Fish) -> TankBehaviorObservation:
    """Build deterministic graph inputs without consuming simulation RNG."""
    food = select_food_target(fish) if fish.can_eat() else None
    food_vector = _offset(fish, food)
    threat = _nearest_threat(fish)
    threat_away_vector = _negated(_offset(fish, threat))
    cohesion, alignment, separation = _school_vectors(fish)
    energy_ratio = fish.energy / max(fish.max_energy, 1.0)
    target_observation = TargetObservation(
        target_vector=food_vector,
        target_velocity=(float(food.vel.x), float(food.vel.y)) if food is not None else (0.0, 0.0),
        target_exists=food is not None,
        threat_vector=threat_away_vector,
        self_velocity=(float(fish.vel.x), float(fish.vel.y)),
        energy_ratio=float(max(0.0, min(1.0, energy_ratio))),
    )
    target_label = "Food" if food is not None else None
    return TankBehaviorObservation(
        values={
            "food_vector": food_vector,
            "threat_away_vector": threat_away_vector,
            "energy_ratio": float(max(0.0, min(1.0, energy_ratio))),
            "cohesion_vector": cohesion,
            "alignment_vector": alignment,
            "separation_vector": separation,
            "current_velocity": (float(fish.vel.x), float(fish.vel.y)),
            "has_target": food is not None,
            **target_observation.to_values(),
        },
        target_label=target_label,
    )


def default_foraging_graph() -> BehaviorGraph:
    """Fixed topology for the first evolvable graph-backed foraging population."""
    register_standard_nodes()
    return BehaviorGraph.from_dict(
        {
            "nodes": [
                {
                    "id": "food",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "food_vector"},
                },
                {
                    "id": "threat",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "threat_away_vector"},
                },
                {
                    "id": "cohesion",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "cohesion_vector"},
                },
                {
                    "id": "energy",
                    "type": "context_scalar_sensor",
                    "parameters": {"field": "energy_ratio"},
                },
                {
                    "id": "target_exists",
                    "type": "context_bool_sensor",
                    "parameters": {"field": "has_target"},
                },
                {
                    "id": "urgency",
                    "type": "threshold_vector_selector",
                    "parameters": {"threshold": 0.35},
                },
                {
                    "id": "blend",
                    "type": "weighted_vector_blend",
                    "parameters": {"first_weight": 1.0, "second_weight": 0.2},
                },
                {"id": "priority", "type": "priority_vector_selector", "parameters": {}},
                {"id": "movement", "type": "normalize_vector", "parameters": {}},
            ],
            "connections": [
                {"source": "energy", "target": "urgency", "port": "value"},
                {"source": "cohesion", "target": "urgency", "port": "when_true"},
                {"source": "food", "target": "urgency", "port": "when_false"},
                {"source": "urgency", "target": "blend", "port": "first"},
                {"source": "cohesion", "target": "blend", "port": "second"},
                {"source": "threat", "target": "priority", "port": "primary"},
                {"source": "blend", "target": "priority", "port": "fallback"},
                {"source": "priority", "target": "movement", "port": "vector"},
            ],
            "output": "movement",
        }
    )


def _nearest_threat(fish: Fish) -> Any | None:
    candidates = [
        entity
        for entity in fish.environment.nearby_agents_by_type(fish, 200.0, Crab)
        if isinstance(entity, Crab)
    ]
    return min(candidates, key=lambda entity: _distance_squared(fish, entity), default=None)


def _school_vectors(
    fish: Fish,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    neighbors = [
        entity
        for entity in fish.environment.nearby_evolving_agents(fish, _SOCIAL_RADIUS)
        if isinstance(entity, Fish) and entity.fish_id != fish.fish_id and not entity.is_dead()
    ]
    if not neighbors:
        return (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)
    neighbors.sort(key=lambda entity: entity.fish_id)
    count = len(neighbors)
    cohesion = (
        sum(entity.pos.x for entity in neighbors) / count - fish.pos.x,
        sum(entity.pos.y for entity in neighbors) / count - fish.pos.y,
    )
    alignment = (
        sum(entity.vel.x for entity in neighbors) / count,
        sum(entity.vel.y for entity in neighbors) / count,
    )
    separation_x = separation_y = 0.0
    for neighbor in neighbors:
        dx, dy = fish.pos.x - neighbor.pos.x, fish.pos.y - neighbor.pos.y
        distance_sq = dx * dx + dy * dy
        if distance_sq > 0.0:
            separation_x += dx / distance_sq
            separation_y += dy / distance_sq
    return cohesion, alignment, (separation_x, separation_y)


def _offset(fish: Fish, entity: Any | None) -> tuple[float, float]:
    if entity is None:
        return 0.0, 0.0
    return float(entity.pos.x - fish.pos.x), float(entity.pos.y - fish.pos.y)


def _negated(vector: tuple[float, float]) -> tuple[float, float]:
    return -vector[0], -vector[1]


def _distance_squared(fish: Fish, entity: Any) -> float:
    dx, dy = entity.pos.x - fish.pos.x, entity.pos.y - fish.pos.y
    return float(dx * dx + dy * dy)


__all__ = ["TankBehaviorObservation", "build_tank_behavior_observation", "default_foraging_graph"]
