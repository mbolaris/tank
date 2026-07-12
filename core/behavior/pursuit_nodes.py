"""Reusable target-pursuit nodes for domain-neutral behavior graphs."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from core.behavior.graph import BehaviorGraph
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
        self_speed = _scalar(inputs["self_speed"])
        speed_multiplier = float(self.parameters.get("speed_multiplier", Scalar(1.0)))
        speed = max(0.0, self_speed * speed_multiplier)
        if speed <= 0.0:
            return Scalar(0.0), Scalar(0.0)
        prediction_strength = float(self.parameters.get("prediction_strength", Scalar(1.0)))
        max_horizon = float(self.parameters.get("max_prediction_horizon", Scalar(100.0)))
        travel_time = min(math.hypot(target_x, target_y) / speed, max_horizon)
        lead_x = (target_vx - self_vx) * travel_time * prediction_strength
        lead_y = (target_vy - self_vy) * travel_time * prediction_strength
        return Scalar(target_x + lead_x), Scalar(target_y + lead_y)


def _components(value: NodeValue) -> tuple[float, float]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError("intercept_target requires finite two-component vectors")
    x, y = float(value[0]), float(value[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise TypeError("intercept_target requires finite two-component vectors")
    return x, y


def _scalar(value: NodeValue) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("intercept_target requires a finite scalar self_speed")
    result = float(value)
    if not math.isfinite(result):
        raise TypeError("intercept_target requires a finite scalar self_speed")
    return result


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
            "self_speed": ValueType.SCALAR,
        },
        ValueType.VECTOR,
        _factory,
        {
            "speed_multiplier": NodeParameterSpec(Scalar(1.0), Scalar(0.5), Scalar(1.5)),
            "prediction_strength": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(2.0)),
            "max_prediction_horizon": NodeParameterSpec(Scalar(100.0), Scalar(1.0), Scalar(500.0)),
        },
    )


def default_pursuit_module_graph() -> BehaviorGraph:
    """Fixed topology for the shared, independently-evolvable pursuit module.

    Both the food adapter (``tank_adapter.build_tank_behavior_observation``)
    and the soccer-ball adapter (``movement.ball_pursuit``) evaluate this SAME
    inherited/mutated graph with their own domain's ``TargetObservation`` -
    the module does not know or care which domain it is steering for. Its
    four evolvable parameters map onto the reusable-pursuit-module spec:
    speed calibration and prediction strength/horizon live on ``intercept_target``;
    pursuit commitment is ``scale_vector``'s existing ``scale`` parameter.
    """
    from core.behavior.standard_nodes import register_standard_nodes

    register_standard_nodes()
    return BehaviorGraph.from_dict(
        {
            "nodes": [
                {
                    "id": "target",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "target_vector"},
                },
                {
                    "id": "target_velocity",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "target_velocity"},
                },
                {
                    "id": "self_velocity",
                    "type": "context_vector_sensor",
                    "parameters": {"field": "self_velocity"},
                },
                {
                    "id": "self_speed",
                    "type": "context_scalar_sensor",
                    "parameters": {"field": "self_speed"},
                },
                {
                    "id": "intercept",
                    "type": "intercept_target",
                    "parameters": {
                        # Calibrate the domain adapter's actual speed rather than
                        # embedding a fish-specific assumed speed in the module.
                        "speed_multiplier": 1.0,
                        "prediction_strength": 1.0,
                        "max_prediction_horizon": 100.0,
                    },
                },
                {"id": "aimed", "type": "normalize_vector", "parameters": {}},
                {"id": "pursuit", "type": "scale_vector", "parameters": {"scale": 1.0}},
            ],
            "connections": [
                {"source": "target", "target": "intercept", "port": "target_vector"},
                {"source": "target_velocity", "target": "intercept", "port": "target_velocity"},
                {"source": "self_velocity", "target": "intercept", "port": "self_velocity"},
                {"source": "self_speed", "target": "intercept", "port": "self_speed"},
                {"source": "intercept", "target": "aimed", "port": "vector"},
                {"source": "aimed", "target": "pursuit", "port": "vector"},
            ],
            "output": "pursuit",
        }
    )


__all__ = ["default_pursuit_module_graph", "intercept_target_definition"]
