"""Tank-specific observation adapter for the reusable behavior graph substrate.

The adapter is the only graph layer allowed to inspect a Fish or Environment.
Nodes receive a plain mapping of scalar, vector, and boolean observations, so
the same steering modules can later be fed by a soccer or navigation adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.algorithms.composable.food_selection import select_food_target
from core.behavior.graph import BehaviorGraph
from core.behavior.standard_nodes import register_standard_nodes
from core.behavior.targeting import TargetObservation
from core.entities import Crab, Fish

_SOCIAL_RADIUS = 120.0

# Fallback for _urgency_threshold when a graph has no "urgency" node (or the
# node's threshold parameter is missing) - matches default_foraging_graph()'s
# own default so behavior is unchanged for the standard topology.
_DEFAULT_URGENCY_THRESHOLD = 0.35


class ForagingIntentKind(str, Enum):
    """What the default foraging graph's fixed topology actually selected.

    Mirrors the graph's own decision structure: the ``priority`` node always
    picks threat when it is nonzero; otherwise the ``urgency`` node picks
    food below its threshold and cohesion at or above it. THREAT and FOOD are
    survival-relevant; COHESION is leisure-tier (see
    ``core.movement.considerations.GraphBehaviorConsideration``, which yields
    to lower-priority drives such as soccer on COHESION).
    """

    THREAT = "threat_avoidance"
    FOOD = "food_pursuit"
    COHESION = "social_cohesion"


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


def _urgency_threshold(graph: BehaviorGraph, default: float = _DEFAULT_URGENCY_THRESHOLD) -> float:
    """Read the foraging graph's own mutable urgency threshold, if present.

    ``urgency`` is a ``threshold_vector_selector`` whose ``threshold``
    parameter is a mutable, evolvable ``NodeParameterSpec`` - it drifts away
    from its 0.35 default once graph-carrying fish are actually selected for.
    Reading it dynamically (rather than hardcoding 0.35) is what keeps
    classification correct as evolution proceeds.
    """
    node = next((candidate for candidate in graph.nodes if candidate.node_id == "urgency"), None)
    if node is None:
        return default
    value = node.parameters.get("threshold")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def classify_foraging_intent(
    observation: TankBehaviorObservation, graph: BehaviorGraph
) -> ForagingIntentKind:
    """Classify what the foraging graph's fixed topology currently selects.

    Mirrors the graph's own node structure exactly (see ``default_foraging_graph``):
    the ``priority`` node picks threat whenever it is nonzero; otherwise the
    ``urgency`` node picks food below its threshold and cohesion at or above
    it. This is the single source of truth for that classification - both
    movement arbitration (``core.movement.considerations.GraphBehaviorConsideration``)
    and the inspector's Behavior Lens call this instead of independently
    re-deriving it, so they cannot disagree.
    """
    threat = observation.values["threat_away_vector"]
    if isinstance(threat, tuple) and len(threat) == 2 and (threat[0] != 0.0 or threat[1] != 0.0):
        return ForagingIntentKind.THREAT
    raw_energy_ratio = observation.values["energy_ratio"]
    energy_ratio = float(raw_energy_ratio) if isinstance(raw_energy_ratio, (int, float)) else 0.0
    if energy_ratio < _urgency_threshold(graph):
        return ForagingIntentKind.FOOD
    return ForagingIntentKind.COHESION


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


__all__ = [
    "ForagingIntentKind",
    "TankBehaviorObservation",
    "build_tank_behavior_observation",
    "classify_foraging_intent",
    "default_foraging_graph",
]
