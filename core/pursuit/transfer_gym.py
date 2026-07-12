"""A frozen, single-agent pursuit-transfer gym for the shared pursuit module.

Mirrors core/foraging/gym.py's shape: an isolated, deterministic episode
runner with floor and ceiling references, independent of ecosystem
confounders (no reproduction, poker, predators, or population feedback).

This is a first, modest cut at the reusable-pursuit-module transfer claim,
not the full multi-generation, multi-seed research study: "training" is a
minimal mutate-and-select (1+K) hill-climb over the shared module's own
crossed_over(), standing in for a full evolutionary population, which is out
of scope here. It evaluates that SAME evolved module, completely unchanged,
against a differently-parameterized test scenario - so beating the untrained
default demonstrates genuine generalization, not a memorized trajectory.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass

from core.behavior.graph import BehaviorGraph, GraphNode
from core.behavior.nodes import NodeParameter, Scalar
from core.behavior.pursuit_nodes import default_pursuit_module_graph
from core.math_utils import Vector2

PURSUER_SPEED = 3.0
CAPTURE_RADIUS = 12.0
MAX_FRAMES = 300
MUTATION_CANDIDATES = 8
MUTATION_STRENGTH = 0.3


@dataclass(frozen=True)
class InterceptionResult:
    """One pursuer's outcome chasing one scripted moving target."""

    intercepted: bool
    time_to_intercept: int | None
    closest_approach: float
    energy_spent: float

    def to_dict(self) -> dict[str, float | int | bool | None]:
        return {
            "intercepted": self.intercepted,
            "time_to_intercept": self.time_to_intercept,
            "closest_approach": self.closest_approach,
            "energy_spent": self.energy_spent,
        }


@dataclass(frozen=True)
class PursuitTransferEvaluation:
    """Floor, untrained, evolved, and ceiling outcomes on the zero-shot test scenario."""

    floor: InterceptionResult
    untrained: InterceptionResult
    evolved: InterceptionResult
    ceiling: InterceptionResult

    @property
    def floor_score(self) -> float:
        return _fitness(self.floor)

    @property
    def untrained_score(self) -> float:
        return _fitness(self.untrained)

    @property
    def evolved_score(self) -> float:
        return _fitness(self.evolved)

    @property
    def ceiling_score(self) -> float:
        return _fitness(self.ceiling)


def _fitness(result: InterceptionResult) -> float:
    """Higher is better. Any interception beats any non-interception; within
    a category, faster interception / closer approach scores higher."""
    if result.intercepted:
        assert result.time_to_intercept is not None
        return 1.0 + 1.0 / result.time_to_intercept
    return 1.0 / (1.0 + result.closest_approach)


def _target_trajectory(seed: int, *, speed_scale: float) -> tuple[Vector2, Vector2, Vector2]:
    """Deterministic pursuer/target start positions and target velocity.

    A fixed integer recurrence (not the platform RNG) scripts the scenario,
    matching core/foraging/gym.py's build_food_schedule so this never drifts
    with unrelated simulation RNG changes elsewhere.
    """
    state = seed & 0xFFFFFFFF

    def _next() -> int:
        nonlocal state
        state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
        return state

    angle = (_next() % 360) * math.pi / 180.0
    distance = 80.0 + float(_next() % 120)
    pursuer_start = Vector2(0.0, 0.0)
    target_start = Vector2(math.cos(angle) * distance, math.sin(angle) * distance)
    heading = (_next() % 360) * math.pi / 180.0
    target_speed = speed_scale * (0.5 + (_next() % 100) / 100.0)
    target_velocity = Vector2(math.cos(heading) * target_speed, math.sin(heading) * target_speed)
    return pursuer_start, target_start, target_velocity


def run_interception_episode(
    module: BehaviorGraph,
    *,
    pursuer_start: Vector2,
    target_start: Vector2,
    target_velocity: Vector2,
) -> InterceptionResult:
    """Run one deterministic pursuer-vs-moving-target episode against ``module``."""
    compiled = module.compile_cached()
    pursuer_pos = pursuer_start
    pursuer_vel = Vector2(0.0, 0.0)
    target_pos = target_start
    closest = (target_pos - pursuer_pos).length()
    energy_spent = 0.0

    for frame in range(1, MAX_FRAMES + 1):
        target_pos = Vector2(target_pos.x + target_velocity.x, target_pos.y + target_velocity.y)
        target_vector = (target_pos.x - pursuer_pos.x, target_pos.y - pursuer_pos.y)
        output = compiled.evaluate(
            {
                "target_vector": target_vector,
                "target_velocity": (target_velocity.x, target_velocity.y),
                "self_velocity": (pursuer_vel.x, pursuer_vel.y),
            }
        )
        vx, vy = (float(output[0]), float(output[1])) if isinstance(output, tuple) else (0.0, 0.0)
        pursuer_vel = Vector2(vx * PURSUER_SPEED, vy * PURSUER_SPEED)
        pursuer_pos = Vector2(pursuer_pos.x + pursuer_vel.x, pursuer_pos.y + pursuer_vel.y)
        energy_spent += pursuer_vel.length()
        distance = (target_pos - pursuer_pos).length()
        closest = min(closest, distance)
        if distance <= CAPTURE_RADIUS:
            return InterceptionResult(True, frame, closest, energy_spent)

    return InterceptionResult(False, None, closest, energy_spent)


