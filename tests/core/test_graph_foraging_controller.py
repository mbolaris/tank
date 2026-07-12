"""Vertical-slice contracts for the feature-flagged graph foraging controller."""

from __future__ import annotations

import random

from backend.simulation_runner import SimulationRunner
from core.behavior.graph import BehaviorGraph, GraphNode
from core.behavior.tank_adapter import default_foraging_graph
from core.entities import Fish
from core.genetics.behavioral_inheritance import inherit_behavior_graph
from core.genetics.trait import GeneticTrait


def _with_blend_weight(graph: BehaviorGraph, weight: float) -> BehaviorGraph:
    nodes = tuple(
        (
            GraphNode(node.node_id, node.node_type, {**node.parameters, "first_weight": weight})
            if node.node_id == "blend"
            else node
        )
        for node in graph.nodes
    )
    return BehaviorGraph(nodes, graph.connections, graph.output_node_id)


def test_graph_controller_has_stable_fingerprint_cached_plan_and_readable_trace() -> None:
    graph = default_foraging_graph()
    context = {
        "food_vector": (3.0, 4.0),
        "threat_away_vector": (0.0, 0.0),
        "energy_ratio": 0.2,
        "cohesion_vector": (0.0, 0.0),
        "alignment_vector": (0.0, 0.0),
        "separation_vector": (0.0, 0.0),
        "current_velocity": (0.0, 0.0),
        "has_target": True,
    }

    first = graph.compile_cached()
    output, trace = first.evaluate_with_trace(context)

    assert graph.fingerprint() == BehaviorGraph.from_dict(graph.to_dict()).fingerprint()
    assert graph.compile_cached() is first
    assert output == (0.6, 0.8)
    assert dict(trace)["food"] == (3.0, 4.0)
    assert dict(trace)["movement"] == output


def test_graph_inheritance_crosses_matching_parameters_without_rewiring() -> None:
    left = _with_blend_weight(default_foraging_graph(), 2.0)
    right = _with_blend_weight(default_foraging_graph(), 0.0)

    child_trait = inherit_behavior_graph(
        GeneticTrait(left),
        GeneticTrait(right),
        weight1=0.5,
        mutation_rate=0.0,
        mutation_strength=0.0,
        rng=random.Random(7),
    )

    assert child_trait is not None
    child = child_trait.value
    assert child.connections == left.connections
    assert child.output_node_id == left.output_node_id
    blend = next(node for node in child.nodes if node.node_id == "blend")
    assert blend.parameters["first_weight"] == 1.0


def test_graph_feature_flag_installs_graphs_and_exposes_an_on_demand_lens() -> None:
    runner = SimulationRunner(seed=42, config={"graph_behavior_enabled": True})
    snapshot = next(entity for entity in runner._collect_entities() if entity.type == "fish")
    fish = next(entity for entity in runner.world.entities_list if isinstance(entity, Fish))
    assert fish.genome.behavioral.behavior_graph is not None

    fish.movement_policy = lambda _observation, _rng: (1.0, 0.0)
    fish.movement_strategy.move(fish)
    rng_state = runner.world.rng.getstate()
    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    lens = result["details"]["behavior"]["lens"]
    movement_intent = result["details"]["behavior"]["movement_intent"]

    assert result["success"] is True
    assert lens["intent"] in {"Chasing food", "Fleeing threat", "Following the group", "Searching"}
    assert lens["graph"]["output"] == "movement"
    assert len(lens["fingerprint"]) == 16
    assert movement_intent["chosen"]["source"] == "policy_override"
    assert movement_intent["suppressed_sources"] == [
        "behavior_graph",
        "ball_pursuit",
        "code_policy",
        "composable_behavior",
    ]
    assert runner.world.rng.getstate() == rng_state
