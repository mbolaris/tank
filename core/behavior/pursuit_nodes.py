"""Reusable target-pursuit nodes for domain-neutral behavior graphs."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from core.behavior.nodes import (
    BehaviorNode,
    NodeCategory,
    NodeDefinition,
    NodeParameter,
    NodeParameterSpec,
    NodeValue,
    Scalar,
    ValueType,
)


@dataclass
class _InterceptTargetSteering:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        target_x, target_y = _components(inputs["target_vector"])
        target_vx, target_vy = _components(inputs["target_velocity"])
        self_vx, self_vy = _components(inputs["self_velocity"])
        speed = float(self.parameters.get("speed", Scalar(1.0)))
        if speed <= 0.0:
            return Scalar(0.0), Scalar(0.0)
        travel_time = math.hypot(target_x, target_y) / speed
        return (
            Scalar(target_x + (target_vx - self_vx) * travel_time),
            Scalar(target_y + (target_vy - self_vy) * travel_time),
        )


def _components(value: NodeValue) -> tuple[float, float]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError("intercept_target requires finite two-component vectors")
    x, y = float(value[0]), float(value[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise TypeError("intercept_target requires finite two-component vectors")
    return x, y


def _factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _InterceptTargetSteering(
        node_id, "intercept_target", NodeCategory.STEERING, MappingProxyType(dict(parameters))
    )


def intercept_target_definition() -> NodeDefinition:
    """Return the registered contract for generic constant-velocity pursuit."""
    return NodeDefinition(
        "intercept_target",
        NodeCategory.STEERING,
        {
            "target_vector": ValueType.VECTOR,
            "target_velocity": ValueType.VECTOR,
            "self_velocity": ValueType.VECTOR,
        },
        ValueType.VECTOR,
        _factory,
        {"speed": NodeParameterSpec(Scalar(1.0), Scalar(0.1), Scalar(10.0))},
    )


__all__ = ["intercept_target_definition"]
