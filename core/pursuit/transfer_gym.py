"""A modular, population-based pursuit-transfer gym for the shared pursuit module.

Provides versioned, deterministic train/val/test trajectory sets for moving food
(foraging) and soccer ball targets. Evaluates multiple comparison groups and tracks
both zero-shot transfer benefit and soccer adaptation speed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from core.behavior.graph import BehaviorGraph, GraphNode
from core.behavior.nodes import Scalar
from core.behavior.pursuit_nodes import default_pursuit_module_graph
from core.math_utils import Vector2

PURSUER_SPEED = 3.0
CAPTURE_RADIUS = 12.0
MAX_FRAMES = 300

# Evolution hyperparameters
POPULATION_SIZE = 16
GENERATIONS = 15
EVOLUTION_RUNS = 2
MUTATION_RATE = 0.2
MUTATION_STRENGTH = 0.1
CROSSOVER_WEIGHT = 0.5


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
class EvaluationSummary:
    """Aggregated metrics over a set of scenarios."""

    capture_rate: float
    median_time: float | None
    mean_miss_distance: float
    mean_energy_spent: float
    family_fitness: dict[str, float]
    overall_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_rate": self.capture_rate,
            "median_time": self.median_time,
            "mean_miss_distance": self.mean_miss_distance,
            "mean_energy_spent": self.mean_energy_spent,
            "family_fitness": self.family_fitness,
            "overall_score": self.overall_score,
        }


@dataclass(frozen=True)
class PursuitScenario:
    """A parameterized interception scenario with a specific trajectory pattern."""

    scenario_id: str
    family_name: str
    pursuer_start: Vector2
    target_positions: list[Vector2]
    target_velocities: list[Vector2]


@dataclass(frozen=True)
class PursuitTransferEvaluation:
    """Rich evaluation payload comparing multiple groups on the zero-shot test set."""

    group_summaries: dict[str, EvaluationSummary]
    adaptation_generations_food: int
    adaptation_generations_random: int
    adaptation_threshold: float

    @property
    def direct_score(self) -> float:
        return self.group_summaries["direct_pursuit"].overall_score

    @property
    def default_score(self) -> float:
        return self.group_summaries["default_module"].overall_score

    @property
    def food_trained_score(self) -> float:
        return self.group_summaries["food_trained"].overall_score

    @property
    def soccer_trained_score(self) -> float:
        return self.group_summaries["soccer_trained"].overall_score

    @property
    def constant_velocity_solver_score(self) -> float:
        return self.group_summaries["constant_velocity_solver"].overall_score


def _fitness(result: InterceptionResult) -> float:
    """Higher is better. Any interception beats any non-interception; within
    a category, faster interception / closer approach scores higher."""
    if result.intercepted:
        assert result.time_to_intercept is not None
        return 1.0 + 1.0 / result.time_to_intercept
    return 1.0 / (1.0 + result.closest_approach)


class ConstantVelocityInterceptor:
    """Analytical reference policy for targets that keep a constant velocity.

    Held-out ball trajectories can bounce, decelerate, or change direction, so
    this is a comparison group rather than an upper-bound "ceiling."
    """

    def compile_cached(self) -> ConstantVelocityInterceptor:
        return self

    def evaluate(self, inputs: dict[str, Any]) -> tuple[float, float]:
        target_x, target_y = inputs["target_vector"]
        target_vx, target_vy = inputs["target_velocity"]
        self_vx, self_vy = inputs["self_velocity"]
        self_speed = inputs["self_speed"]

        # Solve: ||P_t + V_t * t - P_s|| = s * t
        # Let P_t - P_s be (target_x, target_y)
        # Solve quadratic: a * t^2 + b * t + c = 0
        # a = s^2 - ||V_t||^2
        # b = -2 * (P_t - P_s) . V_t
        # c = -||P_t - P_s||^2
        a = self_speed**2 - (target_vx**2 + target_vy**2)
        b = -2.0 * (target_x * target_vx + target_y * target_vy)
        c = -(target_x**2 + target_y**2)

        discriminant = b**2 - 4 * a * c
        if discriminant < 0:
            # Cannot intercept: steer directly at current target position
            dist = math.hypot(target_x, target_y)
            return (target_x / dist, target_y / dist) if dist > 0 else (0.0, 0.0)

        if abs(a) < 1e-6:
            t = -c / b if abs(b) > 1e-6 else 0.0
        else:
            t1 = (-b + math.sqrt(discriminant)) / (2 * a)
            t2 = (-b - math.sqrt(discriminant)) / (2 * a)
            pos_ts = [val for val in (t1, t2) if val > 0]
            t = min(pos_ts) if pos_ts else 0.0

        # Predicted interception point
        ix = target_x + target_vx * t
        iy = target_y + target_vy * t

        dist = math.hypot(ix, iy)
        return (ix / dist, iy / dist) if dist > 0 else (0.0, 0.0)


def generate_food_trajectory(
    family_idx: int,
    rng: random.Random,
) -> tuple[Vector2, list[Vector2], list[Vector2]]:
    """Generate linear food trajectories belonging to one of 5 families."""
    pursuer_start = Vector2(0.0, 0.0)
    angle = rng.uniform(0, 2 * math.pi)
    distance = rng.uniform(80.0, 160.0)
    target_start = Vector2(math.cos(angle) * distance, math.sin(angle) * distance)

    positions = []
    velocities = []
    current_pos = target_start

    if family_idx == 0:
        # Stationary or slowly sinking
        sinking = rng.choice([True, False])
        v = Vector2(0.0, rng.uniform(-0.5, -0.1) if sinking else 0.0)
    elif family_idx == 1:
        # Lateral movement
        perp_angle = angle + math.pi / 2 if rng.choice([True, False]) else angle - math.pi / 2
        speed = rng.uniform(0.5, 1.5)
        v = Vector2(math.cos(perp_angle) * speed, math.sin(perp_angle) * speed)
    elif family_idx == 2:
        # Toward or away
        toward = rng.choice([True, False])
        if toward:
            speed = rng.uniform(0.5, 1.5)
            dir_vec = Vector2(-math.cos(angle), -math.sin(angle))
            v = dir_vec * speed
        else:
            # Start closer and move away
            distance = rng.uniform(50.0, 90.0)
            target_start = Vector2(math.cos(angle) * distance, math.sin(angle) * distance)
            current_pos = target_start
            speed = rng.uniform(0.5, 1.5)
            dir_vec = Vector2(math.cos(angle), math.sin(angle))
            v = dir_vec * speed
    elif family_idx == 3:
        # Direction changes
        change_frame = rng.randint(80, 180)
        speed = rng.uniform(0.8, 1.8)
        h1 = rng.uniform(0, 2 * math.pi)
        v1 = Vector2(math.cos(h1) * speed, math.sin(h1) * speed)
        h2 = h1 + rng.choice([math.pi / 2, -math.pi / 2, math.pi])
        v2 = Vector2(math.cos(h2) * speed, math.sin(h2) * speed)

        curr_v = v1
        for frame in range(MAX_FRAMES + 1):
            if frame == change_frame:
                curr_v = v2
            positions.append(current_pos.copy())
            velocities.append(curr_v.copy())
            current_pos += curr_v
        return pursuer_start, positions, velocities
    else:
        # Different speed ratios
        ratio = rng.uniform(0.1, 0.8)
        speed = ratio * PURSUER_SPEED
        h = rng.uniform(0, 2 * math.pi)
        v = Vector2(math.cos(h) * speed, math.sin(h) * speed)

    for _ in range(MAX_FRAMES + 1):
        positions.append(current_pos.copy())
        velocities.append(v.copy())
        current_pos += v

    return pursuer_start, positions, velocities


def generate_ball_trajectory(
    family_idx: int,
    rng: random.Random,
) -> tuple[Vector2, list[Vector2], list[Vector2]]:
    """Generate ball trajectories modeling friction, boundary bouncing, swerves, and kicks."""
    pursuer_start = Vector2(0.0, 0.0)
    angle = rng.uniform(0, 2 * math.pi)
    distance = rng.uniform(80.0, 160.0)
    target_start = Vector2(math.cos(angle) * distance, math.sin(angle) * distance)

    positions = []
    velocities = []
    current_pos = target_start

    if family_idx == 0:
        # Decelerating Ball (friction)
        speed = rng.uniform(3.0, 5.0)
        h = rng.uniform(0, 2 * math.pi)
        v = Vector2(math.cos(h) * speed, math.sin(h) * speed)
        friction = 0.985
        for _ in range(MAX_FRAMES + 1):
            positions.append(current_pos.copy())
            velocities.append(v.copy())
            current_pos += v
            v *= friction
    elif family_idx == 1:
        # Bouncing Ball (virtual boundaries)
        min_x, max_x = -150.0, 150.0
        min_y, max_y = -150.0, 150.0
        cx = max(min_x + 10.0, min(max_x - 10.0, target_start.x))
        cy = max(min_y + 10.0, min(max_y - 10.0, target_start.y))
        current_pos = Vector2(cx, cy)
        speed = rng.uniform(1.5, 3.0)
        h = rng.uniform(0, 2 * math.pi)
        v = Vector2(math.cos(h) * speed, math.sin(h) * speed)
        for _ in range(MAX_FRAMES + 1):
            positions.append(current_pos.copy())
            velocities.append(v.copy())
            next_pos = current_pos + v
            vx, vy = v.x, v.y
            if next_pos.x <= min_x or next_pos.x >= max_x:
                vx = -vx
            if next_pos.y <= min_y or next_pos.y >= max_y:
                vy = -vy
            v = Vector2(vx, vy)
            current_pos += v
    elif family_idx == 2:
        # Swerve / Curve
        speed = rng.uniform(1.5, 2.5)
        h = rng.uniform(0, 2 * math.pi)
        omega = rng.uniform(0.015, 0.035) * rng.choice([-1.0, 1.0])
        for _ in range(MAX_FRAMES + 1):
            v = Vector2(math.cos(h) * speed, math.sin(h) * speed)
            positions.append(current_pos.copy())
            velocities.append(v.copy())
            current_pos += v
            h += omega
    elif family_idx == 3:
        # Sudden Kick (velocity change)
        change_frame = rng.randint(80, 150)
        speed1 = rng.uniform(1.2, 2.2)
        h1 = rng.uniform(0, 2 * math.pi)
        v1 = Vector2(math.cos(h1) * speed1, math.sin(h1) * speed1)
        speed2 = rng.uniform(1.5, 3.0)
        h2 = rng.uniform(0, 2 * math.pi)
        v2 = Vector2(math.cos(h2) * speed2, math.sin(h2) * speed2)

        v = v1
        for frame in range(MAX_FRAMES + 1):
            if frame == change_frame:
                v = v2
            positions.append(current_pos.copy())
            velocities.append(v.copy())
            current_pos += v
    else:
        # High speed ratios
        ratio = rng.uniform(0.8, 1.3)
        speed = ratio * PURSUER_SPEED
        h = rng.uniform(0, 2 * math.pi)
        v = Vector2(math.cos(h) * speed, math.sin(h) * speed)
        for _ in range(MAX_FRAMES + 1):
            positions.append(current_pos.copy())
            velocities.append(v.copy())
            current_pos += v

    return pursuer_start, positions, velocities


def generate_scenario_set(
    set_type: str,
    seed: int,
    version: str = "v2",
) -> list[PursuitScenario]:
    """Generate a versioned set of deterministic target scenarios."""
    salt = {
        "train": 1000,
        "validation": 2000,
        "held_out": 3000,
        "soccer_train": 4000,
        "soccer_validation": 5000,
    }[set_type]
    rng = random.Random(seed + salt)

    scenarios = []
    # 8 scenarios: families [0, 0, 1, 1, 2, 2, 3, 4]
    family_distribution = [0, 0, 1, 1, 2, 2, 3, 4]
    family_names = {
        0: "stationary_sinking",
        1: "lateral_movement",
        2: "toward_away",
        3: "direction_changes",
        4: "speed_ratios",
    }

    for idx, fam in enumerate(family_distribution):
        scenario_id = f"{set_type}_{version}_{idx}"
        fam_name = family_names[fam]

        if "soccer" in set_type or set_type == "held_out":
            p_start, positions, velocities = generate_ball_trajectory(fam, rng)
        else:
            p_start, positions, velocities = generate_food_trajectory(fam, rng)

        scenarios.append(
            PursuitScenario(
                scenario_id=scenario_id,
                family_name=fam_name,
                pursuer_start=p_start,
                target_positions=positions,
                target_velocities=velocities,
            )
        )
    return scenarios


def run_interception_episode(
    module: BehaviorGraph | ConstantVelocityInterceptor,
    scenario: PursuitScenario,
) -> InterceptionResult:
    """Run one deterministic pursuer-vs-target episode."""
    compiled = module.compile_cached()
    pursuer_pos = scenario.pursuer_start.copy()
    pursuer_vel = Vector2(0.0, 0.0)
    closest = (scenario.target_positions[0] - pursuer_pos).length()
    energy_spent = 0.0

    for frame in range(1, MAX_FRAMES + 1):
        target_pos = scenario.target_positions[frame]
        target_velocity = scenario.target_velocities[frame]
        target_vector = (target_pos.x - pursuer_pos.x, target_pos.y - pursuer_pos.y)

        inputs = {
            "target_vector": target_vector,
            "target_velocity": (target_velocity.x, target_velocity.y),
            "self_velocity": (pursuer_vel.x, pursuer_vel.y),
            "self_speed": PURSUER_SPEED,
        }

        output = compiled.evaluate(inputs)
        vx, vy = (float(output[0]), float(output[1])) if isinstance(output, tuple) else (0.0, 0.0)

        mag = math.hypot(vx, vy)
        if mag > 1e-9:
            vx, vy = vx / mag, vy / mag

        pursuer_vel = Vector2(vx * PURSUER_SPEED, vy * PURSUER_SPEED)
        pursuer_pos = pursuer_pos + pursuer_vel
        energy_spent += pursuer_vel.length()

        distance = (target_pos - pursuer_pos).length()
        closest = min(closest, distance)
        if distance <= CAPTURE_RADIUS:
            return InterceptionResult(True, frame, closest, energy_spent)

    return InterceptionResult(False, None, closest, energy_spent)


def evaluate_module_on_set(
    module: BehaviorGraph | ConstantVelocityInterceptor,
    scenarios: list[PursuitScenario],
) -> EvaluationSummary:
    """Evaluate a module across an entire scenario set and calculate aggregated statistics."""
    results = []
    for scenario in scenarios:
        res = run_interception_episode(module, scenario)
        results.append((scenario, res))

    captured = [res for _, res in results if res.intercepted]
    capture_rate = len(captured) / len(results)

    if captured:
        times: list[int] = sorted(
            [res.time_to_intercept for res in captured if res.time_to_intercept is not None]
        )
        n = len(times)
        if n == 0:
            median_time = None
        elif n % 2 == 1:
            median_time = float(times[n // 2])
        else:
            median_time = float(times[n // 2 - 1] + times[n // 2]) / 2.0
    else:
        median_time = None

    mean_miss_distance = sum(res.closest_approach for _, res in results) / len(results)
    mean_energy_spent = sum(res.energy_spent for _, res in results) / len(results)
    overall_score = sum(_fitness(res) for _, res in results) / len(results)

    family_scores: dict[str, float] = {}
    family_counts: dict[str, int] = {}
    for scenario, res in results:
        fam = scenario.family_name
        family_scores[fam] = family_scores.get(fam, 0.0) + _fitness(res)
        family_counts[fam] = family_counts.get(fam, 0) + 1

    family_fitness = {fam: family_scores[fam] / family_counts[fam] for fam in family_scores}

    return EvaluationSummary(
        capture_rate=capture_rate,
        median_time=median_time,
        mean_miss_distance=mean_miss_distance,
        mean_energy_spent=mean_energy_spent,
        family_fitness=family_fitness,
        overall_score=overall_score,
    )


def run_evolution(
    initial_population: list[BehaviorGraph],
    scenarios: list[PursuitScenario],
    generations: int,
    pop_size: int,
    rng: random.Random,
    target_score_threshold: float | None = None,
    validation_scenarios: list[PursuitScenario] | None = None,
) -> tuple[BehaviorGraph, list[float], int]:
    """Run genetic algorithm over the graph's parameters with optional validation selection."""
    population = list(initial_population)
    while len(population) < pop_size:
        seed_module = population[rng.randrange(len(population))]
        var = seed_module.crossed_over(
            seed_module, weight1=1.0, mutation_rate=1.0, mutation_strength=0.3, rng=rng
        )
        population.append(var)

    best_module = population[0]
    best_score = float("-inf")
    history = []

    pop_scores = []
    for module in population:
        score = evaluate_module_on_set(module, scenarios).overall_score
        pop_scores.append(score)
        if score > best_score:
            best_score = score
            best_module = module

    history.append(best_score)

    selected_module = best_module
    best_validation_score = float("-inf")
    if validation_scenarios is not None:
        best_validation_score = evaluate_module_on_set(
            best_module, validation_scenarios
        ).overall_score

    if target_score_threshold is not None and best_score >= target_score_threshold:
        return best_module, history, 0

    for gen in range(1, generations + 1):
        new_population = []
        elite_idx = pop_scores.index(max(pop_scores))
        new_population.append(population[elite_idx])

        while len(new_population) < pop_size:
            t1 = rng.sample(
                list(zip(population, pop_scores, strict=False)),
                min(3, len(population)),
            )
            parent1 = max(t1, key=lambda x: x[1])[0]

            t2 = rng.sample(
                list(zip(population, pop_scores, strict=False)),
                min(3, len(population)),
            )
            parent2 = max(t2, key=lambda x: x[1])[0]

            child = parent1.crossed_over(
                parent2,
                weight1=CROSSOVER_WEIGHT,
                mutation_rate=MUTATION_RATE,
                mutation_strength=MUTATION_STRENGTH,
                rng=rng,
            )
            new_population.append(child)

        population = new_population
        pop_scores = [best_score]

        for module in population[1:]:
            score = evaluate_module_on_set(module, scenarios).overall_score
            pop_scores.append(score)
            if score > best_score:
                best_score = score
                best_module = module

        history.append(best_score)

        if validation_scenarios is not None:
            elite = population[pop_scores.index(max(pop_scores))]
            validation_score = evaluate_module_on_set(elite, validation_scenarios).overall_score
            if validation_score > best_validation_score:
                best_validation_score = validation_score
                selected_module = elite

        if target_score_threshold is not None and best_score >= target_score_threshold:
            return selected_module, history, gen

    return selected_module, history, generations


