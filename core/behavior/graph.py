"""Typed behavior-graph data and its compiled interpreter.

Graph-backed movement is an opt-in experiment. Compiling validates the graph
and turns it into a flat sequence of callables outside the per-frame hot path.
"""

from __future__ import annotations

import math
import hashlib
import json
import random as pyrandom
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from core.behavior.nodes import (
    NODE_REGISTRY,
    BehaviorNode,
    Bool,
    NodeCategory,
    NodeParameter,
    NodeRegistry,
    NodeValue,
    Scalar,
    ValueType,
)
from core.behavior.compiled_cache import get_compiled_plan


class BehaviorGraphError(ValueError):
    """Raised when graph data cannot be validated or compiled."""


def _is_vector(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and all(type(component) is float and math.isfinite(component) for component in value)
    )


def _matches_value_type(value: object, value_type: ValueType) -> bool:
    if value_type is ValueType.SCALAR:
        return type(value) is float and math.isfinite(value)
    if value_type is ValueType.BOOL:
        return type(value) is bool
    if value_type is ValueType.ENTITY_REF:
        return type(value) is str
    if value_type is ValueType.VECTOR:
        return _is_vector(value)
    if value_type is ValueType.UNIT_VECTOR:
        if not _is_vector(value):
            return False
        vector = cast(tuple[float, float], value)
        length = math.hypot(vector[0], vector[1])
        return length == 0.0 or math.isclose(length, 1.0, rel_tol=1e-6, abs_tol=1e-6)
    return False


def _checked_evaluator(
    evaluator: Callable[[object, Mapping[str, NodeValue]], NodeValue],
    node_id: str,
    output_type: ValueType,
) -> Callable[[object, Mapping[str, NodeValue]], NodeValue]:
    def evaluate(context: object, inputs: Mapping[str, NodeValue]) -> NodeValue:
        value = evaluator(context, inputs)
        if not _matches_value_type(value, output_type):
            raise BehaviorGraphError(
                f"Node {node_id!r} returned an invalid {output_type.value} output "
                f"(got {type(value).__name__})."
            )
        return value

    return evaluate


def _parameters_from_dict(value: object) -> dict[str, NodeParameter]:
    if not isinstance(value, dict):
        raise BehaviorGraphError("Node parameters must be an object.")

    parameters: dict[str, NodeParameter] = {}
    for name, parameter in value.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise BehaviorGraphError(f"Invalid node parameter name {name!r}.")
        if isinstance(parameter, (bool, str)):
            parameters[name] = Bool(parameter) if isinstance(parameter, bool) else parameter
        elif isinstance(parameter, (int, float)) and math.isfinite(float(parameter)):
            parameters[name] = Scalar(float(parameter))
        else:
            raise BehaviorGraphError(
                f"Node parameter {name!r} must be a finite scalar, bool, or string."
            )
    return parameters


@dataclass(frozen=True)
class GraphNode:
    """One serializable node instance in a behavior graph."""

    node_id: str
    node_type: str
    parameters: Mapping[str, NodeParameter]

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.isidentifier():
            raise BehaviorGraphError(f"Invalid graph node id {self.node_id!r}.")
        if not self.node_type or not self.node_type.isidentifier():
            raise BehaviorGraphError(f"Invalid graph node type {self.node_type!r}.")
        object.__setattr__(self, "parameters", _parameters_from_dict(dict(self.parameters)))

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "parameters": dict(sorted(self.parameters.items())),
        }

    @classmethod
    def from_dict(cls, data: object) -> GraphNode:
        if not isinstance(data, dict):
            raise BehaviorGraphError("Graph nodes must be objects.")
        return cls(
            node_id=data.get("id", ""),
            node_type=data.get("type", ""),
            parameters=_parameters_from_dict(data.get("parameters", {})),
        )


@dataclass(frozen=True)
class GraphConnection:
    """A typed edge from one node output to a named target input port."""

    source_id: str
    target_id: str
    target_port: str

    def __post_init__(self) -> None:
        for label, value in (
            ("source", self.source_id),
            ("target", self.target_id),
            ("target port", self.target_port),
        ):
            if not value or not value.isidentifier():
                raise BehaviorGraphError(f"Invalid graph {label} {value!r}.")

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source_id, "target": self.target_id, "port": self.target_port}

    @classmethod
    def from_dict(cls, data: object) -> GraphConnection:
        if not isinstance(data, dict):
            raise BehaviorGraphError("Graph connections must be objects.")
        return cls(
            source_id=data.get("source", ""),
            target_id=data.get("target", ""),
            target_port=data.get("port", ""),
        )


