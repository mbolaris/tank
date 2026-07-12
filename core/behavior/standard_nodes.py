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
    Bool,
    NodeCategory,
    NodeDefinition,
    NodeParameter,
    NodeParameterSpec,
    NodeRegistry,
    NodeValue,
    Scalar,
    UnitVector,
    ValueType,
)
from core.behavior.pursuit_nodes import intercept_target_definition
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
        raw_value = _context_value(context, self.parameters, "context_vector_sensor")
        if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
            raise TypeError("context_vector_sensor field must contain a two-component vector")
        components = cast(Sequence[object], raw_value)
        if len(components) != 2:
            raise TypeError("context_vector_sensor field must contain a two-component vector")
        try:
            if any(isinstance(component, bool) for component in components):
                raise TypeError
            x, y = float(cast(str | float | int, components[0])), float(
                cast(str | float | int, components[1])
            )
        except (TypeError, ValueError) as exc:
            raise TypeError("context_vector_sensor field must contain numeric components") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("context_vector_sensor field must contain finite components")
        return (Scalar(x), Scalar(y))


@dataclass
class _ContextScalarSensor:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def sense(self, context: object) -> NodeValue:
        value = _context_value(context, self.parameters, "context_scalar_sensor")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("context_scalar_sensor field must contain a numeric scalar")
        scalar = float(value)
        if not math.isfinite(scalar):
            raise ValueError("context_scalar_sensor field must contain a finite scalar")
        return Scalar(scalar)


@dataclass
class _ContextBoolSensor:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def sense(self, context: object) -> NodeValue:
        value = _context_value(context, self.parameters, "context_bool_sensor")
        if type(value) is not bool:
            raise TypeError("context_bool_sensor field must contain a boolean")
        return Bool(value)


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


@dataclass
class _InvertVectorSteering:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        x, y = _vector_components(inputs, "vector", self.node_type)
        return Scalar(-x), Scalar(-y)


@dataclass
class _ScaleVectorSteering:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        x, y = _vector_components(inputs, "vector", self.node_type)
        scale = _parameter_float(self.parameters, "scale", 1.0)
        return Scalar(x * scale), Scalar(y * scale)


@dataclass
class _WeightedVectorSteering:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> UnitVector:
        first_x, first_y = _vector_components(inputs, "first", self.node_type)
        second_x, second_y = _vector_components(inputs, "second", self.node_type)
        first_weight = _parameter_float(self.parameters, "first_weight", 1.0)
        second_weight = _parameter_float(self.parameters, "second_weight", 1.0)
        x, y = normalized_components(
            first_x * first_weight + second_x * second_weight,
            first_y * first_weight + second_y * second_weight,
        )
        return UnitVector((Scalar(x), Scalar(y)))


