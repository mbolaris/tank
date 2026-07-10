"""Typed, domain-neutral contracts for future behavior-graph nodes.

The behavior graph is deliberately not wired into genomes or the simulation yet.
This module defines the small vocabulary that any future graph node must use,
and a registry that makes node metadata deterministic and validates graph-port
compatibility before an interpreter is introduced.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import NewType, Protocol, TypeAlias


# These are semantic types, not runtime wrappers.  Keeping vectors in a
# normalized, domain-neutral frame prevents a tank coordinate or soccer field
# coordinate from leaking into the graph's shared middle layer.
Scalar = NewType("Scalar", float)
Bool = NewType("Bool", bool)
EntityRef = NewType("EntityRef", str)
Vector: TypeAlias = tuple[Scalar, Scalar]
UnitVector = NewType("UnitVector", Vector)
NodeValue: TypeAlias = Scalar | Bool | EntityRef | Vector | UnitVector
NodeParameter: TypeAlias = Scalar | Bool | str


class ValueType(str, Enum):
    """The closed set of values that may cross a graph port."""

    SCALAR = "scalar"
    VECTOR = "vector"
    UNIT_VECTOR = "unit_vector"
    ENTITY_REF = "entity_ref"
    BOOL = "bool"


class NodeCategory(str, Enum):
    """The five readable roles allowed in the shared behavior substrate."""

    SENSOR = "sensor"
    SELECTOR = "selector"
    STEERING = "steering"
    MEMORY = "memory"
    ARBITER = "arbiter"


class BehaviorNode(Protocol):
    """Metadata and serialization contract common to every behavior node."""

    node_id: str
    node_type: str
    category: NodeCategory

    def to_parameters(self) -> Mapping[str, NodeParameter]:
        """Return deterministic, JSON-safe node parameters."""
        ...


class SensorNode(BehaviorNode, Protocol):
    """Reads a domain adapter's observation into the shared value vocabulary."""

    def sense(self, context: object) -> NodeValue:
        """Produce one value without consuming graph inputs."""
        ...