@dataclass(frozen=True)
class _CompiledStep:
    node_id: str
    evaluate: Callable[[object, Mapping[str, NodeValue]], NodeValue]
    inputs: tuple[tuple[str, int], ...]

    def run(self, context: object, values: list[NodeValue]) -> NodeValue:
        return self.evaluate(context, {port: values[index] for port, index in self.inputs})


@dataclass(frozen=True)
class CompiledBehaviorGraph:
    """Flat, prevalidated execution plan for a :class:`BehaviorGraph`."""

    steps: tuple[_CompiledStep, ...]
    output_index: int

    def evaluate(self, context: object) -> NodeValue:
        """Run the precompiled plan without parsing or traversing graph topology."""
        values: list[NodeValue] = []
        for step in self.steps:
            values.append(step.run(context, values))
        return values[self.output_index]

    def evaluate_with_trace(
        self, context: object
    ) -> tuple[NodeValue, tuple[tuple[str, NodeValue], ...]]:
        """Evaluate once and return ordered intermediate values for an inspector.

        This is intentionally opt-in: normal simulation execution stores no
        per-fish trace, while a selected fish can be explained on demand.
        """
        values: list[NodeValue] = []
        for step in self.steps:
            values.append(step.run(context, values))
        return values[self.output_index], tuple(
            (step.node_id, values[index]) for index, step in enumerate(self.steps)
        )


def _evaluator_for(node: BehaviorNode) -> Callable[[object, Mapping[str, NodeValue]], NodeValue]:
    """Bind a node's category-specific method once at compile time."""
    if node.category is NodeCategory.SENSOR:
        sense = getattr(node, "sense", None)
        if not callable(sense):
            raise BehaviorGraphError(f"Sensor node {node.node_id!r} must provide sense(context).")
        return lambda context, _inputs: cast(NodeValue, sense(context))

    method_name = {
        NodeCategory.SELECTOR: "select",
        NodeCategory.STEERING: "steer",
        NodeCategory.MEMORY: "update",
        NodeCategory.ARBITER: "arbitrate",
    }[node.category]
    method = getattr(node, method_name, None)
    if not callable(method):
        raise BehaviorGraphError(
            f"{node.category.value.title()} node {node.node_id!r} must provide {method_name}(inputs)."
        )
    return lambda _context, inputs: cast(NodeValue, method(inputs))