def _with_node_params(
    graph: BehaviorGraph, node_id: str, extra_parameters: Mapping[str, NodeParameter]
) -> BehaviorGraph:
    nodes = tuple(
        (
            GraphNode(node.node_id, node.node_type, {**node.parameters, **extra_parameters})
            if node.node_id == node_id
            else node
        )
        for node in graph.nodes
    )
    return BehaviorGraph(nodes, graph.connections, graph.output_node_id)


def _naive_direct_pursuit_module() -> BehaviorGraph:
    """Floor: no prediction at all - matches pre-module direct-line ball chase."""
    return _with_node_params(
        default_pursuit_module_graph(), "intercept", {"prediction_strength": Scalar(0.0)}
    )


# Small deterministic grid searched for the ceiling reference (see
# _ceiling_module). Higher prediction_strength is not simply "better" here:
# because self_velocity itself depends on the module's own prior-frame
# output, strong prediction combined with a fast pursuer can overcorrect
# into oscillation (empirically confirmed - see the PR description). The
# grid finds a good point rather than assuming "generous" parameters win.
_CEILING_PREDICTION_STRENGTHS = (0.5, 0.7, 1.0)
_CEILING_COMMITMENT_SCALES = (1.0, 1.3, 1.6)


def _ceiling_module(
    *, pursuer_start: Vector2, target_start: Vector2, target_velocity: Vector2
) -> BehaviorGraph:
    """Ceiling: the best of a small hand-authored parameter grid for THIS episode.

    Like core/foraging/gym.py's oracle policy, a ceiling reference is allowed
    full-information tuning to the specific episode it is scored on - unlike
    the evolved module, it does not need to generalize zero-shot.
    """
    best_graph: BehaviorGraph | None = None
    best_score = float("-inf")
    for prediction_strength in _CEILING_PREDICTION_STRENGTHS:
        for scale in _CEILING_COMMITMENT_SCALES:
            candidate = _with_node_params(
                default_pursuit_module_graph(),
                "intercept",
                {"prediction_strength": Scalar(prediction_strength)},
            )
            candidate = _with_node_params(candidate, "pursuit", {"scale": Scalar(scale)})
            score = _fitness(
                run_interception_episode(
                    candidate,
                    pursuer_start=pursuer_start,
                    target_start=target_start,
                    target_velocity=target_velocity,
                )
            )
            if score > best_score:
                best_graph, best_score = candidate, score
    assert best_graph is not None
    return best_graph


def _evolve_via_foraging(seed: int) -> BehaviorGraph:
    """Approximate 'evolved via foraging' with a minimal mutate-and-select step.

    A full multi-generation population is out of scope for this first, modest
    benchmark (see module docstring); this is a (1+K) hill-climb: generate K
    mutants of the default module, score each on one moving-food-flavored
    training episode, and keep the best.
    """
    base = default_pursuit_module_graph()
    rng = random.Random(seed)
    pursuer_start, target_start, target_velocity = _target_trajectory(seed, speed_scale=1.2)

    def score(candidate: BehaviorGraph) -> float:
        return _fitness(
            run_interception_episode(
                candidate,
                pursuer_start=pursuer_start,
                target_start=target_start,
                target_velocity=target_velocity,
            )
        )

    best, best_score = base, score(base)
    for _ in range(MUTATION_CANDIDATES):
        candidate = base.crossed_over(
            base, weight1=0.5, mutation_rate=1.0, mutation_strength=MUTATION_STRENGTH, rng=rng
        )
        candidate_score = score(candidate)
        if candidate_score > best_score:
            best, best_score = candidate, candidate_score
    return best


def evaluate_pursuit_transfer(seed: int) -> PursuitTransferEvaluation:
    """Train (mutate+select) on a foraging-flavored task; test zero-shot on a
    differently-parameterized soccer-ball-flavored interception task."""
    evolved = _evolve_via_foraging(seed)
    untrained = default_pursuit_module_graph()
    floor_module = _naive_direct_pursuit_module()

    # A different trajectory (seed+1, different speed_scale) than training, so
    # success here demonstrates generalization rather than memorized parameters.
    pursuer_start, target_start, target_velocity = _target_trajectory(seed + 1, speed_scale=1.8)
    ceiling = _ceiling_module(
        pursuer_start=pursuer_start, target_start=target_start, target_velocity=target_velocity
    )

    def evaluate(module: BehaviorGraph) -> InterceptionResult:
        return run_interception_episode(
            module,
            pursuer_start=pursuer_start,
            target_start=target_start,
            target_velocity=target_velocity,
        )

    return PursuitTransferEvaluation(
        floor=evaluate(floor_module),
        untrained=evaluate(untrained),
        evolved=evaluate(evolved),
        ceiling=evaluate(ceiling),
    )
