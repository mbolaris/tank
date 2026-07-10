"""Tests for the dormant shared behavior-graph contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from core.behavior.nodes import (
    BehaviorNode,
    NodeCategory,
    NodeDefinition,
    NodeParameter,
    NodeRegistry,
    Scalar,
    ValueType,
)


@dataclass
class _TestNode:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters


def _factory(node_type: str, category: NodeCategory):
    def create(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
        return _TestNode(node_id, node_type, category, parameters)

    return create


def _definition(
    node_type: str,
    category: NodeCategory,
    output_type: ValueType,
    input_ports: Mapping[str, ValueType] | None = None,
) -> NodeDefinition:
    return NodeDefinition(
        node_type=node_type,
        category=category,
        input_ports=input_ports or {},
        output_type=output_type,
        factory=_factory(node_type, category),
    )


def test_definition_serialization_is_stable_and_port_metadata_is_immutable():
    definition = _definition(
        "choose_target",
        NodeCategory.SELECTOR,
        ValueType.ENTITY_REF,
        {"candidates": ValueType.ENTITY_REF, "urgency": ValueType.SCALAR},
    )

    assert definition.to_dict() == {
        "node_type": "choose_target",
        "category": "selector",
        "input_ports": {"candidates": "entity_ref", "urgency": "scalar"},
        "output_type": "entity_ref",
    }
    with pytest.raises(TypeError):
        definition.input_ports["extra"] = ValueType.BOOL  # type: ignore[index]


def test_registry_orders_definitions_and_rejects_duplicate_node_types():
    registry = NodeRegistry()
    registry.register(_definition("zeta", NodeCategory.SENSOR, ValueType.SCALAR))
    alpha = _definition("alpha", NodeCategory.SENSOR, ValueType.BOOL)
    registry.register(alpha)

    assert [definition.node_type for definition in registry.definitions()] == ["alpha", "zeta"]
    with pytest.raises(ValueError, match="already registered"):
        registry.register(alpha)


def test_registry_creates_and_serializes_nodes_with_one_common_envelope():
    registry = NodeRegistry()
    registry.register(_definition("energy_sensor", NodeCategory.SENSOR, ValueType.SCALAR))

    node = registry.create("energy_sensor", "energy-1", {"scale": Scalar(0.5)})

    assert registry.serialize(node) == {
        "id": "energy-1",
        "type": "energy_sensor",
        "parameters": {"scale": 0.5},
    }


def test_registry_rejects_factory_metadata_mismatch():
    registry = NodeRegistry()

    def wrong_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
        return _TestNode(node_id, "wrong", NodeCategory.SENSOR, parameters)

    registry.register(
        NodeDefinition(
            "expected",
            NodeCategory.SENSOR,
            {},
            ValueType.SCALAR,
            wrong_factory,
        )
    )

    with pytest.raises(ValueError, match="returned node type"):
        registry.create("expected", "node-1", {})


def test_registry_accepts_only_exactly_typed_connections():
    registry = NodeRegistry()
    registry.register(_definition("energy_sensor", NodeCategory.SENSOR, ValueType.SCALAR))
    registry.register(
        _definition(
            "threshold",
            NodeCategory.SELECTOR,
            ValueType.BOOL,
            {"value": ValueType.SCALAR},
        )
    )
    registry.register(_definition("target_sensor", NodeCategory.SENSOR, ValueType.ENTITY_REF))

    registry.validate_connection("energy_sensor", "threshold", "value")
    with pytest.raises(TypeError, match="Cannot connect"):
        registry.validate_connection("target_sensor", "threshold", "value")
    with pytest.raises(KeyError, match="no input port"):
        registry.validate_connection("energy_sensor", "threshold", "missing")


@pytest.mark.parametrize("node_type", ["", "not a node", "with-dash", "1starts_with_digit"])
def test_definition_rejects_invalid_node_type_names(node_type: str):
    with pytest.raises(ValueError, match="identifiers"):
        _definition(node_type, NodeCategory.SENSOR, ValueType.SCALAR)


def test_definition_rejects_invalid_port_metadata():
    with pytest.raises(ValueError, match="valid identifiers"):
        _definition(
            "sensor", NodeCategory.SENSOR, ValueType.SCALAR, {"not a port": ValueType.SCALAR}
        )
    with pytest.raises(TypeError, match="ValueType"):
        _definition("sensor", NodeCategory.SENSOR, ValueType.SCALAR, {"value": "scalar"})  # type: ignore[dict-item]
