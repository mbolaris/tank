"""Shared, domain-neutral building blocks for organism behavior."""

from core.behavior.graph import BehaviorGraph, BehaviorGraphError, CompiledBehaviorGraph
from core.behavior.nodes import NODE_REGISTRY, NodeCategory, NodeDefinition, NodeRegistry, ValueType
from core.behavior.standard_nodes import register_standard_nodes

register_standard_nodes()

__all__ = [
    "BehaviorGraph",
    "BehaviorGraphError",
    "CompiledBehaviorGraph",
    "NODE_REGISTRY",
    "NodeCategory",
    "NodeDefinition",
    "NodeRegistry",
    "ValueType",
    "register_standard_nodes",
]