@dataclass
class _WeightedVectorBlend:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def steer(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        first_x, first_y = _vector_components(inputs, "first", self.node_type)
        second_x, second_y = _vector_components(inputs, "second", self.node_type)
        first_weight = _parameter_float(self.parameters, "first_weight", 1.0)
        second_weight = _parameter_float(self.parameters, "second_weight", 1.0)
        return (
            Scalar(first_x * first_weight + second_x * second_weight),
            Scalar(first_y * first_weight + second_y * second_weight),
        )


@dataclass
class _ThresholdVectorSelector:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def _selected_port(self, inputs: Mapping[str, NodeValue]) -> tuple[str, float, float]:
        raw_value = inputs.get("value")
        if type(raw_value) is not float or not math.isfinite(raw_value):
            raise TypeError("threshold_vector_selector requires a finite scalar 'value'")
        threshold = _parameter_float(self.parameters, "threshold", 0.0)
        port = "when_true" if raw_value >= threshold else "when_false"
        return port, raw_value, threshold

    def select(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        selected_port, _value, _threshold = self._selected_port(inputs)
        return _vector_value(inputs, selected_port, self.node_type)

    def explain(self, inputs: Mapping[str, NodeValue]) -> Mapping[str, object]:
        """Report which port was selected and the compared value/threshold.

        Shares ``_selected_port`` with ``select`` so this can never disagree
        with what the node actually did, even as ``threshold`` mutates.
        """
        selected_port, value, threshold = self._selected_port(inputs)
        return {"selected_port": selected_port, "value": value, "threshold": threshold}


@dataclass
class _PriorityVectorSelector:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def select(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        primary = _vector_value(inputs, "primary", self.node_type)
        if primary != (0.0, 0.0):
            return primary
        return _vector_value(inputs, "fallback", self.node_type)

    def explain(self, inputs: Mapping[str, NodeValue]) -> Mapping[str, object]:
        """Report whether primary or fallback was selected (mirrors select())."""
        primary = _vector_value(inputs, "primary", self.node_type)
        return {"selected_port": "primary" if primary != (0.0, 0.0) else "fallback"}


def _context_value(
    context: object,
    parameters: Mapping[str, NodeParameter],
    node_type: str,
) -> object:
    if not isinstance(context, Mapping):
        raise TypeError(f"{node_type} requires a mapping context")
    field = parameters.get("field")
    if not isinstance(field, str):
        raise ValueError(f"{node_type} requires a string 'field' parameter")
    return context.get(field)


def _parameter_float(parameters: Mapping[str, NodeParameter], name: str, default: float) -> float:
    value = parameters.get(name, Scalar(default))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Node parameter {name!r} must be a finite scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Node parameter {name!r} must be a finite scalar")
    return result


def _vector_value(
    inputs: Mapping[str, NodeValue], port: str, node_type: str
) -> tuple[Scalar, Scalar]:
    value = inputs.get(port)
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not all(type(component) is float and math.isfinite(component) for component in value)
    ):
        raise TypeError(f"{node_type} requires a finite two-component vector '{port}'")
    return Scalar(float(value[0])), Scalar(float(value[1]))


def _vector_components(
    inputs: Mapping[str, NodeValue], port: str, node_type: str
) -> tuple[float, float]:
    return _vector_value(inputs, port, node_type)


def _context_sensor_factory(
    node_type: str,
    node_class: type[_ContextScalarSensor] | type[_ContextBoolSensor],
    node_id: str,
    parameters: Mapping[str, NodeParameter],
) -> BehaviorNode:
    return node_class(
        node_id,
        node_type,
        NodeCategory.SENSOR,
        MappingProxyType(dict(parameters)),
    )


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


def _invert_vector_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _InvertVectorSteering(
        node_id,
        "invert_vector",
        NodeCategory.STEERING,
        MappingProxyType(dict(parameters)),
    )


def _scale_vector_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _ScaleVectorSteering(
        node_id,
        "scale_vector",
        NodeCategory.STEERING,
        MappingProxyType(dict(parameters)),
    )


def _weighted_vector_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _WeightedVectorSteering(
        node_id,
        "weighted_vector",
        NodeCategory.STEERING,
        MappingProxyType(dict(parameters)),
    )


def _weighted_vector_blend_factory(
    node_id: str, parameters: Mapping[str, NodeParameter]
) -> BehaviorNode:
    return _WeightedVectorBlend(
        node_id,
        "weighted_vector_blend",
        NodeCategory.STEERING,
        MappingProxyType(dict(parameters)),
    )


def _threshold_vector_factory(
    node_id: str, parameters: Mapping[str, NodeParameter]
) -> BehaviorNode:
    return _ThresholdVectorSelector(
        node_id,
        "threshold_vector_selector",
        NodeCategory.SELECTOR,
        MappingProxyType(dict(parameters)),
    )


def _priority_vector_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
    return _PriorityVectorSelector(
        node_id,
        "priority_vector_selector",
        NodeCategory.SELECTOR,
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
            "context_scalar_sensor",
            NodeCategory.SENSOR,
            {},
            ValueType.SCALAR,
            lambda node_id, parameters: _context_sensor_factory(
                "context_scalar_sensor", _ContextScalarSensor, node_id, parameters
            ),
        ),
        NodeDefinition(
            "context_bool_sensor",
            NodeCategory.SENSOR,
            {},
            ValueType.BOOL,
            lambda node_id, parameters: _context_sensor_factory(
                "context_bool_sensor", _ContextBoolSensor, node_id, parameters
            ),
        ),
        NodeDefinition(
            "normalize_vector",
            NodeCategory.STEERING,
            {"vector": ValueType.VECTOR},
            ValueType.UNIT_VECTOR,
            _normalize_vector_factory,
        ),
        NodeDefinition(
            "invert_vector",
            NodeCategory.STEERING,
            {"vector": ValueType.VECTOR},
            ValueType.VECTOR,
            _invert_vector_factory,
        ),
        NodeDefinition(
            "scale_vector",
            NodeCategory.STEERING,
            {"vector": ValueType.VECTOR},
            ValueType.VECTOR,
            _scale_vector_factory,
            {"scale": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(3.0))},
        ),
        NodeDefinition(
            "weighted_vector",
            NodeCategory.STEERING,
            {"first": ValueType.VECTOR, "second": ValueType.VECTOR},
            ValueType.UNIT_VECTOR,
            _weighted_vector_factory,
            {
                "first_weight": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(3.0)),
                "second_weight": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(3.0)),
            },
        ),
        NodeDefinition(
            "weighted_vector_blend",
            NodeCategory.STEERING,
            {"first": ValueType.VECTOR, "second": ValueType.VECTOR},
            ValueType.VECTOR,
            _weighted_vector_blend_factory,
            {
                "first_weight": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(3.0)),
                "second_weight": NodeParameterSpec(Scalar(1.0), Scalar(0.0), Scalar(3.0)),
            },
        ),
        intercept_target_definition(),
        NodeDefinition(
            "threshold_vector_selector",
            NodeCategory.SELECTOR,
            {
                "value": ValueType.SCALAR,
                "when_true": ValueType.VECTOR,
                "when_false": ValueType.VECTOR,
            },
            ValueType.VECTOR,
            _threshold_vector_factory,
            {"threshold": NodeParameterSpec(Scalar(0.5), Scalar(0.0), Scalar(1.0))},
        ),
        NodeDefinition(
            "priority_vector_selector",
            NodeCategory.SELECTOR,
            {"primary": ValueType.VECTOR, "fallback": ValueType.VECTOR},
            ValueType.VECTOR,
            _priority_vector_factory,
        ),
    )
    for definition in definitions:
        try:
            registry.get(definition.node_type)
        except KeyError:
            registry.register(definition)


__all__ = ["register_standard_nodes"]
