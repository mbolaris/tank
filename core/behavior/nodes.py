"""Typed contracts and metadata registry for future shared behavior nodes.

This is intentionally interface-only infrastructure. It defines the small
cross-domain vocabulary that a later behavior graph may use, but does not add
genome data, execute nodes, or alter any simulation decision path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import NewType, Protocol, TypeAlias, TypeVar, runtime_checkable

Scalar: TypeAlias = float
"""A dimensionless numeric value in the behavior-node vocabulary."""

Vector: TypeAlias = tuple[float, float]
"""A two-dimensional vector in a domain's normalized coordinate frame."""

UnitVector = NewType("UnitVector", Vector)
"""A :class:`Vector` whose length is one, except for an explicit zero fallback."""

EntityRef: TypeAlias = int | str
"""A stable, domain-owned entity identifier; never an entity object itself."""

Bool: TypeAlias = bool
"""A boolean behavior signal."""

NodeValue: TypeAlias = Scalar | Vector | UnitVector | EntityRef | Bool
NodeInputs: TypeAlias = Mapping[str, NodeValue]
NodeContext: TypeAlias = Mapping[str, object]


class NodeCategory(str, Enum):
    """The small, interpretable set of behavior-node responsibilities."""

    SENSOR = "sensor"
    SELECTOR = "selector"
    STEERING = "steering"
    MEMORY = "memory"
    ARBITER = "arbiter"


class NodeValueType(str, Enum):
    """Serializable output types permitted at behavior-graph ports."""

    SCALAR = "scalar"
    VECTOR = "vector"
    UNIT_VECTOR = "unit_vector"
    ENTITY_REF = "entity_ref"
    BOOL = "bool"


SensorOutputT = TypeVar("SensorOutputT", covariant=True)
ValueT = TypeVar("ValueT")


@runtime_checkable
class Sensor(Protocol[SensorOutputT]):
    """Read one domain-bound signal without making a decision."""

    node_id: str

    def sense(self, context: NodeContext) -> SensorOutputT:
        """Read and return a typed value from the supplied context."""
        ...


@runtime_checkable
class Selector(Protocol[ValueT]):
    """Choose a typed value from already-provided options."""

    node_id: str

    def select(self, options: Sequence[ValueT]) -> ValueT | None:
        """Return one option, or ``None`` when no option is eligible."""
        ...


@runtime_checkable
class Steering(Protocol):
    """Convert steering inputs into a vector in the current domain's frame."""

    node_id: str

    def steer(self, inputs: NodeInputs) -> Vector:
        """Return the desired steering vector without mutating world state."""
        ...


@runtime_checkable
class Memory(Protocol[ValueT]):
    """Retain a typed value owned by a behavior-node instance."""

    node_id: str

    def read(self) -> ValueT | None:
        """Return the remembered value, if one exists."""
        ...

    def write(self, value: ValueT) -> None:
        """Replace the remembered value."""
        ...


@runtime_checkable
class Arbiter(Protocol[ValueT]):
    """Choose one typed candidate according to an explicit priority rule."""

    node_id: str

    def choose(self, candidates: Sequence[ValueT]) -> ValueT | None:
        """Return the chosen candidate, or ``None`` when none is active."""
        ...


@dataclass(frozen=True)
class NodeDefinition:
    """Stable metadata for one node implementation.

    The definition is deliberately serializable metadata rather than a node
    instance. Future genome serialization, mutation, and crossover can use the
    same registry without creating live behavior objects or consuming RNG.
    """

    node_id: str
    category: NodeCategory
    output_type: NodeValueType
    description: str

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("Behavior node IDs must be non-empty")
        if not self.description:
            raise ValueError("Behavior node descriptions must be non-empty")


class NodeRegistry:
    """A deterministic registry of behavior-node definitions.

    Registration is idempotent for identical definitions and rejects accidental
    redefinition. Listings sort by ``node_id`` so a future graph layer never
    inherits dict-order-dependent scheduling from this metadata registry.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, NodeDefinition] = {}

    def register(self, definition: NodeDefinition) -> None:
        """Register ``definition`` or reject a conflicting node ID."""
        existing = self._definitions.get(definition.node_id)
        if existing is None:
            self._definitions[definition.node_id] = definition
        elif existing != definition:
            raise ValueError(f"Behavior node '{definition.node_id}' is already registered")

    def get(self, node_id: str) -> NodeDefinition | None:
        """Return the definition for ``node_id``, if it is registered."""
        return self._definitions.get(node_id)

    def list(self) -> tuple[NodeDefinition, ...]:
        """Return all definitions in stable node-ID order."""
        return tuple(sorted(self._definitions.values(), key=lambda definition: definition.node_id))

    def clear(self) -> None:
        """Clear definitions; intended only for isolated registry tests."""
        self._definitions.clear()

    def snapshot(self) -> dict[str, NodeDefinition]:
        """Return a shallow copy suitable for test isolation."""
        return dict(self._definitions)

    def restore(self, snapshot: Mapping[str, NodeDefinition]) -> None:
        """Replace definitions with a previously captured snapshot."""
        self._definitions = dict(snapshot)


NODE_REGISTRY = NodeRegistry()
"""Canonical registry for declared shared behavior nodes."""


def register_node(definition: NodeDefinition) -> None:
    """Register a node definition in :data:`NODE_REGISTRY`."""
    NODE_REGISTRY.register(definition)


def get_node(node_id: str) -> NodeDefinition | None:
    """Look up one node definition in :data:`NODE_REGISTRY`."""
    return NODE_REGISTRY.get(node_id)


def list_nodes() -> tuple[NodeDefinition, ...]:
    """List canonical node definitions in stable node-ID order."""
    return NODE_REGISTRY.list()