@dataclass(frozen=True)
class BehaviorGraph:
    """An immutable, acyclic behavior graph with an explicit output node."""

    nodes: tuple[GraphNode, ...]
    connections: tuple[GraphConnection, ...]
    output_node_id: str

    def __post_init__(self) -> None:
        if not self.nodes:
            raise BehaviorGraphError("A behavior graph must contain at least one node.")
        if not self.output_node_id or not self.output_node_id.isidentifier():
            raise BehaviorGraphError(f"Invalid graph output node {self.output_node_id!r}.")

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible graph representation."""
        return {
            "nodes": [node.to_dict() for node in sorted(self.nodes, key=lambda node: node.node_id)],
            "connections": [
                connection.to_dict()
                for connection in sorted(
                    self.connections,
                    key=lambda connection: (
                        connection.target_id,
                        connection.target_port,
                        connection.source_id,
                    ),
                )
            ],
            "output": self.output_node_id,
        }

    def fingerprint(self) -> str:
        """Stable content fingerprint suitable for graph cache and provenance."""
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def from_dict(cls, data: object) -> BehaviorGraph:
        if not isinstance(data, dict):
            raise BehaviorGraphError("Behavior graph must be an object.")
        raw_nodes = data.get("nodes")
        raw_connections = data.get("connections", [])
        if not isinstance(raw_nodes, list) or not isinstance(raw_connections, list):
            raise BehaviorGraphError("Behavior graph nodes and connections must be lists.")
        graph = cls(
            nodes=tuple(GraphNode.from_dict(node) for node in raw_nodes),
            connections=tuple(
                GraphConnection.from_dict(connection) for connection in raw_connections
            ),
            output_node_id=data.get("output", ""),
        )
        issues = graph.validate()
        if issues:
            raise BehaviorGraphError("Invalid behavior graph: " + "; ".join(issues))
        return graph

    def validate(self, registry: NodeRegistry | None = None) -> tuple[str, ...]:
        """Return deterministic structural and optional registry-contract issues."""
        issues: list[str] = []
        nodes_by_id: dict[str, GraphNode] = {}
        for node in self.nodes:
            if node.node_id in nodes_by_id:
                issues.append(f"duplicate node id {node.node_id!r}")
            nodes_by_id[node.node_id] = node

        if self.output_node_id not in nodes_by_id:
            issues.append(f"output node {self.output_node_id!r} does not exist")

        incoming: set[tuple[str, str]] = set()
        for connection in self.connections:
            if connection.source_id not in nodes_by_id:
                issues.append(f"connection source {connection.source_id!r} does not exist")
            if connection.target_id not in nodes_by_id:
                issues.append(f"connection target {connection.target_id!r} does not exist")
            key = (connection.target_id, connection.target_port)
            if key in incoming:
                issues.append(
                    f"input {connection.target_id!r}.{connection.target_port} has multiple sources"
                )
            incoming.add(key)

        if not issues:
            issues.extend(self._topology_issues(nodes_by_id))

        if registry is not None:
            definitions = {}
            for node in sorted(self.nodes, key=lambda item: item.node_id):
                try:
                    definitions[node.node_id] = registry.get(node.node_type)
                except KeyError:
                    issues.append(f"node {node.node_id!r} uses unknown type {node.node_type!r}")

            for node in sorted(self.nodes, key=lambda item: item.node_id):
                definition = definitions.get(node.node_id)
                if definition is None:
                    continue
                connected_ports = {
                    connection.target_port
                    for connection in self.connections
                    if connection.target_id == node.node_id
                }
                for port_name in sorted(definition.input_ports):
                    if port_name not in connected_ports:
                        issues.append(f"required input {node.node_id!r}.{port_name} has no source")
                for parameter_name, spec in definition.parameter_specs.items():
                    if parameter_name in node.parameters:
                        value = node.parameters[parameter_name]
                        if isinstance(value, bool) or not isinstance(value, (int, float)):
                            issues.append(
                                f"node {node.node_id!r} parameter {parameter_name!r} must be numeric"
                            )
                        elif not float(spec.minimum) <= float(value) <= float(spec.maximum):
                            issues.append(
                                f"node {node.node_id!r} parameter {parameter_name!r} is outside bounds"
                            )

            for connection in self.connections:
                source = nodes_by_id.get(connection.source_id)
                target = nodes_by_id.get(connection.target_id)
                if source is None or target is None:
                    continue
                try:
                    registry.validate_connection(
                        source.node_type, target.node_type, connection.target_port
                    )
                except (KeyError, TypeError) as exc:
                    issues.append(str(exc))

        return tuple(issues)

    def _topology_issues(self, nodes_by_id: Mapping[str, GraphNode]) -> list[str]:
        incoming_count = dict.fromkeys(nodes_by_id, 0)
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
        for connection in self.connections:
            incoming_count[connection.target_id] += 1
            outgoing[connection.source_id].append(connection.target_id)

        ready = sorted(node_id for node_id, count in incoming_count.items() if count == 0)
        visited = 0
        while ready:
            node_id = ready.pop(0)
            visited += 1
            for target in sorted(outgoing[node_id]):
                incoming_count[target] -= 1
                if incoming_count[target] == 0:
                    ready.append(target)
                    ready.sort()
        return [] if visited == len(nodes_by_id) else ["graph contains a cycle"]

    def compile(
        self,
        registry: NodeRegistry = NODE_REGISTRY,
        *,
        validate_outputs: bool = False,
    ) -> CompiledBehaviorGraph:
        """Instantiate and bind an immutable flat execution plan once.

        Set ``validate_outputs`` for debug or benchmark runs that should enforce
        each node's declared runtime value type.
        """
        if registry is NODE_REGISTRY:
            from core.behavior.standard_nodes import register_standard_nodes

            register_standard_nodes(registry)
        issues = self.validate(registry)
        if issues:
            raise BehaviorGraphError("Cannot compile behavior graph: " + "; ".join(issues))

        nodes_by_id = {node.node_id: node for node in self.nodes}
        order = self._topological_order(nodes_by_id)
        indices = {node_id: index for index, node_id in enumerate(order)}
        incoming: dict[str, list[GraphConnection]] = {node_id: [] for node_id in order}
        for connection in self.connections:
            incoming[connection.target_id].append(connection)

        steps: list[_CompiledStep] = []
        for node_id in order:
            graph_node = nodes_by_id[node_id]
            definition = registry.get(graph_node.node_type)
            node = registry.create(graph_node.node_type, graph_node.node_id, graph_node.parameters)
            inputs = tuple(
                (connection.target_port, indices[connection.source_id])
                for connection in sorted(
                    incoming[node_id], key=lambda connection: connection.target_port
                )
            )
            evaluator = _evaluator_for(node)
            if validate_outputs:
                evaluator = _checked_evaluator(evaluator, node_id, definition.output_type)
            steps.append(_CompiledStep(node_id, evaluator, inputs))
        return CompiledBehaviorGraph(tuple(steps), indices[self.output_node_id])

    def compile_cached(self, registry: NodeRegistry = NODE_REGISTRY) -> CompiledBehaviorGraph:
        """Return a bounded, registry-specific cached plan for the hot path."""
        return get_compiled_plan(registry, self.fingerprint(), lambda: self.compile(registry))

    def crossed_over(
        self,
        other: BehaviorGraph,
        *,
        weight1: float,
        mutation_rate: float,
        mutation_strength: float,
        rng: pyrandom.Random,
        registry: NodeRegistry = NODE_REGISTRY,
    ) -> BehaviorGraph:
        """Blend matching-node parameters and mutate only declared numeric values.

        Topology is intentionally retained.  Structural mutation belongs to a
        later milestone, after this representation has demonstrated selection.
        """
        if registry is NODE_REGISTRY:
            from core.behavior.standard_nodes import register_standard_nodes

            register_standard_nodes(registry)
        other_nodes = {node.node_id: node for node in other.nodes}
        evolved_nodes: list[GraphNode] = []
        for node in self.nodes:
            parameters = dict(node.parameters)
            counterpart = other_nodes.get(node.node_id)
            definition = registry.get(node.node_type)
            if counterpart is not None and counterpart.node_type == node.node_type:
                for name in sorted(definition.parameter_specs):
                    left = parameters.get(name, definition.parameter_specs[name].default)
                    right = counterpart.parameters.get(
                        name, definition.parameter_specs[name].default
                    )
                    parameters[name] = Scalar(
                        float(left) * weight1 + float(right) * (1.0 - weight1)
                    )
            for name, spec in sorted(definition.parameter_specs.items()):
                value = spec.clamp(parameters.get(name, spec.default))
                if rng.random() < mutation_rate:
                    span = float(spec.maximum) - float(spec.minimum)
                    value = spec.clamp(float(value) + rng.gauss(0.0, mutation_strength * span))
                parameters[name] = value
            evolved_nodes.append(GraphNode(node.node_id, node.node_type, parameters))
        return BehaviorGraph(tuple(evolved_nodes), self.connections, self.output_node_id)

    def _topological_order(self, nodes_by_id: Mapping[str, GraphNode]) -> tuple[str, ...]:
        incoming_count = dict.fromkeys(nodes_by_id, 0)
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
        for connection in self.connections:
            incoming_count[connection.target_id] += 1
            outgoing[connection.source_id].append(connection.target_id)

        ready = sorted(node_id for node_id, count in incoming_count.items() if count == 0)
        order: list[str] = []
        while ready:
            node_id = ready.pop(0)
            order.append(node_id)
            for target in sorted(outgoing[node_id]):
                incoming_count[target] -= 1
                if incoming_count[target] == 0:
                    ready.append(target)
                    ready.sort()
        return tuple(order)


__all__ = [
    "BehaviorGraph",
    "BehaviorGraphError",
    "CompiledBehaviorGraph",
    "GraphConnection",
    "GraphNode",
]
