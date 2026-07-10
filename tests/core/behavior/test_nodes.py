"""Tests for the interface-only shared behavior-node foundation."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.behavior.nodes import (
    Arbiter,
    Memory,
    NodeCategory,
    NodeDefinition,
    NodeRegistry,
    NodeValueType,
    Selector,
    Sensor,
    Steering,
)


def _definition(node_id: str, category: NodeCategory = NodeCategory.SENSOR) -> NodeDefinition:
    return NodeDefinition(
        node_id=node_id,
        category=category,
        output_type=NodeValueType.SCALAR,
        description="Test-only node definition",
    )


def test_registry_lists_definitions_in_stable_node_id_order() -> None:
    registry = NodeRegistry()
    registry.register(_definition("steering.seek", NodeCategory.STEERING))
    registry.register(_definition("sensor.energy"))
    registry.register(_definition("arbiter.priority", NodeCategory.ARBITER))

    assert [definition.node_id for definition in registry.list()] == [
        "arbiter.priority",
        "sensor.energy",
        "steering.seek",
    ]


def test_registry_is_idempotent_and_rejects_conflicting_definition() -> None:
    registry = NodeRegistry()
    definition = _definition("sensor.energy")
    registry.register(definition)
    registry.register(definition)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_definition("sensor.energy", NodeCategory.SELECTOR))


def test_registry_snapshot_restore_and_validation_are_isolated() -> None:
    registry = NodeRegistry()
    registry.register(_definition("sensor.energy"))
    snapshot = registry.snapshot()
    registry.clear()
    registry.restore(snapshot)

    assert registry.get("sensor.energy") == _definition("sensor.energy")
    with pytest.raises(ValueError, match="non-empty"):
        NodeDefinition("", NodeCategory.SENSOR, NodeValueType.SCALAR, "description")


@dataclass
class _ExampleSensor:
    node_id: str = "sensor.energy"

    def sense(self, context: dict[str, object]) -> float:
        return float(context["energy"])


@dataclass
class _ExampleSelector:
    node_id: str = "selector.first"

    def select(self, options: list[float]) -> float | None:
        return options[0] if options else None


@dataclass
class _ExampleSteering:
    node_id: str = "steering.stop"

    def steer(self, inputs: dict[str, object]) -> tuple[float, float]:
        _ = inputs
        return 0.0, 0.0


@dataclass
class _ExampleMemory:
    node_id: str = "memory.scalar"
    value: float | None = None

    def read(self) -> float | None:
        return self.value

    def write(self, value: float) -> None:
        self.value = value


@dataclass
class _ExampleArbiter:
    node_id: str = "arbiter.first"

    def choose(self, candidates: list[float]) -> float | None:
        return candidates[0] if candidates else None


def test_protocols_describe_each_interpretable_node_role() -> None:
    assert isinstance(_ExampleSensor(), Sensor)
    assert isinstance(_ExampleSelector(), Selector)
    assert isinstance(_ExampleSteering(), Steering)
    assert isinstance(_ExampleMemory(), Memory)
    assert isinstance(_ExampleArbiter(), Arbiter)
