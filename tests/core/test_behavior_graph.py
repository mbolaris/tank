"""Tests for dormant behavior-graph validation, compilation, and replay."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from core.behavior.graph import BehaviorGraph, BehaviorGraphError, GraphConnection, GraphNode
from core.behavior.nodes import (
    BehaviorNode,
    Bool,
    NodeCategory,
    NodeDefinition,
    NodeParameter,
    NodeRegistry,
    NodeValue,
    Scalar,
    ValueType,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "behavior_graphs" / "scalar_threshold_v1.json"


@dataclass
class _EnergySensor:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def sense(self, context: object) -> NodeValue:
        assert isinstance(context, Mapping)
        return Scalar(float(context[self.parameters["field"]]))


@dataclass
class _Threshold:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def select(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        return Bool(float(inputs["value"]) >= float(self.parameters["minimum"]))


@dataclass
class _InvalidEnergySensor:
    node_id: str
    node_type: str
    category: NodeCategory
    parameters: Mapping[str, NodeParameter]

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        return self.parameters

    def sense(self, context: object) -> NodeValue:
        return Bool(True)


def _registry(factory_calls: list[str] | None = None) -> NodeRegistry:
    registry = NodeRegistry()

    def sensor_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
        if factory_calls is not None:
            factory_calls.append(node_id)
        return _EnergySensor(node_id, "energy_sensor", NodeCategory.SENSOR, parameters)

    def threshold_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
        if factory_calls is not None:
            factory_calls.append(node_id)
        return _Threshold(node_id, "threshold", NodeCategory.SELECTOR, parameters)

    registry.register(
        NodeDefinition("energy_sensor", NodeCategory.SENSOR, {}, ValueType.SCALAR, sensor_factory)
    )
    registry.register(
        NodeDefinition(
            "threshold",
            NodeCategory.SELECTOR,
            {"value": ValueType.SCALAR},
            ValueType.BOOL,
            threshold_factory,
        )
    )
    return registry


def _invalid_output_registry() -> NodeRegistry:
    registry = NodeRegistry()

    def sensor_factory(node_id: str, parameters: Mapping[str, NodeParameter]) -> BehaviorNode:
        return _InvalidEnergySensor(node_id, "energy_sensor", NodeCategory.SENSOR, parameters)

    registry.register(
        NodeDefinition("energy_sensor", NodeCategory.SENSOR, {}, ValueType.SCALAR, sensor_factory)
    )
    return registry


def test_golden_graph_replay_compiles_once_and_replays_expected_outputs():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    graph = BehaviorGraph.from_dict(payload["graph"])
    factory_calls: list[str] = []
    compiled = graph.compile(_registry(factory_calls))

    assert factory_calls == ["energy", "fed"]
    assert [compiled.evaluate(frame["context"]) for frame in payload["replay"]] == [
        frame["output"] for frame in payload["replay"]
    ]
    assert factory_calls == ["energy", "fed"]


def test_graph_round_trip_is_canonical():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    graph = BehaviorGraph.from_dict(payload["graph"])

    assert BehaviorGraph.from_dict(graph.to_dict()) == graph


def test_compile_rejects_unknown_node_type_and_mismatched_port_type():
    unknown = BehaviorGraph(
        (GraphNode("missing", "missing_type", {}),),
        (),
        "missing",
    )
    with pytest.raises(BehaviorGraphError, match="unknown type"):
        unknown.compile(_registry())

    mismatch = BehaviorGraph(
        (
            GraphNode("energy", "energy_sensor", {"field": "energy"}),
            GraphNode("fed", "threshold", {"minimum": 0.5}),
        ),
        (GraphConnection("energy", "fed", "missing"),),
        "fed",
    )
    with pytest.raises(BehaviorGraphError, match="no input port"):
        mismatch.compile(_registry())


def test_graph_rejects_missing_required_input_port():
    graph = BehaviorGraph(
        (
            GraphNode("energy", "energy_sensor", {"field": "energy"}),
            GraphNode("fed", "threshold", {"minimum": 0.5}),
        ),
        (),
        "fed",
    )

    assert "required input 'fed'.value has no source" in graph.validate(_registry())
    with pytest.raises(BehaviorGraphError, match=r"required input 'fed'\.value"):
        graph.compile(_registry())


def test_compile_can_validate_runtime_output_contracts():
    graph = BehaviorGraph((GraphNode("energy", "energy_sensor", {}),), (), "energy")
    compiled = graph.compile(_invalid_output_registry(), validate_outputs=True)

    with pytest.raises(BehaviorGraphError, match="invalid scalar output"):
        compiled.evaluate({})


def test_graph_rejects_cycles_and_duplicate_input_sources():
    cyclic = {
        "nodes": [
            {"id": "left", "type": "energy_sensor", "parameters": {}},
            {"id": "right", "type": "threshold", "parameters": {}},
        ],
        "connections": [
            {"source": "left", "target": "right", "port": "value"},
            {"source": "right", "target": "left", "port": "value"},
        ],
        "output": "right",
    }
    with pytest.raises(BehaviorGraphError, match="cycle"):
        BehaviorGraph.from_dict(cyclic)

    duplicate = BehaviorGraph(
        (
            GraphNode("one", "energy_sensor", {}),
            GraphNode("two", "energy_sensor", {}),
            GraphNode("target", "threshold", {}),
        ),
        (
            GraphConnection("one", "target", "value"),
            GraphConnection("two", "target", "value"),
        ),
        "target",
    )
    assert "input 'target'.value has multiple sources" in duplicate.validate()
