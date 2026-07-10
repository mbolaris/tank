"""Small, domain-neutral nodes for the first behavior-graph vertical slice."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from core.behavior.nodes import (
    NODE_REGISTRY,
    BehaviorNode,
    NodeCategory,
    NodeDefinition,
    NodeParameter,
    NodeRegistry,
    NodeValue,
    Scalar,
    UnitVector,
    ValueType,
)
from core.behavior.primitives.steering import normalized_components


@dataclass
class _ContextVectorSensor:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def sense(self, context: object) -> NodeValue:
        if not isinstance(context, Mapping):
            raise TypeError("context_vector_sensor requires a mapping context")
        field = self.parameters.get("field")
        if not isinstance(field, str):
            raise ValueError("context_vector_sensor requires a string 'field' parameter")
        raw_value = context.get(field)
        if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
            raise TypeError(f"context field {field!r} must contain a two-component vector")
        components = cast(Sequence[object], raw_value)
        if len(components) != 2:
            raise TypeError(f"context field {field!r} must contain a two-component vector")
        try:
            if any(isinstance(component, bool) for component in components):
                raise TypeError
            x, y = float(cast(str | float | int, components[0])), float(
                cast(str | float | int, components[1])
            )
        except (TypeError, ValueError) as exc:
            raise TypeError(f"context field {field!r} must contain numeric components") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"context field {field!r} must contain finite components")
        return (Scalar(x), Scalar(y))


@dataclass
class _NormalizeVectorSteering:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> UnitVector:
        raw_vector = inputs["vector"]
        if not isinstance(raw_vector, tuple) or len(raw_vector) != 2:
            raise TypeError("normalize_vector requires a two-component vector")
        x, y = normalized_components(float(raw_vector[0]), float(raw_vector[1]))
        return UnitVector((Scalar(x), Scalar(y)))


def _context_vector_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _ContextVectorSensor(
        node_id,
        "context_vector_sensor",
        NodeCategory.SENSOR,
        MappingProxyType(dict(parameters)),
    )


def _normalize_vector_factory(
    node_id: str, parameters: Mapping[str, NodeParameter]
) -> BehaviorNode:
    return _NormalizeVectorSteering(
        node_id,
        "normalize_vector",
        NodeCategory.STEERING,
        MappingProxyType(dict(parameters)),
    )


def register_standard_nodes(registry: NodeRegistry = NODE_REGISTRY) -> None:
    """Register the small standard node vocabulary exactly once per registry."""
    definitions = (
        NodeDefinition(
            "context_vector_sensor",
            NodeCategory.SENSOR,
            {},
            ValueType.VECTOR,
            _context_vector_factory,
        ),
        NodeDefinition(
            "normalize_vector",
            NodeCategory.STEERING,
            {"vector": ValueType.VECTOR},
            ValueType.UNIT_VECTOR,
            _normalize_vector_factory,
        ),
    )
    for definition in definitions:
        try:
            registry.get(definition.node_type)
        except KeyError:
            registry.register(definition)


__all__ = ["register_standard_nodes"]