class SelectorNode(BehaviorNode, Protocol):
    """Chooses one value from typed candidate inputs."""

    def select(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        """Select a value using only declared input ports."""
        ...


class SteeringNode(BehaviorNode, Protocol):
    """Converts typed target inputs into a normalized movement direction."""

    def steer(self, inputs: Mapping[str, NodeValue]) -> UnitVector:
        """Return a direction in the normalized shared frame."""
        ...


class MemoryNode(BehaviorNode, Protocol):
    """Maintains explicit, serializable graph-local state."""

    def update(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        """Update memory and expose its current typed value."""
        ...


class ArbiterNode(BehaviorNode, Protocol):
    """Resolves typed competing outputs into one selected output."""

    def arbitrate(self, inputs: Mapping[str, NodeValue]) -> NodeValue:
        """Choose one value according to the node's explicit policy."""
        ...


NodeFactory: TypeAlias = Callable[[str, Mapping[str, NodeParameter]], BehaviorNode]


def _normalized_ports(ports: Mapping[str, ValueType]) -> Mapping[str, ValueType]:
    """Validate and freeze port metadata supplied by a node definition."""
    normalized = dict(ports)
    for name, value_type in normalized.items():
        if not name or not name.isidentifier():
            raise ValueError(f"Node port names must be valid identifiers, got {name!r}.")
        if not isinstance(value_type, ValueType):
            raise TypeError(f"Port {name!r} must declare a ValueType, got {value_type!r}.")
    return MappingProxyType(normalized)


@dataclass(frozen=True)
class NodeDefinition:
    """Static, serializable metadata for one registered node implementation."""

    node_type: str
    category: NodeCategory
    input_ports: Mapping[str, ValueType]
    output_type: ValueType
    factory: NodeFactory

    def __post_init__(self) -> None:
        if not self.node_type or not self.node_type.isidentifier():
            raise ValueError(
                f"Node types must be non-empty alphanumeric identifiers, got {self.node_type!r}."
            )
        if not isinstance(self.category, NodeCategory):
            raise TypeError(f"Node {self.node_type!r} must declare a NodeCategory.")
        if not isinstance(self.output_type, ValueType):
            raise TypeError(f"Node {self.node_type!r} must declare a ValueType output.")
        if not callable(self.factory):
            raise TypeError(f"Node {self.node_type!r} must provide a factory.")
        object.__setattr__(self, "input_ports", _normalized_ports(self.input_ports))

    def to_dict(self) -> dict[str, object]:
        """Return stable metadata for graph serialization and inspection."""
        return {
            "node_type": self.node_type,
            "category": self.category.value,
            "input_ports": {
                name: value_type.value for name, value_type in sorted(self.input_ports.items())
            },
            "output_type": self.output_type.value,
        }


class NodeRegistry:
    """Registry for behavior nodes and their type-safe graph connections.

    Definitions, rather than domain objects, are registered.  That keeps
    serialization, future mutation, and future crossover centered on one stable
    schema, while each domain remains responsible only for sensor binding and
    actuator adaptation.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, NodeDefinition] = {}

    def register(self, definition: NodeDefinition) -> None:
        """Register one node type exactly once."""
        if definition.node_type in self._definitions:
            raise ValueError(f"Node type {definition.node_type!r} is already registered.")
        self._definitions[definition.node_type] = definition

    def get(self, node_type: str) -> NodeDefinition:
        """Return a definition or raise a clear error for an unknown node."""
        try:
            return self._definitions[node_type]
        except KeyError as exc:
            raise KeyError(f"Unknown behavior node type {node_type!r}.") from exc

    def definitions(self) -> tuple[NodeDefinition, ...]:
        """Return definitions in stable order, independent of registration order."""
        return tuple(self._definitions[name] for name in sorted(self._definitions))

    def create(
        self, node_type: str, node_id: str, parameters: Mapping[str, NodeParameter]
    ) -> BehaviorNode:
        """Create a node and confirm it matches its registered metadata."""
        definition = self.get(node_type)
        node = definition.factory(node_id, MappingProxyType(dict(parameters)))
        if node.node_id != node_id:
            raise ValueError(
                f"Factory for {node_type!r} returned node id {node.node_id!r}, expected {node_id!r}."
            )
        if node.node_type != node_type:
            raise ValueError(f"Factory for {node_type!r} returned node type {node.node_type!r}.")
        if node.category is not definition.category:
            raise ValueError(
                f"Factory for {node_type!r} returned category {node.category.value!r}, "
                f"expected {definition.category.value!r}."
            )
        return node

    def validate_connection(
        self, source_node_type: str, target_node_type: str, target_port: str
    ) -> None:
        """Require a source output to exactly match a target input port's type."""
        source = self.get(source_node_type)
        target = self.get(target_node_type)
        try:
            expected = target.input_ports[target_port]
        except KeyError as exc:
            raise KeyError(f"Node {target_node_type!r} has no input port {target_port!r}.") from exc
        if source.output_type is not expected:
            raise TypeError(
                f"Cannot connect {source_node_type!r} ({source.output_type.value}) to "
                f"{target_node_type!r}.{target_port} ({expected.value})."
            )

    def serialize(self, node: BehaviorNode) -> dict[str, object]:
        """Serialize every registered node through the same stable envelope."""
        definition = self.get(node.node_type)
        if node.category is not definition.category:
            raise ValueError(
                f"Node {node.node_id!r} category does not match {node.node_type!r}'s definition."
            )
        return {
            "id": node.node_id,
            "type": definition.node_type,
            "parameters": dict(sorted(node.to_parameters().items())),
        }


NODE_REGISTRY = NodeRegistry()


__all__ = [
    "ArbiterNode",
    "BehaviorNode",
    "Bool",
    "EntityRef",
    "MemoryNode",
    "NODE_REGISTRY",
    "NodeCategory",
    "NodeDefinition",
    "NodeFactory",
    "NodeParameter",
    "NodeRegistry",
    "NodeValue",
    "Scalar",
    "SelectorNode",
    "SensorNode",
    "SteeringNode",
    "UnitVector",
    "ValueType",
    "Vector",
]
