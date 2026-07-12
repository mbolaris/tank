"""Contracts for the shared, domain-neutral Target Pursuit Module (PR2).

The same module graph is evaluated by both the food adapter
(core.behavior.tank_adapter) and the soccer-ball adapter
(core.movement.ball_pursuit) - these tests cover the module's own topology
and evolvability in isolation, independent of either domain.
"""

from __future__ import annotations

import random
from types import SimpleNamespace

from backend.simulation_runner import SimulationRunner
from core.behavior.graph import BehaviorGraph, GraphNode
from core.behavior.nodes import NODE_REGISTRY
from core.behavior.pursuit_nodes import default_pursuit_module_graph
from core.entities import Fish
from core.genetics.behavioral import BehavioralTraits
from core.genetics.behavioral_inheritance import inherit_behavior_graph
from core.genetics.trait import GeneticTrait


def test_default_module_reproduces_direct_pursuit_at_default_parameters() -> None:
    """At default params, output is a unit vector aimed at a stationary target."""
    module = default_pursuit_module_graph()
    compiled = module.compile_cached()

    assert compiled.evaluate(
        {
            "target_vector": (10.0, 0.0),
            "target_velocity": (0.0, 0.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    ) == (1.0, 0.0)
    assert compiled.evaluate(
        {
            "target_vector": (0.0, 0.0),
            "target_velocity": (0.0, 0.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    ) == (0.0, 0.0)


def test_default_module_leads_a_moving_target() -> None:
    """Prediction is genuinely applied: leading a perpendicular-moving target
    tilts the aim away from the target's raw current-position direction."""
    module = default_pursuit_module_graph()
    compiled = module.compile_cached()

    direct = compiled.evaluate(
        {
            "target_vector": (10.0, 0.0),
            "target_velocity": (0.0, 0.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    )
    led = compiled.evaluate(
        {
            "target_vector": (10.0, 0.0),
            "target_velocity": (0.0, 5.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    )
    assert direct == (1.0, 0.0)
    assert led != direct
    assert led[1] > 0.0  # aim shifts toward where the target is heading


def test_pursuit_commitment_scales_output_magnitude() -> None:
    """scale_vector's existing 'scale' param is pursuit commitment - it changes
    output magnitude without changing direction."""
    nodes = tuple(
        (
            type(node)(node.node_id, node.node_type, {**node.parameters, "scale": 0.5})
            if node.node_id == "pursuit"
            else node
        )
        for node in default_pursuit_module_graph().nodes
    )
    base = default_pursuit_module_graph()
    committed = BehaviorGraph(nodes, base.connections, base.output_node_id)

    full = base.compile_cached().evaluate(
        {
            "target_vector": (10.0, 0.0),
            "target_velocity": (0.0, 0.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    )
    half = committed.compile_cached().evaluate(
        {
            "target_vector": (10.0, 0.0),
            "target_velocity": (0.0, 0.0),
            "self_velocity": (0.0, 0.0),
            "self_speed": 3.0,
        }
    )
    assert full == (1.0, 0.0)
    assert half == (0.5, 0.0)


def test_module_graph_is_evolvable_like_any_other_behavior_graph() -> None:
    """The module rides the exact same crossover/mutation machinery as
    behavior_graph - no bespoke inheritance code needed (PR2's design goal)."""
    module = default_pursuit_module_graph()
    mutated = module.crossed_over(
        module, weight1=0.5, mutation_rate=1.0, mutation_strength=1.0, rng=random.Random(11)
    )

    for node in mutated.nodes:
        definition = NODE_REGISTRY.get(node.node_type)
        for name, spec in definition.parameter_specs.items():
            assert float(spec.minimum) <= float(node.parameters[name]) <= float(spec.maximum)

    child_trait = inherit_behavior_graph(
        GeneticTrait(module),
        GeneticTrait(mutated),
        weight1=0.5,
        mutation_rate=0.0,
        mutation_strength=0.0,
        rng=random.Random(3),
    )
    assert child_trait is not None
    assert child_trait.value.output_node_id == module.output_node_id


def test_target_pursuit_module_inherits_through_behavioral_traits_both_modes() -> None:
    """target_pursuit_module rides BehavioralTraits.from_parents /
    from_parents_recombination via the same generic loop as behavior_graph -
    no bespoke inheritance code needed for the new field."""
    parent1 = BehavioralTraits.random(random.Random(1))
    parent2 = BehavioralTraits.random(random.Random(2))
    parent1.target_pursuit_module = GeneticTrait(default_pursuit_module_graph())
    parent2.target_pursuit_module = GeneticTrait(default_pursuit_module_graph())

    blended = BehavioralTraits.from_parents(parent1, parent2, rng=random.Random(5))
    assert blended.target_pursuit_module is not None
    assert blended.target_pursuit_module.value is not None
    assert isinstance(blended.target_pursuit_module.value, BehaviorGraph)

    recombined = BehavioralTraits.from_parents_recombination(parent1, parent2, rng=random.Random(5))
    assert recombined.target_pursuit_module is not None
    assert recombined.target_pursuit_module.value is not None


def test_target_pursuit_module_absent_for_both_parents_stays_none_in_offspring() -> None:
    """Genomes without the trait (today's universal case) produce offspring
    without it too - the new field must not silently activate itself."""
    parent1 = BehavioralTraits.random(random.Random(1))
    parent2 = BehavioralTraits.random(random.Random(2))
    assert parent1.target_pursuit_module is None
    assert parent2.target_pursuit_module is None

    blended = BehavioralTraits.from_parents(parent1, parent2, rng=random.Random(5))
    recombined = BehavioralTraits.from_parents_recombination(parent1, parent2, rng=random.Random(5))

    assert blended.target_pursuit_module is None
    assert recombined.target_pursuit_module is None


def test_founders_get_the_module_when_its_flag_is_enabled_independently() -> None:
    """The pursuit module flag is an independent graph/module ablation."""
    graph_only = SimulationRunner(seed=42, config={"graph_behavior_enabled": True})
    fish = next(e for e in graph_only.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.behavior_graph is not None
    assert fish.genome.behavioral.target_pursuit_module is None

    both_enabled = SimulationRunner(
        seed=42,
        config={"graph_behavior_enabled": True, "target_pursuit_module_enabled": True},
    )
    fish = next(e for e in both_enabled.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.behavior_graph is not None
    assert fish.genome.behavioral.target_pursuit_module is not None
    assert isinstance(fish.genome.behavioral.target_pursuit_module.value, BehaviorGraph)

    module_flag_only = SimulationRunner(seed=42, config={"target_pursuit_module_enabled": True})
    fish = next(e for e in module_flag_only.world.entities_list if isinstance(e, Fish))
    assert fish.genome.behavioral.behavior_graph is None
    assert fish.genome.behavioral.target_pursuit_module is not None


def test_same_module_instance_serves_both_food_and_soccer_domains() -> None:
    """The central claim: one inherited/mutated module, reachable by both
    adapters through the same genome trait - not two independent copies."""
    from core.behavior.soccer_adapter import build_soccer_target_observation
    from core.behavior.tank_adapter import build_tank_behavior_observation
    from core.movement.ball_pursuit import _pursuit_module_vector
    from core.entities.ball import Ball

    runner = SimulationRunner(
        seed=42,
        config={"graph_behavior_enabled": True, "target_pursuit_module_enabled": True},
    )
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    module = fish.genome.behavioral.target_pursuit_module.value
    assert module is not None
    fish.vel.x = fish.vel.y = 0.0

    # Food adapter: build_tank_behavior_observation consults this exact trait.
    build_tank_behavior_observation(fish)  # exercises the food path without error
    assert fish.genome.behavioral.target_pursuit_module.value is module

    # Soccer adapter: same trait, evaluated directly with ball-shaped inputs -
    # a target straight ahead produces a unit vector aimed at it, exactly like
    # the module-level topology test, proving no domain-specific duplication.
    ball = Ball(fish.environment, x=fish.pos.x + 10.0, y=fish.pos.y)
    result = _pursuit_module_vector(fish, ball)
    assert result is not None
    assert result == (1.0, 0.0)

    # And it is reachable via the domain-neutral soccer_adapter contract too.
    ball_observation = build_soccer_target_observation(
        self_position=(fish.pos.x, fish.pos.y),
        self_velocity=(fish.vel.x, fish.vel.y),
        self_speed=fish.speed,
        ball_position=(fish.pos.x + 10.0, fish.pos.y),
        ball_velocity=(0.0, 0.0),
    )
    assert module.compile_cached().evaluate(ball_observation.to_values()) == (1.0, 0.0)


def test_prediction_mutation_changes_moving_food_and_ball_decisions_identically(
    monkeypatch,
) -> None:
    """The same parameter mutation must affect both domain adapters.

    This deliberately enables only the pursuit flag: the result is an ablation
    of the full foraging graph, and the moving target makes prediction visible.
    """
    from core.behavior.tank_adapter import build_tank_behavior_observation
    from core.behavior.soccer_adapter import build_soccer_target_observation
    from core.movement.ball_pursuit import _pursuit_module_vector
    from core.entities.ball import Ball

    runner = SimulationRunner(seed=42, config={"target_pursuit_module_enabled": True})
    fish = next(e for e in runner.world.entities_list if isinstance(e, Fish))
    module = fish.genome.behavioral.target_pursuit_module.value
    assert module is not None

    target = SimpleNamespace(
        pos=SimpleNamespace(x=fish.pos.x + 10.0, y=fish.pos.y),
        vel=SimpleNamespace(x=0.0, y=2.0),
    )
    monkeypatch.setattr("core.behavior.tank_adapter.select_food_target", lambda _fish: target)

    def with_prediction_strength(strength: float) -> BehaviorGraph:
        return BehaviorGraph(
            tuple(
                GraphNode(
                    node.node_id,
                    node.node_type,
                    (
                        {**node.parameters, "prediction_strength": strength}
                        if node.node_id == "intercept"
                        else node.parameters
                    ),
                )
                for node in module.nodes
            ),
            module.connections,
            module.output_node_id,
        )

    ball = Ball(runner.world, x=target.pos.x, y=target.pos.y)
    ball.vel.x, ball.vel.y = target.vel.x, target.vel.y

    def decisions(graph: BehaviorGraph) -> tuple[tuple[float, float], tuple[float, float]]:
        fish.genome.behavioral.target_pursuit_module.value = graph
        food = build_tank_behavior_observation(fish).values["food_vector"]
        soccer = _pursuit_module_vector(fish, ball)
        assert isinstance(food, tuple) and isinstance(soccer, tuple)
        return food, soccer

    direct_food, direct_ball = decisions(with_prediction_strength(0.0))
    predicted_food, predicted_ball = decisions(with_prediction_strength(1.0))

    assert direct_food == direct_ball
    assert predicted_food == predicted_ball
    assert predicted_food != direct_food
    assert predicted_food[1] > direct_food[1]

    observation = build_soccer_target_observation(
        self_position=(fish.pos.x, fish.pos.y),
        self_velocity=(fish.vel.x, fish.vel.y),
        self_speed=fish.speed,
        ball_position=(ball.pos.x, ball.pos.y),
        ball_velocity=(ball.vel.x, ball.vel.y),
    )
    assert (
        with_prediction_strength(1.0).compile_cached().evaluate(observation.to_values())
        == predicted_ball
    )