def _naive_direct_pursuit_module() -> BehaviorGraph:
    """Naively chases without any velocity lead prediction."""
    nodes = tuple(
        (
            GraphNode(
                node.node_id,
                node.node_type,
                {**node.parameters, "prediction_strength": Scalar(0.0)},
            )
            if node.node_id == "intercept"
            else node
        )
        for node in default_pursuit_module_graph().nodes
    )
    return BehaviorGraph(
        nodes,
        default_pursuit_module_graph().connections,
        default_pursuit_module_graph().output_node_id,
    )


def evaluate_pursuit_transfer(seed: int) -> PursuitTransferEvaluation:
    """Evolve populations over food trajectories; evaluate zero-shot and measure adaptation on ball trajectories."""
    train_food = generate_scenario_set("train", seed)
    validation_food = generate_scenario_set("validation", seed)
    test_ball = generate_scenario_set("held_out", seed)
    train_soccer = generate_scenario_set("soccer_train", seed)
    validation_soccer = generate_scenario_set("soccer_validation", seed)

    base_module = default_pursuit_module_graph()
    direct_pursuit = _naive_direct_pursuit_module()
    constant_velocity_solver = ConstantVelocityInterceptor()

    summaries = {}

    # Group 1: Direct pursuit
    summaries["direct_pursuit"] = evaluate_module_on_set(direct_pursuit, test_ball)

    # Group 2: Default module
    summaries["default_module"] = evaluate_module_on_set(base_module, test_ball)

    # Group 3: Compute-matched random search
    rng_random = random.Random(seed + 4000)
    best_random = base_module
    best_random_score = float("-inf")
    for _ in range(POPULATION_SIZE * GENERATIONS * EVOLUTION_RUNS):
        candidate = base_module.crossed_over(
            base_module,
            weight1=1.0,
            mutation_rate=1.0,
            mutation_strength=MUTATION_STRENGTH,
            rng=rng_random,
        )
        cand_score = evaluate_module_on_set(candidate, train_food).overall_score
        if cand_score > best_random_score:
            best_random = candidate
            best_random_score = cand_score
    summaries["random_search"] = evaluate_module_on_set(best_random, test_ball)

    # Group 4: Food-trained modules (Evolutionary populations)
    food_trained_modules = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 5000 + run_idx * 100)
        initial_pop = [base_module]
        best_of_run, _, _ = run_evolution(
            initial_pop,
            train_food,
            GENERATIONS,
            POPULATION_SIZE,
            run_rng,
            validation_scenarios=validation_food,
        )
        food_trained_modules.append(best_of_run)

    food_evals = [evaluate_module_on_set(m, test_ball) for m in food_trained_modules]
    summaries["food_trained"] = EvaluationSummary(
        capture_rate=sum(e.capture_rate for e in food_evals) / len(food_evals),
        median_time=(
            sum(e.median_time for e in food_evals if e.median_time is not None) / len(food_evals)
            if any(e.median_time is not None for e in food_evals)
            else None
        ),
        mean_miss_distance=sum(e.mean_miss_distance for e in food_evals) / len(food_evals),
        mean_energy_spent=sum(e.mean_energy_spent for e in food_evals) / len(food_evals),
        family_fitness={
            fam: sum(e.family_fitness.get(fam, 0.0) for e in food_evals) / len(food_evals)
            for fam in food_evals[0].family_fitness
        },
        overall_score=sum(e.overall_score for e in food_evals) / len(food_evals),
    )

    # Group 5: Soccer-trained module (Task-specific reference)
    soccer_trained_modules = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 6000 + run_idx * 100)
        initial_pop = [base_module]
        best_of_run, _, _ = run_evolution(
            initial_pop,
            train_soccer,
            GENERATIONS,
            POPULATION_SIZE,
            run_rng,
            validation_scenarios=validation_soccer,
        )
        soccer_trained_modules.append(best_of_run)

    soccer_evals = [evaluate_module_on_set(m, test_ball) for m in soccer_trained_modules]
    summaries["soccer_trained"] = EvaluationSummary(
        capture_rate=sum(e.capture_rate for e in soccer_evals) / len(soccer_evals),
        median_time=(
            sum(e.median_time for e in soccer_evals if e.median_time is not None)
            / len(soccer_evals)
            if any(e.median_time is not None for e in soccer_evals)
            else None
        ),
        mean_miss_distance=sum(e.mean_miss_distance for e in soccer_evals) / len(soccer_evals),
        mean_energy_spent=sum(e.mean_energy_spent for e in soccer_evals) / len(soccer_evals),
        family_fitness={
            fam: sum(e.family_fitness.get(fam, 0.0) for e in soccer_evals) / len(soccer_evals)
            for fam in soccer_evals[0].family_fitness
        },
        overall_score=sum(e.overall_score for e in soccer_evals) / len(soccer_evals),
    )

    # Group 6: Constant-velocity analytical reference (not a ceiling for changing targets).
    summaries["constant_velocity_solver"] = evaluate_module_on_set(
        constant_velocity_solver, test_ball
    )

    # 3. Adaptation speed measurement
    default_score = summaries["default_module"].overall_score
    soccer_reference_score = summaries["soccer_trained"].overall_score
    adaptation_threshold = default_score + max(
        0.001, (soccer_reference_score - default_score) * 0.75
    )

    adapt_runs_food = []
    adapt_runs_random = []
    for run_idx in range(EVOLUTION_RUNS):
        run_rng = random.Random(seed + 7000 + run_idx * 100)
        food_seed = food_trained_modules[run_idx % len(food_trained_modules)]
        initial_pop_food = [food_seed] * POPULATION_SIZE
        _, _, gens_food = run_evolution(
            initial_pop_food,
            test_ball,
            GENERATIONS * 2,
            POPULATION_SIZE,
            run_rng,
            target_score_threshold=adaptation_threshold,
        )
        adapt_runs_food.append(gens_food)

        initial_pop_rand = [base_module] * POPULATION_SIZE
        _, _, gens_rand = run_evolution(
            initial_pop_rand,
            test_ball,
            GENERATIONS * 2,
            POPULATION_SIZE,
            run_rng,
            target_score_threshold=adaptation_threshold,
        )
        adapt_runs_random.append(gens_rand)

    avg_gens_food = int(round(sum(adapt_runs_food) / len(adapt_runs_food)))
    avg_gens_rand = int(round(sum(adapt_runs_random) / len(adapt_runs_random)))

    return PursuitTransferEvaluation(
        group_summaries=summaries,
        adaptation_generations_food=avg_gens_food,
        adaptation_generations_random=avg_gens_rand,
        adaptation_threshold=adaptation_threshold,
    )
