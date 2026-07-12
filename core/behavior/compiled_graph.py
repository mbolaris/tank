"""Compiled execution plan for behavior graphs.

Extracted from graph.py (behavior-preserving move) to keep that file under
this project's per-file line ceiling (see tests/test_god_class_limits.py) as
NodeTrace support is added here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from core.behavior.nodes import BehaviorNode, NodeCategory, NodeValue


class BehaviorGraphError(ValueError):
    """Raised when graph data cannot be validated or compiled."""


@dataclass(frozen=True)
class CompiledStep:
    node_id: str
    evaluate: Callable[[object, Mapping[str, NodeValue]], NodeValue]
    inputs: tuple[tuple[str, int], ...]
    node: BehaviorNode

    def run(self, context: object, values: list[NodeValue]) -> NodeValue:
        return self.evaluate(context, {port: values[index] for port, index in self.inputs})

    def explain(self, values: list[NodeValue]) -> Mapping[str, object] | None:
        """Ask the node what it selected, if it can explain itself.

        Opt-in: most categories (sensors, steering math) have nothing
        meaningful to report. A node may implement
        ``explain(inputs) -> Mapping[str, object]`` describing its own
        decision - e.g. which input port a selector picked and why - so this
        stays correct as evolvable parameters change, instead of a caller
        re-deriving the same decision externally by hardcoding a node id.
        """
        explain = getattr(self.node, "explain", None)
        if not callable(explain):
            return None
        inputs = {port: values[index] for port, index in self.inputs}
        return cast(Mapping[str, object], explain(inputs))


@dataclass(frozen=True)
class NodeTrace:
    """One compiled node's recorded output plus its optional self-explanation."""

    node_id: str
    output: NodeValue
    explanation: Mapping[str, object] | None


@dataclass(frozen=True)
class CompiledBehaviorGraph:
    """Flat, prevalidated execution plan for a :class:`~core.behavior.graph.BehaviorGraph`."""

    steps: tuple[CompiledStep, ...]
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

    def evaluate_with_node_trace(self, context: object) -> tuple[NodeValue, tuple[NodeTrace, ...]]:
        """Evaluate once and return each node's output plus its own explanation.

        Unlike ``evaluate_with_trace``'s plain ``(node_id, value)`` pairs, this
        asks each node to self-report what it selected (via an optional
        ``explain()``) instead of a caller re-deriving it externally - the
        fix for a Behavior Lens that would otherwise have to hardcode
        assumptions about specific node ids or parameter values.
        """
        values: list[NodeValue] = []
        for step in self.steps:
            values.append(step.run(context, values))
        return values[self.output_index], tuple(
            NodeTrace(step.node_id, values[index], step.explain(values))
            for index, step in enumerate(self.steps)
        )


def evaluator_for(node: BehaviorNode) -> Callable[[object, Mapping[str, NodeValue]], NodeValue]:
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


__all__ = [
    "BehaviorGraphError",
    "CompiledBehaviorGraph",
    "CompiledStep",
    "NodeTrace",
    "evaluator_for",
]
