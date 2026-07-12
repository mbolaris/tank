"""Vertical-slice contracts for the feature-flagged graph foraging controller."""

from __future__ import annotations

import random

from backend.simulation_runner import SimulationRunner
from core.behavior.graph import BehaviorGraph, GraphNode
from core.behavior.nodes import NODE_REGISTRY
from core.behavior.tank_adapter import (
    ForagingIntentKind,
    TankBehaviorObservation,
    classify_foraging_intent,
    default_foraging_graph,
)
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


def _with_urgency_threshold(graph: BehaviorGraph, threshold: float) -> BehaviorGraph:
    nodes = tuple(
        (
            GraphNode(node.node_id, node.node_type, {**node.parameters, "threshold": threshold})
            if node.node_id == "urgency"
            else node
        )
        for node in graph.nodes
    )
    return BehaviorGraph(nodes, graph.connections, graph.output_node_id)


def _observation(
    energy_ratio: float, threat_away_vector: tuple[float, float] = (0.0, 0.0)
) -> TankBehaviorObservation:
    return TankBehaviorObservation(
        values={"threat_away_vector": threat_away_vector, "energy_ratio": energy_ratio},
        target_label=None,
    )


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


def test_graph_parameter_mutation_is_deterministic_and_stays_within_declared_bounds() -> None:
    graph = default_foraging_graph()
    first = graph.crossed_over(
        graph,
        weight1=0.5,
        mutation_rate=1.0,
        mutation_strength=10.0,
        rng=random.Random(23),
    )
    second = graph.crossed_over(
        graph,
        weight1=0.5,
        mutation_rate=1.0,
        mutation_strength=10.0,
        rng=random.Random(23),
    )

    assert first == second
    for node in first.nodes:
        definition = NODE_REGISTRY.get(node.node_type)
        for name, spec in definition.parameter_specs.items():
            assert float(spec.minimum) <= float(node.parameters[name]) <= float(spec.maximum)


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


def test_classify_foraging_intent_reads_the_graphs_own_mutable_threshold() -> None:
    graph = _with_urgency_threshold(default_foraging_graph(), 0.6)

    assert (
        classify_foraging_intent(_observation(0.9, threat_away_vector=(1.0, 0.0)), graph)
        is ForagingIntentKind.THREAT
    )
    # 0.5 sits between the module's 0.35 default and this graph's mutated 0.6 threshold:
    # FOOD here proves the classifier reads the graph's own parameter, not a hardcoded 0.35.
    assert classify_foraging_intent(_observation(0.5), graph) is ForagingIntentKind.FOOD
    assert classify_foraging_intent(_observation(0.9), graph) is ForagingIntentKind.COHESION


def test_graph_yields_to_soccer_when_classified_as_cohesion() -> None:
    """The review's explicit case: graph, food pressure, and soccer active together.

    No movement_policy override is set (unlike the lens test above), so
    GraphBehaviorConsideration is actually exercised rather than short-circuited by
    PolicyOverrideConsideration.
    """
    runner = SimulationRunner(seed=42, config={"graph_behavior_enabled": True})
    fish = next(entity for entity in runner.world.entities_list if isinstance(entity, Fish))
    assert fish.genome.behavioral.behavior_graph is not None

    # High energy -> the graph's own urgency node selects cohesion (>= its 0.35 default
    # threshold) rather than food, and simultaneously clears ball_pursuit's own energy
    # gate (PLAY_ENERGY_THRESHOLD_RATIO), so soccer is genuinely eligible to compete
    # rather than being blocked by its own gate regardless of this fix.
    fish.energy = fish.max_energy
    fish.movement_strategy.move(fish)

    arbitration = fish.movement_strategy.last_arbitration
    assert arbitration.selected is not None
    assert arbitration.selected.source != "behavior_graph"


def test_lens_reads_the_graphs_own_mutated_threshold_not_a_hardcoded_one() -> None:
    """Regression test for the review's concern: once urgency.threshold mutates,
    the Lens must explain the graph's actual decision, not a hardcoded 0.35."""
    runner = SimulationRunner(seed=42, config={"graph_behavior_enabled": True})
    snapshot = next(entity for entity in runner._collect_entities() if entity.type == "fish")
    fish = next(entity for entity in runner.world.entities_list if isinstance(entity, Fish))
    graph_trait = fish.genome.behavioral.behavior_graph
    assert graph_trait is not None

    # Mutate the threshold well above the default 0.35. A hardcoded-0.35 check
    # would misclassify energy_ratio=0.5 as cohesion; reading the graph's own
    # (mutated) threshold via its self-reported NodeTrace explanation
    # correctly classifies it as food instead.
    graph_trait.value = _with_urgency_threshold(graph_trait.value, 0.9)
    fish.energy = 0.5 * fish.max_energy

    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})

    assert result["success"] is True
    assert result["details"]["behavior"]["lens"]["intent"] == "Chasing food"
