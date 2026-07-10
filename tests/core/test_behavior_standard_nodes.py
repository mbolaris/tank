"""Tests for the first production behavior-graph node vocabulary."""

from __future__ import annotations

import pytest

from core.behavior.graph import BehaviorGraph, GraphConnection, GraphNode
from core.behavior.nodes import NODE_REGISTRY, NodeRegistry
from core.behavior.standard_nodes import register_standard_nodes


def test_standard_nodes_register_once_and_have_typed_contracts() -> None:
    registry = NodeRegistry()
    register_standard_nodes(registry)
    register_standard_nodes(registry)

    assert [definition.node_type for definition in registry.definitions()] == [
        "context_vector_sensor",
        "normalize_vector",
    ]
    assert registry.get("normalize_vector").input_ports["vector"].value == "vector"
    assert registry.get("normalize_vector").output_type.value == "unit_vector"


def test_standard_graph_replays_context_vector_into_normalized_steering() -> None:
    graph = BehaviorGraph(
        (
            GraphNode("offset", "context_vector_sensor", {"field": "offset"}),
            GraphNode("direction", "normalize_vector", {}),
        ),
        (GraphConnection("offset", "direction", "vector"),),
        "direction",
    )
    compiled = graph.compile(NODE_REGISTRY, validate_outputs=True)

    assert compiled.evaluate({"offset": (3, 4)}) == pytest.approx((0.6, 0.8))
    assert compiled.evaluate({"offset": (0, 0)}) == (0.0, 0.0)
