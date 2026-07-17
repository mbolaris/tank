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
        "context_bool_sensor",
        "context_scalar_sensor",
        "context_vector_sensor",
        "intercept_target",
        "invert_vector",
        "normalize_vector",
        "priority_vector_selector",
        "scale_vector",
        "threshold_vector_selector",
        "weighted_vector",
        "weighted_vector_blend",
    ]
    assert registry.get("normalize_vector").input_ports["vector"].value == "vector"
    assert registry.get("normalize_vector").output_type.value == "unit_vector"
    assert registry.get("weighted_vector").input_ports["first"].value == "vector"
    assert registry.get("threshold_vector_selector").output_type.value == "vector"
    assert registry.get("scale_vector").parameter_specs["scale"].maximum == 3.0


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


def test_threshold_selector_and_weighted_steering_form_typed_vertical_slice() -> None:
    graph = BehaviorGraph(
        (
            GraphNode("energy", "context_scalar_sensor", {"field": "energy"}),
            GraphNode("target", "context_vector_sensor", {"field": "target"}),
            GraphNode("fallback", "context_vector_sensor", {"field": "fallback"}),
            GraphNode("choice", "threshold_vector_selector", {"threshold": 0.5}),
            GraphNode(
                "direction",
                "weighted_vector",
                {"first_weight": 2.0, "second_weight": 1.0},
            ),
        ),
        (
            GraphConnection("energy", "choice", "value"),
            GraphConnection("target", "choice", "when_true"),
            GraphConnection("fallback", "choice", "when_false"),
            GraphConnection("choice", "direction", "first"),
            GraphConnection("fallback", "direction", "second"),
        ),
        "direction",
    )
    compiled = graph.compile(NODE_REGISTRY, validate_outputs=True)

    assert compiled.evaluate(
        {"energy": 0.8, "target": (1, 0), "fallback": (0, 1)}
    ) == pytest.approx((0.894427, 0.447214), abs=1e-6)
    assert compiled.evaluate(
        {"energy": 0.2, "target": (1, 0), "fallback": (0, 1)}
    ) == pytest.approx((0.0, 1.0))


def test_context_scalar_sensor_rejects_boolean_values() -> None:
    graph = BehaviorGraph(
        (GraphNode("energy", "context_scalar_sensor", {"field": "energy"}),),
        (),
        "energy",
    )
    compiled = graph.compile(NODE_REGISTRY, validate_outputs=True)

    with pytest.raises(TypeError, match="numeric scalar"):
        compiled.evaluate({"energy": True})


def test_intercept_target_node_is_domain_neutral() -> None:
    graph = BehaviorGraph(
        (
            GraphNode("target", "context_vector_sensor", {"field": "target_vector"}),
            GraphNode("target_velocity", "context_vector_sensor", {"field": "target_velocity"}),
            GraphNode("self_velocity", "context_vector_sensor", {"field": "self_velocity"}),
            GraphNode("self_speed", "context_scalar_sensor", {"field": "self_speed"}),
            GraphNode("intercept", "intercept_target", {"speed_multiplier": 1.0}),
        ),
        (
            GraphConnection("target", "intercept", "target_vector"),
            GraphConnection("target_velocity", "intercept", "target_velocity"),
            GraphConnection("self_velocity", "intercept", "self_velocity"),
            GraphConnection("self_speed", "intercept", "self_speed"),
        ),
        "intercept",
    )

    assert graph.compile(NODE_REGISTRY, validate_outputs=True).evaluate(
        {
            "target_vector": (10, 0),
            "target_velocity": (2, 0),
            "self_velocity": (1, 0),
            "self_speed": 5.0,
        }
    ) == (12.0, 0.0)


def test_threshold_selector_explains_its_own_decision_via_node_trace() -> None:
    graph = BehaviorGraph(
        (
            GraphNode("energy", "context_scalar_sensor", {"field": "energy"}),
            GraphNode("target", "context_vector_sensor", {"field": "target"}),
            GraphNode("fallback", "context_vector_sensor", {"field": "fallback"}),
            GraphNode("choice", "threshold_vector_selector", {"threshold": 0.5}),
        ),
        (
            GraphConnection("energy", "choice", "value"),
            GraphConnection("target", "choice", "when_true"),
            GraphConnection("fallback", "choice", "when_false"),
        ),
        "choice",
    )
    compiled = graph.compile(NODE_REGISTRY, validate_outputs=True)

    _, trace = compiled.evaluate_with_node_trace(
        {"energy": 0.8, "target": (1.0, 0.0), "fallback": (0.0, 1.0)}
    )
    choice_trace = next(entry for entry in trace if entry.node_id == "choice")
    assert choice_trace.explanation == {
        "selected_port": "when_true",
        "value": 0.8,
        "threshold": 0.5,
    }
    # Sensor nodes have nothing to explain.
    assert next(entry for entry in trace if entry.node_id == "energy").explanation is None

    _, trace_below = compiled.evaluate_with_node_trace(
        {"energy": 0.2, "target": (1.0, 0.0), "fallback": (0.0, 1.0)}
    )
    below_explanation = next(
        entry for entry in trace_below if entry.node_id == "choice"
    ).explanation
    assert below_explanation is not None
    assert below_explanation["selected_port"] == "when_false"


def test_priority_selector_explains_primary_vs_fallback_via_node_trace() -> None:
    graph = BehaviorGraph(
        (
            GraphNode("primary", "context_vector_sensor", {"field": "primary"}),
            GraphNode("fallback", "context_vector_sensor", {"field": "fallback"}),
            GraphNode("priority", "priority_vector_selector", {}),
        ),
        (
            GraphConnection("primary", "priority", "primary"),
            GraphConnection("fallback", "priority", "fallback"),
        ),
        "priority",
    )
    compiled = graph.compile(NODE_REGISTRY, validate_outputs=True)

    _, trace = compiled.evaluate_with_node_trace({"primary": (1.0, 0.0), "fallback": (0.0, 1.0)})
    assert next(entry for entry in trace if entry.node_id == "priority").explanation == {
        "selected_port": "primary"
    }

    _, trace_zero = compiled.evaluate_with_node_trace(
        {"primary": (0.0, 0.0), "fallback": (0.0, 1.0)}
    )
    assert next(entry for entry in trace_zero if entry.node_id == "priority").explanation == {
        "selected_port": "fallback"
    }
